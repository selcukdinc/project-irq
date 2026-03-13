"""
Project IRQ — Log Watcher & Loop Detector
Faz 6A-6B: Real-time log izleme ve loop tespiti.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# Loop tespit kriterleri
LOOP_REPEAT_THRESHOLD = 3           # Aynı hata satırı N+ kez tekrarlanırsa
LOOP_IDLE_SECONDS = 600             # 10 dakika boyunca yeni çıktı yoksa (git, build gibi sessiz işlemler için)
LOOP_MAX_BYTES = 10 * 1024 * 1024  # Çıktı 10MB'ı aşarsa

# Callback type: (reason: str) -> Awaitable[None]
WatchdogCallback = Callable[[str], Awaitable[None]]


class LoopDetector:
    """
    Claude Code çıktısını satır satır izler, loop kriterlerini kontrol eder.

    Kriterler:
      - Aynı hata mesajı LOOP_REPEAT_THRESHOLD+ kez tekrarlanırsa
      - LOOP_IDLE_SECONDS boyunca yeni çıktı gelmezse
      - Toplam çıktı LOOP_MAX_BYTES'ı aşarsa
    """

    def __init__(self) -> None:
        self._line_counts: Counter[str] = Counter()
        self._total_bytes: int = 0
        self._last_output_time: float = time.monotonic()
        self._loop_reason: Optional[str] = None

    @property
    def loop_detected(self) -> bool:
        return self._loop_reason is not None

    @property
    def loop_reason(self) -> Optional[str]:
        return self._loop_reason

    def feed(self, line: str) -> bool:
        """
        Yeni satır ekle. Loop tespit edildiyse True döner.
        Bir kez True döndükten sonra sonraki çağrılarda da True döner.
        """
        if self._loop_reason:
            return True

        self._total_bytes += len(line.encode("utf-8"))
        self._last_output_time = time.monotonic()

        # 10MB boyut sınırı
        if self._total_bytes >= LOOP_MAX_BYTES:
            self._loop_reason = (
                f"Çıktı boyutu 10MB sınırını aştı "
                f"({self._total_bytes // (1024 * 1024)}MB)"
            )
            return True

        # Tekrar eden hata satırı tespiti (error içeren satırları izle)
        stripped = line.strip()
        if stripped and any(
            kw in stripped.lower()
            for kw in ["error", "exception", "hata", "traceback", "warning"]
        ):
            self._line_counts[stripped] += 1
            if self._line_counts[stripped] >= LOOP_REPEAT_THRESHOLD:
                self._loop_reason = (
                    f"Aynı hata mesajı {self._line_counts[stripped]}x tekrarlandı:\n"
                    f"`{stripped[:200]}`"
                )
                return True

        return False

    def check_idle(self) -> bool:
        """Idle timeout kontrol et. Timeout aşıldıysa True döner."""
        if self._loop_reason:
            return True
        idle = time.monotonic() - self._last_output_time
        if idle >= LOOP_IDLE_SECONDS:
            self._loop_reason = (
                f"10 dakika boyunca çıktı gelmedi ({idle:.0f}s sessizlik)"
            )
            return True
        return False


class LogWatcher:
    """
    Runner process'ini async olarak izler.

    Kullanım:
      watcher = LogWatcher(log_path, watchdog_callback)
      watcher.start_idle_monitor_task()
      # Her çıktı satırı için:
      watcher.feed(line)
      # Bittikten sonra:
      watcher.stop_idle_monitor()
    """

    def __init__(
        self,
        log_path: Path,
        watchdog_callback: Optional[WatchdogCallback] = None,
    ) -> None:
        self._log_path = log_path
        self._callback = watchdog_callback
        self._detector = LoopDetector()
        self._lines: list[str] = []
        self._idle_task: Optional[asyncio.Task] = None
        self._notified = False

    def feed(self, line: str) -> None:
        """Runner'dan gelen yeni satırı işle (log + loop tespiti)."""
        self._lines.append(line)

        # Log dosyasına ekle
        try:
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(line if line.endswith("\n") else line + "\n")
        except Exception as exc:
            logger.warning("Log dosyasına yazılamadı: %s", exc)

        # Loop tespiti
        if not self._notified and self._detector.feed(line):
            self._trigger_notify()

    def start_idle_monitor_task(self) -> None:
        """Idle timeout izleme döngüsünü background task olarak başlat."""
        self._idle_task = asyncio.create_task(self._idle_monitor_loop())

    def stop_idle_monitor(self) -> None:
        """Idle monitor'ü durdur (runner tamamlandığında çağır)."""
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()

    async def _idle_monitor_loop(self, interval: float = 30.0) -> None:
        """30 saniyede bir idle timeout kontrol eder."""
        try:
            while True:
                await asyncio.sleep(interval)
                if not self._notified and self._detector.check_idle():
                    self._trigger_notify()
                    break
        except asyncio.CancelledError:
            pass

    def _trigger_notify(self) -> None:
        """Loop tespiti callback'ini tetikle (bir kez)."""
        if self._notified or not self._callback:
            return
        self._notified = True
        reason = self._detector.loop_reason or "Bilinmeyen loop"
        logger.warning("Loop tespit edildi: %s", reason[:100])
        asyncio.create_task(self._callback(reason))

    @property
    def output(self) -> str:
        """Tüm yakalanan çıktıyı döndürür."""
        return "".join(self._lines)

    @property
    def loop_detected(self) -> bool:
        return self._detector.loop_detected
