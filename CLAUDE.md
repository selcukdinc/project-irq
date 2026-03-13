# CLAUDE.md — Project IRQ

> Bu dosya Claude Code ve diğer AI agent'lar için bağlam dosyasıdır.
> Her oturuma başlamadan önce oku.

## Proje Özeti

**Project IRQ** — Telegram üzerinden Claude Code'a uzaktan komut veren,
birden fazla projeyi yöneten, faz ilerlemesini takip eden ve tamamlanan
görevlerin özetini raporlayan akıllı geliştirme asistanı sistemidir.

- **Bot:** `@ireq_bot` (Telegram)
- **Çalışma ortamı:** Mac (yerel) — sunucu yok
- **Gelecek:** IRQ Admin (Flutter mobil uygulama)
- **Hedef:** Tek kullanıcıdan çok kullanıcıya ölçeklenebilir SaaS

---

## Oturum Başlangıç Ritüeli

```
ROADMAP.md'yi oku → mevcut fazı belirle → sıradaki tamamlanmamış adımı yap
```

ROADMAP.md'de her adımın başında `[ ]` veya `[x]` işareti var.
Tamamlanan adımları `[x]` olarak işaretle.

---

## Mimari Genel Bakış

> **Sunucusuz mimari:** Her şey Mac'te çalışır.
> Telegram Bot API'ye doğrudan bağlanır (polling), sunucu gereksiz.

```
┌──────────────┐           ┌──────────────────────────────────────┐
│   Telegram   │  Bot API  │  Mac (Geliştirme Makinesi)           │
│   @ireq_bot  │ ◄────────►│                                      │
│   (Bulut)    │  polling   │  bot/main.py ─── entry point         │
└──────────────┘           │  ├── handlers/                        │
       ▲                   │  │   ├── commands.py     /start etc.  │
       │                   │  │   ├── projects.py     /projects    │
  Telegram                 │  │   ├── claude_cmds.py  /run /model  │
  Kullanıcısı              │  │   └── watchdog.py     loop tespiti │
                           │  └── core/                            │
                           │      ├── config.py       env, sabitler│
                           │      ├── project_registry.py  CRUD    │
                           │      ├── roadmap_parser.py    parser  │
                           │      ├── claude_runner.py  CLI runner │
                           │      ├── model_manager.py  model ctrl │
                           │      ├── cost_tracker.py   maliyet    │
                           │      └── notifier.py       bildirim   │
                           │                                       │
                           │  ~/.irq/                              │
                           │  ├── projects.json    kayıtlı projeler│
                           │  ├── config.json      genel ayarlar   │
                           │  └── logs/            çalışma logları │
                           │                                       │
                           │  ~/Projects/          proje dizinleri │
                           │  ├── project-irq/                     │
                           │  ├── project-xyz/                     │
                           │  └── ...                              │
                           └───────────────────────────────────────┘
```

---

## Teknoloji Stack

| Katman | Teknoloji | Neden |
|---|---|---|
| Bot framework | python-telegram-bot v20+ | Async, olgun, aktif |
| Runtime | Python 3.11+ | Hafif, stabil |
| Claude Code | CLI / Antigravity Extension | Uzaktan prompt yürütme |
| Proje config | JSON (`~/.irq/`) | Basit, human-readable |
| Süreç yönetimi | asyncio subprocess | Claude CLI entegrasyonu |
| Mobil (Faz 9) | Flutter | Tek codebase iOS+Android |

---

## Ortam Değişkenleri

