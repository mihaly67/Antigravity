#!/usr/bin/env bash
# MX VNC Server & Tray Debian Csomagkészítő Szkript
# Verzió: 1.1.0 (Kölcsönös háromgépes távvezérlés: mx, mx-1, jules)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGE_DIR="$REPO_ROOT/packages"
BUILD_DIR="/tmp/mx-vnc-build"

echo "=== MX VNC Server 1.1.0 .deb csomag készítése ==="
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/local/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$BUILD_DIR/etc/init.d"
mkdir -p "$BUILD_DIR/etc/xdg/autostart"
mkdir -p "$BUILD_DIR/etc/sudoers.d"
mkdir -p "$BUILD_DIR/etc/X11/xorg.conf.d"
mkdir -p "$PACKAGE_DIR"

# Fájlok másolása
cp "$SCRIPT_DIR/mx-vnc-server" "$BUILD_DIR/usr/bin/"
cp "$SCRIPT_DIR/mx_vnc_tray.py" "$BUILD_DIR/usr/bin/"
cp "$SCRIPT_DIR/mx-vnc-connect" "$BUILD_DIR/usr/bin/"
cp "$SCRIPT_DIR/x11vnc-service.sh" "$BUILD_DIR/usr/local/bin/"
cp "$SCRIPT_DIR/x11vnc.init" "$BUILD_DIR/etc/init.d/x11vnc"
cp "$SCRIPT_DIR/mx-vnc-server.sudoers" "$BUILD_DIR/etc/sudoers.d/mx-vnc-server"
cp "$SCRIPT_DIR/mx-vnc-server.desktop" "$BUILD_DIR/usr/share/applications/"
cp "$SCRIPT_DIR/mx-vnc-connect.desktop" "$BUILD_DIR/usr/share/applications/"
cp "$SCRIPT_DIR/mx-vnc-server.desktop" "$BUILD_DIR/etc/xdg/autostart/"
cp "$SCRIPT_DIR/mx-vnc-server.svg" "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/"
cp "$SCRIPT_DIR/10-monitor.conf" "$BUILD_DIR/etc/X11/xorg.conf.d/"

# Jogosultságok beállítása
chmod 755 "$BUILD_DIR/usr/bin/"*
chmod 755 "$BUILD_DIR/usr/local/bin/"*
chmod 755 "$BUILD_DIR/etc/init.d/x11vnc"
chmod 644 "$BUILD_DIR/usr/share/applications/"*
chmod 644 "$BUILD_DIR/etc/xdg/autostart/"*
chmod 644 "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/"*
chmod 440 "$BUILD_DIR/etc/sudoers.d/mx-vnc-server"

# DEBIAN/control
cat << 'EOF' > "$BUILD_DIR/DEBIAN/control"
Package: mx-vnc-server
Version: 1.1.0
Architecture: all
Maintainer: Jules <jules@localhost>
Depends: python3, python3-pyqt5, x11vnc, tigervnc-viewer, netcat-traditional | netcat-openbsd | netcat, iproute2
Section: net
Priority: optional
Description: MX VNC Server & Tray Controller
 Complete VNC server with SysVinit supervisor, system tray controller,
 and auto-failover remote desktop connector for mx, mx-1 and jules nodes.
EOF

# DEBIAN/postinst
cat << 'EOF' > "$BUILD_DIR/DEBIAN/postinst"
#!/bin/bash
set -e

# Sudoers jogosultságok
if [ -f /etc/sudoers.d/mx-vnc-server ]; then
    chown root:root /etc/sudoers.d/mx-vnc-server
    chmod 0440 /etc/sudoers.d/mx-vnc-server
fi

# SysVinit szolgáltatás aktiválása runlevel 2,3,4,5-ön
chmod 755 /etc/init.d/x11vnc 2>/dev/null || true
chmod 755 /usr/local/bin/x11vnc-service.sh 2>/dev/null || true
update-rc.d x11vnc defaults 2>/dev/null || true

# Asztali parancsikon kitelepítése a felhasználóknak
for u_home in /home/*; do
    if [ -d "$u_home/Asztal" ]; then
        cp -f /usr/share/applications/mx-vnc-connect.desktop "$u_home/Asztal/mx-vnc-connect.desktop"
        chmod +x "$u_home/Asztal/mx-vnc-connect.desktop"
        user_name=$(basename "$u_home")
        chown "$user_name:$user_name" "$u_home/Asztal/mx-vnc-connect.desktop" 2>/dev/null || true
    fi
done

# Alapértelmezett VNC jelszó (1104) biztosítása
for u_home in /home/*; do
    if [ -d "$u_home" ]; then
        mkdir -p "$u_home/.vnc"
        if [ ! -f "$u_home/.vnc/passwd" ] && which x11vnc >/dev/null 2>&1; then
            x11vnc -storepasswd "1104" "$u_home/.vnc/passwd" >/dev/null 2>&1 || true
            user_name=$(basename "$u_home")
            chown -R "$user_name:$user_name" "$u_home/.vnc" 2>/dev/null || true
            chmod 600 "$u_home/.vnc/passwd" 2>/dev/null || true
        fi
    fi
done

# Szolgáltatás újraindítása
service x11vnc restart 2>/dev/null || /etc/init.d/x11vnc restart 2>/dev/null || true

exit 0
EOF

# DEBIAN/prerm
cat << 'EOF' > "$BUILD_DIR/DEBIAN/prerm"
#!/bin/sh
pkill -f mx_vnc_tray.py 2>/dev/null || true
service x11vnc stop 2>/dev/null || /etc/init.d/x11vnc stop 2>/dev/null || true
exit 0
EOF

# DEBIAN/postrm
cat << 'EOF' > "$BUILD_DIR/DEBIAN/postrm"
#!/bin/sh
if [ "$1" = "purge" ]; then
    update-rc.d -f x11vnc remove 2>/dev/null || true
    rm -f /etc/sudoers.d/mx-vnc-server
    for u_home in /home/*; do
        rm -f "$u_home/Asztal/mx-vnc-connect.desktop"
    done
fi
exit 0
EOF

chmod 755 "$BUILD_DIR/DEBIAN/postinst" "$BUILD_DIR/DEBIAN/prerm" "$BUILD_DIR/DEBIAN/postrm"

# Csomag összeállítása
OUT_DEB="$PACKAGE_DIR/mx-vnc-server_1.1.0_all.deb"
dpkg-deb --root-owner-group --build "$BUILD_DIR" "$OUT_DEB"
echo "✅ Csomag sikeresen elkészült: $OUT_DEB"
dpkg -c "$OUT_DEB"
