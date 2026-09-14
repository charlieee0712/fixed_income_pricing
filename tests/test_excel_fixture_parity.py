"""The committed Excel fixtures still match the live engine (added 2026-09-13).

``integrations/excel_vba/examples/`` holds eleven request/response pairs that SHIP — the
Excel harness replays them in its no-Python mode, and they are the worked examples in the
interface document. Nothing verified them. They were generated on 2026-08-31 and two
rounds of restructuring went past without a single automated check that the engine still
answers those requests the same way; the only test touching ``excel_vba`` greps the .bas
for its field set.

Running them by hand on 2026-09-13 found one real piece of drift, in the frozen v1.0 error
message: it names the configured currencies, and the registry grew from six to fourteen on
2026-09-03. Harmless there — see below — but nothing would have said so.

⚠️ It also found something nobody knew. The first version of this file asserted exact
equality; it passed on the Windows machine that generated the fixtures and put **five
failures on the Linux deployment host**. So **the endpoint's JSON is not byte-identical
across platforms for the lattice products** — CLAUDE.md said it was, but that note dates
from 2026-08-25, when the endpoint priced vanilla bonds only and there was no lattice in
it. The tolerance below is built from measuring that, not from guessing at it.

⚠️ **The two v1.0 pairs are a frozen backward-compatibility corpus, NOT regenerable
goldens, and this file is the first place that is written down.** Their job is to prove
that a typeless request — the shape a v1.0 spreadsheet sends — is still answered, and that
a v1.0-shaped response still carries everything the bridge reads. Today's engine answers
them at ``schema_version`` 1.1 with an added ``inputs_used.instrument_type``, which is the
additive contract working as designed. Regenerating them would destroy the only v1.0
documents in the repository. So they are held to a different, weaker, correct standard:
today's answer must be a SUPERSET of the frozen one.

To regenerate the nine v1.1 goldens after a deliberate engine change, run this **on the
machine whose numbers the fixtures should carry**, then re-run the real-Excel gate::

    PYTHONPATH=src python -c "import json,pathlib; \\
      from pricer.endpoints.main import analyze_payload; \\
      p=pathlib.Path('integrations/excel_vba/examples'); \\
      [ (p/r.name.replace('_request','_response')).write_text( \\
          json.dumps(analyze_payload(json.loads(r.read_text('utf-8'))), indent=2)+'\\n', \\
          encoding='utf-8') for r in p.glob('*request*v1_1.json') ]"
"""
import json
import pathlib

import pytest

from pricer.endpoints.main import analyze_payload

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DATA = _ROOT / "data"
_EXAMPLES = _ROOT / "integrations" / "excel_vba" / "examples"

#: Fields whose text is human-readable and may be reworded without breaking a consumer.
#: Only exempted for the FROZEN v1.0 corpus; the v1.1 goldens compare theirs exactly.
_FREE_TEXT = ("message",)

# ---------------------------------------------------------------------------------------
# How closely a number has to match, and why it is not "exactly".
#
# Measured across all nine goldens on 2026-09-13, Windows against the Linux host:
#
#   every string, code, field and structural element   IDENTICAL
#   prices, spreads, accrued                           <= 6e-16 relative (machine epsilon)
#   durations, dv01                                    <= 4e-13 (one division by the bump)
#   convexity                                          <= 7.5e-08 absolute — the worst
#                                                      anywhere, and the documented profile:
#                                                      a second difference over bump squared
#                                                      amplifies a last ulp by 1e8
#
# Two quantities looked alarming in RELATIVE terms and are not, which is why the scale below
# has a floor of 1.0 instead of dividing by the value: calibration_residual_per_100 (value
# ~6.6e-09, differing by 4e-14) and a puttable's price_effect_per_1pct_vol (value ~1.1e-11 —
# that put is inactive — differing by 7e-15) are near zero by construction, so a relative
# measure on them says nothing at all. Their absolute differences are machine epsilon.
#
# So: non-numeric stays EXACT, because that is where contract drift shows up and it must go
# red. Numbers get a tolerance taken from the measurement.
#
# ⚠️ ONE TOLERANCE FOR EVERYTHING WAS WRONG, and a mutation test caught it before this
# shipped. A single 1e-6 bound looked like 47x headroom over the noise — but the noise it was
# sized for is convexity's, and applying that same bound to a PRICE let a deliberate 1e-4
# perturbation through (1e-4 / 104 = 9.6e-07, just inside 1e-6). The amplification is a
# property of the second-difference formula, not of the endpoint, so only the amplified
# quantity gets the loose bound:
#
#   convexity        1e-6   measured 2.11e-08   47x headroom
#   everything else  1e-10  measured 3.87e-13   258x headroom, and a 1e-4 price move now fails
# ---------------------------------------------------------------------------------------

#: Per-fixture gate for the one quantity a second difference amplifies by 1e8.
_TOL_CONVEXITY = 1e-6

#: Per-fixture gate for every other number: prices, spreads, durations, accrued, residuals.
_TOL_DEFAULT = 1e-10

