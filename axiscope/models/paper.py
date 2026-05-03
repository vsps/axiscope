"""ISO A series paper sizes."""

from dataclasses import dataclass

ISO_A_SIZES: dict[str, tuple[float, float]] = {
    "A0": (841, 1189),
    "A1": (594, 841),
    "A2": (420, 594),
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "A6": (105, 148),
    "A7": (74, 105),
    "A8": (52, 74),
    "A9": (37, 52),
    "A10": (26, 37),
}


@dataclass
class PaperSize:
    name: str
    width_mm: float
    height_mm: float
    landscape: bool = True

    @property
    def display_width(self) -> float:
        return self.height_mm if self.landscape else self.width_mm

    @property
    def display_height(self) -> float:
        return self.width_mm if self.landscape else self.height_mm

    @classmethod
    def from_name(cls, name: str) -> "PaperSize":
        w, h = ISO_A_SIZES[name]
        return cls(name=name, width_mm=w, height_mm=h, landscape=True)
