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

from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from handlers.commands import cmd_start, cmd_status, cmd_help, cmd_ping, cmd_restart
from handlers.projects import (
    callback_phase_detail,
    callback_rdmap_faz,
    callback_rdmap_page,
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
    callback_menu_model_set,
    callback_model_set,
    callback_run_confirm,
    cmd_cancel,
    cmd_history,
    cmd_menu,
    cmd_model,
    cmd_run,
)
from handlers.watchdog import callback_watchdog, cmd_kill, cmd_pause, cmd_resume
from handlers.cost_cmds import (
    callback_budget_set,
    callback_cost_view,
    cmd_budget,
    cmd_cost,
)

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
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("ping",    cmd_ping))
    app.add_handler(CommandHandler("restart", cmd_restart))

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
    app.add_handler(CallbackQueryHandler(callback_rdmap_faz,    pattern=r"^rdmap_faz:"))
    app.add_handler(CallbackQueryHandler(callback_rdmap_page,   pattern=r"^rdmap_page:"))

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
    app.add_handler(CallbackQueryHandler(callback_menu,           pattern=r"^menu_"))
    app.add_handler(CallbackQueryHandler(callback_menu_model_set, pattern=r"^mmdl:"))

    # Faz 7 — Maliyet kontrolü
    app.add_handler(CommandHandler("budget", cmd_budget))
    app.add_handler(CommandHandler("cost", cmd_cost))
    app.add_handler(CallbackQueryHandler(callback_budget_set, pattern=r"^budget_set:"))
    app.add_handler(CallbackQueryHandler(callback_cost_view, pattern=r"^cost_view:"))


# -------------------------------------------------------------
# Main
# -------------------------------------------------------------
_BOT_COMMANDS = [
    BotCommand("start",         "Bot başlat, Chat ID öğren"),
    BotCommand("status",        "Sistem durumu"),
    BotCommand("ping",          "Bot canlı mı?"),
    BotCommand("restart",       "Botu yeniden başlat"),
    BotCommand("help",          "Komut listesi"),
    BotCommand("menu",          "Ana kontrol paneli"),
    BotCommand("where",         "Hızlı bağlam: proje + faz + sıradaki adım"),
    BotCommand("overview",      "Tüm projelerin özet durumu"),
    BotCommand("run",           "Claude Code'a prompt gönder"),
    BotCommand("cancel",        "Çalışan komutu iptal et"),
    BotCommand("history",       "Son çalıştırmaların listesi"),
    BotCommand("roadmap",       "Aktif projenin faz durumu"),
    BotCommand("phase",         "Belirli bir fazın detayı"),
    BotCommand("projects",      "Kayıtlı projeleri listele"),
    BotCommand("current",       "Aktif projeyi göster"),
    BotCommand("addproject",    "Yeni proje kaydet"),
    BotCommand("removeproject", "Proje sil"),
    BotCommand("model",         "Model bilgisi / değiştir"),
    BotCommand("pause",         "Claude Code'u duraklat"),
    BotCommand("resume",        "Claude Code'u devam ettir"),
    BotCommand("kill",          "Çalışan process'i sonlandır"),
    BotCommand("budget",        "Günlük maliyet limiti"),
    BotCommand("cost",          "Harcama özeti"),
]


async def _post_init(app: Application) -> None:
    """Bot başlangıcında komutları BotFather'a kaydet."""
    try:
        await app.bot.set_my_commands(_BOT_COMMANDS)
        logger.info("BotFather komut listesi güncellendi (%d komut)", len(_BOT_COMMANDS))
    except Exception as exc:
        logger.warning("Komut listesi güncellenemedi: %s", exc)

    # Restart bildirimi
    import json
    from core.config import CONFIG_FILE
    restart_file = CONFIG_FILE.parent / "restart.json"
    if restart_file.exists():
        try:
            with open(restart_file, "r") as f:
                data = json.load(f)
            chat_id = data.get("chat_id")
            if chat_id:
                await app.bot.send_message(chat_id=chat_id, text="🚀 *Yeniden başladım!* Komutlarınızı bekliyorum.", parse_mode="Markdown")
            restart_file.unlink()
        except Exception as exc:
            logger.error("Restart bildirimi gönderilemedi: %s", exc)


def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN env değişkeni bulunamadı!")
        raise SystemExit(1)

    logger.info("IRQ Watchdog Bot başlatılıyor...")

    app = (
        Application.builder()
        .token(token)
        .concurrent_updates(True)
        .post_init(_post_init)
        .build()
    )
    register_handlers(app)

    async def error_handler(update, context):
        logger.error("Yakalanmamış hata: %s", context.error, exc_info=context.error)

    app.add_error_handler(error_handler)

    logger.info("Polling modunda çalışıyor...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
