#!/usr/bin/env bash
set -euo pipefail

# Antigravity Repository Auto-Sync Daemon
# Repo: https://github.com/mihaly67/Antigravity
INTERVAL=600 # 10 perc
REPO_DIR="/home/misi/Antigravity"

sync_sources() {
  # 1. Conky szinkronizáció
  if [ -d "/home/misi/.conky/MX-KoO" ]; then
    mkdir -p "$REPO_DIR/conky/MX-KoO"
    cp -u /home/misi/.conky/MX-KoO/* "$REPO_DIR/conky/MX-KoO/" 2>/dev/null || true
  fi

  # 2. Rendszer segédeszközök szinkronizációja
  mkdir -p "$REPO_DIR/tools/mx-hardware-monitor" \
           "$REPO_DIR/tools/mx-ssh-monitor" \
           "$REPO_DIR/tools/mx-security-dashboard" \
           "$REPO_DIR/tools/mx-ram-cleaner" \
           "$REPO_DIR/tools/mx-cpu-gpu-stress-test"

  [ -f "/usr/bin/hardware_monitor_v2.py" ] && cp -u /usr/bin/hardware_monitor_v2.py /usr/bin/mx-hardware-monitor "$REPO_DIR/tools/mx-hardware-monitor/" 2>/dev/null || true
  [ -f "/etc/xdg/autostart/mx-hardware-monitor.desktop" ] && cp -u /etc/xdg/autostart/mx-hardware-monitor.desktop "$REPO_DIR/tools/mx-hardware-monitor/" 2>/dev/null || true

  [ -f "/usr/bin/ssh_tailscale_monitor.py" ] && cp -u /usr/bin/ssh_tailscale_monitor.py /usr/bin/mx-ssh-monitor "$REPO_DIR/tools/mx-ssh-monitor/" 2>/dev/null || true
  [ -f "/usr/share/applications/mx-ssh-monitor.desktop" ] && cp -u /usr/share/applications/mx-ssh-monitor.desktop "$REPO_DIR/tools/mx-ssh-monitor/" 2>/dev/null || true

  [ -f "/usr/bin/security_dashboard.py" ] && cp -u /usr/bin/security_dashboard.py /usr/bin/mx-security-dashboard "$REPO_DIR/tools/mx-security-dashboard/" 2>/dev/null || true
  [ -f "/etc/xdg/autostart/mx-security-dashboard.desktop" ] && cp -u /etc/xdg/autostart/mx-security-dashboard.desktop "$REPO_DIR/tools/mx-security-dashboard/" 2>/dev/null || true

  [ -f "/usr/bin/jules_ram_cleaner.py" ] && cp -u /usr/bin/jules_ram_cleaner.py /usr/bin/mx-ram-cleaner "$REPO_DIR/tools/mx-ram-cleaner/" 2>/dev/null || true
  [ -f "/usr/share/applications/mx-ram-cleaner.desktop" ] && cp -u /usr/share/applications/mx-ram-cleaner.desktop "$REPO_DIR/tools/mx-ram-cleaner/" 2>/dev/null || true

  [ -f "/usr/bin/jules_cpu_stress_test.py" ] && cp -u /usr/bin/jules_cpu_stress_test.py /usr/bin/mx-cpu-gpu-stress-test "$REPO_DIR/tools/mx-cpu-gpu-stress-test/" 2>/dev/null || true
  [ -f "/usr/share/applications/mx-cpu-gpu-stress-test.desktop" ] && cp -u /usr/share/applications/mx-cpu-gpu-stress-test.desktop "$REPO_DIR/tools/mx-cpu-gpu-stress-test/" 2>/dev/null || true

  # 3. Telepítő (.deb) csomagok másolása
  mkdir -p "$REPO_DIR/packages"
  if compgen -G "/home/misi/Letöltések/*.deb" > /dev/null; then
    cp -u /home/misi/Letöltések/*.deb "$REPO_DIR/packages/" 2>/dev/null || true
  fi

  # 4. Rendszer szkriptek
  mkdir -p "$REPO_DIR/scripts"
  [ -f "/etc/init.d/tailscaled" ] && cp -u /etc/init.d/tailscaled "$REPO_DIR/scripts/tailscaled.init" 2>/dev/null || true
  cp -u "$0" "$REPO_DIR/scripts/git-autopush.sh" 2>/dev/null || true
}

run_once() {
  if [ -d "$REPO_DIR/.git" ]; then
    sync_sources
    cd "$REPO_DIR"
    if [ -n "$(git status --porcelain)" ]; then
      git add -A
      git commit -m "auto(sync): $(date '+%Y-%m-%d %H:%M:%S')"
      git pull --rebase origin main || true
      git push origin main || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] Push nem sikerült: $REPO_DIR"
    fi
  fi
}

if [[ "${1:-}" == "--daemon" || "${1:-}" == "-d" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] git-autopush daemon elindítva az Antigravity repóhoz (intervallum: ${INTERVAL}s)"
  while true; do
    run_once
    sleep "$INTERVAL"
  done
else
  run_once
fi
