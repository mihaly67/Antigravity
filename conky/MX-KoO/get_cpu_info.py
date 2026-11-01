#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Könnyűsúlyú CPU mag- és hőmérséklet-kinyerő Conky-hoz.
Közvetlenül a /sys/class/hwmon interfészt olvassa (0 subprocess, <1ms futási idő).
"""

import sys
import glob
import os

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
    cores = []
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
                        cores.append((cid, val))
                    elif 'Package' in lbl:
                        pkg_temp = f"{val}°C"
            except Exception:
                pass

    if '--pkg' in sys.argv:
        print(pkg_temp)
        return

    # Default or --cores: format 2-column grid
    cores.sort(key=lambda x: x[0])
    if not cores:
        # Fallback if no coretemp
        for i in range(1, 5):
            print(f"${{font Open Sans:size=8}}${{color}}Core {i-1}:${{alignr}}${{color2}}${{cpubar 5,120 cpu{i}}}${{color}}")
        return

    mid = (len(cores) + 1) // 2
    left = cores[:mid]
    right = cores[mid:]

    for i in range(len(left)):
        c_l, t_l = left[i]
        cpu_idx_l = i + 1
        line = f"${{font Open Sans:size=8}}${{color}}C{c_l}: ${{color3}}{t_l}°C ${{color2}}${{cpubar 5,45 cpu{cpu_idx_l}}}${{color}}"
        if i < len(right):
            c_r, t_r = right[i]
            cpu_idx_r = mid + i + 1
            line += f"${{goto 146}}${{color}}C{c_r}: ${{color3}}{t_r}°C ${{color2}}${{cpubar 5,45 cpu{cpu_idx_r}}}${{color}}"
        print(line)

if __name__ == '__main__':
    main()
