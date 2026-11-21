#!/usr/bin/env bash
# Auto-detect desktop user (Jules, jules, misi, Misi)
for u in Jules jules misi Misi $(ls -1 /home 2>/dev/null | grep -v 'lost+found'); do
    if [ -d "/home/$u" ]; then
        VNC_USER="$u"
        break
    fi
done

AUTH_FILE="/home/$VNC_USER/.Xauthority"
PASSWD_FILE="/home/$VNC_USER/.vnc/passwd"

# Biztosítjuk a jelszófájl meglétét (alapértelmezett: 1104)
if [ ! -f "$PASSWD_FILE" ] && which x11vnc >/dev/null 2>&1; then
    mkdir -p "/home/$VNC_USER/.vnc"
    x11vnc -storepasswd "1104" "$PASSWD_FILE" >/dev/null 2>&1 || true
    chown -R "$VNC_USER:$VNC_USER" "/home/$VNC_USER/.vnc" 2>/dev/null || true
    chmod 600 "$PASSWD_FILE" 2>/dev/null || true
fi

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
