#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MX CPU Monitor - Rendszermutatók, szenzorok és CPU specifikációk
Közvetlen /proc és /sys elérés külső függőségek nélkül.
Támogatja a kikapcsolt magok 0 MHz-es állapotát, az átlagos órajelet,
a Linux CPU kormányzót és a hardveres/gyári Xeon specifikációk (Alap, Max Turbo, All-Core Turbo) megjelenítését.
"""

import os
import re
import time
import glob
import subprocess

# Ismert Xeon és szerver processzor specifikációs adatbázis
XEON_SPECS_DB = {
    'E5-2618L v4': {
        'model_clean': 'Intel Xeon E5-2618L v4',
        'arch': 'Broadwell-EP (14nm)',
        'base': 2.20,
        'all_core': 2.40,
        'max_turbo': 3.20,
        'min_freq': 1.20,
        'tdp': 75,
        'bins': [
            ('1–2 aktív mag', '3.20 GHz', 'Csúcs egy/kétmagos turbó frekvencia'),
            ('3 aktív mag', '3.10 GHz', '3 magos terhelés'),
            ('4 aktív mag', '3.00 GHz', '4 magos terhelés'),
            ('5–6 aktív mag', '2.80 – 2.90 GHz', 'Közepes terhelés'),
            ('7–8 aktív mag', '2.60 – 2.70 GHz', 'Magas terhelés'),
            ('9–10 aktív mag (Minden mag)', '2.40 GHz', 'All-Core Turbo (Teljes terhelés a 75 W TDP limit alatt)'),
            ('Garantált alapórajel', '2.20 GHz', 'Gyári alapfrekvencia terhelés alatt'),
            ('Energiatakarékos alapjárat', '1.20 GHz', 'Minimális működési frekvencia (LFM)'),
            ('Kikapcsolt mag', '0 MHz', 'Offline / Parkolt állapot')
        ],
        'explanation': (
            "Miért 2.40 GHz az órajel teljes terhelésnél?\n\n"
            "Az Intel a Broadwell-EP architektúránál a fogyasztási és hőtermelési keretek alapján szigorúan szabályozza "
            "a többmagos turbó szorzókat. Amikor mind a 10 fizikai mag (20 szál) 100%-os terhelést kap, a processzor "
            "2.40 GHz-es All-Core Turbóra áll be. Ez pontosan 200 MHz-cel lépi túl a 2.20 GHz-es alapórajelet, "
            "így garantálja, hogy a csomag fogyasztása stabilan a 75 Wattos TDP határérték alatt maradjon anélkül, "
            "hogy hőmérsékleti fojtás (thermal throttling) lépne fel."
        )
    },
    'E5-2620 v4': {
        'model_clean': 'Intel Xeon E5-2620 v4',
        'arch': 'Broadwell-EP (14nm)',
        'base': 2.10, 'all_core': 2.30, 'max_turbo': 3.00, 'min_freq': 1.20, 'tdp': 85,
        'bins': [
            ('1–2 mag', '3.00 GHz', 'Max Turbo'),
            ('8 mag (All-Core)', '2.30 GHz', 'All-Core Turbo (85 W TDP)'),
            ('Alapórajel', '2.10 GHz', 'Garantált alapfrekvencia'),
            ('Alapjárat', '1.20 GHz', 'LFM alapjárat'),
            ('Kikapcsolt', '0 MHz', 'Offline')
        ],
        'explanation': '8 magos Broadwell-EP processzor 85W TDP kerettel. Teljes terhelésnél az órajel 2.30 GHz.'
    },
    'E5-2630 v4': {
        'model_clean': 'Intel Xeon E5-2630 v4',
        'arch': 'Broadwell-EP (14nm)',
        'base': 2.20, 'all_core': 2.40, 'max_turbo': 3.10, 'min_freq': 1.20, 'tdp': 85,
        'bins': [
            ('1–2 mag', '3.10 GHz', 'Max Turbo'),
            ('10 mag (All-Core)', '2.40 GHz', 'All-Core Turbo (85 W TDP)'),
            ('Alapórajel', '2.20 GHz', 'Garantált alapfrekvencia'),
            ('Alapjárat', '1.20 GHz', 'LFM alapjárat'),
            ('Kikapcsolt', '0 MHz', 'Offline')
        ],
        'explanation': '10 magos Broadwell-EP processzor 85W TDP kerettel. Teljes terhelésnél az órajel 2.40 GHz.'
    },
    'E5-2630L v4': {
        'model_clean': 'Intel Xeon E5-2630L v4',
        'arch': 'Broadwell-EP (14nm)',
        'base': 1.80, 'all_core': 2.00, 'max_turbo': 2.90, 'min_freq': 1.20, 'tdp': 55,
        'bins': [
            ('1–2 mag', '2.90 GHz', 'Max Turbo'),
            ('10 mag (All-Core)', '2.00 GHz', 'All-Core Turbo (55 W TDP)'),
            ('Alapórajel', '1.80 GHz', 'Alapfrekvencia'),
            ('Alapjárat', '1.20 GHz', 'LFM alapjárat'),
            ('Kikapcsolt', '0 MHz', 'Offline')
        ],
        'explanation': 'Ultra alacsony fogyasztású 55W-os 10 magos Xeon. Teljes terhelésnél az órajel 2.00 GHz.'
    },
    'E5-2640 v4': {
        'model_clean': 'Intel Xeon E5-2640 v4',
        'arch': 'Broadwell-EP (14nm)',
        'base': 2.40, 'all_core': 2.60, 'max_turbo': 3.40, 'min_freq': 1.20, 'tdp': 90,
        'bins': [
            ('1–2 mag', '3.40 GHz', 'Max Turbo'),
            ('10 mag (All-Core)', '2.60 GHz', 'All-Core Turbo (90 W TDP)'),
            ('Alapórajel', '2.40 GHz', 'Alapfrekvencia'),
            ('Alapjárat', '1.20 GHz', 'LFM alapjárat'),
            ('Kikapcsolt', '0 MHz', 'Offline')
        ],
        'explanation': '10 magos 90W TDP processzor. Teljes terhelésnél 2.60 GHz-es órajellel üzemel.'
    },
    'E5-2680 v4': {
        'model_clean': 'Intel Xeon E5-2680 v4',
        'arch': 'Broadwell-EP (14nm)',
        'base': 2.40, 'all_core': 2.90, 'max_turbo': 3.30, 'min_freq': 1.20, 'tdp': 120,
        'bins': [
            ('1–2 mag', '3.30 GHz', 'Max Turbo'),
            ('14 mag (All-Core)', '2.90 GHz', 'All-Core Turbo (120 W TDP)'),
            ('Alapórajel', '2.40 GHz', 'Alapfrekvencia'),
            ('Alapjárat', '1.20 GHz', 'LFM alapjárat'),
            ('Kikapcsolt', '0 MHz', 'Offline')
        ],
        'explanation': '14 magos 120W TDP processzor. Teljes terhelésnél 2.90 GHz-es órajellel üzemel.'
    },
    'E5-2690 v4': {
        'model_clean': 'Intel Xeon E5-2690 v4',
        'arch': 'Broadwell-EP (14nm)',
        'base': 2.60, 'all_core': 3.20, 'max_turbo': 3.50, 'min_freq': 1.20, 'tdp': 135,
        'bins': [
            ('1–2 mag', '3.50 GHz', 'Max Turbo'),
            ('14 mag (All-Core)', '3.20 GHz', 'All-Core Turbo (135 W TDP)'),
            ('Alapórajel', '2.60 GHz', 'Alapfrekvencia'),
            ('Alapjárat', '1.20 GHz', 'LFM alapjárat'),
            ('Kikapcsolt', '0 MHz', 'Offline')
        ],
        'explanation': '14 magos csúcs Xeon 135W TDP-vel. Teljes terhelésnél 3.20 GHz-es órajellel üzemel.'
    },
    'E5-2678 v3': {
        'model_clean': 'Intel Xeon E5-2678 v3',
        'arch': 'Haswell-EP (22nm)',
        'base': 2.50, 'all_core': 2.90, 'max_turbo': 3.30, 'min_freq': 1.20, 'tdp': 120,
        'bins': [
            ('1–2 mag', '3.30 GHz', 'Max Turbo'),
            ('12 mag (All-Core)', '2.90 GHz', 'All-Core Turbo (120 W TDP)'),
            ('Alapórajel', '2.50 GHz', 'Alapfrekvencia'),
            ('Alapjárat', '1.20 GHz', 'LFM alapjárat'),
            ('Kikapcsolt', '0 MHz', 'Offline')
        ],
        'explanation': '12 magos népszerű Haswell-EP processzor. Teljes terhelésnél 2.90 GHz-es órajellel üzemel.'
    }
}


def get_cpu_specification(model_name, n_cores, detected_tdp=65.0):
    """
    Automatikus CPU specifikáció és turbó szintek meghatározása
    bármilyen Xeon vagy Intel processzorhoz.
    """
    for key, spec in XEON_SPECS_DB.items():
        if key in model_name:
            return spec

    # Általános intelligens meghatározás bármilyen más CPU esetén
    base_ghz = 2.0
    m = re.search(r'@\s*([\d\.]+)\s*GHz', model_name, re.I)
    if m:
        base_ghz = float(m.group(1))

    max_turbo_ghz = base_ghz
    try:
        with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
            max_turbo_ghz = int(f.read().strip()) / 1e6
    except Exception:
        pass

    min_freq_ghz = 1.20
    try:
        with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq', 'r') as f:
            min_freq_ghz = int(f.read().strip()) / 1e6
    except Exception:
        pass

    # All-Core becslés TDP és magszám alapján
    if max_turbo_ghz > base_ghz:
        all_core_ghz = round(base_ghz + (max_turbo_ghz - base_ghz) * 0.25, 2)
    else:
        all_core_ghz = base_ghz

    bins = [
        ('1–2 mag (Csúcs)', f'{max_turbo_ghz:.2f} GHz', 'Maximális egy/kétmagos turbó órajel'),
        (f'{n_cores} mag (Teljes terhelés)', f'{all_core_ghz:.2f} GHz', f'All-Core Turbo ({detected_tdp:.0f} W TDP korlát alatt)'),
        ('Garantált alapórajel', f'{base_ghz:.2f} GHz', 'Gyári alapfrekvencia folyamatos terhelésnél'),
        ('Energiatakarékos alapjárat', f'{min_freq_ghz:.2f} GHz', 'Minimális működési frekvencia (LFM)'),
        ('Kikapcsolt mag', '0 MHz', 'Offline / Parkolt állapot')
    ]

    return {
        'model_clean': model_name.replace('(R)', '').replace('(TM)', '').strip(),
        'arch': 'Intel x86_64',
        'base': base_ghz,
        'all_core': all_core_ghz,
        'max_turbo': max_turbo_ghz,
        'min_freq': min_freq_ghz,
        'tdp': detected_tdp,
        'bins': bins,
        'explanation': (
            f"A processzor gyári alapórajele {base_ghz:.2f} GHz, a maximális egy-kétmagos turbó frekvenciája pedig {max_turbo_ghz:.2f} GHz. "
            f"Minden mag 100%-os terhelése esetén az All-Core frekvencia ~{all_core_ghz:.2f} GHz körül alakul, "
            f"biztosítva a(z) {detected_tdp:.0f} W TDP fogyasztási keret betartását."
        )
    }


class SystemMetrics:
    def __init__(self):
        self.prev_stat = self._read_stat()
        self.prev_rapl = self._read_rapl()
        self.prev_time = time.time()
        self.cpu_model = self._detect_cpu_model()
        self.core_count, self.thread_count = self._detect_core_counts()
        self.cores = self.core_count
        self.threads = self.thread_count
        self.tdp = self._detect_tdp()
        self.specs = get_cpu_specification(self.cpu_model, self.core_count, self.tdp)

    def _detect_cpu_model(self):
        model = "Ismeretlen CPU"
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        model = line.split(':', 1)[1].strip()
                        break
        except Exception:
            pass
        return model

    def _detect_core_counts(self):
        threads = os.cpu_count() or 1
        cores_set = set()
        try:
            with open('/proc/cpuinfo', 'r') as f:
                curr_phys = None
                curr_core = None
                for line in f:
                    line = line.strip()
                    if line.startswith('physical id'):
                        curr_phys = line.split(':', 1)[1].strip()
                    elif line.startswith('core id'):
                        curr_core = line.split(':', 1)[1].strip()
                    if curr_phys is not None and curr_core is not None:
                        cores_set.add((curr_phys, curr_core))
                        curr_phys = None
                        curr_core = None
        except Exception:
            pass
        cores = len(cores_set) if cores_set else (threads // 2 if threads > 1 else 1)
        return cores, threads

    def is_core_online(self, i):
        online_p = f"/sys/devices/system/cpu/cpu{i}/online"
        if os.path.exists(online_p):
            try:
                with open(online_p, "r") as f:
                    return f.read().strip() == "1"
            except Exception:
                pass
        try:
            if os.path.exists("/sys/devices/system/cpu/offline"):
                with open("/sys/devices/system/cpu/offline", "r") as f:
                    off_str = f.read().strip()
                    if off_str:
                        for part in off_str.split(","):
                            if "-" in part:
                                s, e = map(int, part.split("-"))
                                if s <= i <= e:
                                    return False
                            elif part.isdigit() and int(part) == i:
                                return False
        except Exception:
            pass
        return os.path.exists(f"/sys/devices/system/cpu/cpu{i}")

    def get_available_governors(self):
        p = '/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors'
        if os.path.exists(p):
            try:
                with open(p, 'r') as f:
                    govs = f.read().strip().split()
                    if govs:
                        return govs
            except Exception:
                pass
        return ['ondemand', 'powersave', 'performance', 'conservative', 'schedutil']

    def get_current_governor(self):
        p = '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'
        if os.path.exists(p):
            try:
                with open(p, 'r') as f:
                    return f.read().strip()
            except Exception:
                pass
        return 'ondemand'

    def set_governor(self, gov_name):
        gov_files = glob.glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor')
        if not gov_files:
            return False

        direct_failed = False
        success = True
        for gf in gov_files:
            try:
                with open(gf, 'w') as f:
                    f.write(gov_name)
            except (PermissionError, OSError):
                direct_failed = True
                break
            except Exception:
                success = False

        if direct_failed:
            try:
                cmd = f'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo "{gov_name}" > "$f" 2>/dev/null; done'
                subprocess.run(['pkexec', 'sh', '-c', cmd], check=True)
                return True
            except Exception:
                return False

        return success

    def _read_stat(self):
        data = {}
        try:
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if line.startswith('cpu'):
                        parts = line.strip().split()
                        name = parts[0]
                        vals = [int(x) for x in parts[1:]]
                        busy = vals[0] + vals[1] + vals[2]
                        if len(vals) > 5: busy += vals[5]
                        if len(vals) > 6: busy += vals[6]
                        if len(vals) > 7: busy += vals[7]
                        total = sum(vals)
                        data[name] = (busy, total)
        except Exception:
            pass
        return data

    def _read_rapl(self):
        rapl_files = glob.glob('/sys/class/powercap/intel-rapl/intel-rapl:*/energy_uj')
        total_energy = 0
        found = False
        for rf in rapl_files:
            try:
                with open(rf, 'r') as f:
                    total_energy += int(f.read().strip())
                    found = True
            except Exception:
                pass
        return total_energy if found else None

    def _detect_tdp(self):
        limit_files = glob.glob('/sys/class/powercap/intel-rapl/intel-rapl:*/constraint_0_power_limit_uw')
        for lf in limit_files:
            try:
                with open(lf, 'r') as f:
                    uw = int(f.read().strip())
                    if uw > 0:
                        return uw / 1e6
            except Exception:
                pass
        return 65.0

    def get_memory_info(self):
        total_kb = 0
        avail_kb = 0
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        total_kb = int(line.split()[1])
                    elif line.startswith('MemAvailable:'):
                        avail_kb = int(line.split()[1])
        except Exception:
            pass
        used_kb = max(0, total_kb - avail_kb)
        pct = (used_kb / total_kb * 100.0) if total_kb > 0 else 0.0
        return {
            'total_gb': total_kb / (1024.0 * 1024.0),
            'used_gb': used_kb / (1024.0 * 1024.0),
            'pct': pct
        }

    def update(self):
        curr_time = time.time()
        dt = curr_time - self.prev_time
        if dt <= 0.001:
            dt = 0.001
        self.prev_time = curr_time

        ncpu = self.thread_count
        online_status = [self.is_core_online(i) for i in range(ncpu)]
        active_count = sum(online_status)

        # CPU Terhelés számítás
        curr_stat = self._read_stat()
        loads = {}
        for k in curr_stat:
            if k in self.prev_stat:
                b1, t1 = self.prev_stat[k]
                b2, t2 = curr_stat[k]
                db = b2 - b1
                dtot = t2 - t1
                load = (db / dtot * 100.0) if dtot > 0 else 0.0
                loads[k] = max(0.0, min(100.0, load))
            else:
                loads[k] = 0.0
        self.prev_stat = curr_stat

        # Fogyasztás
        curr_rapl = self._read_rapl()
        power_w = 0.0
        power_is_real = False
        if curr_rapl is not None and self.prev_rapl is not None and dt > 0:
            de = curr_rapl - self.prev_rapl
            if de >= 0:
                power_w = de / (dt * 1e6)
                power_is_real = True
        self.prev_rapl = curr_rapl

        tot_load = loads.get('cpu', 0.0)
        if not power_is_real:
            power_w = self.tdp * (0.15 + 0.85 * (tot_load / 100.0))

        # Órajelek magonként
        freqs = {}
        for i in range(ncpu):
            if not online_status[i]:
                freqs[f"cpu{i}"] = 0.0
                loads[f"cpu{i}"] = 0.0
                continue

            p = f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq"
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        freqs[f"cpu{i}"] = int(f.read().strip()) / 1000.0 # MHz
                except Exception:
                    freqs[f"cpu{i}"] = 0.0
            else:
                freqs[f"cpu{i}"] = 0.0

        if sum(freqs.values()) == 0 and active_count > 0:
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    idx = 0
                    for line in f:
                        if line.startswith('cpu MHz'):
                            val = float(line.split(':', 1)[1].strip())
                            if idx < ncpu and online_status[idx]:
                                freqs[f'cpu{idx}'] = val
                            elif idx < ncpu:
                                freqs[f'cpu{idx}'] = 0.0
                            idx += 1
            except Exception:
                pass

        # Átlagos órajel
        active_freq_list = [freqs[f"cpu{i}"] for i in range(ncpu) if online_status[i] and freqs.get(f"cpu{i}", 0.0) > 0]
        avg_freq = (sum(active_freq_list) / len(active_freq_list)) if active_freq_list else 0.0

        # Aktuális kormányzó
        curr_gov = self.get_current_governor()

        # Hőmérsékletek
        pkg_temp = None
        core_temps = {}
        for h in glob.glob('/sys/class/hwmon/hwmon*'):
            for t_in in glob.glob(os.path.join(h, 'temp*_input')):
                try:
                    lbl_f = t_in.replace('_input', '_label')
                    lbl = ''
                    if os.path.exists(lbl_f):
                        with open(lbl_f, 'r') as f:
                            lbl = f.read().strip()
                    val = int(open(t_in).read().strip()) / 1000.0
                    if any(x in lbl for x in ['Package', 'Tdie', 'Tctl']):
                        pkg_temp = val
                    elif 'Core' in lbl:
                        core_temps[lbl] = val
                    elif pkg_temp is None:
                        pkg_temp = val
                except Exception:
                    pass

        if pkg_temp is None:
            for tz in glob.glob('/sys/class/thermal/thermal_zone*/temp'):
                try:
                    val = int(open(tz).read().strip()) / 1000.0
                    if 10.0 <= val <= 115.0:
                        pkg_temp = val
                        break
                except Exception:
                    pass

        mem = self.get_memory_info()

        return {
            'cpu_model': self.cpu_model,
            'cores': self.core_count,
            'threads': self.thread_count,
            'active_threads': active_count,
            'online_status': online_status,
            'specs': self.specs,
            'total_load': tot_load,
            'core_loads': [loads.get(f'cpu{i}', 0.0) if online_status[i] else 0.0 for i in range(ncpu)],
            'frequencies': [freqs.get(f'cpu{i}', 0.0) for i in range(ncpu)],
            'avg_freq': avg_freq,
            'governor': curr_gov,
            'power_w': power_w,
            'power_real': power_is_real,
            'tdp': self.tdp,
            'pkg_temp': pkg_temp or 0.0,
            'core_temps': core_temps,
            'memory': mem
        }
