"""
Project IRQ — IRQ Watchdog Bot
Entry point. Handler'ları register eder, polling başlatır.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# .env dosyasını yükle (proje kök dizini)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from handlers.commands import cmd_start, cmd_status, cmd_help, cmd_ping
from handlers.projects import (
    callback_phase_detail,
    callback_select_project,
    cmd_addproject,
    cmd_current,
    cmd_phase,
    cmd_projects,
    cmd_removeproject,
    cmd_roadmap,
)
from handlers.claude_cmds import callback_model_set, callback_run_confirm, cmd_cancel, cmd_model, cmd_run

# -------------------------------------------------------------
# Logging
# -------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------
# Handler kaydı
# -------------------------------------------------------------
def register_handlers(app: Application) -> None:
    # Faz 1
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("ping",   cmd_ping))

    # Faz 2A — Proje yönetimi
    app.add_handler(CommandHandler("projects",      cmd_projects))
    app.add_handler(CommandHandler("addproject",     cmd_addproject))
    app.add_handler(CommandHandler("removeproject",  cmd_removeproject))
    app.add_handler(CommandHandler("current",        cmd_current))
    app.add_handler(CallbackQueryHandler(callback_select_project, pattern=r"^sel_proj:"))

    # Faz 2B — ROADMAP & faz yönetimi
    app.add_handler(CommandHandler("roadmap",  cmd_roadmap))
    app.add_handler(CommandHandler("phase",    cmd_phase))
    app.add_handler(CallbackQueryHandler(callback_phase_detail, pattern=r"^phase_detail:"))

    # Faz 3A-3B — Claude Code entegrasyonu
    app.add_handler(CommandHandler("run",    cmd_run))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CallbackQueryHandler(callback_run_confirm, pattern=r"^run_confirm:"))

    # Faz 4 — Model kontrolü
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CallbackQueryHandler(callback_model_set, pattern=r"^model_set:"))


# -------------------------------------------------------------
# Main
# -------------------------------------------------------------
def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN env değişkeni bulunamadı!")
        raise SystemExit(1)

    logger.info("IRQ Watchdog Bot başlatılıyor...")

    app = Application.builder().token(token).build()
    register_handlers(app)

    async def error_handler(update, context):
        logger.error("Yakalanmamış hata: %s", context.error, exc_info=context.error)

    app.add_error_handler(error_handler)

    logger.info("Polling modunda çalışıyor...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
