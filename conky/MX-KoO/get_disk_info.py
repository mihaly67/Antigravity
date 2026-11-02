#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dinamikus lemez és csatolt meghajtó figyelő Conky-hoz.
Automatikusan felismeri a másodlagos partíciókat (pl. /data), a később
csatlakoztatott külső USB meghajtókat és hálózati megosztásokat, majd megjeleníti
azokat a /home tárhely alatti területen (kiszűrve a bind-mount duplikációkat).
"""

import os
import glob

EXCLUDED_FS = {
    'sysfs', 'proc', 'devtmpfs', 'devpts', 'tmpfs', 'cgroup', 'cgroup2',
    'pstore', 'bpf', 'autofs', 'ramfs', 'hugetlbfs', 'mqueue', 'debugfs',
    'tracefs', 'fusectl', 'configfs', 'securityfs', 'efivarfs', 'squashfs',
    'fuse.gvfsd-fuse', 'fuse.portal', 'nsfs', 'overlay'
}
EXCLUDED_MOUNTS = {
    '/', '/home', '/boot', '/boot/efi', '/bin', '/sbin', '/usr', '/lib',
    '/lib64', '/var', '/tmp', '/opt', '/srv', '/etc', '/root', '/proc', '/sys', '/dev'
}
EXCLUDED_PREFIXES = (
    '/dev/', '/proc/', '/sys/', '/run/credentials', '/run/user', '/run/lock',
    '/var/', '/usr/', '/lib', '/etc/', '/home/'
)


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
    seen_mounts = set()
    seen_devs = set()

    raw_entries = []
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    dev, mnt, fstype = parts[0], parts[1], parts[2]
                    real_dev = os.path.realpath(dev) if dev.startswith('/dev/') else dev
                    raw_entries.append((dev, real_dev, mnt, fstype))
                    if mnt in ('/', '/home', '/boot', '/boot/efi'):
                        seen_devs.add(real_dev)
    except Exception:
        pass

    for dev, real_dev, mnt, fstype in raw_entries:
        if fstype in EXCLUDED_FS or mnt in EXCLUDED_MOUNTS or mnt in seen_mounts:
            continue
        if any(mnt.startswith(pref) for pref in EXCLUDED_PREFIXES):
            continue
        if dev.startswith('/dev/loop') or dev.startswith('/dev/ram') or not mnt.startswith('/'):
            continue

        is_real_device = dev.startswith('/dev/') or dev.startswith('/dev/mapper/')
        is_media_path = any(mnt.startswith(prefix) for prefix in ('/media/', '/mnt/', '/run/media/'))

        if is_real_device or is_media_path:
            if is_real_device and real_dev in seen_devs:
                continue
            seen_mounts.add(mnt)
            if is_real_device:
                seen_devs.add(real_dev)

            name = labels.get(real_dev, None) or labels.get(dev, None)
            if not name:
                name = os.path.basename(mnt.rstrip('/'))
            if not name or name == '/':
                name = os.path.basename(dev)

            mounts.append((name, mnt, fstype))

    if not mounts:
        return

    for name, mnt, fstype in mounts:
        print(f"${{voffset -6}}${{font Open Sans:bold:size=8}}Csatolt tár ({name})$font$alignr${{fs_used {mnt}}} / ${{fs_size {mnt}}} ({fstype})")
        print(f"$alignr Használt: ${{fs_used_perc {mnt}}}%")
        print(f"${{color2}}${{fs_bar 4 {mnt}}}${{color}}")


if __name__ == '__main__':
    main()
