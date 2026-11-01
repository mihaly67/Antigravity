#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Könnyűsúlyú CPU mag- és szál-kinyerő Conky-hoz.
Közvetlenül a /sys/class/hwmon kernel interfészt olvassa (0 subprocess overhead).
Pontos összerendelés a 10 fizikai mag és a 20 logikai szál (Hyper-Threading) között.
"""

import sys
import glob
import os

# Fizikai magok és logikai szálak pontos megfeleltetése az E5-2618L v4 architektúrán
# raw_core_id -> (megjelenített mag sorszám 1-10, 1. szál Conky index, 2. szál Conky index)
CORE_MAP = {
    0: (1, 1, 11),
    1: (2, 2, 12),
    2: (3, 3, 13),
    3: (4, 4, 14),
    4: (5, 5, 15),
    8: (6, 6, 16),
    9: (7, 7, 17),
    10: (8, 8, 18),
    11: (9, 9, 19),
    12: (10, 10, 20)
}

def get_coretemp():
    for h in glob.glob('/sys/class/hwmon/hwmon*'):
        try:
            with open(os.path.join(h, 'name'), 'r') as f:
                if 'coretemp' in f.read():
                    return h
        except Exception:
            pass
    return None

def main():
    hw = get_coretemp()
    temps = {}
    pkg_temp = "N/A"

    if hw:
        for lp in glob.glob(os.path.join(hw, 'temp*_label')):
            ip = lp.replace('_label', '_input')
            try:
                with open(lp, 'r') as fl, open(ip, 'r') as fi:
                    lbl = fl.read().strip()
                    val = int(fi.read().strip()) // 1000
                    if lbl.startswith('Core '):
                        cid = int(lbl.split()[1])
                        temps[cid] = val
                    elif 'Package' in lbl:
                        pkg_temp = f"{val}°C"
            except Exception:
                pass

    if '--pkg' in sys.argv:
        print(pkg_temp)
        return

    # Megjelenítés: 10 fizikai mag és a 20 logikai szál
    for raw_id in sorted(CORE_MAP.keys(), key=lambda x: CORE_MAP[x][0]):
        disp_num, t1, t2 = CORE_MAP[raw_id]
        temp = temps.get(raw_id, 0)
        line = (
            f"${{font Open Sans:size=8}}${{color}}Mag {disp_num:02d}: "
            f"${{color3}}{temp:2d}°C${{color}}  "
            f"${{goto 88}}${{color}}Sz{t1:02d}: ${{color2}}${{cpubar 5,50 cpu{t1}}}${{color}}  "
            f"${{goto 182}}${{color}}Sz{t2:02d}: ${{color2}}${{cpubar 5,50 cpu{t2}}}${{color}}"
        )
        print(line)

if __name__ == '__main__':
    main()
