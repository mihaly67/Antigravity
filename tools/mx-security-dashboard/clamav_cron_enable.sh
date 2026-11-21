#!/usr/bin/env bash
# Enable ClamAV 4-hour automatic update cron job
echo '0 */4 * * * root /usr/local/bin/update_clamav.sh' > /etc/cron.d/update_clamav
chmod 644 /etc/cron.d/update_clamav
