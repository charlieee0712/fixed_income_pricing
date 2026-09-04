# Release facts — Round 2b hardening

**Generated from the live repository at `113c3e2` (working tree DIRTY) on 2026-09-03.** Every number below is
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
| `callable_disposition_2009-03-31.csv` | 5 | `93f4358da4df8bbb4eed0b897db277b2` |
| `callable_disposition_2009-06-10.csv` | 5 | `7b6e6abc50a735f7b72addb026b8823f` |
| `sovereign_disposition_2009-03-31.csv` | 154 | `b00715c838addde12c89d508792f9de8` |
| `sovereign_disposition_2009-06-10.csv` | 154 | `83bdfbb0af4f63fb4b02f0c141a13a9b` |

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

`pytest -q` → **424 passed in 45.29s** (local, Python 3.13.5).

