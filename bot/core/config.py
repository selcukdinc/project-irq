"""
Project IRQ — Konfigürasyon
Env değişkenleri ve sabitler.
"""

import os
from pathlib import Path

# ~/.irq/ dizini
IRQ_HOME = Path.home() / ".irq"
PROJECTS_FILE = IRQ_HOME / "projects.json"
CONFIG_FILE = IRQ_HOME / "config.json"
LOGS_DIR = IRQ_HOME / "logs"

# Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# Claude Code
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
CLAUDE_TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "300"))

# Maliyet
COST_LIMIT_USD = float(os.environ.get("COST_LIMIT_USD", "5.0"))


def ensure_irq_dirs() -> None:
    """~/.irq/ ve alt dizinleri yoksa oluşturur."""
    IRQ_HOME.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
