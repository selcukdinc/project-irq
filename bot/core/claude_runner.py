"""
Project IRQ — Claude Code CLI Runner
Faz 3A: Claude Code CLI'ı async subprocess ile çalıştırır.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from .config import CLAUDE_TIMEOUT
from .model_manager import get_current_model

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Claude Code CLI çalıştırma sonucu."""
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    elapsed_seconds: float = 0.0
    cancelled: bool = False

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
    """

    def __init__(self) -> None:
        self._process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def run(
        self,
        prompt: str,
        project_path: str,
        model: str | None = None,
        timeout: int | None = None,
    ) -> RunResult:
        """
        Claude Code CLI'ı çalıştır ve sonucu döndür.

        Args:
            prompt: Claude'a gönderilecek prompt
            project_path: Proje dizini (--add-dir)
            model: Kullanılacak model (varsayılan: config'den)
            timeout: Timeout (saniye, varsayılan: config'den)
        """
        if self.is_running:
            return RunResult(
                stderr="⚠️ Zaten çalışan bir komut var. Önce /cancel ile iptal edin.",
                returncode=1,
            )

        model = model or get_current_model()
        timeout = timeout or CLAUDE_TIMEOUT

        cmd = [
            "claude",
            "-p", prompt,
            "--model", model,
            "--add-dir", project_path,
        ]

        logger.info("Claude CLI çalıştırılıyor: model=%s, path=%s", model, project_path)
        logger.debug("Prompt: %s", prompt[:200])

        start = time.monotonic()
        result = RunResult()

        async with self._lock:
            try:
                self._process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=project_path,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        self._process.communicate(),
                        timeout=timeout,
                    )
                    result.stdout = stdout_bytes.decode("utf-8", errors="replace")
                    result.stderr = stderr_bytes.decode("utf-8", errors="replace")
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
                result.elapsed_seconds = time.monotonic() - start

        status = "OK" if result.ok else "FAIL"
        logger.info(
            "Claude CLI tamamlandı: %s (%.1fs, rc=%d)",
            status, result.elapsed_seconds, result.returncode,
        )
        return result

    async def cancel(self) -> bool:
        """Çalışan process'i iptal et. İptal edildiyse True döner."""
        proc = self._process
        if proc is None or proc.returncode is not None:
            return False

        logger.info("Claude CLI iptal ediliyor (PID: %s)", proc.pid)
        try:
            proc.terminate()
            # 3 saniye bekle, kapanmazsa kill
            try:
                await asyncio.wait_for(proc.wait(), timeout=3)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass

        return True


# Singleton instance — tüm handler'lar bunu kullanır
runner = ClaudeRunner()
