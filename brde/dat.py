"""
brde.dat - read-only reader for "Battle Realms.dat", the format the .xlsx replaced.

The .dat is the game's own binary copy of the same tables the workbook holds: 111
`Enum_*` tables and 89 data tables. It carries the column names and one type code
per column, so it describes itself and no layout has to be guessed.

Reading only, on purpose. A string field is length-prefixed and stored inline, so
changing one shifts every byte after it and invalidates both offset tables. That
is a different problem from the one this module solves, and it is not started here.

No Qt, no openpyxl, nothing from the rest of the package. This module sits below
`brde.core` in the import order and must not import upwards.

Layout
------
::

    0x00  u32     version, 2
    0x04  u32     header size, 20
    0x08  u32     0
    0x0C  u64     offset of the data block
    header size:
          u32     E, the number of enum tables
          u64 xE  one offset per enum table
          str xE  the table names, "Enum_AbilityType"
    at each enum table's offset:
          u32     C, the number of entries
          str xC  the descriptions
          i32 xC  the codes, in the same order

    at the data block's offset:
          u32     T, the number of data tables
          u64 xT  one offset per table's column block
          u64 xT  one offset per table's row block
          str xT  the table names, "Data_Units"
    at each column block's offset:
          u32     N, the number of columns
          u32 xN  the field type of each column
          str xN  the column names
    at each row block's offset:
          u32     R, the number of rows
                  R rows of N fields, packed with no padding or alignment

A string is a tag byte, then a u32 length counting UTF-16 code units *including*
the terminator, then that many UTF-16LE units. So the length is never 0, and 1 is
the empty string. The tag is 0 for all 33937 strings in the vanilla file; it is
checked rather than skipped, because it is the byte that shows a misparse first.

Field types: 2 is a one-byte boolean, 4 an i32, 5 a f32, 7 a string. Nothing else
occurs in the vanilla file, and an unknown code is an error rather than a guess -
inventing a width would silently shift every field after it and still produce
numbers that look like numbers.

Two things this module does not do, both deliberate. It does not infer which
column references which enum: the .dat has explicit type codes, and the inference
in `brde.schema` exists precisely because the .xlsx threw them away. And it does
not format an enum label, so the `' - '` separator keeps the four definitions it
already has rather than gaining a fifth here.
"""
from __future__ import annotations

import struct

__all__ = ['DatError', 'DatEnum', 'DatTable', 'DatFile', 'xlsx_sheet_name',
           'FIELD_BOOL', 'FIELD_INT', 'FIELD_FLOAT', 'FIELD_STRING',
           'FIELD_NAMES']

SUPPORTED_VERSIONS = (2,)
HEADER_SIZE = 20
STRING_TAG = 0

FIELD_BOOL = 2
FIELD_INT = 4
FIELD_FLOAT = 5
FIELD_STRING = 7

FIELD_NAMES = {FIELD_BOOL: 'bool', FIELD_INT: 'int',
               FIELD_FLOAT: 'float', FIELD_STRING: 'string'}

# Excel's own limit on a sheet name, and the reason four tables are named
# differently in the two files: "Enum_AbilityType" fits, while
# "Enum_InterfaceModelAnimStateType" is 32 characters and lands in the workbook
# as "Enum_InterfaceModelAnimStateTyp". Plain truncation, nothing cleverer.
EXCEL_SHEET_LIMIT = 31


class DatError(Exception):
    """The file is not a Battle Realms .dat, or is not shaped like one."""


def xlsx_sheet_name(name: str) -> str:
    """The .dat table name as the workbook spells it.

    Four names differ between the two files and all four differ only by being too
    long for Excel: `Data_UnitToWarPartyEffectiveness` is the data one, and
    `Enum_InterfaceModelAnimStateType`, `Enum_ProjectileCollisionResultType` and
    `Enum_UnitStaticAttachmentStateType` are the enums. Use this to look a .dat
    table up in a `BRWorkbook`, never the raw name.
    """
    return name[:EXCEL_SHEET_LIMIT]


