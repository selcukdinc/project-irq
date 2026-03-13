"""
Project IRQ — Proje Registry
Proje CRUD işlemleri. Veriler ~/.irq/projects.json'da saklanır.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .config import PROJECTS_FILE, ensure_irq_dirs

logger = logging.getLogger(__name__)


def _load_data() -> dict:
    """projects.json'ı oku; dosya yoksa boş yapı döndür."""
    ensure_irq_dirs()
    if not PROJECTS_FILE.exists():
        return {"projects": []}
    try:
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("projects.json okunamadı: %s", exc)
        return {"projects": []}


def _save_data(data: dict) -> None:
    """projects.json'a yaz."""
    ensure_irq_dirs()
    PROJECTS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def list_projects() -> list[dict]:
    """Kayıtlı tüm projeleri döndür."""
    return _load_data()["projects"]


def get_project(project_id: str) -> Optional[dict]:
    """ID'ye göre proje bul."""
    for p in list_projects():
        if p["id"] == project_id:
            return p
    return None


def get_active_project() -> Optional[dict]:
    """active=True olan projeyi döndür."""
    for p in list_projects():
        if p.get("active"):
            return p
    return None


def add_project(name: str, path: str, roadmap_path: str = "ROADMAP.md") -> dict:
    """Yeni proje ekle. ID, isimden türetilir (slug)."""
    project_id = name.lower().replace(" ", "-")
    data = _load_data()

    # Aynı ID varsa hata
    for p in data["projects"]:
        if p["id"] == project_id:
            raise ValueError(f"'{project_id}' ID'li proje zaten var.")

    # Path kontrolü
    proj_path = Path(path).expanduser().resolve()
    if not proj_path.is_dir():
        raise FileNotFoundError(f"Dizin bulunamadı: {proj_path}")

    project = {
        "id": project_id,
        "name": name,
        "path": str(proj_path),
        "roadmap_path": roadmap_path,
        "active": len(data["projects"]) == 0,  # ilk proje otomatik aktif
    }
    data["projects"].append(project)
    _save_data(data)
    logger.info("Proje eklendi: %s (%s)", name, proj_path)
    return project


def remove_project(project_id: str) -> bool:
    """Proje sil. Başarılıysa True döner."""
    data = _load_data()
    original_len = len(data["projects"])
    data["projects"] = [p for p in data["projects"] if p["id"] != project_id]

    if len(data["projects"]) == original_len:
        return False

    _save_data(data)
    logger.info("Proje silindi: %s", project_id)
    return True


def set_active_project(project_id: str) -> Optional[dict]:
    """Belirtilen projeyi aktif yap, diğerlerini pasif yap."""
    data = _load_data()
    found = None
    for p in data["projects"]:
        if p["id"] == project_id:
            p["active"] = True
            found = p
        else:
            p["active"] = False

    if found:
        _save_data(data)
        logger.info("Aktif proje değiştirildi: %s", project_id)
    return found
