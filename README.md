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
| `graf_C.txt` | Input contoh **C** (graf huruf A–J, B → H). |
| `test_input_C.py` | Pengujian otomatis input C (dibandingkan dengan Floyd-Warshall dan brute force). |
| `Docs/gambar_input_C/` | Tangkapan layar GUI untuk input C. |

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

## 7. Hasil untuk input C (`graf_C.txt`: B → H)

Input C memakai graf huruf A–J dari soal (10 simpul, 15 sisi tak berarah), disimpan sebagai
`graf_C.txt`. Program tidak diubah sama sekali; cukup jalankan dengan nama file tersebut.

```text
graf = {
'A': {'B': 4, 'C': 2},
'B': {'A': 4, 'C': 1, 'D': 5},
'C': {'A': 2, 'B': 1, 'E': 10, 'F': 3},
'D': {'B': 5, 'E': 2, 'G': 4},
'E': {'C': 10, 'D': 2, 'F': 2, 'H': 3},
'F': {'C': 3, 'E': 2, 'I': 11},
'G': {'D': 4, 'H': 1},
'H': {'E': 3, 'G': 1, 'I': 5, 'J': 7},
'I': {'F': 11, 'H': 5, 'J': 2},
'J': {'H': 7, 'I': 2}
}
B H
```

Keluaran `python MMAIKelompok1.py --cli graf_C.txt`:

```text
=== Dijkstra ===
Jalur terpendek: B→C→F→E→H
Bobot minimum: 9
Waktu runtime: 9.21 µs (rata-rata dari 1787× eksekusi)
Simpul diperluas: 8, relaksasi sisi: 12

=== A* ===
Jalur terpendek: B→C→F→E→H
Bobot minimum: 9
Waktu runtime: 24.89 µs (rata-rata dari 1767× eksekusi)
Simpul diperluas: 7, relaksasi sisi: 11
```

| Metrik | Dijkstra | A\* |
|--------|----------|-----|
| Jalur terpendek | B→C→F→E→H | B→C→F→E→H |
| Bobot minimum | 9 | 9 |
| Simpul diperluas | 8 dari 10 | 7 dari 10 |
| Relaksasi sisi | 12 | 11 |
| Waktu, mode teks `--cli` (µs) | 9,21 | 24,89 |
| Waktu, GUI per algoritma (µs) | 9,79 | 25,00 |
| Waktu, GUI tombol Bandingkan (µs) | 9,55 | 22,99 |

Ketiga pengukuran waktu di atas diambil pada MacBook Pro (macOS, Python dari Anaconda) dan
terlihat di tangkapan layar `C2`, `C4`, `C5`, dan `C6`. Sebagai pembanding, median 30
pengukuran di Linux x86_64 (Python 3.12) adalah 8,8 µs untuk Dijkstra dan 22,2 µs untuk A\*.
Angka mutlak berbeda di setiap komputer dan setiap kali dijalankan; yang konsisten adalah
Dijkstra sekitar 2,4–2,7× lebih cepat.

### Jejak Dijkstra

| Urutan | Simpul diambil | d (final) | Relaksasi yang memperbarui jarak |
|--------|----------------|-----------|----------------------------------|
| 1 | B | 0 | A = 4, C = 1, D = 5 |
| 2 | C | 1 | A: 4 → 3, E = 11, F = 4 |
| 3 | A | 3 | (tetangga sudah final) |
| 4 | F | 4 | E: 11 → 6, I = 15 |
| 5 | D | 5 | G = 9 (D→E = 7 tidak memperbarui 6) |
| 6 | E | 6 | H = 9 |
| 7 | G | 9 | (G→H = 10 tidak memperbarui 9) |
| 8 | H | 9 | tujuan diambil, berhenti |

### Jejak A\*

Heuristik `h(n) = w_min × hop(n, H)` dengan `w_min = 1`:
h(A) = 3, h(B) = 3, h(C) = 2, h(D) = 2, h(F) = 2, h(E) = 1, h(G) = 1, h(I) = 1, h(J) = 1, h(H) = 0.

| Urutan | Simpul diambil | g | h | f = g + h | Relaksasi yang memperbarui |
|--------|----------------|---|---|-----------|----------------------------|
| 1 | B | 0 | 3 | 3 | A = 4, C = 1, D = 5 |
| 2 | C | 1 | 2 | 3 | A: 4 → 3, E = 11, F = 4 |
| 3 | F | 4 | 2 | 6 | E: 11 → 6, I = 15 |
| 4 | A | 3 | 3 | 6 | (tetangga sudah final) |
| 5 | E | 6 | 1 | 7 | H = 9 |
| 6 | D | 5 | 2 | 7 | G = 9 |
| 7 | H | 9 | 0 | 9 | tujuan diambil, berhenti |

### Analisis

