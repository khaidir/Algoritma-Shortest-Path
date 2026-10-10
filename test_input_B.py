"""
test_input_B.py
===============

Pengujian otomatis untuk input B (graf V1-V15 yang sama dengan input A,
dari V1 ke V10) pada Tugas 1 MMAI1001. Pengujian memastikan:

1. Dijkstra dan A* menghasilkan jalur dan bobot sesuai contoh output soal
   (V1 -> V4 -> V6 -> V10, bobot 400).
2. Bobot tersebut sama dengan hasil algoritma pembanding independen
   (Floyd-Warshall, all-pairs) dan dengan penelusuran semua jalur sederhana
   (brute force), serta jalur optimalnya tunggal.
3. Heuristik A* h(n) = w_min x hop(n, tujuan) dengan tujuan V10 admissible
   dan konsisten, sehingga optimalitas A* terjamin.
4. A* benar-benar memangkas pencarian: cabang V3, V5, V7, V9 tidak diperluas.

Algoritma pembanding diambil dari test_input_C.py dan hanya dipakai untuk
pengujian, bukan bagian program utama.

Cara menjalankan (dari folder program):
    python test_input_B.py          # atau: python -m unittest test_input_B -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

from algoritma import a_star, dijkstra, heuristik_hop
from pembaca_graf import baca_file_graf
from test_input_C import floyd_warshall, semua_jalur_sederhana

FOLDER = Path(__file__).resolve().parent
FILE_A = FOLDER / "graf.txt"
FILE_B = FOLDER / "graf_B.txt"
JALUR_SOAL = ["V1", "V4", "V6", "V10"]
BOBOT_SOAL = 400


class UjiInputB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = baca_file_graf(FILE_B)
        cls.graf = cls.data.graf

    def test_file_terbaca(self):
        self.assertEqual((self.data.awal, self.data.akhir), ("V1", "V10"))
        self.assertEqual(len(self.data.simpul), 15)
        self.assertEqual(self.data.jumlah_sisi, 18)
        # Soal memakai graf yang sama dengan input A; hanya tujuannya berbeda.
        self.assertEqual(self.graf, baca_file_graf(FILE_A).graf)

    def test_dijkstra_sesuai_soal(self):
        hasil = dijkstra(self.graf, "V1", "V10")
        self.assertEqual(hasil.jalur, JALUR_SOAL)
        self.assertEqual(hasil.bobot, BOBOT_SOAL)

    def test_astar_sesuai_soal(self):
        hasil = a_star(self.graf, "V1", "V10")
        self.assertEqual(hasil.jalur, JALUR_SOAL)
        self.assertEqual(hasil.bobot, BOBOT_SOAL)

    def test_cocok_dengan_floyd_warshall(self):
        jarak = floyd_warshall(self.graf)
        self.assertEqual(jarak["V1"]["V10"], BOBOT_SOAL)
        # Kedua algoritma juga benar untuk SEMUA pasangan simpul pada graf ini.
        for u in self.graf:
            for v in self.graf:
                self.assertEqual(dijkstra(self.graf, u, v).bobot, jarak[u][v], (u, v))
                self.assertEqual(a_star(self.graf, u, v).bobot, jarak[u][v], (u, v))

    def test_jalur_optimal_tunggal(self):
        jalur = semua_jalur_sederhana(self.graf, "V1", "V10")
        terbaik = [j for b, j in jalur if b == BOBOT_SOAL]
        self.assertEqual(jalur[0][0], BOBOT_SOAL)
        self.assertEqual(terbaik, [JALUR_SOAL])

    def test_heuristik_admissible_dan_konsisten(self):
        h = heuristik_hop(self.graf, "V10")
        jarak = floyd_warshall(self.graf)
        for n in self.graf:
            self.assertLessEqual(h[n], jarak[n]["V10"], f"h({n}) melebihi biaya sebenarnya")
        for u, adj in self.graf.items():
            for v, w in adj.items():
                self.assertLessEqual(h[u], w + h[v], f"tidak konsisten pada sisi {u}-{v}")

    def test_astar_memangkas_cabang(self):
        diperluas_dijkstra = [l.simpul for l in dijkstra(self.graf, "V1", "V10", catat=True).langkah
                              if l.jenis == "ambil"]
        diperluas_astar = [l.simpul for l in a_star(self.graf, "V1", "V10", catat=True).langkah
                           if l.jenis == "ambil"]
        self.assertEqual(diperluas_dijkstra, ["V1", "V2", "V4", "V5", "V3", "V9", "V6", "V7", "V10"])
        self.assertEqual(diperluas_astar, ["V1", "V2", "V4", "V6", "V10"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
