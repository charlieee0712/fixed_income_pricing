"""Build the investor deck (.pptx) FROM the markdown script.

    python scripts/make_investor_deck.py
        --input  docs/ryse_investor_update_v3_2026-09-21.md
        --output "docs/Ryse Presentation v3.pptx"

⭐ The markdown is the single source. Keeping a hand-edited .pptx beside a hand-edited
script is the two-owners-one-decision shape this project keeps closing: the two drift, and
the one that gets presented is whichever the presenter happened to open. Edit the markdown,
re-run this, and the deck follows.

What the parser takes from the script:

  ``## Slide N — Title``      a new slide, titled with whatever follows the dash
  ``- bullet``                a bullet, wrapped lines joined; ``**bold**`` becomes bold runs
  ``<!-- slide-chart -->``    the NEXT table becomes a real, editable PowerPoint chart
  ``<!-- slide-table -->``    the NEXT table becomes a real, editable PowerPoint table
  ``**Chart: …** — `path```   an image to place (kept for decks that still want a picture)
  ``*Say:* …``                the presenter's words -> SPEAKER NOTES, never the slide
  ``[ … ]``                   a note to ourselves -> dropped entirely
  a table with no marker      appended to the notes rather than shown

⚠️ **Native, not a picture.** An earlier version placed the coverage chart as a PNG and a
reviewer could not edit the numbers on it — a deck somebody else has to finish is a deck
they have to be able to change. Marked tables and charts are now real PowerPoint objects.

Slide size is **10 x 5.625 in**, matching the deck this one continues, so slides can be
moved between them without re-scaling.

Needs ``python-pptx`` (``pip install python-pptx``). Deliberately NOT in requirements.txt —
that file lists what the pricing system needs to run, and document tooling is not that;
``scripts/md_to_pdf.py`` treats ``markdown`` the same way.
"""
from __future__ import annotations

import argparse
import pathlib
import re

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

INK = RGBColor(0x1F, 0x4E, 0x79)          # headings and the "complete" series
BODY = RGBColor(0x26, 0x26, 0x26)
QUIET = RGBColor(0x70, 0x70, 0x70)
RULE = RGBColor(0xD9, 0xD9, 0xD9)
#: One colour per chart series, in the order the marked table lists them.
SERIES_INK = [RGBColor(0x1F, 0x4E, 0x79), RGBColor(0xD6, 0x89, 0x10),
              RGBColor(0x9E, 0x9E, 0x9E), RGBColor(0xD9, 0xD9, 0xD9)]

#: Printed when a source line matched no rule. Silence here would mean content in the
#: script that never reaches the deck, which is how a lead line went missing once.
NOT_PLACED_BANNER = (
    "\n  !! THESE SOURCE LINES REACHED NO RULE and are NOT in the deck:")

SLIDE_W, SLIDE_H = Inches(10.0), Inches(5.625)
MARGIN = Inches(0.55)