* **Hasil sesuai soal.** Kedua algoritma menemukan B→C→F→E→H dengan bobot 9. Hasil ini dicek
  ulang oleh `test_input_C.py` terhadap Floyd-Warshall (semua pasangan simpul) dan penelusuran
  semua 22 jalur sederhana dari B ke H: jalur berbobot 9 hanya satu, dan dua jalur terbaik
  berikutnya (B→D→E→H dan B→D→G→H) berbobot 10.
* **Contoh relaksasi yang jelas.** Sisi langsung C→E berbobot 10, tetapi jalan memutar C→F→E
  hanya 3 + 2 = 5. Kedua algoritma mula-mula mencatat E = 11 (lewat C), lalu memperbaruinya
  menjadi 6 saat F diperluas. Inilah alasan jalur terpendek melewati F, meskipun jumlah sisinya
  lebih banyak daripada B→D→E→H.
* **A\* hanya menghemat satu simpul (G), dan penghematan itu berasal dari aturan seri.**
  Dijkstra wajib memperluas semua simpul dengan d < 9, yaitu B, C, A, F, D, E. A\* wajib
  memperluas semua simpul dengan f < 9, dan ternyata himpunannya sama persis: B (3), C (3),
  F (6), A (6), E (7), D (7). Perbedaannya hanya pada G dan H yang sama-sama berjarak 9:
  Dijkstra memecah seri berdasarkan urutan masuk antrian sehingga G diambil sebelum H, sedangkan
  A\* memecah seri dengan h lebih kecil sehingga H diambil lebih dulu. Pada input A, A\*
  benar-benar memangkas pencarian (12 → 7 simpul).
* **Penyebabnya: heuristik kurang informatif pada input C.** Bobot sisi terkecil hanya 1,
  sehingga h(n) sama dengan jumlah hop. Perkiraan dari B hanya h(B) = 3, sepertiga dari biaya
  sebenarnya 9; rata-rata rasio h/h\* semua simpul 0,37. Pada input A, w_min = 70 sehingga
  h(V1) = 280 dari 505 (rasio 0,55; rata-rata 0,53). Makin dekat h ke biaya sebenarnya,
  makin banyak simpul yang bisa dilewati A\*.
* **Waktu.** Dijkstra sekitar 2,4–2,7× lebih cepat pada semua pengukuran. A\* menghitung heuristik dengan BFS untuk semua
  simpul dan menyimpan tuple heap yang lebih besar, sementara simpul yang dihemat hanya satu.
  Pada graf sekecil ini, biaya tambahan A\* tidak tertutup oleh penghematannya.

### Tangkapan layar GUI

| File | Isi | Sumber |
|------|-----|--------|
| `Docs/gambar_input_C/C0_tampilan_awal.png` | Graf C dimuat, B (hijau) dan H (merah) | Uji Linux |
| `Docs/gambar_input_C/C1_dijkstra_langkah9.png` | Dijkstra di tengah animasi (langkah 9) | Uji Linux |
| `Docs/gambar_input_C/C2_dijkstra_hasil.png` | Hasil akhir Dijkstra (9,79 µs) | MacBook Pro |
| `Docs/gambar_input_C/C3_astar_langkah9.png` | A\* di tengah animasi, label g dan h terlihat | Uji Linux |
| `Docs/gambar_input_C/C4_astar_hasil.png` | Hasil akhir A\* (25,00 µs) | MacBook Pro |
| `Docs/gambar_input_C/C5_perbandingan.png` | Tombol **Bandingkan Dijkstra vs A\*** | MacBook Pro |
| `Docs/gambar_input_C/C6_terminal_cli_dan_tes.png` | Mode teks `--cli` dan `test_input_C.py` (6 tes OK) | MacBook Pro |

Hasil yang sama di Linux dan macOS menunjukkan program berjalan di lebih dari satu komputer,
sesuai syarat soal.

### Pengujian otomatis

```bash
python test_input_C.py
```

Enam pengujian: file terbaca (10 simpul, 15 sisi, B → H), Dijkstra dan A\* sesuai contoh soal,
kedua algoritma cocok dengan Floyd-Warshall untuk semua 100 pasangan simpul, jalur optimal
tunggal, serta heuristik admissible dan konsisten pada graf C. Algoritma pembanding hanya
ada di file pengujian, bukan bagian program utama.

## 8. Lanjutan untuk tim: input B dan C

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
| C: B → H | B→C→F→E→H | 9 | 9,2–9,8 µs | 23,0–24,9 µs | 8 / 7 (lihat bagian 7) |

## 9. Ide untuk video presentasi (±10 menit)

1. Pengantar masalah & format `graf.txt` (anggota 1).
2. Penjelasan Dijkstra + demo animasi langkah demi langkah dengan tombol **→** (anggota 2).
3. Penjelasan A\* + heuristik `w_min × hop` + demo (anggota 3).
4. Perbandingan hasil input A, B, C dan analisis kompleksitas (anggota lain).