#: Set-level: the worst deviation anywhere, as a FRACTION OF ITS OWN BUDGET, must stay under
#: this. Measured 0.021 — convexity using 2% of its allowance. Separate from the gates on
#: purpose: the floor could grow tenfold with every per-fixture test still passing, and
#: nobody would hear about it.
_BUDGET_USED_MAX = 0.10


def _tolerance(path):
    """The applicable bound for a numeric field, by name.

    Inputs
    ------
    1. path : str — the dotted path of the field.

    Returns: float — :data:`_TOL_CONVEXITY` for convexity, :data:`_TOL_DEFAULT` otherwise.
    """
    return _TOL_CONVEXITY if path.endswith("convexity") else _TOL_DEFAULT


def _budget_used(path, committed, fresh):
    """How much of this field's tolerance the difference consumes, as a fraction.

    Scaled by ``max(1, |committed|)`` rather than by ``|committed|``: several fields here
    are near zero by construction (a calibration residual, an inactive option's price
    effect), and a relative measure on those reports enormous differences that are in fact
    machine epsilon.
    """
    return (abs(fresh - committed) / max(1.0, abs(committed))) / _tolerance(path)


@pytest.fixture(autouse=True)
def _data_dir(monkeypatch):
    """Point the endpoint at the repo's own curve exports, whatever the CWD."""
    monkeypatch.setenv("FIP_DATA_DIR", str(_DATA))


def _pairs():
    """Every (request, response) fixture pair on disk, with its schema generation.

    Returns: list of (request_path, response_path, generation) where generation is
    ``"1.1"`` for a regenerable golden and ``"1.0"`` for the frozen corpus.

    ⚠️ Raises rather than skipping when a request has no partner: a new fixture whose
    name does not follow the convention must fail loudly, not vanish from the run.
    """
    out = []
    for request in sorted(_EXAMPLES.glob("*request*.json")):
        response = _EXAMPLES / request.name.replace("_request", "_response")
        if not response.exists():                    # the error pair is named differently
            response = _EXAMPLES / request.name.replace("_request", "")
        if not response.exists():
            raise AssertionError(f"{request.name} has no response fixture beside it")
        out.append((request, response, "1.1" if "_v1_1" in request.name else "1.0"))
    return out


_PAIRS = _pairs()
_GOLDEN = [p for p in _PAIRS if p[2] == "1.1"]
_FROZEN = [p for p in _PAIRS if p[2] == "1.0"]


