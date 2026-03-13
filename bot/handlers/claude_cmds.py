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
from core.model_manager import (
    SUPPORTED_MODELS,
    get_current_model,
    model_info_text,
    resolve_model,
    set_model,
)
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


# ------------------------------------------------------------------
# /model [model_adı] — model göster veya değiştir
# ------------------------------------------------------------------
async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    current = get_current_model()

    # Argümansız: mevcut modeli göster + inline buton listesi
    if not context.args:
        lines = [f"🤖 *Mevcut Model:* `{current}`\n", "📋 *Kullanılabilir Modeller:*"]
        for mid, desc in SUPPORTED_MODELS.items():
            marker = "✅" if mid == current else "  "
            lines.append(f"{marker} `{mid}`\n    _{desc}_")

        buttons = [
            [InlineKeyboardButton(f"{'✅ ' if mid == current else ''}{desc.split('—')[0].strip()}", callback_data=f"model_set:{mid}")]
            for mid, desc in SUPPORTED_MODELS.items()
        ]

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    # Argümanla: modeli değiştir
    name = context.args[0].strip()
    resolved = resolve_model(name)
    if not resolved:
        valid = ", ".join(f"`{m}`" for m in SUPPORTED_MODELS)
        await update.message.reply_text(
            f"❌ Geçersiz model: `{name}`\n\nGeçerli modeller:\n{valid}",
            parse_mode="Markdown",
        )
        return

    if resolved == current:
        await update.message.reply_text(
            f"ℹ️ Zaten bu model kullanılıyor: `{resolved}`",
            parse_mode="Markdown",
        )
        return

    set_model(resolved)
    await update.message.reply_text(
        f"✅ Model değiştirildi!\n\n"
        f"🤖 `{resolved}`\n"
        f"_{model_info_text(resolved)}_",
        parse_mode="Markdown",
    )


# ------------------------------------------------------------------
# Inline callback — model seçim butonu
# ------------------------------------------------------------------
async def callback_model_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await query.answer("🚫 Yetkiniz yok.", show_alert=True)
        return

    model_id = query.data.split(":", 1)[1]
    current = get_current_model()

    if model_id == current:
        await query.answer(f"Zaten bu model seçili: {model_id}", show_alert=False)
        return

    if not set_model(model_id):
        await query.edit_message_text("❌ Model değiştirilemedi. Geçersiz model ID.")
        return

    # Mesajı güncelle — yeni durumu yansıt
    lines = [f"🤖 *Aktif Model:* `{model_id}`\n", "📋 *Kullanılabilir Modeller:*"]
    for mid, desc in SUPPORTED_MODELS.items():
        marker = "✅" if mid == model_id else "  "
        lines.append(f"{marker} `{mid}`\n    _{desc}_")

    buttons = [
        [InlineKeyboardButton(f"{'✅ ' if mid == model_id else ''}{desc.split('—')[0].strip()}", callback_data=f"model_set:{mid}")]
        for mid, desc in SUPPORTED_MODELS.items()
    ]

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
