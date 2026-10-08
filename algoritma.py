"""
algoritma.py
============

Implementasi dua algoritma shortest path yang dibandingkan pada tugas ini:

1. **Dijkstra**  - greedy, selalu memperluas simpul dengan jarak ``g`` terkecil.
2. **A\\* (A-Star)** - memperluas simpul dengan ``f = g + h`` terkecil, di mana
   ``h`` adalah estimasi (heuristik) sisa biaya menuju tujuan.

Kedua fungsi dapat (opsional) mencatat setiap langkah pencarian ke dalam daftar
:class:`Langkah`. Catatan ini dipakai GUI untuk menganimasikan proses pencarian
secara dinamis. Saat mengukur waktu, pencatatan dimatikan agar pengukuran
mencerminkan kecepatan algoritma yang sesungguhnya.

Heuristik A* tanpa koordinat
----------------------------
File graf hanya berisi bobot sisi, tanpa koordinat simpul, sehingga jarak
Euclidean/Manhattan tidak dapat dipakai. Sebagai gantinya digunakan::

    h(n) = w_min x hop(n, tujuan)

* ``hop(n, tujuan)`` = jumlah sisi minimum dari ``n`` ke tujuan (dihitung
  dengan BFS dari tujuan pada graf terbalik).
* ``w_min`` = bobot sisi terkecil di seluruh graf.

Heuristik ini **admissible** (tidak pernah melebihi biaya sebenarnya) karena
jalur mana pun dari ``n`` ke tujuan minimal melewati ``hop(n)`` sisi, dan
setiap sisi berbobot minimal ``w_min``. Heuristik ini juga **konsisten**:
``h(u) ≤ w(u,v) + h(v)`` karena ``hop(u) ≤ 1 + hop(v)`` dan ``w(u,v) ≥ w_min``.
Akibatnya A* dijamin menemukan jalur optimal dan setiap simpul cukup
diperluas satu kali.

Kompleksitas (V = jumlah simpul, E = jumlah sisi)
-------------------------------------------------
* Dijkstra (binary heap, *lazy deletion*): waktu O((V + E) log V),
  ruang O(V + E).
* A* (heuristik konsisten): kasus terburuk sama dengan Dijkstra,
  O((V + E) log V) + O(V + E) untuk menghitung heuristik dengan BFS;
  ruang O(V + E). Dalam praktik A* biasanya memperluas lebih sedikit simpul.
"""

from __future__ import annotations

import gc
import heapq
import time
from collections import deque
from dataclasses import dataclass, field
from itertools import count
from typing import Callable, Dict, List, Optional, Set, Tuple

from pembaca_graf import Graf

INF = float("inf")


# --------------------------------------------------------------------------- #
# Struktur data hasil
# --------------------------------------------------------------------------- #


@dataclass
class Langkah:
    """Satu peristiwa dalam proses pencarian (dipakai untuk animasi GUI).

    Attributes:
        jenis: ``"mulai"``, ``"ambil"`` (simpul dikeluarkan dari antrian
            prioritas dan diperluas), ``"periksa"`` (relaksasi sisi), atau
            ``"selesai"``.
        simpul: simpul utama pada peristiwa ini.
        tetangga: simpul tetangga (khusus ``"periksa"``).
        g: nilai g (jarak dari awal) untuk simpul/tetangga terkait.
        h: nilai heuristik (0 untuk Dijkstra).
        g_lama: nilai g tetangga sebelum relaksasi (khusus ``"periksa"``).
        diperbarui: True jika relaksasi menghasilkan jarak yang lebih kecil.
        keterangan: kalimat penjelasan yang ditampilkan di log GUI.
    """

    jenis: str
    simpul: str
    tetangga: Optional[str] = None
    g: float = 0.0
    h: float = 0.0
    g_lama: float = INF
    diperbarui: bool = False
    keterangan: str = ""


