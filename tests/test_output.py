"""HTML rendering and CLI tests."""

import syhwp
from syhwp.__main__ import main


def test_html_document(sample_hwpx):
    h = syhwp.extract_html(sample_hwpx)
    assert h.startswith("<!doctype html>")
    assert "<table>" in h and "<td>구분</td>" in h
    assert "충북 AI" in h


def test_html_escapes():
    from syhwp import Document, Paragraph

    doc = Document(format="hwp5", blocks=[Paragraph("a < b & c > d")])
    assert "a &lt; b &amp; c &gt; d" in doc.html


def test_cli_markdown(sample_hwpx, capsys):
    rc = main([sample_hwpx])
    assert rc == 0
    out = capsys.readouterr().out
    assert "| 구분 | 내용 |" in out


def test_cli_text(sample_hwpx, capsys):
    rc = main([sample_hwpx, "--text"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "구분" in out and "|" not in out


def test_cli_error_on_bad_file(tmp_path, capsys):
    p = tmp_path / "x.txt"
    p.write_bytes(b"not a document")
    rc = main([str(p)])
    assert rc == 1
    assert "syhwp:" in capsys.readouterr().err
