"""Corpus smoke test — runs syhwp over any real documents placed in tests/data/
(gitignored). Skips when the corpus is absent so CI stays green without shipping
copyrighted files."""

import glob
import os

import pytest

import syhwp
from syhwp import SyhwpError

_DATA = os.path.join(os.path.dirname(__file__), "data")
_FILES = sorted(
    glob.glob(os.path.join(_DATA, "*.hwp")) + glob.glob(os.path.join(_DATA, "*.hwpx"))
)


@pytest.mark.skipif(not _FILES, reason="no local corpus in tests/data (gitignored)")
@pytest.mark.parametrize("path", _FILES, ids=[os.path.basename(f) for f in _FILES])
def test_corpus_open_and_render(path):
    try:
        doc = syhwp.open(path)
    except SyhwpError:
        return  # encrypted / distribution / corrupt are acceptable outcomes
    assert doc.format in ("hwp5", "hwpx")
    # rendering must not raise
    assert isinstance(doc.text, str)
    assert isinstance(doc.markdown, str)