@dataclass
class HasilPencarian:
    """Hasil akhir sebuah algoritma shortest path.

    Attributes:
        algoritma: nama algoritma.
        jalur: daftar simpul dari awal ke akhir (kosong jika tidak ada jalur).
        bobot: total bobot jalur (``inf`` jika tidak ada jalur).
        simpul_diperluas: banyaknya simpul yang dikeluarkan dari antrian dan
            diperluas (ukuran efisiensi pencarian).
        relaksasi: banyaknya sisi yang diperiksa (relaksasi).
        langkah: catatan langkah untuk animasi (kosong jika tidak dicatat).
        heuristik: nilai h untuk setiap simpul (khusus A*).
        waktu_us: rata-rata waktu eksekusi dalam mikrodetik.
        jumlah_ulang: berapa kali algoritma dijalankan untuk merata-rata waktu.
    """

    algoritma: str
    jalur: List[str]
    bobot: float
    simpul_diperluas: int
    relaksasi: int
    langkah: List[Langkah] = field(default_factory=lambda: [])  # type: List[Langkah]
    heuristik: Dict[str, float] = field(default_factory=lambda: {})  # type: Dict[str, float]
    waktu_us: float = 0.0
    jumlah_ulang: int = 0

    @property
    def ditemukan(self) -> bool:
        """True jika jalur dari awal ke akhir ditemukan."""
        return bool(self.jalur)


# --------------------------------------------------------------------------- #
# Fungsi bantu
# --------------------------------------------------------------------------- #
def format_angka(x: float) -> str:
    """Format angka agar rapi: 505.0 -> '505', 12.5 -> '12.5', inf -> '∞'."""
    if x == INF:
        return "∞"
    if float(x).is_integer():
        return str(int(x))
    return f"{x:.2f}".rstrip("0").rstrip(".")


def format_jalur(jalur: List[str]) -> str:
    """Gabungkan daftar simpul menjadi teks 'V1→V2→V3'."""
    return "→".join(jalur) if jalur else "(tidak ada jalur)"


def _bangun_jalur(induk: Dict[str, Optional[str]], akhir: str) -> List[str]:
    """Telusuri balik pointer ``induk`` dari simpul akhir hingga simpul awal."""
    if akhir not in induk:
        return []
    jalur: List[str] = []
    simpul: Optional[str] = akhir
    while simpul is not None:
        jalur.append(simpul)
        simpul = induk[simpul]
    jalur.reverse()
    return jalur


# --------------------------------------------------------------------------- #
# Algoritma 1: Dijkstra
# --------------------------------------------------------------------------- #
def dijkstra(graf: Graf, awal: str, akhir: str, catat: bool = False) -> HasilPencarian:
    """Cari jalur terpendek dari ``awal`` ke ``akhir`` dengan algoritma Dijkstra.

    Antrian prioritas diimplementasikan dengan ``heapq`` (binary min-heap).
    Entri lama di heap tidak dihapus, melainkan diabaikan saat dikeluarkan
    (*lazy deletion*) karena simpulnya sudah ada di himpunan ``selesai``.

    Args:
        graf: adjacency list berbobot non-negatif.
        awal: simpul awal.
        akhir: simpul tujuan.
        catat: True untuk merekam setiap langkah (untuk animasi).

    Returns:
        HasilPencarian berisi jalur, bobot minimum, dan statistik.
    """
    jarak: Dict[str, float] = {awal: 0}
    induk: Dict[str, Optional[str]] = {awal: None}
    urutan = count()  # pemecah seri agar heap stabil & tidak membandingkan string
    antrian = [(0.0, next(urutan), awal)]
    selesai: Set[str] = set()
    relaksasi = 0
    langkah: List[Langkah] = []

    if catat:
        langkah.append(Langkah("mulai", awal, g=0,
                               keterangan=f"Mulai dari {awal}: jarak({awal}) = 0, "
                                          "simpul lain = ∞."))

    while antrian:
        d, _, u = heapq.heappop(antrian)
        if u in selesai:
            continue  # entri usang (lazy deletion)
        selesai.add(u)
        if catat:
            langkah.append(Langkah("ambil", u, g=d,
                                   keterangan=f"Ambil {u} (jarak terkecil = {format_angka(d)})"
                                              " → jarak final."))
        if u == akhir:
            break  # tujuan sudah final, pencarian boleh berhenti

        for v, w in graf[u].items():
            if v in selesai:
                continue
            relaksasi += 1
            baru = d + w
            lama = jarak.get(v, INF)
            lebih_baik = baru < lama
            if lebih_baik:
                jarak[v] = baru
                induk[v] = u
                heapq.heappush(antrian, (float(baru), next(urutan), v))
            if catat:
                tanda = "<" if lebih_baik else "≥"
                aksi = f"perbarui jarak({v})" if lebih_baik else "tidak berubah"
                langkah.append(Langkah(
                    "periksa", u, tetangga=v, g=baru, g_lama=lama, diperbarui=lebih_baik,
                    keterangan=f"   Periksa {u}→{v}: {format_angka(d)} + {format_angka(w)} = "
                               f"{format_angka(baru)} {tanda} {format_angka(lama)} → {aksi}"))

    jalur = _bangun_jalur(induk, akhir) if akhir in selesai else []
    bobot = jarak[akhir] if jalur else INF
    if catat:
        langkah.append(Langkah("selesai", akhir, g=bobot, keterangan=_teks_selesai(jalur, bobot)))
    return HasilPencarian("Dijkstra", jalur, bobot, len(selesai), relaksasi, langkah)


