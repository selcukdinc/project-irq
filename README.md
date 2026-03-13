# 🤖 Project IRQ

Telegram üzerinden Claude Code'a uzaktan komut veren, birden fazla projeyi yöneten,
faz ilerlemesini takip eden ve tamamlanan görevlerin özetini raporlayan
akıllı geliştirme asistanı.

**Bot:** [@ireque_bot](https://t.me/reque_bot)

---

## ✨ Özellikler

### ✅ Mevcut (Faz 1–4)
- 🤖 Telegram bot — `/start`, `/status`, `/help`, `/ping`
- 🏠 Mac'te yerel çalışma — sunucu gereksiz, maliyet $0
- 📂 **Çoklu Proje Yönetimi** — Telegram'dan proje seçimi, ROADMAP takibi (`/projects`, `/addproject`, `/roadmap`, `/phase`, `/current`)
- 🖥️ **Uzaktan Claude Code** — Telegram'dan prompt gönder, sonucu al (`/run`, `/cancel`)
- 🔐 **Güvenlik & Kontrol** — admin doğrulama, hassas komut onayı, rate limiting
- 🔄 **Model Kontrolü** — Claude Code modelini Telegram'dan görme/değiştirme (`/model`)

### ⏳ Planlanan
- 📊 **Faz Bildirimleri** — tamamlanan görevlerin otomatik özet raporu
- 🔍 **Watchdog** — Claude Code log izleme, loop tespiti, `/pause` `/resume`
- 💰 **Maliyet Kontrolü** — API harcama takibi ve limit, `/budget` `/cost`
- 👥 **Çok Kullanıcı** — SQLite, kullanıcı bazlı izolasyon
- 📱 **Flutter Mobil** — IRQ Admin uygulaması

---

## 🏗️ Mimari

```
┌──────────────┐           ┌────────────────────────────┐
│   Telegram   │  Bot API  │  Mac (Senin Bilgisayarın)  │
│   @ireque_bot │ ◄────────►│                            │
│   (Bulut)    │  polling   │  IRQ Bot                   │
└──────────────┘           │  ├── Telegram handler'lar   │
       ▲                   │  ├── Claude Code CLI runner │
       │                   │  ├── Proje registry         │
   Telegram                │  ├── ROADMAP parser         │
   Kullanıcısı             │  └── Model manager          │
                           │                             │
                           │  ~/Projects/                │
                           │  ├── project-irq/           │
                           │  ├── project-xyz/           │
                           │  └── ...                    │
                           └─────────────────────────────┘
```

> **Sunucu yok** — her şey yerel Mac'te çalışır.
> Mac açıkken Telegram'dan komut verirsin, Claude Code çalışır.

---

## 🚀 Hızlı Başlangıç

```bash
# 1. Repoyu klonla
git clone https://github.com/KULLANICI/project-irq.git
cd project-irq

# 2. Venv oluştur
python -m venv .venv
source .venv/bin/activate
pip install -r bot/requirements.txt

# 3. .env oluştur
cp .env.example .env
# Token ve Chat ID'yi yaz

# 4. Bot'u başlat
python bot/main.py
```

---

## ⚙️ Gereksinimler

- Python 3.11+
- Telegram bot token (@BotFather)
- Claude Code CLI (Faz 3+, Antigravity extension)

---

## 📋 Telegram Bot Komutları

| Komut | Açıklama |
|-------|----------|
| `/start` | Bot başlat, Chat ID öğren |
| `/status` | Sistem durumu |
| `/help` | Komut listesi |
| `/ping` | Bot canlı mı kontrolü |
| `/projects` | Proje listesi (inline seçim) |
| `/addproject <isim> <path>` | Yeni proje kaydet |
| `/removeproject <id>` | Proje sil |
| `/current` | Aktif proje göster |
| `/roadmap` | Faz ilerleme durumu |
| `/phase <no>` | Belirli faz detayı |
| `/run <prompt>` | Claude Code'a prompt gönder |
| `/cancel` | Çalışan komutu iptal et |
| `/model` | Aktif modeli göster + inline seçim |
| `/model <model_adı>` | Modeli değiştir |

---

## 📖 Dokümantasyon

- [ROADMAP.md](ROADMAP.md) — fazlar ve ilerleme durumu
- [CLAUDE.md](CLAUDE.md) — AI agent bağlam dosyası (mimari, kurallar, komutlar)

---

## 📜 Lisans

Özel proje — tüm hakları saklıdır.
