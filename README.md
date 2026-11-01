# MX Linux CPU & System Monitor

Könnyűsúlyú, alacsony erőforrás-igényű rendszermonitor és CPU governor vezérlő MX Linux (Debian 12 / SysVinit) rendszerekhez.

## Főbb funkciók
- **Valós idejű telemetria:** CPU terhelés, magonkénti órajelek, hőmérséklet és fogyasztás (Intel/AMD RAPL).
- **Hardveres governor szabályozás:** Valós idejű CPU frekvencia- és teljesítményprofil váltás (performance, powersave, schedutil).
- **Rendszerintegráció:** SysVinit démon és init script, udev szabályok (`99-mx-cpu-rapl.rules`), XDG autostart és asztali ikonok.
- **Minimális lábnyom:** Nincs felesleges függőség vagy Electron overhead; Python és natív Linux `sysfs` interfész.

## Mappa felépítés
- `main.py` - Felhasználói felület és tálca/ablak logika
- `metrics.py` - CPU és hardveres mérési adatok kinyerése (`/sys/devices/system/cpu`, RAPL)
- `pkg/` - Debian (.deb) csomagkészítéshez szükséges fájlok (DEBIAN control/postinst, `/etc/init.d`, `/usr/bin`, `/usr/share`)

## Futtatás
```bash
python3 main.py
```

