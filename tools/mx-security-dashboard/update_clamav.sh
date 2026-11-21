#!/usr/bin/env bash
# ClamAV Signature Updater
/usr/bin/freshclam --quiet 2>/dev/null || true