# ------------------------------------------------------------------ reading
class _Reader:
    """A position in the buffer, and the primitives the format is made of."""

    __slots__ = ('buf', 'pos')

    def __init__(self, buf: bytes, pos: int = 0):
        self.buf = buf
        self.pos = pos

    def seek(self, pos: int):
        if not 0 <= pos <= len(self.buf):
            raise DatError('offset 0x%X is outside the file (size 0x%X)'
                           % (pos, len(self.buf)))
        self.pos = pos

    def _unpack(self, fmt: str, size: int):
        try:
            v = struct.unpack_from(fmt, self.buf, self.pos)[0]
        except struct.error:
            raise DatError('the file ends inside a %d byte field at 0x%X'
                           % (size, self.pos)) from None
        self.pos += size
        return v

    def u32(self) -> int:
        return self._unpack('<I', 4)

    def i32(self) -> int:
        return self._unpack('<i', 4)

    def f32(self) -> float:
        return self._unpack('<f', 4)

    def u64(self) -> int:
        return self._unpack('<Q', 8)

    def byte(self) -> int:
        if self.pos >= len(self.buf):
            raise DatError('the file ends at 0x%X, where a byte was expected'
                           % self.pos)
        v = self.buf[self.pos]
        self.pos += 1
        return v

    def string(self) -> str:
        start = self.pos
        tag = self.byte()
        if tag != STRING_TAG:
            raise DatError('string at 0x%X has tag %d, expected %d'
                           % (start, tag, STRING_TAG))
        units = self.u32()
        if units < 1:
            raise DatError('string at 0x%X has length 0; the terminator is '
                           'counted, so 1 is the shortest there can be' % start)
        end = self.pos + 2 * units
        if end > len(self.buf):
            raise DatError('string at 0x%X claims %d characters, which runs past '
                           'the end of the file' % (start, units))
        raw = self.buf[self.pos:end]
        self.pos = end
        if raw[-2:] != b'\x00\x00':
            raise DatError('string at 0x%X is not NUL terminated' % start)
        try:
            return raw[:-2].decode('utf-16-le')
        except UnicodeDecodeError as exc:
            raise DatError('string at 0x%X is not valid UTF-16: %s'
                           % (start, exc)) from None

    def field(self, kind: int):
        """One packed value of the given field type."""
        if kind == FIELD_INT:
            return self.i32()
        if kind == FIELD_FLOAT:
            return self.f32()
        if kind == FIELD_STRING:
            return self.string()
        if kind == FIELD_BOOL:
            # Returned as 0/1 rather than True/False. The workbook stores these
            # columns as 0 and 1, and a Python bool would export as TRUE/FALSE.
            # The raw byte is kept, so a value the game never writes survives.
            return self.byte()
        raise DatError('unknown field type %d at 0x%X' % (kind, self.pos))


# ------------------------------------------------------------------ model
class DatEnum:
    """One Enum_* table: numeric code to description.

    `items` is [(code, description)] in file order. The workbook's `EnumTable`
    carries a third "group" column; the .dat has no counterpart for it.
    """

    __slots__ = ('name', 'items', 'code2desc', 'codes')

    def __init__(self, name: str, items: list):
        self.name = name
        self.items = items
        self.code2desc = {c: d for c, d in items}
        self.codes = set(self.code2desc)

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return '<DatEnum %s, %d codes>' % (self.name, len(self.items))


class DatTable:
    """One data table: column names, their field types, and the rows."""

    __slots__ = ('name', 'headers', 'types', 'rows')

    def __init__(self, name: str, headers: list, types: list, rows: list):
        self.name = name
        self.headers = headers
        self.types = types
        self.rows = rows

    @property
    def ncols(self) -> int:
        return len(self.headers)

    @property
    def nrows(self) -> int:
        return len(self.rows)

    def column_index(self, header: str) -> int:
        """The column's index, or -1. Names are compared exactly, as stored."""
        try:
            return self.headers.index(header)
        except ValueError:
            return -1

    def value(self, row: int, col: int):
        """One cell. Coordinates are 0-based data-area indices, as in brde.core."""
        return self.rows[row][col]

    def as_sheet(self) -> list:
        """Header row followed by the data rows, the shape a sheet is written in."""
        return [list(self.headers)] + [list(r) for r in self.rows]

    def __repr__(self):
        return '<DatTable %s, %d cols x %d rows>' % (self.name, self.ncols,
                                                     self.nrows)


