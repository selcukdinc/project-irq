# 🤖 Project IRQ

Telegram üzerinden Claude Code'a uzaktan komut veren, birden fazla projeyi yöneten,
faz ilerlemesini takip eden ve tamamlanan görevlerin özetini raporlayan
akıllı geliştirme asistanı.

**Bot:** [@ireque_bot](https://t.me/ireque_bot)

---

## ✨ Özellikler

### ✅ Mevcut (Faz 1–5 + 2D)
- 🤖 Telegram bot — `/start`, `/status`, `/help`, `/ping`
- 🏠 Mac'te yerel çalışma — sunucu gereksiz, maliyet $0
- 📂 **Çoklu Proje Yönetimi** — `irq init` ile kayıt, inline butonlarla seçim
- 📍 **Bağlam Komutları** — `/where` (neredeyim?), `/overview` (tüm projeler)
- 🗺 **ROADMAP Takibi** — faz ilerleme çubuğu, detay, inline navigasyon (← Geri)
- 🖥️ **Uzaktan Claude Code** — Telegram'dan prompt gönder, sonucu al (`/run`, `/cancel`)
- 🔐 **Güvenlik & Kontrol** — admin doğrulama, hassas komut onayı, rate limiting
- 🔄 **Model Kontrolü** — Sonnet / Opus / Haiku seçimi inline butonlarla (`/model`)
- 📋 **Çalıştırma Geçmişi** — her `/run` kalıcı loglanır, `/history` ile listele

### ⏳ Planlanan
- 🔍 **Watchdog** — Claude Code log izleme, loop tespiti, `/pause` `/resume`
- 🏠 **Command Center** — `/menu` ile tek panelden tüm kontrol
- 💰 **Maliyet Kontrolü** — API harcama takibi, `/budget` `/cost`
- 👥 **Çok Kullanıcı** — SQLite, kullanıcı bazlı izolasyon
- 📱 **Flutter Mobil** — IRQ Admin uygulaması

---

## 🏗️ Mimari

```
┌──────────────┐           ┌────────────────────────────┐
│   Telegram   │  Bot API  │  Mac (Senin Bilgisayarın)  │
│   @ireque_bot │ ◄────────►│                            │
│   (Bulut)    │  polling   │  IRQ Bot (Python)          │
└──────────────┘           │  ├── Telegram handler'lar   │
       ▲                   │  ├── Claude Code CLI runner │
       │                   │  ├── Proje registry         │
   Telegram                │  ├── ROADMAP parser         │
   Kullanıcısı             │  ├── Model manager          │
                           │  └── Notifier (history)     │
                           │                             │
                           │  irq CLI (terminal)         │
                           │  └── irq init <path>        │
                           │                             │
                           │  ~/Projects/                │
                           │  ├── project-irq/  ← aktif  │
                           │  ├── project-xyz/           │
                           │  └── ...                    │
                           └─────────────────────────────┘
```

> **Sunucu yok** — her şey yerel Mac'te çalışır.
> Bilgisayar açıkken Telegram'dan komut verirsin, Claude Code çalışır.

---

## 🚀 Hızlı Başlangıç

```bash
# 1. Repoyu klonla
git clone https://github.com/selcukdinc/project-irq.git
cd project-irq

# 2. Venv oluştur
python -m venv .venv
source .venv/bin/activate
pip install -r bot/requirements.txt

# 3. .env oluştur
cp .env.example .env
# TELEGRAM_TOKEN ve ADMIN_CHAT_ID'yi yaz

# 4. Projeyi sisteme kaydet
python bot/cli.py init          # mevcut dizin
python bot/cli.py list          # kayıtlı projeleri gör

# 5. Bot'u başlat
python bot/main.py
```

Telegram'dan `/where` yazarak başla.

---

## ⚙️ Gereksinimler

- Python 3.11+
- Telegram bot token ([@BotFather](https://t.me/BotFather))
- [Claude Code CLI](https://claude.ai/code) (`/run` komutu için)

---

## 📋 Telegram Bot Komutları

### Bağlam & Navigasyon
| Komut | Açıklama |
|-------|----------|
| `/where` | Aktif proje + mevcut faz + sıradaki adım |
| `/overview` | Tüm projelerin ilerleme özeti |

### Proje Yönetimi
| Komut | Açıklama |
|-------|----------|
| `/projects` | Proje listesi + inline seçim |
| `/current` | Aktif proje göster |
| `/roadmap` | Faz ilerleme durumu |
| `/phase <no>` | Belirli fazın detayı |
| `/addproject <isim> <path>` | Proje kaydet (terminal'de `irq init` tercih edilir) |
| `/removeproject <id>` | Proje sil |

### Claude Code
| Komut | Açıklama |
|-------|----------|
| `/run <prompt>` | Claude Code'a prompt gönder |
| `/cancel` | Çalışan komutu iptal et |
| `/model` | Aktif modeli göster + inline değiştir |
| `/history [n]` | Son N çalıştırmanın listesi (varsayılan: 10) |

### Sistem
| Komut | Açıklama |
|-------|----------|
| `/start` | Bot başlat, Chat ID öğren |
| `/status` | Sistem durumu |
| `/help` | Komut listesi |
| `/ping` | Bot canlı mı? |

### Terminal CLI (`irq`)
| Komut | Açıklama |
|-------|----------|
| `python bot/cli.py init` | Mevcut projeyi sisteme kaydet |
| `python bot/cli.py init <path>` | Başka projeyi kaydet |
| `python bot/cli.py list` | Kayıtlı projeleri listele |

---

## 📖 Dokümantasyon

- [ROADMAP.md](ROADMAP.md) — fazlar ve ilerleme durumu
- [CLAUDE.md](CLAUDE.md) — AI agent bağlam dosyası (mimari, kurallar, komutlar)

---

## 📜 Lisans

Özel proje — tüm hakları saklıdır.
