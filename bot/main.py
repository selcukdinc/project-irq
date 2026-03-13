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
    callback_where_back,
    callback_where_phase,
    cmd_addproject,
    cmd_current,
    cmd_overview,
    cmd_phase,
    cmd_projects,
    cmd_removeproject,
    cmd_roadmap,
    cmd_where,
)
from handlers.claude_cmds import (
    callback_menu,
    callback_model_set,
    callback_run_confirm,
    cmd_cancel,
    cmd_history,
    cmd_menu,
    cmd_model,
    cmd_run,
)
from handlers.watchdog import callback_watchdog, cmd_kill, cmd_pause, cmd_resume

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

    # Faz 2D — Bağlam komutları
    app.add_handler(CommandHandler("where",    cmd_where))
    app.add_handler(CommandHandler("overview", cmd_overview))
    app.add_handler(CallbackQueryHandler(callback_where_phase, pattern=r"^where_phase:"))
    app.add_handler(CallbackQueryHandler(callback_where_back,  pattern=r"^where_back$"))
    app.add_handler(CallbackQueryHandler(callback_select_project, pattern=r"^where_projects$"))

    # Faz 3A-3B — Claude Code entegrasyonu
    app.add_handler(CommandHandler("run",    cmd_run))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CallbackQueryHandler(callback_run_confirm, pattern=r"^run_confirm:"))

    # Faz 5C — Çalıştırma geçmişi
    app.add_handler(CommandHandler("history", cmd_history))

    # Faz 4 — Model kontrolü
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CallbackQueryHandler(callback_model_set, pattern=r"^model_set:"))

    # Faz 6B-6C — Watchdog: loop bildirimi + süreç kontrolü
    app.add_handler(CommandHandler("pause",  cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("kill",   cmd_kill))
    app.add_handler(CallbackQueryHandler(callback_watchdog, pattern=r"^watchdog:"))

    # Faz 6D — /menu Command Center
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CallbackQueryHandler(callback_menu, pattern=r"^menu_"))


# -------------------------------------------------------------
# Main
# -------------------------------------------------------------
def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN env değişkeni bulunamadı!")
        raise SystemExit(1)

    logger.info("IRQ Watchdog Bot başlatılıyor...")

    app = Application.builder().token(token).concurrent_updates(True).build()
    register_handlers(app)

    async def error_handler(update, context):
        logger.error("Yakalanmamış hata: %s", context.error, exc_info=context.error)

    app.add_error_handler(error_handler)

    logger.info("Polling modunda çalışıyor...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
