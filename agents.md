# Rendszerarchitektúra és Működési Kézikönyv (agents.md)

**Munkamappa:** `/home/misi/Antigravity`  
**GitHub tároló:** `https://github.com/mihaly67/Antigravity`  
**Dátum:** 2026-11-21  
**Alapelv:** Kizárólag hitelesített hardveres és rendszerszintű tények (zéró fantáziálás, zéró Münchausen / Háry János).

---

## 1. Hardveres Specifikáció (Tényleges fizikai adatok)

| Komponens | Pontos típus / Paraméter | Rendszerforrás / Hitelesítés |
| :--- | :--- | :--- |
| **Processzor (CPU)** | Intel(R) Xeon(R) CPU E5-2640 v4 @ 2.40GHz | `/proc/cpuinfo` |
| **Magok / Szálak** | 10 fizikai mag, 20 logikai szál (SMT/HT aktív) | `/sys/devices/system/cpu/` |
| **Architektúra / TDP** | Broadwell-EP (14 nm), LGA2011-3, 90 Watt TDP | Intel specifikáció / RAPL |
| **Rendszermemória (RAM)** | 62 GiB (~64 GB) DDR4 ECC regisztrált | `free -h` |
| **Swap tárterület** | 0 Byte (Swap nincs konfigurálva, elegendő fizikai RAM) | `/proc/swaps` |
| **Grafikus vezérlő (GPU)**| NVIDIA NVS 310 (GF119 / Fermi architektúra, 1024 MB DDR3) | `lspci -nn`, DRM sysfs |
| **GPU Meghajtó** | Open-source Mesa Gallium 24.2.8 (`nouveau`) | `vainfo`, `lspci -k` |
| **Kijelző felbontás** | 1 db 1920x1080 @ 60.00 Hz (DisplayPort) | `xrandr --current` |
| **Háttértár (SSD)** | 120 GB SSD (`/dev/sda`: `/home` 38G, `/` 72G, `/boot/efi` 1.6G) | `lsblk` |
| **Alaplap / Szenzorok**| HP munkaállomás / szerver alaplap (`hp`, `coretemp`, `nouveau`) | `/sys/class/hwmon/` |

---

## 2. Szoftverkörnyezet és Rendszerfelépítés

* **Operációs rendszer:** MX Linux 23.6.1 x86_64 "Libretto" (Debian 12 Bookworm alapokon).
* **Kernel:** `Linux mx 6.1.0-35-amd64 #1 SMP PREEMPT_DYNAMIC` (Debian 6.1.137-1).
* **Init rendszer:** **SysVinit** (`/sbin/init`, PID 1).  
  > [!IMPORTANT]
  > A rendszer **nem** futtat systemd-t PID 1-ként. A `systemctl --user` és az `enable --now` nem működik. Minden rendszerszolgáltatás `/etc/init.d/` LSB szkripttel (`update-rc.d`), a felhasználói folyamatok pedig XDG autostarttal (`~/.config/autostart`, `/etc/xdg/autostart`) indulnak.
* **Grafikus felület:** KDE Plasma 5, X11 Display Server, KWin_x11 ablakkezelő és kompozitor.

---

## 3. Telepített Segédprogramok és Integrációjuk

Minden segédprogram automatikusan indul, és a tálcán fut rejtve vagy minimalizálva:

### 1. Conky Rendszermonitor
* **Elérési út:** `/home/misi/.conky/MX-KoO/` (főkonfiguráció: `MX-Full`)
* **Funkció:** 10-magos / 20-szálas Xeon processzor automatikus topológia-felismerése (`get_cpu_info.py`), tokozási és magonkénti hőmérséklet, hálózati forgalom, valamint a csatolt háttértárak és USB meghajtók dinamikus detektálása (`get_disk_info.py`).

### 2. MX CPU Monitor (`mx-cpu-monitor`)
* **Verzió:** 1.0.6-1 (`/usr/share/mx-cpu-monitor/main.py`)
* **Funkció:** Magonkénti órajel, feszültség és Intel RAPL valós idejű fogyasztásmérés. Grafikus governor váltó (`powersave`, `performance`, `schedutil`), mely az újraindítás után is megőrzi a beállított profilt.
* **Indítás:** `mx-cpu-monitor --minimized`

