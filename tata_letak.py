"""
tata_letak.py
=============

Menghitung posisi (koordinat) setiap simpul agar graf dapat digambar di layar.

File graf tidak memuat koordinat, jadi posisi dihitung otomatis dengan metode
**stress majorization** (keluarga *force-directed layout*):

* Jarak "ideal" antara dua simpul = jumlah hop terpendek di antara keduanya.
* Posisi diperbaiki berulang-ulang agar jarak di layar sedekat mungkin dengan
  jarak ideal tersebut, sehingga simpul yang bertetangga saling berdekatan dan
  persilangan sisi berkurang.

Hasilnya deterministik (selalu sama untuk graf yang sama) dan dinormalisasi
ke rentang [0, 1] sehingga mudah diskalakan ke ukuran canvas berapa pun.
Hanya memakai pustaka standar Python (tanpa numpy).
"""

from __future__ import annotations

import math
import random
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from pembaca_graf import Graf

Posisi = Dict[str, Tuple[float, float]]


def _jarak_hop(graf: Graf, urutan: List[str]) -> Dict[str, Dict[str, float]]:
    """Hitung jarak hop semua pasangan simpul (graf dianggap tak berarah)."""
    tetangga: Dict[str, Set[str]] = {v: set() for v in urutan}
    for u, adj in graf.items():
        for v in adj:
            tetangga[u].add(v)
            tetangga[v].add(u)

    jarak: Dict[str, Dict[str, float]] = {}
    for s in urutan:
        d: Dict[str, float] = {s: 0.0}
        antrian = deque([s])
        while antrian:
            x = antrian.popleft()
            for y in tetangga[x]:
                if y not in d:
                    d[y] = d[x] + 1
                    antrian.append(y)
        jarak[s] = d

    # Simpul pada komponen berbeda diberi jarak "sedikit lebih jauh" dari maksimum
    terjauh = max((max(d.values()) for d in jarak.values()), default=1)
    for s in urutan:
        for t in urutan:
            jarak[s].setdefault(t, terjauh + 1)
    return jarak


def hitung_tata_letak(graf: Graf, urutan: List[str], awal: Optional[str] = None,
                      akhir: Optional[str] = None, iterasi: int = 400,
                      seed: int = 7) -> Posisi:
    """Hitung posisi simpul ternormalisasi ke [0, 1] × [0, 1].

    Args:
        graf: adjacency list.
        urutan: daftar simpul.
        awal, akhir: jika diberikan, tata letak diputar sehingga simpul awal
            berada di kiri dan simpul akhir di kanan (lebih mudah dibaca).
        iterasi: banyaknya iterasi perbaikan posisi.
        seed: benih acak agar hasil selalu sama.

    Returns:
        Dictionary ``{simpul: (x, y)}`` dengan x, y di rentang [0, 1].
    """
    n = len(urutan)
    if n == 0:
        return {}
    if n == 1:
        return {urutan[0]: (0.5, 0.5)}

    jarak = _jarak_hop(graf, urutan)
    acak = random.Random(seed)

    # Posisi awal: melingkar + sedikit gangguan acak (deterministik)
    jari = n / 2
    pos: Dict[str, List[float]] = {v: [jari * math.cos(2 * math.pi * i / n) + acak.uniform(-0.3, 0.3),
               jari * math.sin(2 * math.pi * i / n) + acak.uniform(-0.3, 0.3)]
           for i, v in enumerate(urutan)}

    # Stress majorization (versi per-simpul / Gauss-Seidel)
    for _ in range(iterasi):
        for i in urutan:
            xi, yi = pos[i]
            jumlah_x = jumlah_y = jumlah_w = 0.0
            for j in urutan:
                if i == j:
                    continue
                dij = jarak[i][j]
                w = 1.0 / (dij * dij)          # pasangan dekat lebih diutamakan
                xj, yj = pos[j]
                dx, dy = xi - xj, yi - yj
                panjang = math.hypot(dx, dy) or 1e-9
                jumlah_x += w * (xj + dij * dx / panjang)
                jumlah_y += w * (yj + dij * dy / panjang)
                jumlah_w += w
            pos[i] = [jumlah_x / jumlah_w, jumlah_y / jumlah_w]

    # Putar agar simpul awal di kiri dan simpul akhir di kanan
    if awal in pos and akhir in pos and awal != akhir:
        dx = pos[akhir][0] - pos[awal][0]
        dy = pos[akhir][1] - pos[awal][1]
        sudut = -math.atan2(dy, dx)
        c, s = math.cos(sudut), math.sin(sudut)
        pos = {v: [x * c - y * s, x * s + y * c] for v, (x, y) in pos.items()}

    # Normalisasi tiap sumbu ke [0, 1]; sumbu tanpa variasi diletakkan di tengah
    def normalisasi(nilai: List[float]) -> List[float]:
        kecil, besar = min(nilai), max(nilai)
        if besar - kecil < 1e-9:
            return [0.5] * len(nilai)
        return [(t - kecil) / (besar - kecil) for t in nilai]

    xs = normalisasi([pos[v][0] for v in urutan])
    ys = normalisasi([pos[v][1] for v in urutan])
    return {v: (x, y) for v, x, y in zip(urutan, xs, ys)}
