"""
Project IRQ — Claude Code Handler'ları
Faz 3A-3B: /run, /cancel komutları + güvenlik & kontrol
Faz 6A: LogWatcher entegrasyonu (streaming + loop tespiti)
Faz 6D: /menu Command Center
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.claude_runner import runner
from core.config import LOGS_DIR, ensure_irq_dirs
from core.cost_tracker import CostTracker  # Faz 7: Maliyet takibi
from core.log_watcher import LogWatcher
from core.model_manager import (
    SUPPORTED_MODELS,
    get_current_model,
    model_info_text,
    resolve_model,
    set_model,
)
from core.notifier import format_history_list, load_history, make_run_record, save_run
from core.project_registry import get_active_project
from core.roadmap_parser import parse_roadmap

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
    import sys

    # "Çalışıyor" mesajı gönder
    status_msg = await update.effective_message.reply_text(
        f"⏳ *Claude Code çalışıyor...*\n\n"
        f"📂 Proje: {project['name']}\n"
        f"💬 Prompt: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`",
        parse_mode="Markdown",
    )

    # Faz 6A: LogWatcher hazırla
    ensure_irq_dirs()
    log_filename = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{project['name']}.log"
    log_path = LOGS_DIR / log_filename

    # Terminale başlık yazdır — hangi process çalışıyor görünsün
    print(f"\n{'='*60}", flush=True)
    print(f"[IRQ] Claude CLI başlatıldı", flush=True)
    print(f"[IRQ] Proje : {project['name']} ({project['path']})", flush=True)
    print(f"[IRQ] Prompt: {prompt[:120]}", flush=True)
    print(f"{'='*60}", flush=True)

    # Watchdog callback — bot context'ini taşır
    from handlers.watchdog import create_watchdog_callback
    bot = update.get_bot()
    chat_id = str(update.effective_chat.id)
    watchdog_cb = create_watchdog_callback(bot, chat_id)

    watcher = LogWatcher(log_path=log_path, watchdog_callback=watchdog_cb)
    watcher.start_idle_monitor_task()

    # line_callback: hem terminale yaz hem watcher'a ilet
    def _line_handler(line: str) -> None:
        sys.stdout.write(line)
        sys.stdout.flush()
        watcher.feed(line)

    # Telegram'a periyodik "hala çalışıyor" güncellemesi (her 30 sn)
    start_time = time.monotonic()
    _update_task: list[asyncio.Task] = []

    async def _periodic_update() -> None:
        """30 saniyede bir Telegram mesajını güncelle."""
        try:
            while True:
                await asyncio.sleep(30)
                elapsed = _format_elapsed(time.monotonic() - start_time)
                try:
                    await status_msg.edit_text(
                        f"⏳ *Claude Code çalışıyor...* ({elapsed})\n\n"
                        f"📂 Proje: {project['name']}\n"
                        f"💬 Prompt: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`\n\n"
                        f"_/cancel ile iptal edebilirsin_",
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass  # Mesaj değişmediyse Telegram hata verir, yoksay
        except asyncio.CancelledError:
            pass

    _update_task.append(asyncio.create_task(_periodic_update()))

    # Claude Code çalıştır (streaming line_callback ile)
    result = await runner.run(
        prompt=prompt,
        project_path=project["path"],
        line_callback=_line_handler,
    )

    # Cleanup
    for t in _update_task:
        t.cancel()
    watcher.stop_idle_monitor()

    print(f"\n{'='*60}", flush=True)
    print(f"[IRQ] Claude CLI tamamlandı (rc={result.returncode}, {result.elapsed_seconds:.1f}s)", flush=True)
    print(f"{'='*60}\n", flush=True)

    # Faz 5: Çalıştırma geçmişine kaydet
    try:
        record = make_run_record(
            project_name=project["name"],
            project_path=project["path"],
            prompt=prompt,
            wall_start=result.wall_start,
            elapsed=result.elapsed_seconds,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            cancelled=result.cancelled,
        )
        save_run(record)
    except Exception as exc:
        logger.warning("History kaydedilemedi: %s", exc)

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


# ------------------------------------------------------------------
# /history [n] — son N tamamlanan çalıştırmayı listele (Faz 5C)
# ------------------------------------------------------------------
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    n = 10
    if context.args:
        try:
            n = max(1, min(int(context.args[0]), 50))
        except ValueError:
            pass

    records = load_history(n)

    if not records:
        await update.message.reply_text(
            "📭 Henüz tamamlanmış çalıştırma yok.\n"
            "Başlamak için: `/run <prompt>`",
            parse_mode="Markdown",
        )
        return

    lines = [f"📋 *Son {len(records)} Çalıştırma*\n"]
    for i, r in enumerate(records, 1):
        mins = int(r.elapsed_seconds // 60)
        secs = int(r.elapsed_seconds % 60)
        elapsed = f"{mins}dk {secs}s" if mins > 0 else f"{secs}s"
        prompt_short = r.prompt[:50] + ("…" if len(r.prompt) > 50 else "")
        lines.append(
            f"{i}. {r.status_emoji} `{r.started_at}` — {elapsed}\n"
            f"   📂 {r.project_name}\n"
            f"   💬 {prompt_short}"
        )

    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")


# ------------------------------------------------------------------
# /menu — Ana kontrol paneli (Faz 6D)
# ------------------------------------------------------------------

def _build_menu_content() -> tuple[str, InlineKeyboardMarkup]:
    """Ana menü mesajı ve inline butonları oluşturur."""
    project = get_active_project()
    current_model = get_current_model()

    # Proje satırı
    if project:
        # ROADMAP ilerleme hesapla
        roadmap_path = Path(project["path"]) / project.get("roadmap_path", "ROADMAP.md")
        try:
            phases = parse_roadmap(roadmap_path)
            total_steps = sum(len(p.steps) for p in phases)
            done_steps = sum(sum(1 for s in p.steps if s.done) for p in phases)
            pct = int((done_steps / total_steps * 100) if total_steps else 0)
            bar_filled = pct // 10
            bar = "▓" * bar_filled + "░" * (10 - bar_filled)
            proj_line = f"📂 {project['name']}  {bar}  %{pct}"
        except Exception:
            proj_line = f"📂 {project['name']}"
    else:
        proj_line = "📂 Aktif proje yok"

    # Durum satırı
    if runner.is_running:
        status_line = "🟢 Çalışıyor" + (" (duraklatıldı)" if runner.is_paused else "")
    else:
        status_line = "⚪ Boşta"

    text = (
        "🏠 *IRQ Command Center*\n"
        f"{proj_line}\n"
        f"{status_line}  |  🤖 `{current_model.split('-')[1] if '-' in current_model else current_model}`\n"
    )

    buttons = [
        [
            InlineKeyboardButton("▶️ Çalıştır", callback_data="menu_run"),
            InlineKeyboardButton("⏹ İptal", callback_data="menu_cancel"),
        ],
        [
            InlineKeyboardButton("⏸ Duraklat", callback_data="menu_pause"),
            InlineKeyboardButton("▶ Devam Et", callback_data="menu_resume"),
        ],
        [
            InlineKeyboardButton("📊 Roadmap", callback_data="menu_roadmap"),
            InlineKeyboardButton("📂 Projeler", callback_data="menu_projects"),
        ],
        [
            InlineKeyboardButton("🤖 Model", callback_data="menu_model"),
            InlineKeyboardButton("📋 Geçmiş", callback_data="menu_history"),
        ],
    ]
    return text, InlineKeyboardMarkup(buttons)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ana kontrol panelini göster."""
    chat_id = str(update.effective_chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Yetkiniz yok.")
        return

    text, markup = _build_menu_content()
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ana menü inline buton callback'leri."""
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
        await query.answer("🚫 Yetkiniz yok.", show_alert=True)
        return

    action = query.data  # "menu_run", "menu_cancel", vb.

    if action == "menu_run":
        await query.edit_message_text(
            "📝 Çalıştırmak için `/run <prompt>` komutunu kullan.\n\n"
            "Örnek: `/run projedeki test sayısını söyle`",
            parse_mode="Markdown",
        )

    elif action == "menu_cancel":
        if not runner.is_running:
            await query.answer("Çalışan komut yok.", show_alert=True)
        else:
            await runner.cancel()
            text, markup = _build_menu_content()
            await query.edit_message_text(
                "🚫 Komut iptal edildi.\n\n" + text,
                parse_mode="Markdown",
                reply_markup=markup,
            )

    elif action == "menu_pause":
        if not runner.is_running:
            await query.answer("Çalışan komut yok.", show_alert=True)
        elif runner.is_paused:
            await query.answer("Zaten duraklatılmış.", show_alert=False)
        else:
            ok = await runner.pause()
            if ok:
                text, markup = _build_menu_content()
                await query.edit_message_text(
                    "⏸ Duraklatıldı.\n\n" + text,
                    parse_mode="Markdown",
                    reply_markup=markup,
                )
            else:
                await query.answer("Duraklatılamadı.", show_alert=True)

    elif action == "menu_resume":
        if not runner.is_running:
            await query.answer("Çalışan komut yok.", show_alert=True)
        elif not runner.is_paused:
            await query.answer("Komut zaten çalışıyor.", show_alert=False)
        else:
            ok = await runner.resume()
            if ok:
                text, markup = _build_menu_content()
                await query.edit_message_text(
                    "▶️ Devam ediyor.\n\n" + text,
                    parse_mode="Markdown",
                    reply_markup=markup,
                )
            else:
                await query.answer("Devam ettirilemedi.", show_alert=True)

    elif action == "menu_roadmap":
        # /where komutunu inline olarak göster
        from handlers.projects import cmd_where
        await query.edit_message_text(
            "📊 Roadmap için /where veya /roadmap komutunu kullan.",
            parse_mode="Markdown",
        )

    elif action == "menu_projects":
        await query.edit_message_text(
            "📂 Projeler için /projects komutunu kullan.",
            parse_mode="Markdown",
        )

    elif action == "menu_model":
        current = get_current_model()
        buttons = [
            [InlineKeyboardButton(
                f"{'✅ ' if mid == current else ''}{desc.split('—')[0].strip()}",
                callback_data=f"model_set:{mid}",
            )]
            for mid, desc in SUPPORTED_MODELS.items()
        ]
        lines = [f"🤖 *Mevcut Model:* `{current}`\n", "📋 *Kullanılabilir Modeller:*"]
        for mid, desc in SUPPORTED_MODELS.items():
            marker = "✅" if mid == current else "  "
            lines.append(f"{marker} `{mid}`\n    _{desc}_")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "menu_history":
        records = load_history(5)
        if not records:
            await query.edit_message_text("📭 Henüz tamamlanmış çalıştırma yok.")
            return
        lines = ["📋 *Son 5 Çalıştırma*\n"]
        for i, r in enumerate(records, 1):
            mins = int(r.elapsed_seconds // 60)
            secs = int(r.elapsed_seconds % 60)
            elapsed = f"{mins}dk {secs}s" if mins > 0 else f"{secs}s"
            prompt_short = r.prompt[:40] + ("…" if len(r.prompt) > 40 else "")
            lines.append(
                f"{i}. {r.status_emoji} {elapsed}\n"
                f"   {prompt_short}"
            )
        await query.edit_message_text("\n\n".join(lines), parse_mode="Markdown")
