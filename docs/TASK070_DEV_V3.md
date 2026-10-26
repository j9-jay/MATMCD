# TASK_070 head B DEV_V3: 5-stage reasoning-state retrieval (development split only)

Date: 2026-10-27. Branch `task070/head-b-dev-v3`. Code: `scripts/task070_direct.py` (`DirectSelector.select`, state branches only).

Scope: RCAEval RE2-OB repetition 1 (`--split dev`, all 30 cases = 5 services x 6 faults, `--start 0 --cases 30`).
Every run below covers 30 cases. No test-split run, no output head A, no category 2, no freeze.

Unchanged (shared): `task070_corpus.py`, `K_DIRECT = 24`, `ORDER_REPEATS = 3`, `SAMPLING`, `SYSTEM`, `TEMPLATE`,
`FLAT_QUERY`, `parse_ranking`, `judge`, the `none`/`flat`/`role_only` branches and `ROLE_DOCUMENT_BUDGET`,
`task070_metrics.py`, Qwen3.5-4B via the pinned llama-server, BGE-M3 embeddings. No downloads.
The STATE_DEV_V2 constants (`STATE_BUDGET`, `PLANNER_TEMPLATE`, `case_overview`) stay in the file because
`role_only` uses `STATE_BUDGET["STRUCTURE"]`; the state methods no longer use them.

## 1. Design

Both state methods share S1, S2, S4 and S5; they differ only in S3. Each stage draws only units that no
earlier stage chose. Order of evidence given to the judge: S1, S2, S4, then the flat fill.

| stage | what it selects | budget (start run) |
|---|---|---|
| S1 telemetry | the KPI unit (frontend p90 latency); the most-flagged metric of each of the `N_SUSPECTS = 3` strongest-deviation services (`deviation_strength` / `strength_order`, services with zero flagged metric-minutes are not suspects); `trace_error` units, most error spans first | kpi 1 + metric 3 + trace_error 3 = 7 |
| S2 structure | `call_graph` units that mention a suspect, and wiki units from docs 03, 04, 07, 10 that mention a suspect; both ranked by `S2_QUERY` ("Dependencies and call flow of <suspects>: which services call them, which services they call, upstream and downstream paths from frontend.") | call_graph 2 + wiki 3 = 5 |
| S3 hypotheses | up to `N_HYPOTHESES = 3` (service, mechanism) pairs; no retrieval | 0 |
| S4 evidence per hypothesis | the service's telemetry (`metric` only when flagged, `log_template`, `trace_perf`, `trace_error`) and wiki units of the mechanism's docs that mention the service, both ranked by `S4_QUERY` ("Hypothesis: <service> caused the incident through <phrase>. Evidence of <phrase> in <service>: abnormal metrics, error logs, failing or slow calls, related configuration and error handling.") | 12, split evenly: per = 12 // #hypotheses, wiki = max(1, per // 4), telemetry = per - wiki (3 hypotheses: 3 telemetry + 1 wiki each) |
| S5 | unchanged judge (output head B) | - |
| fill | unused budget filled by `FLAT_QUERY` over all remaining units | 24 - selected |

Mechanisms (`MECHANISMS`: key -> query phrase, wiki docs searched in S4):

| key | phrase | wiki docs |
|---|---|---|
| cpu | CPU saturation | 18, 19 |
| memory | memory exhaustion | 18, 14, 19 |
| disk | disk I/O pressure | 14, 15, 18 |
| network | network or connection failure | 11, 17, 20 |
| latency | slow responses | 11, 24, 19 |
| load | abnormal request load | 18, 11 |
| errors | failing requests and errors | 11, 05, 06, 24 |

Metric column suffix -> mechanism (`METRIC_MECHANISM`): cpu -> cpu, mem -> memory, diskio -> disk,
socket -> network, latency-90 -> latency, workload -> load, error -> errors.

### S3 rule of state_fixed (label-free, depends on S1)

