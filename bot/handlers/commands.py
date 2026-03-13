"""
Project IRQ — Komut Handler'ları
Phase 1: /start, /status, /help, /ping
"""

import logging
import os
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from core.ai_runner import runner
from core.config import CLAUDE_MODEL

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user    = update.effective_user.first_name or "Kullanıcı"

    await update.message.reply_text(
        f"👋 Merhaba {user}!\n\n"
        f"🤖 *IRQ Watchdog Bot* aktif.\n"
        f"🔑 Chat ID'n: `{chat_id}`\n\n"
        f"Bu ID'yi `.env` dosyasına `ADMIN_CHAT_ID` olarak ekle, "
        f"ardından bot'u yeniden başlat.\n\n"
        f"📋 Tüm komutlar için /help",
        parse_mode="Markdown",
    )
    logger.info("/start — kullanıcı: %s (%s)", user, chat_id)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    claude_status = "🟢 Çalışıyor" if runner.is_running else "⚪ Boşta"

    await update.message.reply_text(
        f"📊 *IRQ Watchdog — Durum*\n"
        f"🕐 {now}\n\n"
        f"*Claude Code:* {claude_status}\n"
        f"*Model:* `{CLAUDE_MODEL}`\n\n"
        f"💰 *Günlük Maliyet:* _(Faz 7'de aktif)_\n\n"
        f"✅ Bot çalışıyor.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *IRQ Bot — Komut Listesi*\n\n"
        "*Genel:*\n"
        "/start    — başlat, Chat ID öğren\n"
        "/status   — sistem durumu\n"
        "/ping     — bot çalışıyor mu?\n"
        "/help     — bu mesaj\n\n"
        "*Proje Yönetimi:*\n"
        "/projects      — kayıtlı projeler\n"
        "/addproject    — yeni proje ekle\n"
        "/removeproject — proje sil\n"
        "/current       — aktif proje\n"
        "/roadmap       — faz durumu\n\n"
        "*Claude Code:*\n"
        "/run <prompt>  — Claude Code'a prompt gönder\n"
        "/cancel        — çalışan komutu iptal et\n\n"
        "*Yakında:*\n"
        "/model    — model bilgisi / değiştir",
        parse_mode="Markdown",
    )


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🏓 Pong!")
    logger.debug("/ping — %s", update.effective_chat.id)


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botu yeniden başlat (self-restart)."""
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    import json
    import sys
    from core.config import CONFIG_FILE

    restart_file = CONFIG_FILE.parent / "restart.json"
    try:
        with open(restart_file, "w") as f:
            json.dump({"chat_id": chat_id}, f)
    except Exception as exc:
        logger.error("Restart dosyası yazılamadı: %s", exc)

    await update.message.reply_text("🔄 Bot yeniden başlatılıyor... Lütfen bekleyin.")
    logger.info("Bot yeniden başlatılıyor (kullanıcı: %s)", chat_id)

    # Replace the current process
    os.execv(sys.executable, [sys.executable] + sys.argv)
