#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dinamikus, univerzális CPU detektáló és formázó Conky-hoz.
Automatikusan felismeri a processzor modelljét, a fizikai magok számát,
a logikai szálak (Hyper-Threading / SMT) összerendelését és a hardveres
hőmérsékleteket sysfs-ből (Intel coretemp, AMD k10temp/zenpower).
"""

import sys
import glob
import os
import re

def get_cpu_model():
    model = 'Processzor'
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'model name' in line:
                    model = line.split(':', 1)[1].strip()
                    break
    except Exception:
        pass
    model = re.sub(r'\(R\)|\(TM\)|CPU|@.*', '', model)
    model = re.sub(r'\s+', ' ', model).strip()
    return model

def get_topology():
    """
    Visszaadja a fizikai magok listáját és a hozzájuk tartozó Conky CPU indexeket (1-alapú).
    Formátum: [(physical_core_id, [conky_thread_idx1, conky_thread_idx2, ...]), ...]
    """
    cpu_dirs = sorted(glob.glob('/sys/devices/system/cpu/cpu[0-9]*'), 
                      key=lambda p: int(os.path.basename(p)[3:]))
    cores_dict = {}
    for cd in cpu_dirs:
        top_dir = os.path.join(cd, 'topology')
        if not os.path.exists(top_dir):
            continue
        try:
            with open(os.path.join(top_dir, 'core_id'), 'r') as f:
                cid = int(f.read().strip())
            with open(os.path.join(top_dir, 'thread_siblings_list'), 'r') as f:
                sib_str = f.read().strip()
                sibs = []
                for part in sib_str.split(','):
                    if '-' in part:
                        s, e = map(int, part.split('-'))
                        sibs.extend(range(s, e + 1))
                    else:
                        sibs.append(int(part))
            if cid not in cores_dict:
                # Conky index = linux CPU id + 1 (mivel cpu0 a teljes CPU)
                cores_dict[cid] = [s + 1 for s in sorted(sibs)]
        except Exception:
            pass

    sorted_cores = sorted(cores_dict.items(), key=lambda x: x[0])
    return sorted_cores

def get_hwmon_temps():
    temps = {}
    pkg_temp = "N/A"
    
    hwmon_dirs = glob.glob('/sys/class/hwmon/hwmon*')
    cpu_hwmon = None
    for h in hwmon_dirs:
        try:
            with open(os.path.join(h, 'name'), 'r') as f:
                n = f.read().strip().lower()
                if 'coretemp' in n or 'k10temp' in n or 'zenpower' in n:
                    cpu_hwmon = h
                    break
        except Exception:
            pass

    if not cpu_hwmon and hwmon_dirs:
        cpu_hwmon = hwmon_dirs[0]

    if cpu_hwmon:
        for lp in glob.glob(os.path.join(cpu_hwmon, 'temp*_label')):
            ip = lp.replace('_label', '_input')
            try:
                with open(lp, 'r') as fl, open(ip, 'r') as fi:
                    lbl = fl.read().strip()
                    val = int(fi.read().strip()) // 1000
                    if lbl.startswith('Core '):
                        cid = int(lbl.split()[1])
                        temps[cid] = val
                    elif any(k in lbl for k in ['Package', 'Tdie', 'Tctl']):
                        pkg_temp = f"{val}°C"
            except Exception:
                pass
        if pkg_temp == "N/A":
            t1 = os.path.join(cpu_hwmon, 'temp1_input')
            if os.path.exists(t1):
                try:
                    with open(t1, 'r') as fi:
                        pkg_temp = f"{int(fi.read().strip()) // 1000}°C"
                except Exception:
                    pass

    return temps, pkg_temp

def main():
    if '--header' in sys.argv:
        model = get_cpu_model()
        cores = get_topology()
        num_cores = len(cores) if cores else 1
        num_threads = os.cpu_count() or num_cores
        print(f"{model} ({num_cores} Mag / {num_threads} Szál)")
        return

    if '--pkg' in sys.argv:
        _, pkg_temp = get_hwmon_temps()
        print(pkg_temp)
        return

    cores = get_topology()
    temps, _ = get_hwmon_temps()

    if not cores:
        print("${font Open Sans:size=8}CPU topológia nem elérhető$font")
        return

    voff = "${voffset -3}" if len(cores) >= 16 else "${voffset -1}"
    for idx, (cid, threads) in enumerate(cores, 1):
        temp_val = temps.get(cid, None)
        temp_str = f"{temp_val:2d}°C" if temp_val is not None else "--°C"

        if len(threads) == 2:
            t1, t2 = threads[0], threads[1]
            line = (
                f"{voff}${{font Open Sans:size=8}}${{color}}Mag {idx:02d}: "
                f"${{color3}}{temp_str}${{color}}"
                f"${{goto 88}}${{color}}Sz{t1:02d}: ${{color2}}${{cpubar 4,56 cpu{t1}}}${{color}}"
                f"${{goto 188}}${{color}}Sz{t2:02d}: ${{color2}}${{cpubar 4,58 cpu{t2}}}${{color}}"
            )
        elif len(threads) == 1:
            t1 = threads[0]
            line = (
                f"${{font Open Sans:size=8}}${{color}}Mag {idx:02d}: "
                f"${{color3}}{temp_str}${{color}}  "
                f"${{goto 88}}${{color}}Szál {t1:02d}: ${{color2}}${{cpubar 5,145 cpu{t1}}}${{color}}"
            )
        else:
            line = f"${{font Open Sans:size=8}}${{color}}Mag {idx:02d}: ${{color3}}{temp_str}${{color}}"
            for tid in threads[:4]:
                line += f" ${{color2}}${{cpubar 5,30 cpu{tid}}}${{color}}"

        print(line)

if __name__ == '__main__':
    main()