# --------------------------------------------------------------------------- #
# Algoritma 2: A* (A-Star)
# --------------------------------------------------------------------------- #
def heuristik_hop(graf: Graf, akhir: str) -> Dict[str, float]:
    """Hitung heuristik ``h(n) = w_min × hop(n, akhir)`` untuk semua simpul.

    Jumlah hop dihitung dengan BFS mulai dari ``akhir`` pada graf terbalik
    (mengikuti arah sisi masuk), sehingga tetap benar untuk graf berarah.
    Simpul yang tidak dapat mencapai tujuan mendapat ``h = inf``.

    Kompleksitas: O(V + E) waktu dan ruang.
    """
    w_min = min((w for adj in graf.values() for w in adj.values()), default=0)

    # Graf terbalik: untuk setiap v, siapa saja u yang punya sisi u→v
    masuk: Dict[str, List[str]] = {v: [] for v in graf}
    for u, adj in graf.items():
        for v in adj:
            masuk.setdefault(v, []).append(u)

    hop = {akhir: 0}
    antrian = deque([akhir])
    while antrian:
        v = antrian.popleft()
        for u in masuk.get(v, ()):
            if u not in hop:
                hop[u] = hop[v] + 1
                antrian.append(u)

    return {v: (w_min * hop[v] if v in hop else INF) for v in graf}


def a_star(graf: Graf, awal: str, akhir: str, catat: bool = False) -> HasilPencarian:
    """Cari jalur terpendek dengan algoritma A* (A-Star).

    Simpul diperluas berdasarkan ``f(n) = g(n) + h(n)`` terkecil. Bila ada
    nilai f yang sama, simpul dengan h lebih kecil (lebih dekat ke tujuan)
    didahulukan. Karena heuristik konsisten, simpul yang sudah diperluas
    (closed set) tidak perlu dibuka ulang.

    Args:
        graf: adjacency list berbobot non-negatif.
        awal: simpul awal.
        akhir: simpul tujuan.
        catat: True untuk merekam setiap langkah (untuk animasi).

    Returns:
        HasilPencarian berisi jalur, bobot minimum, statistik, dan nilai h.
    """
    h = heuristik_hop(graf, akhir)
    g: Dict[str, float] = {awal: 0}
    induk: Dict[str, Optional[str]] = {awal: None}
    urutan = count()
    antrian = [(h[awal], h[awal], next(urutan), awal)]  # (f, h, seri, simpul)
    tertutup: Set[str] = set()
    relaksasi = 0
    langkah: List[Langkah] = []

    if catat:
        langkah.append(Langkah("mulai", awal, g=0, h=h[awal],
                               keterangan=f"Mulai dari {awal}: g = 0, h = {format_angka(h[awal])}, "
                                          f"f = {format_angka(h[awal])}  "
                                          "[h(n) = bobot sisi minimum × jumlah hop ke tujuan]"))

    if h[awal] == INF:
        antrian.clear()  # tujuan tidak terjangkau dari awal → langsung selesai

    while antrian:
        f, _, _, u = heapq.heappop(antrian)
        if u in tertutup:
            continue
        tertutup.add(u)
        if catat:
            langkah.append(Langkah("ambil", u, g=g[u], h=h[u],
                                   keterangan=f"Ambil {u} (f terkecil = {format_angka(g[u])} + "
                                              f"{format_angka(h[u])} = {format_angka(f)})."))
        if u == akhir:
            break

        for v, w in graf[u].items():
            if v in tertutup or h.get(v, INF) == INF:
                continue  # sudah final, atau tidak mungkin mencapai tujuan
            relaksasi += 1
            baru = g[u] + w
            lama = g.get(v, INF)
            lebih_baik = baru < lama
            if lebih_baik:
                g[v] = baru
                induk[v] = u
                heapq.heappush(antrian, (baru + h[v], h[v], next(urutan), v))
            if catat:
                tanda = "<" if lebih_baik else "≥"
                aksi = (f"perbarui, f({v}) = {format_angka(baru)} + {format_angka(h[v])} = "
                        f"{format_angka(baru + h[v])}") if lebih_baik else "tidak berubah"
                langkah.append(Langkah(
                    "periksa", u, tetangga=v, g=baru, h=h[v], g_lama=lama, diperbarui=lebih_baik,
                    keterangan=f"   Periksa {u}→{v}: g = {format_angka(g[u])} + {format_angka(w)} = "
                               f"{format_angka(baru)} {tanda} {format_angka(lama)} → {aksi}"))

    jalur = _bangun_jalur(induk, akhir) if akhir in tertutup else []
    bobot = g[akhir] if jalur else INF
    if catat:
        langkah.append(Langkah("selesai", akhir, g=bobot, keterangan=_teks_selesai(jalur, bobot)))
    return HasilPencarian("A*", jalur, bobot, len(tertutup), relaksasi, langkah, heuristik=h)


