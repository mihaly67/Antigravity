#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dinamikus lemez és csatolt meghajtó figyelő Conky-hoz.
Automatikusan felismeri a később csatlakoztatott külső USB meghajtókat,
másodlagos partíciókat és hálózati megosztásokat, majd megjeleníti
azokat a /home tárhely alatti területen.
"""

import os
import glob

EXCLUDED_FS = {
    'sysfs', 'proc', 'devtmpfs', 'devpts', 'tmpfs', 'cgroup', 'cgroup2', 
    'pstore', 'bpf', 'autofs', 'ramfs', 'hugetlbfs', 'mqueue', 'debugfs', 
    'tracefs', 'fusectl', 'configfs', 'securityfs', 'efivarfs', 'squashfs',
    'fuse.gvfsd-fuse'
}
EXCLUDED_MOUNTS = {'/', '/home', '/boot', '/boot/efi'}

def get_disk_labels():
    labels = {}
    if os.path.exists('/dev/disk/by-label'):
        for p in glob.glob('/dev/disk/by-label/*'):
            try:
                real_dev = os.path.realpath(p)
                labels[real_dev] = os.path.basename(p)
            except Exception:
                pass
    return labels

def main():
    labels = get_disk_labels()
    mounts = []
    seen = set()

    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    dev, mnt, fstype = parts[0], parts[1], parts[2]
                    
                    if fstype in EXCLUDED_FS or mnt in EXCLUDED_MOUNTS or mnt in seen:
                        continue
                    if dev.startswith('/dev/loop') or dev.startswith('/dev/ram'):
                        continue

                    # Valós blokkeszközök (/dev/sd*, /dev/nvme*, /dev/mmcblk*, mapper)
                    # vagy /media/, /mnt/, /run/media/ alatti csatolási pontok
                    is_real_device = dev.startswith('/dev/') or dev.startswith('/dev/mapper/')
                    is_media_path = any(mnt.startswith(prefix) for prefix in ['/media/', '/mnt/', '/run/media/'])

                    if is_real_device or is_media_path:
                        seen.add(mnt)
                        # Meghajtó neve: címke > mappa neve > eszköz neve
                        name = labels.get(dev, None)
                        if not name:
                            name = os.path.basename(mnt.rstrip('/'))
                        if not name or name == '/':
                            name = os.path.basename(dev)
                        
                        mounts.append((name, mnt, fstype))
    except Exception:
        pass

    if not mounts:
        return

    # Formázás a Conky felületre
    for name, mnt, fstype in mounts:
        print(f"${{voffset -6}}${{font Open Sans:bold:size=8}}Csatolt tár ({name})$font$alignr${{fs_used {mnt}}} / ${{fs_size {mnt}}} ({fstype})")
        print(f"$alignr Használt: ${{fs_used_perc {mnt}}}%")
        print(f"${{color2}}${{fs_bar 4 {mnt}}}${{color}}")

if __name__ == '__main__':
    main()

