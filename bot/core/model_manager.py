"""
Project IRQ — Model Manager
Faz 4: Claude Code model bilgisi ve değiştirme, ~/.irq/config.json'da saklanır.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .config import CONFIG_FILE, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Desteklenen modeller ve açıklamaları
SUPPORTED_MODELS: dict[str, str] = {
    "claude-sonnet-4-20250514":  "Sonnet 4 — Dengeli (hız + zeka)",
    "claude-opus-4-20250514":    "Opus 4 — En güçlü, daha yavaş",
    "claude-haiku-4-5-20251001": "Haiku 4.5 — En hızlı, ekonomik",
    "gemini-2.0-flash":          "Gemini Flash — Çok hızlı",
    "gemini-2.5-pro":            "Gemini 2.5 Pro — En gelişmiş",
}

# Model kısa etiketleri (inline buton callback için)
MODEL_ALIASES: dict[str, str] = {
    "sonnet4":  "claude-sonnet-4-20250514",
    "opus4":    "claude-opus-4-20250514",
    "haiku45":  "claude-haiku-4-5-20251001",
    "flash":    "gemini-2.0-flash",
    "gemini25": "gemini-2.5-pro",
}


def _load_config() -> dict:
    """~/.irq/config.json yükler, yoksa boş dict döner."""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("config.json okunamadı: %s", exc)
    return {}


def _save_config(data: dict) -> None:
    """~/.irq/config.json'a yazar."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.error("config.json yazılamadı: %s", exc)


def get_current_model() -> str:
    """Şu an aktif modeli döndürür. Önce config.json, sonra env, sonra varsayılan."""
    cfg = _load_config()
    return cfg.get("model", CLAUDE_MODEL)


def set_model(model_id: str) -> bool:
    """
    Modeli değiştir ve config.json'a kaydet.
    Geçerli model ID değilse False döner.
    """
    if model_id not in SUPPORTED_MODELS:
        logger.warning("Geçersiz model: %s", model_id)
        return False
    cfg = _load_config()
    cfg["model"] = model_id
    _save_config(cfg)
    logger.info("Model değiştirildi: %s", model_id)
    return True


def resolve_model(name: str) -> Optional[str]:
    """
    Hem tam model ID hem kısa etiket kabul eder.
    Geçersizse None döner.
    """
    if name in SUPPORTED_MODELS:
        return name
    return MODEL_ALIASES.get(name.lower())


def model_info_text(model_id: str) -> str:
    """Tek model için açıklama satırı."""
    return SUPPORTED_MODELS.get(model_id, "Bilinmeyen model")
