"""
MMAIKelompok1.py
================

File utama Tugas 1 MMAI1001 Kecerdasan Artificial:
pencarian jalur terpendek (shortest path) dengan **Dijkstra** dan **A***,
lengkap dengan visualisasi GUI (tkinter).

Program membaca graf dari file ``graf.txt``, lalu menampilkan:
jalur terpendek, bobot minimum, dan waktu running untuk setiap algoritma,
serta perbandingan keduanya.

Cara menjalankan
----------------
    python MMAIKelompok1.py                 # GUI, membaca graf.txt di folder ini
    python MMAIKelompok1.py graf_lain.txt   # GUI dengan file graf lain
    python MMAIKelompok1.py --cli           # mode teks (tanpa GUI)
    python MMAIKelompok1.py --cli graf.txt  # mode teks dengan file tertentu

Struktur modul
--------------
* ``pembaca_graf.py`` - membaca & memvalidasi file graf.
* ``algoritma.py``    - implementasi Dijkstra, A*, dan pengukuran waktu.
* ``tata_letak.py``   - menghitung posisi simpul untuk digambar.
* ``visualisasi.py``  - antarmuka grafis tkinter dan animasi pencarian.

Semua modul hanya memakai pustaka standar Python (≥ 3.8), jadi program dapat
dijalankan di Windows, macOS, maupun Linux tanpa instalasi paket tambahan.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from algoritma import ALGORITMA, HasilPencarian, format_angka, format_jalur, jalankan
from pembaca_graf import DataGraf, GrafError, baca_file_graf

# Ganti "X" dengan nomor kelompok (juga ganti nama file ini).
NAMA_KELOMPOK = "Kelompok X"
JUDUL_APLIKASI = f"MMAI {NAMA_KELOMPOK} – Visualisasi Shortest Path (Dijkstra vs A*)"

FOLDER_PROGRAM = Path(__file__).resolve().parent
FILE_GRAF_BAWAAN = "graf.txt"


def cari_file_graf(path: Optional[str]) -> Path:
    """Tentukan file graf yang dipakai.

    Jika ``path`` tidak diberikan, cari ``graf.txt`` di folder program terlebih
    dahulu, lalu di folder kerja saat ini (current working directory).
    """
    if path:
        return Path(path)
    for kandidat in (FOLDER_PROGRAM / FILE_GRAF_BAWAAN, Path.cwd() / FILE_GRAF_BAWAAN):
        if kandidat.exists():
            return kandidat
    return FOLDER_PROGRAM / FILE_GRAF_BAWAAN


def mode_teks(data: DataGraf) -> None:
    """Cetak hasil semua algoritma ke terminal dengan format sesuai soal."""
    print(f"File graf   : {data.sumber}")
    print(f"Graf        : {len(data.simpul)} simpul, {data.jumlah_sisi} sisi")
    print(f"Pencarian   : {data.awal} → {data.akhir}")
    for pesan in data.peringatan:
        print(f"Catatan     : {pesan}")

    semua: list[HasilPencarian] = []
    for nama in ALGORITMA:
        hasil = jalankan(nama, data.graf, data.awal, data.akhir, catat=False)
        semua.append(hasil)
        print(f"\n=== {nama} ===")
        print(f"Jalur terpendek: {format_jalur(hasil.jalur)}")
        print(f"Bobot minimum: {format_angka(hasil.bobot)}")
        print(f"Waktu runtime: {hasil.waktu_us:.2f} µs "
              f"(rata-rata dari {hasil.jumlah_ulang}× eksekusi)")
        print(f"Simpul diperluas: {hasil.simpul_diperluas}, relaksasi sisi: {hasil.relaksasi}")

    print("\n=== Perbandingan ===")
    print(f"{'Algoritma':<10} {'Bobot':>8} {'Waktu (µs)':>12} {'Diperluas':>10} {'Relaksasi':>10}")
    for h in semua:
        print(f"{h.algoritma:<10} {format_angka(h.bobot):>8} {h.waktu_us:>12.2f} "
              f"{h.simpul_diperluas:>10} {h.relaksasi:>10}")
    bobot_sama = len({format_angka(h.bobot) for h in semua}) == 1
    print("Kesimpulan: bobot minimum " + ("SAMA" if bobot_sama else "BERBEDA")
          + " pada semua algoritma.")


def _siapkan_output_utf8() -> None:
    """Pastikan karakter seperti '→' dan 'µ' dapat dicetak di terminal Windows."""
    for aliran in (sys.stdout, sys.stderr):
        try:
            aliran.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


def main(argv: Optional[list[str]] = None) -> int:
    """Titik masuk program. Mengembalikan kode keluar (0 = sukses)."""
    _siapkan_output_utf8()
    parser = argparse.ArgumentParser(
        description="Shortest path Dijkstra vs A* dengan visualisasi GUI (Tugas 1 MMAI1001).")
    parser.add_argument("file_graf", nargs="?", help="path file graf (bawaan: graf.txt)")
    parser.add_argument("--cli", action="store_true",
                        help="tampilkan hasil di terminal saja (tanpa GUI)")
    args = parser.parse_args(argv)

    path = cari_file_graf(args.file_graf)
    data: Optional[DataGraf] = None
    try:
        data = baca_file_graf(path)
    except FileNotFoundError:
        print(f"File graf tidak ditemukan: {path}", file=sys.stderr)
        if args.cli:
            return 1
    except GrafError as e:
        print(f"Format file graf tidak valid ({path}): {e}", file=sys.stderr)
        if args.cli:
            return 1

    if args.cli:
        if data is None:
            return 1
        mode_teks(data)
        return 0

    try:
        from visualisasi import jalankan_gui
    except ImportError as e:  # tkinter tidak terpasang
        print(f"GUI tidak dapat dibuka karena tkinter tidak tersedia ({e}).\n"
              "  • Ubuntu/Debian : sudo apt install python3-tk\n"
              "  • macOS Homebrew: brew install python-tk\n"
              "  • Windows/macOS installer python.org sudah menyertakan tkinter.\n"
              "Menampilkan hasil dalam mode teks:\n", file=sys.stderr)
        if data is None:
            return 1
        mode_teks(data)
        return 0

    # Jika graf gagal dibaca, GUI tetap dibuka agar pengguna bisa memilih file lain.
    jalankan_gui(JUDUL_APLIKASI, data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
