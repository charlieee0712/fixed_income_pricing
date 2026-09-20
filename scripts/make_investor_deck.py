"""Build the investor deck (.pptx) FROM the markdown script.

    python scripts/make_investor_deck.py
        --input  docs/investor_update_2026-09-19.md
        --output docs/investor_update_2026-09-19.pptx

⭐ The markdown is the single source. Keeping a hand-edited .pptx beside a hand-edited
script is the two-owners-one-decision shape this project keeps closing: the two drift, and
the one that gets presented is whichever the presenter happened to open. Edit the markdown,
re-run this, and the deck follows.

What the parser takes from the script:

  ``## Slide N — Title``   a new slide, titled with whatever follows the dash
  ``- bullet``             a bullet, wrapped lines joined; ``**bold**`` becomes bold runs
  ``**Chart: …** — `path```the image to place on that slide
  ``*Say:* …``             the presenter's words -> the slide's SPEAKER NOTES, never the slide
  ``[ … ]``                a note to ourselves -> dropped entirely
  ``| a | b |``            a table -> appended to the notes, not shown (see below)

⚠️ Tables go to the notes on purpose. The one table in this deck restates what its chart
already shows, with a "why" column; on a slide that is duplication read by nobody, and in
the presenter's notes it is exactly what they want when somebody asks.

Needs ``python-pptx`` (``pip install python-pptx``). It is deliberately NOT in
requirements.txt — that file lists what the pricing system needs to run, and document
tooling is not that; ``scripts/md_to_pdf.py`` treats ``markdown`` the same way.
"""
from __future__ import annotations

import argparse
import pathlib
import re

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Inches, Pt

INK = RGBColor(0x1F, 0x4E, 0x79)          # the deck's one accent, same blue as the chart
BODY = RGBColor(0x26, 0x26, 0x26)
QUIET = RGBColor(0x70, 0x70, 0x70)

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.8)


def parse(markdown_text):
    """Turn the script into ``[{title, subtitle, bullets, image, notes}]``.

    Inputs
    ------
    1. markdown_text : str — the whole script file.

    Returns: list of dicts, one per ``## Slide N — …`` heading, in order.
    """
    slides = []
    current = None
    note_lines, table_lines, in_note, in_aside = [], [], False, False

    def flush():
        if current is None:
            return
        notes = " ".join(note_lines).strip()
        if table_lines:
            notes = (notes + "\n\nFor reference:\n" + "\n".join(table_lines)).strip()
        current["notes"] = notes
        slides.append(current)

    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            if not heading.lower().startswith("slide"):
                flush()
                current = None
                continue
            flush()
            title = re.sub(r"^Slide\s*\d+\s*[—-]\s*", "", heading).strip()
            current = {"title": title, "subtitle": None, "bullets": [], "image": None,
                       "notes": ""}
            note_lines, table_lines, in_note, in_aside = [], [], False, False
            continue

        if current is None:
            continue

        if in_aside:                                   # a bracketed note to ourselves
            if stripped.endswith("]"):
                in_aside = False
            continue
        if stripped.startswith("["):
            in_aside = not stripped.endswith("]")
            continue

        if stripped.startswith("*Say:*"):
            in_note = True
            note_lines.append(stripped[len("*Say:*"):].strip())
            continue
        if in_note:
            if not stripped:
                in_note = False
            else:
                note_lines.append(stripped)
            continue

        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                table_lines.append("  " + " | ".join(c for c in cells if c))
            continue

        m = re.match(r"\*\*Chart:.*?\*\*\s*[—-]\s*`([^`]+)`", stripped)
        if m:
            current["image"] = m.group(1)
            continue

        if stripped.startswith("- "):
            current["bullets"].append(stripped[2:].strip())
            continue
        if stripped and current["bullets"] and raw.startswith("  "):
            current["bullets"][-1] += " " + stripped          # a wrapped bullet
            continue
        if stripped.startswith("**") and stripped.endswith("**") and not current["bullets"]:
            current["subtitle"] = stripped
            continue

    flush()
    return slides


def _write(frame, text, size, colour=BODY, bold_default=False, space_after=Pt(14)):
    """Append one paragraph, honouring ``**bold**`` and dropping stray emphasis marks."""
    para = frame.paragraphs[0] if not frame.text and len(frame.paragraphs) == 1 \
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


def build(slides, out_path, root):
    """Render the parsed script to a 16:9 deck."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
    blank = prs.slide_layouts[6]

    for index, spec in enumerate(slides):
        slide = prs.slides.add_slide(blank)
        first = index == 0

        box = slide.shapes.add_textbox(MARGIN, Inches(0.55 if not first else 2.2),
                                       SLIDE_W - 2 * MARGIN, Inches(1.1))
        box.text_frame.word_wrap = True
        _write(box.text_frame, spec["title"], Pt(40 if first else 30), INK,
               bold_default=True, space_after=Pt(4))

        top = Inches(3.35) if first else Inches(1.75)
        if spec["subtitle"]:
            sub = slide.shapes.add_textbox(MARGIN, Inches(3.25), SLIDE_W - 2 * MARGIN,
                                           Inches(0.7))
            sub.text_frame.word_wrap = True
            _write(sub.text_frame, spec["subtitle"], Pt(20), QUIET)
            top = Inches(4.15)

        if spec["image"]:
            picture = root / spec["image"]
            if picture.exists():
                width = SLIDE_W - 2 * MARGIN
                slide.shapes.add_picture(str(picture), MARGIN, Inches(1.85), width=width)
                # the chart's own aspect decides where the bullets can start
                shape = slide.shapes[-1]
                top = Emu(int(shape.top) + int(shape.height)) + Inches(0.35)

        if spec["bullets"]:
            body = slide.shapes.add_textbox(MARGIN, top, SLIDE_W - 2 * MARGIN,
                                            SLIDE_H - top - Inches(0.6))
            frame = body.text_frame
            frame.word_wrap = True
            for bullet in spec["bullets"]:
                _write(frame, "•  " + bullet, Pt(19 if not first else 18),
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
    for i, spec in enumerate(slides, 1):
        print(f"  {i}. {spec['title'][:58]:58s} "
              f"{len(spec['bullets'])} bullets"
              f"{'  +chart' if spec['image'] else ''}"
              f"{'  +notes' if spec['notes'] else '  NO NOTES'}")


if __name__ == "__main__":
    main()
