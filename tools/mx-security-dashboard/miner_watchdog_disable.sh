#!/usr/bin/env bash
# Disable Miner Watchdog cron job
rm -f /etc/cron.d/miner_watchdog
pkill -9 -f miner_watchdog.sh 2>/dev/null || true