def parse(markdown_text):
    """Turn the script into ``[{title, bullets, image, chart, table, notes}]``."""
    slides, current = [], None
    note_lines, loose_table, in_note, in_aside = [], [], False, False
    pending = None                      # "chart" | "table" | None, set by an HTML comment
    started = False                     # has the marked table produced a row yet?

    def flush():
        if current is None:
            return
        notes = " ".join(note_lines).strip()
        if loose_table:
            notes = (notes + "\n\nFor reference:\n" + "\n".join(loose_table)).strip()
        current["notes"] = notes
        slides.append(current)

    for raw in markdown_text.splitlines():
        line, stripped = raw.rstrip(), raw.strip()

        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            flush()
            current, note_lines, loose_table = None, [], []
            in_note = in_aside = False
            pending, started = None, False
            if heading.lower().startswith("slide"):
                current = {"title": re.sub(r"^Slide\s*\d+\s*[—-]\s*", "", heading).strip(),
                           "bullets": [], "image": None, "chart": None, "table": None,
                           "lead": None, "notes": "", "dropped": []}
            continue
        if current is None:
            continue

        if in_aside:
            if stripped.endswith("]"):
                in_aside = False
            continue
        if stripped.startswith("["):
            in_aside = not stripped.endswith("]")
            continue

        if stripped.startswith("<!--"):
            if "slide-chart" in stripped:
                pending = "chart"
            elif "slide-table" in stripped:
                pending = "table"
            continue

        if stripped.startswith("*Say:*"):
            in_note = True
            note_lines.append(stripped[len("*Say:*"):].strip())
            continue
        if in_note:
            if stripped:
                note_lines.append(stripped)
            else:
                in_note = False
            continue

        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue                                  # the ---|--- separator row
            if pending in ("chart", "table"):
                if current[pending] is None:
                    current[pending] = []
                current[pending].append(cells)
                started = True
            else:
                loose_table.append("  " + " | ".join(c for c in cells if c))
            continue
        if pending and started and not stripped:
            # A blank line ends a marked table -- but only once it has actually begun.
            # The marker sits on its own line with a blank line after it, so clearing on
            # the FIRST blank would drop every marked table. It did.
            pending, started = None, False
            continue

        m = re.match(r"\*\*Chart:.*?\*\*\s*[—-]\s*`([^`]+)`", stripped)
        if m:
            current["image"] = m.group(1)
            continue
        if stripped.startswith("- "):
            current["bullets"].append(stripped[2:].strip())
            continue
        if stripped and current["bullets"] and raw.startswith("  "):
            current["bullets"][-1] += " " + stripped
            continue
        # A bold standalone line BEFORE any bullet is the slide's LEAD LINE: the point of
        # the slide, said once, with no bullet so it does not read as another item.
        if (stripped.startswith("**") and stripped.endswith("**")
                and not current["bullets"] and current["lead"] is None):
            current["lead"] = stripped
            continue
        # Anything else carrying content reached no rule and would vanish without a word.
        # An earlier version dropped a lead line exactly this way: present in the source,
        # absent from the deck, and nothing said so.
        if stripped and not stripped.startswith(("---", "```", "|", "<!--")):
            current["dropped"].append(stripped)

    flush()
    return slides


def _write(frame, text, size, colour=BODY, bold_default=False, space_after=Pt(9)):
    """Append one paragraph, honouring ``**bold**`` and dropping stray emphasis marks."""
    para = frame.paragraphs[0] if (not frame.text and len(frame.paragraphs) == 1) \
        else frame.add_paragraph()
    para.space_after = space_after
    for i, chunk in enumerate(text.split("**")):
        if not chunk:
            continue
        run = para.add_run()
        run.text = chunk.replace("*", "")
        run.font.size = size
        run.font.bold = bold_default or (i % 2 == 1)
        run.font.color.rgb = colour
    return para


def _add_chart(slide, rows, top):
    """A real, editable stacked bar. ``rows`` is [[header...], [label, value], ...]."""
    body = [r for r in rows[1:] if len(r) >= 2 and r[1].replace(",", "").strip().isdigit()]
    data = CategoryChartData()
    data.categories = [""]
    for label, value in ((r[0], int(r[1].replace(",", ""))) for r in body):
        data.add_series(label, (value,))

    height = Inches(1.5)
    frame = slide.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, MARGIN, top,
                                   SLIDE_W - 2 * MARGIN, height, data)
    chart = frame.chart
    chart.has_title = False
    chart.value_axis.visible = False
    chart.value_axis.has_major_gridlines = False
    chart.category_axis.visible = False
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(10)

    total = sum(int(r[1].replace(",", "")) for r in body)
    for i, plot_series in enumerate(chart.plots[0].series):
        plot_series.format.fill.solid()
        plot_series.format.fill.fore_color.rgb = SERIES_INK[i % len(SERIES_INK)]
        share = int(body[i][1].replace(",", "")) / total
        if share > 0.08:                       # only label a band wide enough to hold text
            plot_series.has_data_labels = True
            labels = plot_series.data_labels
            labels.number_format, labels.number_format_is_linked = '#,##0', False
            labels.font.size = Pt(12)
            labels.font.bold = True
            labels.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    chart.plots[0].gap_width = 40
    chart.plots[0].overlap = 100
    return Emu(int(top) + int(height)) + Inches(0.12)


