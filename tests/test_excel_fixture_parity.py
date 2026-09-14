"""The committed Excel fixtures still match the live engine (added 2026-09-13).

``integrations/excel_vba/examples/`` holds eleven request/response pairs that SHIP — the
Excel harness replays them in its no-Python mode, and they are the worked examples in the
interface document. Nothing verified them. They were generated on 2026-08-31 and two
rounds of restructuring went past without a single automated check that the engine still
answers those requests the same way; the only test touching ``excel_vba`` greps the .bas
for its field set.

Running them by hand on 2026-09-13 found nine reproducing byte-for-byte and one real piece
of drift, in the frozen v1.0 error message: it names the configured currencies, and the
registry grew from six to fourteen on 2026-09-03. Harmless there — see below — but nothing
would have said so.

⚠️ **The two v1.0 pairs are a frozen backward-compatibility corpus, NOT regenerable
goldens, and this file is the first place that is written down.** Their job is to prove
that a typeless request — the shape a v1.0 spreadsheet sends — is still answered, and that
a v1.0-shaped response still carries everything the bridge reads. Today's engine answers
them at ``schema_version`` 1.1 with an added ``inputs_used.instrument_type``, which is the
additive contract working as designed. Regenerating them would destroy the only v1.0
documents in the repository. So they are held to a different, weaker, correct standard:
today's answer must be a SUPERSET of the frozen one.

To regenerate the nine v1.1 goldens after a deliberate engine change::

    PYTHONPATH=src python -c "import json,pathlib,sys; \\
      from pricer.endpoints.main import analyze_payload; \\
      p=pathlib.Path('integrations/excel_vba/examples'); \\
      [ (p/r.name.replace('_request','_response')).write_text( \\
          json.dumps(analyze_payload(json.loads(r.read_text('utf-8'))), indent=2)+'\\n', \\
          encoding='utf-8') for r in p.glob('*request*v1_1.json') ]"

then re-run the real-Excel gate, because the harness compares against these files.
"""
import json
import pathlib

import pytest

from pricer.endpoints.main import analyze_payload

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DATA = _ROOT / "data"
_EXAMPLES = _ROOT / "integrations" / "excel_vba" / "examples"

#: Fields whose text is human-readable and may be reworded without breaking a consumer.
#: Only exempted for the FROZEN v1.0 corpus; the v1.1 goldens are held to exact equality.
_FREE_TEXT = ("message",)


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
def test_a_shipped_v1_1_fixture_still_reproduces_exactly(request_path, response_path):
    """Byte-for-byte, with nothing stripped.

    The endpoint is fully deterministic on these payloads — ``request_id`` is echoed from
    the request rather than generated, and no field carries a timestamp — so there is
    nothing to exempt and the strictest possible comparison is also the correct one.
    (Verified by running each payload twice: eleven for eleven identical.)
    """
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    committed = json.loads(response_path.read_text(encoding="utf-8"))
    assert analyze_payload(payload) == committed


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
    beside them are NOT exempt and are compared exactly).
    """
    if path == ".schema_version":
        return []
    if path.split(".")[-1] in _FREE_TEXT:
        return [] if isinstance(fresh, str) == isinstance(frozen, str) else \
               [f"{path}: text field changed type"]
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
        for i, entry in enumerate(frozen):       # prefix semantics: extra entries are additive
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
