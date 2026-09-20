"""The one chart in the investor deck: where the 2,260 securities stand.

Deliberately plain. On a slide read from six metres the only things that survive are the
lengths and the four labels, so everything else is removed.
"""
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SEGMENTS = [
    ("Priced today",                       766,  "#1f4e79"),
    ("Waiting on data we have asked for", 1046,  "#d68910"),
    ("Scoped, not yet built",              412,  "#9e9e9e"),
    ("Excluded / out of scope",             36,  "#d9d9d9"),
]
TOTAL = sum(n for _, n, _ in SEGMENTS)
assert TOTAL == 2260, TOTAL

fig, ax = plt.subplots(figsize=(13, 2.6))
left = 0
for label, n, colour in SEGMENTS:
    ax.barh([0], [n], left=left, color=colour, height=0.52, edgecolor="white", linewidth=2)
    if n / TOTAL > 0.08:                       # only label a segment wide enough to hold text
        ax.text(left + n / 2, 0, f"{n:,}\n{n / TOTAL:.0%}", ha="center", va="center",
                color="white", fontsize=17, fontweight="bold", linespacing=1.35)
    left += n

ax.set_xlim(0, TOTAL)
ax.set_ylim(-0.6, 0.72)
ax.axis("off")

# The legend carries the words; the bar carries the quantities.
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in SEGMENTS]
ax.legend(handles, [l for l, _, _ in SEGMENTS], loc="upper center",
          bbox_to_anchor=(0.5, 0.06), ncol=4, frameon=False, fontsize=13.5,
          handlelength=1.1, handleheight=1.1, columnspacing=1.9)

ax.text(0, 0.62, "2,260 securities in the portfolio", fontsize=15.5,
        fontweight="bold", color="#333333")
ax.text(TOTAL, 0.62, "36 excluded", fontsize=12, color="#888888", ha="right")

out = pathlib.Path("docs/img/investor_coverage.png")
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print("wrote", out, f"({out.stat().st_size:,} bytes)")