def _add_table(slide, rows, top):
    """A real, editable table. First row is the header; a ``**Total**`` row is emphasised."""
    n_rows, n_cols = len(rows), max(len(r) for r in rows)
    height = min(Inches(0.235) * n_rows, SLIDE_H - top - Inches(0.2))
    shape = slide.shapes.add_table(n_rows, n_cols, MARGIN, top,
                                   SLIDE_W - 2 * MARGIN, height)
    table = shape.table
    widths = (0.38, 3.05, 1.05, 1.25, 3.17)                # tuned for the category table
    for c in range(n_cols):
        table.columns[c].width = Inches(widths[c] if c < len(widths) else 1.2)

    for r, row in enumerate(rows):
        for c in range(n_cols):
            cell = table.cell(r, c)
            raw = row[c] if c < len(row) else ""
            text = raw.replace("**", "")
            cell.text = text
            para = cell.text_frame.paragraphs[0]
            para.alignment = PP_ALIGN.RIGHT if (c in (0, 2, 3) and r > 0) else PP_ALIGN.LEFT
            for run in para.runs:
                run.font.size = Pt(9.5)
                run.font.bold = (r == 0) or raw.startswith("**")
                run.font.color.rgb = INK if r == 0 else BODY
            cell.margin_top = cell.margin_bottom = Pt(1)
    return Emu(int(top) + int(height)) + Inches(0.15)


def build(slides, out_path, root):
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
    blank = prs.slide_layouts[6]

    for index, spec in enumerate(slides):
        slide = prs.slides.add_slide(blank)
        first = index == 0

        box = slide.shapes.add_textbox(MARGIN, Inches(1.55 if first else 0.34),
                                       SLIDE_W - 2 * MARGIN, Inches(0.8))
        box.text_frame.word_wrap = True
        _write(box.text_frame, spec["title"], Pt(30 if first else 23), INK,
               bold_default=True, space_after=Pt(3))

        top = Inches(2.55) if first else Inches(1.18)
        if spec.get("lead"):
            lead_h = Inches(0.56)
            lead_box = slide.shapes.add_textbox(MARGIN, top, SLIDE_W - 2 * MARGIN, lead_h)
            lead_box.text_frame.word_wrap = True
            _write(lead_box.text_frame, spec["lead"], Pt(16), INK, space_after=Pt(2))
            top = Emu(int(top) + int(lead_h))
        if spec.get("chart"):
            top = _add_chart(slide, spec["chart"], top)
        if spec.get("table"):
            top = _add_table(slide, spec["table"], top)
        if spec["image"]:
            picture = root / spec["image"]
            if picture.exists():
                slide.shapes.add_picture(str(picture), MARGIN, top,
                                         width=SLIDE_W - 2 * MARGIN)
                shape = slide.shapes[-1]
                top = Emu(int(shape.top) + int(shape.height)) + Inches(0.15)

        if spec["bullets"]:
            body = slide.shapes.add_textbox(MARGIN, top, SLIDE_W - 2 * MARGIN,
                                            SLIDE_H - top - Inches(0.2))
            frame = body.text_frame
            frame.word_wrap = True
            for bullet in spec["bullets"]:
                _write(frame, "•  " + bullet, Pt(13 if not first else 13),
                       BODY if not first else QUIET)

        if spec["notes"]:
            slide.notes_slide.notes_text_frame.text = spec["notes"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return len(slides)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    source = pathlib.Path(args.input)
    root = source.resolve().parents[1]
    slides = parse(source.read_text(encoding="utf-8"))
    if not slides:
        raise SystemExit(f"no '## Slide N — …' headings found in {source}")
    out = pathlib.Path(args.output)
    n = build(slides, out, root)
    print(f"wrote {out} ({n} slides, {out.stat().st_size:,} bytes)")
    unplaced = [(i, ln) for i, s in enumerate(slides, 1) for ln in s.get("dropped", [])]
    if unplaced:
        print(NOT_PLACED_BANNER)
        for i, ln in unplaced:
            print("     slide %d: %s" % (i, ln[:88]))

    for i, spec in enumerate(slides, 1):
        extras = "".join([
            "  +chart" if spec.get("chart") else "",
            f"  +table({len(spec['table'])}r)" if spec.get("table") else "",
            "  +lead" if spec.get("lead") else "",
            "  +image" if spec.get("image") else "",
            "  +notes" if spec["notes"] else "  NO NOTES",
        ])
        print(f"  {i}. {spec['title'][:46]:46s} {len(spec['bullets'])}b{extras}")


if __name__ == "__main__":
    main()
