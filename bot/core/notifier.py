"""
Project IRQ — Notifier & History Tracker
Faz 5: Çalıştırma geçmişi kaydı ve tamamlanma mesaj formatlaması.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List

from .config import LOGS_DIR

logger = logging.getLogger(__name__)

HISTORY_FILE = LOGS_DIR.parent / "history.json"
MAX_HISTORY = 50  # Dosyada tutulacak maksimum kayıt sayısı


@dataclass
class RunRecord:
    """Tek bir Claude Code çalıştırma kaydı."""

    id: str               # timestamp tabanlı benzersiz ID
    project_name: str
    project_path: str
    prompt: str
    started_at: str       # ISO8601 (yerel saat)
    elapsed_seconds: float
    stdout: str
    stderr: str
    returncode: int
    cancelled: bool

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.cancelled

    @property
    def status_emoji(self) -> str:
        if self.cancelled:
            return "🚫"
        return "✅" if self.ok else "❌"

    @property
    def status_label(self) -> str:
        if self.cancelled:
            return "İptal Edildi"
        return "Tamamlandı" if self.ok else "Hata"


# ------------------------------------------------------------------
# Kayıt & Yükleme
# ------------------------------------------------------------------

def save_run(record: RunRecord) -> None:
    """
    Çalıştırma kaydını:
      1. ~/.irq/logs/<id>_<project>.log dosyasına yazar
      2. ~/.irq/history.json listesine ekler (en fazla MAX_HISTORY kayıt)
    """
    from .config import ensure_irq_dirs
    ensure_irq_dirs()

    # Ham log dosyası
    log_file = LOGS_DIR / f"{record.id}_{record.project_name}.log"
    try:
        log_file.write_text(
            f"ID: {record.id}\n"
            f"Project: {record.project_name}\n"
            f"Path: {record.project_path}\n"
            f"Started: {record.started_at}\n"
            f"Elapsed: {record.elapsed_seconds:.1f}s\n"
            f"Return code: {record.returncode}\n"
            f"Cancelled: {record.cancelled}\n"
            f"Prompt:\n{record.prompt}\n"
            f"--- STDOUT ---\n{record.stdout}\n"
            f"--- STDERR ---\n{record.stderr}\n",
            encoding="utf-8",
        )
        logger.debug("Log dosyasına yazıldı: %s", log_file)
    except Exception as exc:
        logger.warning("Log dosyasına yazılamadı: %s", exc)

    # history.json
    records = _load_raw()
    records.append(asdict(record))
    if len(records) > MAX_HISTORY:
        records = records[-MAX_HISTORY:]
    try:
        HISTORY_FILE.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("History güncellendi (%d kayıt)", len(records))
    except Exception as exc:
        logger.warning("History dosyasına yazılamadı: %s", exc)


def load_history(n: int = 10) -> List[RunRecord]:
    """Son n çalıştırma kaydını döndürür (en yeni önce)."""
    raw = _load_raw()
    return [RunRecord(**r) for r in reversed(raw[-n:])]


def _load_raw() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("History okunamadı: %s", exc)
        return []


# ------------------------------------------------------------------
# Mesaj Formatlaması
# ------------------------------------------------------------------

def format_run_summary(record: RunRecord) -> str:
    """Tamamlanan çalıştırma için Telegram mesaj metnini döndürür."""
    mins = int(record.elapsed_seconds // 60)
    secs = int(record.elapsed_seconds % 60)
    elapsed_str = f"{mins}dk {secs}s" if mins > 0 else f"{secs}s"

    # Çıktı önizlemesi (en fazla 400 karakter)
    raw_out = record.stdout.strip() or record.stderr.strip()
    if raw_out:
        output_preview = raw_out[:400]
        if len(raw_out) > 400:
            output_preview += "\n…_(kırpıldı)_"
    else:
        output_preview = "_(boş çıktı)_"

    prompt_preview = record.prompt[:80] + ("…" if len(record.prompt) > 80 else "")

    lines = [
        f"{record.status_emoji} *{record.status_label}* | ⏱️ {elapsed_str}",
        "",
        f"📂 Proje: {record.project_name}",
        f"💬 `{prompt_preview}`",
        "",
        "📝 Çıktı:",
        output_preview,
    ]
    return "\n".join(lines)


def format_history_list(records: List[RunRecord]) -> str:
    """Geçmiş listesi için Telegram mesaj metnini döndürür."""
    if not records:
        return "📭 Henüz tamamlanmış çalıştırma yok."

    lines = [f"📋 *Son {len(records)} Çalıştırma*\n"]
    for i, r in enumerate(records, 1):
        mins = int(r.elapsed_seconds // 60)
        secs = int(r.elapsed_seconds % 60)
        elapsed = f"{mins}dk {secs}s" if mins > 0 else f"{secs}s"
        prompt_short = r.prompt[:50] + ("…" if len(r.prompt) > 50 else "")
        lines.append(
            f"{i}\\. {r.status_emoji} `{r.started_at}` — {elapsed}\n"
            f"   📂 {r.project_name}\n"
            f"   💬 {prompt_short}"
        )
    return "\n\n".join(lines)


# ------------------------------------------------------------------
# Yardımcı — RunRecord oluşturma
# ------------------------------------------------------------------

def make_run_record(
    project_name: str,
    project_path: str,
    prompt: str,
    wall_start: float,   # time.time() değeri
    elapsed: float,
    stdout: str,
    stderr: str,
    returncode: int,
    cancelled: bool,
) -> RunRecord:
    """RunResult ve proje bilgisinden RunRecord oluşturur."""
    dt_str = datetime.fromtimestamp(wall_start).strftime("%Y-%m-%dT%H:%M:%S")
    rid = datetime.fromtimestamp(wall_start).strftime("%Y%m%d_%H%M%S")
    return RunRecord(
        id=rid,
        project_name=project_name,
        project_path=project_path,
        prompt=prompt,
        started_at=dt_str,
        elapsed_seconds=elapsed,
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        cancelled=cancelled,
    )
