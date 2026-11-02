#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MX CPU Monitor - Rendszermutatók, szenzorok, fizikai mag-topológia és teljes Xeon E5 v3/v4 adatbázis
Közvetlen /proc és /sys elérés külső függőségek nélkül.
Támogatja a kikapcsolt magok 0 MHz-es állapotát, az átlagos órajelet,
a nem-folytonos Xeon fizikai core_id -> HT szál hőmérséklet-hozzárendelést,
a Linux CPU kormányzót és a teljes 108-modellből álló Intel Xeon E5 v3/v4 specifikációs katalógust.
"""

import os
import re
import time
import glob
import subprocess

XEON_ULTIMATE_CATALOG = [
    ('E5-2622 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 8, 16, 2.4, 3.4, '20 MB', 85, 'DDR4-1866', 'Egyedi alacsony fogyasztású virtualizációs OEM modell.'),
    ('E5-2629 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 8, 16, 2.4, 3.2, '20 MB', 85, 'DDR4-1866', 'Hálózati eszközökhöz és SAN/NAS szerverekhez optimalizált OEM.'),
    ('E5-2649 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 10, 20, 2.3, 3.0, '25 MB', 105, 'DDR4-2133', 'Költséghatékony sűrűség-orientált OEM felhőszerverekhez.'),
    ('E5-2652 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 10, 20, 2.3, 2.8, '25 MB', 105, 'DDR4-2133', 'Ritka, dedikált céleszközökbe szánt OEM processzor.'),
    ('E5-2658A v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 12, 24, 2.2, 2.9, '30 MB', 105, 'DDR4-2133', 'Beágyazott/Hosszú életciklusú ipari hardverekbe szánt frissített változat.'),
    ('E5-2663 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 10, 20, 2.8, 3.5, '25 MB', 120, 'DDR4-2133', 'Magas alapórajellel rendelkező egyedi OEM munkaállomásokhoz.'),
    ('E5-2666 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 10, 20, 2.9, 3.5, '25 MB', 135, 'DDR4-2133', 'Amazon AWS exkluzív chip. Magas fogyasztási limittel felhőalapú számításokhoz.'),
    ('E5-2669 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 12, 24, 2.6, 3.4, '30 MB', 120, 'DDR4-2133', 'Frekvencia-optimalizált OEM darab adatbázis-kezelő szerverekhez.'),
    ('E5-2673 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 12, 24, 2.4, 3.2, '30 MB', 105, 'DDR3 / DDR4', 'Microsoft Azure exkluzív chip. Hibrid DDR3 és DDR4 támogatással!'),
    ('E5-2675 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 16, 32, 1.8, 2.3, '40 MB', 110, 'DDR4-2133', 'Sűrű magelosztású, kifejezetten hideg/alacsony energiaigényű tárolószerverekhez.'),
    ('E5-2676 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 12, 24, 2.4, 3.0, '30 MB', 110, 'DDR4-2133', 'Amazon AWS rendszereibe szánt nagy darabszámú egyedi verzió.'),
    ('E5-2678 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 12, 24, 2.5, 3.3, '30 MB', 120, 'DDR3 / DDR4', 'Ázsiai OEM piacra szánt slágerchip, egyedülálló gyári DDR3 ECC és DDR4 memóriatámogatással.'),
    ('E5-2682 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 16, 32, 2.5, 3.0, '40 MB', 120, 'DDR4-2133', 'Köztes OEM modell nagy sűrűségű felhő számítási pontokhoz.'),
    ('E5-2686 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 18, 36, 2.0, 3.5, '45 MB', 120, 'DDR4-2133', 'Amazon AWS egyedi csúcschip. 18 mag szigorú 120W-os keretben, magas egy-magos turbóval.'),
    ('E5-2692 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 12, 24, 3.0, 3.6, '30 MB', 165, 'DDR4-2133', 'Szuper-számítógépes fürtökbe (HPC) épített extrém teljesítményű verzió.'),
    ('E5-2696 v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 18, 36, 2.3, 3.8, '45 MB', 160, 'DDR4-2133', 'Az igazi v3 király. A lakossági 2699 v3 feljavított verziója 160W-os limittel és magasabb All-Core Turbo megtartással.'),
    ('E5-2698A v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 16, 32, 2.8, 3.2, '40 MB', 165, 'DDR4-2133', 'Egyedi frekvencia-optimalizált OEM chip nagyvállalati adatbázisokhoz.'),
    ('E5-2698B v3', 'OEM & Titkos Szériák (v3-v4)', 'v3 (Haswell-EP)', 16, 32, 2.0, 3.4, '40 MB', 135, 'DDR4-2133', 'Oracle/Sun rendszerekhez készített speciális energiatakarékos és frekvencia-skálázott változat.'),
    ('E5-2673 v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 20, 40, 2.3, 3.3, '50 MB', 135, 'DDR4-2400', 'Microsoft Azure felhőszolgáltatásokhoz tervezett egyedi, óriási magszámú OEM darab.'),
    ('E5-2676 v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 16, 32, 2.4, 3.0, '40 MB', 145, 'DDR4-2400', 'Amazon AWS szerverparkok frissítésére szánt egyedi architektúra.'),
    ('E5-2682 v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 16, 32, 2.5, 3.0, '40 MB', 120, 'DDR4-2400', 'Nagy felhőszolgáltatóknak gyártott energiatakarékos, magas alapórajeles OEM modell.'),
    ('E5-2686 v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 18, 36, 2.3, 3.0, '45 MB', 145, 'DDR4-2400', 'Amazon AWS exkluzív v4 processzor összetett felhőalapú virtualizációhoz.'),
    ('E5-2689 v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 10, 20, 3.1, 3.8, '25 MB', 165, 'DDR4-2400', 'Extrém magas órajeles OEM chip, kifejezetten High-Frequency Trading (HFT) és HPC célra.'),
    ('E5-2696 v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 22, 44, 2.2, 3.6, '55 MB', 150, 'DDR4 / DDR3', 'A Broadwell-EP legdurvább OEM csúcsa. 22 mag, 150W TDP limit, és néhány alaplapban hibrid DDR3 támogatás!'),
    ('E5-2699A v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 22, 44, 2.4, 3.6, '55 MB', 145, 'DDR4-2400', 'Hivatalos késői prémium kiadás. Magasabb alap- és All-Core Turbo órajel, mint az alap 2699 v4-nél.'),
    ('E5-2699C v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 22, 44, 2.2, 3.6, '55 MB', 145, 'DDR4-2400', 'Egyedi OEM / Cisco és speciális rack rendszerek számára átnevezett csúcsmodell.'),
    ('E5-2699R v4', 'OEM & Titkos Szériák (v3-v4)', 'v4 (Broadwell-EP)', 22, 44, 2.2, 3.6, '55 MB', 145, 'DDR4-2400', 'Refresh széria, egyedi mikrokód frissítéssel kiadott szerver-specifikus változat.'),
    ('E5-1620 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 4, 8, 3.5, 3.6, '10 MB', 140, 'DDR4-2133', 'Munkaállomás (1S)'),
    ('E5-1630 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 4, 8, 3.7, 3.8, '10 MB', 140, 'DDR4-2133', 'Munkaállomás (1S)'),
    ('E5-1650 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 6, 12, 3.5, 3.8, '15 MB', 140, 'DDR4-2133', 'Munkaállomás (1S) - Szorzózármentes'),
    ('E5-1660 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 8, 16, 3.0, 3.5, '20 MB', 140, 'DDR4-2133', 'Munkaállomás (1S) - Szorzózármentes'),
    ('E5-1680 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 8, 16, 3.2, 3.5, '20 MB', 140, 'DDR4-2133', 'Munkaállomás (1S) - Szorzózármentes csúcs'),
    ('E5-2603 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 6, 6, 1.6, 1.6, '15 MB', 85, 'DDR4-2133', 'Alap Szerver (2S)'),
    ('E5-2609 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 6, 6, 1.9, 1.9, '15 MB', 85, 'DDR4-2133', 'Alap Szerver (2S)'),
    ('E5-2620 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 6, 12, 2.4, 3.2, '15 MB', 85, 'DDR4-2133', 'Standard Szerver (2S)'),
    ('E5-2623 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 4, 8, 3.0, 3.5, '10 MB', 105, 'DDR4-2133', 'Frekvencia-optimalizált (2S)'),
    ('E5-2630 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 8, 16, 2.4, 3.2, '20 MB', 85, 'DDR4-2133', 'Standard Szerver (2S)'),
    ('E5-2630L v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 8, 16, 1.8, 2.9, '20 MB', 55, 'DDR4-2133', 'Alacsony fogyasztású (L)'),
    ('E5-2637 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 4, 8, 3.5, 3.7, '15 MB', 135, 'DDR4-2133', 'Frekvencia-optimalizált (2S)'),
    ('E5-2640 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 8, 16, 2.6, 3.4, '20 MB', 90, 'DDR4-2133', 'Standard Szerver (2S)'),
    ('E5-2643 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 6, 12, 3.4, 3.7, '20 MB', 135, 'DDR4-2133', 'Magas frekvenciájú szerver'),
    ('E5-2650 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 10, 20, 2.3, 3.0, '25 MB', 105, 'DDR4-2133', 'Standard Szerver (2S)'),
    ('E5-2650L v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 12, 24, 1.8, 2.5, '30 MB', 65, 'DDR4-2133', 'Alacsony fogyasztású (L)'),
    ('E5-2658 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 12, 24, 2.2, 2.9, '30 MB', 105, 'DDR4-2133', 'Beágyazott/Ipari széria'),
    ('E5-2660 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 10, 20, 2.6, 3.3, '25 MB', 105, 'DDR4-2133', 'Nagy teljesítményű szerver'),
    ('E5-2667 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 8, 16, 3.2, 3.6, '20 MB', 135, 'DDR4-2133', 'Frekvencia-optimalizált csúcs'),
    ('E5-2670 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 12, 24, 2.3, 3.1, '30 MB', 120, 'DDR4-2133', 'Nagy teljesítményű szerver'),
    ('E5-2680 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 12, 24, 2.5, 3.3, '30 MB', 120, 'DDR4-2133', 'Nagy teljesítményű szerver'),
    ('E5-2683 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 14, 28, 2.0, 3.0, '35 MB', 120, 'DDR4-2133', 'Nagy sűrűségű szerver'),
    ('E5-2687W v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 10, 20, 3.1, 3.5, '25 MB', 160, 'DDR4-2133', 'Munkaállomás kiadás (W)'),
    ('E5-2690 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 12, 24, 2.6, 3.5, '30 MB', 135, 'DDR4-2133', 'Prémium nagyteljesítményű szerver'),
    ('E5-2695 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 14, 28, 2.3, 3.3, '35 MB', 120, 'DDR4-2133', 'Prémium nagyteljesítményű szerver'),
    ('E5-2697 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 14, 28, 2.6, 3.6, '35 MB', 145, 'DDR4-2133', 'Prémium nagyteljesítményű szerver'),
    ('E5-2698 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 16, 32, 2.3, 3.6, '40 MB', 135, 'DDR4-2133', 'Prémium szerver csúcs'),
    ('E5-2699 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 18, 36, 2.3, 3.6, '45 MB', 145, 'DDR4-2133', 'Hivatalos kiskereskedelmi csúcsmodell'),
    ('E5-4610 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 10, 20, 1.7, 2.1, '25 MB', 105, 'DDR4-2133', '4-utas szerver (4S)'),
    ('E5-4620 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 10, 20, 2.0, 2.6, '25 MB', 105, 'DDR4-2133', '4-utas szerver (4S)'),
    ('E5-4627 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 10, 10, 2.6, 3.2, '25 MB', 135, 'DDR4-2133', '4-utas szerver (HyperThreading nélkül)'),
    ('E5-4640 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 12, 24, 1.9, 2.6, '30 MB', 105, 'DDR4-2133', '4-utas szerver (4S)'),
    ('E5-4650 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 12, 24, 2.1, 2.8, '30 MB', 105, 'DDR4-2133', '4-utas szerver (4S)'),
    ('E5-4655 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 6, 12, 2.9, 3.2, '15 MB', 135, 'DDR4-2133', '4-utas szerver (4S)'),
    ('E5-4660 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 14, 28, 2.1, 2.9, '35 MB', 125, 'DDR4-2133', '4-utas szerver (4S)'),
    ('E5-4667 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 16, 32, 2.0, 2.9, '40 MB', 135, 'DDR4-2133', '4-utas szerver (4S)'),
    ('E5-4669 v3', 'Teljes E5 v3 Család', 'v3 (Haswell-EP)', 18, 36, 2.1, 2.9, '45 MB', 135, 'DDR4-2133', '4-utas szerver csúcsmodell'),
    ('E5-1603 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 4, 4, 2.8, 2.8, '10 MB', 140, 'DDR4-2400', 'Belépő munkaállomás (1S)'),
    ('E5-1607 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 4, 4, 3.1, 3.1, '10 MB', 140, 'DDR4-2400', 'Belépő munkaállomás (1S)'),
    ('E5-1620 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 4, 8, 3.5, 3.8, '10 MB', 140, 'DDR4-2400', 'Munkaállomás (1S)'),
    ('E5-1630 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 4, 8, 3.7, 4.0, '10 MB', 140, 'DDR4-2400', 'Munkaállomás (1S)'),
    ('E5-1650 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 6, 12, 3.6, 4.0, '15 MB', 140, 'DDR4-2400', 'Munkaállomás (1S) - Szorzózármentes'),
    ('E5-1660 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 8, 16, 3.2, 3.8, '20 MB', 140, 'DDR4-2400', 'Munkaállomás (1S) - Szorzózármentes'),
    ('E5-1680 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 8, 16, 3.4, 4.0, '20 MB', 140, 'DDR4-2400', 'Munkaállomás csúcsmodell'),
    ('E5-2603 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 6, 6, 1.7, 1.7, '15 MB', 85, 'DDR4-2400', 'Alap Szerver (2S)'),
    ('E5-2608L v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 8, 16, 1.6, 1.7, '20 MB', 50, 'DDR4-2400', 'Alacsony fogyasztású (L)'),
    ('E5-2609 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 8, 8, 1.7, 1.7, '20 MB', 85, 'DDR4-2400', 'Alap Szerver (2S)'),
    ('E5-2618L v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 10, 20, 2.2, 3.2, '25 MB', 75, 'DDR4-2400', 'Alacsony fogyasztású (L)'),
    ('E5-2620 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 8, 16, 2.1, 3.0, '20 MB', 85, 'DDR4-2400', 'Standard Szerver (2S) - Rendkívül népszerű'),
    ('E5-2623 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 4, 8, 2.6, 3.2, '10 MB', 85, 'DDR4-2400', 'Frekvencia-optimalizált (2S)'),
    ('E5-2628L v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 12, 24, 1.9, 2.4, '30 MB', 75, 'DDR4-2400', 'Alacsony fogyasztású (L)'),
    ('E5-2630 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 10, 20, 2.2, 3.1, '25 MB', 85, 'DDR4-2400', 'Standard Szerver (2S)'),
    ('E5-2630L v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 10, 20, 1.8, 2.9, '25 MB', 55, 'DDR4-2400', 'Alacsony fogyasztású (L)'),
    ('E5-2637 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 4, 8, 3.5, 3.7, '15 MB', 135, 'DDR4-2400', 'Frekvencia-optimalizált (2S)'),
    ('E5-2640 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 10, 20, 2.4, 3.4, '25 MB', 90, 'DDR4-2400', 'Standard Szerver (2S)'),
    ('E5-2643 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 6, 12, 3.4, 3.7, '20 MB', 135, 'DDR4-2400', 'Magas frekvenciájú szerver'),
    ('E5-2648L v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 14, 28, 1.8, 2.5, '35 MB', 75, 'DDR4-2400', 'Alacsony fogyasztású (L)'),
    ('E5-2650 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 12, 24, 2.2, 2.9, '30 MB', 105, 'DDR4-2400', 'Standard Szerver (2S)'),
    ('E5-2650L v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 14, 28, 1.7, 2.5, '35 MB', 65, 'DDR4-2400', 'Alacsony fogyasztású (L)'),
    ('E5-2658 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 14, 28, 2.3, 2.8, '35 MB', 105, 'DDR4-2400', 'Beágyazott/Ipari széria'),
    ('E5-2660 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 14, 28, 2.0, 3.2, '35 MB', 105, 'DDR4-2400', 'Nagy teljesítményű szerver'),
    ('E5-2667 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 8, 16, 3.2, 3.6, '20 MB', 135, 'DDR4-2400', 'Frekvencia-optimalizált szerver'),
    ('E5-2680 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 14, 28, 2.4, 3.3, '35 MB', 120, 'DDR4-2400', 'Nagy teljesítményű szerver'),
    ('E5-2683 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 16, 32, 2.1, 3.0, '40 MB', 120, 'DDR4-2400', 'Nagy sűrűségű szerver'),
    ('E5-2687W v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 12, 24, 3.0, 3.5, '30 MB', 160, 'DDR4-2400', 'Munkaállomás kiadás (W)'),
    ('E5-2690 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 14, 28, 2.6, 3.5, '35 MB', 135, 'DDR4-2400', 'Prémium nagyteljesítményű szerver'),
    ('E5-2695 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 18, 36, 2.1, 3.3, '45 MB', 120, 'DDR4-2400', 'Prémium nagyteljesítményű szerver'),
    ('E5-2697 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 18, 36, 2.3, 3.6, '45 MB', 145, 'DDR4-2400', 'Prémium nagyteljesítményű szerver'),
    ('E5-2697A v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 16, 32, 2.6, 3.6, '40 MB', 145, 'DDR4-2400', 'Frekvencia-súlyozott prémium kiadás'),
    ('E5-2698 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 20, 40, 2.2, 3.6, '50 MB', 135, 'DDR4-2400', 'Prémium csúcsszerver'),
    ('E5-2699 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 22, 44, 2.2, 3.6, '55 MB', 145, 'DDR4-2400', 'Hivatalos lakossági csúcsmodell'),
    ('E5-4610 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 10, 20, 1.8, 2.1, '25 MB', 105, 'DDR4-2400', '4-utas szerver (4S)'),
    ('E5-4620 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 10, 20, 2.1, 2.6, '25 MB', 105, 'DDR4-2400', '4-utas szerver (4S)'),
    ('E5-4627 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 10, 10, 2.6, 3.2, '25 MB', 135, 'DDR4-2400', '4-utas szerver (HyperThreading nélkül)'),
    ('E5-4628L v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 10, 20, 1.8, 2.2, '25 MB', 75, 'DDR4-2400', '4-utas alacsony fogyasztású (L)'),
    ('E5-4640 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 12, 24, 2.1, 2.6, '30 MB', 105, 'DDR4-2400', '4-utas szerver (4S)'),
    ('E5-4650 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 14, 28, 2.2, 2.8, '35 MB', 105, 'DDR4-2400', '4-utas szerver (4S)'),
    ('E5-4655 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 8, 16, 2.5, 2.8, '30 MB', 135, 'DDR4-2400', '4-utas szerver (4S)'),
    ('E5-4660 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 16, 32, 2.2, 3.0, '40 MB', 120, 'DDR4-2400', '4-utas szerver (4S)'),
    ('E5-4667 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 18, 36, 2.2, 3.0, '45 MB', 135, 'DDR4-2400', '4-utas szerver (4S)'),
    ('E5-4669 v4', 'Teljes E5 v4 Család', 'v4 (Broadwell-EP)', 22, 44, 2.2, 3.0, '55 MB', 135, 'DDR4-2400', '4-utas szerver csúcsmodell'),
]

# Egyedi, ismert All-Core Turbo órajelek (GHz) a legnépszerűbb Xeon E5 v3 / v4 modellekhez
KNOWN_ALL_CORE_TURBO = {
    'E5-2673 v4': 2.80,
    'E5-2618L v4': 2.40,
    'E5-2620 v4': 2.30,
    'E5-2630 v4': 2.40,
    'E5-2630L v4': 2.00,
    'E5-2640 v4': 2.60,
    'E5-2650 v4': 2.50,
    'E5-2660 v4': 2.40,
    'E5-2676 v4': 2.70,
    'E5-2680 v4': 2.90,
    'E5-2682 v4': 2.90,
    'E5-2683 v4': 2.60,
    'E5-2686 v4': 2.70,
    'E5-2689 v4': 3.70,
    'E5-2690 v4': 3.20,
    'E5-2695 v4': 2.60,
    'E5-2696 v4': 2.80,
    'E5-2697 v4': 2.80,
    'E5-2697A v4': 3.10,
    'E5-2698 v4': 2.70,
    'E5-2699 v4': 2.80,
    'E5-2699A v4': 3.00,
    'E5-2699C v4': 2.80,
    'E5-2699R v4': 2.80,
    'E5-2673 v3': 2.70,
    'E5-2676 v3': 2.70,
    'E5-2678 v3': 2.90,
    'E5-2680 v3': 2.90,
    'E5-2683 v3': 2.50,
    'E5-2686 v3': 2.30,
    'E5-2690 v3': 3.10,
    'E5-2696 v3': 2.80,
    'E5-2697 v3': 3.10,
    'E5-2698 v3': 2.80,
    'E5-2699 v3': 2.80,
}


def _build_xeon_specs_db():
    db = {}
    for (model, cat, gen, c_num, t_num, base_f, turbo_f, cache, tdp_f, mem, note) in XEON_ULTIMATE_CATALOG:
        arch = 'Broadwell-EP (14nm)' if 'v4' in gen else 'Haswell-EP (22nm)'
        if turbo_f <= base_f:
            all_core = base_f
        elif model in KNOWN_ALL_CORE_TURBO:
            all_core = KNOWN_ALL_CORE_TURBO[model]
        else:
            # 100 MHz-es (0.10 GHz) szorzólépcsőre kerekített All-Core Turbo
            step = round((turbo_f - base_f) * 0.45 * 10.0) / 10.0
            all_core = round(min(turbo_f, max(base_f, base_f + max(0.1, step))), 2)

        if model == 'E5-2673 v4':
            bins = [
                ('1 aktív mag (Max Boost / TBMT)', '3.30 – 3.60 GHz', 'Csúcs egymagos turbó (OEM spec: 3.30 GHz / HW limit: 3.60 GHz)'),
                ('2 aktív mag', '3.30 GHz', 'Kétmagos turbó frekvencia'),
                ('3–4 aktív mag', '3.10 – 3.20 GHz', 'Alacsony magszámú terhelés'),
                ('5–8 aktív mag', '3.00 GHz', 'Közepes terhelés'),
                ('9–12 aktív mag', '2.90 GHz', 'Magas terhelés'),
                ('13–20 aktív mag (Minden mag)', '2.80 GHz', 'All-Core Turbo (20 mag / 40 szál teljes terhelés, 135 W TDP)'),
                ('Garantált alapórajel', '2.30 GHz', 'Gyári alapfrekvencia folyamatos / AVX terhelés alatt'),
                ('Energiatakarékos alapjárat', '1.20 GHz', 'Minimális működési frekvencia (LFM)'),
                ('Kikapcsolt mag', '0 MHz', 'Offline / Parkolt állapot')
            ]
            explanation = (
                f"{note}\n\n"
                "Miért 2.80 GHz az órajel teljes (20 mag / 40 szál) terhelésnél?\n"
                "Az Intel Broadwell-EP architektúránál a 20 fizikai magos (50 MB L3 Cache) E5-2673 v4 processzor "
                "minden mag 100%-os terhelésekor 2.80 GHz-es All-Core Turbóra áll be (+500 MHz-cel a 2.30 GHz-es alapórajel felett), "
                "így garantálja a 135 Wattos TDP fogyasztási és hőtermelési keret pontos betartását. "
                "Alacsony szálú terhelésnél a turbó órajel 3.30 GHz-ig (a Linux cpufreq / Turbo Boost Max 3.0 hardveres határán 3.60 GHz-ig) emelkedik."
            )
        elif model == 'E5-2618L v4':
            bins = [
                ('1–2 aktív mag', '3.20 GHz', 'Csúcs egy/kétmagos turbó frekvencia'),
                ('3 aktív mag', '3.10 GHz', '3 magos terhelés'),
                ('4 aktív mag', '3.00 GHz', '4 magos terhelés'),
                ('5–6 aktív mag', '2.80 – 2.90 GHz', 'Közepes terhelés'),
                ('7–8 aktív mag', '2.60 – 2.70 GHz', 'Magas terhelés'),
                ('9–10 aktív mag (Minden mag)', '2.40 GHz', 'All-Core Turbo (Teljes terhelés a 75 W TDP limit alatt)'),
                ('Garantált alapórajel', '2.20 GHz', 'Gyári alapfrekvencia terhelés alatt'),
                ('Energiatakarékos alapjárat', '1.20 GHz', 'Minimális működési frekvencia (LFM)'),
                ('Kikapcsolt mag', '0 MHz', 'Offline / Parkolt állapot')
            ]
            explanation = (
                "Miért 2.40 GHz az órajel teljes terhelésnél?\n\n"
                "Az Intel a Broadwell-EP architektúránál a fogyasztási és hőtermelési keretek alapján szigorúan szabályozza "
                "a többmagos turbó szorzókat. Amikor mind a 10 fizikai mag (20 szál) 100%-os terhelést kap, a processzor "
                "2.40 GHz-es All-Core Turbóra áll be. Ez pontosan 200 MHz-cel lépi túl a 2.20 GHz-es alapórajelet, "
                "így garantálja, hogy a csomag fogyasztása stabilan a 75 Wattos TDP határérték alatt maradjon."
            )
        else:
            if turbo_f <= base_f:
                bins = [
                    (f'1–{c_num} aktív mag (Fix órajel)', f'{base_f:.2f} GHz', f'Turbó nélküli fix órajel ({tdp_f} W TDP)'),
                    ('Energiatakarékos alapjárat', '1.20 GHz', 'Minimális működési frekvencia (LFM)'),
                    ('Kikapcsolt mag', '0 MHz', 'Offline / Parkolt állapot')
                ]
            else:
                mid_f = round((turbo_f + all_core) / 2.0, 2)
                mid_c = max(3, c_num // 2)
                bins = [
                    ('1–2 aktív mag (Csúcs)', f'{turbo_f:.2f} GHz', 'Maximális egy/kétmagos turbó órajel'),
                    (f'3–{mid_c} aktív mag', f'{mid_f:.2f} GHz', 'Közepes többszálú terhelés'),
                    (f'{c_num} aktív mag (All-Core)', f'{all_core:.2f} GHz', f'All-Core Turbo ({tdp_f} W TDP keret alatt)'),
                    ('Garantált alapórajel', f'{base_f:.2f} GHz', 'Gyári alapfrekvencia folyamatos terhelésnél'),
                    ('Energiatakarékos alapjárat', '1.20 GHz', 'Minimális működési frekvencia (LFM)'),
                    ('Kikapcsolt mag', '0 MHz', 'Offline / Parkolt állapot')
                ]
            explanation = (
                f"Kategória: {cat} | {c_num} mag / {t_num} szál | {cache} L3 Cache | Memória: {mem}\n"
                f"Háttér: {note}\n\n"
                f"Gyári alapórajel: {base_f:.2f} GHz, maximális turbó: {turbo_f:.2f} GHz, "
                f"minden mag ({c_num}C/{t_num}T) terhelésekor az All-Core Turbo ~{all_core:.2f} GHz a {tdp_f} W TDP keret alatt."
            )

        db[model] = {
            'key': model,
            'model_clean': f'Intel Xeon {model}',
            'arch': arch,
            'category': cat,
            'cores_spec': c_num,
            'threads_spec': t_num,
            'cache': cache,
            'memory': mem,
            'note': note,
            'base': base_f,
            'all_core': all_core,
            'max_turbo': turbo_f,
            'min_freq': 1.20,
            'tdp': float(tdp_f),
            'bins': bins,
            'explanation': explanation,
        }
    return db


XEON_SPECS_DB = _build_xeon_specs_db()


def get_cpu_specification(model_name, n_cores, detected_tdp=65.0):
    """
    Automatikus CPU specifikáció és turbó szintek meghatározása
    a 108-modellből álló Xeon E5 v3/v4 adatbázisból vagy általános detektálással.
    """
    # Hosszabb kulcsok előre (pl. E5-2699A v4 megelőzze az E5-2699 v4-et, E5-2630L v4 az E5-2630 v4-et)
    for key in sorted(XEON_SPECS_DB.keys(), key=len, reverse=True):
        if key.lower() in model_name.lower():
            spec = dict(XEON_SPECS_DB[key])
            # Ha a Linux cpufreq magasabb boost határt lát (pl. E5-2673 v4 esetén 3.60 GHz single-core limit)
            try:
                with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
                    hw_max = round(int(f.read().strip()) / 1e6, 2)
                    if hw_max > spec['max_turbo']:
                        spec['hw_max_turbo'] = hw_max
            except Exception:
                pass
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

    if max_turbo_ghz > base_ghz:
        all_core_ghz = round(base_ghz + (max_turbo_ghz - base_ghz) * 0.40, 2)
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
        'key': model_name,
        'model_clean': model_name.replace('(R)', '').replace('(TM)', '').strip(),
        'arch': 'Intel x86_64',
        'category': 'Általános x86_64',
        'cores_spec': n_cores,
        'threads_spec': os.cpu_count() or n_cores,
        'cache': 'N/A',
        'memory': 'DDR4',
        'note': 'Automatikusan felismert processzor.',
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
        self.thread_topology, self.thread_to_core_id = self._detect_topology()
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

    def _detect_topology(self):
        """
        Felépíti a logikai szál (cpu0..cpuN) -> fizikai mag (core_id és 1-alapú Mag sorszám)
        leképezést. Kezeli a Xeon processzorok nem-folytonos core_id számozását (pl. 0..4, 8..12, 16..20, 24..28).
        """
        cpu_dirs = sorted(
            glob.glob('/sys/devices/system/cpu/cpu[0-9]*'),
            key=lambda p: int(os.path.basename(p)[3:])
        )
        raw_cores = {}
        thread_to_cid = {}
        for cd in cpu_dirs:
            t_idx = int(os.path.basename(cd)[3:])
            top_dir = os.path.join(cd, 'topology')
            cid = t_idx
            sibs = [t_idx]
            if os.path.exists(top_dir):
                try:
                    with open(os.path.join(top_dir, 'core_id'), 'r') as f:
                        cid = int(f.read().strip())
                    with open(os.path.join(top_dir, 'thread_siblings_list'), 'r') as f:
                        sib_str = f.read().strip()
                        parsed_sibs = []
                        for part in sib_str.split(','):
                            if '-' in part:
                                s, e = map(int, part.split('-'))
                                parsed_sibs.extend(range(s, e + 1))
                            else:
                                parsed_sibs.append(int(part))
                        if parsed_sibs:
                            sibs = sorted(parsed_sibs)
                except Exception:
                    pass
            thread_to_cid[t_idx] = cid
            if cid not in raw_cores:
                raw_cores[cid] = sibs

        sorted_cids = sorted(raw_cores.keys())
        cid_to_phys_idx = {cid: idx + 1 for idx, cid in enumerate(sorted_cids)}

        topology = {}
        for t_idx, cid in thread_to_cid.items():
            sibs = raw_cores.get(cid, [t_idx])
            ht_idx = (sibs.index(t_idx) + 1) if t_idx in sibs else 1
            topology[t_idx] = {
                'thread_id': t_idx,
                'conky_thread_idx': t_idx + 1,
                'hw_core_id': cid,
                'phys_core_idx': cid_to_phys_idx.get(cid, t_idx + 1),
                'ht_idx': ht_idx,
                'siblings': sibs,
            }
        return topology, thread_to_cid

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
                cmd = f'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo "{gov_name}" > "" 2>/dev/null; done'
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

        # Hőmérsékletek (fizikai core_id alapján leképzés minden logikai szálra is)
        pkg_temp = None
        raw_core_temps = {}
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
                    elif lbl.startswith('Core '):
                        cid = int(lbl.split()[1])
                        raw_core_temps[cid] = val
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

        core_temps = {}
        for cid, val in raw_core_temps.items():
            core_temps[f"HWCore {cid}"] = val
        for i in range(ncpu):
            hw_cid = self.thread_to_core_id.get(i, i)
            if hw_cid in raw_core_temps:
                core_temps[f"Core {i}"] = raw_core_temps[hw_cid]

        mem = self.get_memory_info()

        return {
            'cpu_model': self.cpu_model,
            'cores': self.core_count,
            'threads': self.thread_count,
            'active_threads': active_count,
            'online_status': online_status,
            'specs': self.specs,
            'topology': self.thread_topology,
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
