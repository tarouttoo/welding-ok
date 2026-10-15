"""ГОСТ 3.1118-82 form builder (форма 1 / 1а) — layout only (ADR 0001, issue #2).

This module owns the static form: рамка, графы, основная надпись. It fills
nothing and knows nothing about ok.json; render.py maps contract fields into
the coordinates exposed via FormLayout. Fonts, borders, merges and page setup
live here and in the rest of renderer/ — never in the contract.

Geometry is a best-faith millimetre reconstruction of the standard form:
альбомный лист A4 (297×210), поле подшивки 20 мм слева, остальные поля 5 мм;
шапка «Наименование изделия» / «Обозначение изделия»; основная таблица
(Цех … Т шт) per ГОСТ 3.1118-82; большая зона содержания операции; основная
надпись по ГОСТ 3.1103-83 (185×55, форма 1) в правом нижнем углу листа 1 и
малая основная надпись (15 мм, форма 1а) на последующих листах. The
university-supplied xlsx (examples/reference/) is a filling reference only,
never the template; the maintainer should verify the reconstruction against
the ГОСТ text. No geometry assertions exist anywhere (ADR 0001) — mapping
tests only check which value landed in which графа.

The sheet is laid out on a 2 mm column grid so that every zone boundary
(all zone widths are even millimetres) falls on a column edge; rows carry
explicit millimetre heights per zone.
"""

from __future__ import annotations

from dataclasses import dataclass

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.page import PageMargins

# --- sheet geometry, millimetres (all even: they sit on the 2 mm grid) ------

PAGE_W, PAGE_H = 297, 210
FRAME = (20, 5, 292, 205)  # x0, y0, x1, y1: 20 mm binding margin, 5 mm elsewhere
GRID_MM = 2

HEADER = (5, 20)  # шапка изделия: y range; values 5..15, labels 15..20
HEADER_SPLIT_X = 172  # «Наименование изделия» [20, 172] | «Обозначение изделия» [172, 292]

TABLE_HEADER = (20, 35)  # основная таблица per ГОСТ 3.1118-82
TABLE_ROW_H = 8
TABLE_COL_X = (20, 32, 42, 54, 70, 120, 154, 198, 206, 214, 220, 228, 236, 246, 252, 260, 268, 280, 292)
TABLE_HEADERS = (
    "Цех", "Уч.", "Раб. место", "Номер операции", "Код, наименование операции",
    "Обозначение документа", "Код и наименование оборудования", "СМ", "Проф.",
    "Р", "УТ", "КР", "КОИД", "ЕН", "ОП", "Кшт", "Т пз", "Т шт",
)
NUMBER_COL = (54, 70)  # графа «Номер операции»

CONTENT_ROW_H = 8

ON = (106, 150, 292, 205)  # основная надпись, ГОСТ 3.1103-83: 186×55 (185 rounded to the grid)
ON_SPLIT_X = 172  # left block (подписи/изменения) [106, 172] | right block [172, 292]
ON_CHANGES_COLS = (106, 114, 124, 148, 160, 172)
ON_CHANGES_HEADERS = ("Изм.", "Лист", "№ докум.", "Подп.", "Дата")
ON_SIGN_COLS = (106, 130, 146, 158, 172)
ON_SIGNS = ("Разраб.", "Пров.", "Т.контр.", "Н.контр.", "Утв.")
ON_RIGHT_SECTIONS = (150, 165, 190, 200, 205)  # обозначение | наименование | материал | label

FORM1A = (20, TABLE_HEADER[1])  # content zone starts right under the repeated table header
FORM1A_ON = (106, 190, 292, 205)  # малая основная надпись, 15 mm
FORM1A_DESIGNATION_X = (172, 244)
FORM1A_SHEET_X = (244, 268)
FORM1A_SHEETS_X = (268, 292)

BOTTOM_MARGIN_H = 5

# --- styling (everything the renderer never touches) -------------------------

FONT_LABEL = Font(name="Arial", size=6)
FONT_HEADER_LABEL = Font(name="Arial", size=7)
FONT_VALUE = Font(name="Arial", size=10)
SIDE = Side(style="thin")

ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_LEFT_TOP = Alignment(horizontal="left", vertical="top", wrap_text=True)


def _col_units(mm: float) -> float:
    """openpyxl column width units for a wanted width in millimetres."""
    return round((mm * 96 / 25.4 - 5) / 7, 4)