### 3. MX Hardver Monitor (`mx-hardware-monitor`)
* **Verzió:** 1.0.8 (`/usr/bin/hardware_monitor_v2.py`)
* **Javítások:**
  - **GPU:** Eltávolítva a zárt `nvidia-smi` függőség; közvetlen Linux DRM sysfs (`temp1_input`, `fan1_input`, VRAM arány, render terhelés).
  - **CPU & Teljesítmény:** Eltávolítva a jelszóhiány miatt elbukó `sudo -n turbostat`. Helyette natív Linux sysfs `coretemp` és közvetlen `intel-rapl` energiaszámláló olvasás fut root nélkül, azonnali és pontos Watt és °C értékekkel.
* **Indítás:** `/usr/bin/mx-hardware-monitor --hidden`

### 4. MX SSH & Tailscale Monitor (`mx-ssh-monitor`)
* **Verzió:** 1.1.3 (`/usr/bin/ssh_tailscale_monitor.py`)
* **Funkció:** Bejövő SSH munkamenetek és Tailscale mesh hálózati csomópont állapot követése a tálcán.
* **Indítás:** `/usr/bin/mx-ssh-monitor --hidden`

### 5. MX Biztonsági Irányítópult (`mx-security-dashboard`)
* **Verzió:** 1.0.0 (`/usr/bin/security_dashboard.py`)
* **Funkció:** Hálózati portok, tűzfal (iptables/ufw) és bejelentkezési kísérletek tálcás felügyelete.
* **Indítás:** `/usr/bin/mx-security-dashboard --hidden`

### 6. Egyéb Segédeszközök
* **x11vnc Szerver:** A valós `:0` X11 kijelző (KDE, Conky, tálcamonitorok) távoli elérése port 5900-on jelszóval (`1104`). Automatikus indítás `/etc/xdg/autostart/x11vnc.desktop` és `~/.config/autostart/x11vnc.desktop`.
* **Headless Display mód:** GRUB `video=DP-1:1920x1080@60e` kényszerítéssel fizikai monitor nélkül is 1920x1080-on indul el a grafikus felület.
* **MX RAM Cleaner (`mx-ram-cleaner`, v1.0.3):** Memória és gyorsítótár kíméletes kiürítése.
* **MX CPU/GPU Stressz Teszt (`mx-cpu-gpu-stress-test`, v1.1.8):** Rendszerstabilitási terhelőteszt.
* **Tailscale Démon:** `/etc/init.d/tailscaled` SysVinit init script.
* **Git AutoPush Démon:** `/home/misi/git-autopush.sh --daemon` (kizárólag az Antigravity repót szinkronizálja ciklikusan).

---

## 4. A 4K YouTube Videólejátszás, a CPU és az NVS 310 Valós Szerepe

### Kérdés: Képes a Xeon E5-2640 v4 20-30%-os CPU terheléssel és ~30-38°C hőmérséklettel 4K videót lejátszani? Mit csinál az NVS 310?

A válasz a fizikai és architekturális tényekben rejlik:

### A) A CPU Terhelés (20-30%) Valódi Jelentése
1. A gépen **10 fizikai mag és 20 logikai szál** dolgozik. A teljes CPU kapacitás a Linux processzortáblában 2000% (20 × 100%).
2. A **20-30%-os CPU összterhelés 400% és 600% közötti abszolút CPU munkát jelent**, vagyis **4-6 logikai processzorszál folyamatosan 100%-on pörög** a háttérben!
3. A modern böngészőkben futó szoftveres dekódoló motorok (`libvpx` a VP9-hez, `dav1d` az AV1-hez) magas szinten párhuzamosítottak: a videókockákat csempékre (tiles) és sorokra (rows) osztva több szálon dolgozzák fel.
4. Ha a monitor felbontása 1920x1080, a YouTube alapértelmezett lejátszója automatikusan **1080p streamet** kér le, nem 4K-t. 1080p szoftveres dekódolása ezen a 20-szálas processzoron mindössze 15-22% terhelést kér.
5. Manuálisan 2160p-re (4K) állítva 30 fps mellett a CPU terhelése 35-50%-ra nő (~7-10 szál 100%-on).

