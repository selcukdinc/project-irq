"""
Project IRQ — Claude Code CLI Runner
Faz 3A: Claude Code CLI'ı async subprocess ile çalıştırır.
Faz 6A: Streaming line-by-line output + pause/resume desteği.
Faz 7: Maliyet takibi ve limit kontrolü.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .config import CLAUDE_TIMEOUT
from .model_manager import get_current_model
from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# Line callback type: her çıktı satırı için çağrılır
LineCallback = Callable[[str], None]


@dataclass
class RunResult:
    """Claude Code CLI çalıştırma sonucu."""
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    elapsed_seconds: float = 0.0
    cancelled: bool = False
    wall_start: float = 0.0   # time.time() — Faz 5 history için

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.cancelled

    @property
    def output(self) -> str:
        """Kullanıcıya gösterilecek çıktı."""
        return self.stdout.strip() if self.ok else (self.stderr.strip() or self.stdout.strip())


class ClaudeRunner:
    """
    Claude Code CLI wrapper.
    Aynı anda sadece 1 process çalışır (eşzamanlılık koruması).
    Faz 6: pause/resume (SIGSTOP/SIGCONT) ve streaming output desteği.
    """

    def __init__(self) -> None:
        self._process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()
        self._paused = False

        # Faz 7: Maliyet takibi
        config_dir = Path.home() / ".irq"
        config_dir.mkdir(exist_ok=True)
        self._cost_tracker = CostTracker(config_dir)

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    @property
    def is_paused(self) -> bool:
        return self._paused

    async def run(
        self,
        prompt: str,
        project_path: str,
        model: str | None = None,
        timeout: int | None = None,
        line_callback: LineCallback | None = None,
    ) -> RunResult:
        """
        Claude Code CLI'ı çalıştır ve sonucu döndür.

        Args:
            prompt: Claude'a gönderilecek prompt
            project_path: Proje dizini (--add-dir)
            model: Kullanılacak model (varsayılan: config'den)
            timeout: Timeout (saniye, varsayılan: config'den)
            line_callback: Her çıktı satırı için çağrılacak callable (Faz 6A)
        """
        if self.is_running:
            return RunResult(
                stderr="⚠️ Zaten çalışan bir komut var. Önce /cancel ile iptal edin.",
                returncode=1,
            )

        model = model or get_current_model()
        timeout = timeout or CLAUDE_TIMEOUT
        self._paused = False

        cmd = [
            "claude",
            "-p", prompt,
            "--model", model,
            "--add-dir", project_path,
            "--verbose",  # Faz 7: Maliyet bilgisi için verbose output
        ]

        logger.info("Claude CLI çalıştırılıyor: model=%s, path=%s", model, project_path)
        logger.debug("Prompt: %s", prompt[:200])

        start = time.monotonic()
        result = RunResult(wall_start=time.time())

        async with self._lock:
            try:
                self._process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=project_path,
                )

                try:
                    stdout_buf, stderr_buf = await asyncio.wait_for(
                        self._read_streams(line_callback),
                        timeout=timeout,
                    )
                    await self._process.wait()
                    result.stdout = stdout_buf
                    result.stderr = stderr_buf
                    result.returncode = self._process.returncode or 0
                except asyncio.TimeoutError:
                    logger.warning("Claude CLI timeout (%ds)", timeout)
                    self._process.kill()
                    await self._process.wait()
                    result.stderr = f"⏱️ Timeout: {timeout} saniye aşıldı."
                    result.returncode = -1

            except FileNotFoundError:
                result.stderr = "❌ 'claude' CLI bulunamadı. Claude Code kurulu mu?"
                result.returncode = 127
                logger.error("claude CLI bulunamadı")
            except Exception as exc:
                result.stderr = f"❌ Beklenmeyen hata: {exc}"
                result.returncode = 1
                logger.error("Claude CLI hatası: %s", exc, exc_info=True)
            finally:
                self._process = None
                self._paused = False
                result.elapsed_seconds = time.monotonic() - start

        status = "OK" if result.ok else "FAIL"
        logger.info(
            "Claude CLI tamamlandı: %s (%.1fs, rc=%d)",
            status, result.elapsed_seconds, result.returncode,
        )

        # Faz 7: Maliyet takibi
        try:
            # Proje adını path'den çıkar
            project_name = Path(project_path).name

            # Sadece başarılı çalıştırmaları kaydet (maliyet oluşanları)
            if result.ok or (result.returncode != 127):  # CLI bulunamadı hatası değilse
                cost_entry = self._cost_tracker.record_usage(
                    project=project_name,
                    prompt=prompt,
                    model=model,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    duration_seconds=result.elapsed_seconds
                )

                logger.debug(f"Maliyet kaydedildi: ${cost_entry.cost_usd:.4f}")

                # Günlük limit kontrolü
                if self._cost_tracker.check_daily_limit_exceeded():
                    logger.warning("⚠️ Günlük maliyet limiti aşıldı!")

        except Exception as exc:
            logger.error("Maliyet takip hatası: %s", exc)

        return result

    async def _read_streams(
        self,
        line_callback: LineCallback | None,
    ) -> tuple[str, str]:
        """
        stdout ve stderr'ı paralel oku.
        line_callback varsa her stdout satırı için çağırır.
        """
        proc = self._process
        assert proc is not None

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        async def read_stdout() -> None:
            assert proc.stdout is not None
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace")
                stdout_lines.append(line)
                if line_callback:
                    try:
                        line_callback(line)
                    except Exception as exc:
                        logger.debug("line_callback hatası: %s", exc)

        async def read_stderr() -> None:
            assert proc.stderr is not None
            while True:
                raw = await proc.stderr.readline()
                if not raw:
                    break
                stderr_lines.append(raw.decode("utf-8", errors="replace"))

        await asyncio.gather(read_stdout(), read_stderr())
        return "".join(stdout_lines), "".join(stderr_lines)

    async def cancel(self) -> bool:
        """Çalışan process'i iptal et. İptal edildiyse True döner."""
        proc = self._process
        if proc is None or proc.returncode is not None:
            return False

        logger.info("Claude CLI iptal ediliyor (PID: %s)", proc.pid)

        # Önce SIGCONT gönder (pause edilmişse resume et, yoksa kill bloklanır)
        if self._paused:
            try:
                proc.send_signal(signal.SIGCONT)
            except ProcessLookupError:
                pass
            self._paused = False

        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=3)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass

        return True

    async def pause(self) -> bool:
        """
        Çalışan process'i durdur (SIGSTOP).
        Faz 6C: /pause komutu için.
        """
        proc = self._process
        if proc is None or proc.returncode is not None:
            return False
        if self._paused:
            return False  # Zaten duraklatılmış

        try:
            proc.send_signal(signal.SIGSTOP)
            self._paused = True
            logger.info("Claude CLI duraklatıldı (PID: %s)", proc.pid)
            return True
        except (ProcessLookupError, OSError) as exc:
            logger.warning("SIGSTOP gönderilemedi: %s", exc)
            return False

    async def resume(self) -> bool:
        """
        Duraklatılmış process'i devam ettir (SIGCONT).
        Faz 6C: /resume komutu için.
        """
        proc = self._process
        if proc is None or proc.returncode is not None:
            return False
        if not self._paused:
            return False  # Zaten çalışıyor

        try:
            proc.send_signal(signal.SIGCONT)
            self._paused = False
            logger.info("Claude CLI devam ettiriliyor (PID: %s)", proc.pid)
            return True
        except (ProcessLookupError, OSError) as exc:
            logger.warning("SIGCONT gönderilemedi: %s", exc)
            return False


# Singleton instance — tüm handler'lar bunu kullanır
runner = ClaudeRunner()
