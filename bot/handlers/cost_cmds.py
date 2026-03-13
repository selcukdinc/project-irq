"""
Project IRQ — Maliyet Kontrolü Handler'ları
Faz 7: /budget, /cost komutları ve maliyet takibi
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# Cost tracker instance
_cost_tracker: CostTracker | None = None


def _get_cost_tracker() -> CostTracker:
    """Cost tracker singleton'ını al"""
    global _cost_tracker
    if _cost_tracker is None:
        config_dir = Path.home() / ".irq"
        config_dir.mkdir(exist_ok=True)
        _cost_tracker = CostTracker(config_dir)
    return _cost_tracker


def _format_currency(amount: float) -> str:
    """USD formatı"""
    return f"${amount:.2f}"


# ------------------------------------------------------------------
# /budget [limit] — günlük maliyet limitini göster/ayarla
# ------------------------------------------------------------------
async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Günlük maliyet limitini göster veya ayarla"""
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    cost_tracker = _get_cost_tracker()

    # Argümansız: mevcut limiti göster
    if not context.args:
        current_limit = cost_tracker.get_daily_limit()
        daily_spent = cost_tracker.get_daily_cost()
        remaining = cost_tracker.get_remaining_budget()

        # Kullanım çubuğu
        if current_limit > 0:
            usage_pct = min(100, int((daily_spent / current_limit) * 100))
            bar_filled = usage_pct // 10
            bar = "🟢" * bar_filled + "⚪" * (10 - bar_filled)
        else:
            bar = "⚪" * 10

        # Renk kodu
        if daily_spent >= current_limit:
            status_emoji = "🔴"
            status_text = "Limit aşıldı!"
        elif daily_spent >= current_limit * 0.8:
            status_emoji = "🟡"
            status_text = "Limite yakın"
        else:
            status_emoji = "🟢"
            status_text = "Normal"

        text = (
            f"💰 *Günlük Bütçe Durumu*\n\n"
            f"{status_emoji} {status_text}\n\n"
            f"**Günlük Limit:** {_format_currency(current_limit)}\n"
            f"**Harcanan:** {_format_currency(daily_spent)}\n"
            f"**Kalan:** {_format_currency(remaining)}\n\n"
            f"**Kullanım:** {bar} `{usage_pct}%`\n\n"
            f"_Limit değiştirmek için:_\n"
            f"`/budget <miktar>`\n"
            f"Örnek: `/budget 10.50`"
        )

        # Inline butonlar - yaygın limitler
        buttons = [
            [
                InlineKeyboardButton("$5", callback_data="budget_set:5.0"),
                InlineKeyboardButton("$10", callback_data="budget_set:10.0"),
                InlineKeyboardButton("$20", callback_data="budget_set:20.0"),
            ],
            [
                InlineKeyboardButton("$50", callback_data="budget_set:50.0"),
                InlineKeyboardButton("Sınırsız", callback_data="budget_set:999999.0"),
            ],
        ]

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    # Argümanla: limiti değiştir
    try:
        new_limit = float(context.args[0])
        if new_limit < 0:
            raise ValueError("Negatif olamaz")

        old_limit = cost_tracker.get_daily_limit()
        cost_tracker.set_daily_limit(new_limit)

        if new_limit >= 999999:
            limit_text = "Sınırsız"
        else:
            limit_text = _format_currency(new_limit)

        await update.message.reply_text(
            f"✅ *Günlük limit güncellendi!*\n\n"
            f"**Eski:** {_format_currency(old_limit)}\n"
            f"**Yeni:** {limit_text}\n\n"
            f"_Bu limit aşıldığında Claude Code çalıştırması uyarı verir._",
            parse_mode="Markdown",
        )

    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Geçersiz miktar!\n\n"
            "**Kullanım:** `/budget <miktar>`\n\n"
            "**Örnekler:**\n"
            "• `/budget 5` → $5.00\n"
            "• `/budget 12.50` → $12.50\n"
            "• `/budget 0` → Ücretsiz mod",
            parse_mode="Markdown",
        )


# ------------------------------------------------------------------
# /cost [days] — maliyet özetini göster
# ------------------------------------------------------------------
async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Son N günün maliyet özetini göster"""
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    days = 7  # Varsayılan
    if context.args:
        try:
            days = max(1, min(int(context.args[0]), 30))
        except ValueError:
            pass

    cost_tracker = _get_cost_tracker()
    summary = cost_tracker.get_cost_summary(days)

    if summary["total_cost"] == 0:
        await update.message.reply_text(
            "💸 Henüz maliyet kaydı yok.\n\n"
            "Claude Code kullandıkça burada görünecek.",
        )
        return

    # Günlük breakdown
    daily_lines = []
    for date_str, cost in summary["daily_costs"].items():
        date_obj = datetime.fromisoformat(date_str).date()
        day_name = date_obj.strftime("%a")
        if date_obj == date.today():
            day_name = "Bugün"
        elif date_obj == date.today() - timedelta(days=1):
            day_name = "Dün"
        daily_lines.append(f"• {day_name} {date_obj.strftime('%m/%d')}: {_format_currency(cost)}")

    # Model breakdown
    model_lines = []
    for model, stats in summary["usage_by_model"].items():
        model_short = model.split("-")[1] if "-" in model else model
        model_lines.append(
            f"• `{model_short}`: {stats['count']} çalıştırma, {_format_currency(stats['cost'])}"
        )

    # Ana özet
    avg_daily = summary["total_cost"] / days if days > 0 else 0
    daily_limit = summary["daily_limit"]

    text = (
        f"💰 *Maliyet Özeti* _(Son {days} gün)_\n\n"
        f"**Toplam Harcama:** {_format_currency(summary['total_cost'])}\n"
        f"**Günlük Ortalama:** {_format_currency(avg_daily)}\n"
        f"**Günlük Limit:** {_format_currency(daily_limit)}\n\n"
        f"**📅 Günlük Detay:**\n" + "\n".join(daily_lines[:7]) + "\n\n"
        f"**🤖 Model Kullanımı:**\n" + "\n".join(model_lines[:5])
    )

    # Eğer çok uzunsa kırp
    if len(text) > 4000:
        text = text[:3900] + "\n\n_... (kırpıldı)_"

    # Inline butonlar - farklı zaman aralıkları
    buttons = [
        [
            InlineKeyboardButton("1 gün", callback_data="cost_view:1"),
            InlineKeyboardButton("7 gün", callback_data="cost_view:7"),
            InlineKeyboardButton("30 gün", callback_data="cost_view:30"),
        ],
        [
            InlineKeyboardButton("🔄 Yenile", callback_data=f"cost_view:{days}"),
        ],
    ]

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ------------------------------------------------------------------
# Inline callback'ler
# ------------------------------------------------------------------
async def callback_budget_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Budget limiti ayarlama inline callback'i"""
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await query.answer("🚫 Yetkiniz yok.", show_alert=True)
        return

    try:
        new_limit = float(query.data.split(":", 1)[1])
        cost_tracker = _get_cost_tracker()
        old_limit = cost_tracker.get_daily_limit()
        cost_tracker.set_daily_limit(new_limit)

        if new_limit >= 999999:
            limit_text = "Sınırsız"
        else:
            limit_text = _format_currency(new_limit)

        await query.edit_message_text(
            f"✅ *Günlük limit güncellendi!*\n\n"
            f"**Eski:** {_format_currency(old_limit)}\n"
            f"**Yeni:** {limit_text}\n\n"
            f"_/cost ile harcamaları kontrol edebilirsin._",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Budget ayarlama hatası: {e}")
        await query.edit_message_text("❌ Limit ayarlanamadı. Tekrar deneyin.")


async def callback_cost_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maliyet görüntüleme callback'i"""
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await query.answer("🚫 Yetkiniz yok.", show_alert=True)
        return

    try:
        days = int(query.data.split(":", 1)[1])
        cost_tracker = _get_cost_tracker()
        summary = cost_tracker.get_cost_summary(days)

        if summary["total_cost"] == 0:
            await query.edit_message_text("💸 Bu dönemde maliyet kaydı yok.")
            return

        # Günlük breakdown
        daily_lines = []
        sorted_dates = sorted(summary["daily_costs"].items(), reverse=True)
        for date_str, cost in sorted_dates[:min(7, days)]:
            date_obj = datetime.fromisoformat(date_str).date()
            day_name = date_obj.strftime("%a")
            if date_obj == date.today():
                day_name = "Bugün"
            elif date_obj == date.today() - timedelta(days=1):
                day_name = "Dün"
            daily_lines.append(f"• {day_name} {date_obj.strftime('%m/%d')}: {_format_currency(cost)}")

        # Model breakdown
        model_lines = []
        for model, stats in summary["usage_by_model"].items():
            model_short = model.split("-")[1] if "-" in model else model
            model_lines.append(
                f"• `{model_short}`: {stats['count']}x, {_format_currency(stats['cost'])}"
            )

        # Ana özet
        avg_daily = summary["total_cost"] / days if days > 0 else 0

        text = (
            f"💰 *Maliyet Özeti* _(Son {days} gün)_\n\n"
            f"**Toplam:** {_format_currency(summary['total_cost'])}\n"
            f"**Günlük Ortalama:** {_format_currency(avg_daily)}\n\n"
            f"**📅 Günlük Detay:**\n" + "\n".join(daily_lines) + "\n\n"
            f"**🤖 Model Kullanımı:**\n" + "\n".join(model_lines[:3])
        )

        # Butonlar
        buttons = [
            [
                InlineKeyboardButton("1 gün", callback_data="cost_view:1"),
                InlineKeyboardButton("7 gün", callback_data="cost_view:7"),
                InlineKeyboardButton("30 gün", callback_data="cost_view:30"),
            ],
            [
                InlineKeyboardButton("🔄 Yenile", callback_data=f"cost_view:{days}"),
            ],
        ]

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Maliyet görüntüleme hatası: {e}")
        await query.edit_message_text("❌ Veriler yüklenemedi.")