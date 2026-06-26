# Root conftest: put the repo root and src/ on sys.path so tests can import the
# layered packages (curves, credit, ...) without an install. Run pytest from repo root.
import pathlib
import sys

_ROOT = pathlib.Path(__file__).parent
for _p in (_ROOT, _ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
