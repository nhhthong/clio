#!/usr/bin/env bash
# selftest.sh — every clio-test.sh selftest, each on its own throwaway repo. Prints OK or what failed.
cd "$(dirname "$0")" || exit 1
bad=0
for f in selftest-gate.sh selftest-red.sh selftest-batch.sh; do
  out=$(bash "$f" 2>&1)
  if [ "$(tail -1 <<<"$out")" = OK ]; then continue; fi
  echo "== $f"; echo "$out"; bad=1
done
[ $bad -eq 0 ] && echo OK
exit $bad
