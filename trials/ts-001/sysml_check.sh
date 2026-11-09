#!/usr/bin/env bash
# Validate SysML v2 text files with the OMG pilot implementation (TS-001 trial).
# Usage: SYSML_KERNEL=<dir holding jupyter-sysml-kernel-*-all.jar and sysml.library> sysml_check.sh FILE... [-- %command...]
# The kernel comes from github.com/Systems-Modeling/SysML-v2-Pilot-Implementation releases
# (jupyter-sysml-kernel-0.63.1.zip, release 2026-09.1). It is not part of the repo.
# Safety: input always ends with %exit, output is capped at 200 KB, and the run times out after 300 s.
# (A run without %exit loops forever at end of input and once wrote a 12 GB log.)
set -uo pipefail
K="${SYSML_KERNEL:?set SYSML_KERNEL}"
files=(); cmds=()
while [[ $# -gt 0 && "$1" != "--" ]]; do files+=("$1"); shift; done
[[ "${1:-}" == "--" ]] && shift && cmds=("$@")
# The REPL reads a blank line as the end of one input, so each file goes in as one blank-line-free chunk.
input=$(for f in "${files[@]}"; do grep -v '^[[:space:]]*$' "$f"; echo; done; for c in "${cmds[@]}"; do echo "$c"; echo; done; echo "%exit")
out=$(printf '%s\n' "$input" | timeout 300 java -cp "$K"/jupyter-sysml-kernel-*-all.jar \
      org.omg.sysml.interactive.SysMLInteractive "$K/sysml.library/" 2>&1 | head -c 200000)
printf '%s\n' "$out" | grep -vE '^(Reading |log4j:)'
if printf '%s\n' "$out" | grep -qE 'ERROR|Exception'; then echo "SYSML CHECK: FAIL"; exit 1; fi
echo "SYSML CHECK: OK"