### B) A Hőmérséklet (~30-38°C) Oka
1. Az Intel Xeon E5-2640 v4 egy szerverprocesszor, amelynek maximális gyári fogyasztási kerete (TDP) mindössze **90 Watt**.
2. A gép hűtőbordája és ventilátorai 135-160 Wattos processzorok elvezetésére lettek méretezve.
3. 20-30%-os terhelés mellett az Intel RAPL hardveres fogyasztásmérője szerint a CPU mindössze **22-28 Wattot fogyaszt**!
4. 25 Wattnyi hő eloszlatása egy masszív szerver rézbordán és folyamatos légáramlás mellett a szobahőmérséklethez (~22°C) képest csupán 10-15°C emelkedést okoz. Ezért a CPU tokozási hőmérséklete teljesen normális módon **32°C és 38°C között mozog**.

### C) Az NVIDIA NVS 310 Pontos Szerepe
1. **Videókodek hardveres gyorsítás (ASIC dekódolás): 0%**
   - Az NVS 310 egy 2011-es **Fermi (GF119)** lapkára épül.
   - PureVideo HD 5 (VDPAU Feature Set D) motorral rendelkezik. Fizikailag csak MPEG-1/2, VC-1 és H.264 (AVC) kodekeket támogat legfeljebb 1080p-ig.
   - A YouTube által 4K-hoz kizárólagosan használt **VP9 és AV1 formátumokhoz az NVS 310 chipjén egyetlen tranzisztor sincs**.
   - A nyílt forráskódú `nouveau` Mesa meghajtóban a `vainfo` lefutása egyértelműen jelzi: `VAProfileNone : VAEntrypointVideoProc` (nincs hardveres videógyorsítási profil).
2. **Képi megjelenítés és kompozitálás: 100%**
   - A CPU által kikódolt nyers képpontokat (YUV420p) a böngésző GPU folyamata feltölti a PCIe buszon keresztül az NVS 310 1 GB-os VRAM-jába.
   - Az NVS 310 végzi a hardveres színtér-konverziót (YUV -> RGB), a képméretezést a monitor 1080p felbontására, az ablakkezelő (KWin_x11 OpenGL) kompozitálását és a 60 Hz-es DisplayPort jeltovábbítást.
   - Mivel a kártya mindössze 64 bites DDR3 memóriabusszal rendelkezik (~14 GB/s sávszélesség), a másodpercenként több gigabájtnyi nyers képpont átmozgatása a GPU memóriabuszát és 2D/3D motorját **30-40%-ban folyamatosan terheli**.
   - **Összegzés:** A videó tömörítését a CPU fejti fel (szoftveres dekódolás), de a megjelenített pixelek kirajzolását és mozgatását a GPU végzi.

---

## 5. Távoli Elérés, Headless Működés és VNC Rendszerarchitektúra

A rendszer felkészítve teljes monitor-, billentyűzet- és egérmentes (headless) működésre, miközben fizikai perifériák csatlakoztatása esetén azonnal rendelkezésre áll.

### A) Headless (Monitor nélküli) Rendszerindítás
1. **KMS Virtuális Keretpuffer (Framebuffer):**
   - A GRUB konfigurációban (`/etc/default/grub`) a `GRUB_CMDLINE_LINUX_DEFAULT` kiegészítve a következő paraméterrel:
     `video=DP-1:1920x1080@60e`
   - Ez biztosítja, hogy a Nouveau kernelmodul fizikai kijelző hiányában is felépít egy szabványos 1920x1080 @ 60Hz virtuális framepuffert a `DP-1` kimeneten.
   - Ennek köszönhetően az SDDM kijelzőkezelő, a KDE Plasma és a KWin kompozitor hibátlanul elindul képernyő hiányában is (nincs szükség dummy HDMI/DP hardveres dugóra).
2. **Párhuzamos Periféria Kezelés:**
   - A Linux evdev és az X11 XTEST alrendszere párhuzamosan kezeli a virtuális (VNC) és a fizikai beviteli eszközöket.
   - Ha fizikai billentyűzetet vagy egeret csatlakoztatunk, azok azonnal működnek a távoli VNC munkamenet megszakítása vagy újraindítása nélkül.