def _teks_selesai(jalur: List[str], bobot: float) -> str:
    """Kalimat penutup untuk log animasi."""
    if not jalur:
        return "Selesai: tidak ada jalur menuju simpul tujuan."
    return f"Selesai: jalur {format_jalur(jalur)} dengan bobot {format_angka(bobot)}."


# --------------------------------------------------------------------------- #
# Registrasi algoritma & pengukuran waktu
# --------------------------------------------------------------------------- #
FungsiAlgoritma = Callable[..., HasilPencarian]

#: Daftar algoritma yang tersedia. Tambahkan algoritma baru cukup di sini.
ALGORITMA: Dict[str, FungsiAlgoritma] = {
    "Dijkstra": dijkstra,
    "A*": a_star,
}


def ukur_waktu(fungsi: FungsiAlgoritma, graf: Graf, awal: str, akhir: str,
               target_detik: float = 0.05, maks_ulang: int = 5000) -> Tuple[float, int]:
    """Ukur rata-rata waktu eksekusi algoritma (tanpa pencatatan langkah).

    Satu kali eksekusi pada graf kecil hanya butuh beberapa mikrodetik sehingga
    hasilnya sangat dipengaruhi noise. Karena itu algoritma dijalankan berulang
    (jumlah ulang menyesuaikan agar total ≈ ``target_detik``) lalu dirata-rata.
    Garbage collector dimatikan sementara, seperti yang dilakukan modul
    ``timeit``, agar tidak mengganggu pengukuran.

    Returns:
        Tuple ``(rata_rata_mikrodetik, jumlah_ulang)``.
    """
    fungsi(graf, awal, akhir)  # pemanasan (warm-up)
    gc_aktif = gc.isenabled()
    gc.disable()
    try:
        t0 = time.perf_counter()
        fungsi(graf, awal, akhir)
        sekali = max(time.perf_counter() - t0, 1e-7)
        ulang = int(min(maks_ulang, max(10, target_detik / sekali)))

        mulai = time.perf_counter()
        for _ in range(ulang):
            fungsi(graf, awal, akhir)
        total = time.perf_counter() - mulai
    finally:
        if gc_aktif:
            gc.enable()
    return total / ulang * 1e6, ulang


def jalankan(nama: str, graf: Graf, awal: str, akhir: str, catat: bool = True) -> HasilPencarian:
    """Jalankan algoritma ``nama`` lengkap dengan pengukuran waktu.

    Algoritma dijalankan sekali dengan pencatatan langkah (untuk animasi),
    lalu diukur waktunya secara terpisah tanpa pencatatan.
    """
    fungsi = ALGORITMA[nama]
    hasil = fungsi(graf, awal, akhir, catat=catat)
    hasil.waktu_us, hasil.jumlah_ulang = ukur_waktu(fungsi, graf, awal, akhir)
    return hasil
