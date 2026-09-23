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
  ``<!-- slide-chart -->``    the NEXT table becomes a stacked bar drawn from rectangles
  ``<!-- slide-table -->``    the NEXT table becomes a real, editable PowerPoint table
  ``<!-- slide-columns -->``  the NEXT 2-column table becomes two side-by-side text boxes;
                              row 1 holds the two headings, later rows the lines under them,
                              and a blank cell is simply skipped so the halves may differ
  ``**Chart: …** — `path```   an image to place (kept for decks that still want a picture)
  ``*Say:* …``                the presenter's words -> SPEAKER NOTES, never the slide
  ``[ … ]``                   a note to ourselves -> dropped entirely
  a table with no marker      appended to the notes rather than shown

⚠️ **Everything on a slide must be editable in GOOGLE SLIDES, not just in PowerPoint.**
Version 1 placed the coverage bar as a PNG and the reviewer could not edit the numbers.
Version 3 "fixed" that with a real PowerPoint chart object — which did not reach the problem
at all: she works in Google Slides, and Slides cannot open an embedded OOXML chart. It passes
the bytes through untouched (verified: the chart part came back byte-identical, sha e4b438fd)
and shows a rendered preview in its place. That preview is what she meant by blurry, and it
is why the same slide was un-editable in both rounds. So the bar is now ordinary rectangles
and text boxes, which Slides imports as native objects. Tables round-trip fine — hers did.

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
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

INK = RGBColor(0x1F, 0x4E, 0x79)          # headings and the "complete" series
BODY = RGBColor(0x26, 0x26, 0x26)
QUIET = RGBColor(0x70, 0x70, 0x70)
RULE = RGBColor(0xD9, 0xD9, 0xD9)
#: One colour per bar segment, in the order the marked table lists them.
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
                           "columns": None, "lead": None, "notes": "", "dropped": []}
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
            elif "slide-columns" in stripped:
                pending = "columns"
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
            if pending in ("chart", "table", "columns"):
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
    """A stacked bar drawn from PLAIN RECTANGLES. ``rows`` is [[header...], [label, value], ...].

    Not a chart object, on purpose — see the note at the top of this file. Rectangles and text
    boxes survive a Google Slides round trip as editable native shapes; a chart object does not.
    """
    body = [r for r in rows[1:] if len(r) >= 2 and r[1].replace(",", "").strip().isdigit()]
    values = [int(r[1].replace(",", "")) for r in body]
    total = sum(values)

    bar_w, bar_h = int(SLIDE_W - 2 * MARGIN), Inches(0.92)
    # Cumulative ROUNDED edges, so segment i+1 begins exactly where segment i ends. Widths
    # rounded independently leave sub-EMU gaps, and Slides draws a gap as a visible seam.
    edges, running = [0], 0
    for v in values:
        running += v
        edges.append(int(round(bar_w * running / total)))

    label_top = Emu(int(top) + int(bar_h) + int(Inches(0.06)))
    for i, value in enumerate(values):
        left, width = Emu(int(MARGIN) + edges[i]), Emu(edges[i + 1] - edges[i])
        colour = SERIES_INK[i % len(SERIES_INK)]

        seg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, bar_h)
        seg.fill.solid()
        seg.fill.fore_color.rgb = colour
        seg.line.fill.background()          # no theme outline
        seg.shadow.inherit = False          # no theme shadow
        seg.text_frame.word_wrap = False
        seg.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        _write(seg.text_frame, "**{:,}**".format(value), Pt(14),
               RGBColor(0xFF, 0xFF, 0xFF), space_after=Pt(0))
        seg.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

        # The name sits UNDER its own segment, in its own colour: the reader never has to
        # match a swatch in a legend to a band in the bar.
        cap = slide.shapes.add_textbox(left, label_top, width, Inches(0.42))
        cap.text_frame.word_wrap = True
        _write(cap.text_frame, "**{}**".format(body[i][0]), Pt(10), colour, space_after=Pt(0))

    return Emu(int(label_top) + int(Inches(0.42))) + Inches(0.10)