One hypothesis per S1 suspect, in deviation-strength order (at most 3). Its mechanism comes from that
service's S1 evidence: the suffix of its most-flagged metric (the metric S1 selected), plus `errors` if S1
selected a `trace_error` unit of that service; `latency` if neither exists (did not occur). Multiple keys
join their phrases with "and" in the S4 query and union their docs.

### S3 of state_dynamic (planner, temperature 0, same client as the judge)

System: `You form root-cause hypotheses for a microservice incident. Reply with JSON only.`
User (`PLANNER3_TEMPLATE`):

```
Incident: frontend latency increased.

Candidate root-cause services: <the 12 candidates>

Evidence gathered so far (telemetry: user-facing symptom, anomalous services, trace errors; then system structure: call graph and wiki):
[1] <S1/S2 unit text>
...

Mechanisms: cpu (CPU saturation), memory (memory exhaustion), disk (disk I/O pressure), network (network or connection failure), latency (slow responses), load (abnormal request load), errors (failing requests and errors).

Form up to three root-cause hypotheses, most likely first. Each names one candidate service and one mechanism from the list. Reply with JSON:
{"hypotheses": [{"service": "<candidate>", "mechanism": "<mechanism>"}]}
```

Parsing (`parse_hypotheses`): first `{...}` block as JSON; entries with a candidate service, deduplicated,
at most 3. Unknown or missing mechanism for a valid service -> the state_fixed mechanism rule for that
service (its S1 evidence, else its flagged metrics in the whole case). If nothing usable parses -> the
state_fixed hypotheses (`info.plan_used_default = true`). In every completed state_dynamic case of the
start run and iteration 1 the planner reply parsed (0 fallbacks).

Sanity check before the full run: selection only for dev case `ob-4490c7f4fb` (state_fixed: 24 units,
S1 4 / S2 5 / S4 12 / flat fill 3), then one LLM case for state_dynamic (run `dev_20261026T161559Z`, 1 case,
planner JSON parsed). That one-case folder is a sanity check only, not a development observation.

## 2. Start run `dev_20261026T161939Z` (5 methods, 30 dev cases)

| method | role | Avg@5 (95% CI) | AC@1 | AC@3 | RR | failed | strict P | strict R | citation P | doc share |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | comparison | 0.227 [0.113, 0.347] | 0.017 | 0.272 | 0.223 | 0 | - | - | - | - |
| flat | comparison | 0.550 [0.410, 0.687] | 0.283 | 0.600 | 0.476 | 0 | 0.000 | 0.000 | 0.000 | 0.811 |
| role_only | comparison | 0.795 [0.677, 0.902] | 0.636 | 0.825 | 0.752 | 3 | 0.032 | 0.276 | 0.143 | 0.167 |
| state_fixed | proposed | 0.930 [0.853, 0.987] | 0.839 | 0.950 | 0.901 | 2 | 0.122 | 0.981 | 0.438 | 0.372 |
| state_dynamic | reference | 0.855 [0.748, 0.945] | 0.747 | 0.875 | 0.826 | 5 | 0.122 | 0.992 | 0.380 | 0.363 |

Per service (Avg@5):

| method | checkoutservice | currencyservice | emailservice | productcatalogservice | recommendationservice |
|---|---:|---:|---:|---:|---:|
| none | 0.467 | 0.350 | 0.033 | 0.283 | 0.000 |
| flat | 0.350 | 1.000 | 0.000 | 0.867 | 0.533 |
| role_only | 0.550 | 0.875 | 0.833 | 0.875 | 0.842 |
| state_fixed | 0.875 | 0.875 | 1.000 | 0.900 | 1.000 |
| state_dynamic | 0.592 | 0.983 | 0.875 | 0.950 | 0.875 |

Complete cases (no method failed): 22 of 30: none 0.200, flat 0.573, role_only 0.882, state_fixed 0.973, state_dynamic 0.973.

Failures (scored as all candidates tied, frozen rule; all are judge-output failures, the selection never failed):

