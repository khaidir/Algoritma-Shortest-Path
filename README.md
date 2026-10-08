# Tugas 1 MMAI1001 Kecerdasan Artificial — Kelompok X

Pencarian jalur terpendek (*shortest path*) dengan **Dijkstra** dan **A\* (A-Star)**,
lengkap dengan GUI **tkinter** yang menganimasikan proses pencarian langkah demi langkah.

Program membaca graf dari `graf.txt`, lalu menampilkan **jalur terpendek**, **bobot minimum**,
dan **waktu running** untuk kedua algoritma, serta perbandingan keduanya.

> Ganti `X` dengan nomor kelompok: rename `MMAIKelompok1.py` → `MMAIKelompok<nomor>.py`
> dan ubah konstanta `NAMA_KELOMPOK` di baris awal file tersebut.

| No | Nama anggota | NPM | Kontribusi |
|----|--------------|-----|------------|
| 1  |              |     |            |
| 2  |              |     |            |
| 3  |              |     |            |

---

## 1. Struktur file

| File | Isi |
|------|-----|
| `MMAIKelompok1.py` | **File utama.** Membaca argumen, memuat graf, membuka GUI atau mode teks (`--cli`). |
| `pembaca_graf.py` | Membaca & memvalidasi `graf.txt` (aman: memakai `ast.literal_eval`, tidak mengeksekusi isi file). |
| `algoritma.py` | Implementasi Dijkstra, A\*, heuristik A\*, dan pengukuran waktu. |
| `tata_letak.py` | Menghitung posisi simpul secara otomatis (stress majorization) untuk digambar. |
| `visualisasi.py` | GUI tkinter: gambar graf, animasi pencarian, panel hasil, tabel perbandingan, log. |
| `graf.txt` | Input contoh **A** (V1 → V15). |

## 2. Kebutuhan

* **Python 3.8 atau lebih baru.** Tidak ada library eksternal — hanya pustaka standar
  (`tkinter`, `heapq`, `ast`, `time`, dll.), jadi tidak perlu `pip install` apa pun.
* `tkinter` sudah termasuk dalam installer Python resmi dari python.org (Windows & macOS).
  Jika memakai Python dari package manager dan muncul `No module named 'tkinter'`:
  * Ubuntu/Debian: `sudo apt install python3-tk`
  * macOS (Homebrew): `brew install python-tk`

  Bila tkinter tetap tidak tersedia, program otomatis beralih ke mode teks.

## 3. Cara menjalankan

Buka terminal di folder ini, lalu:

```bash
python MMAIKelompok1.py                  # GUI, membaca graf.txt di folder program
python MMAIKelompok1.py graf_lain.txt    # GUI dengan file graf lain
python MMAIKelompok1.py --cli            # mode teks saja (tanpa GUI)
python MMAIKelompok1.py --cli graf.txt   # mode teks dengan file tertentu
```

Di macOS/Linux gunakan `python3` bila perintah `python` tidak tersedia.
File graf juga bisa diganti langsung dari GUI lewat tombol **Buka file graf…**.

### Format `graf.txt`

```text
graph = {
'V1': {'V2': 120, 'V4': 200},
'V2': {'V1': 120, 'V3': 150, 'V5': 90},
...
}
V1 V15
```

* Setiap simpul dipetakan ke `{tetangga: bobot}`. Nama variabel (`graph`/`graf`) bebas.
* Baris terakhir: **simpul awal** dan **simpul akhir** dipisah spasi.
* Pembaca file toleran terhadap tanda kutip "pintar" (‘ ’) hasil salin dari PDF.
* Bobot harus angka **non-negatif** (syarat Dijkstra & A\*); jika tidak, muncul pesan kesalahan yang jelas.

## 4. Cara memakai GUI

| Kontrol | Fungsi |
|---------|--------|
| Simpul awal / akhir | Pilih simpul (bawaan dari baris terakhir `graf.txt`). |
| Algoritma | Dijkstra atau A\*. |
| Jeda animasi | Kecepatan animasi (50–1500 ms per langkah). |
| **▶ Animasikan** `Spasi` | Memutar animasi otomatis; tekan lagi untuk jeda. |
| **Satu langkah** `→` | Maju satu langkah (cocok untuk menjelaskan saat presentasi). |
| **Hasil langsung** `Enter` | Langsung tampilkan hasil akhir. |
| **Reset** `R` | Kembalikan tampilan graf ke awal. |
| **Bandingkan Dijkstra vs A\*** | Jalankan keduanya dan isi tabel perbandingan + kesimpulan. |

