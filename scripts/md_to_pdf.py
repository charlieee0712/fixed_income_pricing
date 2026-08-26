"""Render a Markdown document to a client-ready PDF, on this machine alone.

    python scripts/md_to_pdf.py --input docs/report.md --output out/report.pdf

Replaces the old two-machine dance (pandoc on server 47 for the HTML, Edge headless
locally for the PDF): the local Python has ``markdown``, and Edge is a Windows install, so
one command now does both. Keep the intermediate HTML with ``--keep-html`` when a layout
needs inspecting.

Three Edge flags are load-bearing and were each learned the hard way:
  --headless=new       current Edge builds ignore the bare --headless: the browser starts
                       a windowed path instead, emits libpng warnings, and writes NO PDF
                       while still exiting successfully.
  --user-data-dir      a throwaway profile. Without it, an already-running Edge answers
                       the request and the PDF is silently NOT written.
  --no-pdf-header-footer  suppresses the date/URL furniture. The older
                       --print-to-pdf-no-header does nothing in current builds.

Note the shared failure mode: every one of these fails by producing nothing rather than by
erroring, which is why the caller checks for the file itself.
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time

EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.55; color: #1a1a1a; max-width: 100%; }
h1 { font-size: 19pt; margin: 0 0 2pt 0; border-bottom: 2px solid #1a1a1a;
     padding-bottom: 6pt; }
h2 { font-size: 13.5pt; margin: 20pt 0 6pt 0; color: #12305c; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt 0; color: #12305c; }
p, li { margin: 0 0 7pt 0; }
ul, ol { margin: 0 0 8pt 0; padding-left: 20pt; }
strong { color: #000; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9.5pt;
       background: #f2f4f7; padding: 1pt 3pt; border-radius: 2pt; }
pre { background: #f7f8fa; border: 1px solid #dde1e7; border-radius: 3pt;
      padding: 8pt 10pt; overflow-x: auto; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 9pt; line-height: 1.4; }
table { border-collapse: collapse; margin: 8pt 0 12pt 0; width: 100%;
        page-break-inside: avoid; font-size: 10pt; }
th, td { border: 1px solid #c9cfd8; padding: 4pt 7pt; text-align: left;
         vertical-align: top; }
th { background: #eef1f5; font-weight: 600; }
blockquote { border-left: 3px solid #b8c2d0; margin: 8pt 0; padding: 2pt 0 2pt 12pt;
             color: #333; }
hr { border: none; border-top: 1px solid #d5dae1; margin: 16pt 0; }
h2, h3 { page-break-after: avoid; }
"""


def find_browser(explicit=None) -> str:
    """Locate the Edge executable used to print the PDF.

    Inputs
    ------
    1. explicit : str | None — a path supplied on the command line, tried first.

    Returns: str — path to the browser. Raises ``SystemExit`` with a readable message
    when none of the known locations exists.
    """
    for candidate in ([explicit] if explicit else []) + list(EDGE_CANDIDATES):
        if candidate and os.path.exists(candidate):
            return candidate
    raise SystemExit("Edge was not found; pass --browser with the path to msedge.exe")


def render_html(markdown_text: str, title: str) -> str:
    """Convert Markdown to a standalone, styled HTML document.

    Inputs
    ------
    1. markdown_text : str — the document source.
    2. title         : str — the HTML title (shown only in metadata; the PDF has no
       header furniture).

    Returns: str — a complete HTML document with the stylesheet inlined.
    """
    import markdown

    body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
    )
    return (f"<!DOCTYPE html>\n<html><head><meta charset='utf-8'>"
            f"<title>{title}</title><style>{CSS}</style></head>"
            f"<body>\n{body}\n</body></html>\n")


def print_pdf(html_path: str, pdf_path: str, browser: str, timeout: int = 120) -> None:
    """Print an HTML file to PDF with headless Edge.

    Inputs
    ------
    1. html_path : str — the source HTML.
    2. pdf_path  : str — the PDF to write (overwritten if present).
    3. browser   : str — path to msedge.exe.
    4. timeout   : int — seconds to wait for the browser.

    Returns: None. Raises ``SystemExit`` if the browser produced no file.
    """
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--user-data-dir={profile}",
             f"--print-to-pdf={os.path.abspath(pdf_path)}",
             f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}"],
            timeout=timeout, capture_output=True,
        )
        for _ in range(40):                      # the flag returns before the flush
            if os.path.exists(pdf_path):
                break
            time.sleep(0.25)
    if not os.path.exists(pdf_path):
        raise SystemExit(f"no PDF was produced at {pdf_path}; run with --keep-html and "
                         f"open the HTML to see what the browser was given")


def main(argv=None) -> int:
    """Entry point: read Markdown, render HTML, print PDF, report the size."""
    parser = argparse.ArgumentParser(description="Markdown -> styled PDF (local Edge).")
    parser.add_argument("--input", required=True, help="source .md file")
    parser.add_argument("--output", required=True, help=".pdf file to write")
    parser.add_argument("--title", default=None, help="document title (default: filename)")
    parser.add_argument("--browser", default=None, help="path to msedge.exe")
    parser.add_argument("--keep-html", action="store_true", help="keep the intermediate HTML")
    args = parser.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as handle:
        text = handle.read()

    title = args.title or os.path.splitext(os.path.basename(args.input))[0]
    html_path = os.path.splitext(args.output)[0] + ".html"
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(render_html(text, title))

    print_pdf(html_path, args.output, find_browser(args.browser))
    if not args.keep_html:
        os.remove(html_path)
    print(f"wrote {args.output} ({os.path.getsize(args.output):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