| method | case | error |
|---|---|---|
| role_only | ob-1ca11ec53c, ob-da45478718, ob-72f4804e8b | RANKING line names no candidate |
| state_fixed | ob-0ed36a9ed3 | No RANKING line (ranking written one name per line without the label) |
| state_fixed | ob-6cf8e0404a | finish_reason=length (ranking degenerated into repeated metric names) |
| state_dynamic | ob-0ed36a9ed3, ob-4643c89835, ob-72f4804e8b | finish_reason=length (repetition loops) |
| state_dynamic | ob-23063f7a6f | No RANKING line |
| state_dynamic | ob-74b7f07db3 | RANKING line names no candidate (label line, then a numbered list) |

Observations (dev):
- state_fixed: the root-cause service was one of the 3 hypotheses in 28 of 28 completed cases; Avg@5 < 1 in
  only 3 completed cases (productcatalogservice delay / loss / mem: recommendationservice or frontend ranked
  above it). Most of the gap to 1.0 is the 2 failed cases (each scored 0.25 instead of ~1).
- state_dynamic: root in hypotheses 25 of 25 completed; the planner adds `frontend` as a hypothesis in most
  cases; 5 judge failures.
- Stage composition of state_fixed over the 28 completed cases: S1 125 units (84 metric, 28 KPI, 13
  trace_error), S2 137 (67 wiki 03, 53 call_graph, 13 wiki 04, 4 wiki 10), S4 328 (109 log_template, 95
  metric, 22 trace_perf + 11 health-check / export trace_perf, 6 health-check log templates, 42 wiki 18, 19
  wiki 24, 16 wiki 19, 7 wiki 11, 1 trace_error), flat fill 82 (58 wiki 11, 24 wiki 24).
- One ranking over all telemetry kinds in S4 puts many normal log templates and health-check traces ahead
  of the service's other flagged metrics (example, case ob-4490c7f4fb: S4 for emailservice picked the
  "send order confirmation email" log template, emailservice_latency-90 and the Health/Check trace).

## 3. Iteration 1 `dev_20261026T174146Z` (state_fixed, state_dynamic; 30 dev cases)

Change: in S4 the hypothesis service's anomaly-marked telemetry (`S4_ANOMALY_KINDS` = flagged `metric`,
`trace_error`) is taken first, ranked by the state query; the rest of the telemetry budget goes to
log_template / trace_perf ranked by the same query. Budgets unchanged.

| method | role | Avg@5 (95% CI) | AC@1 | AC@3 | RR | failed | strict P | strict R | citation P | doc share |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| state_fixed | proposed | 0.965 [0.908, 1.000] | 0.919 | 0.975 | 0.950 | 1 | 0.122 | 1.000 | 0.445 | 0.374 |
| state_dynamic | reference | 0.965 [0.908, 1.000] | 0.919 | 0.975 | 0.950 | 1 | 0.121 | 1.000 | 0.363 | 0.362 |

| method | checkoutservice | currencyservice | emailservice | productcatalogservice | recommendationservice |
|---|---:|---:|---:|---:|---:|
| state_fixed | 0.875 | 0.983 | 1.000 | 0.967 | 1.000 |
| state_dynamic | 1.000 | 0.983 | 1.000 | 0.967 | 0.875 |

Complete cases: 28 of 30: state_fixed 0.989, state_dynamic 0.989.
Failures: state_fixed ob-0ed36a9ed3 (No RANKING line, same case as in the start run);
state_dynamic ob-72f4804e8b (finish_reason=length).

Observations: S4 of state_fixed now holds 115 flagged metrics (was 95) and 98 log templates (was 109);
health-check units 15 (was 17). Completed cases with Avg@5 < 1: currencyservice delay (0.90,
checkoutservice ranked first) and productcatalogservice mem (0.80). Root in hypotheses 29/29 (both methods).

Decision: ADOPTED. state_fixed 30-case mean Avg@5 0.930 -> 0.965; per-service changes
checkoutservice 0.875 -> 0.875, currencyservice 0.875 -> 0.983, emailservice 1.000 -> 1.000,
productcatalogservice 0.900 -> 0.967, recommendationservice 1.000 -> 1.000 (no service drops).
Caveat: of the +0.035, 0.025 comes from case ob-6cf8e0404a, which failed in the start run (length) and
completed with Avg@5 1.0 here; judge format failures change from run to run, so the gain is not clearly
separable from that failure noise.

