#!/usr/bin/env python3
"""
Задача 17: тетраэдры из файла.
Читает путь к файлу, отбрасывает вырожденные (V ≈ 0),
находит тетраэдр с наиболее удалённым от (0,0,0) центроидом,
печатает cos двугранного угла между гранями (P1,P2,P3) и (P1,P2,P4)
и средний объём всех невырожденных тетраэдров.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

EPS = 1e-9


@dataclass
class Vec3:
    x: float
    y: float
    z: float

    def __add__(self, o: Vec3) -> Vec3:
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: Vec3) -> Vec3:
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __truediv__(self, s: float) -> Vec3:
        return Vec3(self.x / s, self.y / s, self.z / s)

    def dot(self, o: Vec3) -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: Vec3) -> Vec3:
        return Vec3(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )

    def norm(self) -> float:
        return math.sqrt(self.dot(self))


def tetra_volume(p1: Vec3, p2: Vec3, p3: Vec3, p4: Vec3) -> float:
    """Объём |det(P2-P1, P3-P1, P4-P1)| / 6."""
    a, b, c = p2 - p1, p3 - p1, p4 - p1
    return abs(a.dot(b.cross(c))) / 6.0


def centroid(pts: list[Vec3]) -> Vec3:
    s = pts[0] + pts[1] + pts[2] + pts[3]
    return s / 4.0


def dihedral_cos(p1: Vec3, p2: Vec3, p3: Vec3, p4: Vec3) -> float:
    """
    Cos угла между нормалями к граням (P1,P2,P3) и (P1,P2,P4).
    n1 = (P2-P1) × (P3-P1), n2 = (P2-P1) × (P4-P1).
    """
    e = p2 - p1
    n1 = e.cross(p3 - p1)
    n2 = e.cross(p4 - p1)
    d = n1.norm() * n2.norm()
    if d < EPS:
        raise ValueError("cannot compute dihedral: degenerate face normal")
    return n1.dot(n2) / d


def main() -> None:
    path = input().strip() if len(sys.argv) < 2 else sys.argv[1]

    best = None  # (dist2, pts, volume)
    volumes: list[float] = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            nums = list(map(float, line.split()))
            if len(nums) != 12:
                continue
            pts = [Vec3(*nums[i : i + 3]) for i in range(0, 12, 3)]
            vol = tetra_volume(*pts)
            if vol <= EPS:
                continue
            volumes.append(vol)
            c = centroid(pts)
            dist2 = c.dot(c)
            if best is None or dist2 > best[0]:
                best = (dist2, pts, vol)

    if best is None:
        print("no non-degenerate tetrahedra")
        return

    cos_a = dihedral_cos(*best[1])
    avg_vol = sum(volumes) / len(volumes)
    print(cos_a)
    print(avg_vol)


if __name__ == "__main__":
    main()
