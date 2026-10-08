"""
pembaca_graf.py
===============

Modul untuk membaca file graf (misalnya ``graf.txt``) dan mengubahnya menjadi
struktur data Python yang siap dipakai oleh algoritma shortest path.

Format file yang didukung (sesuai soal Tugas 1 MMAI1001)::

    graph = {
    'V1': {'V2': 120, 'V4': 200},
    'V2': {'V1': 120, 'V3': 150, 'V5': 90},
    ...
    }
    V1 V15

* Bagian ``{ ... }`` adalah *adjacency list* berbobot: setiap simpul
  dipetakan ke dictionary ``{tetangga: bobot}``.
* Nama variabel di depan ``=`` boleh apa saja (``graph``, ``graf``, dll.)
  atau bahkan tidak ada sama sekali.
* Baris terakhir yang tidak kosong berisi **simpul awal** dan **simpul akhir**
  yang dipisahkan spasi.

Pembaca ini sengaja dibuat toleran terhadap masalah yang sering muncul
ketika teks disalin dari PDF/Word, misalnya tanda kutip "pintar" (‘ ’ “ ”),
spasi tak terputus (non-breaking space), dan BOM di awal file.

Parsing dictionary dilakukan dengan ``ast.literal_eval`` sehingga aman:
isi file **tidak pernah dieksekusi** sebagai kode Python.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union

# Tipe alias: graf berbobot berbentuk {simpul: {tetangga: bobot}}
Graf = Dict[str, Dict[str, float]]

# Karakter yang sering ikut tersalin dari PDF/Word dan perlu dinormalisasi.
_PENGGANTI_KARAKTER = {
    "‘": "'",  # ‘  kutip tunggal pembuka
    "’": "'",  # ’  kutip tunggal penutup
    "“": '"',  # “  kutip ganda pembuka
    "”": '"',  # ”  kutip ganda penutup
    " ": " ",  # spasi tak terputus
    "﻿": "",   # BOM (byte order mark)
}


class GrafError(ValueError):
    """Dilempar ketika isi file graf tidak sesuai format yang diharapkan."""


@dataclass
class DataGraf:
    """Hasil pembacaan file graf.

    Attributes:
        graf: adjacency list berbobot ``{simpul: {tetangga: bobot}}``.
        awal: simpul awal (dari baris terakhir file).
        akhir: simpul akhir/tujuan (dari baris terakhir file).
        simpul: daftar seluruh simpul sesuai urutan kemunculan di file.
        sumber: path file asal (kosong jika dibaca dari teks).
        peringatan: catatan non-fatal yang perlu diketahui pengguna.
    """

    graf: Graf
    awal: str
    akhir: str
    simpul: List[str]
    sumber: str = ""
    peringatan: List[str] = field(default_factory=lambda: [])  # type: List[str]

    def daftar_sisi(self) -> List[Tuple[str, str, float, bool]]:
        """Kembalikan daftar sisi unik untuk keperluan visualisasi.

        Sisi ``u-v`` yang muncul dua arah dengan bobot sama dihitung satu kali
        (graf tak berarah). Sisi yang hanya ada satu arah ditandai berarah.

        Returns:
            List tuple ``(u, v, bobot, berarah)``.
        """
        sisi: List[Tuple[str, str, float, bool]] = []
        sudah: Set[Tuple[str, str]] = set()
        for u in self.simpul:
            for v, w in self.graf[u].items():
                if (v, u) in sudah:
                    continue  # pasangan balik sudah dicatat
                balik = self.graf.get(v, {}).get(u)
                berarah = balik is None or balik != w
                sisi.append((u, v, w, berarah))
                sudah.add((u, v))
        return sisi

    @property
    def jumlah_sisi(self) -> int:
        """Jumlah sisi unik pada graf."""
        return len(self.daftar_sisi())


def _normalisasi_teks(teks: str) -> str:
    """Ganti karakter 'pintar' hasil salin dari PDF menjadi ASCII biasa."""
    for lama, baru in _PENGGANTI_KARAKTER.items():
        teks = teks.replace(lama, baru)
    return teks


def _cari_kurung_penutup(teks: str, posisi_buka: int) -> int:
    """Cari indeks ``}`` yang menutup ``{`` pada ``posisi_buka``.

    Fungsi memperhitungkan kurung bersarang dan mengabaikan kurung yang berada
    di dalam string (misalnya nama simpul ``'A{1}'``).

    Raises:
        GrafError: jika kurung tidak pernah ditutup.
    """
    kedalaman = 0
    kutip_aktif = ""  # karakter kutip yang sedang membuka string, jika ada
    for i in range(posisi_buka, len(teks)):
        c = teks[i]
        if kutip_aktif:
            if c == kutip_aktif:
                kutip_aktif = ""
            continue
        if c in ("'", '"'):
            kutip_aktif = c
        elif c == "{":
            kedalaman += 1
        elif c == "}":
            kedalaman -= 1
            if kedalaman == 0:
                return i
    raise GrafError("Kurung kurawal '{' pada definisi graf tidak ditutup dengan '}'.")


def _bersihkan_nama(nama: str) -> str:
    """Hilangkan spasi dan tanda kutip di sekitar nama simpul."""
    return str(nama).strip().strip("'\"").strip()


def parse_teks_graf(teks: str, sumber: str = "") -> DataGraf:
    """Ubah teks berformat graf.txt menjadi objek :class:`DataGraf`.

    Args:
        teks: seluruh isi file graf.
        sumber: nama/path file (hanya untuk informasi).

    Returns:
        DataGraf yang sudah divalidasi.

    Raises:
        GrafError: jika format tidak valid, bobot bukan angka/negatif,
            atau simpul awal/akhir tidak ditemukan.
    """
    teks = _normalisasi_teks(teks)

    # 1) Ambil bagian dictionary { ... }
    buka = teks.find("{")
    if buka < 0:
        raise GrafError("Definisi graf tidak ditemukan (tidak ada tanda '{').")
    tutup = _cari_kurung_penutup(teks, buka)
    try:
        mentah = ast.literal_eval(teks[buka:tutup + 1])
    except (ValueError, SyntaxError) as e:
        raise GrafError(f"Isi dictionary graf tidak valid: {e}") from None
    if not isinstance(mentah, dict) or not mentah:
        raise GrafError("Graf harus berupa dictionary yang tidak kosong.")

    mentah_dict: Dict[str, Dict[str, object]] = mentah  # type: ignore[assignment]

    # 2) Validasi dan bangun adjacency list
    graf: Graf = {}
    urutan: List[str] = []
    for u_mentah, tetangga in mentah_dict.items():
        u = _bersihkan_nama(str(u_mentah))
        if u not in graf:
            graf[u] = {}
            urutan.append(u)
        for v_mentah, w in tetangga.items():
            v = _bersihkan_nama(str(v_mentah))
            # bool adalah turunan int di Python, jadi ditolak secara eksplisit
            if isinstance(w, bool) or not isinstance(w, (int, float)):
                raise GrafError(f"Bobot sisi {u}→{v} harus berupa angka, bukan {w!r}.")
            if w < 0:
                raise GrafError(f"Bobot sisi {u}→{v} bernilai negatif ({w}). "
                                "Dijkstra dan A* hanya berlaku untuk bobot non-negatif.")
            graf[u][v] = w
            if v not in graf:
                # simpul yang baru muncul sebagai tetangga tetap didaftarkan
                graf[v] = {}
                urutan.append(v)

    # 3) Baca baris simpul awal & akhir (baris tidak kosong terakhir setelah '}')
    peringatan: List[str] = []
    baris = [b.strip() for b in teks[tutup + 1:].splitlines() if b.strip()]
    if baris:
        token = [_bersihkan_nama(t) for t in baris[-1].replace(",", " ").split()]
        token = [t for t in token if t]
        if len(token) < 2:
            raise GrafError("Baris terakhir harus berisi simpul awal dan simpul akhir, "
                            "contoh: V1 V15")
        awal, akhir = token[0], token[1]
    else:
        awal, akhir = urutan[0], urutan[-1]
        peringatan.append(f"Baris simpul awal/akhir tidak ada; dipakai {awal} → {akhir}.")

    for nama, peran in ((awal, "awal"), (akhir, "akhir")):
        if nama not in graf:
            raise GrafError(f"Simpul {peran} '{nama}' tidak terdapat di dalam graf.")

    data = DataGraf(graf=graf, awal=awal, akhir=akhir, simpul=urutan,
                    sumber=sumber, peringatan=peringatan)

    # 4) Catat sisi satu arah (graf berarah) sebagai informasi saja
    berarah = [f"{u}→{v}" for u, v, _, arah in data.daftar_sisi() if arah]
    if berarah:
        peringatan.append("Sisi berikut hanya satu arah / bobot berbeda (diperlakukan "
                          "sebagai sisi berarah): " + ", ".join(berarah))
    return data


def baca_file_graf(path: Union[str, Path]) -> DataGraf:
    """Baca file graf dari disk.

    Args:
        path: lokasi file graf (mis. ``graf.txt``).

    Returns:
        DataGraf hasil parsing.

    Raises:
        FileNotFoundError: jika file tidak ada.
        GrafError: jika isi file tidak valid.
    """
    path = Path(path)
    try:
        teks = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        # Cadangan untuk file yang disimpan dengan encoding lama (mis. Windows-1252)
        teks = path.read_text(encoding="latin-1")
    return parse_teks_graf(teks, sumber=str(path))
