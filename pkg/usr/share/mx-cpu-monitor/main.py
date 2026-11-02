#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MX CPU Monitor - KDE Plasma stílusú asztali és tálca-alkalmazás
Magszám, magonkénti/szálankénti terhelés, órajel, fogyasztás, fizikai mag-hőmérséklet,
átlagos órajel, CPU kormányzó vezérlés, valamint teljes (108 modelles) Intel Xeon E5 v3/v4
specifikációs és turbó órajel katalógus.
"""

import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QScrollArea, QGridLayout, QFrame,
    QSystemTrayIcon, QMenu, QAction, QActionGroup, QPushButton, QComboBox,
    QSizePolicy, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QTabWidget, QLineEdit, QAbstractItemView
)
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QBrush

from metrics import SystemMetrics, XEON_ULTIMATE_CATALOG, XEON_SPECS_DB

APP_NAME = "MX CPU Monitor"
APP_VERSION = "1.0.5"

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
    """Részletes CPU specifikációs, turbó órajel és 108-modelles Xeon E5 v3/v4 katalógus ablak"""
    def __init__(self, specs, cores, threads, icon_path, parent=None):
        super().__init__(parent)
        self.specs = specs
        self.cores = cores
        self.threads = threads
        self.icon_path = icon_path
        self.setWindowTitle("CPU Gyári Specifikáció & Intel Xeon E5 v3/v4 Katalógus")
        self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(820, 600)
        self.resize(940, 660)

        self.setStyleSheet("""
            QDialog {
                background-color: #1e2226;
                color: #eff0f1;
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #eff0f1;
            }
            QTabWidget::pane {
                border: 1px solid #3d444d;
                border-radius: 6px;
                background-color: #1e2226;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #2b3036;
                color: #bdc3c7;
                border: 1px solid #3d444d;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #3daee9;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #31363b;
                color: #eff0f1;
            }
            QFrame.PillCard {
                background-color: #2b3036;
                border: 1px solid #3d444d;
                border-radius: 8px;
                padding: 8px;
            }
            QLineEdit {
                background-color: #232629;
                border: 1px solid #3d444d;
                border-radius: 5px;
                color: #eff0f1;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3daee9;
            }
            QComboBox {
                background-color: #2b3036;
                border: 1px solid #3daee9;
                border-radius: 5px;
                color: #3daee9;
                padding: 5px 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #232629;
                border: 1px solid #474d54;
                selection-background-color: #3daee9;
                selection-color: #ffffff;
                color: #eff0f1;
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
                padding: 5px;
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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Fejléc
        hdr_layout = QHBoxLayout()
        icon_lbl = QLabel()
        pix = QPixmap(icon_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_lbl.setPixmap(pix)
        hdr_layout.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        self.title_lbl = QLabel(specs.get('model_clean', 'Intel Xeon CPU'))
        self.title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #3daee9;")
        cache_str = specs.get('cache', 'N/A')
        mem_str = specs.get('memory', 'DDR4')
        cat_str = specs.get('category', '')
        self.arch_lbl = QLabel(
            f"Architektúra: {specs.get('arch', 'x86_64')}  |  {cores} fizikai mag / {threads} szál  |  "
            f"L3 Cache: {cache_str}  |  Memória: {mem_str}  |  {cat_str}"
        )
        self.arch_lbl.setStyleSheet("font-size: 12px; color: #bdc3c7;")
        title_vbox.addWidget(self.title_lbl)
        title_vbox.addWidget(self.arch_lbl)
        hdr_layout.addLayout(title_vbox)
        hdr_layout.addStretch()
        layout.addLayout(hdr_layout)

        # Fülek (Aktuális CPU + 108 modelles Xeon Katalógus)
        self.tabs = QTabWidget()
        self.tab_current = QWidget()
        self.tab_catalog = QWidget()
        self.tabs.addTab(self.tab_current, f"🖥️ Aktuális Processzor ({specs.get('key', 'CPU')})")
        self.tabs.addTab(self.tab_catalog, f"📚 Xeon E5 v3 / v4 Ultimate Katalógus ({len(XEON_ULTIMATE_CATALOG)} modell)")
        layout.addWidget(self.tabs, stretch=1)

        self._build_current_cpu_tab(specs)
        self._build_catalog_tab()

        # Bezárás gomb
        btn_box = QHBoxLayout()
        lbl_hint = QLabel("💡 Tipp: A Katalógus fülön duplán kattintva bármelyik Xeon modell részletes turbó táblázata megtekinthető.")
        lbl_hint.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        btn_box.addWidget(lbl_hint)
        btn_box.addStretch()
        btn_close = QPushButton("Rendben / Bezárás")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _build_current_cpu_tab(self, specs):
        tab_layout = QVBoxLayout(self.tab_current)
        tab_layout.setContentsMargins(14, 14, 14, 14)
        tab_layout.setSpacing(12)

        # 5 Gyors statisztika kártya
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(10)

        self.pill_base_lbl = None
        p1, self.pill_base_val = self._create_pill("ALAPÓRAJEL", f"{specs.get('base', 2.2):.2f} GHz", "#3daee9")
        p2, self.pill_all_val = self._create_pill("ALL-CORE TURBO", f"{specs.get('all_core', 2.4):.2f} GHz", "#2ecc71")
        turbo_disp = f"{specs.get('max_turbo', 3.2):.2f} GHz"
        if specs.get('hw_max_turbo') and specs['hw_max_turbo'] > specs.get('max_turbo', 0):
            turbo_disp = f"{specs['max_turbo']:.2f} / {specs['hw_max_turbo']:.2f} GHz"
        p3, self.pill_turbo_val = self._create_pill("MAX TURBO", turbo_disp, "#f39c12")
        p4, self.pill_cache_val = self._create_pill("L3 CACHE & MEM", f"{specs.get('cache', 'N/A')} ({specs.get('memory', 'DDR4')})", "#9b59b6")
        p5, self.pill_tdp_val = self._create_pill("TDP KERET", f"{specs.get('tdp', 75):.0f} W", "#e74c3c")

        for p in (p1, p2, p3, p4, p5):
            pills_layout.addWidget(p)
        tab_layout.addLayout(pills_layout)

        # Turbó szintek táblázat
        self.lbl_tbl = QLabel("Gyári turbó órajel lépcsők (Turbo Bins):")
        self.lbl_tbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #3daee9; margin-top: 2px;")
        tab_layout.addWidget(self.lbl_tbl)

        self.bins_table = QTableWidget(0, 3)
        self.bins_table.setHorizontalHeaderLabels(["Állapot / Aktív magok", "Órajel", "Megjegyzés / Funkció"])
        self.bins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.bins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.bins_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.bins_table.verticalHeader().setVisible(False)
        self.bins_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.bins_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        tab_layout.addWidget(self.bins_table, stretch=1)

        # Részletes szöveges magyarázat
        lbl_exp = QLabel("Működési tájékoztató és modell háttér:")
        lbl_exp.setStyleSheet("font-weight: bold; font-size: 13px; color: #3daee9;")
        tab_layout.addWidget(lbl_exp)

        self.txt_exp = QTextEdit()
        self.txt_exp.setReadOnly(True)
        self.txt_exp.setMaximumHeight(105)
        tab_layout.addWidget(self.txt_exp)

        self._populate_spec_details(specs)

    def _populate_spec_details(self, specs):
        self.pill_base_val.setText(f"{specs.get('base', 2.2):.2f} GHz")
        self.pill_all_val.setText(f"{specs.get('all_core', 2.4):.2f} GHz")
        turbo_disp = f"{specs.get('max_turbo', 3.2):.2f} GHz"
        if specs.get('hw_max_turbo') and specs['hw_max_turbo'] > specs.get('max_turbo', 0):
            turbo_disp = f"{specs['max_turbo']:.2f} / {specs['hw_max_turbo']:.2f} GHz"
        self.pill_turbo_val.setText(turbo_disp)
        self.pill_cache_val.setText(f"{specs.get('cache', 'N/A')} ({specs.get('memory', 'DDR4')})")
        self.pill_tdp_val.setText(f"{specs.get('tdp', 75):.0f} W")

        bins = specs.get('bins', [])
        self.bins_table.setRowCount(len(bins))
        max_t_str = f"{specs.get('max_turbo', 0):.2f}"
        all_c_str = f"{specs.get('all_core', 0):.2f}"

        for row, (state, freq, note) in enumerate(bins):
            item_state = QTableWidgetItem(state)
            item_state.setFont(QFont("Segoe UI", 9, QFont.Bold))
            item_freq = QTableWidgetItem(freq)
            item_freq.setFont(QFont("monospace", 10, QFont.Bold))
            if max_t_str in freq or "Csúcs" in note or "Max" in state:
                item_freq.setForeground(QBrush(QColor("#00e5ff")))
            elif all_c_str in freq or "All-Core" in note:
                item_freq.setForeground(QBrush(QColor("#2ecc71")))
            elif "0 MHz" in freq:
                item_freq.setForeground(QBrush(QColor("#7f8c8d")))
            item_note = QTableWidgetItem(note)

            self.bins_table.setItem(row, 0, item_state)
            self.bins_table.setItem(row, 1, item_freq)
            self.bins_table.setItem(row, 2, item_note)

        self.txt_exp.setText(specs.get('explanation', ''))

    def _build_catalog_tab(self):
        cat_layout = QVBoxLayout(self.tab_catalog)
        cat_layout.setContentsMargins(14, 14, 14, 14)
        cat_layout.setSpacing(10)

        # Szűrősáv
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        lbl_cat = QLabel("Széria:")
        lbl_cat.setStyleSheet("font-weight: bold; color: #3daee9;")
        self.combo_cat = QComboBox()
        self.combo_cat.addItems([
            f"Összes kategória ({len(XEON_ULTIMATE_CATALOG)} modell)",
            "OEM & Titkos Szériák (v3-v4)",
            "Teljes E5 v3 Család",
            "Teljes E5 v4 Család"
        ])
        self.combo_cat.currentIndexChanged.connect(self._filter_catalog)

        lbl_search = QLabel("Keresés:")
        lbl_search.setStyleSheet("font-weight: bold; color: #3daee9;")
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Modell, magszám, TDP vagy kulcsszó (pl. 2673, 20C, Azure, AWS, DDR3, 145W)...")
        self.edit_search.textChanged.connect(self._filter_catalog)

        self.btn_reset_curr = QPushButton("Saját CPU visszaállítása")
        self.btn_reset_curr.clicked.connect(self._reset_to_machine_cpu)

        filter_layout.addWidget(lbl_cat)
        filter_layout.addWidget(self.combo_cat)
        filter_layout.addWidget(lbl_search)
        filter_layout.addWidget(self.edit_search, stretch=1)
        filter_layout.addWidget(self.btn_reset_curr)
        cat_layout.addLayout(filter_layout)

        # Táblázat
        cols = ["Modell", "Kategória", "Gen", "Mag/Szál", "Alap", "All-Core", "Max Turbo", "Cache", "TDP", "Memória", "Típus / Háttér megjegyzés"]
        self.cat_table = QTableWidget(0, len(cols))
        self.cat_table.setHorizontalHeaderLabels(cols)
        for c in range(len(cols) - 1):
            self.cat_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.cat_table.horizontalHeader().setSectionResizeMode(len(cols) - 1, QHeaderView.Stretch)
        self.cat_table.verticalHeader().setVisible(False)
        self.cat_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cat_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cat_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cat_table.cellDoubleClicked.connect(self._on_catalog_row_double_clicked)
        cat_layout.addWidget(self.cat_table, stretch=1)

        self._filter_catalog()

    def _filter_catalog(self):
        cat_idx = self.combo_cat.currentIndex()
        cat_filter = None
        if cat_idx == 1:
            cat_filter = "OEM & Titkos Szériák (v3-v4)"
        elif cat_idx == 2:
            cat_filter = "Teljes E5 v3 Család"
        elif cat_idx == 3:
            cat_filter = "Teljes E5 v4 Család"

        q = self.edit_search.text().strip().lower()
        curr_key = self.specs.get('key', '')

        filtered = []
        for item in XEON_ULTIMATE_CATALOG:
            model, cat, gen, c_num, t_num, base_f, turbo_f, cache, tdp_f, mem, note = item
            if cat_filter and cat != cat_filter:
                continue
            row_str = f"{model} {cat} {gen} {c_num}C/{t_num}T {base_f:.2f} {turbo_f:.2f} {cache} {tdp_f}W {mem} {note}".lower()
            if q and q not in row_str:
                continue
            filtered.append(item)

        self.cat_table.setRowCount(len(filtered))
        selected_row = None

        for r, item in enumerate(filtered):
            model, cat, gen, c_num, t_num, base_f, turbo_f, cache, tdp_f, mem, note = item
            spec = XEON_SPECS_DB.get(model, {})
            all_core = spec.get('all_core', base_f)
            gen_short = "v4 (14nm)" if "v4" in gen else "v3 (22nm)"
            turbo_str = "Nincs" if turbo_f <= base_f else f"{turbo_f:.2f} GHz"

            vals = [
                model,
                cat.replace(" (v3-v4)", ""),
                gen_short,
                f"{c_num}C / {t_num}T",
                f"{base_f:.2f} GHz",
                f"{all_core:.2f} GHz",
                turbo_str,
                cache,
                f"{tdp_f} W",
                mem,
                note
            ]
            is_current = (model.lower() == curr_key.lower())
            if is_current:
                selected_row = r

            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c in (0, 3, 4, 5, 6, 8):
                    it.setFont(QFont("monospace", 9, QFont.Bold if c in (0, 5, 6) else QFont.Normal))
                if c == 0:
                    it.setForeground(QBrush(QColor("#3daee9")))
                elif c == 5:
                    it.setForeground(QBrush(QColor("#2ecc71")))
                elif c == 6 and turbo_f > base_f:
                    it.setForeground(QBrush(QColor("#f39c12")))
                if is_current:
                    it.setBackground(QBrush(QColor("#1b3b2b")))
                self.cat_table.setItem(r, c, it)

        if selected_row is not None:
            self.cat_table.selectRow(selected_row)

    def _on_catalog_row_double_clicked(self, row, _col):
        model_item = self.cat_table.item(row, 0)
        if not model_item:
            return
        model_key = model_item.text().strip()
        if model_key in XEON_SPECS_DB:
            spec = XEON_SPECS_DB[model_key]
            self.title_lbl.setText(f"{spec['model_clean']} (Katalógus előnézet)")
            self.arch_lbl.setText(
                f"Architektúra: {spec['arch']}  |  {spec['cores_spec']} fizikai mag / {spec['threads_spec']} szál  |  "
                f"L3 Cache: {spec['cache']}  |  Memória: {spec['memory']}  |  {spec['category']}"
            )
            self.lbl_tbl.setText(f"Gyári turbó órajel lépcsők ({spec['model_clean']}):")
            self._populate_spec_details(spec)
            self.tabs.setTabText(0, f"🖥️ Kiválasztott: {model_key}")
            self.tabs.setCurrentIndex(0)

    def _reset_to_machine_cpu(self):
        self.title_lbl.setText(self.specs.get('model_clean', 'Intel Xeon CPU'))
        self.arch_lbl.setText(
            f"Architektúra: {self.specs.get('arch', 'x86_64')}  |  {self.cores} fizikai mag / {self.threads} szál  |  "
            f"L3 Cache: {self.specs.get('cache', 'N/A')}  |  Memória: {self.specs.get('memory', 'DDR4')}  |  "
            f"{self.specs.get('category', '')}"
        )
        self.lbl_tbl.setText("Gyári turbó órajel lépcsők (Turbo Bins):")
        self._populate_spec_details(self.specs)
        self.tabs.setTabText(0, f"🖥️ Aktuális Processzor ({self.specs.get('key', 'CPU')})")
        self.tabs.setCurrentIndex(0)

    def _create_pill(self, title, val, color):
        frame = QFrame()
        frame.setProperty("class", "PillCard")
        v = QVBoxLayout(frame)
        v.setContentsMargins(8, 6, 8, 6)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #bdc3c7;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};")
        v.addWidget(lbl_t)
        v.addWidget(lbl_v)
        return frame, lbl_v


class CoreRowWidget(QFrame):
    """Egyes CPU szálak / magok mutatója (Mag/Szál azonosító, Load bar, Frequency, Fizikai Mag Temp)"""
    def __init__(self, core_idx, topo_info=None, has_ht=True, parent=None):
        super().__init__(parent)
        self.core_idx = core_idx
        self.topo_info = topo_info or {}
        self.setObjectName("CoreCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame#CoreCard {
                background-color: #2b3036;
                border: 1px solid #3d444d;
                border-radius: 6px;
                padding: 3px;
            }
            QFrame#CoreCard:hover {
                border: 1px solid #3daee9;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        phys_idx = self.topo_info.get('phys_core_idx', core_idx + 1)
        conky_sz = self.topo_info.get('conky_thread_idx', core_idx + 1)
        hw_cid = self.topo_info.get('hw_core_id', core_idx)

        if has_ht:
            label_text = f"M{phys_idx:02d}·Sz{conky_sz:02d}"
            label_width = 68
        else:
            label_text = f"Mag {phys_idx:02d}"
            label_width = 55

        self.lbl_name = QLabel(label_text)
        self.lbl_name.setFixedWidth(label_width)
        self.lbl_name.setStyleSheet("font-weight: bold; color: #eff0f1; font-size: 11px;")
        self.setToolTip(
            f"Fizikai mag: Mag {phys_idx:02d} (HW Core ID: {hw_cid})\n"
            f"Logikai szál: Szál {conky_sz:02d} (Linux cpu{core_idx})"
        )
        layout.addWidget(self.lbl_name)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(17)
        self.bar.setTextVisible(True)
        self.bar.setAlignment(Qt.AlignCenter)
        self.set_bar_color(0)
        layout.addWidget(self.bar, stretch=1)

        self.lbl_freq = QLabel("0 MHz")
        self.lbl_freq.setFixedWidth(72)
        self.lbl_freq.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_freq.setStyleSheet("color: #3daee9; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.lbl_freq)

        self.lbl_temp = QLabel("-- °C")
        self.lbl_temp.setFixedWidth(44)
        self.lbl_temp.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_temp.setStyleSheet("color: #2ecc71; font-family: monospace; font-size: 11px;")
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
                font-size: 10px;
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
            self.bar.setFormat("Offline (0%)")
            self.bar.setStyleSheet("""
                QProgressBar {
                    background-color: #1a1d20;
                    border: 1px solid #33383e;
                    border-radius: 4px;
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 10px;
                }
                QProgressBar::chunk {
                    background-color: transparent;
                }
            """)
            self.lbl_name.setStyleSheet("font-weight: bold; color: #7f8c8d; font-size: 11px;")
            self.lbl_freq.setText("0 MHz")
            self.lbl_freq.setStyleSheet("color: #7f8c8d; font-family: monospace; font-size: 11px;")
            self.lbl_temp.setText("--")
            self.lbl_temp.setStyleSheet("color: #7f8c8d; font-family: monospace; font-size: 11px;")
        else:
            self.bar.setFormat("%p%")
            self.lbl_name.setStyleSheet("font-weight: bold; color: #eff0f1; font-size: 11px;")
            self.bar.setValue(int(load))
            self.set_bar_color(load)

            if freq >= 1000:
                self.lbl_freq.setText(f"{freq/1000.0:.2f} GHz")
            else:
                self.lbl_freq.setText(f"{int(freq)} MHz")
            self.lbl_freq.setStyleSheet("color: #3daee9; font-family: monospace; font-size: 11px;")

            if temp is not None:
                self.lbl_temp.setText(f"{temp:.0f} °C")
                if temp > 75:
                    self.lbl_temp.setStyleSheet("color: #e74c3c; font-family: monospace; font-size: 11px; font-weight: bold;")
                elif temp > 60:
                    self.lbl_temp.setStyleSheet("color: #f39c12; font-family: monospace; font-size: 11px;")
                else:
                    self.lbl_temp.setStyleSheet("color: #2ecc71; font-family: monospace; font-size: 11px;")
            else:
                self.lbl_temp.setText("-- °C")


class MainWindow(QMainWindow):
    def __init__(self, icon_path, start_minimized=False):
        super().__init__()
        self.icon_path = icon_path
        self.metrics = SystemMetrics()
        self.specs = self.metrics.specs
        self.app_icon = QIcon(self.icon_path)
        self.setWindowIcon(self.app_icon)
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

        self.is_compact = False
        if self.metrics.thread_count >= 32:
            self.current_cols = 4
            self.prev_full_size = QSize(1100, 760)
        elif self.metrics.thread_count >= 16:
            self.current_cols = 2
            self.prev_full_size = QSize(880, 680)
        else:
            self.current_cols = 2
            self.prev_full_size = QSize(820, 620)
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
        self.cpu_name_lbl = QLabel(
            f"{self.metrics.cpu_model}  •  {self.metrics.cores} Mag / {self.metrics.threads} Szál"
        )
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
        if self.specs.get('hw_max_turbo') and self.specs['hw_max_turbo'] > self.specs.get('max_turbo', 0):
            turbo_val = f"{self.specs['max_turbo']:.2f}–{self.specs['hw_max_turbo']:.2f} GHz"
        tdp_val = f"{self.specs.get('tdp', 75):.0f} W"
        cache_val = self.specs.get('cache', 'N/A')

        lbl_base = QLabel(f"⚡ Alap: <b style='color:#3daee9;'>{base_val}</b>")
        lbl_allcore = QLabel(f"🔥 All-Core (100%): <b style='color:#2ecc71;'>{allcore_val}</b> <span style='color:#bdc3c7;'>({tdp_val} TDP)</span>")
        lbl_turbo = QLabel(f"🚀 Max Turbo: <b style='color:#f39c12;'>{turbo_val}</b>")
        lbl_cache = QLabel(f"🗄️ L3 Cache: <b style='color:#9b59b6;'>{cache_val}</b>")

        banner_layout.addWidget(lbl_base)
        banner_layout.addWidget(lbl_allcore)
        banner_layout.addWidget(lbl_turbo)
        banner_layout.addWidget(lbl_cache)
        banner_layout.addStretch()

        btn_info = QPushButton("ℹ️ Specifikáció & Xeon Katalógus (108)")
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
        lbl_temp_title = QLabel("PROCESSZOR HŐMÉRSÉKLET")
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

        # 4. MAGONKÉNTI / SZÁLANKÉNTI LISTA RÉSZ
        self.lbl_cores_hdr = QLabel(
            f"Magonkénti és szálankénti terhelés, órajel és fizikai mag-hőmérséklet "
            f"({self.metrics.cores} fizikai mag / {self.metrics.threads} szál)"
        )
        self.lbl_cores_hdr.setStyleSheet("font-weight: bold; font-size: 13px; color: #3daee9; margin-top: 2px;")
        self.root_layout.addWidget(self.lbl_cores_hdr)

        self.scroll_cores = QScrollArea()
        self.scroll_cores.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setSpacing(6)

        self.core_widgets = []
        n_threads = self.metrics.thread_count
        has_ht = n_threads > self.metrics.core_count
        for i in range(n_threads):
            topo_info = self.metrics.thread_topology.get(i, {})
            w = CoreRowWidget(i, topo_info=topo_info, has_ht=has_ht)
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
        """Megnyitja a részletes CPU specifikációs és 108-modelles Xeon katalógus ablakot"""
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
            cols = max(1, min(4, avail_w // 245))
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
            self.resize(520, 260)
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

        act_specs = QAction("ℹ️ CPU Specifikáció & Xeon Katalógus (108)...", self)
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
            self.sub_cores.setText(f"{total - active} szál kikapcsolva")
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

        # Magonkénti / szálankénti értékek frissítése
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
        tray_tip = (
            f"{APP_NAME} ({self.specs.get('key', '')})\n"
            f"Kormányzó: {current_gov}\n"
            f"Összes terhelés: {tot:.1f}%\n"
            f"Átlag: {self.val_avg_freq.text().replace('Átlag: ', '')}\n"
            f"Processzor hőmérséklet: {temp:.1f}°C\n"
            f"Fogyasztás: {pw:.1f} W"
        )
        if active < total:
            tray_tip += f"\nAktív szálak: {active}/{total}"
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