def _add_columns(slide, rows, top):
    """Two side-by-side text boxes. ``rows[0]`` holds the headings, the rest the lines.

    Text boxes, not a table: the other presenter edits her half in Google Slides, where a
    text box arrives native and editable. A blank cell is skipped rather than drawn, so the
    two halves need not be the same length.
    """
    gutter = Inches(0.55)
    col_w = Emu(int((SLIDE_W - 2 * MARGIN - gutter) / 2))
    height = SLIDE_H - top - Inches(0.35)

    # A hairline between the halves, so the eye splits the slide without being told.
    rule = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Emu(int(MARGIN) + int(col_w) + int(gutter) // 2 - 6350),
        top, Emu(12700), Emu(int(height) - int(Inches(0.2))))
    rule.fill.solid()
    rule.fill.fore_color.rgb = RULE
    rule.line.fill.background()
    rule.shadow.inherit = False

    for col in (0, 1):
        left = Emu(int(MARGIN) + col * (int(col_w) + int(gutter)))
        box = slide.shapes.add_textbox(left, top, col_w, height)
        box.text_frame.word_wrap = True
        for r_i, row in enumerate(rows):
            cell = row[col].strip() if col < len(row) else ""
            if not cell:
                continue
            if r_i == 0:
                _write(box.text_frame, cell, Pt(17), INK, bold_default=True,
                       space_after=Pt(7))
            else:
                _write(box.text_frame, cell, Pt(12), BODY, space_after=Pt(8))
    return Emu(int(top) + int(height))


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
        if spec.get("columns"):
            top = _add_columns(slide, spec["columns"], top)
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


#: How the coarse bar on the coverage slide groups the per-category statuses in the table
#: beside it. Declared rather than inferred, so renaming either one fails loudly instead of
#: silently splitting the two slides -- which is exactly what happened between v4 and v5.
#:
#: WHAT THIS CANNOT SEE, measured by mutation rather than assumed: a category moving between
#: two statuses that land in the SAME segment. "Scoped, not started" and "Out of scope" both
#: roll into "Not yet built", so moving a row between them leaves the bar correct and the
#: check silent. That is sound for the bar, but any PROSE quoting one of those two subtotals
#: is unguarded -- slide 7's note says sixteen for futures and options. A four-segment bar
#: would catch it; it was rejected because the fourth segment is one security in 2,260 and
#: renders as a hairline. The run prints the subtotals so the split is at least visible.
COVERAGE_GROUPS = {
    "Complete": ("Complete",),
    "Engine built \u2014 next": ("Engine built \u2014 next",),
    "Not yet built": ("Scoped, not started", "Out of scope"),
}