class DatFile:
    """The whole .dat in memory.

    `enums` is keyed without the `Enum_` prefix, the way `BRWorkbook.enums` is.
    `tables` is keyed by the name as the .dat spells it, which is not always what
    the workbook calls it - see `xlsx_sheet_name`.
    """

    def __init__(self, path: str, progress=None, strict: bool = True):
        self.path = path
        self.version = 0
        self.enums: dict[str, DatEnum] = {}
        self.enum_order: list[str] = []
        self.tables: dict[str, DatTable] = {}
        self.table_order: list[str] = []
        with open(path, 'rb') as fh:
            buf = fh.read()
        self._load(buf, progress, strict)

    # -------------------------------------------------------------- loading
    def _load(self, buf: bytes, progress, strict: bool):
        r = _Reader(buf)
        self.version = r.u32()
        if self.version not in SUPPORTED_VERSIONS:
            raise DatError('version %d is not supported (expected %s)'
                           % (self.version,
                              ', '.join(str(v) for v in SUPPORTED_VERSIONS)))
        header_size = r.u32()
        if header_size < HEADER_SIZE:
            raise DatError('header size %d is too small to be a .dat header'
                           % header_size)
        r.u32()                       # always 0 in the vanilla file
        data_at = r.u64()

        # Every block ends exactly where the next one begins, with nothing in
        # between and nothing left over at the end of the file. That is what
        # proved this layout in the first place, so it is checked rather than
        # assumed: a field width read wrongly surfaces here as a few bytes of
        # drift, instead of as plausible-looking nonsense in a cell.
        def ends_at(what: str, expected: int):
            if strict and r.pos != expected:
                raise DatError('%s ends at 0x%X, expected 0x%X'
                               % (what, r.pos, expected))

        r.seek(header_size)
        n_enums = r.u32()
        enum_at = [r.u64() for _ in range(n_enums)]
        enum_names = [r.string() for _ in range(n_enums)]
        if n_enums:
            ends_at('the enum name list', enum_at[0])

        r.seek(data_at)
        n_tables = r.u32()
        cols_at = [r.u64() for _ in range(n_tables)]
        rows_at = [r.u64() for _ in range(n_tables)]
        table_names = [r.string() for _ in range(n_tables)]
        if n_tables:
            ends_at('the table name list', cols_at[0])

        total = n_enums + n_tables
        step = 0
        for i, name in enumerate(enum_names):
            if progress:
                progress(step, total, name)
            step += 1
            r.seek(enum_at[i])
            count = r.u32()
            descs = [r.string() for _ in range(count)]
            codes = [r.i32() for _ in range(count)]
            ends_at(name, enum_at[i + 1] if i + 1 < n_enums else data_at)
            key = name[5:] if name.startswith('Enum_') else name
            self.enums[key] = DatEnum(key, list(zip(codes, descs)))
            self.enum_order.append(key)

        for i, name in enumerate(table_names):
            if progress:
                progress(step, total, name)
            step += 1
            r.seek(cols_at[i])
            ncols = r.u32()
            types = [r.u32() for _ in range(ncols)]
            for kind in types:
                if kind not in FIELD_NAMES:
                    raise DatError('%s: unknown field type %d' % (name, kind))
            headers = [r.string() for _ in range(ncols)]
            ends_at('%s columns' % name,
                    cols_at[i + 1] if i + 1 < n_tables else rows_at[0])

            r.seek(rows_at[i])
            nrows = r.u32()
            rows = [[r.field(k) for k in types] for _ in range(nrows)]
            ends_at('%s rows' % name,
                    rows_at[i + 1] if i + 1 < n_tables else len(buf))

            self.tables[name] = DatTable(name, headers, types, rows)
            self.table_order.append(name)

        if progress:
            progress(total, total, '')

    # ------------------------------------------------------------ accessors
    def value(self, table: str, row: int, col: int):
        """One cell, addressed the way `BRWorkbook.value` addresses one."""
        return self.tables[table].rows[row][col]

    def __repr__(self):
        return '<DatFile %r, %d enums, %d tables>' % (self.path,
                                                      len(self.enums),
                                                      len(self.tables))


# --------------------------------------------------------------- command line
def _main(argv) -> int:
    """python -m brde.dat <file.dat> [table]  - summarise, or dump one table."""
    if not argv:
        print(_main.__doc__.strip())
        return 2
    try:
        dat = DatFile(argv[0])
    except (OSError, DatError) as exc:
        print('error: %s' % exc)
        return 1

    if len(argv) < 2:
        print('%s\nversion %d, %d enum tables, %d data tables\n'
              % (dat.path, dat.version, len(dat.enums), len(dat.tables)))
        for name in dat.table_order:
            t = dat.tables[name]
            print('  %-34s %4d cols x %6d rows' % (name, t.ncols, t.nrows))
        return 0

    wanted = argv[1]
    table = dat.tables.get(wanted)
    if table is None:
        print('no table named %r. Run without a table name to list them.' % wanted)
        return 1
    for i, (head, kind) in enumerate(zip(table.headers, table.types)):
        print('  [%3d] %-40s %s' % (i, head, FIELD_NAMES[kind]))
    print()
    for ri, row in enumerate(table.rows):
        print('%5d  %s' % (ri, '  '.join(str(v) for v in row)))
    return 0


if __name__ == '__main__':
    import sys

    sys.exit(_main(sys.argv[1:]))
