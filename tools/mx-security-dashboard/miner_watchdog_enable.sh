#!/usr/bin/env bash
# Enable Miner Watchdog cron job
echo '* * * * * root /usr/local/bin/miner_watchdog.sh' > /etc/cron.d/miner_watchdog
chmod 644 /etc/cron.d/miner_watchdog