`.env` dosyası (git'e **gitmiyor**), `.env.example` referans olarak repoda var.

```env
# Telegram
TELEGRAM_TOKEN=          # BotFather'dan
ADMIN_CHAT_ID=           # /start çalıştırınca öğrenilir

# Genel
ENV=dev                  # dev | prod
LOG_LEVEL=INFO           # DEBUG | INFO | WARNING

# Claude Code (Faz 4)
CLAUDE_MODEL=claude-sonnet-4-20250514   # Varsayılan model
CLAUDE_TIMEOUT=300       # Saniye, max çalışma süresi

# Maliyet (Faz 7)
COST_LIMIT_USD=5.0       # Günlük maliyet limiti
```

---

## Geliştirme Kuralları

### Kod Stili
- Python: PEP8, type hints tercih edilir
- Async/await: tüm handler'lar async olmalı
- Loglama: `logger = logging.getLogger(__name__)` her dosyada
- Exception'lar sessizce yutulmamalı, her zaman loglanmalı

### Handler Ekleme Kalıbı
```python
# bot/handlers/yeni_modul.py içine yeni komut eklerken:
async def cmd_yenikomut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("...", parse_mode="Markdown")

# main.py'daki register_handlers() içine:
app.add_handler(CommandHandler("yenikomut", cmd_yenikomut))
```

### Claude Code Runner Kuralları (Faz 3+)
- Claude Code CLI subprocess ile çalıştırılır (`asyncio.create_subprocess_exec`)
- stdout ve stderr ayrı ayrı pipe edilir
- Timeout: varsayılan 5 dakika, `.env` ile değiştirilebilir
- Aynı anda sadece 1 Claude Code process'i çalışır
- Process PID takip edilir (cancel/kill için)

### Git Commit Kuralları
```
feat: yeni özellik
fix: hata düzeltme
chore: bağımlılık, config değişikliği
docs: sadece dokümantasyon
```

---

## Çalıştırma

```bash
# Venv oluştur (bir kere)
cd ~/Projects/project-irq
python -m venv .venv
source .venv/bin/activate
pip install -r bot/requirements.txt

# .env oluştur (bir kere)
cp .env.example .env
# Token ve Chat ID'yi yaz

# Bot'u başlat
python bot/main.py

# Arka planda çalıştır (opsiyonel)
nohup python bot/main.py &
# veya launchd ile daemon olarak (Teknik Borç'ta)
```

---

## Faz Durumu

Güncel durum için `ROADMAP.md`'ye bak.

| Faz | Başlık | Durum |
|-----|--------|-------|
| 0 | Proje Altyapısı | ✅ Tamamlandı |
| 1 | Minimal Telegram Bot | 🔄 Devam ediyor |
| 2 | Proje Registry & Yönetim | ⏳ Bekliyor |
| 3 | Claude Code Entegrasyonu | ⏳ Bekliyor |
| 4 | Model Kontrolü | ⏳ Bekliyor |
| 5 | Faz Tamamlama Bildirimleri | ⏳ Bekliyor |
| 6 | Watchdog Engine | ⏳ Bekliyor |
| 7 | Maliyet Kontrolü | ⏳ Bekliyor |
| 8 | Çok Kullanıcı & SaaS | ⏳ Bekliyor |
| 9 | Flutter Mobil | ⏳ Bekliyor |

---

## Telegram Bot Komutları (Mevcut + Planlanan)

| Komut | Faz | Açıklama |
|-------|-----|----------|
| `/start` | 1 | Bot başlat, Chat ID öğren |
| `/status` | 1 | Sistem durumu |
| `/help` | 1 | Komut listesi |
| `/ping` | 1 | Bot canlı mı? |
| `/projects` | 2 | Proje listesi (inline butonlar) |
| `/addproject` | 2 | Yeni proje kaydet |
| `/roadmap` | 2 | Aktif projenin faz durumu |
| `/current` | 2 | Aktif proje göster |
| `/run <prompt>` | 3 | Claude Code'a prompt gönder |
| `/cancel` | 3 | Çalışan komutu iptal et |
| `/model` | 4 | Model bilgisi / değiştir |
| `/history` | 5 | Tamamlanan görevler |
| `/pause` | 6 | Claude Code durdur |
| `/resume` | 6 | Devam ettir |
| `/budget` | 7 | Maliyet limiti |
| `/cost` | 7 | Harcama özeti |

---

## Dosya Yapısı

```
project-irq/
├── bot/
│   ├── main.py              — entry point, polling başlatır
│   ├── requirements.txt     — Python bağımlılıkları
│   ├── handlers/            — Telegram komut handler'ları
│   │   ├── __init__.py
│   │   ├── commands.py      — /start, /status, /help, /ping
│   │   ├── projects.py      — /projects, /addproject (Faz 2)
│   │   ├── claude_cmds.py   — /run, /model, /cancel (Faz 3-4)
│   │   └── watchdog.py      — loop tespiti (Faz 6)
│   └── core/                — iş mantığı modülleri
│       ├── __init__.py
│       ├── config.py        — env değişkenleri, sabitler
│       ├── project_registry.py — proje CRUD (Faz 2)
│       ├── roadmap_parser.py   — ROADMAP.md parser (Faz 2)
│       ├── claude_runner.py    — Claude Code CLI wrapper (Faz 3)
│       ├── model_manager.py    — model bilgisi/değiştir (Faz 4)
│       ├── notifier.py         — bildirim gönderici (Faz 5)
│       ├── cost_tracker.py     — maliyet takibi (Faz 7)
│       └── log_watcher.py      — log izleme (Faz 6)
├── docs/                    — ek dokümantasyon
├── .env.example             — ortam değişkenleri şablonu
├── .gitignore
├── .claudeignore
├── CLAUDE.md                — bu dosya (AI agent bağlamı)
├── ROADMAP.md               — fazlar ve ilerleme
└── README.md                — proje tanıtımı
```

---

## Bilinen Kısıtlamalar

- Mac kapalıysa bot çalışmaz (tasarım gereği — "bilgisayar aktifse" mantığı)
- Webhook modu yok, polling kullanılıyor (yeterli, sunucu yok çünkü)
- SQLite henüz yok (Faz 8'de gerekecek)
- Çok kullanıcı modunda sunucu ihtiyacı tekrar değerlendirilecek (Faz 8)
