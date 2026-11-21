import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QLabel, QPushButton, QHBoxLayout, QTextEdit, QComboBox, QTabWidget, QCheckBox)
from PyQt5.QtCore import Qt, QProcess, QDir, QProcessEnvironment
from PyQt5.QtGui import QFont, QIcon, QTextCursor
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

# A Heaven bináris lehetséges helyei (keresési sorrend)
HEAVEN_SEARCH_PATHS = [
    "/home/Jules/HardverMonitor_dev/heaven/heaven",
    "/home/Jules/HardverMonitor_dev/heaven/Unigine_Heaven-4.0/heaven",
    "/opt/Unigine_Heaven-4.0/heaven",
    "/opt/unigine/Unigine_Heaven-4.0/heaven",
    "/usr/local/Unigine_Heaven-4.0/heaven",
    os.path.expanduser("~/Unigine_Heaven-4.0/heaven"),
]
# A Heaven wrapper script (ha a bináris helye ismert)
HEAVEN_WRAPPER = "/usr/bin/unigine-heaven"


class CPUGPUStressApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jules PC Stress Test - v1.1.8")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QLabel { color: white; }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #475569; color: #94a3b8; }
            QComboBox, QCheckBox {
                background-color: #1e293b;
                color: white;
                border: 1px solid #334155;
                padding: 5px;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #000000;
                color: #22c55e;
                font-family: monospace;
                border: 1px solid #334155;
            }
            QTabWidget::pane { border: 1px solid #334155; }
            QTabBar::tab {
                background: #1e293b;
                color: white;
                padding: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: #3b82f6; }
        """)

        # Set KDE Icons (No Tray Icon, Just Window Icon)
        icon_path = "/usr/share/icons/oxygen/base/128x128/apps/utilities-system-monitor.png"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("utilities-system-monitor"))

        # UI Setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        title_label = QLabel("Jules CPU & GPU Stress Test")
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
        self.cpu_status_label.setStyleSheet("color: #22c55e;")
        layout.addWidget(self.cpu_status_label, alignment=Qt.AlignCenter)

        self.cpu_type_combo = QComboBox()
        self.cpu_type_combo.addItems([
            "Small FFTs (Maximum power, heat, and CPU stress)",
            "Large FFTs (Maximum power and some RAM tested)",
            "Blend (All of the above - tests lots of RAM)"
        ])
        layout.addWidget(self.cpu_type_combo)

        self.cpu_console = QTextEdit()
        self.cpu_console.setReadOnly(True)
        layout.addWidget(self.cpu_console)

        btn_layout = QHBoxLayout()
        self.cpu_start_btn = QPushButton("Prime95 Indítása")
        self.cpu_stop_btn = QPushButton("Leállítás")
        self.cpu_stop_btn.setEnabled(False)
        
        self.cpu_start_btn.clicked.connect(self.start_cpu_stress)
        self.cpu_stop_btn.clicked.connect(self.stop_cpu_stress)
        
        btn_layout.addWidget(self.cpu_start_btn)
        btn_layout.addWidget(self.cpu_stop_btn)
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "Prime95 (CPU)")
        
        self.cpu_process = QProcess()
        self.cpu_process.readyReadStandardOutput.connect(self.handle_cpu_stdout)
        self.cpu_process.readyReadStandardError.connect(self.handle_cpu_stderr)
        self.cpu_process.finished.connect(self.cpu_process_finished)

    def setup_gpu_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        warning_lbl = QLabel("VIGYÁZAT: A GPU teszt hirtelen hőmérsékletemelkedést okoz!\nGyőződj meg róla, hogy a Quadro kártyák hűtése megfelelő.")
        warning_lbl.setStyleSheet("color: #ef4444; font-weight: bold;")
        layout.addWidget(warning_lbl, alignment=Qt.AlignCenter)
        
        self.gpu_status_label = QLabel("Állapot: Készen áll")
        self.gpu_status_label.setStyleSheet("color: #22c55e;")
        layout.addWidget(self.gpu_status_label, alignment=Qt.AlignCenter)

        # --- GPU választó (hardver szintű azonosítás) ---
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
            self.gpu_selector_combo.addItem("Nem található NVIDIA GPU (nvidia-smi hiba)")
        gpu_select_layout.addWidget(gpu_select_label)
        gpu_select_layout.addWidget(self.gpu_selector_combo, 1)
        layout.addLayout(gpu_select_layout)

        # --- Teszt nehézségi fok (preset) választó ---
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Nehézség:")
        self.gpu_preset_combo = QComboBox()
        self.gpu_preset_combo.addItems([
            "Basic (MSAA 0 — alap terhelés)",
            "Medium (MSAA 2 — közepes terhelés)",
            "High (MSAA 4 — erős terhelés)",
            "Extreme (MSAA 8 — maximális terhelés)"
        ])
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.gpu_preset_combo, 1)
        layout.addLayout(preset_layout)
        
        self.gpu_fullscreen_cb = QCheckBox("Teljes képernyő")
        layout.addWidget(self.gpu_fullscreen_cb)

        self.gpu_console = QTextEdit()
        self.gpu_console.setReadOnly(True)
        layout.addWidget(self.gpu_console)

        btn_layout = QHBoxLayout()
        self.gpu_start_btn = QPushButton("Unigine Heaven Indítása")
        self.gpu_stop_btn = QPushButton("Leállítás")
        self.gpu_stop_btn.setEnabled(False)
        
        self.gpu_start_btn.clicked.connect(self.start_gpu_stress)
        self.gpu_stop_btn.clicked.connect(self.stop_gpu_stress)
        
        btn_layout.addWidget(self.gpu_start_btn)
        btn_layout.addWidget(self.gpu_stop_btn)
        layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "Unigine Heaven (GPU)")
        
        self.gpu_process = QProcess()
        self.gpu_process.readyReadStandardOutput.connect(self.handle_gpu_stdout)
        self.gpu_process.readyReadStandardError.connect(self.handle_gpu_stderr)
        self.gpu_process.finished.connect(self.gpu_process_finished)

    # --- CPU LOGIC ---
    def write_prime_txt(self, test_type):
        torture_type = 3
        if "Small" in test_type:
            torture_type = 1
        elif "Large" in test_type:
            torture_type = 2
            
        config_path = os.path.expanduser("~/.jules_mprime")
        if not os.path.exists(config_path):
            os.makedirs(config_path)

        prime_txt = os.path.join(config_path, "prime.txt")
        with open(prime_txt, "w") as f:
            f.write(f"V24OptionsConverted=1\n")
            f.write(f"Torture={torture_type}\n")
            
        return config_path

    def start_cpu_stress(self):
        mprime_path = "/usr/bin/mprime"
        if not os.path.exists(mprime_path):
            self.cpu_console.append(f"Hiba: Az mprime nem található a {mprime_path} útvonalon!")
            return

        selected_test = self.cpu_type_combo.currentText()
        config_dir = self.write_prime_txt(selected_test)

        self.cpu_process.setWorkingDirectory(config_dir)
        self.cpu_process.start(mprime_path, ["-t"])
        
        self.cpu_status_label.setText(f"Állapot: PRIME95 FUT ({selected_test})")
        self.cpu_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.cpu_start_btn.setEnabled(False)
        self.cpu_type_combo.setEnabled(False)
        self.cpu_stop_btn.setEnabled(True)
        self.cpu_console.clear()
        self.cpu_console.append(f"--- Prime95 Indítása: {selected_test} ---")
        
    def stop_cpu_stress(self):
        if self.cpu_process.state() == QProcess.Running:
            self.cpu_process.terminate()
            self.cpu_process.waitForFinished(3000)
            self.cpu_process.kill()
            
        self.cpu_status_label.setText("Állapot: Leállítva")
        self.cpu_status_label.setStyleSheet("color: #22c55e;")
        self.cpu_start_btn.setEnabled(True)
        self.cpu_type_combo.setEnabled(True)
        self.cpu_stop_btn.setEnabled(False)
        self.cpu_console.append("--- Prime95 Leállítva ---")

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
        """Hardver szintű GPU azonositas nvidia-smi segitsegevel.
        Visszater: GPU dict lista [{index, name, uuid, pci_bus_id, pci_device_id, vram, driver, is_display_gpu}]."""
        try:
            result = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=index,name,uuid,pci.bus_id,pci.device_id,memory.total,driver_version",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return []
            gpus = []
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
                    })
            # Megjelenito GPU azonositas glxinfo segitsegevel
            display_gpu_name = self.detect_display_gpu()
            for gpu in gpus:
                gpu["is_display_gpu"] = (gpu["name"] == display_gpu_name)
            return gpus
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            return []

    def detect_display_gpu(self):
        """Meghatarozza melyik GPU futtatja az X szervert (glxinfo OpenGL renderer).
        Visszater: GPU nev string, vagy None ha nem allapithato meg."""
        try:
            result = subprocess.run(
                ["glxinfo"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return None
            for line in result.stdout.split("\n"):
                if "OpenGL renderer string:" in line:
                    # Formatum: "OpenGL renderer string: Quadro P2000/PCIe/SSE2"
                    renderer = line.split(":", 1)[1].strip()
                    return renderer.split("/")[0].strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def find_heaven_binary(self):
        """Megkeresi az Unigine Heaven binárist több lehetséges útvonalon.
        Visszatér: (bináris_útvonal, munkakönyvtár) tuple, vagy (None, None) ha nem található."""
        # 1. Közvetlen bináris keresése az ismert helyeken
        for path in HEAVEN_SEARCH_PATHS:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                work_dir = os.path.dirname(path)
                return (path, work_dir)
        # 2. A /usr/bin/unigine-heaven wrapper script ellenőrzése
        if os.path.isfile(HEAVEN_WRAPPER) and os.access(HEAVEN_WRAPPER, os.X_OK):
            return (HEAVEN_WRAPPER, None)
        return (None, None)

    def start_gpu_stress(self):
        heaven_path, work_dir = self.find_heaven_binary()
        if not heaven_path:
            self.gpu_console.clear()
            self.gpu_console.append("=" * 60)
            self.gpu_console.append("HIBA: Az Unigine Heaven bináris nem található!")
            self.gpu_console.append("")
            self.gpu_console.append("Keresett útvonalak:")
            for p in HEAVEN_SEARCH_PATHS:
                self.gpu_console.append(f"  - {p}")
            self.gpu_console.append(f"  - {HEAVEN_WRAPPER} (wrapper)")
            self.gpu_console.append("")
            self.gpu_console.append("Telepítési útmutató:")
            self.gpu_console.append("  1. Töltsd le: https://assets.unigine.com/d/Unigine_Heaven-4.0.run")
            self.gpu_console.append("  2. chmod +x Unigine_Heaven-4.0.run")
            self.gpu_console.append("  3. ./Unigine_Heaven-4.0.run --target /home/Jules/HardverMonitor_dev/heaven")
            self.gpu_console.append("  4. A bináris a /home/Jules/HardverMonitor_dev/heaven/heaven útvonalon lesz")
            self.gpu_console.append("=" * 60)
            self.gpu_status_label.setText("Állapot: Heaven NEM TELEPÍTVE!")
            self.gpu_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
            return

        # GPU választás (ha van felismert GPU)
        selected_gpu_index = 0
        selected_gpu_name = "ismeretlen"
        if self.gpus and self.gpu_selector_combo.count() > 0:
            selected_gpu_index = self.gpus[self.gpu_selector_combo.currentIndex()]["index"]
            selected_gpu_name = self.gpus[self.gpu_selector_combo.currentIndex()]["name"]

        # Preset (nehézségi fok) feldolgozása
        preset_text = self.gpu_preset_combo.currentText()
        if "Basic" in preset_text:
            preset_name, msaa = "Basic", "0"
        elif "Medium" in preset_text:
            preset_name, msaa = "Medium", "2"
        elif "High" in preset_text:
            preset_name, msaa = "High", "4"
        else:  # Extreme
            preset_name, msaa = "Extreme", "8"

        is_fs = self.gpu_fullscreen_cb.isChecked()

        # Build command arguments based on preset
        args = []
        if is_fs:
            args.extend(["-video_fullscreen", "1"])
        else:
            args.extend(["-video_fullscreen", "0", "-video_width", "1280", "-video_height", "720"])
        args.extend(["-extern_preset", preset_name, "-video_multisample", msaa, "-video_app", "opengl"])

        # QProcessEnvironment beállítása a kiválasztott GPU-hoz
        # MEGJEGYZES: Ket azonos driveru NVIDIA GPU eseten a PRIME offload
        # (__NV_PRIME_RENDER_OFFLOAD) buffer masolast okoz a renderelo es a
        # megjelenito GPU kozott, ami akadozast (stuttering) okoz.
        # Ezert csak CUDA_VISIBLE_DEVICES-t allitjuk, a renderelo GPU az X szerver
        # konfiguraciatol fugg (megjelenito GPU).
        # A __GL_SYNC_TO_VBLANK=0 kikapcsolja a driver szintu VSync-et, ami tovabb
        # csokkenti az akadozast.
        env = QProcessEnvironment.systemEnvironment()
        env.insert("CUDA_VISIBLE_DEVICES", str(selected_gpu_index))
        env.insert("__GL_SYNC_TO_VBLANK", "0")
        env.insert("__GL_MAX_FRAME_ALLOWED", "0")
        self.gpu_process.setProcessEnvironment(env)

        # Working directory beállítása a Heaven bináris könyvtárára
        if work_dir:
            self.gpu_process.setWorkingDirectory(work_dir)

        self.gpu_process.start(heaven_path, args)
        
        self.gpu_status_label.setText(f"Állapot: UNIGINE HEAVEN FUT (GPU {selected_gpu_index}: {selected_gpu_name})")
        self.gpu_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.gpu_start_btn.setEnabled(False)
        self.gpu_selector_combo.setEnabled(False)
        self.gpu_preset_combo.setEnabled(False)
        self.gpu_fullscreen_cb.setEnabled(False)
        self.gpu_stop_btn.setEnabled(True)
        self.gpu_console.clear()
        self.gpu_console.append(f"--- Unigine Heaven Indítása ---")
        self.gpu_console.append(f"Bináris: {heaven_path}")
        if work_dir:
            self.gpu_console.append(f"Munkakönyvtár: {work_dir}")
        self.gpu_console.append(f"GPU: [{selected_gpu_index}] {selected_gpu_name}")
        self.gpu_console.append(f"Preset: {preset_name} (MSAA {msaa}) | Fullscreen: {is_fs}")
        self.gpu_console.append(f"Env: CUDA_VISIBLE_DEVICES={selected_gpu_index}, VSync=OFF (zero-copy render)")
        
    def stop_gpu_stress(self):
        if self.gpu_process.state() == QProcess.Running:
            self.gpu_process.terminate()
            self.gpu_process.waitForFinished(3000)
            self.gpu_process.kill()
            
        self.gpu_status_label.setText("Állapot: Leállítva")
        self.gpu_status_label.setStyleSheet("color: #22c55e;")
        self.gpu_start_btn.setEnabled(True)
        self.gpu_selector_combo.setEnabled(True)
        self.gpu_preset_combo.setEnabled(True)
        self.gpu_fullscreen_cb.setEnabled(True)
        self.gpu_stop_btn.setEnabled(False)
        self.gpu_console.append("--- Unigine Heaven Leállítva ---")

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
