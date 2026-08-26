"""File-based runner for the vanilla JSON interface (plan §8): one request file in,
one response file out. This is the process the Excel/VBA bridge invokes; it is also
the simplest way to try the interface by hand.

Run from the repo root (server 47 or any machine with the repo + data):

    PYTHONPATH=src python3 scripts/price_json.py \
        --input  integrations/excel_vba/examples/vanilla_request_v1.json \
        --output /tmp/response.json

Options:
    --input     request JSON file (one request object)
    --output    response JSON file, written atomically (temp file + replace)
    --data-dir  where the *_Yield_Curve.txt exports live (else FIP_DATA_DIR, else data/)

Exit codes:
    0  status="ok"
    1  the request was refused — a readable error response WAS still written
    2  the files themselves could not be read or written (nothing to parse)

Only a short status line goes to stdout: the request payload is never echoed."""
import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, "src")

from pricer.endpoints import contracts                      # noqa: E402
from pricer.endpoints.main import analyze_vanilla_payload    # noqa: E402


def parse_args(argv=None):
    """Command-line arguments.

    Inputs
    ------
    1. argv : list | None — argument vector (defaults to ``sys.argv[1:]``).

    Returns: ``argparse.Namespace`` with ``input``, ``output``, ``data_dir``.
    """
    parser = argparse.ArgumentParser(description="Price one vanilla bond from a JSON request.")
    parser.add_argument("--input", required=True, help="request JSON file")
    parser.add_argument("--output", required=True, help="response JSON file to write")
    parser.add_argument("--data-dir", default=None,
                        help="directory holding the par-curve txt files "
                             "(default: $FIP_DATA_DIR, else 'data')")
    return parser.parse_args(argv)


def read_request(path: str):
    """Read and parse the request file.

    Inputs
    ------
    1. path : str — request JSON file.

    Returns: ``(payload, error_response)`` — exactly one of the two is None. A
    malformed file becomes an INVALID_JSON *response*, not a traceback.
    """
    with open(path, "r", encoding="utf-8-sig") as handle:   # -sig: Excel writes a BOM
        text = handle.read()
    try:
        return json.loads(text), None
    except ValueError as exc:
        return None, contracts.error_response(
            contracts.INVALID_JSON,
            f"the request file is not valid JSON ({exc.__class__.__name__}: "
            f"{str(exc).splitlines()[0]})",
        )


def write_response(path: str, response: dict) -> None:
    """Write the response atomically as UTF-8 JSON.

    Inputs
    ------
    1. path     : str — response file to create or replace.
    2. response : dict — the response object.

    Returns: None. ``allow_nan=False`` guarantees standard JSON — the endpoint has
    already turned any non-finite number into ``null`` with a warning.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(response, out, indent=2, allow_nan=False)
            out.write("\n")
        os.replace(temp_path, path)
    except BaseException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def status_line(response: dict) -> str:
    """One short line for stdout — status, request id, and the error code if any."""
    if response["status"] == "ok":
        return f"ok request_id={response['request_id']}"
    code = response["errors"][0]["code"] if response["errors"] else "UNKNOWN"
    return f"error code={code} request_id={response['request_id']}"


def main(argv=None) -> int:
    """Entry point: read, price, write, report.

    Inputs
    ------
    1. argv : list | None — argument vector.

    Returns: int — the process exit code (0 / 1 / 2 as documented above).
    """
    args = parse_args(argv)
    if args.data_dir:
        os.environ["FIP_DATA_DIR"] = args.data_dir

    try:
        payload, failure = read_request(args.input)
    except OSError as exc:
        print(f"error could not read the request file ({exc.__class__.__name__})")
        return 2

    response = failure if failure is not None else analyze_vanilla_payload(payload)

    try:
        write_response(args.output, response)
    except OSError as exc:
        print(f"error could not write the response file ({exc.__class__.__name__})")
        return 2

    print(status_line(response))
    return 0 if response["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
