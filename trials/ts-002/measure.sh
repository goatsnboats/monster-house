#!/usr/bin/env bash
# TS-002: run one trial command, then sample its CPU use and memory from /proc
# between 5 s and 25 s. Usage: measure.sh <label> <command...>
label=$1; shift
"$@" > /tmp/ts002-measure-$label.log 2>&1 &
pid=$!
sleep 5
read -r u1 s1 < <(awk '{print $14, $15}' /proc/$pid/stat)
t1=$(date +%s.%N); peak=0
for i in $(seq 1 20); do
  rss=$(awk '/VmRSS/ {print $2}' /proc/$pid/status 2>/dev/null || echo 0)
  [ "${rss:-0}" -gt "$peak" ] && peak=$rss
  sleep 1
done
read -r u2 s2 < <(awk '{print $14, $15}' /proc/$pid/stat)
t2=$(date +%s.%N)
hz=$(getconf CLK_TCK)
cpu=$(echo "scale=1; 100 * (($u2 + $s2) - ($u1 + $s1)) / $hz / ($t2 - $t1)" | bc)
wait $pid
echo "$label: cpu=${cpu}% of one core, peak_rss=$((peak / 1024)) MB | $(grep -E '^\{|"frames"' /tmp/ts002-measure-$label.log | tail -1)"
