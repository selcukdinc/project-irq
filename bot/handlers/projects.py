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
    overall_progress,
    parse_roadmap,
    _progress_bar,
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

    # /where'deki "📂 Projeler" butonu
    if query.data == "where_projects":
        projects = list_projects()
        buttons = [
            [InlineKeyboardButton(
                f"{'✅ ' if p.get('active') else '📁 '}{p['name']}",
                callback_data=f"sel_proj:{p['id']}",
            )]
            for p in projects
        ]
        await query.edit_message_text(
            "📂 *Kayıtlı Projeler*\nAktif projeyi değiştirmek için seç:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

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
_PHASES_PER_ROW = 4
_PHASES_PER_PAGE = 12  # 3 satır × 4 buton


def _roadmap_path_for(project: dict) -> str | None:
    """Projenin ROADMAP.md tam yolunu döndürür."""
    from pathlib import Path
    rp = Path(project["path"]) / project.get("roadmap_path", "ROADMAP.md")
    return str(rp) if rp.is_file() else None


def _build_roadmap_content(
    back_to: str = "",
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup | None]:
    """
    Roadmap özet mesajı ve faz butonlarını oluşturur.

    Args:
        back_to: "menu" → 🏠 Menü geri butonu ekle; "" → geri buton yok
        page:    Faz sayfalama (her sayfada _PHASES_PER_PAGE faz)
    """
    project = get_active_project()
    if not project:
        return "📂 Aktif proje yok. Önce `/projects` ile proje seç.", None

    rp = _roadmap_path_for(project)
    if not rp:
        return f"❌ ROADMAP.md bulunamadı: `{project['path']}/ROADMAP.md`", None

    phases = parse_roadmap(rp)
    if not phases:
        return "❌ ROADMAP parse edilemedi.", None

    text = format_roadmap_summary(phases)

    total = len(phases)
    start = page * _PHASES_PER_PAGE
    end = min(start + _PHASES_PER_PAGE, total)
    page_phases = phases[start:end]

    # Faz butonları: 4'lü grid
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for p in page_phases:
        emoji = p.status_emoji
        row.append(InlineKeyboardButton(
            f"{emoji} {p.label}",
            callback_data=f"rdmap_faz:{back_to}:{p.number}",
        ))
        if len(row) == _PHASES_PER_ROW:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Sayfalama satırı
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(
            "◀️ Önceki", callback_data=f"rdmap_page:{back_to}:{page - 1}"
        ))
    if end < total:
        nav_row.append(InlineKeyboardButton(
            "Sonraki ▶️", callback_data=f"rdmap_page:{back_to}:{page + 1}"
        ))
    if nav_row:
        buttons.append(nav_row)

    # Geri butonu
    if back_to == "menu":
        buttons.append([InlineKeyboardButton("🏠 ← Menü", callback_data="menu_back")])

    return text, InlineKeyboardMarkup(buttons) if buttons else None


async def cmd_roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, markup = _build_roadmap_content(back_to="")
    await update.message.reply_text(
        text,
        reply_markup=markup,
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
# /where — aktif proje + mevcut faz + sıradaki adım (hızlı bağlam)
# ------------------------------------------------------------------

def _build_where_content() -> tuple[str, InlineKeyboardMarkup] | tuple[str, None]:
    """
    /where ekranı için (text, markup) döndürür.
    Hata durumunda (hata_mesajı, None) döner.
    """
    project = get_active_project()
    if not project:
        return (
            "📂 Aktif proje yok.\n\n"
            "Terminalde projenin dizininde şunu çalıştır:\n"
            "`python bot/cli.py init`",
            None,
        )

    rp = _roadmap_path_for(project)
    if not rp:
        return f"❌ ROADMAP.md bulunamadı: `{project['path']}/ROADMAP.md`", None

    phases = parse_roadmap(rp)
    if not phases:
        return "❌ ROADMAP parse edilemedi.", None

    completed_steps, total_steps, pct = overall_progress(phases)
    total_phases = len(phases)

    current_phase = next(
        (p for p in phases if p.total > 0 and p.progress < 100),
        phases[-1],
    )
    next_step = next((s.text for s in current_phase.steps if not s.done), None)

    bar = _progress_bar(pct)
    lines = [
        f"📂 *{project['name']}*",
        "",
        f"🗺 `{bar}` %{pct:.0f}  ({completed_steps}/{total_steps} adım)",
        f"📍 {current_phase.label} ({current_phase.number}/{total_phases}){' — ' + current_phase.title if current_phase.title else ''}",
    ]
    if next_step:
        lines += ["", "⏭ *Sıradaki adım:*", f"⬜ {next_step[:120]}"]

    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Roadmap", callback_data=f"where_phase:{current_phase.number}"),
        InlineKeyboardButton("📂 Projeler", callback_data="where_projects"),
    ]])
    return "\n".join(lines), markup


