# 🤖 Project IRQ

Telegram üzerinden Claude Code'a uzaktan komut veren, birden fazla projeyi yöneten,
faz ilerlemesini takip eden ve tamamlanan görevlerin özetini raporlayan
akıllı geliştirme asistanı.

**Bot:** [@reque_bot](https://t.me/reque_bot)

---

## ✨ Özellikler

### Mevcut (Faz 1)
- 🤖 Telegram bot — `/start`, `/status`, `/help`, `/ping`
- 🏠 Mac'te yerel çalışma — sunucu gereksiz, maliyet $0

### Planlanan
- 📂 **Çoklu Proje Yönetimi** — Telegram'dan proje seçimi, ROADMAP takibi
- 🖥️ **Uzaktan Claude Code** — Telegram'dan prompt gönder, Claude Code çalıştırsın
- 🔄 **Model Kontrolü** — Claude Code modelini Telegram'dan görme/değiştirme
- 📊 **Faz Bildirimleri** — tamamlanan görevlerin otomatik özet raporu
- 🔍 **Watchdog** — Claude Code log izleme, loop tespiti
- 💰 **Maliyet Kontrolü** — API harcama takibi ve limit

---

## 🏗️ Mimari

```
┌──────────────┐           ┌────────────────────────────┐
│   Telegram   │  Bot API  │  Mac (Senin Bilgisayarın)  │
│   @reque_bot │ ◄────────►│                            │
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
| `/projects` | Proje listesi *(Faz 2)* |
| `/roadmap` | Faz ilerleme durumu *(Faz 2)* |
| `/run <prompt>` | Claude Code'a prompt gönder *(Faz 3)* |
| `/model` | Model bilgisi/değiştir *(Faz 4)* |

---

## 📖 Dokümantasyon

- [ROADMAP.md](ROADMAP.md) — fazlar ve ilerleme durumu
- [CLAUDE.md](CLAUDE.md) — AI agent bağlam dosyası (mimari, kurallar, komutlar)

---

## 📜 Lisans

Özel proje — tüm hakları saklıdır.
