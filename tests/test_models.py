"""Model unit tests for block types and document metadata."""

from syhwp import Cell, Document, Equation, Image, Paragraph, Table


def test_equation_text():
    assert Equation("a over b").text == "[수식: a over b]"
    assert Equation("").text == "[수식]"
    assert Equation("x").to_markdown() == "[수식: x]"


def test_image_text():
    assert Image().text == "[그림]"
    assert Image(alt="사진").text == "[사진]"


def test_document_version_and_filters():
    doc = Document(
        format="hwp5",
        version="5.1.0.1",
        blocks=[
            Paragraph("hi"),
            Equation("e=mc^2"),
            Image(),
            Table(n_rows=1, n_cols=1, cells=[Cell(0, 0, "x")]),
        ],
    )
    assert doc.version == "5.1.0.1"
    assert len(doc.paragraphs) == 1
    assert len(doc.tables) == 1
    assert len(doc.equations) == 1


def test_document_markdown_includes_blocks():
    doc = Document(format="hwp5", blocks=[Paragraph("intro"), Equation("a+b")])
    md = doc.markdown
    assert "intro" in md and "[수식: a+b]" in md
