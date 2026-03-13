"""
Project IRQ — Claude Code Handler'ları
Faz 3A-3B: /run, /cancel komutları + güvenlik & kontrol
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.claude_runner import runner
from core.project_registry import get_active_project

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# Rate limiting: dakikada max 5 komut
_RATE_LIMIT = 5
_RATE_WINDOW = 60  # saniye
_run_timestamps: deque[float] = deque()

# Onay bekleyen prompt'lar: {chat_id: {prompt, project}}
_pending_confirms: dict[str, dict] = {}

# Telegram mesaj karakter limiti
_TG_MAX_LEN = 4096


def _truncate(text: str, max_len: int = _TG_MAX_LEN - 200) -> str:
    """Uzun çıktıyı kırp, son kısmı göster (en güncel bilgi orada)."""
    if len(text) <= max_len:
        return text
    return "… _(kırpıldı)_\n\n" + text[-max_len:]


def _format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}dk {secs}s"


# ------------------------------------------------------------------
# /run <prompt> — Claude Code'a prompt gönder
# ------------------------------------------------------------------
async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Admin kontrolü
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    # Prompt kontrolü
    if not context.args:
        await update.message.reply_text(
            "📝 Kullanım: `/run <prompt>`\n\n"
            "Örnek:\n"
            "`/run bu projede kaç test var?`",
            parse_mode="Markdown",
        )
        return

    prompt = " ".join(context.args)

    # Rate limiting kontrolü
    now = time.monotonic()
    while _run_timestamps and now - _run_timestamps[0] > _RATE_WINDOW:
        _run_timestamps.popleft()
    if len(_run_timestamps) >= _RATE_LIMIT:
        await update.message.reply_text(
            f"⚠️ Rate limit: dakikada en fazla {_RATE_LIMIT} komut.\n"
            "Biraz bekleyip tekrar dene.",
        )
        return

    # Aktif proje kontrolü
    project = get_active_project()
    if not project:
        await update.message.reply_text(
            "📂 Aktif proje yok. Önce `/projects` ile proje seç.",
            parse_mode="Markdown",
        )
        return

    # Zaten çalışıyor mu?
    if runner.is_running:
        await update.message.reply_text(
            "⚠️ Zaten çalışan bir komut var.\n"
            "İptal etmek için: /cancel",
        )
        return

    # Hassas komutlar için onay mekanizması
    _SENSITIVE_KEYWORDS = ["delete", "remove", "drop", "sil", "kaldır", "reset", "force"]
    if any(kw in prompt.lower() for kw in _SENSITIVE_KEYWORDS):
        _pending_confirms[chat_id] = {"prompt": prompt, "project": project}
        await update.message.reply_text(
            f"⚠️ *Hassas komut tespit edildi!*\n\n"
            f"💬 `{prompt[:200]}`\n\n"
            f"Devam etmek istiyor musun?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Evet, çalıştır", callback_data="run_confirm:yes"),
                    InlineKeyboardButton("❌ İptal", callback_data="run_confirm:no"),
                ]
            ]),
        )
        return

    _run_timestamps.append(now)
    await _execute_run(update, prompt, project)


async def _execute_run(update: Update, prompt: str, project: dict) -> None:
    """Claude Code'u çalıştır ve sonucu gönder."""
    # "Çalışıyor" mesajı gönder
    status_msg = await update.effective_message.reply_text(
        f"⏳ *Claude Code çalışıyor...*\n\n"
        f"📂 Proje: {project['name']}\n"
        f"💬 Prompt: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`",
        parse_mode="Markdown",
    )

    # Claude Code çalıştır
    result = await runner.run(
        prompt=prompt,
        project_path=project["path"],
    )

    # Sonucu gönder
    elapsed = _format_elapsed(result.elapsed_seconds)
    output = _truncate(result.output) if result.output else "_(boş çıktı)_"

    if result.ok:
        text = (
            f"✅ *Tamamlandı* ({elapsed})\n\n"
            f"{output}"
        )
    elif result.cancelled:
        text = f"🚫 *İptal edildi* ({elapsed})"
    else:
        text = (
            f"❌ *Hata* ({elapsed})\n\n"
            f"{output}"
        )

    # Durum mesajını güncelle
    try:
        await status_msg.edit_text(text, parse_mode="Markdown")
    except Exception:
        # Markdown parse hatası olursa düz text olarak gönder
        try:
            await status_msg.edit_text(text)
        except Exception as exc:
            logger.error("Mesaj güncellenemedi: %s", exc)
            await update.message.reply_text(text[:_TG_MAX_LEN])


# ------------------------------------------------------------------
# /cancel — çalışan komutu iptal et
# ------------------------------------------------------------------
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    if not runner.is_running:
        await update.message.reply_text("ℹ️ Şu an çalışan bir komut yok.")
        return

    cancelled = await runner.cancel()
    if cancelled:
        await update.message.reply_text("🚫 Komut iptal edildi.")
    else:
        await update.message.reply_text("ℹ️ Komut zaten tamamlanmış.")


# ------------------------------------------------------------------
# Inline callback — hassas komut onayı
# ------------------------------------------------------------------
async def callback_run_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    choice = query.data.split(":", 1)[1]

    pending = _pending_confirms.pop(chat_id, None)
    if not pending:
        await query.edit_message_text("⏳ Onay süresi dolmuş. Tekrar `/run` kullan.", parse_mode="Markdown")
        return

    if choice == "yes":
        _run_timestamps.append(time.monotonic())
        await query.edit_message_text("✅ Onaylandı, çalıştırılıyor...")
        await _execute_run(update, pending["prompt"], pending["project"])
    else:
        await query.edit_message_text("❌ İptal edildi.")
