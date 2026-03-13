#!/usr/bin/env python3
"""
irq — Project IRQ Terminal CLI

Kullanım:
    irq init              # mevcut dizini sisteme kaydet
    irq init <path>       # belirli bir dizini kaydet
    irq init <path> -n "Proje Adı"

Bu araç bilgisayar başında, bir kere çalıştırılır.
Sonrasında her şey Telegram üzerinden uzaktan yönetilir.
"""

import argparse
import json
import sys
from pathlib import Path

IRQ_HOME = Path.home() / ".irq"
PROJECTS_FILE = IRQ_HOME / "projects.json"
LOGS_DIR = IRQ_HOME / "logs"


def _ensure_dirs() -> None:
    IRQ_HOME.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


def _load() -> dict:
    if PROJECTS_FILE.exists():
        try:
            return json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"projects": []}


def _save(data: dict) -> None:
    _ensure_dirs()
    PROJECTS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def cmd_init(args: argparse.Namespace) -> None:
    # Dizin belirle
    path = Path(args.path).expanduser().resolve() if args.path else Path.cwd()

    if not path.is_dir():
        print(f"❌  Dizin bulunamadı: {path}")
        sys.exit(1)

    # ROADMAP.md kontrolü
    roadmap = path / "ROADMAP.md"
    if not roadmap.exists():
        print(f"⚠️   ROADMAP.md bulunamadı: {path}")
        print("    Devam etmek için proje dizinine bir ROADMAP.md ekleyin.")
        sys.exit(1)

    # Proje adı ve ID
    name = args.name or path.name
    project_id = name.lower().replace(" ", "-")

    data = _load()

    # Zaten kayıtlı mı?
    for p in data["projects"]:
        if p["id"] == project_id:
            # Aktif olarak işaretle
            for q in data["projects"]:
                q["active"] = q["id"] == project_id
            _save(data)
            print(f"✅  '{name}' zaten kayıtlı — aktif proje olarak ayarlandı.")
            print(f"    Telegram'dan /where ile durumu görebilirsin.")
            return

    # Diğerlerini pasif yap
    for p in data["projects"]:
        p["active"] = False

    project = {
        "id": project_id,
        "name": name,
        "path": str(path),
        "roadmap_path": "ROADMAP.md",
        "active": True,
    }
    data["projects"].append(project)
    _save(data)

    print(f"✅  '{name}' sisteme eklendi ve aktif proje olarak ayarlandı.")
    print(f"    Yol    : {path}")
    print(f"    ID     : {project_id}")
    print(f"    Telegram'dan /where ile durumu görebilirsin.")


def cmd_list(_args: argparse.Namespace) -> None:
    data = _load()
    projects = data.get("projects", [])
    if not projects:
        print("Kayıtlı proje yok. `irq init` ile proje ekle.")
        return
    print(f"{'ID':<20} {'Ad':<25} Aktif  Yol")
    print("-" * 80)
    for p in projects:
        active = "✅" if p.get("active") else "  "
        print(f"{p['id']:<20} {p['name']:<25} {active}     {p['path']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="irq",
        description="IRQ — Telegram Claude Code asistanı CLI",
    )
    sub = parser.add_subparsers(dest="command", metavar="<komut>")

    # irq init
    init_p = sub.add_parser("init", help="Projeyi IRQ sistemine kaydet")
    init_p.add_argument(
        "path",
        nargs="?",
        help="Proje dizini (varsayılan: mevcut dizin)",
    )
    init_p.add_argument(
        "--name", "-n",
        help="Proje adı (varsayılan: dizin adı)",
    )

    # irq list
    sub.add_parser("list", help="Kayıtlı projeleri listele")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
