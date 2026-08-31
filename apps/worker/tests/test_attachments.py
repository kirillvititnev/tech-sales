from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook
from pypdf import PdfWriter

from apps.worker.attachments import (
    MAX_BYTES,
    extract_price_list_text,
    is_price_list_attachment,
    message_price_texts,
)
from apps.worker.parser import parse_price_text


def _xlsx_bytes(rows: list[list[object]]) -> bytes:
    book = Workbook()
    sheet = book.active
    for row in rows:
        sheet.append(row)
    buf = BytesIO()
    book.save(buf)
    return buf.getvalue()


def test_xlsx_extract_feeds_parser() -> None:
    data = _xlsx_bytes(
        [
            ["iPhone 16 128GB Black", 61200],
            ["AirPods 4", 9600],
        ]
    )
    text = extract_price_list_text(data, "price.xlsx")
    lines = parse_price_text(text)
    prices = {line.price for line in lines}
    assert Decimal("61200") in prices
    assert Decimal("9600") in prices
    assert any("iPhone 16" in line.title for line in lines)


def test_oversize_and_macro_ext_are_empty() -> None:
    assert extract_price_list_text(b"x" * (MAX_BYTES + 1), "price.xlsx") == ""
    assert extract_price_list_text(b"not-a-workbook", "macro.xlsm") == ""
    assert not is_price_list_attachment("macro.xlsm")
    assert is_price_list_attachment("price.xlsx")
    assert is_price_list_attachment("list.PDF")


def test_encrypted_pdf_skipped() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt("secret")
    buf = BytesIO()
    writer.write(buf)
    assert extract_price_list_text(buf.getvalue(), "secret.pdf") == ""


@pytest.mark.asyncio
async def test_message_price_texts_caption_then_xlsx() -> None:
    class Attr:
        file_name = "price.xlsx"

    class Doc:
        attributes = [Attr()]

    async def download() -> bytes:
        return _xlsx_bytes([["Galaxy S23 128GB Black", 42800]])

    blobs = await message_price_texts(
        caption="  шапка канала  ",
        document=Doc(),
        size=2048,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download=download,
    )
    assert blobs[0] == "шапка канала"
    assert len(blobs) == 2
    lines = parse_price_text(blobs[1])
    assert any(line.price == Decimal("42800") for line in lines)


@pytest.mark.asyncio
async def test_message_price_texts_skips_oversize_download() -> None:
    called = False

    async def download() -> bytes:
        nonlocal called
        called = True
        return b"x"

    class Attr:
        file_name = "price.xlsx"

    class Doc:
        attributes = [Attr()]

    blobs = await message_price_texts(
        caption="only caption",
        document=Doc(),
        size=MAX_BYTES + 1,
        mime=None,
        download=download,
    )
    assert blobs == ["only caption"]
    assert called is False
