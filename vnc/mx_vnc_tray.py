#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MX VNC Vezérlő & Tálca Indikátor (mx-vnc-server)
Gazda (host) VNC szerver felügyelet, állapotjelző és kliens végpont.
Kompatibilis: Debian 12 / MX Linux 23.6 / KDE Plasma X11
"""

import sys
import os
import re
import socket
import subprocess
import signal
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QFormLayout, QLineEdit, QMessageBox, QFrame
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush
from PyQt5.QtCore import Qt, QTimer, QRectF

LOCK_FILE = "/tmp/mx_vnc_tray.pid"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('1.1.1.1', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            out = subprocess.check_output(["hostname", "-I"], timeout=1).decode().strip()
            return out.split()[0] if out else "127.0.0.1"
        except Exception:
            return "127.0.0.1"

def get_tailscale_ip():
    try:
        out = subprocess.check_output(["tailscale", "ip", "-4"], timeout=1, stderr=subprocess.DEVNULL).decode().strip()
        if out and re.match(r'^\d+\.\d+\.\d+\.\d+$', out):
            return out
    except Exception:
        pass
    return None

def check_server_status():
    """
    Visszatér: (is_listening: bool, pid: int|None, clients: list)
    """
    is_listening = False
    server_pid = None
    clients = []

    # Figyelő port ellenőrzése
    try:
        out = subprocess.check_output(
            ["ss", "-tlpn", "sport = :5900"],
            timeout=1, stderr=subprocess.DEVNULL
        ).decode()
        if "LISTEN" in out:
            is_listening = True
            m = re.search(r'pid=(\d+)', out)
            if m:
                server_pid = int(m.group(1))
    except Exception:
        pass

    # Aktív kapcsolatok ellenőrzése
    try:
        out_estab = subprocess.check_output(
            ["ss", "-tn", "sport = :5900"],
            timeout=1, stderr=subprocess.DEVNULL
        ).decode()
        for line in out_estab.splitlines():
            line = line.strip()
            if line.startswith("ESTAB"):
                parts = line.split()
                if len(parts) >= 5:
                    clients.append(parts[4])
    except Exception:
        pass

    return is_listening, server_pid, clients

def generate_tray_icon(state="listening"):
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Monitor külső káva
    painter.setPen(QPen(QColor(30, 34, 42), 2))
    painter.setBrush(QBrush(QColor(22, 25, 32)))
    painter.drawRoundedRect(4, 6, 56, 40, 5, 5)

    # Belső kijelző felület
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(14, 18, 24)))
    painter.drawRoundedRect(7, 9, 50, 34, 3, 3)

    # Talp
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(55, 60, 70)))
    painter.drawRect(28, 46, 8, 8)
    painter.drawRoundedRect(20, 54, 24, 4, 2, 2)

    # VNC felirat a képernyőn
    font = QFont("SansSerif", 11, QFont.Bold)
    painter.setFont(font)
    painter.setPen(QColor(215, 222, 235))
    painter.drawText(QRectF(7, 9, 50, 34), Qt.AlignCenter, "VNC")

    # Állapotjelző LED (Jobb alsó sarok)
    led_radius = 7
    led_center_x = 52
    led_center_y = 40

    if state == "listening":
        color = QColor(46, 204, 113)  # Élénk zöld (Figyel)
    elif state == "connected":
        color = QColor(52, 152, 219)  # Élénk kék (Csatlakozva)
    else:
        color = QColor(231, 76, 60)   # Élénk piros (Leállítva)

    # Glow effekt
    glow_color = QColor(color.red(), color.green(), color.blue(), 110)
    painter.setBrush(QBrush(glow_color))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(
        int(led_center_x - led_radius - 2),
        int(led_center_y - led_radius - 2),
        int((led_radius + 2) * 2),
        int((led_radius + 2) * 2)
    )

    # Tömör LED
    painter.setBrush(QBrush(color))
    painter.setPen(QPen(QColor(255, 255, 255), 1.5))
    painter.drawEllipse(
        int(led_center_x - led_radius),
        int(led_center_y - led_radius),
        int(led_radius * 2),
        int(led_radius * 2)
    )

    painter.end()
    return QIcon(pixmap)


class VncInfoDialog(QDialog):
    def __init__(self, local_ip, tailscale_ip, port=5900, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MX VNC Kiszolgáló & Kliens Részletek")
        self.setFixedSize(480, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e222b;
                color: #e0e0e0;
                font-family: 'Segoe UI', 'Noto Sans', sans-serif;
            }
            QLabel {
                color: #dcdcdc;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #3c4250;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                color: #5dade2;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #12151b;
                border: 1px solid #3c4250;
                border-radius: 4px;
                padding: 5px 8px;
                color: #2ecc71;
                font-weight: bold;
                font-family: monospace;
                font-size: 13px;
            }
            QPushButton {
                background-color: #2c3e50;
                color: #ffffff;
                border: 1px solid #34495e;
                border-radius: 4px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #34495e;
                border-color: #5dade2;
            }
            QPushButton#actionBtn {
                background-color: #27ae60;
                border-color: #2ecc71;
            }
            QPushButton#actionBtn:hover {
                background-color: #2ecc71;
            }
        """)

        layout = QVBoxLayout(self)

        title_lbl = QLabel("<h2>🖥️ MX VNC Állapot és Csatlakozás</h2>")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        # Hálózati adatok csoport
        net_grp = QGroupBox("Gazda (Host) Csatlakozási Címek")
        f_layout = QFormLayout(net_grp)

        self.lan_edit = QLineEdit(f"{local_ip}:{port}")
        self.lan_edit.setReadOnly(True)
        btn_copy_lan = QPushButton("Másolás")
        btn_copy_lan.clicked.connect(lambda: self.copy_text(self.lan_edit.text()))
        h_lan = QHBoxLayout()
        h_lan.addWidget(self.lan_edit)
        h_lan.addWidget(btn_copy_lan)
        f_layout.addRow("Helyi Hálózat (LAN):", h_lan)

        if tailscale_ip:
            self.tail_edit = QLineEdit(f"{tailscale_ip}:{port}")
            self.tail_edit.setReadOnly(True)
            btn_copy_tail = QPushButton("Másolás")
            btn_copy_tail.clicked.connect(lambda: self.copy_text(self.tail_edit.text()))
            h_tail = QHBoxLayout()
            h_tail.addWidget(self.tail_edit)
            h_tail.addWidget(btn_copy_tail)
            f_layout.addRow("Tailscale VPN:", h_tail)

        self.pwd_edit = QLineEdit("1104")
        self.pwd_edit.setReadOnly(True)
        btn_copy_pwd = QPushButton("Másolás")
        btn_copy_pwd.clicked.connect(lambda: self.copy_text(self.pwd_edit.text()))
        h_pwd = QHBoxLayout()
        h_pwd.addWidget(self.pwd_edit)
        h_pwd.addWidget(btn_copy_pwd)
        f_layout.addRow("VNC Jelszó:", h_pwd)

        layout.addWidget(net_grp)

        # Információs doboz
        info_grp = QGroupBox("Működési Információk")
        i_layout = QVBoxLayout(info_grp)
        info_text = (
            "• <b>Párhuzamos bemenet:</b> A távoli VNC és a helyi fizikai egér/billentyűzet "
            "egyszerre működik, egymás blokkolása nélkül.<br>"
            "• <b>Monitor nélküli üzem:</b> Kizárólag az MX-1 Xeon gazdagép dolgozik monitor nélkül (1080p DP-1 virtuális keret). "
            "Az MX és a Jules gépek fizikai képernyővel rendelkeznek.<br>"
            "• <b>Kliens szoftverek:</b> Másik gépről elérhető Remmina, TigerVNC, TightVNC "
            "vagy RealVNC kliensekkel."
        )
        lbl_info = QLabel(info_text)
        lbl_info.setWordWrap(True)
        i_layout.addWidget(lbl_info)
        layout.addWidget(info_grp)

        # Alsó gombok
        btn_layout = QHBoxLayout()
        btn_remmina = QPushButton("🖥️ Remmina Megnyitása")
        btn_remmina.clicked.connect(self.launch_remmina)
        btn_layout.addWidget(btn_remmina)

        btn_close = QPushButton("Bezárás")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def copy_text(self, text):
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Másolva", f"A vágólapra másolva:\n{text}")

    def launch_remmina(self):
        try:
            subprocess.Popen(["remmina"], start_new_session=True)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Nem sikerült elindítani a Remminát:\n{e}")


class VncTrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.icons = {
            "listening": generate_tray_icon("listening"),
            "connected": generate_tray_icon("connected"),
            "stopped": generate_tray_icon("stopped")
        }

        self.local_ip = get_local_ip()
        self.tailscale_ip = get_tailscale_ip()
        self.port = 5900

        self.current_state = "unknown"
        self.previous_clients = set()

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.icons["listening"])
        self.tray.setVisible(True)

        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #1e222b;
                color: #e0e0e0;
                border: 1px solid #3c4250;
                padding: 4px;
                font-family: 'Segoe UI', 'Noto Sans', sans-serif;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2980b9;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #7f8c8d;
            }
            QMenu::separator {
                height: 1px;
                background: #3c4250;
                margin: 4px 0px;
            }
        """)

        # Fejléc címke
        self.act_header = QAction("🖥️ MX VNC KÖZPONT", self.menu)
        font_hdr = QFont()
        font_hdr.setBold(True)
        self.act_header.setFont(font_hdr)
        self.act_header.setEnabled(False)
        self.menu.addAction(self.act_header)

        # Állapot
        self.act_status = QAction("🟢 Állapot: Figyel (5900)", self.menu)
        self.act_status.setEnabled(False)
        self.menu.addAction(self.act_status)

        self.menu.addSeparator()

        # IP címek másolása
        self.act_copy_lan = QAction(f"🌐 Helyi IP: {self.local_ip}:{self.port}  (Másolás)", self.menu)
        self.act_copy_lan.triggered.connect(lambda: self.copy_to_clip(f"{self.local_ip}:{self.port}"))
        self.menu.addAction(self.act_copy_lan)

        if self.tailscale_ip:
            self.act_copy_tail = QAction(f"🔒 Tailscale: {self.tailscale_ip}:{self.port}  (Másolás)", self.menu)
            self.act_copy_tail.triggered.connect(lambda: self.copy_to_clip(f"{self.tailscale_ip}:{self.port}"))
            self.menu.addAction(self.act_copy_tail)

        # Aktív kapcsolatok
        self.act_clients = QAction("👥 Kapcsolatok: 0 aktív kliens", self.menu)
        self.act_clients.setEnabled(False)
        self.menu.addAction(self.act_clients)

        self.menu.addSeparator()

        # Kliens opciók - Kölcsönös távvezérlés (mx, mx-1, jules)
        self.conn_menu = self.menu.addMenu("🚀 Csatlakozás másik géphez...")
        
        act_conn_auto = QAction("⚡ Automatikus partner (LAN / Tailscale)", self.conn_menu)
        font_conn = QFont()
        font_conn.setBold(True)
        act_conn_auto.setFont(font_conn)
        act_conn_auto.triggered.connect(lambda: self.launch_peer_connect())
        self.conn_menu.addAction(act_conn_auto)

        self.conn_menu.addSeparator()

        is_mx = (self.local_ip == "192.168.1.106" or self.tailscale_ip == "100.95.215.75")
        is_mx1 = (self.local_ip == "192.168.1.105" or self.tailscale_ip == "100.118.197.74")
        is_jules = (self.local_ip == "192.168.1.104" or self.tailscale_ip == "100.77.191.66")

        lbl_mx = "🖥️ MX Másik Gép (192.168.1.106 / 100.95.215.75)" + (" [Ez a helyi gép]" if is_mx else "")
        act_conn_mx = QAction(lbl_mx, self.conn_menu)
        act_conn_mx.triggered.connect(lambda: self.launch_peer_connect("mx"))
        if is_mx:
            act_conn_mx.setEnabled(False)
        self.conn_menu.addAction(act_conn_mx)

        lbl_mx1 = "🚀 MX-1 Xeon Gazdagép (192.168.1.105 / 100.118.197.74)" + (" [Ez a helyi gép]" if is_mx1 else "")
        act_conn_mx1 = QAction(lbl_mx1, self.conn_menu)
        act_conn_mx1.triggered.connect(lambda: self.launch_peer_connect("mx1"))
        if is_mx1:
            act_conn_mx1.setEnabled(False)
        self.conn_menu.addAction(act_conn_mx1)

        lbl_jules = "☁️ Jules Munkaállomás (192.168.1.104 / 100.77.191.66)" + (" [Ez a helyi gép]" if is_jules else "")
        act_conn_jules = QAction(lbl_jules, self.conn_menu)
        act_conn_jules.triggered.connect(lambda: self.launch_peer_connect("jules"))
        if is_jules:
            act_conn_jules.setEnabled(False)
        self.conn_menu.addAction(act_conn_jules)

        self.act_remmina = QAction("🖥️ Remmina VNC/RDP Kezelő indítása...", self.menu)
        self.act_remmina.triggered.connect(self.launch_remmina)
        self.menu.addAction(self.act_remmina)

        self.act_vncviewer = QAction("⚡ TigerVNC Kézi kapcsolódás...", self.menu)
        self.act_vncviewer.triggered.connect(self.launch_vncviewer)
        self.menu.addAction(self.act_vncviewer)

        self.menu.addSeparator()

        # Gazda szerver vezérlés
        self.act_toggle_server = QAction("⏹️ VNC Szerver leállítása", self.menu)
        self.act_toggle_server.triggered.connect(self.toggle_server)
        self.menu.addAction(self.act_toggle_server)

        self.act_restart_server = QAction("🔄 VNC Szerver újraindítása", self.menu)
        self.act_restart_server.triggered.connect(self.restart_server)
        self.menu.addAction(self.act_restart_server)

        self.act_info = QAction("ℹ️ Csatlakozási adatok (Jelszó, Port)...", self.menu)
        self.act_info.triggered.connect(self.show_info_dialog)
        self.menu.addAction(self.act_info)

        self.menu.addSeparator()

        self.act_quit = QAction("❌ Tálcaikon bezárása", self.menu)
        self.act_quit.triggered.connect(self.quit_app)
        self.menu.addAction(self.act_quit)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_activated)

        # Periodikus ellenőrző időzítő (2 másodpercenként)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(2000)

        # Kezdeti állapotfrissítés
        self.update_status()

        # Ha nem fut a szerver, elindítjuk automatikusan a háttérben
        is_listening, _, _ = check_server_status()
        if not is_listening:
            self.start_server()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_info_dialog()

    def copy_to_clip(self, text):
        QApplication.clipboard().setText(text)
        self.tray.showMessage(
            "Vágólapra másolva",
            f"{text}",
            QSystemTrayIcon.Information,
            2000
        )

    def launch_peer_connect(self, target=None):
        try:
            cmd = ["/usr/bin/mx-vnc-connect"]
            if target:
                cmd.append(target)
            if os.path.exists(cmd[0]):
                subprocess.Popen(cmd, start_new_session=True)
            else:
                self.launch_vncviewer()
        except Exception as e:
            self.tray.showMessage("Hiba", f"Kapcsolódás nem indítható: {e}", QSystemTrayIcon.Warning)

    def launch_remmina(self):
        try:
            subprocess.Popen(["remmina"], start_new_session=True)
        except Exception as e:
            self.tray.showMessage("Hiba", f"Remmina nem indítható: {e}", QSystemTrayIcon.Warning)

    def launch_vncviewer(self):
        try:
            subprocess.Popen(["vncviewer"], start_new_session=True)
        except Exception as e:
            self.tray.showMessage("Hiba", f"TigerVNC nem indítható: {e}", QSystemTrayIcon.Warning)

    def start_server(self):
        if os.path.exists("/etc/init.d/x11vnc"):
            subprocess.run(["sudo", "-n", "/etc/init.d/x11vnc", "start"], stderr=subprocess.DEVNULL)
        elif os.path.exists("/usr/local/bin/x11vnc-service.sh"):
            subprocess.Popen(["/usr/local/bin/x11vnc-service.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.tray.showMessage("VNC Kiszolgáló", "x11vnc kiszolgáló indítása folyamatban...", QSystemTrayIcon.Information, 2000)
        self.update_status()

    def stop_server(self):
        if os.path.exists("/etc/init.d/x11vnc"):
            subprocess.run(["sudo", "-n", "/etc/init.d/x11vnc", "stop"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "x11vnc.*5900"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "x11vnc-service.sh"], stderr=subprocess.DEVNULL)
        self.tray.showMessage("VNC Kiszolgáló", "x11vnc kiszolgáló leállítva.", QSystemTrayIcon.Warning, 2000)
        self.update_status()

    def restart_server(self):
        if os.path.exists("/etc/init.d/x11vnc"):
            subprocess.run(["sudo", "-n", "/etc/init.d/x11vnc", "restart"], stderr=subprocess.DEVNULL)
        else:
            self.stop_server()
            self.start_server()
        self.tray.showMessage("VNC Kiszolgáló", "x11vnc kiszolgáló újraindítva.", QSystemTrayIcon.Information, 2000)
        self.update_status()

    def toggle_server(self):
        is_listening, _, _ = check_server_status()
        if is_listening:
            self.stop_server()
        else:
            self.start_server()

    def show_info_dialog(self):
        dlg = VncInfoDialog(self.local_ip, self.tailscale_ip, self.port)
        dlg.exec_()

    def update_status(self):
        is_listening, pid, clients = check_server_status()
        client_set = set(clients)

        # Csatlakozási értesítések
        new_conns = client_set - self.previous_clients
        if new_conns:
            for c in new_conns:
                self.tray.showMessage(
                    "🔵 Új VNC Kapcsolat",
                    f"Távoli kliens csatlakozott:\n{c}",
                    QSystemTrayIcon.Information,
                    4000
                )

        if self.previous_clients and not client_set and is_listening:
            self.tray.showMessage(
                "⚪ VNC Kapcsolat Lezárult",
                "A távoli kliens bontotta a kapcsolatot.",
                QSystemTrayIcon.Information,
                3000
            )

        self.previous_clients = client_set

        # Állapot meghatározása
        if not is_listening:
            state = "stopped"
            status_text = "🔴 Állapot: Leállítva"
            self.act_toggle_server.setText("▶️ VNC Szerver elindítása")
            tooltip_status = "LEÁLLÍTVA"
        elif len(clients) > 0:
            state = "connected"
            status_text = f"🔵 Állapot: Csatlakozva ({len(clients)} kliens)"
            self.act_toggle_server.setText("⏹️ VNC Szerver leállítása")
            tooltip_status = f"AKTÍV ({len(clients)} kliens csatlakozva)"
        else:
            state = "listening"
            status_text = "🟢 Állapot: Figyel (:5900)"
            self.act_toggle_server.setText("⏹️ VNC Szerver leállítása")
            tooltip_status = "FIGYEL (Várakozás kapcsolatra)"

        # Ikon frissítése ha változott
        if state != self.current_state:
            self.tray.setIcon(self.icons[state])
            self.current_state = state

        # Menü szövegek frissítése
        self.act_status.setText(status_text)
        client_desc = ", ".join(clients) if clients else "Nincs aktív kliens"
        self.act_clients.setText(f"👥 Kapcsolatok: {client_desc}")

        # Tooltip frissítése
        tip = (
            f"MX VNC Központ\n"
            f"Állapot: {tooltip_status}\n"
            f"Port: {self.port}\n"
            f"LAN IP: {self.local_ip}:{self.port}"
        )
        if self.tailscale_ip:
            tip += f"\nTailscale: {self.tailscale_ip}:{self.port}"
        if clients:
            tip += f"\nKliens: {', '.join(clients)}"
        self.tray.setToolTip(tip)

    def quit_app(self):
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass
        self.app.quit()

    def run(self):
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        return self.app.exec_()


def main():
    # Szignálok kezelése (pl. kill szignál esetén tiszta kilépés)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    # PID ellenőrzés
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            # Ellenőrizzük, él-e még
            os.kill(old_pid, 0)
            print(f"MX VNC Tray már fut (PID: {old_pid}). Kilépés.")
            sys.exit(0)
        except (OSError, ValueError):
            pass

    app = VncTrayApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
