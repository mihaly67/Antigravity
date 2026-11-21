#!/usr/bin/env bash
# Non-interactive ClamAV engine upgrade
export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get install --only-upgrade -y clamav clamav-daemon clamav-freshclam