## 4. Iteration 2 `dev_20261026T181418Z` (state_fixed, state_dynamic; 30 dev cases) - REJECTED

Motivation (iteration 1 observation): about 3 units per case came from the flat fill, all generic wiki 11 /
24 sections, mainly because S1's 3 trace_error slots are unused in most cases (13 trace_error units over
29 cases). Change on top of iteration 1: budget left unused by S1 and S2 is added to S4
(per = (12 + unused) // #hypotheses) instead of going to the flat fill.

| method | role | Avg@5 (95% CI) | AC@1 | AC@3 | RR | failed | strict P | strict R | citation P | doc share |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| state_fixed | proposed | 0.955 [0.898, 0.993] | 0.869 | 0.975 | 0.925 | 1 | 0.121 | 1.000 | 0.376 | 0.290 |
| state_dynamic | reference | 0.993 [0.980, 1.000] | 0.967 | 1.000 | 0.983 | 0 | 0.121 | 1.000 | 0.364 | 0.260 |

| method | checkoutservice | currencyservice | emailservice | productcatalogservice | recommendationservice |
|---|---:|---:|---:|---:|---:|
| state_fixed | 0.967 | 1.000 | 1.000 | 0.933 | 0.875 |
| state_dynamic | 1.000 | 1.000 | 1.000 | 0.967 | 1.000 |

Complete cases: 29 of 30: state_fixed 0.979, state_dynamic 0.993.
Failures: state_fixed ob-fdb7bfa35f (RANKING line names no candidate). state_dynamic none.

Observations: flat fill fell to 28 units (state_fixed) / 7 (state_dynamic); the freed slots in S4 went
mostly to further log templates and trace_perf units, including 29 health-check / export trace_perf units
(iteration 1: 11). Doc share fell from 0.374 to 0.290. state_fixed completed cases with Avg@5 < 1:
checkoutservice delay (0.80; the case that failed twice before now completes), productcatalogservice cpu
(0.80, was 1.0) and mem (0.80).

Decision: REJECTED and reverted. state_fixed mean Avg@5 0.965 -> 0.955 (not an improvement), and
recommendationservice 1.000 -> 0.875 (drop 0.125 > 0.10, caused by the failed case ob-fdb7bfa35f). The
state_dynamic gain (0.965 -> 0.993) does not count for adoption (the rule is defined on state_fixed only).

## 5. Final DEV_V3 design

Start design + iteration 1 (anomaly-marked telemetry first in S4). Budgets: S1 7 (kpi 1, metric 3,
trace_error 3), S2 5 (call_graph 2, wiki 3), S4 12 (3 hypotheses x (3 telemetry + 1 wiki)), flat fill for
the rest; K_DIRECT 24. Development observations for the final design: run `dev_20261026T174146Z`
(state_fixed 0.965 [0.908, 1.000], state_dynamic 0.965 [0.908, 1.000]); the 5-method comparison is the
start run `dev_20261026T161939Z` (start design, before iteration 1).

Notes and limits:
- Judge format failures (no RANKING line, label without names, repetition until max_tokens) differ
  between runs on the same case and evidence design; with 30 cases one failure moves a mean by 0.025. All
  adoption decisions above are within this noise; the CIs of the three runs overlap widely.
- The STATE_DEV_V2 history comments in `task070_direct.py` (its dev numbers) were visible while editing
  the code; no other TASK_070 report, log, analysis file or earlier run was opened.
- Dev runs of this task: `dev_20261026T161559Z` (1-case sanity check, state_dynamic only),
  `dev_20261026T161939Z` (start), `dev_20261026T174146Z` (iteration 1, adopted),
  `dev_20261026T181418Z` (iteration 2, rejected). Each folder has `analysis.json`.