def verify(out, slides, draft=False):
    """Read the written deck back and cross-check the bar against the table.

    Reads the FILE, not the in-memory model: the question is what ships, and a bar drawn as
    shapes has no series to interrogate. Raises on any disagreement.
    """
    from pptx import Presentation

    prs = Presentation(str(out))
    problems, notes, blanks = [], [], []

    # 1. Nothing on any slide may be a chart object or a picture. Google Slides cannot edit
    #    either: it shows a rendered preview, which is how the bar came to be called blurry.
    for i, slide in enumerate(prs.slides, 1):
        for sh in slide.shapes:
            if getattr(sh, "has_chart", False):
                problems.append("slide %d holds a CHART OBJECT; Slides cannot edit one" % i)
            if sh.shape_type is not None and "PICTURE" in str(sh.shape_type):
                problems.append("slide %d holds a PICTURE; it will not be editable" % i)

    # A bio half written for somebody else to complete carries <<LIKE THIS>> markers.
    # One left in by accident goes up on a screen in front of the investors, so the deck
    # is refused rather than shipped. Chosen over [SQUARE BRACKETS] because the parser
    # already treats a bracketed line as a note to ourselves and silently drops it.
    for i, slide in enumerate(prs.slides, 1):
        for sh in slide.shapes:
            if sh.has_text_frame and "<<" in sh.text_frame.text:
                for frag in sh.text_frame.text.split("<<")[1:]:
                    blanks.append("slide %d: <<%s"
                                  % (i, frag.split(">>")[0][:62] + ">>"))

    chart_rows = next((s["chart"] for s in slides if s.get("chart")), None)
    table_rows = next((s["table"] for s in slides if s.get("table")), None)
    if not chart_rows or not table_rows:
        return notes, problems, blanks

    def num(x):
        return int(x.replace(",", "").replace("*", "").strip())

    bar = {r[0]: num(r[1]) for r in chart_rows[1:]
           if len(r) >= 2 and r[1].replace(",", "").strip().isdigit()}

    # 2. Every status in the table must belong to exactly one bar segment, and vice versa.
    by_status = {}
    total_row = None
    for r in table_rows[1:]:
        if len(r) >= 5 and r[3].replace(",", "").replace("*", "").strip().isdigit():
            if "Total" in r[1]:
                total_row = num(r[3])
            else:
                by_status[r[4]] = by_status.get(r[4], 0) + num(r[3])
    if set(bar) != set(COVERAGE_GROUPS):
        problems.append("bar segments %s do not match the declared grouping %s"
                        % (sorted(bar), sorted(COVERAGE_GROUPS)))
    claimed = [s for g in COVERAGE_GROUPS.values() for s in g]
    for status in by_status:
        if status not in claimed:
            problems.append('table status "%s" belongs to no bar segment' % status)

    # 3. Each segment must equal the categories it claims to cover.
    for label, statuses in COVERAGE_GROUPS.items():
        want = sum(by_status.get(s, 0) for s in statuses)
        got = bar.get(label)
        if got != want:
            problems.append('"%s": bar says %s, the table rows under it sum to %s'
                            % (label, got, want))
        else:
            if len(statuses) > 1:
                notes.append("   ^ a row moving between those two is INVISIBLE here; "
                             "check any prose quoting either subtotal")
            notes.append('"%s" %s = %s' % (label, got, " + ".join(
                "%s %d" % (s, by_status[s]) for s in statuses if s in by_status)))

    if total_row is not None and sum(bar.values()) != total_row:
        problems.append("the bar sums to %d, the table total says %d"
                        % (sum(bar.values()), total_row))
    else:
        notes.append("bar total = table total = %s" % format(sum(bar.values()), ","))

    # 4. The segments must tile: each begins exactly where the last ended, and together they
    #    span the full bar. A sub-EMU gap renders in Slides as a visible seam.
    slide6 = next((s for s in prs.slides
                   if any(sh.has_text_frame and sh.text_frame.text.strip()
                          == format(list(bar.values())[0], ",") for sh in s.shapes)), None)
    if slide6 is not None:
        segs = sorted((sh for sh in slide6.shapes
                       if sh.has_text_frame
                       and sh.text_frame.text.strip().replace(",", "").isdigit()
                       and sh.height > Inches(0.5)), key=lambda s: s.left)
        if len(segs) != len(bar):
            problems.append("found %d bar rectangles, expected %d" % (len(segs), len(bar)))
        for a, b in zip(segs, segs[1:]):
            if int(a.left) + int(a.width) != int(b.left):
                problems.append("a %d EMU seam between two segments"
                                % (int(b.left) - int(a.left) - int(a.width)))
        if segs:
            span = int(segs[-1].left) + int(segs[-1].width) - int(segs[0].left)
            if span != int(SLIDE_W - 2 * MARGIN):
                problems.append("the segments span %d EMU, the bar is %d"
                                % (span, int(SLIDE_W - 2 * MARGIN)))
            else:
                notes.append("%d segments tile the bar exactly, no seams" % len(segs))
    return notes, problems, blanks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--draft", action="store_true",
                    help="allow unfilled <<placeholders>>, for circulating to be completed")
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

    notes, problems, blanks = verify(out, slides, draft=args.draft)
    for note in notes:
        print("  ok   " + note)
    if problems:
        print("\n  !! THE COVERAGE BAR AND THE CATEGORY TABLE DISAGREE:")
        for p in problems:
            print("     " + p)
    if blanks:
        print("\n  %s %d PLACEHOLDER%s STILL UNFILLED:"
              % ("--" if args.draft else "!!", len(blanks), "" if len(blanks) == 1 else "S"))
        for b in blanks:
            print("     " + b)
        print("     %s" % ("this is a DRAFT -- fine to circulate so they can be filled in"
                           if args.draft
                           else "refusing to ship; re-run with --draft to circulate it"))
    if problems or (blanks and not args.draft):
        # Move the bad file aside rather than leave it under the name somebody will grab.
        rejected = out.with_suffix(".REJECTED.pptx")
        rejected.unlink(missing_ok=True)
        out.rename(rejected)
        print("\n     moved to %s" % rejected.name)
        raise SystemExit(1)

    for i, spec in enumerate(slides, 1):
        extras = "".join([
            "  +chart" if spec.get("chart") else "",
            "  +columns" if spec.get("columns") else "",
            f"  +table({len(spec['table'])}r)" if spec.get("table") else "",
            "  +lead" if spec.get("lead") else "",
            "  +image" if spec.get("image") else "",
            "  +notes" if spec["notes"] else "  NO NOTES",
        ])
        print(f"  {i}. {spec['title'][:46]:46s} {len(spec['bullets'])}b{extras}")


if __name__ == "__main__":
    main()
