#!/usr/bin/env bash
# Run a CI step. If it fails, publish the end of its output as an error
# annotation, which is readable on the run page without signing in.
# Usage: run_step.sh "Step name" command [args...]
name="$1"
shift
log="$(mktemp)"
"$@" >"$log" 2>&1
code=$?
cat "$log"
if [ "$code" -ne 0 ]; then
  message="$(tail -n 60 "$log" | python -c "import sys; print(sys.stdin.read().replace('%', '%25').replace('\r', '').replace('\n', '%0A'))")"
  echo "::error title=${name} failed (exit ${code})::${message}"
fi
exit "$code"
