"""Command-line interface: ``python -m syhwp [--text|--markdown|--html] FILE``."""

import argparse
import sys

from . import __version__, extract_html, extract_markdown, extract_text
from .exceptions import SyhwpError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="syhwp",
        description="Extract text/markdown/HTML from Korean HWP 5.x and HWPX files.",
    )
    parser.add_argument("file", help="path to a .hwp or .hwpx document")
    fmt = parser.add_mutually_exclusive_group()
    fmt.add_argument(
        "--text", action="store_const", const="text", dest="fmt", help="plain text"
    )
    fmt.add_argument(
        "--markdown", "--md", action="store_const", const="markdown", dest="fmt",
        help="GFM markdown (default)",
    )
    fmt.add_argument(
        "--html", action="store_const", const="html", dest="fmt", help="HTML document"
    )
    parser.add_argument("--version", action="version", version=f"syhwp {__version__}")
    args = parser.parse_args(argv)

    renderers = {
        "text": extract_text,
        "markdown": extract_markdown,
        "html": extract_html,
    }
    render = renderers[args.fmt or "markdown"]
    try:
        out = render(args.file)
    except SyhwpError as e:
        print(f"syhwp: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"syhwp: cannot read {args.file!r}: {e}", file=sys.stderr)
        return 1

    sys.stdout.write(out)
    if not out.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
