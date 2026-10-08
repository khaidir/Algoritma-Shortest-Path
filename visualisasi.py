"""
visualisasi.py
==============

Antarmuka grafis (GUI) berbasis **tkinter** untuk memvisualisasikan proses
pencarian jalur terpendek secara dinamis.

Fitur utama
-----------
* Menggambar graf (simpul, sisi, bobot) dengan tata letak otomatis.
  Simpul dapat digeser dengan mouse agar tampilan lebih rapi.
* Memilih simpul awal, simpul akhir, dan algoritma (Dijkstra / A*).
* Animasi langkah demi langkah: simpul yang sedang diperluas, simpul di
  antrian prioritas (frontier), simpul yang sudah final, sisi yang sedang
  direlaksasi, serta nilai g (dan h untuk A*) di setiap simpul.
* Menampilkan jalur terpendek, bobot minimum, waktu running, dan statistik.
* Tabel perbandingan Dijkstra vs A* untuk analisis.

Pintasan keyboard: ``Spasi`` = animasikan/jeda, ``→`` = satu langkah,
``Enter`` = hasil langsung, ``R`` = reset.

tkinter termasuk pustaka standar Python sehingga tidak perlu instalasi
tambahan (lihat README jika tkinter belum tersedia di Linux/macOS Homebrew).
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from algoritma import (ALGORITMA, HasilPencarian, format_angka, format_jalur, jalankan)
from pembaca_graf import DataGraf, GrafError, baca_file_graf
from tata_letak import hitung_tata_letak

# --------------------------------------------------------------------------- #
# Konstanta tampilan
# --------------------------------------------------------------------------- #
WARNA = {
    "latar": "#f7f9fc",
    "sisi": "#c3ccd6",
    "teks_bobot": "#4a5568",
    "simpul": "#ffffff",
    "garis_simpul": "#5b6b7f",
    "teks": "#1f2933",
    "awal": "#2e9d5b",          # simpul awal
    "akhir": "#d64545",         # simpul tujuan
    "sekarang": "#ff8c1a",      # simpul yang sedang diperluas
    "frontier": "#ffd166",      # simpul di antrian prioritas
    "final": "#a8c8f0",         # simpul yang jaraknya sudah final
    "pohon": "#7aa7e0",         # sisi pada pohon jalur sementara (pointer induk)
    "periksa_baik": "#2e9d5b",  # relaksasi berhasil memperbarui jarak
    "periksa_buruk": "#d64545", # relaksasi tidak memperbarui jarak
    "jalur": "#7b3fe4",         # jalur terpendek akhir
}
JARI_SIMPUL = 20      # jari-jari lingkaran simpul (piksel)
MARGIN = 45           # jarak tepi canvas ke simpul terluar (piksel)
RUANG_LEGENDA = 52    # tinggi area legenda (dua baris) di atas canvas (piksel)
FONT_SIMPUL = ("Helvetica", 10, "bold")
FONT_KECIL = ("Helvetica", 9)
FONT_KECIL_TEBAL = ("Helvetica", 9, "bold")


@dataclass
class KeadaanVisual:
    """Keadaan pencarian yang sedang ditampilkan di canvas.

    Keadaan ini dibangun ulang dengan "memutar" daftar :class:`Langkah`
    hasil algoritma satu per satu.
    """

    final: Set[str] = field(default_factory=lambda: set())  # type: Set[str]
    frontier: Set[str] = field(default_factory=lambda: set())  # type: Set[str]
    sekarang: Optional[str] = None
    sisi_aktif: Optional[Tuple[str, str]] = None
    sisi_aktif_berhasil: bool = False
    g: Dict[str, float] = field(default_factory=lambda: {})  # type: Dict[str, float]
    h: Dict[str, float] = field(default_factory=lambda: {})  # type: Dict[str, float]
    induk: Dict[str, str] = field(default_factory=lambda: {})  # type: Dict[str, str]
    jalur: List[str] = field(default_factory=lambda: [])  # type: List[str]


class AplikasiShortestPath:
    """Jendela utama aplikasi visualisasi shortest path."""

    def __init__(self, root: tk.Tk, judul: str, data: Optional[DataGraf] = None) -> None:
        self.root = root
        self.root.title(judul)
        # Ukuran jendela menyesuaikan layar (laptop kecil tetap muat)
        lebar = min(1600, self.root.winfo_screenwidth() - 40)
        tinggi = min(960, self.root.winfo_screenheight() - 80)
        self.root.geometry(f"{lebar}x{tinggi}")
        self.root.minsize(1050, 680)

        # Data graf & tata letak
        self.data: Optional[DataGraf] = None
        self.posisi: Dict[str, Tuple[float, float]] = {}   # koordinat ternormalisasi
        self.sisi: List[Tuple[str, str, float, bool]] = []

        # Keadaan animasi
        self.keadaan = KeadaanVisual()
        self.hasil_aktif: Optional[HasilPencarian] = None   # hasil yang sedang dianimasikan
        self.indeks_langkah = 0
        self.berjalan = False
        self.id_after: Optional[str] = None
        self.hasil_per_algoritma: Dict[str, HasilPencarian] = {}
        self.simpul_diseret: Optional[str] = None
        self.teks_ringkasan = ""   # ringkasan hasil yang ditulis di bawah canvas

        self._bangun_ui()
        self._ikat_pintasan()
        if data is not None:
            self.muat_data(data)

    # ------------------------------------------------------------------ #
    # Pembuatan antarmuka
    # ------------------------------------------------------------------ #
    def _bangun_ui(self) -> None:
        """Susun widget: pengaturan & kontrol di atas, canvas + panel hasil di
        tengah, log proses di bawah. Tata letak ini muat di layar 1366×768."""
        gaya = ttk.Style()
        if self.root.tk.call("tk", "windowingsystem") != "aqua":
            try:
                gaya.theme_use("clam")  # tampilan lebih modern di Windows/Linux
            except tk.TclError:
                pass
        gaya.configure("Nilai.TLabel", font=("Helvetica", 10, "bold"))
        gaya.configure("Treeview", rowheight=22)

        utama = ttk.Frame(self.root, padding=8)
        utama.pack(fill=tk.BOTH, expand=True)

        # Urutan pack penting: bagian atas & bawah dipasang lebih dulu agar
        # tidak terdesak ketika jendela diperkecil; bagian tengah mengisi sisanya.
        self._bangun_panel_pengaturan(utama)
        self._bangun_panel_log(utama)

        tengah = ttk.Frame(utama)
        tengah.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        kanan = ttk.Frame(tengah, width=420)
        kanan.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        kanan.pack_propagate(False)
        self._bangun_panel_hasil(kanan)
        self._bangun_panel_perbandingan(kanan)

        self.canvas = tk.Canvas(tengah, bg=WARNA["latar"], highlightthickness=1,
                                highlightbackground="#d5dbe3")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.gambar())
        self.canvas.bind("<ButtonPress-1>", self._mulai_seret)
        self.canvas.bind("<B1-Motion>", self._seret)
        self.canvas.bind("<ButtonRelease-1>", self._akhiri_seret)

    def _bangun_panel_pengaturan(self, induk: ttk.Frame) -> None:
        """Baris atas: file graf, simpul awal/akhir, algoritma, kecepatan, dan
        tombol-tombol kontrol pencarian."""
        bingkai = ttk.LabelFrame(induk, text="Data Graf, Pengaturan & Kontrol", padding=(8, 4))
        bingkai.pack(side=tk.TOP, fill=tk.X)

        # ----- Baris 1: data & pengaturan -----
        baris1 = ttk.Frame(bingkai)
        baris1.pack(fill=tk.X)
        ttk.Button(baris1, text="Buka file graf…", command=self.buka_file,
                   takefocus=False).pack(side=tk.LEFT)
        self.var_file = tk.StringVar(value="Belum ada file")
        ttk.Label(baris1, textvariable=self.var_file, width=30).pack(side=tk.LEFT, padx=(8, 4))

        ttk.Separator(baris1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(baris1, text="Simpul awal").pack(side=tk.LEFT, padx=(0, 4))
        self.var_awal = tk.StringVar()
        self.cb_awal = ttk.Combobox(baris1, textvariable=self.var_awal, state="readonly",
                                    width=7, takefocus=False)
        self.cb_awal.pack(side=tk.LEFT)
        ttk.Label(baris1, text="Simpul akhir").pack(side=tk.LEFT, padx=(12, 4))
        self.var_akhir = tk.StringVar()
        self.cb_akhir = ttk.Combobox(baris1, textvariable=self.var_akhir, state="readonly",
                                     width=7, takefocus=False)
        self.cb_akhir.pack(side=tk.LEFT)
        for cb in (self.cb_awal, self.cb_akhir):
            cb.bind("<<ComboboxSelected>>", lambda _e: self._query_berubah())

        ttk.Separator(baris1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(baris1, text="Algoritma").pack(side=tk.LEFT, padx=(0, 6))
        self.var_algoritma = tk.StringVar(value=next(iter(ALGORITMA)))
        for nama in ALGORITMA:
            ttk.Radiobutton(baris1, text=nama, value=nama, variable=self.var_algoritma,
                            command=self._algoritma_berubah, takefocus=False
                            ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Separator(baris1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(baris1, text="Jeda animasi").pack(side=tk.LEFT, padx=(0, 4))
        self.var_jeda = tk.IntVar(value=600)
        self.var_teks_jeda = tk.StringVar(value="600 ms")
        ttk.Scale(baris1, from_=50, to=1500, orient=tk.HORIZONTAL, length=130,
                  variable=self.var_jeda, takefocus=False,
                  command=lambda nilai: self.var_teks_jeda.set(f"{float(nilai):.0f} ms")
                  ).pack(side=tk.LEFT)
        ttk.Label(baris1, textvariable=self.var_teks_jeda, width=8).pack(side=tk.LEFT, padx=4)

        # ----- Baris 2: tombol kontrol -----
        baris2 = ttk.Frame(bingkai)
        baris2.pack(fill=tk.X, pady=(6, 2))
        self.tombol_animasi = ttk.Button(baris2, text="▶  Animasikan  [Spasi]", width=22,
                                         command=self.animasikan, takefocus=False)
        self.tombol_animasi.pack(side=tk.LEFT, padx=(0, 6))
        for teks, perintah in [("Satu langkah  [→]", self.satu_langkah),
                               ("Hasil langsung  [Enter]", self.hasil_langsung),
                               ("Reset  [R]", self.reset),
                               ("Bandingkan Dijkstra vs A*", self.bandingkan)]:
            ttk.Button(baris2, text=teks, command=perintah,
                       takefocus=False).pack(side=tk.LEFT, padx=(0, 6))

    def _bangun_panel_log(self, induk: ttk.Frame) -> None:
        """Bagian bawah: kotak log langkah pencarian dan baris status."""
        bingkai_log = ttk.LabelFrame(induk, text="Log proses pencarian", padding=4)
        bingkai_log.pack(side=tk.BOTTOM, fill=tk.X)
        self.teks_log = tk.Text(bingkai_log, height=7, wrap="none", font="TkFixedFont",
                                bg="#ffffff", fg=WARNA["teks"], relief="flat",
                                state="disabled")
        gulir = ttk.Scrollbar(bingkai_log, orient=tk.VERTICAL, command=self.teks_log.yview)  # type: ignore[arg-type]
        self.teks_log.configure(yscrollcommand=gulir.set)
        gulir.pack(side=tk.RIGHT, fill=tk.Y)
        self.teks_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.teks_log.tag_configure("judul", font=("Helvetica", 10, "bold"))
        self.teks_log.tag_configure("ambil", foreground="#1d4ed8")
        self.teks_log.tag_configure("baik", foreground="#15803d")
        self.teks_log.tag_configure("buruk", foreground="#8a94a3")
        self.teks_log.tag_configure("hasil", foreground=WARNA["jalur"],
                                    font=("Helvetica", 10, "bold"))
        self.teks_log.tag_configure("peringatan", foreground="#b45309")

        self.var_status = tk.StringVar(value="Muat file graf untuk memulai.")
        ttk.Label(induk, textvariable=self.var_status, anchor="w",
                  padding=(2, 4, 2, 2)).pack(side=tk.BOTTOM, fill=tk.X)

    def _bangun_panel_hasil(self, induk: ttk.Frame) -> None:
        """Panel hasil: jalur, bobot minimum, waktu running, dan statistik."""
        bingkai = ttk.LabelFrame(induk, text="Hasil", padding=6)
        bingkai.pack(fill=tk.X)
        bingkai.columnconfigure(1, weight=1)
        self.var_hasil: Dict[str, tk.StringVar] = {}
        baris = [("algoritma", "Algoritma"), ("jalur", "Jalur terpendek"),
                 ("bobot", "Bobot minimum"), ("waktu", "Waktu runtime"),
                 ("diperluas", "Simpul diperluas"), ("relaksasi", "Relaksasi sisi")]
        for i, (kunci, label) in enumerate(baris):
            ttk.Label(bingkai, text=label).grid(row=i, column=0, sticky="nw", pady=1,
                                               padx=(0, 8))
            var = tk.StringVar(value="-")
            ttk.Label(bingkai, textvariable=var, style="Nilai.TLabel",
                      wraplength=285).grid(row=i, column=1, sticky="w", pady=1)
            self.var_hasil[kunci] = var

    def _bangun_panel_perbandingan(self, induk: ttk.Frame) -> None:
        """Tabel perbandingan hasil Dijkstra dan A*."""
        bingkai = ttk.LabelFrame(induk, text="Perbandingan Algoritma", padding=6)
        bingkai.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        kolom = ["metrik"] + list(ALGORITMA)
        self.tabel = ttk.Treeview(bingkai, columns=kolom, show="headings", height=5,
                                  selectmode="none")
        self.tabel.heading("metrik", text="Metrik")
        self.tabel.column("metrik", width=122, anchor="w", stretch=False)
        for nama in ALGORITMA:
            self.tabel.heading(nama, text=nama)
            self.tabel.column(nama, width=132, anchor="center", stretch=True)
        self.baris_tabel = [("jalur", "Jalur"), ("bobot", "Bobot minimum"),
                            ("waktu", "Waktu (µs)"), ("diperluas", "Simpul diperluas"),
                            ("relaksasi", "Relaksasi sisi")]
        for kunci, label in self.baris_tabel:
            self.tabel.insert("", tk.END, iid=kunci, values=[label] + ["-"] * len(ALGORITMA))
        self.tabel.pack(fill=tk.X)
        self.var_kesimpulan = tk.StringVar(value="Jalankan kedua algoritma untuk melihat "
                                                 "perbandingan.")
        ttk.Label(bingkai, textvariable=self.var_kesimpulan, wraplength=390,
                  justify="left").pack(anchor="w", pady=(6, 0))

    def _ikat_pintasan(self) -> None:
        """Pintasan keyboard (berguna saat presentasi/rekam video)."""
        self.root.bind("<space>", lambda _e: self.animasikan())
        self.root.bind("<Right>", lambda _e: self.satu_langkah())
        self.root.bind("<Return>", lambda _e: self.hasil_langsung())
        self.root.bind("<KeyPress-r>", lambda _e: self.reset())
        self.root.bind("<KeyPress-R>", lambda _e: self.reset())

    # ------------------------------------------------------------------ #
    # Memuat data graf
    # ------------------------------------------------------------------ #
    def buka_file(self) -> None:
        """Tampilkan dialog untuk memilih file graf lalu memuatnya."""
        folder = Path(self.data.sumber).parent if self.data and self.data.sumber else Path.cwd()
        path = filedialog.askopenfilename(
            title="Pilih file graf", initialdir=str(folder),
            filetypes=[("File teks", "*.txt"), ("Semua file", "*.*")])
        if not path:
            return
        try:
            self.muat_data(baca_file_graf(path))
        except (OSError, GrafError) as e:
            messagebox.showerror("Gagal membaca graf", str(e), parent=self.root)

    def muat_data(self, data: DataGraf) -> None:
        """Pasang data graf baru: hitung tata letak dan isi pilihan simpul."""
        self.data = data
        self.sisi = data.daftar_sisi()
        self.posisi = hitung_tata_letak(data.graf, data.simpul, data.awal, data.akhir)
        self.cb_awal["values"] = data.simpul
        self.cb_akhir["values"] = data.simpul
        self.var_awal.set(data.awal)
        self.var_akhir.set(data.akhir)
        nama_file = Path(data.sumber).name if data.sumber else "(teks)"
        nama_pendek = nama_file if len(nama_file) <= 14 else nama_file[:12] + "…"
        self.var_file.set(f"{nama_pendek} • {len(data.simpul)} simpul, {data.jumlah_sisi} sisi")
        self._kosongkan_perbandingan()
        self.reset()
        self._bersihkan_log()
        self._log(f"Graf dimuat dari {nama_file}: {len(data.simpul)} simpul, "
                  f"{data.jumlah_sisi} sisi. Simpul awal/akhir dari file: "
                  f"{data.awal} → {data.akhir}.", "judul")
        for pesan in data.peringatan:
            self._log("Catatan: " + pesan, "peringatan")
        self._log("Tekan Spasi untuk animasi, → untuk satu langkah, atau Enter untuk hasil "
                  "langsung. Simpul dapat digeser dengan mouse.")

    # ------------------------------------------------------------------ #
    # Kontrol pencarian & animasi
    # ------------------------------------------------------------------ #
    def _siapkan_pencarian(self) -> bool:
        """Jalankan algoritma terpilih (dengan pencatatan langkah & pengukuran
        waktu) lalu kosongkan tampilan agar langkah dapat diputar ulang."""
        if self.data is None:
            messagebox.showinfo("Belum ada graf", "Silakan buka file graf terlebih dahulu.",
                                parent=self.root)
            return False
        awal, akhir = self.var_awal.get(), self.var_akhir.get()
        nama = self.var_algoritma.get()

        self.var_status.set(f"Menjalankan {nama} dan mengukur waktu…")
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            hasil = jalankan(nama, self.data.graf, awal, akhir)
        finally:
            self.root.config(cursor="")

        self.hasil_aktif = hasil
        self.indeks_langkah = 0
        self.keadaan = KeadaanVisual(h=dict(hasil.heuristik))
        self.teks_ringkasan = ""
        for var in self.var_hasil.values():
            var.set("…")
        self.var_hasil["algoritma"].set(nama)
        self._bersihkan_log()
        self._log(f"=== {nama}: mencari jalur {awal} → {akhir} ===", "judul")
        return True

    def _perlu_disiapkan(self) -> bool:
        """True jika belum ada pencarian aktif atau pencarian sebelumnya selesai."""
        return (self.hasil_aktif is None
                or self.indeks_langkah >= len(self.hasil_aktif.langkah))

    def animasikan(self) -> None:
        """Mulai animasi otomatis, atau jeda jika animasi sedang berjalan."""
        if self.berjalan:
            self.jeda()
            return
        if self._perlu_disiapkan() and not self._siapkan_pencarian():
            return
        self.berjalan = True
        self.tombol_animasi.config(text="❚❚  Jeda  [Spasi]")
        self._detak()

    def _detak(self) -> None:
        """Satu 'detak' animasi: terapkan satu langkah lalu jadwalkan berikutnya."""
        if not self.berjalan:
            return
        if self._terapkan_langkah():
            self.jeda()  # langkah terakhir sudah diterapkan
            return
        self.id_after = self.root.after(int(self.var_jeda.get()), self._detak)

    def jeda(self) -> None:
        """Hentikan animasi otomatis (keadaan tetap dipertahankan)."""
        self.berjalan = False
        if self.id_after is not None:
            self.root.after_cancel(self.id_after)
            self.id_after = None
        self.tombol_animasi.config(text="▶  Animasikan  [Spasi]")

    def satu_langkah(self) -> None:
        """Maju tepat satu langkah pencarian."""
        self.jeda()
        if self._perlu_disiapkan() and not self._siapkan_pencarian():
            return
        self._terapkan_langkah()

    def hasil_langsung(self) -> None:
        """Selesaikan pencarian seketika tanpa animasi."""
        self.jeda()
        if self._perlu_disiapkan() and not self._siapkan_pencarian():
            return
        while not self._terapkan_langkah(gambar=False):
            pass
        self.gambar()

    def reset(self) -> None:
        """Kembalikan tampilan graf ke keadaan awal (tabel perbandingan tetap)."""
        self.jeda()
        self.hasil_aktif = None
        self.indeks_langkah = 0
        self.keadaan = KeadaanVisual()
        self.teks_ringkasan = ""
        for var in self.var_hasil.values():
            var.set("-")
        if self.data is not None:
            self.var_status.set(f"Siap. Pilih algoritma lalu jalankan pencarian "
                                f"{self.var_awal.get()} → {self.var_akhir.get()}.")
        self.gambar()

    def _query_berubah(self) -> None:
        """Simpul awal/akhir diganti: hasil lama tidak berlaku lagi."""
        self._kosongkan_perbandingan()
        self.reset()

    def _algoritma_berubah(self) -> None:
        """Algoritma diganti: hentikan animasi yang sedang berjalan."""
        self.reset()

    def _terapkan_langkah(self, gambar: bool = True) -> bool:
        """Terapkan satu :class:`Langkah` ke keadaan visual.

        Returns:
            True jika seluruh langkah sudah diterapkan (pencarian selesai).
        """
        hasil = self.hasil_aktif
        if hasil is None or self.indeks_langkah >= len(hasil.langkah):
            return True
        langkah = hasil.langkah[self.indeks_langkah]
        self.indeks_langkah += 1
        k = self.keadaan
        tag = ""

        if langkah.jenis == "mulai":
            k.frontier.add(langkah.simpul)
            k.g[langkah.simpul] = 0
            tag = "judul"
        elif langkah.jenis == "ambil":
            k.sekarang = langkah.simpul
            k.frontier.discard(langkah.simpul)
            k.final.add(langkah.simpul)
            k.sisi_aktif = None
            tag = "ambil"
        elif langkah.jenis == "periksa":
            k.sisi_aktif = (langkah.simpul, langkah.tetangga)  # type: ignore[assignment]
            k.sisi_aktif_berhasil = langkah.diperbarui
            if langkah.diperbarui and langkah.tetangga is not None:
                k.g[langkah.tetangga] = langkah.g
                k.induk[langkah.tetangga] = langkah.simpul
                k.frontier.add(langkah.tetangga)
            tag = "baik" if langkah.diperbarui else "buruk"
        elif langkah.jenis == "selesai":
            k.sekarang = None
            k.sisi_aktif = None
            k.jalur = list(hasil.jalur)
            tag = "hasil"
            self._tampilkan_hasil(hasil)

        self._log(langkah.keterangan, tag)
        selesai = self.indeks_langkah >= len(hasil.langkah)
        if not selesai:
            self.var_status.set(f"{hasil.algoritma}: langkah {self.indeks_langkah} dari "
                                f"{len(hasil.langkah)}")
        if gambar:
            self.gambar()
        return selesai

    def bandingkan(self) -> None:
        """Jalankan kedua algoritma pada query yang sama dan isi tabel."""
        self.jeda()
        if self.data is None:
            return
        awal, akhir = self.var_awal.get(), self.var_akhir.get()
        self.var_status.set("Menjalankan semua algoritma dan mengukur waktu…")
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            semua = [jalankan(nama, self.data.graf, awal, akhir, catat=False)
                     for nama in ALGORITMA]
        finally:
            self.root.config(cursor="")

        self.hasil_aktif = None
        self.keadaan = KeadaanVisual(jalur=list(semua[0].jalur))
        self._bersihkan_log()
        self._log(f"=== Perbandingan algoritma: {awal} → {akhir} ===", "judul")
        for hasil in semua:
            self._catat_perbandingan(hasil, log_kesimpulan=False)
            self._log(f"{hasil.algoritma:<9} jalur {format_jalur(hasil.jalur)} | bobot "
                      f"{format_angka(hasil.bobot)} | waktu {hasil.waktu_us:.2f} µs "
                      f"(rata-rata {hasil.jumlah_ulang}×) | diperluas "
                      f"{hasil.simpul_diperluas} | relaksasi {hasil.relaksasi}")

        pemisah = " | "
        self.var_hasil["algoritma"].set(pemisah.join(h.algoritma for h in semua))
        self.var_hasil["jalur"].set(format_jalur(semua[0].jalur))
        self.var_hasil["bobot"].set(pemisah.join(format_angka(h.bobot) for h in semua))
        self.var_hasil["waktu"].set(pemisah.join(f"{h.waktu_us:.2f} µs" for h in semua))
        self.var_hasil["diperluas"].set(pemisah.join(str(h.simpul_diperluas) for h in semua))
        self.var_hasil["relaksasi"].set(pemisah.join(str(h.relaksasi) for h in semua))
        self.teks_ringkasan = (f"Jalur terpendek: {format_jalur(semua[0].jalur)}    "
                               f"Bobot minimum: {format_angka(semua[0].bobot)}    " +
                               "   ".join(f"{h.algoritma}: {h.waktu_us:.2f} µs" for h in semua))
        self._log("Kesimpulan: " + self.var_kesimpulan.get(), "judul")
        self.var_status.set("Perbandingan selesai.")
        self.gambar()

    # ------------------------------------------------------------------ #
    # Hasil & perbandingan
    # ------------------------------------------------------------------ #
    def _tampilkan_hasil(self, hasil: HasilPencarian) -> None:
        """Tulis hasil akhir ke panel Hasil, tabel, dan ringkasan di canvas."""
        self.var_hasil["algoritma"].set(hasil.algoritma)
        self.var_hasil["jalur"].set(format_jalur(hasil.jalur))
        self.var_hasil["bobot"].set(format_angka(hasil.bobot))
        self.var_hasil["waktu"].set(f"{hasil.waktu_us:.2f} µs  (rata-rata "
                                    f"{hasil.jumlah_ulang}×)")
        self.var_hasil["diperluas"].set(f"{hasil.simpul_diperluas} dari "
                                        f"{len(self.data.simpul) if self.data else '?'} simpul")
        self.var_hasil["relaksasi"].set(str(hasil.relaksasi))
        self.teks_ringkasan = (f"{hasil.algoritma}    Jalur terpendek: "
                               f"{format_jalur(hasil.jalur)}    Bobot minimum: "
                               f"{format_angka(hasil.bobot)}    Waktu runtime: "
                               f"{hasil.waktu_us:.2f} µs")
        self.var_status.set(f"{hasil.algoritma} selesai.")
        self._catat_perbandingan(hasil)

    def _catat_perbandingan(self, hasil: HasilPencarian, log_kesimpulan: bool = True) -> None:
        """Isi kolom tabel perbandingan untuk satu algoritma."""
        self.hasil_per_algoritma[hasil.algoritma] = hasil
        nilai = {
            "jalur": format_jalur(hasil.jalur),
            "bobot": format_angka(hasil.bobot),
            "waktu": f"{hasil.waktu_us:.2f}",
            "diperluas": str(hasil.simpul_diperluas),
            "relaksasi": str(hasil.relaksasi),
        }
        for kunci, isi in nilai.items():
            self.tabel.set(kunci, hasil.algoritma, isi)
        self._perbarui_kesimpulan(log_kesimpulan)

    def _perbarui_kesimpulan(self, log_kesimpulan: bool = True) -> None:
        """Tulis kesimpulan singkat bila semua algoritma sudah dijalankan."""
        if len(self.hasil_per_algoritma) < len(ALGORITMA):
            belum = [n for n in ALGORITMA if n not in self.hasil_per_algoritma]
            self.var_kesimpulan.set("Belum dijalankan: " + ", ".join(belum) + ".")
            return
        d, a = self.hasil_per_algoritma["Dijkstra"], self.hasil_per_algoritma["A*"]
        sama = abs(d.bobot - a.bobot) < 1e-9 or d.bobot == a.bobot
        bagian = ["Bobot kedua algoritma sama (" + format_angka(d.bobot) + ") → hasil konsisten."
                  if sama else "PERHATIAN: bobot berbeda!"]
        bagian.append(f"A* memperluas {a.simpul_diperluas} simpul vs Dijkstra "
                      f"{d.simpul_diperluas} simpul.")
        cepat, lambat = (d, a) if d.waktu_us <= a.waktu_us else (a, d)
        rasio = lambat.waktu_us / cepat.waktu_us if cepat.waktu_us > 0 else 1.0
        bagian.append(f"{cepat.algoritma} {rasio:.2f}× lebih cepat dalam waktu eksekusi.")
        kesimpulan = " ".join(bagian)
        self.var_kesimpulan.set(kesimpulan)
        if log_kesimpulan:
            self._log("Kesimpulan: " + kesimpulan, "judul")

    def _kosongkan_perbandingan(self) -> None:
        """Hapus isi tabel perbandingan (mis. ketika query berubah)."""
        self.hasil_per_algoritma.clear()
        for kunci, label in self.baris_tabel:
            self.tabel.item(kunci, values=[label] + ["-"] * len(ALGORITMA))
        self.var_kesimpulan.set("Jalankan kedua algoritma untuk melihat perbandingan.")

    # ------------------------------------------------------------------ #
    # Log
    # ------------------------------------------------------------------ #
    def _log(self, teks: str, tag: str = "") -> None:
        """Tambahkan satu baris ke kotak log."""
        self.teks_log.configure(state="normal")
        self.teks_log.insert(tk.END, teks + "\n", tag)
        self.teks_log.see(tk.END)
        self.teks_log.configure(state="disabled")

    def _bersihkan_log(self) -> None:
        """Kosongkan kotak log."""
        self.teks_log.configure(state="normal")
        self.teks_log.delete("1.0", tk.END)
        self.teks_log.configure(state="disabled")

    # ------------------------------------------------------------------ #
    # Menggambar graf
    # ------------------------------------------------------------------ #
    def _ke_layar(self, simpul: str) -> Tuple[float, float]:
        """Ubah koordinat ternormalisasi [0, 1] menjadi piksel canvas."""
        lebar = max(self.canvas.winfo_width(), 2 * MARGIN + 10)
        tinggi = max(self.canvas.winfo_height(), 2 * MARGIN + RUANG_LEGENDA + 10)
        nx, ny = self.posisi[simpul]
        atas = MARGIN + RUANG_LEGENDA
        bawah = MARGIN + 18  # ruang untuk ringkasan hasil
        return (MARGIN + nx * (lebar - 2 * MARGIN),
                atas + ny * (tinggi - atas - bawah))

    def gambar(self) -> None:
        """Gambar ulang seluruh canvas sesuai keadaan visual saat ini."""
        c = self.canvas
        c.delete("all")
        if self.data is None or not self.posisi:
            c.create_text(c.winfo_width() / 2, c.winfo_height() / 2,
                          text="Belum ada graf. Klik \"Buka file graf…\".",
                          fill=WARNA["teks_bobot"], font=("Helvetica", 12))
            return

        k = self.keadaan
        sisi_jalur: Set[FrozenSet[str]] = {frozenset(p) for p in zip(k.jalur, k.jalur[1:])}
        koordinat = {v: self._ke_layar(v) for v in self.data.simpul}

        # 1) Sisi beserta bobotnya
        for u, v, w, berarah in self.sisi:
            self._gambar_sisi(koordinat[u], koordinat[v], u, v, w, berarah, sisi_jalur)

        # 2) Simpul beserta label nilai g/h
        for simpul in self.data.simpul:
            self._gambar_simpul(simpul, *koordinat[simpul])

        # 3) Legenda dan ringkasan hasil
        self._gambar_legenda()
        if self.teks_ringkasan:
            c.create_text(12, c.winfo_height() - 14, anchor="w", text=self.teks_ringkasan,
                          fill=WARNA["jalur"], font=("Helvetica", 11, "bold"))

    def _gambar_sisi(self, p: Tuple[float, float], q: Tuple[float, float], u: str, v: str,
                     bobot: float, berarah: bool, sisi_jalur: Set[FrozenSet[str]]) -> None:
        """Gambar satu sisi dengan warna sesuai perannya dalam pencarian."""
        k = self.keadaan
        pasangan = frozenset((u, v))
        warna, tebal, putus = WARNA["sisi"], 2, ()
        if pasangan in sisi_jalur:
            warna, tebal = WARNA["jalur"], 6
        elif k.sisi_aktif is not None and frozenset(k.sisi_aktif) == pasangan:
            if k.sisi_aktif_berhasil:
                warna, tebal = WARNA["periksa_baik"], 5
            else:
                warna, tebal, putus = WARNA["periksa_buruk"], 4, (6, 4)
        elif k.induk.get(v) == u or k.induk.get(u) == v:
            warna, tebal = WARNA["pohon"], 4

        if berarah:
            # Persingkat garis agar mata panah tidak tertutup lingkaran simpul
            dx, dy = q[0] - p[0], q[1] - p[1]
            panjang = max((dx * dx + dy * dy) ** 0.5, 1e-9)
            q = (q[0] - dx / panjang * JARI_SIMPUL, q[1] - dy / panjang * JARI_SIMPUL)
            self.canvas.create_line(*p, *q, fill=warna, width=tebal, dash=putus,
                                    arrow=tk.LAST, arrowshape=(12, 14, 5))
        else:
            self.canvas.create_line(*p, *q, fill=warna, width=tebal, dash=putus)

        # Label bobot di tengah sisi dengan latar agar mudah dibaca
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        teks = self.canvas.create_text(mx, my, text=format_angka(bobot), font=FONT_KECIL_TEBAL,
                                       fill=WARNA["jalur"] if warna == WARNA["jalur"]
                                       else WARNA["teks_bobot"])
        x1, y1, x2, y2 = self.canvas.bbox(teks)
        latar = self.canvas.create_rectangle(x1 - 3, y1 - 1, x2 + 3, y2 + 1,
                                             fill=WARNA["latar"], outline="")
        self.canvas.tag_lower(latar, teks)

    def _gambar_simpul(self, simpul: str, x: float, y: float) -> None:
        """Gambar satu simpul: warna isi menunjukkan statusnya dalam pencarian."""
        k = self.keadaan
        awal, akhir = self.var_awal.get(), self.var_akhir.get()

        # Status pencarian simpul (dipakai sebagai warna isi / cincin)
        if simpul == k.sekarang:
            status = WARNA["sekarang"]
        elif simpul in k.final:
            status = WARNA["final"]
        elif simpul in k.frontier:
            status = WARNA["frontier"]
        else:
            status = None

        if simpul in (awal, akhir):
            # Simpul awal/akhir selalu hijau/merah; status ditunjukkan lewat cincin
            isi = WARNA["awal"] if simpul == awal else WARNA["akhir"]
            garis, tebal, warna_teks = status or "#2d3748", 4 if status else 2, "#ffffff"
        else:
            isi = status or WARNA["simpul"]
            garis, tebal, warna_teks = WARNA["garis_simpul"], 2, WARNA["teks"]
        if simpul in k.jalur:
            garis, tebal = WARNA["jalur"], 4

        r = JARI_SIMPUL
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=isi, outline=garis,
                                width=tebal)
        self.canvas.create_text(x, y, text=simpul, fill=warna_teks, font=FONT_SIMPUL)

        # Penanda AWAL / TUJUAN di atas simpul
        if simpul == awal:
            self.canvas.create_text(x, y - r - 9, text="AWAL", fill=WARNA["awal"],
                                    font=FONT_KECIL_TEBAL)
        elif simpul == akhir:
            self.canvas.create_text(x, y - r - 9, text="TUJUAN", fill=WARNA["akhir"],
                                    font=FONT_KECIL_TEBAL)

        # Label nilai: Dijkstra → d=..., A* → g=... h=...
        label: List[str] = []
        if simpul in k.g:
            label.append(("g=" if k.h else "d=") + format_angka(k.g[simpul]))
        if k.h and simpul in k.h:
            label.append("h=" + format_angka(k.h[simpul]))
        if label:
            teks = self.canvas.create_text(x, y + r + 10, text="  ".join(label),
                                           font=FONT_KECIL, fill=WARNA["teks"])
            x1, y1, x2, y2 = self.canvas.bbox(teks)
            latar = self.canvas.create_rectangle(x1 - 3, y1, x2 + 3, y2, fill="#ffffff",
                                                 outline="#d5dbe3")
            self.canvas.tag_lower(latar, teks)

    def _gambar_legenda(self) -> None:
        """Legenda warna di bagian atas canvas (baris 1: simpul, baris 2: sisi)."""
        item = [(WARNA["awal"], "Awal"), (WARNA["akhir"], "Tujuan"),
                (WARNA["sekarang"], "Sedang diperluas"), (WARNA["frontier"], "Di antrian"),
                (WARNA["final"], "Sudah final")]
        x, y = 14, 16
        for warna, teks in item:
            self.canvas.create_oval(x, y - 7, x + 14, y + 7, fill=warna, outline="#5b6b7f")
            id_teks = self.canvas.create_text(x + 20, y, text=teks, anchor="w",
                                              font=FONT_KECIL, fill=WARNA["teks"])
            x = self.canvas.bbox(id_teks)[2] + 18
        # Keterangan sisi
        x, y = 14, 38
        sisi_legenda: List[Tuple[str, str, Tuple[int, ...]]] = [
            (WARNA["jalur"], "Jalur terpendek", ()),
            (WARNA["periksa_baik"], "Relaksasi berhasil", ()),
            (WARNA["periksa_buruk"], "Relaksasi tidak memperbarui", (6, 4)),
            (WARNA["pohon"], "Pohon induk sementara", ()),
        ]
        for warna_sisi, teks_sisi, putus_sisi in sisi_legenda:
            self.canvas.create_line(x, y, x + 22, y, fill=warna_sisi, width=4, dash=putus_sisi)
            id_teks = self.canvas.create_text(x + 28, y, text=teks_sisi, anchor="w",
                                              font=FONT_KECIL, fill=WARNA["teks"])
            x = self.canvas.bbox(id_teks)[2] + 18

    # ------------------------------------------------------------------ #
    # Menggeser simpul dengan mouse
    # ------------------------------------------------------------------ #
    def _simpul_di(self, x: float, y: float) -> Optional[str]:
        """Cari simpul yang berada di bawah kursor (jika ada)."""
        if self.data is None:
            return None
        for simpul in self.data.simpul:
            sx, sy = self._ke_layar(simpul)
            if (sx - x) ** 2 + (sy - y) ** 2 <= (JARI_SIMPUL + 4) ** 2:
                return simpul
        return None

    def _mulai_seret(self, event: tk.Event) -> None:
        self.simpul_diseret = self._simpul_di(event.x, event.y)

    def _seret(self, event: tk.Event) -> None:
        """Pindahkan simpul mengikuti kursor (koordinat disimpan ternormalisasi)."""
        if self.simpul_diseret is None:
            return
        lebar = max(self.canvas.winfo_width(), 2 * MARGIN + 10)
        tinggi = max(self.canvas.winfo_height(), 2 * MARGIN + RUANG_LEGENDA + 10)
        atas, bawah = MARGIN + RUANG_LEGENDA, MARGIN + 18
        nx = (event.x - MARGIN) / (lebar - 2 * MARGIN)
        ny = (event.y - atas) / (tinggi - atas - bawah)
        self.posisi[self.simpul_diseret] = (min(max(nx, 0.0), 1.0), min(max(ny, 0.0), 1.0))
        self.gambar()

    def _akhiri_seret(self, _event: tk.Event) -> None:
        self.simpul_diseret = None


def jalankan_gui(judul: str, data: Optional[DataGraf] = None) -> None:
    """Buat jendela tkinter dan jalankan aplikasi hingga ditutup."""
    _aktifkan_dpi_windows()
    root = tk.Tk()
    AplikasiShortestPath(root, judul, data)
    root.mainloop()


def _aktifkan_dpi_windows() -> None:
    """Di Windows, minta tampilan tajam pada layar HiDPI (diabaikan di OS lain)."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:
        pass
