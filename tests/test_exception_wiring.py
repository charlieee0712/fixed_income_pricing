"""Every name used in an `except` clause must actually be bound in that file.

This is a static check, and it exists because a runtime one is worthless here: an
`except (CalibrationError, ValueError)` whose `CalibrationError` was never imported is
perfectly valid Python until the moment an exception passes through it. `scripts/
phase2_risk.py` shipped in exactly that state — three handlers naming an unimported class.
The five production drivers all ran green against it, because no bond in the portfolio
happened to fail calibration that day. The first one that did would have got a
`NameError` where a flagged output row belonged.

So the check runs over the source text, not over an execution: parse each file, collect the
names appearing in exception handlers, and require each to be either a builtin or bound
somewhere in the module.
"""
import ast
import builtins
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_FILES = sorted(
    p for p in list((_ROOT / "src").rglob("*.py")) + list((_ROOT / "scripts").rglob("*.py"))
    if "__pycache__" not in p.parts
)


def handler_names(tree):
    """The identifiers a file's `except` clauses depend on, dotted roots included."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            for sub in ast.walk(node.type):
                if isinstance(sub, ast.Name):
                    names.add(sub.id)
                elif isinstance(sub, ast.Attribute):
                    root = sub
                    while isinstance(root, ast.Attribute):
                        root = root.value
                    if isinstance(root, ast.Name):
                        names.add(root.id)
    return names


def bound_names(tree):
    """Everything the module binds at any level: imports, assignments, defs, classes."""
    bound = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                bound.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, (ast.arg,)):
            bound.add(node.arg)
    return bound


@pytest.mark.parametrize("path", _FILES, ids=lambda p: str(p.relative_to(_ROOT)).replace("\\", "/"))
def test_every_caught_exception_name_is_bound(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    unbound = handler_names(tree) - bound_names(tree)
    assert not unbound, (
        f"{path.relative_to(_ROOT)} catches {sorted(unbound)}, which it never imports or "
        f"defines. This raises NameError the first time that handler is reached."
    )


def test_the_check_itself_catches_the_defect_it_was_written_for():
    """A check that has never fired is not evidence. This is the exact shipped defect."""
    shipped = ast.parse(
        "from pricing.risk import risk_metrics\n"
        "try:\n"
        "    oas = implied_oas(bond)\n"
        "except (CalibrationError, ValueError) as e:\n"
        "    rows.append(flagged(bond, e))\n"
    )
    assert handler_names(shipped) - bound_names(shipped) == {"CalibrationError"}

    fixed = ast.parse("from pricer.errors import CalibrationError\n" + ast.unparse(shipped))
    assert handler_names(fixed) - bound_names(fixed) == set()

    # and the forms that must NOT be flagged: builtins, dotted access, a local alias
    ok = ast.parse(
        "import pricer.errors as err\n"
        "Alias = err.CalibrationError\n"
        "try:\n    f()\nexcept (ValueError, err.CalibrationError, Alias):\n    pass\n"
    )
    assert handler_names(ok) - bound_names(ok) == set()
