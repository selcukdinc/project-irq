"""
Project IRQ — Komut Handler'ları
Phase 1: /start, /status, /help, /ping
"""

import logging
import os
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

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

    await update.message.reply_text(
        f"📊 *IRQ Watchdog — Durum*\n"
        f"🕐 {now}\n\n"
        f"*İzlenen Agentlar:*\n"
        f"   _(Phase 2'de aktif olacak)_\n\n"
        f"💰 *Günlük Maliyet:* _(Phase 3'te aktif)_\n\n"
        f"✅ Bot çalışıyor.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *IRQ Bot — Komut Listesi*\n\n"
        "*Mevcut (Phase 1):*\n"
        "/start    — başlat, Chat ID öğren\n"
        "/status   — sistem durumu\n"
        "/ping     — bot çalışıyor mu?\n"
        "/help     — bu mesaj\n\n"
        "*Yakında (Phase 2):*\n"
        "/pause    — agent'ı durdur\n"
        "/resume   — devam et\n"
        "/skip     — adımı atla\n\n"
        "*Yakında (Phase 3):*\n"
        "/budget   — maliyet limiti ayarla\n"
        "/cost     — harcama özeti",
        parse_mode="Markdown",
    )


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🏓 Pong!")
    logger.debug("/ping — %s", update.effective_chat.id)
