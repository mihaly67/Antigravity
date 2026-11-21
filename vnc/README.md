# MX Kölcsönös VNC Rendszerarchitektúra & Kézikönyv

Ez a modul a hálózatban lévő 3 csomópont (**`mx`**, **`mx-1`** és **`jules`**) közötti **kölcsönös, kétirányú távoli asztal elérést**, felügyeletet és automatikus hibatűrést valósítja meg.

---

## 1. Érintett Gépek és Hálózati Topológia

A gépek fizikai gigabites helyi hálózaton (LAN) és globális titkosított WireGuard hálózaton (Tailscale Mesh VPN) keresztül is össze vannak kötve:

| Gép Azonosító | Szerepkör | Processzor (CPU) | Helyi LAN IP | Tailscale VPN IP | Felhasználó / Jelszó |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`mx-1`** | Gazdagép (Host) | Intel Xeon E5-2640 v4 (20 szál) | `192.168.1.105` | `100.118.197.74` | `misi` / `1104` |
| **`mx`** | Másik gép (Peer) | AMD Phenom II X4 945 (4 mag) | `192.168.1.106` | `100.95.215.75` | `Misi` / `1104` |
| **`jules`** | Fejlesztői környezet | Jules Cloud / Devbox | *dinamikus* | `100.77.191.66` | `jules` / `1104` |

* **Alapértelmezett VNC port:** `5900/tcp` (mindkét gépen engedélyezve az UFW tűzfalban).
* **Alapértelmezett VNC jelszó:** `1104` (automatikus bejelentkezés, jelszókérés nélküli csatlakozás).

---

## 2. Intelligens Útvonalválasztás és Auto-Failover