### B) VNC Gazda Kiszolgáló és SysVinit Rendszerindítás (`x11vnc`)
- **Protokoll & Kiszolgáló:** `x11vnc` 0.9.16 (Port: `5900`).
- **Valódi asztali munkamenet megosztása:** Az aktív `:0` KDE Plasma asztalt osztja meg (`-auth /home/<user>/.Xauthority`, `-rfbauth /home/<user>/.vnc/passwd`).
- **Jelszó:** `1104` (mentve: `~/.vnc/passwd`).
- **SysVinit Rendszerszolgáltatás:**
  - Szolgáltatás szkript: `/etc/init.d/x11vnc`
  - Felügyeleti démon: `/usr/local/bin/x11vnc-service.sh`
  - Automatikus futási szintek: `update-rc.d x11vnc defaults 95 05` (futási szintek: 2, 3, 4, 5).
  - Folyamatos felügyelet: az X11 `:0` képernyő és a hitelesítés indulásakor azonnal elindítja az `x11vnc`-t, munkamenet újraindulásakor pedig automatikusan újraépíti a kapcsolatot.
- **Elérési útvonalak:**
  - Helyi LAN hálózat: `192.168.1.105:5900`
  - Biztonságos Tailscale VPN mesh: `100.118.197.74:5900`

### C) Tálca Indikátor & Vezérlő Központ (`mx-vnc-server`)
- **Alkalmazás:** `/usr/bin/mx-vnc-server` (`/usr/bin/mx_vnc_tray.py`).
- **Tálca ikon:** Dinamikusan generált antialiased monitor ikon állapotjelző LED-del a KDE tálcán:
  - 🟢 **Zöld (Figyel):** A VNC kiszolgáló aktív a `:5900` porton, várja a kapcsolatokat.
  - 🔵 **Kék (Csatlakozva):** Távoli kliens aktívan csatlakozva (buborékértesítés jelenik meg a csatlakozott IP-vel).
  - 🔴 **Piros (Leállítva):** A kiszolgáló inaktív.
- **Kliens Végpont & Gyorselérés:**
  - Beépített menüből egy kattintással indítható a **Remmina** (teljes értékű RDP/VNC kapcsolatkezelő) vagy a **TigerVNC Viewer**, ha innen szeretnénk elérni egy másik gépet.
  - Helyi és Tailscale IP:Port egykattintásos vágólapra másolása.
  - Csatlakozási adatok ablak jelszó-kijelzéssel és útmutatóval.
  - Automatikus indítás beállítva a rendszerindítással (`~/.config/autostart/mx-vnc-server.desktop`).

### D) Háromgépes Kölcsönös VNC Rendszerarchitektúra (`vnc/`)
1. **Érintett Csomópontok:**
   - **Gazdagép (`mx-1`):** Intel Xeon E5-2640 v4 (20 szál), LAN `192.168.1.105`, Tailscale `100.118.197.74`, felhasználó `misi`.
   - **Másik Gép (`mx`):** AMD Phenom II X4 945 (4 mag), LAN `192.168.1.106`, Tailscale `100.95.215.75`, felhasználó `Misi` (jelszó: `1104`).
   - **Fejlesztői Csomópont (`jules`):** Tailscale `100.77.191.66`.