Simpul dapat **digeser dengan mouse** untuk merapikan tampilan.

Arti warna di canvas:

* Hijau = simpul awal, merah = simpul tujuan.
* Oranye = simpul yang **sedang diperluas**; kuning = simpul **di antrian prioritas**;
  biru muda = simpul yang jaraknya **sudah final**.
* Sisi hijau = relaksasi berhasil memperbarui jarak; merah putus-putus = tidak memperbarui;
  biru = pohon induk sementara; **ungu tebal = jalur terpendek**.
* Label di bawah simpul: `d=` jarak sementara (Dijkstra) atau `g=`/`h=` (A\*).

Panel kanan menampilkan jalur terpendek, bobot minimum, waktu runtime, jumlah simpul
diperluas, dan jumlah relaksasi sisi. Log di bawah mencatat setiap langkah algoritma.

## 5. Algoritma yang digunakan

### Alasan pemilihan

* Semua bobot pada graf soal **non-negatif** dan yang dicari adalah jalur dari **satu simpul
  awal ke satu simpul tujuan**. Untuk kasus ini Dijkstra adalah algoritma klasik yang optimal
  dan efisien.
* **A\*** adalah pengembangan Dijkstra yang memakai heuristik untuk mengarahkan pencarian ke
  tujuan — topik inti mata kuliah Kecerdasan Artificial (*informed search*). Membandingkan
  keduanya menunjukkan pengaruh heuristik terhadap jumlah simpul yang dieksplorasi.
* Bellman-Ford tidak diperlukan karena tidak ada bobot negatif (dan lebih lambat, O(V·E)).
  Floyd-Warshall menghitung semua pasangan simpul (O(V³)), berlebihan untuk satu pasangan.

### Dijkstra

Simpan jarak sementara `d[v]` (awal = 0, lainnya = ∞). Ulangi: ambil simpul dengan `d`
terkecil dari antrian prioritas (min-heap), tandai **final**, lalu **relaksasi** setiap
tetangganya: jika `d[u] + w(u,v) < d[v]`, perbarui `d[v]` dan catat `induk[v] = u`.
Berhenti ketika simpul tujuan diambil; jalur direkonstruksi dari pointer `induk`.

### A\* (A-Star)

Sama seperti Dijkstra, tetapi simpul diambil berdasarkan `f(n) = g(n) + h(n)`, dengan
`g(n)` = biaya dari awal dan `h(n)` = estimasi sisa biaya ke tujuan.

File graf **tidak memiliki koordinat**, sehingga jarak Euclidean tidak dapat dipakai.
Heuristik yang digunakan:

```text
h(n) = w_min × hop(n, tujuan)
```

* `hop(n, tujuan)` = jumlah sisi minimum dari `n` ke tujuan (BFS dari tujuan).
* `w_min` = bobot sisi terkecil di graf (pada input A: 70).

Heuristik ini **admissible** (tidak pernah melebihi biaya sebenarnya, karena setiap jalur
minimal melewati `hop(n)` sisi yang masing-masing berbobot ≥ `w_min`) dan **konsisten**
(`h(u) ≤ w(u,v) + h(v)`), sehingga A\* **dijamin menghasilkan jalur optimal** yang sama
dengan Dijkstra.

### Kompleksitas waktu dan ruang

V = jumlah simpul, E = jumlah sisi.

| Algoritma | Waktu | Ruang | Keterangan |
|-----------|-------|-------|------------|
| Dijkstra (binary heap) | O((V + E) log V) | O(V + E) | Heap dengan *lazy deletion* bisa berisi hingga O(E) entri. |
| A\* (heuristik konsisten) | O((V + E) log V) + O(V + E) | O(V + E) | O(V + E) tambahan untuk menghitung heuristik dengan BFS. Kasus terburuk sama dengan Dijkstra; dalam praktik simpul yang diperluas lebih sedikit. |

### Pengukuran waktu

