#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MX CPU Monitor - KDE Plasma stílusú asztali és tálca-alkalmazás
Magszám, magonkénti terhelés, órajel, fogyasztás, hőmérséklet, átlagos órajel,
CPU kormányzó vezérlés, valamint hardveres CPU specifikációk (Alap, Max Turbo, All-Core Turbo).
"""

import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QScrollArea, QGridLayout, QFrame,
    QSystemTrayIcon, QMenu, QAction, QActionGroup, QPushButton, QComboBox,
    QSizePolicy, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit
)
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap

from metrics import SystemMetrics

APP_NAME = "MX CPU Monitor"
APP_VERSION = "1.0.4"

# Kormányzó leírások magyarul
GOV_TOOLTIPS = {
    "ondemand": "Dinamikus: Terhelés esetén azonnal a maximumra emeli az órajelet, egyébként takarékoskodik.",
    "performance": "Teljesítmény: Mindig maximális órajelen tartja a magokat a leggyorsabb reakcióért.",
    "powersave": "Energiatakarékos: Minimális órajelen tartja a magokat a legkisebb fogyasztásért.",
    "conservative": "Kiegyensúlyozott: Fokozatosan, lépésről lépésre emeli és csökkenti a frekvenciát.",
    "schedutil": "Ütemező: A Linux kernel CPU-ütemezőjének közvetlen terhelési adatai alapján szabályoz.",
    "userspace": "Kézi / Felhasználói beállítás."
}

class CpuSpecsDialog(QDialog):
    """Részletes CPU specifikációs és turbó órajel tájékoztató ablak"""
    def __init__(self, specs, cores, threads, icon_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CPU Gyári Specifikáció és Órajel Tájékoztató")
        self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(640, 520)
        self.resize(700, 560)

        self.setStyleSheet("""
            QDialog {
                background-color: #1e2226;
                color: #eff0f1;
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #eff0f1;
            }
            QFrame.PillCard {
                background-color: #2b3036;
                border: 1px solid #3d444d;
                border-radius: 8px;
                padding: 8px;
            }
            QTableWidget {
                background-color: #232629;
                border: 1px solid #3d444d;
                border-radius: 6px;
                gridline-color: #31363b;
                color: #eff0f1;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #3daee9;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2b3036;
                color: #3daee9;
                font-weight: bold;
                border: 1px solid #3d444d;
                padding: 6px;
            }
            QTextEdit {
                background-color: #232629;
                border: 1px solid #3d444d;
                border-radius: 6px;
                color: #bdc3c7;
                font-size: 12px;
                line-height: 1.4;
            }
            QPushButton {
                background-color: #31363b;
                border: 1px solid #4d565f;
                border-radius: 5px;
                color: #eff0f1;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3daee9;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Fejléc
        hdr_layout = QHBoxLayout()
        icon_lbl = QLabel()
        pix = QPixmap(icon_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_lbl.setPixmap(pix)
        hdr_layout.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel(specs.get('model_clean', 'Intel Xeon CPU'))
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #3daee9;")
        arch_lbl = QLabel(f"Architektúra: {specs.get('arch', 'x86_64')} | {cores} fizikai mag / {threads} szál")
        arch_lbl.setStyleSheet("font-size: 12px; color: #bdc3c7;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(arch_lbl)
        hdr_layout.addLayout(title_vbox)
        hdr_layout.addStretch()
        layout.addLayout(hdr_layout)

        # 4 Gyors statisztika kártya
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(10)

        p1 = self._create_pill("ALAPÓRAJEL", f"{specs.get('base', 2.2):.2f} GHz", "#3daee9")
        p2 = self._create_pill("ALL-CORE TURBO", f"{specs.get('all_core', 2.4):.2f} GHz", "#2ecc71")
        p3 = self._create_pill("MAX TURBO", f"{specs.get('max_turbo', 3.2):.2f} GHz", "#f39c12")
        p4 = self._create_pill("TDP KERET", f"{specs.get('tdp', 75):.0f} W", "#e74c3c")

        pills_layout.addWidget(p1)
        pills_layout.addWidget(p2)
        pills_layout.addWidget(p3)
        pills_layout.addWidget(p4)
        layout.addLayout(pills_layout)

        # Turbó szintek táblázat
        lbl_tbl = QLabel("Gyári turbó órajel lépcsők (Turbo Bins):")
        lbl_tbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #3daee9; margin-top: 4px;")
        layout.addWidget(lbl_tbl)

        bins = specs.get('bins', [])
        table = QTableWidget(len(bins), 3)
        table.setHorizontalHeaderLabels(["Állapot / Aktív magok", "Órajel", "Megjegyzés / Funkció"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        for row, (state, freq, note) in enumerate(bins):
            item_state = QTableWidgetItem(state)
            item_state.setFont(QFont("Segoe UI", 9, QFont.Bold))
            item_freq = QTableWidgetItem(freq)
            item_freq.setFont(QFont("monospace", 10, QFont.Bold))
            if "3.2" in freq:
                item_freq.setForeground(Qt.cyan)
            elif "2.4" in freq:
                item_freq.setForeground(Qt.green)
            item_note = QTableWidgetItem(note)

            table.setItem(row, 0, item_state)
            table.setItem(row, 1, item_freq)
            table.setItem(row, 2, item_note)

        layout.addWidget(table, stretch=1)

        # Részletes szöveges magyarázat
        lbl_exp = QLabel("Működési tájékoztató teljes terhelésnél:")
        lbl_exp.setStyleSheet("font-weight: bold; font-size: 13px; color: #3daee9;")
        layout.addWidget(lbl_exp)

        txt_exp = QTextEdit()
        txt_exp.setReadOnly(True)
        txt_exp.setMaximumHeight(85)
        txt_exp.setText(specs.get('explanation', ''))
        layout.addWidget(txt_exp)

        # Bezárás gomb
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton("Rendben / Bezárás")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _create_pill(self, title, val, color):
        frame = QFrame()
        frame.setProperty("class", "PillCard")
        v = QVBoxLayout(frame)
        v.setContentsMargins(8, 6, 8, 6)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #bdc3c7;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
        v.addWidget(lbl_t)
        v.addWidget(lbl_v)
        return frame


class CoreRowWidget(QFrame):
    """Egyes CPU magok mutatója (Load bar, Frequency, Temp)"""
    def __init__(self, core_idx, parent=None):
        super().__init__(parent)
        self.core_idx = core_idx
        self.setObjectName("CoreCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame#CoreCard {
                background-color: #2b3036;
                border: 1px solid #3d444d;
                border-radius: 6px;
                padding: 4px;
            }
            QFrame#CoreCard:hover {
                border: 1px solid #3daee9;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        self.lbl_name = QLabel(f"Mag {core_idx:02d}")
        self.lbl_name.setFixedWidth(55)
        self.lbl_name.setStyleSheet("font-weight: bold; color: #eff0f1;")
        layout.addWidget(self.lbl_name)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(18)
        self.bar.setTextVisible(True)
        self.bar.setAlignment(Qt.AlignCenter)
        self.set_bar_color(0)
        layout.addWidget(self.bar, stretch=1)

        self.lbl_freq = QLabel("0 MHz")
        self.lbl_freq.setFixedWidth(78)
        self.lbl_freq.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_freq.setStyleSheet("color: #3daee9; font-family: monospace; font-size: 12px;")
        layout.addWidget(self.lbl_freq)

        self.lbl_temp = QLabel("-- °C")
        self.lbl_temp.setFixedWidth(52)
        self.lbl_temp.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_temp.setStyleSheet("color: #2ecc71; font-family: monospace; font-size: 12px;")
        layout.addWidget(self.lbl_temp)

    def set_bar_color(self, val):
        if val < 50:
            c = "#2ecc71"
        elif val < 80:
            c = "#f39c12"
        else:
            c = "#e74c3c"
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #1e2226;
                border: 1px solid #3d444d;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {c};
                border-radius: 3px;
            }}
        """)

    def update_data(self, load, freq, temp=None, is_online=True):
        if not is_online or freq == 0.0:
            self.bar.setValue(0)
            self.bar.setFormat("Kikapcsolva (0%)")
            self.bar.setStyleSheet("""
                QProgressBar {
                    background-color: #1a1d20;
                    border: 1px solid #33383e;
                    border-radius: 4px;
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 11px;
                }
                QProgressBar::chunk {
                    background-color: transparent;
                }
            """)
            self.lbl_name.setStyleSheet("font-weight: bold; color: #7f8c8d;")
            self.lbl_freq.setText("0 MHz")
            self.lbl_freq.setStyleSheet("color: #7f8c8d; font-family: monospace; font-size: 12px;")
            self.lbl_temp.setText("--")
            self.lbl_temp.setStyleSheet("color: #7f8c8d; font-family: monospace; font-size: 12px;")
        else:
            self.bar.setFormat("%p%")
            self.lbl_name.setStyleSheet("font-weight: bold; color: #eff0f1;")
            self.bar.setValue(int(load))
            self.set_bar_color(load)

            if freq >= 1000:
                self.lbl_freq.setText(f"{freq/1000.0:.2f} GHz")
            else:
                self.lbl_freq.setText(f"{int(freq)} MHz")
            self.lbl_freq.setStyleSheet("color: #3daee9; font-family: monospace; font-size: 12px;")

            if temp is not None:
                self.lbl_temp.setText(f"{temp:.0f} °C")
                if temp > 75:
                    self.lbl_temp.setStyleSheet("color: #e74c3c; font-family: monospace; font-size: 12px; font-weight: bold;")
                elif temp > 60:
                    self.lbl_temp.setStyleSheet("color: #f39c12; font-family: monospace; font-size: 12px;")
                else:
                    self.lbl_temp.setStyleSheet("color: #2ecc71; font-family: monospace; font-size: 12px;")
            else:
                self.lbl_temp.setText("")


class MainWindow(QMainWindow):
    def __init__(self, icon_path, start_minimized=False):
        super().__init__()
        self.icon_path = icon_path
        self.metrics = SystemMetrics()
        self.specs = self.metrics.specs
        self.app_icon = QIcon(self.icon_path)
        self.setWindowIcon(self.app_icon)
        self.setWindowTitle(APP_NAME)

        self.is_compact = False
        self.current_cols = 2
        self.prev_full_size = QSize(860, 680)
        self.is_updating_gov_ui = False

        self.setMinimumSize(480, 360)
        self.resize(self.prev_full_size)

        self.apply_theme()
        self.init_ui()
        self.init_tray()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_metrics)
        self.timer.start(1000)

        self.refresh_metrics()

        if not start_minimized:
            self.show()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2226;
            }
            QWidget {
                color: #eff0f1;
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
            }
            QFrame.StatCard {
                background-color: #2b3036;
                border: 1px solid #3d444d;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame.SpecBanner {
                background-color: #24292e;
                border: 1px solid #3d444d;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QLabel.CardTitle {
                color: #bdc3c7;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
            }
            QScrollArea {
                border: 1px solid #3d444d;
                border-radius: 8px;
                background-color: #1e2226;
            }
            QPushButton {
                background-color: #31363b;
                border: 1px solid #4d565f;
                border-radius: 5px;
                color: #eff0f1;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3daee9;
                color: #ffffff;
                border: 1px solid #2980b9;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
            QPushButton#ToggleBtn {
                background-color: #2a3d4f;
                border: 1px solid #3daee9;
                color: #3daee9;
            }
            QPushButton#ToggleBtn:hover {
                background-color: #3daee9;
                color: #ffffff;
            }
            QPushButton#InfoBtn {
                background-color: #203545;
                border: 1px solid #2980b9;
                color: #3daee9;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton#InfoBtn:hover {
                background-color: #3daee9;
                color: #ffffff;
            }
            QComboBox {
                background-color: #2b3036;
                border: 1px solid #3daee9;
                border-radius: 5px;
                color: #3daee9;
                padding: 4px 10px;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #232629;
                border: 1px solid #474d54;
                selection-background-color: #3daee9;
                selection-color: #ffffff;
                color: #eff0f1;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1e2226;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #474d54;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #3daee9;
            }
        """)

    def init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        self.root_layout = QVBoxLayout(central)
        self.root_layout.setContentsMargins(14, 14, 14, 14)
        self.root_layout.setSpacing(10)

        # 1. FEJLÉC
        self.header_layout = QHBoxLayout()
        icon_lbl = QLabel()
        pix = QPixmap(self.icon_path).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_lbl.setPixmap(pix)
        self.header_layout.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel(APP_NAME)
        title_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #3daee9;")
        self.cpu_name_lbl = QLabel(self.metrics.cpu_model)
        self.cpu_name_lbl.setStyleSheet("font-size: 12px; color: #bdc3c7;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(self.cpu_name_lbl)
        self.header_layout.addLayout(title_vbox)
        self.header_layout.addStretch()

        self.btn_toggle_compact = QPushButton("🗗 Kompakt nézet")
        self.btn_toggle_compact.setObjectName("ToggleBtn")
        self.btn_toggle_compact.clicked.connect(self.toggle_compact_mode)
        self.header_layout.addWidget(self.btn_toggle_compact)

        self.root_layout.addLayout(self.header_layout)

        # 2. GYÁRI SPECIFIKÁCIÓK ÉS ÓRAJEL SÁV (SpecBanner)
        self.spec_banner = QFrame()
        self.spec_banner.setProperty("class", "SpecBanner")
        banner_layout = QHBoxLayout(self.spec_banner)
        banner_layout.setContentsMargins(8, 5, 8, 5)
        banner_layout.setSpacing(14)

        base_val = f"{self.specs.get('base', 2.2):.2f} GHz"
        allcore_val = f"{self.specs.get('all_core', 2.4):.2f} GHz"
        turbo_val = f"{self.specs.get('max_turbo', 3.2):.2f} GHz"
        tdp_val = f"{self.specs.get('tdp', 75):.0f} W"

        lbl_base = QLabel(f"⚡ Alap: <b style='color:#3daee9;'>{base_val}</b>")
        lbl_allcore = QLabel(f"🔥 All-Core (100%): <b style='color:#2ecc71;'>{allcore_val}</b> <span style='color:#bdc3c7;'>({tdp_val} TDP)</span>")
        lbl_turbo = QLabel(f"🚀 Max Turbo (1–2 mag): <b style='color:#f39c12;'>{turbo_val}</b>")

        banner_layout.addWidget(lbl_base)
        banner_layout.addWidget(lbl_allcore)
        banner_layout.addWidget(lbl_turbo)
        banner_layout.addStretch()

        btn_info = QPushButton("ℹ️ Specifikáció & Turbó")
        btn_info.setObjectName("InfoBtn")
        btn_info.clicked.connect(self.open_specs_dialog)
        banner_layout.addWidget(btn_info)

        self.root_layout.addWidget(self.spec_banner)

        # 3. 4 FŐ ÖSSZESÍTŐ KÁRTYA
        self.cards_frame = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_frame)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        # Card 1: Összes terhelés és átlag órajel
        self.card_load = QFrame()
        self.card_load.setProperty("class", "StatCard")
        v1 = QVBoxLayout(self.card_load)
        v1.setContentsMargins(10, 8, 10, 8)
        lbl_load_title = QLabel("ÖSSZES TERHELÉS & ÁTLAG ÓRAJEL")
        lbl_load_title.setProperty("class", "CardTitle")
        v1.addWidget(lbl_load_title)

        h_load_vals = QHBoxLayout()
        self.val_total_load = QLabel("0.0 %")
        self.val_total_load.setStyleSheet("font-size: 20px; font-weight: bold; color: #2ecc71;")
        self.val_avg_freq = QLabel("Átlag: 0 MHz")
        self.val_avg_freq.setStyleSheet("font-size: 13px; font-weight: bold; color: #3daee9; font-family: monospace;")
        self.val_avg_freq.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h_load_vals.addWidget(self.val_total_load)
        h_load_vals.addWidget(self.val_avg_freq)
        v1.addLayout(h_load_vals)

        self.total_load_bar = QProgressBar()
        self.total_load_bar.setRange(0, 100)
        self.total_load_bar.setFixedHeight(6)
        self.total_load_bar.setTextVisible(False)
        self.total_load_bar.setStyleSheet("QProgressBar { background: #1e2226; border-radius: 3px; } QProgressBar::chunk { background: #2ecc71; border-radius: 3px; }")
        v1.addWidget(self.total_load_bar)
        self.cards_layout.addWidget(self.card_load, stretch=3)

        # Card 2: Magok / Szálak
        self.card_cores = QFrame()
        self.card_cores.setProperty("class", "StatCard")
        v2 = QVBoxLayout(self.card_cores)
        v2.setContentsMargins(10, 8, 10, 8)
        lbl_cores_title = QLabel("MAGOK / SZÁLAK")
        lbl_cores_title.setProperty("class", "CardTitle")
        v2.addWidget(lbl_cores_title)
        self.val_cores = QLabel(f"{self.metrics.threads} szál")
        self.val_cores.setStyleSheet("font-size: 20px; font-weight: bold; color: #3daee9;")
        self.sub_cores = QLabel(f"{self.metrics.cores} fizikai mag")
        self.sub_cores.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        v2.addWidget(self.val_cores)
        v2.addWidget(self.sub_cores)
        self.cards_layout.addWidget(self.card_cores, stretch=2)

        # Card 3: Fogyasztás
        self.card_power = QFrame()
        self.card_power.setProperty("class", "StatCard")
        v3 = QVBoxLayout(self.card_power)
        v3.setContentsMargins(10, 8, 10, 8)
        lbl_pwr_title = QLabel("FOGYASZTÁS")
        lbl_pwr_title.setProperty("class", "CardTitle")
        v3.addWidget(lbl_pwr_title)
        self.val_power = QLabel("0.0 W")
        self.val_power.setStyleSheet("font-size: 20px; font-weight: bold; color: #f39c12;")
        self.sub_power = QLabel(f"TDP: {self.metrics.tdp:.0f} W")
        self.sub_power.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        v3.addWidget(self.val_power)
        v3.addWidget(self.sub_power)
        self.cards_layout.addWidget(self.card_power, stretch=2)

        # Card 4: Hőmérséklet
        self.card_temp = QFrame()
        self.card_temp.setProperty("class", "StatCard")
        v4 = QVBoxLayout(self.card_temp)
        v4.setContentsMargins(10, 8, 10, 8)
        lbl_temp_title = QLabel("HŐMÉRSÉKLET")
        lbl_temp_title.setProperty("class", "CardTitle")
        v4.addWidget(lbl_temp_title)
        self.val_temp = QLabel("-- °C")
        self.val_temp.setStyleSheet("font-size: 20px; font-weight: bold; color: #2ecc71;")
        self.sub_temp = QLabel("Csomag (Package)")
        self.sub_temp.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        v4.addWidget(self.val_temp)
        v4.addWidget(self.sub_temp)
        self.cards_layout.addWidget(self.card_temp, stretch=2)

        self.root_layout.addWidget(self.cards_frame)

        # 4. MAGONKÉNTI LISTA RÉSZ
        self.lbl_cores_hdr = QLabel("Magonkénti terhelés és órajel")
        self.lbl_cores_hdr.setStyleSheet("font-weight: bold; font-size: 13px; color: #3daee9; margin-top: 2px;")
        self.root_layout.addWidget(self.lbl_cores_hdr)

        self.scroll_cores = QScrollArea()
        self.scroll_cores.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setSpacing(8)

        self.core_widgets = []
        n_threads = self.metrics.thread_count
        for i in range(n_threads):
            w = CoreRowWidget(i)
            self.core_widgets.append(w)

        self.rebuild_core_grid(self.current_cols)

        self.scroll_cores.setWidget(self.scroll_content)
        self.root_layout.addWidget(self.scroll_cores, stretch=1)

        # 5. LÁBLÉC: MEMÓRIA + KORMÁNYZÓ + FRISSÍTÉS + GOMBOK
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setSpacing(10)

        self.lbl_mem = QLabel("RAM: -- / -- GB")
        self.lbl_mem.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        self.footer_layout.addWidget(self.lbl_mem)

        self.footer_layout.addStretch()

        # Kormányzó
        lbl_gov = QLabel("Kormányzó:")
        lbl_gov.setStyleSheet("color: #3daee9; font-weight: bold; font-size: 12px;")
        self.combo_gov = QComboBox()
        self.available_govs = self.metrics.get_available_governors()
        self.combo_gov.addItems(self.available_govs)
        curr_gov = self.metrics.get_current_governor()
        if curr_gov in self.available_govs:
            self.combo_gov.setCurrentIndex(self.available_govs.index(curr_gov))
        self.combo_gov.currentIndexChanged.connect(self.on_governor_combo_changed)
        self.update_gov_tooltip(curr_gov)
        self.footer_layout.addWidget(lbl_gov)
        self.footer_layout.addWidget(self.combo_gov)

        # Frissítési gyakoriság
        lbl_rate = QLabel("Frissítés:")
        lbl_rate.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        self.combo_rate = QComboBox()
        self.combo_rate.addItems(["0.5 mp", "1.0 mp", "2.0 mp", "3.0 mp"])
        self.combo_rate.setCurrentIndex(1)
        self.combo_rate.currentIndexChanged.connect(self.on_rate_changed)
        self.footer_layout.addWidget(lbl_rate)
        self.footer_layout.addWidget(self.combo_rate)

        btn_htop = QPushButton("Htop / Monitor")
        btn_htop.clicked.connect(self.launch_htop)
        self.footer_layout.addWidget(btn_htop)

        btn_hide = QPushButton("Tálcára")
        btn_hide.clicked.connect(self.hide)
        self.footer_layout.addWidget(btn_hide)

        self.root_layout.addLayout(self.footer_layout)

    def open_specs_dialog(self):
        """Megnyitja a részletes CPU specifikációs és turbó órajel tájékoztató ablakot"""
        dlg = CpuSpecsDialog(self.specs, self.metrics.cores, self.metrics.threads, self.icon_path, self)
        dlg.exec_()

    def update_gov_tooltip(self, gov):
        tip = GOV_TOOLTIPS.get(gov, "Linux CPU frekvencia szabályozó.")
        self.combo_gov.setToolTip(f"CPU Kormányzó: {gov}\n{tip}")

    def on_governor_combo_changed(self, idx):
        if self.is_updating_gov_ui:
            return
        gov = self.available_govs[idx]
        self.apply_governor(gov)

    def apply_governor(self, gov):
        ok = self.metrics.set_governor(gov)
        self.update_gov_tooltip(gov)

        if hasattr(self, 'gov_actions'):
            self.is_updating_gov_ui = True
            for g_name, act in self.gov_actions.items():
                act.setChecked(g_name == gov)
            if gov in self.available_govs:
                self.combo_gov.setCurrentIndex(self.available_govs.index(gov))
            self.is_updating_gov_ui = False

        if ok:
            self.tray.showMessage("CPU Kormányzó", f"Aktív profil: {gov}", QSystemTrayIcon.Information, 1500)
        self.refresh_metrics()

    def rebuild_core_grid(self, cols):
        self.current_cols = cols
        for i, w in enumerate(self.core_widgets):
            self.grid_layout.removeWidget(w)
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(w, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.is_compact and hasattr(self, 'scroll_cores'):
            avail_w = self.scroll_cores.viewport().width()
            cols = max(1, min(4, avail_w // 260))
            if cols != self.current_cols:
                self.rebuild_core_grid(cols)

    def toggle_compact_mode(self):
        self.is_compact = not self.is_compact

        if self.is_compact:
            self.prev_full_size = self.size()
            self.lbl_cores_hdr.hide()
            self.scroll_cores.hide()
            self.btn_toggle_compact.setText("🗖 Részletes nézet")

            self.setMinimumSize(420, 240)
            self.resize(480, 260)
        else:
            self.lbl_cores_hdr.show()
            self.scroll_cores.show()
            self.btn_toggle_compact.setText("🗗 Kompakt nézet")

            self.setMinimumSize(480, 360)
            self.resize(self.prev_full_size)

    def init_tray(self):
        self.tray = QSystemTrayIcon(self.app_icon, self)
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #232629;
                border: 1px solid #474d54;
                color: #eff0f1;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3daee9;
                color: #ffffff;
            }
        """)

        act_toggle = QAction("Ablak megjelenítése / elrejtése", self)
        act_toggle.triggered.connect(self.toggle_window)
        tray_menu.addAction(act_toggle)

        act_compact = QAction("Váltás kompakt / részletes nézetre", self)
        act_compact.triggered.connect(self.toggle_compact_mode)
        tray_menu.addAction(act_compact)

        act_specs = QAction("ℹ️ CPU Specifikáció és Turbo adatok...", self)
        act_specs.triggered.connect(self.open_specs_dialog)
        tray_menu.addAction(act_specs)

        gov_menu = tray_menu.addMenu("CPU Kormányzó (Profil)")
        self.gov_group = QActionGroup(self)
        self.gov_actions = {}
        curr_gov = self.metrics.get_current_governor()

        for g in self.available_govs:
            act = QAction(f"{g}", self, checkable=True)
            if g == curr_gov:
                act.setChecked(True)
            act.triggered.connect(lambda checked, name=g: self.apply_governor(name))
            self.gov_group.addAction(act)
            gov_menu.addAction(act)
            self.gov_actions[g] = act

        tray_menu.addSeparator()

        act_htop = QAction("Htop indítása", self)
        act_htop.triggered.connect(self.launch_htop)
        tray_menu.addAction(act_htop)

        tray_menu.addSeparator()

        act_quit = QAction("Kilépés", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(act_quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_window()

    def toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def on_rate_changed(self, idx):
        rates = [500, 1000, 2000, 3000]
        self.timer.setInterval(rates[idx])

    def launch_htop(self):
        terms = [
            ["x-terminal-emulator", "-e", "htop"],
            ["konsole", "-e", "htop"],
            ["xfce4-terminal", "-e", "htop"],
            ["xterm", "-e", "htop"]
        ]
        for cmd in terms:
            try:
                subprocess.Popen(cmd)
                return
            except Exception:
                continue

    def refresh_metrics(self):
        m = self.metrics.update()

        # Összes terhelés
        tot = m['total_load']
        self.val_total_load.setText(f"{tot:.1f} %")
        self.total_load_bar.setValue(int(tot))
        if tot < 50:
            c = "#2ecc71"
        elif tot < 80:
            c = "#f39c12"
        else:
            c = "#e74c3c"
        self.val_total_load.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {c};")
        self.total_load_bar.setStyleSheet(f"QProgressBar {{ background: #1e2226; border-radius: 3px; }} QProgressBar::chunk {{ background: {c}; border-radius: 3px; }}")

        # Átlagos órajel
        avg_fq = m.get('avg_freq', 0.0)
        if avg_fq >= 1000:
            self.val_avg_freq.setText(f"Átlag: {avg_fq/1000.0:.2f} GHz")
        else:
            self.val_avg_freq.setText(f"Átlag: {int(avg_fq)} MHz")

        # Magszám kártya
        active = m.get('active_threads', self.metrics.thread_count)
        total = self.metrics.thread_count
        if active < total:
            self.val_cores.setText(f"{active} / {total} szál")
            self.sub_cores.setText(f"{total - active} mag kikapcsolva")
        else:
            self.val_cores.setText(f"{total} szál")
            self.sub_cores.setText(f"{self.metrics.cores} fizikai mag / 1 foglalat")

        # Fogyasztás
        pw = m['power_w']
        self.val_power.setText(f"{pw:.1f} W")
        sub_text = "Valós Intel RAPL" if m['power_real'] else "Becsült érték"
        self.sub_power.setText(f"{sub_text} (TDP: {m['tdp']:.0f} W)")

        # Hőmérséklet
        temp = m['pkg_temp']
        if temp > 0:
            self.val_temp.setText(f"{temp:.1f} °C")
            if temp > 75:
                tc = "#e74c3c"
            elif temp > 60:
                tc = "#f39c12"
            else:
                tc = "#2ecc71"
            self.val_temp.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {tc};")
        else:
            self.val_temp.setText("N/A")

        # Magonkénti értékek frissítése
        loads = m['core_loads']
        freqs = m['frequencies']
        core_temps = m['core_temps']
        online_status = m.get('online_status', [True] * len(self.core_widgets))

        for i, w in enumerate(self.core_widgets):
            is_on = online_status[i] if i < len(online_status) else True
            ld = loads[i] if (is_on and i < len(loads)) else 0.0
            fq = freqs[i] if (is_on and i < len(freqs)) else 0.0
            t = core_temps.get(f"Core {i}", None) if is_on else None
            w.update_data(ld, fq, t, is_online=is_on)

        # Kormányzó szinkronizálása
        current_gov = m.get('governor', 'ondemand')
        if not self.is_updating_gov_ui and self.combo_gov.currentText() != current_gov:
            self.is_updating_gov_ui = True
            if current_gov in self.available_govs:
                self.combo_gov.setCurrentIndex(self.available_govs.index(current_gov))
            if hasattr(self, 'gov_actions') and current_gov in self.gov_actions:
                self.gov_actions[current_gov].setChecked(True)
            self.update_gov_tooltip(current_gov)
            self.is_updating_gov_ui = False

        # Memória
        mem = m['memory']
        self.lbl_mem.setText(f"RAM: {mem['used_gb']:.1f} GB / {mem['total_gb']:.1f} GB ({mem['pct']:.0f}%)")

        # Tálca tooltip
        tray_tip = f"{APP_NAME}\nKormányzó: {current_gov}\nÖsszes terhelés: {tot:.1f}%\nÁtlag: {self.val_avg_freq.text().replace('Átlag: ', '')}\nHőmérséklet: {temp:.1f}°C\nFogyasztás: {pw:.1f} W"
        if active < total:
            tray_tip += f"\nAktív magok: {active}/{total}"
        self.tray.setToolTip(tray_tip)


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"{APP_NAME} v{APP_VERSION}")
        print("Használat: mx-cpu-monitor [KAPCSOLÓK]")
        print("Kapcsolók:")
        print("  --minimized, --tray, -m   Indítás kis méretben a tálcán")
        print("  --compact, -c             Indítás kompakt nézetben")
        print("  -h, --help                Súgó megjelenítése")
        sys.exit(0)

    start_minimized = "--minimized" in sys.argv or "--tray" in sys.argv or "-m" in sys.argv
    start_compact = "--compact" in sys.argv or "-c" in sys.argv

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    icon_candidates = [
        "/usr/share/icons/hicolor/128x128/apps/mx-cpu-monitor.png",
        "/usr/share/pixmaps/mx-cpu-monitor.png",
        os.path.join(os.path.dirname(__file__), "icon-128.png"),
        os.path.join(os.path.dirname(__file__), "mx-cpu-monitor.png"),
        "/usr/share/mx-cpu-monitor/icon-128.png"
    ]
    icon_path = next((p for p in icon_candidates if os.path.exists(p)), "")

    win = MainWindow(icon_path, start_minimized=start_minimized)
    if start_compact:
        win.toggle_compact_mode()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
