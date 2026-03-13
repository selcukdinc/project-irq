"""
Project IRQ — Watchdog Handler'ları
Faz 6B-6C: Loop tespiti bildirimleri, /pause, /resume, /kill komutları.
"""

from __future__ import annotations

import logging
import os

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.ai_runner import runner

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")


# ------------------------------------------------------------------
# Watchdog Callback Factory (Faz 6B)
# ------------------------------------------------------------------

def create_watchdog_callback(bot: Bot, chat_id: str):
    """
    Loop tespiti anında Telegram'a bildirim gönderecek async callback döndürür.
    Bu callback, LogWatcher'a verilir ve _execute_run() içinde kullanılır.

    Mesajda Devam Et / Atla / Durdur inline butonları gönderilir.
    """
    async def _callback(reason: str) -> None:
        text = (
            "⚠️ *Loop Tespit Edildi!*\n\n"
            f"🔍 Sebep:\n{reason}\n\n"
            "Ne yapmak istersin?"
        )
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("▶️ Devam Et", callback_data="watchdog:continue"),
                InlineKeyboardButton("⏭ Atla", callback_data="watchdog:skip"),
            ],
            [
                InlineKeyboardButton("⏹ Durdur", callback_data="watchdog:stop"),
            ],
        ])
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=markup,
            )
            logger.info("Watchdog bildirimi gönderildi (chat_id=%s)", chat_id)
        except Exception as exc:
            logger.error("Watchdog bildirimi gönderilemedi: %s", exc)

    return _callback


# ------------------------------------------------------------------
# /pause — Claude Code'u durdur (SIGSTOP)
# ------------------------------------------------------------------
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    if not runner.is_running:
        await update.message.reply_text("ℹ️ Şu an çalışan bir komut yok.")
        return

    if runner.is_paused:
        await update.message.reply_text(
            "ℹ️ Komut zaten duraklatılmış. Devam ettirmek için: /resume"
        )
        return

    ok = await runner.pause()
    if ok:
        await update.message.reply_text(
            "⏸ *Claude Code duraklatıldı.*\n"
            "Devam ettirmek için: /resume\n"
            "Sonlandırmak için: /kill",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("❌ Duraklatılamadı. Process mevcut değil.")


# ------------------------------------------------------------------
# /resume — Duraklatılmış komutu devam ettir (SIGCONT)
# ------------------------------------------------------------------
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    if not runner.is_running:
        await update.message.reply_text("ℹ️ Şu an çalışan bir komut yok.")
        return

    if not runner.is_paused:
        await update.message.reply_text(
            "ℹ️ Komut zaten çalışıyor. Durdurmak için: /pause"
        )
        return

    ok = await runner.resume()
    if ok:
        await update.message.reply_text("▶️ *Claude Code devam ediyor...*", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Devam ettirilemedi.")


# ------------------------------------------------------------------
# /kill — Çalışan process'i sonlandır (cancel gibi ama farklı isimde)
# ------------------------------------------------------------------
async def cmd_kill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    if not runner.is_running:
        await update.message.reply_text("ℹ️ Şu an çalışan bir komut yok.")
        return

    killed = await runner.cancel()
    if killed:
        await update.message.reply_text("🛑 *Komut sonlandırıldı.*", parse_mode="Markdown")
    else:
        await update.message.reply_text("ℹ️ Komut zaten tamamlanmış.")


# ------------------------------------------------------------------
# Inline callback — Watchdog Devam Et / Atla / Durdur (Faz 6B)
# ------------------------------------------------------------------
async def callback_watchdog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await query.answer("🚫 Yetkiniz yok.", show_alert=True)
        return

    action = query.data.split(":", 1)[1]

    if action == "continue":
        # Eğer process duraklatılmışsa devam ettir, yoksa sadece bildirimi kapat
        if runner.is_running and runner.is_paused:
            await runner.resume()
            await query.edit_message_text(
                "▶️ *Devam Et* seçildi — Claude Code çalışmaya devam ediyor.",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                "▶️ *Devam Et* seçildi — komut zaten çalışıyor.",
                parse_mode="Markdown",
            )

    elif action == "skip":
        # Loop'u yoksay, sadece bildirimi kapat
        await query.edit_message_text(
            "⏭ *Atla* seçildi — loop bildirimi kapatıldı. Komut çalışmaya devam ediyor.",
            parse_mode="Markdown",
        )

    elif action == "stop":
        if runner.is_running:
            await runner.cancel()
            await query.edit_message_text(
                "⏹ *Durdur* seçildi — Claude Code sonlandırıldı.",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                "ℹ️ Komut zaten tamamlanmış.",
                parse_mode="Markdown",
            )

    else:
        await query.edit_message_text("❓ Bilinmeyen watchdog komutu.")