Satu kali eksekusi pada graf kecil hanya beberapa mikrodetik sehingga rawan *noise*.
Karena itu setiap algoritma dijalankan berulang kali (±50 ms total, maks. 5000 kali)
**tanpa** pencatatan langkah animasi, lalu dirata-rata (`time.perf_counter`,
garbage collector dimatikan sementara seperti modul `timeit`). Satuan: mikrodetik (µs).
Nilai waktu berbeda di setiap komputer; yang dibandingkan adalah perbandingan relatifnya.

## 6. Hasil untuk input A (`graf.txt`: V1 → V15)

Keluaran `python MMAIKelompok1.py --cli`:

```text
=== Dijkstra ===
Jalur terpendek: V1→V2→V5→V9→V12→V15
Bobot minimum: 505
Waktu runtime: 8.82 µs (rata-rata dari 4768× eksekusi)
Simpul diperluas: 12, relaksasi sisi: 16

=== A* ===
Jalur terpendek: V1→V2→V5→V9→V12→V15
Bobot minimum: 505
Waktu runtime: 19.39 µs (rata-rata dari 2188× eksekusi)
Simpul diperluas: 7, relaksasi sisi: 9
```

| Metrik | Dijkstra | A\* |
|--------|----------|-----|
| Jalur terpendek | V1→V2→V5→V9→V12→V15 | V1→V2→V5→V9→V12→V15 |
| Bobot minimum | 505 | 505 |
| Simpul diperluas | 12 dari 15 | 7 dari 15 |
| Relaksasi sisi | 16 | 9 |
| Waktu (contoh, µs) | ±9 | ±19 |

**Analisis singkat**

* Kedua algoritma menghasilkan jalur dan bobot yang **sama (505)**, sesuai contoh output soal —
  membuktikan heuristik A\* admissible sehingga optimalitas terjaga.
* A\* hanya memperluas **7 simpul** (vs 12 pada Dijkstra) dan melakukan 9 relaksasi (vs 16):
  heuristik berhasil "mengarahkan" pencarian ke V15 sehingga simpul yang menjauhi tujuan
  (V3, V6, V7, V8, V10) tidak perlu diperluas, padahal Dijkstra memperluas semuanya.
  Urutan perluasan Dijkstra: V1, V2, V4, V5, V3, V9, V6, V7, V10, V12, V8, V15;
  A\*: V1, V2, V4, V5, V9, V12, V15.
* Namun pada graf sekecil ini A\* justru **lebih lambat** dalam waktu eksekusi, karena harus
  menghitung heuristik untuk semua simpul (BFS O(V + E)) dan mengelola tuple heap yang lebih
  besar. Penghematan simpul belum sebanding dengan biaya tambahan tersebut. Pada graf yang jauh
  lebih besar (ribuan simpul) atau jika heuristik lebih informatif (misalnya ada koordinat
  peta), keuntungan A\* akan semakin terasa.

## 7. Lanjutan untuk tim: input B dan C

Program sudah generik — untuk menguji input lain cukup buat file graf baru, tanpa mengubah kode.

1. Buat `graf_B.txt` (graf sama dengan A, baris terakhir `V1 V10`) dan `graf_C.txt`
   (graf huruf A–J, baris terakhir `B H`) sesuai soal.
2. Jalankan `python MMAIKelompok1.py graf_B.txt` (atau pakai tombol **Buka file graf…**),
   lalu tekan **Bandingkan Dijkstra vs A\***. Ulangi untuk `graf_C.txt`.
3. Cocokkan dengan contoh output di soal, ambil screenshot, dan lengkapi tabel berikut
   untuk laporan:

| Input | Jalur terpendek (soal) | Bobot (soal) | Waktu Dijkstra | Waktu A\* | Diperluas D / A\* |
|-------|------------------------|--------------|----------------|-----------|-------------------|
| A: V1 → V15 | V1→V2→V5→V9→V12→V15 | 505 | lihat bagian 6 | lihat bagian 6 | 12 / 7 |
| B: V1 → V10 | V1→V4→V6→V10 | 400 | … | … | … |
| C: B → H | B→C→F→E→H | 9 | … | … | … |

## 8. Ide untuk video presentasi (±10 menit)

1. Pengantar masalah & format `graf.txt` (anggota 1).
2. Penjelasan Dijkstra + demo animasi langkah demi langkah dengan tombol **→** (anggota 2).
3. Penjelasan A\* + heuristik `w_min × hop` + demo (anggota 3).
4. Perbandingan hasil input A, B, C dan analisis kompleksitas (anggota lain).
