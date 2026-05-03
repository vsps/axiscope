"""Abstract base class for drawing tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from PySide6.QtGui import QPainterPath

from axiscope.models.paper import PaperSize


@dataclass
class ControlDef:
    """Describes one user-facing parameter for a drawing tool."""

    key: str
    label: str
    kind: str = "float"  # "float" | "int" | "choice"
    default: float = 0.0
    minimum: float = 0.0
    maximum: float = 100.0
    step: float = 1.0
    decimals: int = 1
    suffix: str = ""
    choices: list[str] = field(default_factory=list)  # for "choice" kind

    def clamp(self, value: float) -> float:
        return max(self.minimum, min(self.maximum, value))


class BaseTool(ABC):
    """A drawing tool plugin.

    Subclass this, set ``name`` and ``controls``, and implement
    ``generate_paths``.  The UI will auto-build a controls panel from
    the ``controls`` list.
    """

    name: str = ""

    @property
    @abstractmethod
    def controls(self) -> list[ControlDef]:
        """Return the parameter definitions for this tool (master layer)."""
        ...

    @property
    def modulator_controls(self) -> list[ControlDef]:
        """Controls for additional layers.  Defaults to ``controls``.
        Override to show a subset (e.g. omit duration/samples)."""
        return self.controls

    @abstractmethod
    def generate_paths(
        self,
        params: dict[str, float],
        paper: PaperSize,
        stroke_mm: float,
    ) -> list[QPainterPath]:
        """Generate drawing paths for the given parameters and paper size.

        *params* keys match the ``ControlDef.key`` values declared in
        ``controls``.  Return a list of ``QPainterPath`` objects in
        **millimetre** coordinates (centred at origin 0,0).
        """
        ...

    def get_defaults(self) -> dict[str, float]:
        """Return {key: default} for every control."""
        return {c.key: c.default for c in self.controls}
