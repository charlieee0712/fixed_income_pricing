# Release facts — Round 2b hardening

**Generated from the live repository at `16318c1` (working tree DIRTY) on 2026-09-15.** Every number below is
read out of a file a driver just wrote. Regenerate with `PYTHONPATH=src python
scripts/release_facts.py` after any code-bearing change, and re-run the drivers first.

## Production outputs

| file | rows | sha256 (first 32) |
|---|---:|---|
| `implied_oas_2009-03-31.csv` | 566 | `020bdbbc2c81da5038b57d9ef636373c` |
| `implied_oas.csv` | 561 | `7929ff77df17db630c07689bd3799c20` |
| `callable_risk.csv` | 3 | `703292d505475b2e63cd495e008a4106` |
| `phase2_risk_2009-03-31.csv` | 63 | `ea732f0ec3d52e74cbb97113492be71f` |
| `phase2_risk_2009-06-10.csv` | 63 | `fadd25a09b6d4128f5782bf3d038cc9c` |
| `sovereign_risk_2009-03-31.csv` | 154 | `40baf346bbb8afbaf5c29cb195dc8df1` |
| `sovereign_risk_2009-06-10.csv` | 154 | `d91e3c8ff42724a48ce5e4ceb0855202` |

## Disposition sidecars — every security accounted for, at both dates

These are the evidence that nothing is silently dropped: the population, the rows that
reached the output, and a NAMED reason for every one that did not. The filenames are
dated because an undated default let the 6-10 run overwrite the 3-31 one.

| file | rows | sha256 (first 32) |
|---|---:|---|
| `corporate_disposition_2009-03-31.csv` | 732 | `5d9860529d3a6a7f20ff54c62535822b` |
| `corporate_disposition_2009-06-10.csv` | 732 | `e53594606bcddbd1c28ff472354bf5d6` |
| `callable_disposition_2009-03-31.csv` | 5 | `041d6048529e381648cf80e7e8d85f34` |
| `callable_disposition_2009-06-10.csv` | 5 | `cbd0feaacac48bdbb1932f96bc22b5c3` |
| `sovereign_disposition_2009-03-31.csv` | 154 | `b00715c838addde12c89d508792f9de8` |
| `sovereign_disposition_2009-06-10.csv` | 154 | `83bdfbb0af4f63fb4b02f0c141a13a9b` |

## Text fingerprints -- what floating point cannot move

A whole-file sha256 answers *are these the same bytes*, and across processors the honest
answer is routinely no: a convexity divides a second difference by the square of a small
bump, multiplying a last-digit rounding by a hundred million. The digests below cover only
the columns that carry **no arithmetic** -- identifiers, routes, dates, flags, reason
codes. Those are decided by logic, so they must be IDENTICAL on every machine.

**A differing sha256 above with a matching digest below is rounding. A differing digest
below is a defect** -- and the kind that hides: on 2026-09-03 a driver flag embedded a
filesystem path, so one failure read two different ways on Windows and on Linux.

Checked on any machine by `PYTHONPATH=src python scripts/platform_parity.py`.

| file | text columns | digest |
|---|---:|---|
| `implied_oas_2009-03-31.csv` | 13 | `3de68dfcc827597f` |
| `implied_oas.csv` | 13 | `aa0995f394df3e73` |
| `callable_risk.csv` | 11 | `7ef56b443b448fd8` |
| `phase2_risk_2009-03-31.csv` | 17 | `e4ea5c4fc972b269` |
| `phase2_risk_2009-06-10.csv` | 17 | `7af5a11f39cc3fa9` |
| `sovereign_risk_2009-03-31.csv` | 20 | `92c2a10ec6287756` |
| `sovereign_risk_2009-06-10.csv` | 20 | `b9519b9260184405` |
| `corporate_disposition_2009-03-31.csv` | 5 | `d7a83a7b1f377094` |
| `corporate_disposition_2009-06-10.csv` | 5 | `df819ce056b736f9` |
| `callable_disposition_2009-03-31.csv` | 5 | `605e56988db3808b` |
| `callable_disposition_2009-06-10.csv` | 5 | `b619857b1f02ceea` |
| `sovereign_disposition_2009-03-31.csv` | 4 | `1155b48c221fd1e8` |
| `sovereign_disposition_2009-06-10.csv` | 4 | `fa76b8d0b409b8f8` |

## Corporate coverage

| valuation date | rows in output | with a model spread | carried at the custodian mark |
|---|---:|---:|---:|
| 2009-03-31 (baseline) | 566 | 555 | 11 |
| 2009-06-10 (control) | 561 | 550 | 11 |

## Routes at the 2009-03-31 baseline

| route | bonds |
|---|---:|
| `vanilla` | 481 |
| `make-whole-as-vanilla` | 47 |
| `vanilla-schedule` | 10 |
| `hybrid` | 10 |
| `hybrid-margin-unavailable` | 8 |
| `floating` | 7 |
| `recovery` | 3 |

## Confidence labelling

A number that rests on a term nobody has confirmed, or on an estimate of an observable,
says so in the row it appears in — not only in prose somewhere else.

| label | count | what it means |
|---|---:|---|
| `current_coupon_source=base_curve_proxy` | 6 | the coupon already running was not in the custodian file, so it is estimated from the curve and held fixed while the risk is measured; the sensitivities are provisional |
| `current_coupon_source=supplied` | 1 | the actual fixing was used |
| `exercise_terms_status=provisional` | 8 | every lattice-priced bond: a custodian date with the par-call convention applied on top, verified by nobody |
| `exercise_terms_status=confirmed` | 0 | no exercise term in this project has been confirmed against Bloomberg |

## Test suite

`pytest -q` → **485 passed in 43.98s** (local, Python 3.13.5).