A távoli kapcsolódást az [`mx-vnc-connect`](file:///home/misi/Antigravity/vnc/mx-vnc-connect) okos parancsfájl vezérli:

```mermaid
flowchart TD
    A["Indítás: Asztali ikon vagy Tálcamenü"] --> B{"Van célpont megadva?<br/>(mx / mx1 / jules)"}
    B -->|Nem| C["Helyi gép IP automatikus detektálása"]
    B -->|Igen| D["Célgép kiválasztása paraméter alapján"]
    C --> D
    D --> E{"Elérhető a célgép LAN-on?<br/>Port 5900 teszt (nc -zv -w 1)"}
    E -->|Igen (Nyitva)| F["Csatlakozás Gigabit LAN-on keresztül<br/>(192.168.1.x:5900) - Min. késleltetés"]
    E -->|Nem| G{"Elérhető Tailscale VPN-en?<br/>Port 5900 teszt (100.x.x.x)"}
    G -->|Igen (Nyitva)| H["Csatlakozás Tailscale VPN-en keresztül<br/>(100.x.x.x:5900) - Titkosított csatorna"]
    G -->|Nem| I["Alapértelmezett LAN cím hívása hibajelzéssel"]
    F --> J["VNC jelszó (1104) automatikus betöltése"]
    H --> J
    I --> J
    J --> K["TigerVNC / vncviewer ablak azonnali indítása"]
```

### Parancssori használat
```bash
# Automatikus csatlakozás a másik helyi partnerhez (mx-1 -> mx, vagy mx -> mx-1):
mx-vnc-connect

# Közvetlen csatlakozás az mx (Phenom) géphez:
mx-vnc-connect mx

# Közvetlen csatlakozás az mx-1 (Xeon) géphez:
mx-vnc-connect mx1

# Csatlakozás a Jules géphez:
mx-vnc-connect jules

# Csatlakozás egyedi IP-címre:
mx-vnc-connect 192.168.1.50
```

---

## 3. Rendszerkomponensek és Fájlstruktúra

A csomag és a forrásfájlok elhelyezkedése a tárolóban:

```
vnc/
├── README.md                 # Ez a részletes rendszerleírás
├── build-deb.sh              # 1-kattintásos Debian .deb csomagépítő
├── mx-vnc-connect            # Auto LAN/VPN failover kliens indító szkript
├── mx-vnc-connect.desktop    # Asztali indítóikon (1-kattintásos távvezérlés)
├── mx-vnc-server             # Tálcaalkalmazást indító háttér-wrapper
├── mx-vnc-server.desktop     # Rendszerindításkor induló tálcaikon (Autostart)
├── mx-vnc-server.sudoers     # Jelszómentes (NOPASSWD) szervervezérlési szabály
├── mx-vnc-server.svg         # Vektoros hálózati monitor ikon
├── mx_vnc_tray.py            # PyQt5 valós idejű állapotjelző és tálcamenü
├── x11vnc-service.sh         # Folyamatos újraindító felügyelő (daemon supervisor)
└── x11vnc.init               # SysVinit LSB szolgáltatás (/etc/init.d/x11vnc)
```

### Telepített rendszerszintű elemek:
1. **SysVinit háttérszolgáltatás:**
   * `/etc/init.d/x11vnc` (Runlevel 2, 3, 4, 5 alatt aktív).
   * `/usr/local/bin/x11vnc-service.sh`: Figyeli az X11 displayt (`:0`), kijelentkezés vagy újraindítás esetén automatikusan újraindítja a kiszolgálót.
   * Headless üzemmód: Fizikai monitor és perifériák nélkül is fut.
2. **PyQt5 Tálca Indikátor (`/usr/bin/mx_vnc_tray.py`):**
   * 🟢 **Zöld (Figyel):** Port 5900 nyitva, bejövő kapcsolatra készen.
   * 🔵 **Kék (Csatlakozva):** Aktív távoli kliens vezérli a képernyőt.
   * 🔴 **Piros (Leállítva):** Kiszolgáló inaktív.
   * **Gyorsfunkciók a tálcamenüből:**
     * Helyi LAN és Tailscale IP azonnali vágólapra másolása.
     * Csatlakozás a másik géphez (külön almenü: Automatikus / MX / MX-1 / Jules).
     * Szerver indítása, leállítása és újraindítása jelszókérés nélkül.
3. **Biztonság és Jogosultságok:**
   * `/etc/sudoers.d/mx-vnc-server`: `0440` jogosultság, `root:root` tulajdon.
   * Szabály: `ALL ALL=(root) NOPASSWD: /usr/sbin/service x11vnc *, /etc/init.d/x11vnc *`

---

## 4. Telepítés és Csomagkészítés

A rendszer egyetlen önálló `.deb` csomagba van csomagolva (`mx-vnc-server_1.1.0_all.deb`), amely mindkét gépre telepíthető:

### Csomag újrafordítása:
```bash
cd /home/misi/Antigravity/vnc
./build-deb.sh
```

### Telepítés a helyi gépre (`mx-1`):
```bash
sudo dpkg -i /home/misi/Antigravity/packages/mx-vnc-server_1.1.0_all.deb
sudo apt-get install -f -y
```

### Telepítés a másik gépre (`mx`):
```bash
scp /home/misi/Antigravity/packages/mx-vnc-server_1.1.0_all.deb Misi@192.168.1.106:/home/Misi/Letöltések/
ssh Misi@192.168.1.106 "echo 1104 | sudo -S dpkg -i /home/Misi/Letöltések/mx-vnc-server_1.1.0_all.deb && echo 1104 | sudo -S apt-get install -f -y"
```

---

## 5. Tűzfal és Hálózati Ellenőrzés

Mindkét gépen az UFW (Uncomplicated Firewall) kezeli a védelmet:

```bash
# Engedélyezett szabályok mindkét gépen:
sudo ufw allow from 192.168.1.0/24
sudo ufw allow 22/tcp
sudo ufw allow 5900/tcp
```

### Kapcsolat ellenőrzése parancssorból:
```bash
# Port 5900 vizsgálata mx gépen mx-1-ről:
nc -zv -w 2 192.168.1.106 5900
nc -zv -w 2 100.95.215.75 5900

# Port 5900 vizsgálata mx-1 gépen mx-ről:
nc -zv -w 2 192.168.1.105 5900
nc -zv -w 2 100.118.197.74 5900
```

---

## 6. Monitor Nélküli (Headless) és Kijelző Hibaelhárítás (NVIDIA NVS 310 / MX-1)

Az `mx-1` gép (HP Z440 Workstation, NVIDIA NVS 310 kártya `nouveau` meghajtóval) monitor nélküli (headless) VNC használatakor, illetve passzív átalakítók esetén speciális konfigurációt igényel.

### 6.1. Feltárt Gyökérokok (Root Cause Analysis)

1. **Hiányzó EDID adat és hibás felbontás:**
   * Ha nincs csatlakoztatva monitor, vagy a DP->HDMI / DP->VGA adapter nem ad át DDC jelet, az EDID mérete 0 byte.
   * Xorg konfiguráció nélkül az automatikus módválasztó egy elavult CRT módot (**2048x1536 @ 60Hz**) kényszerít a kimenetre, amit a modern LCD monitorok nem képesek megjeleníteni (*Out of Range* / fekete képernyő).
2. **Kernel Driver Összeomlás (Crash) hibás GRUB beállítás miatt:**
   * Ha a GRUB-ban a `video=DP-1:1920x1080@60e` paraméterrel próbáljuk kényszeríteni a portot, a `nouveau` driver az indulás 10. másodpercében elbukja a DisplayPort link traininget, és **0-val való osztási hibával összeomlik a kernelben** (`divide error: 0000 [#1] nv50_disp_super_2_2`).
   * Ez a hiba teljesen lefagyasztja a GPU kijelzővezérlőjét (`DRM: core notifier timeout`), és a kártya semmilyen képet nem tud kiküldeni, VNC-n sem.

### 6.2. A Helyes és Működő Megoldás

#### 1. A GRUB tisztítása
A kernel parancssorából el kell távolítani a kártékony `video=...` opciót:
Fájl: `/etc/default/grub`
```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
```
Módosítás után érvényesíteni kell:
```bash
sudo update-grub
```

#### 2. Xorg Monitorkonfiguráció (`10-monitor.conf`)
A felbontást nem a kernelben, hanem az Xorg szintjén kell rögzíteni. A tárolóban megtalálható a [`10-monitor.conf`](file:///home/misi/Antigravity/vnc/10-monitor.conf) fájl, melyet az `/etc/X11/xorg.conf.d/10-monitor.conf` helyre kell elhelyezni:

```xorg
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
    Option "DPMS" "false"
EndSection

Section "Monitor"
    Identifier "DP-1"
    Modeline "1920x1080" 148.50 1920 2008 2052 2200 1080 1084 1089 1125 +hsync +vsync
    Option "Enable" "true"
    Option "PreferredMode" "1920x1080"
    Option "Primary" "true"
EndSection

Section "Device"
    Identifier "Card0"
    Driver "modesetting"
    Option "Monitor-DP-1" "DP-1"
EndSection

Section "Screen"
    Identifier "Screen0"
    Device "Card0"
    Monitor "DP-1"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Virtual 1920 1080
        Modes "1920x1080"
    EndSubSection
EndSection
```

* **`Option "Enable" "true"` & `Virtual 1920 1080`:** Gondoskodik róla, hogy a framebuffer akkor is pontosan 1920x1080 méretű maradjon a VNC számára, ha fizikailag nincs monitor bedugva a DP-1 portba.
* **`DPMS "false"` & `BlankTime "0"`:** Megakadályozza, hogy tétlenség esetén a kijelző lekapcsoljon és fekete képet közvetítsen a VNC.

#### 3. KDE Energiagazdálkodás
A `~/.config/powermanagementprofilesrc` fájlban a tétlenségi időzítőket 0-ra kell állítani, hogy a KDE se küldje alvó állapotba a képernyőt:
```ini
[AC][DPMSControl]
idleTime=0
[AC][SuspendSession]
idleTime=0
```

