#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
validation_dir="$(mktemp -d "${TMPDIR:-/tmp}/analysis-state-validation.XXXXXX")"
cas_python="${CAS_PYTHON:-python3}"
echo "Validation directory: $validation_dir"
"$cas_python" -m venv "$validation_dir/build-env"
"$validation_dir/build-env/bin/python" -m pip install 'build>=1.2' 'PyYAML>=6'
"$validation_dir/build-env/bin/python" "$repo_dir/scripts/check_release_files.py"
"$validation_dir/build-env/bin/python" -m build "$repo_dir" --outdir "$validation_dir/dist"
"$cas_python" -m venv "$validation_dir/runtime-env"
"$validation_dir/runtime-env/bin/python" -m pip install "$validation_dir"/dist/*.whl

cd "$validation_dir"
"$validation_dir/runtime-env/bin/python" -m unittest discover -s "$repo_dir/tests" -v
"$validation_dir/runtime-env/bin/analysis-state" demo "$validation_dir/example" > "$validation_dir/demo.json"
"$validation_dir/runtime-env/bin/python" -m pip freeze > "$validation_dir/dependencies.txt"
"$validation_dir/runtime-env/bin/python" --version
git -C "$repo_dir" rev-parse HEAD > "$validation_dir/source-commit.txt"
echo "PASS: clean wheel install, behavioral tests, and three-turn demo. Evidence: $validation_dir"