def _row_pt(mm: float) -> float:
    """openpyxl row height points for a wanted height in millimetres."""
    return round(mm * 72 / 25.4, 2)


# --- layout descriptors ------------------------------------------------------


@dataclass(frozen=True)
class SheetLayout:
    """Coordinates a renderer may write to, for one sheet of the form."""

    title: str
    product_name_cell: str | None  # шапка «Наименование изделия» (форма 1 only)
    product_designation_cell: str | None  # шапка «Обозначение изделия»: stays blank
    table_number_cells: tuple[str, ...]  # графа «Номер операции», one per операция
    on_designation_cell: str | None  # основная надпись: обозначение документа (форма 1)
    on_name_cell: str | None  # основная надпись: наименование изделия (форма 1)
    on_material_cell: str | None  # основная надпись: материал (форма 1)
    content_cells: tuple[str, ...]  # зона содержания, top → down
    sheet_no_cell: str | None  # «Лист» on форма 1а
    sheets_total_cell: str | None  # «Листов» on форма 1а


@dataclass(frozen=True)
class FormLayout:
    sheets: tuple[SheetLayout, ...]

    def content_slots(self) -> list[tuple[str, str]]:
        """(sheet title, cell) for every content slot, in fill order."""
        return [(s.title, cell) for s in self.sheets for cell in s.content_cells]