async def cmd_where(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, markup = _build_where_content()
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=markup,
    )


# ------------------------------------------------------------------
# /overview — tüm projelerin özet durumu tek mesajda
# ------------------------------------------------------------------
async def cmd_overview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from pathlib import Path as _Path

    projects = list_projects()
    if not projects:
        await update.message.reply_text(
            "📂 Kayıtlı proje yok.\n\n"
            "Terminalde projenin dizininde şunu çalıştır:\n"
            "`python bot/cli.py init`",
            parse_mode="Markdown",
        )
        return

    lines = ["📊 *Proje Genel Durumu*\n"]

    for p in projects:
        active_mark = " ✅" if p.get("active") else ""
        rp_path = _Path(p["path"]) / p.get("roadmap_path", "ROADMAP.md")

        if rp_path.is_file():
            phases = parse_roadmap(str(rp_path))
            completed, total, pct = overall_progress(phases)
            bar = _progress_bar(pct, length=8)
            current = next(
                (ph for ph in phases if ph.total > 0 and ph.progress < 100), None
            )
            phase_label = f"{current.label} ({current.number}/{len(phases)})" if current else "✅ Tamamlandı"
            lines.append(f"*{p['name']}*{active_mark}")
            lines.append(f"  `{bar}` %{pct:.0f}  —  {phase_label}")
        else:
            lines.append(f"*{p['name']}*{active_mark}")
            lines.append("  ⚠️ ROADMAP bulunamadı")

        lines.append("")

    # Inline butonlarla proje geçişi
    buttons = [
        [InlineKeyboardButton(
            f"{'✅ ' if p.get('active') else ''}{p['name']}",
            callback_data=f"sel_proj:{p['id']}",
        )]
        for p in projects
    ]

    await update.message.reply_text(
        "\n".join(lines).rstrip(),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ------------------------------------------------------------------
# Inline buton callback — faz detayı (/phase komutu, eski butonlar)
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


# ------------------------------------------------------------------
# Inline callback — Roadmap grid'den faz detayı (rdmap_faz:back_to:no)
# ------------------------------------------------------------------
async def callback_rdmap_faz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Roadmap grid butonundan faz detayı. Geri butonu back_to'ya göre belirlenir."""
    query = update.callback_query
    await query.answer()

    project = get_active_project()
    if not project:
        await query.edit_message_text("❌ Aktif proje yok.")
        return

    # callback_data: "rdmap_faz:{back_to}:{phase_no}"
    parts = query.data.split(":", 2)
    back_to = parts[1] if len(parts) > 1 else ""
    phase_no = int(parts[2]) if len(parts) > 2 else 0

    rp = _roadmap_path_for(project)
    if not rp:
        await query.edit_message_text("❌ ROADMAP dosyası bulunamadı.")
        return

    phase = get_phase(rp, phase_no)
    if not phase:
        await query.edit_message_text(f"❌ Faz {phase_no} bulunamadı.")
        return

    back_buttons: list[InlineKeyboardButton] = [
        InlineKeyboardButton("← Roadmap", callback_data=f"rdmap_page:{back_to}:0"),
    ]
    if back_to == "menu":
        back_buttons.append(InlineKeyboardButton("🏠 Menü", callback_data="menu_back"))

    await query.edit_message_text(
        format_phase_detail(phase),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([back_buttons]),
    )


# ------------------------------------------------------------------
# Inline callback — Roadmap sayfalama (rdmap_page:back_to:page)
# ------------------------------------------------------------------
async def callback_rdmap_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Roadmap faz grid'ini belirtilen sayfada yeniden render eder."""
    query = update.callback_query
    await query.answer()

    # callback_data: "rdmap_page:{back_to}:{page}"
    parts = query.data.split(":", 2)
    back_to = parts[1] if len(parts) > 1 else ""
    page = int(parts[2]) if len(parts) > 2 else 0

    text, markup = _build_roadmap_content(back_to=back_to, page=page)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)


# ------------------------------------------------------------------
# Inline callback — /where'den faz detayı (← Geri butonu ile)
# ------------------------------------------------------------------
async def callback_where_phase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    back_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("← /where", callback_data="where_back"),
    ]])
    await query.edit_message_text(
        format_phase_detail(phase),
        parse_mode="Markdown",
        reply_markup=back_markup,
    )


# ------------------------------------------------------------------
# Inline callback — /where ekranına geri dön
# ------------------------------------------------------------------
async def callback_where_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    text, markup = _build_where_content()
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=markup,
    )
