#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import glob
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QLabel, QPushButton, QHBoxLayout, QTextEdit, QComboBox, QTabWidget, QCheckBox)
from PyQt5.QtCore import Qt, QProcess, QDir, QProcessEnvironment
from PyQt5.QtGui import QFont, QIcon, QTextCursor
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

HEAVEN_SEARCH_PATHS = [
    "/home/Jules/HardverMonitor_dev/heaven/heaven",
    "/home/Jules/HardverMonitor_dev/heaven/Unigine_Heaven-4.0/heaven",
    "/opt/Unigine_Heaven-4.0/heaven",
    "/opt/unigine/Unigine_Heaven-4.0/heaven",
    "/usr/local/Unigine_Heaven-4.0/heaven",
    os.path.expanduser("~/Unigine_Heaven-4.0/heaven"),
]
HEAVEN_WRAPPER = "/usr/bin/unigine-heaven"


class CPUGPUStressApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MX CPU & GPU Stressz Teszt")
        self.setMinimumSize(850, 620)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QLabel { color: white; }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #475569; color: #94a3b8; }
            QComboBox, QCheckBox {
                background-color: #1e293b;
                color: white;
                border: 1px solid #334155;
                padding: 6px;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #000000;
                color: #22c55e;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #334155;
            }
            QTabWidget::pane { border: 1px solid #334155; }
            QTabBar::tab {
                background: #1e293b;
                color: white;
                padding: 10px 20px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected { background: #3b82f6; }
        """)

        icon_path = "/usr/share/icons/oxygen/base/128x128/apps/utilities-system-monitor.png"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("utilities-system-monitor"))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        title_label = QLabel("MX CPU & GPU Stressz Teszt")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        main_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.setup_cpu_tab()
        self.setup_gpu_tab()

    def setup_cpu_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.cpu_status_label = QLabel("Állapot: Készen áll")
        self.cpu_status_label.setStyleSheet("color: #22c55e; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.cpu_status_label, alignment=Qt.AlignCenter)

        cpu_select_layout = QHBoxLayout()
        cpu_select_label = QLabel("Teszt profil:")
        self.cpu_type_combo = QComboBox()
        self.cpu_type_combo.addItems([
            "1. Maximális CPU terhelés (Matrix szorzás, minden szál — stress-ng)",
            "2. Lebegőpontos & Memória stressz (FFT + 8GB RAM — stress-ng)",
            "3. Rendszer összetett terhelés (Minden algoritmus ciklikusan — stress-ng)",
            "4. Prime95 Torture Test (mprime, ha telepítve van)"
        ])
        cpu_select_layout.addWidget(cpu_select_label)
        cpu_select_layout.addWidget(self.cpu_type_combo, 1)
        layout.addLayout(cpu_select_layout)

        self.cpu_console = QTextEdit()
        self.cpu_console.setReadOnly(True)
        layout.addWidget(self.cpu_console)

        btn_layout = QHBoxLayout()
        self.cpu_start_btn = QPushButton("CPU Teszt Indítása")
        self.cpu_stop_btn = QPushButton("Leállítás")
        self.cpu_stop_btn.setEnabled(False)
        
        self.cpu_start_btn.clicked.connect(self.start_cpu_stress)
        self.cpu_stop_btn.clicked.connect(self.stop_cpu_stress)
        
        btn_layout.addWidget(self.cpu_start_btn)
        btn_layout.addWidget(self.cpu_stop_btn)
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "CPU Stressz (stress-ng)")
        
        self.cpu_process = QProcess()
        self.cpu_process.readyReadStandardOutput.connect(self.handle_cpu_stdout)
        self.cpu_process.readyReadStandardError.connect(self.handle_cpu_stderr)
        self.cpu_process.finished.connect(self.cpu_process_finished)

    def setup_gpu_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        warning_lbl = QLabel("VIGYÁZAT: A GPU teszt hirtelen terhelést és melegedést okoz!\nGyőződj meg róla, hogy a grafikus kártya hűtése megfelelő.")
        warning_lbl.setStyleSheet("color: #ef4444; font-weight: bold;")
        layout.addWidget(warning_lbl, alignment=Qt.AlignCenter)
        
        self.gpu_status_label = QLabel("Állapot: Készen áll")
        self.gpu_status_label.setStyleSheet("color: #22c55e; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.gpu_status_label, alignment=Qt.AlignCenter)

        gpu_select_layout = QHBoxLayout()
        gpu_select_label = QLabel("Cél GPU:")
        self.gpu_selector_combo = QComboBox()
        self.gpus = self.enumerate_gpus()
        if self.gpus:
            for gpu in self.gpus:
                display_tag = " [Megjelenítő GPU]" if gpu.get("is_display_gpu") else " [Renderelő GPU]"
                label = f"[{gpu['index']}] {gpu['name']} ({gpu['vram']} MiB) — {gpu['pci_bus_id']}{display_tag}"
                self.gpu_selector_combo.addItem(label)
        else:
            self.gpu_selector_combo.addItem("Nem található aktív GPU")
        gpu_select_layout.addWidget(gpu_select_label)
        gpu_select_layout.addWidget(self.gpu_selector_combo, 1)
        layout.addLayout(gpu_select_layout)

        preset_layout = QHBoxLayout()
        preset_label = QLabel("Teszt motor és profil:")
        self.gpu_preset_combo = QComboBox()
        self.gpu_preset_combo.addItems([
            "1. glmark2 — Folyamatos OpenGL terhelés (1280x720 ablak)",
            "2. glmark2 — Maximális OpenGL terhelés (Teljes képernyő 1080p)",
            "3. glmark2 — Standard teljesítmény benchmark (1 kör + pontszám)",
            "4. Unigine Heaven Benchmark (ha telepítve van)"
        ])
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.gpu_preset_combo, 1)
        layout.addLayout(preset_layout)

        self.gpu_console = QTextEdit()
        self.gpu_console.setReadOnly(True)
        layout.addWidget(self.gpu_console)

        btn_layout = QHBoxLayout()
        self.gpu_start_btn = QPushButton("GPU Teszt Indítása")
        self.gpu_stop_btn = QPushButton("Leállítás")
        self.gpu_stop_btn.setEnabled(False)
        
        self.gpu_start_btn.clicked.connect(self.start_gpu_stress)
        self.gpu_stop_btn.clicked.connect(self.stop_gpu_stress)
        
        btn_layout.addWidget(self.gpu_start_btn)
        btn_layout.addWidget(self.gpu_stop_btn)
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "GPU Stressz (glmark2 / OpenGL)")
        
        self.gpu_process = QProcess()
        self.gpu_process.readyReadStandardOutput.connect(self.handle_gpu_stdout)
        self.gpu_process.readyReadStandardError.connect(self.handle_gpu_stderr)
        self.gpu_process.finished.connect(self.gpu_process_finished)

    # --- CPU LOGIC ---
    def start_cpu_stress(self):
        selected_text = self.cpu_type_combo.currentText()
        self.cpu_console.clear()

        if "Prime95" in selected_text:
            mprime_path = "/usr/bin/mprime"
            if not os.path.exists(mprime_path):
                self.cpu_console.append("HIBA: Az mprime (Prime95) nem található a /usr/bin/mprime útvonalon!")
                self.cpu_console.append("Tipp: Használd a stress-ng profilokat (1-3), amelyek azonnal elérhetők.")
                return
            config_dir = os.path.expanduser("~/.jules_mprime")
            os.makedirs(config_dir, exist_ok=True)
            with open(os.path.join(config_dir, "prime.txt"), "w") as f:
                f.write("V24OptionsConverted=1\nTorture=1\n")
            self.cpu_process.setWorkingDirectory(config_dir)
            self.cpu_process.start(mprime_path, ["-t"])
            cmd_desc = f"mprime -t ({config_dir})"
        else:
            stress_ng = "/usr/bin/stress-ng"
            if not os.path.exists(stress_ng):
                self.cpu_console.append("HIBA: A stress-ng nem található! Telepítés: sudo apt install stress-ng")
                return

            if "Matrix" in selected_text:
                args = ["--cpu", "0", "--cpu-method", "matrixprod", "--metrics-brief", "-t", "0"]
            elif "FFT" in selected_text:
                args = ["--cpu", "0", "--cpu-method", "fft", "--vm", "2", "--vm-bytes", "8G", "--metrics-brief", "-t", "0"]
            else:
                args = ["--cpu", "0", "--cpu-method", "all", "--metrics-brief", "-t", "0"]

            self.cpu_process.start(stress_ng, args)
            cmd_desc = f"{stress_ng} {' '.join(args)}"

        self.cpu_status_label.setText("Állapot: CPU STRESSZ TESZT AKTÍV (Minden mag 100%)")
        self.cpu_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.cpu_start_btn.setEnabled(False)
        self.cpu_type_combo.setEnabled(False)
        self.cpu_stop_btn.setEnabled(True)
        self.cpu_console.append(f"--- CPU Stressz Teszt Elindítva ---")
        self.cpu_console.append(f"Parancs: {cmd_desc}\n")

    def stop_cpu_stress(self):
        if self.cpu_process.state() != QProcess.NotRunning:
            self.cpu_process.terminate()
            self.cpu_process.waitForFinished(1000)
            if self.cpu_process.state() != QProcess.NotRunning:
                self.cpu_process.kill()
        subprocess.run(["pkill", "-9", "-f", "stress-ng"], stderr=subprocess.DEVNULL)

        self.cpu_status_label.setText("Állapot: Leállítva")
        self.cpu_status_label.setStyleSheet("color: #22c55e;")
        self.cpu_start_btn.setEnabled(True)
        self.cpu_type_combo.setEnabled(True)
        self.cpu_stop_btn.setEnabled(False)
        self.cpu_console.append("\n--- CPU Teszt Leállítva ---")

    def handle_cpu_stdout(self):
        data = self.cpu_process.readAllStandardOutput()
        self.cpu_console.moveCursor(QTextCursor.End)
        self.cpu_console.insertPlainText(bytes(data).decode("utf8", errors="ignore"))
        self.cpu_console.moveCursor(QTextCursor.End)

    def handle_cpu_stderr(self):
        data = self.cpu_process.readAllStandardError()
        self.cpu_console.moveCursor(QTextCursor.End)
        self.cpu_console.insertPlainText(bytes(data).decode("utf8", errors="ignore"))
        self.cpu_console.moveCursor(QTextCursor.End)

    def cpu_process_finished(self):
        self.stop_cpu_stress()

    # --- GPU LOGIC ---
    def enumerate_gpus(self):
        gpus = []
        # 1. Próbálkozás nvidia-smi-vel
        try:
            result = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=index,name,uuid,pci.bus_id,pci.device_id,memory.total,driver_version",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 7:
                        gpus.append({
                            "index": int(parts[0]),
                            "name": parts[1],
                            "uuid": parts[2],
                            "pci_bus_id": parts[3],
                            "pci_device_id": parts[4],
                            "vram": int(parts[5]),
                            "driver": parts[6],
                            "is_display_gpu": True
                        })
                if gpus:
                    return gpus
        except Exception:
            pass

        # 2. Open-source Mesa / Nouveau detektálás
        try:
            lspci = subprocess.check_output("lspci -nn | grep -i vga", shell=True, text=True)
            pci_bus = lspci.split()[0]
            gpu_name = "NVIDIA NVS 310" if "NVS 310" in lspci or "0df7" in lspci else "VGA vezérlő"
            
            renderer = "Mesa Nouveau"
            try:
                glx = subprocess.check_output("glxinfo 2>/dev/null | grep 'OpenGL renderer string'", shell=True, text=True)
                renderer = glx.split(":", 1)[1].strip()
            except Exception:
                pass

            gpus.append({
                "index": 0,
                "name": f"{gpu_name} ({renderer})",
                "uuid": "nouveau-drm-card0",
                "pci_bus_id": f"0000:{pci_bus}",
                "pci_device_id": "0x0df7",
                "vram": 1024,
                "driver": "nouveau / Mesa Gallium",
                "is_display_gpu": True
            })
        except Exception:
            pass

        return gpus

    def find_heaven_binary(self):
        for path in HEAVEN_SEARCH_PATHS:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return (path, os.path.dirname(path))
        if os.path.isfile(HEAVEN_WRAPPER) and os.access(HEAVEN_WRAPPER, os.X_OK):
            return (HEAVEN_WRAPPER, None)
        return (None, None)

    def start_gpu_stress(self):
        selected_preset = self.gpu_preset_combo.currentText()
        self.gpu_console.clear()

        if "Heaven" in selected_preset:
            heaven_path, work_dir = self.find_heaven_binary()
            if not heaven_path:
                self.gpu_console.append("HIBA: Az Unigine Heaven bináris nem található a rendszeren!")
                self.gpu_console.append("Tipp: Válaszd a glmark2 OpenGL profilt (1-3), amely natívan támogatott ezen a hardveren.")
                return
            args = ["-video_fullscreen", "0", "-video_width", "1280", "-video_height", "720", "-video_app", "opengl"]
            if work_dir:
                self.gpu_process.setWorkingDirectory(work_dir)
            self.gpu_process.start(heaven_path, args)
            cmd_desc = f"{heaven_path} {' '.join(args)}"
        else:
            glmark2_path = "/usr/bin/glmark2"
            if not os.path.exists(glmark2_path):
                self.gpu_console.append("HIBA: A glmark2 nem található! Telepítés: sudo apt install glmark2-x11")
                return

            if "Folyamatos" in selected_preset:
                args = ["-s", "1280x720", "--run-forever"]
            elif "Maximális" in selected_preset:
                args = ["--fullscreen", "--run-forever"]
            else:
                args = ["-s", "1280x720"]

            env = QProcessEnvironment.systemEnvironment()
            env.insert("vblank_mode", "0")
            self.gpu_process.setProcessEnvironment(env)
            self.gpu_process.start(glmark2_path, args)
            cmd_desc = f"{glmark2_path} {' '.join(args)}"

        self.gpu_status_label.setText("Állapot: GPU STRESSZ TESZT AKTÍV")
        self.gpu_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.gpu_start_btn.setEnabled(False)
        self.gpu_preset_combo.setEnabled(False)
        self.gpu_stop_btn.setEnabled(True)
        self.gpu_console.append(f"--- GPU Stressz Teszt Elindítva ---")
        self.gpu_console.append(f"Parancs: {cmd_desc}\n")

    def stop_gpu_stress(self):
        if self.gpu_process.state() != QProcess.NotRunning:
            self.gpu_process.terminate()
            self.gpu_process.waitForFinished(1000)
            if self.gpu_process.state() != QProcess.NotRunning:
                self.gpu_process.kill()
        subprocess.run(["pkill", "-9", "-f", "glmark2"], stderr=subprocess.DEVNULL)

        self.gpu_status_label.setText("Állapot: Leállítva")
        self.gpu_status_label.setStyleSheet("color: #22c55e;")
        self.gpu_start_btn.setEnabled(True)
        self.gpu_preset_combo.setEnabled(True)
        self.gpu_stop_btn.setEnabled(False)
        self.gpu_console.append("\n--- GPU Teszt Leállítva ---")

    def handle_gpu_stdout(self):
        data = self.gpu_process.readAllStandardOutput()
        self.gpu_console.moveCursor(QTextCursor.End)
        self.gpu_console.insertPlainText(bytes(data).decode("utf8", errors="ignore"))
        self.gpu_console.moveCursor(QTextCursor.End)

    def handle_gpu_stderr(self):
        data = self.gpu_process.readAllStandardError()
        self.gpu_console.moveCursor(QTextCursor.End)
        self.gpu_console.insertPlainText(bytes(data).decode("utf8", errors="ignore"))
        self.gpu_console.moveCursor(QTextCursor.End)

    def gpu_process_finished(self):
        self.stop_gpu_stress()

    def closeEvent(self, event):
        self.stop_cpu_stress()
        self.stop_gpu_stress()
        QApplication.instance().quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    socket = QLocalSocket()
    socket.connectToServer('Jules_CPUGPU_Stress_Test_Instance')
    if socket.waitForConnected(500):
        socket.write(b"SHOW")
        socket.waitForBytesWritten(500)
        sys.exit(0)
        
    server = QLocalServer()
    server.removeServer('Jules_CPUGPU_Stress_Test_Instance')
    if not server.listen('Jules_CPUGPU_Stress_Test_Instance'):
        sys.exit(1)
        
    monitor = CPUGPUStressApp()
    
    def on_new_connection():
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(500)
        conn.readAll()
        monitor.showNormal()
        monitor.activateWindow()
        
    server.newConnection.connect(on_new_connection)
    
    monitor.show()
    sys.exit(app.exec_())
