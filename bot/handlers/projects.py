"""
Project IRQ — Proje Yönetim Handler'ları
Phase 2A-2B: /projects, /addproject, /removeproject, /roadmap, /phase
"""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.project_registry import (
    add_project,
    get_active_project,
    list_projects,
    remove_project,
    set_active_project,
)
from core.roadmap_parser import (
    format_phase_detail,
    format_roadmap_summary,
    get_phase,
    parse_roadmap,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# /projects — kayıtlı projeleri inline butonlarla listele
# ------------------------------------------------------------------
async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    projects = list_projects()

    if not projects:
        await update.message.reply_text(
            "📂 Henüz kayıtlı proje yok.\n\n"
            "Yeni proje eklemek için:\n"
            "`/addproject <isim> <dizin_yolu>`",
            parse_mode="Markdown",
        )
        return

    buttons = []
    for p in projects:
        label = f"{'✅' if p.get('active') else '📁'} {p['name']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"sel_proj:{p['id']}")])

    await update.message.reply_text(
        "📂 *Kayıtlı Projeler*\nAktif projeyi değiştirmek için bir tane seç:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


# ------------------------------------------------------------------
# Inline buton callback — proje seçimi
# ------------------------------------------------------------------
async def callback_select_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    project_id = query.data.split(":", 1)[1]
    project = set_active_project(project_id)

    if project:
        await query.edit_message_text(
            f"✅ Aktif proje değiştirildi: *{project['name']}*\n"
            f"📁 `{project['path']}`",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text("❌ Proje bulunamadı.")


# ------------------------------------------------------------------
# /addproject <isim> <path> — yeni proje kaydet
# ------------------------------------------------------------------
async def cmd_addproject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "📝 Kullanım: `/addproject <isim> <dizin_yolu>`\n\n"
            "Örnek:\n"
            "`/addproject MyApp ~/Projects/my-app`",
            parse_mode="Markdown",
        )
        return

    name = args[0]
    path = " ".join(args[1:])  # path'te boşluk olabilir

    try:
        project = add_project(name, path)
        active_mark = " (aktif)" if project.get("active") else ""
        await update.message.reply_text(
            f"✅ Proje eklendi{active_mark}!\n\n"
            f"*{project['name']}*\n"
            f"📁 `{project['path']}`\n"
            f"🆔 `{project['id']}`",
            parse_mode="Markdown",
        )
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
    except FileNotFoundError as exc:
        await update.message.reply_text(f"❌ {exc}")


# ------------------------------------------------------------------
# /removeproject <id> — proje sil
# ------------------------------------------------------------------
async def cmd_removeproject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "📝 Kullanım: `/removeproject <proje_id>`\n\n"
            "Proje ID'lerini görmek için /projects",
            parse_mode="Markdown",
        )
        return

    project_id = args[0]
    if remove_project(project_id):
        await update.message.reply_text(f"🗑️ Proje silindi: `{project_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ `{project_id}` bulunamadı.", parse_mode="Markdown")


# ------------------------------------------------------------------
# /current — aktif projeyi göster
# ------------------------------------------------------------------
async def cmd_current(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    project = get_active_project()

    if not project:
        await update.message.reply_text(
            "📂 Aktif proje yok.\n"
            "Proje eklemek için: `/addproject <isim> <path>`",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"📌 *Aktif Proje*\n\n"
        f"*{project['name']}*\n"
        f"📁 `{project['path']}`\n"
        f"🆔 `{project['id']}`",
        parse_mode="Markdown",
    )


# ------------------------------------------------------------------
# /roadmap — aktif projenin faz durumunu göster
# ------------------------------------------------------------------
def _roadmap_path_for(project: dict) -> str | None:
    """Projenin ROADMAP.md tam yolunu döndürür."""
    from pathlib import Path
    rp = Path(project["path"]) / project.get("roadmap_path", "ROADMAP.md")
    return str(rp) if rp.is_file() else None


async def cmd_roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    project = get_active_project()
    if not project:
        await update.message.reply_text(
            "📂 Aktif proje yok. Önce `/projects` ile proje seç.",
            parse_mode="Markdown",
        )
        return

    rp = _roadmap_path_for(project)
    if not rp:
        await update.message.reply_text("❌ ROADMAP dosyası bulunamadı.")
        return

    phases = parse_roadmap(rp)
    text = format_roadmap_summary(phases)

    # Her faz için Detay butonu
    buttons = []
    for p in phases:
        buttons.append([
            InlineKeyboardButton(
                f"📊 Faz {p.number} Detay", callback_data=f"phase_detail:{p.number}"
            )
        ])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


# ------------------------------------------------------------------
# /phase <faz_no> — belirli fazın detaylarını göster
# ------------------------------------------------------------------
async def cmd_phase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    project = get_active_project()
    if not project:
        await update.message.reply_text(
            "📂 Aktif proje yok. Önce `/projects` ile proje seç.",
            parse_mode="Markdown",
        )
        return

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "📝 Kullanım: `/phase <faz_numarası>`\nÖrnek: `/phase 2`",
            parse_mode="Markdown",
        )
        return

    phase_no = int(args[0])
    rp = _roadmap_path_for(project)
    if not rp:
        await update.message.reply_text("❌ ROADMAP dosyası bulunamadı.")
        return

    phase = get_phase(rp, phase_no)
    if not phase:
        await update.message.reply_text(f"❌ Faz {phase_no} bulunamadı.")
        return

    await update.message.reply_text(
        format_phase_detail(phase),
        parse_mode="Markdown",
    )


# ------------------------------------------------------------------
# Inline buton callback — faz detayı
# ------------------------------------------------------------------
async def callback_phase_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    project = get_active_project()
    if not project:
        await query.edit_message_text("❌ Aktif proje yok.")
        return

    phase_no = int(query.data.split(":", 1)[1])
    rp = _roadmap_path_for(project)
    if not rp:
        await query.edit_message_text("❌ ROADMAP dosyası bulunamadı.")
        return

    phase = get_phase(rp, phase_no)
    if not phase:
        await query.edit_message_text(f"❌ Faz {phase_no} bulunamadı.")
        return

    await query.edit_message_text(
        format_phase_detail(phase),
        parse_mode="Markdown",
    )
