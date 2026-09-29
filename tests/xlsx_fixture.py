"""Tiny OOXML fixture for mapping tests."""

from html import escape
from zipfile import ZipFile


def write_mapping(path, entries):
    rows = [("报表类型", "专属知识包名称"), *entries]
    body = "".join(
        f'<row r="{number}"><c r="A{number}" t="inlineStr"><is><t>{escape(report)}</t></is></c>'
        f'<c r="B{number}" t="inlineStr"><is><t>{escape(filename)}</t></is></c></row>'
        for number, (report, filename) in enumerate(rows, 1)
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml",
                         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                         f"<sheetData>{body}</sheetData></worksheet>")


def write_definition(path, entries):
    rows = [("KPI_CN", "Definition"), *entries]
    body = "".join(
        f'<row r="{number}"><c r="A{number}" t="inlineStr"><is><t>{escape(name)}</t></is></c>'
        f'<c r="E{number}" t="inlineStr"><is><t>{escape(definition)}</t></is></c></row>'
        for number, (name, definition) in enumerate(rows, 1)
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml",
                         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                         f"<sheetData>{body}</sheetData></worksheet>")