def _numeric(value):
    """A JSON number, excluding bool (which is an int in Python and is not a measurement)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _compare(committed, fresh, path=""):
    """Structural and textual equality, with a numeric tolerance.

    Inputs
    ------
    1. committed : the fixture on disk.
    2. fresh     : today's answer.
    3. path      : dotted path, carried into the failure message.

    Returns: ``(failures, worst)`` — ``failures`` is a list of strings, empty when the two
    agree; ``worst`` is ``(budget_used, path)`` for the numeric difference that consumed
    the largest share of its own tolerance, whether or not it exceeded it.
    """
    worst = (0.0, path or ".")
    if _numeric(committed) and _numeric(fresh):
        used = _budget_used(path, committed, fresh)
        worst = (used, path)
        if used > 1.0:
            return [f"{path}: {committed!r} -> {fresh!r} "
                    f"({used:.1f}x its {_tolerance(path):.0e} budget)"], worst
        return [], worst
    if isinstance(committed, dict):
        if not isinstance(fresh, dict):
            return [f"{path}: was an object, now {type(fresh).__name__}"], worst
        fails = [f"{path}.{k}: dropped" for k in committed if k not in fresh]
        fails += [f"{path}.{k}: added" for k in fresh if k not in committed]
        for key in committed:
            if key in fresh:
                sub, w = _compare(committed[key], fresh[key], f"{path}.{key}")
                fails += sub
                worst = max(worst, w)
        return fails, worst
    if isinstance(committed, list):
        if not isinstance(fresh, list):
            return [f"{path}: was an array, now {type(fresh).__name__}"], worst
        if len(committed) != len(fresh):
            return [f"{path}: {len(committed)} entries -> {len(fresh)}"], worst
        fails = []
        for i, entry in enumerate(committed):
            sub, w = _compare(entry, fresh[i], f"{path}[{i}]")
            fails += sub
            worst = max(worst, w)
        return fails, worst
    return ([] if committed == fresh else [f"{path}: {committed!r} -> {fresh!r}"]), worst


def test_the_fixture_set_is_the_one_we_think_it_is():
    """Guard against a silently empty parametrisation.

    A discovery loop that finds nothing passes every test derived from it. This is the
    only assertion here that does not depend on the loop having found anything.
    """
    assert len(_PAIRS) == 11, [p[0].name for p in _PAIRS]
    assert len(_GOLDEN) == 9
    assert len(_FROZEN) == 2


@pytest.mark.parametrize("request_path,response_path",
                         [(a, b) for a, b, _ in _GOLDEN],
                         ids=[a.stem for a, _, _ in _GOLDEN])
def test_a_shipped_v1_1_fixture_still_reproduces(request_path, response_path):
    """Structure and text exactly; numbers to the measured cross-platform floor.

    The endpoint is deterministic on these payloads — ``request_id`` is echoed from the
    request rather than generated, and no field carries a timestamp — so ON ONE MACHINE
    this is byte-for-byte, verified by running each payload twice. Across machines it is
    not, and the tolerance block above says by how much and why.
    """
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    committed = json.loads(response_path.read_text(encoding="utf-8"))
    failures, _ = _compare(committed, analyze_payload(payload))
    assert failures == []


def test_the_cross_platform_noise_floor_is_still_where_we_measured_it():
    """The floor itself, not any one fixture.

    Every per-fixture test could pass while the noise floor quietly grew tenfold — a real
    change in the arithmetic wearing the costume of rounding. This asserts the worst
    deviation across the whole set as a fraction of its own budget, which is a statement
    about the numerics rather than about any single bond.
    """
    worst = (0.0, "nothing")
    for request_path, response_path, _ in _GOLDEN:
        _, w = _compare(json.loads(response_path.read_text(encoding="utf-8")),
                        analyze_payload(json.loads(request_path.read_text(encoding="utf-8"))))
        worst = max(worst, w)
    assert worst[0] < _BUDGET_USED_MAX, \
        f"noise floor moved: {worst[1]} now uses {worst[0]:.1%} of its tolerance"


def _shortfalls(frozen, fresh, path=""):
    """Every field the frozen document carries, still present with the same value.

    Inputs
    ------
    1. frozen : the committed v1.0 document (or a fragment of it).
    2. fresh  : today's answer to the same request.
    3. path   : dotted path, for the failure message.

    Returns: list[str] — empty when today's answer is a superset of the frozen one.

    Two exemptions, each for a stated reason rather than to make the test pass:
    ``schema_version`` (1.0 -> 1.1 is the version string doing its job) and free-text
    ``message`` fields (human-readable; the machine-readable ``code`` and ``field``
    beside them are NOT exempt and are compared exactly). Numbers use the same tolerance
    as the goldens, for the same measured reason.
    """
    if path == ".schema_version":
        return []
    if path.split(".")[-1] in _FREE_TEXT:
        return [] if isinstance(fresh, str) == isinstance(frozen, str) else \
               [f"{path}: text field changed type"]
    if _numeric(frozen) and _numeric(fresh):
        used = _budget_used(path, frozen, fresh)
        return [] if used <= 1.0 else [f"{path}: {frozen!r} -> {fresh!r}"]
    if isinstance(frozen, dict):
        if not isinstance(fresh, dict):
            return [f"{path}: was an object, now {type(fresh).__name__}"]
        out = []
        for key in frozen:
            if key not in fresh:
                out.append(f"{path}.{key}: dropped")
            else:
                out += _shortfalls(frozen[key], fresh[key], f"{path}.{key}")
        return out
    if isinstance(frozen, list):
        if not isinstance(fresh, list):
            return [f"{path}: was an array, now {type(fresh).__name__}"]
        if len(fresh) < len(frozen):
            return [f"{path}: had {len(frozen)} entries, now {len(fresh)}"]
        out = []
        for i, entry in enumerate(frozen):     # prefix semantics: extra entries are additive
            out += _shortfalls(entry, fresh[i], f"{path}[{i}]")
        return out
    return [] if frozen == fresh else [f"{path}: {frozen!r} -> {fresh!r}"]


@pytest.mark.parametrize("request_path,response_path",
                         [(a, b) for a, b, _ in _FROZEN],
                         ids=[a.stem for a, _, _ in _FROZEN])
def test_a_frozen_v1_0_fixture_is_still_answered_and_still_a_subset(request_path,
                                                                    response_path):
    """v1.1 is ADDITIVE over v1.0 — the guarantee a v1.0 spreadsheet depends on.

    These two are never regenerated (see the module docstring), so the useful question is
    not "does today's engine emit this document" but "would a consumer of this document
    still work". That means: the typeless request is still answered, and every field the
    frozen response carries is still produced with the same value.
    """
    frozen = json.loads(response_path.read_text(encoding="utf-8"))
    assert frozen["schema_version"] == "1.0", "this pair is the v1.0 corpus"
    assert "instrument_type" not in json.loads(
        request_path.read_text(encoding="utf-8")).get("bond", {}), \
        "a v1.0 request is typeless — that is what makes it a v1.0 request"

    fresh = analyze_payload(json.loads(request_path.read_text(encoding="utf-8")))
    assert fresh["status"] == frozen["status"]
    assert _shortfalls(frozen, fresh) == []


def test_the_frozen_corpus_is_not_accidentally_regenerable():
    """⚠️ Pins the DIVERGENCE, so nobody 'fixes' it by regenerating.

    If today's engine ever answered a typeless request at schema 1.0 again, either the
    additive contract was rolled back or these files were regenerated — and regenerating
    them would delete the only v1.0 documents in the repository, which are the whole point
    of keeping them. Either way it is a decision, not a tidy-up, so it must go red first.
    """
    for request_path, _, _ in _FROZEN:
        fresh = analyze_payload(json.loads(request_path.read_text(encoding="utf-8")))
        assert fresh["schema_version"] == "1.1"