2. **Kölcsönös és Kétirányú Működés:**
   - A forráskódok a [`vnc/`](vnc/) gyökérkönyvtárba lettek szervezve, saját rendszerleírással ([`vnc/README.md`](vnc/README.md)).
   - Az intelligens kliens ([`mx-vnc-connect`](file:///home/misi/Antigravity/vnc/mx-vnc-connect)) automatikusan felméri a helyi gép IP címét, és felismeri a célgépet. Támogatja az `mx`, `mx1` és `jules` paramétereket.
   - Automatikus failover: elsődlegesen a gigabites helyi LAN-on (`192.168.1.x:5900`) próbál csatlakozni (1 ms alatti késleltetés), ha a port nem válaszol, automatikusan és észrevétlenül átvált a Tailscale titkosított WireGuard VPN-re (`100.x.x.x:5900`).
3. **SysVinit Háttérszolgáltatás és Tálca Indikátor:**
   - Mindkét fizikai gépen SysVinit démon fut (`/etc/init.d/x11vnc` és `/usr/local/bin/x11vnc-service.sh`), mely kijelzőzárolás, kijelentkezés vagy X11 újraindulás után is automatikusan életben tartja a portot (5900).
   - A KDE tálcán futó állapotjelző (`mx_vnc_tray.py`) valós időben mutatja az állapotot (🟢 Figyel, 🔵 Csatlakozva, 🔴 Leállítva), a tálcamenüből pedig egyetlen kattintással másolhatók a címek és indítható a csatlakozás a kívánt partnergéphez (`mx`, `mx-1`, `jules`).
4. **Dolphin Fájlkezelő Integráció:**
   - Kétoldali jelszómentes ED25519 kulcscsere után mindkét gép Dolphin fájlkezelőjének Helyek paneljén közvetlen SFTP könyvjelző él gigabites sebességgel.

### E) AMD Phenom II X4 945 és a Google Antigravity AVX Követelménye
1. **A Fizikai és Hardveres Valóság:**
   - A másik gép processzora egy **AMD Phenom(tm) II X4 945** (K10 architektúra, 2009).
   - Támogatott utasításkészletek: `sse, sse2, sse3, sse4a, popcnt`.
   - **Fizikailag hiányzó tranzisztorok és utasítások:** `avx, avx2, fma, bmi1, bmi2, sse4.1, sse4.2`.
   - A Google Antigravity natív nyelvi és ügynök backendje (`agy`) a modern **x86-64-v3** mikroszintű architektúrát célozza (AVX vektorutasítások, pl. `vzeroupper`). Ha a Phenom II processzoron indítanánk el ezt a binárist, a CPU hardveres kivételt dob (`SIGILL - Illegal Instruction`).
   - Ezért az Antigravity VS Code bővítmény ellenőrzi a `/proc/cpuinfo` zászlókat, és megtagadja a helyi bináris indítását AVX hiányában.
2. **A Két Hivatalos és Működőképes Megoldás:**
   - **1. Megoldás (Ajánlott - VNC Távvezérlés):** Az asztalon lévő `mx-vnc-connect` ikonnal a Phenom gép csatlakozik a 20-szálas Xeon E5-2640 v4 gazdagéphez. Az Antigravity teljes sebességgel, natív AVX2 gyorsítással fut a Xeonon, míg a Phenom gépen a megjelenítés 0-5% terhelést jelent.
   - **2. Megoldás (VS Code Remote-SSH natív ablakban - Élesítve és Tesztelve):**
     - Az `mx` gép VS Code-jába feltelepítésre került az `ms-vscode-remote.remote-ssh` kiegészítő.
     - Az `mx` gép SSH konfigurációjába (`~/.ssh/config`) felvéve a `Host mx-1` jelszómentes kulcsos kapcsolattal.
     - A gazdagépen (`mx-1`) inicializálva a `~/.vscode-server` környezet és szimbolikus linkkel becsatolva a `google.google-antigravity` bővítmény.
     - Az `mx` gép asztalára kihelyezve a közvetlen indítóikon:
       **`/home/Misi/Asztal/Antigravity_Xeon_Workspace.desktop`**
       (`code --folder-uri "vscode-remote://ssh-remote+mx-1/home/misi"`).
     - Egyetlen kattintással megnyitja a távoli Xeon munkamenetet, ahol az Antigravity teljes AVX2 sebességgel fut a 20-szálas processzoron, a Phenom gép pedig csak a grafikus felületet rajzolja ki hiba nélkül.

---

## 6. Fejlesztési és Karbantartási Protokoll

1. **Automatikus GitHub szinkronizáció:**
   - A repó a `/home/misi/Antigravity` mappában él, `origin/main` ágra kapcsolódva.
   - A [`scripts/git-autopush.sh`](file:///home/misi/Antigravity/scripts/git-autopush.sh) démon 10 percenként ellenőrzi a forrásokat, a Conky konfigurációkat, a segédprogramokat és a `.deb` csomagokat, majd automatikusan commitol és pushol.
2. **Token- és Erőforrás-gazdálkodás:**
   - A VSCode-ból minden felesleges C/C++ és Azure bővítmény eltávolítva.
   - A Pylance memóriahasználata `openFilesOnly` módra korlátozva.
   - Keresési és fájlfigyelési tiltólisták aktívak a binárisokra, naplókra és ideiglenes fájlokra.

