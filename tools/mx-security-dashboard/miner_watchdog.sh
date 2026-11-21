#!/usr/bin/env bash
# Miner Watchdog — Scans and terminates unauthorized crypto miners
MINERS=("xmrig" "minerd" "cpuminer" "ethminer" "stratum" "nbminer" "t-rex" "gminer" "lolminer")
for m in "${MINERS[@]}"; do
  pkill -9 -f "$m" 2>/dev/null || true
done
