# Antigravity — MX Linux Rendszermonitor és Segédeszköz Csomag

Átfogó, hardverközeli rendszermonitorozó és felügyeleti eszközkészlet MX Linux (Debian 12 / SysVinit / X11) környezetre optimalizálva.

## 🚀 Komponensek és Eszközök

### 1. Conky Rendszermonitor (`conky/MX-KoO/`)
- **Intel Xeon E5 v3/v4 & többmagos topológia támogatás:** Automatikus fizikai mag és logikai szál (HT/SMT) párosítás, tokozási és magonkénti hőmérséklet-kijelzés.
- **Dinamikus meghajtó-kezelés (`get_disk_info.py`):** Automatikusan felismeri a csatlakoztatott külső USB lemezeket és másodlagos partíciókat a `/home` alatt, kiszűrve a duplikációkat és bind-mountokat.
- **Kompakt kialakítás:** 900p / 1080p kijelzőkre optimalizált függőleges térközök, tiszta magyar felület.

### 2. MX CPU Monitor (`main.py`, `metrics.py`, `pkg/`)
- Valós idejű magonkénti órajel, feszültség, RAPL fogyasztásmérés.
- Hardveres CPU governor vezérlő (powersave, performance, schedutil) és SysVinit újraindítás-biztos állapotmegőrzés.
- Tálcán futás (`--minimized`, `--hidden`).

### 3. MX Hardver Monitor (`tools/mx-hardware-monitor/`)
- Teljes GPU telemetria: NVIDIA NVS 310 / Fermi és Nouveau meghajtó natív DRM sysfs integráció.
- Valós idejű GPU terhelés, hőfok (~44°C), ventilátor-fordulatszám (~2150 RPM), VRAM használat és becsült fogyasztás.

### 4. MX SSH & Tailscale Monitor (`tools/mx-ssh-monitor/`)
- Valós idejű SSH kapcsolatok és Tailscale hálózati csomópont állapot követése.
- Tálcán futó értesítések és gyors kapcsolódás.

### 5. MX Biztonsági Irányítópult (`tools/mx-security-dashboard/`)
- Nyitott portok, tűzfal (iptables/ufw), aktív hálózati szolgáltatások és bejelentkezési kísérletek vizsgálata.

### 6. MX VNC Központ & Tálca Indikátor (`tools/mx-vnc-server/`)
- Valós idejű VNC szerver felügyelet a KDE tálcán (`🟢 Figyel :5900`, `🔵 Csatlakozva`, `🔴 Leállítva`).
- Helyi LAN (`192.168.1.105:5900`) és Tailscale VPN (`100.118.197.74:5900`) címek egykattintásos vágólapra másolása.
- Kliens és gazda végpont: egykattintásos Remmina VNC/RDP kapcsolatkezelő és TigerVNC gyors-kliens indítás.
- Headless működés támogatása: monitor, billentyűzet és egér nélküli rendszerindítás virtuális 1080p DP-1 kerettel.
- Párhuzamos bemenetkezelés: a távoli vezérlés és a helyi fizikai perifériák egyidejűleg használhatók.

### 7. További Eszközök
- **MX RAM Cleaner (`tools/mx-ram-cleaner/`):** Linux cache és memória kíméletes felszabadítása.
- **MX CPU/GPU Stressz Teszt (`tools/mx-cpu-gpu-stress-test/`):** Hardveres terhelésteszt és stabilitás-ellenőrzés.

---

## 📦 Telepítőcsomagok (.deb)
A legfrissebb előre fordított Debian csomagok a [`packages/`](file:///home/misi/Antigravity/packages) mappában találhatók:
- `mx-cpu-monitor_1.0.6-1_all.deb`
- `mx-hardware-monitor_1.0.8_all.deb`
- `mx-ssh-monitor_1.1.3_all.deb`
- `mx-security-dashboard_1.0.0_all.deb`
- `mx-vnc-server_1.0.0_all.deb`
- `mx-ram-cleaner_1.0.3_all.deb`
- `mx-cpu-gpu-stress-test_1.1.8_all.deb`

Telepítés:
```bash
sudo dpkg -i packages/<csomagnév>.deb
```

---

## 🔄 Automatikus Szinkronizáció
A rendszer automatikus szinkronizációját a [`scripts/git-autopush.sh`](file:///home/misi/Antigravity/scripts/git-autopush.sh) démon végzi.
- Ciklikusan összegyűjti a módosított konfigurációkat és forrásokat.
- Automatikus commitot és pusht hajt végre a `main` ágra: `https://github.com/mihaly67/Antigravity`.