def form1_content_capacity(n_op_rows: int) -> int:
    """Content slots on форма 1 for a given number of таблица body rows."""
    content_top = TABLE_HEADER[1] + n_op_rows * TABLE_ROW_H
    return int((ON[1] - content_top) // CONTENT_ROW_H)


FORM1A_CONTENT_CAPACITY = int((FORM1A_ON[1] - FORM1A[1]) // CONTENT_ROW_H)


# --- painter -----------------------------------------------------------------


class _Sheet:
    """Millimetre-addressed painter over one worksheet.

    Rows are appended with explicit heights; every zone edge coincides with a
    row boundary, so rect() can resolve y-coordinates to row indices exactly.
    """

    def __init__(self, ws, title: str):
        self.ws = ws
        self.title = title
        self.ws.sheet_view.showGridLines = False
        self._y = 0.0
        self._rows: list[tuple[float, float, int]] = []  # (y0, y1, row index)
        self._last_col = 0

    # -- grid

    def add_row(self, height_mm: float) -> int:
        self._y += height_mm
        idx = len(self._rows) + 1
        self._rows.append((self._y - height_mm, self._y, idx))
        self.ws.row_dimensions[idx].height = _row_pt(height_mm)
        return idx

    def finish_grid(self) -> None:
        """Set up columns and page setup; append the bottom margin row.

        Call once all zone rows have been added — it must run last so the
        bottom margin row and the print area sit after every zone.
        """
        self.ws.column_dimensions["A"].width = _col_units(FRAME[0])
        n_grid = (FRAME[2] - FRAME[0]) // GRID_MM
        for k in range(1, n_grid + 1):
            self.ws.column_dimensions[get_column_letter(k + 1)].width = _col_units(GRID_MM)
        self._last_col = n_grid + 2
        self.ws.column_dimensions[get_column_letter(self._last_col)].width = _col_units(PAGE_W - FRAME[2])
        self.add_row(BOTTOM_MARGIN_H)
        last_row = len(self._rows)
        self.ws.print_area = f"A1:{get_column_letter(self._last_col)}{last_row}"
        self.ws.page_setup.orientation = "landscape"
        self.ws.page_setup.paperSize = 9  # A4
        self.ws.page_setup.fitToWidth = 1
        self.ws.page_setup.fitToHeight = 1
        self.ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        self.ws.page_margins = PageMargins(
            left=FRAME[0] / 25.4, right=(PAGE_W - FRAME[2]) / 25.4,
            top=FRAME[1] / 25.4, bottom=(PAGE_H - FRAME[3]) / 25.4,
            header=0, footer=0,
        )

    # -- coordinates

    def _c(self, x: float) -> int:
        """Boundary x (mm) → first column index covering [x, x+GRID_MM). Column A is the margin."""
        return 2 + int(x - FRAME[0]) // GRID_MM

    def _row_at(self, y: float) -> int:
        for y0, y1, idx in self._rows:
            if y0 <= y < y1:
                return idx
        raise ValueError(f"y={y} is not inside any row")

    def _row_end(self, y: float) -> int:
        for y0, y1, idx in self._rows:
            if y0 < y <= y1:
                return idx
        raise ValueError(f"y={y} is not inside any row")

    # -- drawing

    def _side(self, row: int, col: int, **sides: Side) -> None:
        cell = self.ws.cell(row=row, column=col)
        border = cell.border
        merged = {
            "left": sides.get("left", border.left),
            "right": sides.get("right", border.right),
            "top": sides.get("top", border.top),
            "bottom": sides.get("bottom", border.bottom),
        }
        cell.border = Border(**merged)

    def rect(self, x0: float, y0: float, x1: float, y1: float) -> tuple[int, int, int, int]:
        """Draw a rectangle border; returns (row0, col0, row1, col1)."""
        r0, r1 = self._row_at(y0), self._row_end(y1)
        c0, c1 = self._c(x0), self._c(x1) - 1
        for col in range(c0, c1 + 1):
            self._side(r0, col, top=SIDE)
            self._side(r1, col, bottom=SIDE)
        for row in range(r0, r1 + 1):
            self._side(row, c0, left=SIDE)
            self._side(row, c1, right=SIDE)
        return r0, c0, r1, c1

    def put(
        self,
        x0: float, y0: float, x1: float, y1: float,
        value: str | int | None = None,
        font: Font | None = None,
        align: Alignment | None = None,
    ) -> str:
        """Merge a zone, set its (anchor) value, font and alignment; return the anchor ref."""
        r0, c0, r1, c1 = self.rect(x0, y0, x1, y1)
        if (r1, c1) != (r0, c0):
            self.ws.merge_cells(start_row=r0, start_column=c0, end_row=r1, end_column=c1)
        anchor = self.ws.cell(row=r0, column=c0)
        if value is not None:
            anchor.value = value
        if font is not None:
            anchor.font = font
        if align is not None:
            anchor.alignment = align
        return f"{get_column_letter(c0)}{r0}"

    def frame(self) -> None:
        self.rect(FRAME[0], FRAME[1], FRAME[2], FRAME[3])


# --- форма 1 -----------------------------------------------------------------


def build_form1(wb: Workbook, n_op_rows: int, n_content: int) -> SheetLayout:
    """Build форма 1 (первый или заглавный лист) into a new worksheet."""
    ws = wb.create_sheet("Форма 1")
    sh = _Sheet(ws, "Форма 1")
    sh.add_row(FRAME[1])  # top margin
    sh.add_row(HEADER[1] - 10)  # шапка values (10 mm)
    sh.add_row(5)  # шапка labels
    sh.add_row(TABLE_HEADER[1] - HEADER[1])  # таблица header (15 mm)
    for _ in range(n_op_rows):
        sh.add_row(TABLE_ROW_H)

    layout_cells: dict[str, str] = {}

    # шапка изделия
    layout_cells["product_name"] = sh.put(
        FRAME[0], HEADER[0], HEADER_SPLIT_X, HEADER[0] + 10,
        font=FONT_VALUE, align=ALIGN_CENTER,
    )
    sh.put(FRAME[0], HEADER[0] + 10, HEADER_SPLIT_X, HEADER[1],
           value="Наименование изделия", font=FONT_HEADER_LABEL, align=ALIGN_CENTER)
    layout_cells["product_designation"] = sh.put(
        HEADER_SPLIT_X, HEADER[0], FRAME[2], HEADER[0] + 10,
        font=FONT_VALUE, align=ALIGN_CENTER,
    )
    sh.put(HEADER_SPLIT_X, HEADER[0] + 10, FRAME[2], HEADER[1],
           value="Обозначение изделия", font=FONT_HEADER_LABEL, align=ALIGN_CENTER)

    # основная таблица: header cells + «Номер операции» body cells
    for i, label in enumerate(TABLE_HEADERS):
        x0, x1 = TABLE_COL_X[i], TABLE_COL_X[i + 1]
        sh.put(x0, TABLE_HEADER[0], x1, TABLE_HEADER[1], value=label, font=FONT_LABEL, align=ALIGN_CENTER)
    table_number_cells = []
    for r in range(n_op_rows):
        y0 = TABLE_HEADER[1] + r * TABLE_ROW_H
        table_number_cells.append(sh.put(
            NUMBER_COL[0], y0, NUMBER_COL[1], y0 + TABLE_ROW_H,
            font=FONT_VALUE, align=ALIGN_CENTER,
        ))

    # зона содержания операции
    content_top = TABLE_HEADER[1] + n_op_rows * TABLE_ROW_H
    if content_top > ON[1]:
        raise ValueError(
            f"{n_op_rows} таблица rows overflow форма 1 (v1 draws all rows on the first sheet); "
            "a card with that many operations needs a template extension"
        )
    n_slots = int((ON[1] - content_top) // CONTENT_ROW_H)
    assert n_slots >= n_content, "template asked to fit more content lines than the zone holds"
    content_cells = []
    for i in range(n_slots):
        y0 = content_top + i * CONTENT_ROW_H
        sh.add_row(CONTENT_ROW_H)
        content_cells.append(sh.put(
            FRAME[0], y0, FRAME[2], y0 + CONTENT_ROW_H,
            font=FONT_VALUE, align=ALIGN_LEFT_TOP,
        ))
    filler = ON[1] - (content_top + n_slots * CONTENT_ROW_H)
    if filler > 0:
        sh.add_row(filler)  # unruled gap above the основная надпись
    for _ in range(11):
        sh.add_row(5)  # основная надпись band (11 × 5 mm = 55 mm)
    sh.finish_grid()
    sh.frame()

    # основная надпись (ГОСТ 3.1103-83, 186×55 на сетке)
    x_r0, x_r1 = ON_SPLIT_X, ON[2]
    # правый блок: обозначение документа | наименование изделия | материал
    on_designation = sh.put(x_r0, ON_RIGHT_SECTIONS[0], x_r1, ON_RIGHT_SECTIONS[1],
                            font=FONT_VALUE, align=ALIGN_CENTER)
    on_name = sh.put(x_r0, ON_RIGHT_SECTIONS[1], x_r1, ON_RIGHT_SECTIONS[2],
                     font=FONT_VALUE, align=ALIGN_CENTER)
    on_material = sh.put(x_r0, ON_RIGHT_SECTIONS[2], x_r1, ON_RIGHT_SECTIONS[3],
                         font=FONT_VALUE, align=ALIGN_CENTER)
    sh.put(x_r0, ON_RIGHT_SECTIONS[3], x_r1, ON_RIGHT_SECTIONS[4],
           value="материал", font=FONT_LABEL, align=ALIGN_CENTER)
    # левый блок: таблица изменений (шапка + пустые строки)
    for i in range(len(ON_CHANGES_COLS) - 1):
        x0, x1 = ON_CHANGES_COLS[i], ON_CHANGES_COLS[i + 1]
        sh.put(x0, ON[1], x1, ON[1] + 5, value=ON_CHANGES_HEADERS[i], font=FONT_LABEL, align=ALIGN_CENTER)
        sh.rect(x0, ON[1] + 5, x1, ON[1] + 30)
    # левый блок: подписи
    for r, sign in enumerate(ON_SIGNS):
        y0 = ON[1] + 30 + r * 5
        for i in range(len(ON_SIGN_COLS) - 1):
            x0, x1 = ON_SIGN_COLS[i], ON_SIGN_COLS[i + 1]
            sh.put(x0, y0, x1, y0 + 5,
                   value=sign if i == 0 else None, font=FONT_LABEL, align=ALIGN_CENTER)

    return SheetLayout(
        title="Форма 1",
        product_name_cell=layout_cells["product_name"],
        product_designation_cell=layout_cells["product_designation"],
        table_number_cells=tuple(table_number_cells),
        on_designation_cell=on_designation,
        on_name_cell=on_name,
        on_material_cell=on_material,
        content_cells=tuple(content_cells),
        sheet_no_cell=None,
        sheets_total_cell=None,
    )


# --- форма 1а ----------------------------------------------------------------


def build_form1a(wb: Workbook, sheet_no: int, n_content: int) -> SheetLayout:
    """Build форма 1а (последующий лист) into a new worksheet."""
    title = f"Форма 1а ({sheet_no})"
    sh = _Sheet(wb.create_sheet(title), title)
    sh.add_row(FRAME[1])  # top margin
    sh.add_row(TABLE_HEADER[1] - FRAME[1])  # повтор шапки основной таблицы (15 mm)

    n_slots = int((FORM1A_ON[1] - TABLE_HEADER[1]) // CONTENT_ROW_H)
    assert n_slots >= n_content, "template asked to fit more content lines than the zone holds"
    content_cells = []
    for i in range(n_slots):
        y0 = TABLE_HEADER[1] + i * CONTENT_ROW_H
        sh.add_row(CONTENT_ROW_H)
        content_cells.append(sh.put(
            FRAME[0], y0, FRAME[2], y0 + CONTENT_ROW_H,
            font=FONT_VALUE, align=ALIGN_LEFT_TOP,
        ))
    filler = FORM1A_ON[1] - (TABLE_HEADER[1] + n_slots * CONTENT_ROW_H)
    if filler > 0:
        sh.add_row(filler)  # unruled gap above the малая основная надпись
    for _ in range(3):
        sh.add_row(5)  # малая основная надпись band (3 × 5 mm = 15 mm)
    sh.finish_grid()
    sh.frame()

    for i, label in enumerate(TABLE_HEADERS):
        x0, x1 = TABLE_COL_X[i], TABLE_COL_X[i + 1]
        sh.put(x0, FRAME[1], x1, TABLE_HEADER[1], value=label, font=FONT_LABEL, align=ALIGN_CENTER)

    # малая основная надпись (форма 1а ГОСТ 3.1103-83): изменения | обозначение | Лист | Листов
    for i in range(len(ON_CHANGES_COLS) - 1):
        x0, x1 = ON_CHANGES_COLS[i], ON_CHANGES_COLS[i + 1]
        sh.put(x0, FORM1A_ON[1], x1, FORM1A_ON[3],
               value=ON_CHANGES_HEADERS[i], font=FONT_LABEL,
               align=Alignment(horizontal="center", vertical="top", wrap_text=True))
    sh.put(FORM1A_DESIGNATION_X[0], FORM1A_ON[1], FORM1A_DESIGNATION_X[1], FORM1A_ON[3],
           font=FONT_VALUE, align=ALIGN_CENTER)
    sheet_no_cell = sh.put(FORM1A_SHEET_X[0], FORM1A_ON[1], FORM1A_SHEET_X[1], FORM1A_ON[1] + 10,
                           font=FONT_VALUE, align=ALIGN_CENTER)
    sh.put(FORM1A_SHEET_X[0], FORM1A_ON[1] + 10, FORM1A_SHEET_X[1], FORM1A_ON[3],
           value="Лист", font=FONT_LABEL, align=ALIGN_CENTER)
    sheets_total_cell = sh.put(FORM1A_SHEETS_X[0], FORM1A_ON[1], FORM1A_SHEETS_X[1], FORM1A_ON[1] + 10,
                               font=FONT_VALUE, align=ALIGN_CENTER)
    sh.put(FORM1A_SHEETS_X[0], FORM1A_ON[1] + 10, FORM1A_SHEETS_X[1], FORM1A_ON[3],
           value="Листов", font=FONT_LABEL, align=ALIGN_CENTER)

    return SheetLayout(
        title=title,
        product_name_cell=None,
        product_designation_cell=None,
        table_number_cells=(),
        on_designation_cell=None,
        on_name_cell=None,
        on_material_cell=None,
        content_cells=tuple(content_cells),
        sheet_no_cell=sheet_no_cell,
        sheets_total_cell=sheets_total_cell,
    )


# --- document assembly -------------------------------------------------------


def build_document(wb: Workbook, n_op_rows: int, n_content_lines: int) -> FormLayout:
    """Build форма 1 plus as many форма 1а sheets as the content needs.

    Pagination is pure layout: content lines fill the зона содержания slot by
    slot and overflow onto форма 1а sheets. Sheet counts («Лист»/«Листов») are
    layout facts and are filled here.
    """
    assert n_content_lines >= 1, "a contract always yields at least the process line"
    sheets: list[SheetLayout] = []

    cap1 = form1_content_capacity(n_op_rows)
    first = min(n_content_lines, cap1)
    sheets.append(build_form1(wb, n_op_rows, first))
    remaining = n_content_lines - first

    sheet_no = 2
    while remaining > 0:
        take = min(remaining, FORM1A_CONTENT_CAPACITY)
        sheets.append(build_form1a(wb, sheet_no, take))
        remaining -= take
        sheet_no += 1

    total = len(sheets)
    for s in sheets:
        if s.sheet_no_cell is not None:
            no = int(s.title.rsplit("(", 1)[1].rstrip(")"))
            wb[s.title][s.sheet_no_cell] = no
            wb[s.title][s.sheets_total_cell] = total

    return FormLayout(sheets=tuple(sheets))
