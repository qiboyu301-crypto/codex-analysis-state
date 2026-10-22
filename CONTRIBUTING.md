# Contributing

Start with the README example and report what you expected, what happened, the
package/Python/Codex versions, and the smallest synthetic input that reproduces
the issue. Remove private data and credentials from shared logs.

Keep contributions focused on reproducible analysis behavior. Useful work
includes installation fixes, historical-set examples, tests for definition
inheritance, and clearer explanations of actual failure cases. Preserve raw
precision and score actual agent replies when evaluating a model.

Before proposing a protocol change, show the request and computation that need
it. Use ordinary Python and small explicit functions. Avoid adding generic
frameworks or fallback behavior without a demonstrated need.

Validation command:

```sh
bash scripts/validate_release.sh
```

It installs from a built wheel in a clean environment and exercises meaningful
success/failure paths without model calls. Model experiments are a separate,
explicit activity; record their conditions, costs, coverage and failures.

Retain third-party notices. Identify changes to vendored code explicitly and
update PROVENANCE.json if its pinned source changes. The initial maintainer is
the repository owner, qiboyu301-crypto; use repository issues and pull requests
for project discussion.
