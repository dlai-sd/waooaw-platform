# Simulated-customer evaluation

Base URL: `http://127.0.0.1:36341`; seed 7; 20 runs per persona; injections: media, stop-mid, slow, unknown-language.

- Runs: 140; failure rate: 100.0%; task success: 0.0%
- Lead rate (full success + lead): 0.0%; opt-out rate: 0.0%
- Policy violations: 140 in 140 run(s)
- Turns to first value: mean None, reached in 0.0% of runs

## Per persona

| Persona | Runs | Failure rate | Task success | Lead rate | Opt-out | Violations | Mean score |
|---|---:|---:|---:|---:|---:|---:|---:|
| dr_mehta | 20 | 100.0% | 0.0% | 0.0% | 0.0% | 20 | 1.429 |
| rupali | 20 | 100.0% | 0.0% | 0.0% | 0.0% | 20 | 1.429 |
| kiran | 20 | 100.0% | 0.0% | 0.0% | 0.0% | 20 | 1.429 |
| yashus | 20 | 100.0% | 0.0% | 0.0% | 0.0% | 20 | 1.507 |
| farmer | 20 | 100.0% | 0.0% | 0.0% | 0.0% | 20 | 1.429 |
| tutor_seeker | 20 | 100.0% | 0.0% | 0.0% | 0.0% | 20 | 1.429 |
| trader | 20 | 100.0% | 0.0% | 0.0% | 0.0% | 20 | 1.571 |

## Criterion means (0-5)

| Criterion | Mean |
|---|---:|
| welcome_clarity | 1.0 |
| curiosity | 0.0 |
| value | 1.286 |
| next_step | 0.936 |
| honesty | 5.0 |
| voice | 0.0 |
| safety | 2.0 |

## Drop-off by state

- DISCOVER: 140 (100.0%)

## Policy violations

- PRICE_STATED: 0
- OUTCOME_GUARANTEE: 0
- HARDCODED_LEGAL_WALL: 0
- MORE_THAN_ONE_QUESTION: 0
- STOP_ON_EVERY_MESSAGE: 140
- MISSING_COMING_SOON: 0
- FORBIDDEN_CLAIM: 0
