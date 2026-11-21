#!/usr/bin/env bash
# Auto-detect desktop user (misi or Misi)
if [ -d "/home/misi" ]; then
    VNC_USER="misi"
elif [ -d "/home/Misi" ]; then
    VNC_USER="Misi"
else
    VNC_USER=$(ls -1 /home | head -n 1)
fi

AUTH_FILE="/home/$VNC_USER/.Xauthority"
PASSWD_FILE="/home/$VNC_USER/.vnc/passwd"

while true; do
    if [ -e /tmp/.X11-unix/X0 ] && [ -f "$AUTH_FILE" ] && [ -f "$PASSWD_FILE" ]; then
        if ! ss -tlpn 'sport = :5900' 2>/dev/null | grep -q LISTEN; then
            /usr/bin/x11vnc \
                -display :0 \
                -auth "$AUTH_FILE" \
                -rfbauth "$PASSWD_FILE" \
                -forever \
                -shared \
                -repeat \
                -noxdamage \
                -rfbport 5900
        fi
    fi
    sleep 3
done
