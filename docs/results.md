# Historical results and limitations

The following results motivated this package. They were produced by frozen
predecessor workflows in longDS-codex, not by version 0.1.0.dev0 of this package.
Both cases concern `business/netflix_movies_and_tv_shows/task2` with 34 successive
requests. Each row's denominator is that experiment's 34 actual final replies.

## Single-task comparison

| Workflow | Correct replies | Accuracy |
|---|---:|---:|
| Native | 13/34 | 38.24% |
| StateM Parquet analysis workflow | 27/34 | 79.41% |

Actor: gpt-6-luna, xhigh. Judge: ocg/deepseek-v4.1-flash, max, using the official
prompt. Both arms completed and were scored for all 34 turns, with zero scoring
failures. The observed difference is 14 correct replies, or 41.18 percentage
points. Budgets were not aligned, each arm has one trajectory, and turns are
dependent. This is not evidence of a general or purely state-structure effect.
Some diagnostic-prefix judgments changed during full scoring of unchanged
answers; the full formal result is the reported one.

## Development iteration

| Workflow snapshot | Correct replies | Accuracy |
|---|---:|---:|
| Initial Parquet retention approach | 1/34 | 2.94% |
| Adopted binding-oriented version | 29/34 | 85.29% |

The adopted actor commit was `54bf4fbeb8852286ba54021df96b114602253fd1`.
Actor and judge used ocg/deepseek-v4.1-flash, max. The developer inspected this
task's reference answers/code and scoring while modifying actor-visible rules.
This is **reference-informed development on the same task**, not an independent
held-out comparison against Native. The initial retention approach was itself
an earlier workflow variant, not Native Codex.

The adopted version separated entity membership, current measurements and
historical baselines, and supplied rank, grouping-weight and membership helpers.
Later iterations also regressed. A same-answer regrade produced 30/34 because
one judgment changed; the original 29/34 remains the primary reported result.

## Broader context

A separate 24-task, 777-turn Luna comparison reported Native 494/777 (63.58%)
and StateM 507/777 (65.25%) using a 642-turn regrade plus the existing 135-turn
Business scores. Another preserved scoring version was 510/777 (65.64%).
These are not two independent generations. Settings and code differed, StateM
mixed Standard/Fast, and gains were concentrated in Business; other domains
included regressions. The 507/777 figure is not a uniform full-777 regrade.

## Evidence availability

[Historical snapshots](../evidence/netflix-task2/snapshots.json) record counts,
run identities and hashes of source documents. They are curated summaries, not
a substitute for an independently accessible complete reproduction package.
Raw datasets, benchmark reference solutions, credentials and full transcripts
are not bundled in this source release. Public evidence export and dataset
access instructions remain a subsequent release task.

For a new evaluation, freeze the package, Skill, model, Codex CLI, data inputs,
judge prompt, budget and settings. Score actual final replies. Keep development
tasks identified, use untouched tasks and repetitions, and report coverage,
generation failures, scoring failures, time and token cost alongside accuracy.
