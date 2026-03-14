"""
Project IRQ — ROADMAP Parser
Markdown ROADMAP.md dosyasını parse eder, fazları ve adımları çıkarır.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Step:
    text: str
    done: bool


@dataclass
class Phase:
    number: int
    title: str
    label: str = ""         # görünen etiket: "Faz 1", "v1.7", "Teknik Borç" vb.
    description: str = ""
    steps: list[Step] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def completed(self) -> int:
        return sum(1 for s in self.steps if s.done)

    @property
    def progress(self) -> float:
        return (self.completed / self.total * 100) if self.total else 0.0

    @property
    def status_emoji(self) -> str:
        if self.completed == self.total and self.total > 0:
            return "✅"
        if self.completed > 0:
            return "🔨"
        return "⏳"


# Regex patterns — çoklu ROADMAP format desteği
_FAZ_RE  = re.compile(r"^##\s+Faz\s+(\d+)\s*[—–-]\s*(.+)$")  # ## Faz N — Başlık
_VER_RE  = re.compile(r"^##\s+(v[\d.]+)\s*[—–-]\s*(.+)$")     # ## vX.Y — Başlık
_H2_RE   = re.compile(r"^##\s+(.+)$")                           # ## Herhangi başlık (fallback)
_STEP_RE = re.compile(r"^-\s+\[([ xX])\]\s+(.+)$")
_DESC_RE = re.compile(r"^>\s*(?:Hedef:\s*)?(.+)$")


def parse_roadmap(roadmap_path: str | Path) -> list[Phase]:
    """ROADMAP.md dosyasını parse edip Phase listesi döndürür."""
    path = Path(roadmap_path)
    if not path.is_file():
        logger.warning("ROADMAP dosyası bulunamadı: %s", path)
        return []

    text = path.read_text(encoding="utf-8")
    phases: list[Phase] = []
    current: Phase | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # ## Faz N — Başlık  (orijinal IRQ formatı)
        m = _FAZ_RE.match(stripped)
        if m:
            current = Phase(
                number=len(phases) + 1,
                title=m.group(2).strip(),
                label=f"Faz {m.group(1)}",
            )
            phases.append(current)
            continue

        # ## vX.Y — Başlık  (semantik versiyon formatı)
        m = _VER_RE.match(stripped)
        if m:
            current = Phase(
                number=len(phases) + 1,
                title=m.group(2).strip(),
                label=m.group(1),
            )
            phases.append(current)
            continue

        # ## Genel başlık  (fallback — her türlü ## başlık)
        m = _H2_RE.match(stripped)
        if m:
            current = Phase(
                number=len(phases) + 1,
                title="",
                label=m.group(1).strip(),
            )
            phases.append(current)
            continue

        if current is None:
            continue

        # Faz açıklaması (> Hedef: ...)
        m = _DESC_RE.match(stripped)
        if m and not current.steps:
            desc = m.group(1).strip()
            if current.description:
                current.description += " " + desc
            else:
                current.description = desc
            continue

        # Adım (- [ ] veya - [x])
        m = _STEP_RE.match(stripped)
        if m:
            done = m.group(1).lower() == "x"
            current.steps.append(Step(text=m.group(2).strip(), done=done))

    return phases


def get_phase(roadmap_path: str | Path, phase_number: int) -> Phase | None:
    """Belirli bir fazı döndürür."""
    for phase in parse_roadmap(roadmap_path):
        if phase.number == phase_number:
            return phase
    return None


def overall_progress(phases: list[Phase]) -> tuple[int, int, float]:
    """Toplam ilerleme: (tamamlanan, toplam, yüzde)."""
    total = sum(p.total for p in phases)
    completed = sum(p.completed for p in phases)
    pct = (completed / total * 100) if total else 0.0
    return completed, total, pct


def format_roadmap_summary(phases: list[Phase]) -> str:
    """Tüm fazların kısa özetini Telegram mesajı olarak formatla."""
    if not phases:
        return "❌ ROADMAP parse edilemedi veya boş."

    completed, total, pct = overall_progress(phases)
    lines = [f"📊 *ROADMAP Durumu* — %{pct:.0f} tamamlandı ({completed}/{total})\n"]

    for p in phases:
        bar = _progress_bar(p.progress)
        header = f"{p.label} — {p.title}" if p.title else p.label
        lines.append(
            f"{p.status_emoji} *{header}*\n"
            f"   {bar} {p.completed}/{p.total}"
        )

    return "\n".join(lines)


def format_phase_detail(phase: Phase) -> str:
    """Tek bir fazın detaylı görünümünü Telegram mesajı olarak formatla."""
    bar = _progress_bar(phase.progress)
    header = f"{phase.label} — {phase.title}" if phase.title else phase.label
    lines = [
        f"{phase.status_emoji} *{header}*",
        f"{bar} %{phase.progress:.0f} ({phase.completed}/{phase.total})",
    ]

    if phase.description:
        lines.append(f"\n_{phase.description}_")

    lines.append("")
    for step in phase.steps:
        mark = "✅" if step.done else "⬜"
        lines.append(f"{mark} {step.text}")

    return "\n".join(lines)


def _progress_bar(pct: float, length: int = 10) -> str:
    """Yüzdeye göre metin tabanlı ilerleme çubuğu."""
    filled = round(pct / 100 * length)
    return "▓" * filled + "░" * (length - filled)
