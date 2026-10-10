"""
test_input_C.py
===============

Pengujian otomatis untuk input C (graf huruf A-J, dari B ke H) pada Tugas 1
MMAI1001. Pengujian memastikan:

1. Dijkstra dan A* menghasilkan jalur dan bobot sesuai contoh output soal
   (B -> C -> F -> E -> H, bobot 9).
2. Bobot tersebut sama dengan hasil algoritma pembanding independen
   (Floyd-Warshall, all-pairs) dan dengan penelusuran semua jalur sederhana
   (brute force), serta jalur optimalnya tunggal.
3. Heuristik A* h(n) = w_min x hop(n, tujuan) pada input C admissible dan
   konsisten, sehingga optimalitas A* terjamin.

Algoritma pembanding hanya dipakai untuk pengujian, bukan bagian program utama.

Cara menjalankan (dari folder program):
    python test_input_C.py          # atau: python -m unittest test_input_C -v
"""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from algoritma import a_star, dijkstra, heuristik_hop
from pembaca_graf import baca_file_graf

FILE_C = Path(__file__).resolve().parent / "graf_C.txt"
JALUR_SOAL = ["B", "C", "F", "E", "H"]
BOBOT_SOAL = 9


def floyd_warshall(graf):
    """Jarak terpendek semua pasangan simpul (pembanding independen, O(V^3))."""
    simpul = list(graf)
    jarak = {u: {v: (0 if u == v else math.inf) for v in simpul} for u in simpul}
    for u, adj in graf.items():
        for v, w in adj.items():
            jarak[u][v] = min(jarak[u][v], w)
    for k in simpul:
        for i in simpul:
            for j in simpul:
                if jarak[i][k] + jarak[k][j] < jarak[i][j]:
                    jarak[i][j] = jarak[i][k] + jarak[k][j]
    return jarak


def semua_jalur_sederhana(graf, awal, akhir):
    """Daftar (bobot, jalur) untuk semua jalur tanpa simpul berulang."""
    hasil = []

    def telusur(u, jalur, bobot):
        if u == akhir:
            hasil.append((bobot, list(jalur)))
            return
        for v, w in graf[u].items():
            if v not in jalur:
                jalur.append(v)
                telusur(v, jalur, bobot + w)
                jalur.pop()

    telusur(awal, [awal], 0)
    return sorted(hasil)


class UjiInputC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = baca_file_graf(FILE_C)
        cls.graf = cls.data.graf

    def test_file_terbaca(self):
        self.assertEqual((self.data.awal, self.data.akhir), ("B", "H"))
        self.assertEqual(len(self.data.simpul), 10)
        self.assertEqual(self.data.jumlah_sisi, 15)

    def test_dijkstra_sesuai_soal(self):
        hasil = dijkstra(self.graf, "B", "H")
        self.assertEqual(hasil.jalur, JALUR_SOAL)
        self.assertEqual(hasil.bobot, BOBOT_SOAL)

    def test_astar_sesuai_soal(self):
        hasil = a_star(self.graf, "B", "H")
        self.assertEqual(hasil.jalur, JALUR_SOAL)
        self.assertEqual(hasil.bobot, BOBOT_SOAL)

    def test_cocok_dengan_floyd_warshall(self):
        jarak = floyd_warshall(self.graf)
        self.assertEqual(jarak["B"]["H"], BOBOT_SOAL)
        # Kedua algoritma juga benar untuk SEMUA pasangan simpul pada graf C.
        for u in self.graf:
            for v in self.graf:
                self.assertEqual(dijkstra(self.graf, u, v).bobot, jarak[u][v], (u, v))
                self.assertEqual(a_star(self.graf, u, v).bobot, jarak[u][v], (u, v))

    def test_jalur_optimal_tunggal(self):
        jalur = semua_jalur_sederhana(self.graf, "B", "H")
        terbaik = [j for b, j in jalur if b == BOBOT_SOAL]
        self.assertEqual(jalur[0][0], BOBOT_SOAL)
        self.assertEqual(terbaik, [JALUR_SOAL])

    def test_heuristik_admissible_dan_konsisten(self):
        h = heuristik_hop(self.graf, "H")
        jarak = floyd_warshall(self.graf)
        for n in self.graf:
            self.assertLessEqual(h[n], jarak[n]["H"], f"h({n}) melebihi biaya sebenarnya")
        for u, adj in self.graf.items():
            for v, w in adj.items():
                self.assertLessEqual(h[u], w + h[v], f"tidak konsisten pada sisi {u}-{v}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
