# ROADMAP.md — Project IRQ

> **Okuma talimatı (Claude Code için):** Bu dosyayı her oturumda oku.
> `[ ]` = yapılmadı, `[x]` = tamamlandı. Sıradaki `[ ]`'den başla.
>
> **Proje vizyonu:** Telegram üzerinden Claude Code'a uzaktan komut veren,
> çoklu proje yöneten, faz ilerlemesini takip eden akıllı geliştirme asistanı.
>
> **Mimari:** Sunucusuz — her şey Mac'te çalışır, Telegram Bot API doğrudan kullanılır.

---

## Faz 0 — Proje Altyapısı

> Hedef: Proje iskeletinin hazır olması, bot tokenlarının ayarlanması.

- [x] Proje ismi belirlendi: **Project IRQ**
- [x] Bot kullanıcı adı alındı: `@reque_bot`
- [x] Klasör yapısı tasarlandı
- [x] `.env.example` oluşturuldu
- [x] `.gitignore` oluşturuldu
- [x] `.claudeignore` oluşturuldu
- [x] GitHub repo oluşturuldu ve ilk commit atıldı
- [x] `README.md` temel bilgilerle dolduruldu
- [x] `CLAUDE.md` proje bağlamı yazıldı

---

## Faz 1 — Minimal Telegram Bot (Yerel)

> Hedef: Bot Mac'te ayakta, Telegram komutlarına cevap veriyor.

- [x] `python-telegram-bot==20.7` seçildi
- [x] `bot/main.py` yazıldı (async polling)
- [x] `/start`, `/status`, `/help`, `/ping` komutları eklendi
- [x] `.env` şablonu hazırlandı
- [x] Python venv oluşturuldu: `python -m venv .venv`
- [x] Bağımlılıklar kuruldu: `pip install -r bot/requirements.txt`
- [x] `.env` dosyası oluşturuldu, token ve chat ID yazıldı
- [x] Bot local olarak test edildi: `python bot/main.py`
- [x] `/start` komutu çalıştı, Chat ID alındı
- [x] `ADMIN_CHAT_ID` `.env`'e yazıldı
- [x] Bot'a BotFather üzerinden komut listesi eklendi (`/setcommands`)
- [x] Handler'lar `bot/handlers/commands.py`'de (modüler yapı) ✔️ zaten orada

---

## Faz 2 — Proje Registry & Yönetim Sistemi

> Hedef: Birden fazla projeyi Telegram'dan yönetebilme,
> ROADMAP bazlı faz ilerlemesini takip edebilme.

### 2A — Proje Registry
- [ ] `~/.irq/projects.json` konfigürasyon formatı tasarlandı:
  ```json
  {
    "projects": [
      {
        "id": "project-irq",
        "name": "Project IRQ",
        "path": "/Users/selcukdinc/Projects/project-irq",
        "roadmap_path": "ROADMAP.md",
        "active": true
      }
    ]
  }
  ```
- [ ] `bot/core/project_registry.py` yazıldı — proje CRUD işlemleri
- [ ] Telegram'dan `/projects` komutu: kayıtlı projeleri inline butonlarla listele
- [ ] Telegram'dan `/addproject <isim> <path>` komutu: yeni proje kaydet
- [ ] Telegram'dan `/removeproject <id>` komutu: proje sil

### 2B — ROADMAP Parser
- [ ] `bot/core/roadmap_parser.py` yazıldı:
  - Markdown ROADMAP.md'yi parse et
  - Faz isimlerini, adımları ve `[ ]`/`[x]` durumlarını çıkar
  - İlerleme yüzdesini hesapla
- [ ] Telegram'dan `/roadmap` komutu: seçili projenin faz durumunu göster
- [ ] Her faz için inline butonlar: `📊 Detay`, `▶️ İlerlet`
- [ ] `/phase <faz_no>` komutu: belirli fazın detaylarını göster

### 2C — Proje Seçim Akışı
- [ ] Telegram inline butonlarla proje seçim menüsü
- [ ] Seçili proje oturumda aktif olarak tutulur (conversation state)
- [ ] `/current` komutu: şu an hangi proje aktif göster
- [ ] Her komut çalışmadan önce aktif proje kontrolü yapılır

---

## Faz 3 — Claude Code Entegrasyonu

> Hedef: Telegram'dan Claude Code CLI'a prompt göndermek,
> sonuçları geri almak. Her şey Mac'te, aynı process'te.

### 3A — Claude Code CLI Runner
- [ ] Claude Code CLI komut yapısı belirlendi:
  - `claude --model <model> --project <path> --prompt "<prompt>"`
  - Antigravity context'i ile çalışma şekli doğrulandı
- [ ] `bot/core/claude_runner.py` yazıldı:
  - CLI'ı `asyncio.create_subprocess_exec` ile çalıştır
  - stdout/stderr'ı async yakala
  - Timeout ve hata yönetimi
- [ ] Telegram'dan `/run <prompt>` komutu:
  - Aktif projeye Claude Code prompt'u gönder
  - "⏳ Çalışıyor..." mesajı göster
  - Tamamlanınca sonucu gönder
- [ ] Uzun çalışan işlemler için ilerleme bildirimi (mesaj güncelleme)

### 3B — Güvenlik & Kontrol
- [ ] Sadece `ADMIN_CHAT_ID`'den gelen komutlar kabul edilir
- [ ] Hassas komutlar için onay mekanizması (inline butonlarla Evet/Hayır)
- [ ] Rate limiting: dakikada max 5 Claude Code komutu
- [ ] Çalışan komutu iptal etme: `/cancel` komutu
- [ ] Eşzamanlı çalışma koruması: aynı anda sadece 1 prompt

---

## Faz 4 — Claude Code Model Kontrolü

> Hedef: Telegram'dan Claude Code'un hangi modeli kullandığını görebilme
> ve değiştirebilme.

- [ ] Claude Code desteklenen modeller listesi alınıyor
  - claude-sonnet-4-20250514
  - claude-opus-4-20250514
  - claude-3.5-haiku
  - (ve diğer güncel modeller)
- [ ] `/model` komutu: şu an aktif modeli göster
- [ ] `/model <model_adı>` komutu: modeli değiştir
- [ ] Model değişikliği inline butonlarla (liste halinde seçim)
- [ ] Model bilgisi `~/.irq/config.json`'da saklanır
- [ ] Model limitleri ve maliyetleri hakkında bilgi gösterme

---

## Faz 5 — Faz Tamamlama Bildirimleri

> Hedef: Claude Code bir faz/görev tamamladığında, neler yaptığının özetini
> otomatik olarak Telegram'a gönderme.

### 5A — Çıktı Yakalama
- [ ] Claude Code çıktısı (stdout) real-time olarak yakalanıyor
- [ ] Çıktı buffer'lanıyor ve log dosyasına yazılıyor (`~/.irq/logs/`)
- [ ] Faz tamamlama sinyali tespit ediliyor (çıktı parse)

### 5B — Özet Oluşturma
- [ ] Claude Code'un son mesajı (faz bitti mesajı) yakalanıyor
- [ ] Özet formatı belirlendi:
  ```
  ✅ Faz Tamamlandı!
  
  📂 Proje: project-irq
  🎯 Faz: 3 — Claude Code Entegrasyonu
  ⏱️ Süre: 12dk
  
  📝 Özet:
  - claude_runner.py oluşturuldu
  - /run komutu eklendi
  - 3 test yazıldı, hepsi geçti
  
  📊 ROADMAP İlerlemesi: %45 → %52
  ```
- [ ] ROADMAP.md otomatik güncelleniyor (`[ ]` → `[x]`)

### 5C — Bildirim Gönderme
- [ ] Telegram mesajı formatlanıp gönderiliyor
- [ ] Hata durumunda farklı format: ❌ ile birlikte hata detayı
- [ ] `/history` komutu: son N tamamlanan görevin listesi

---

## Faz 6 — Watchdog Engine (Log İzleme)

> Hedef: Claude Code çalışırken logları izle, loop tespiti yap, bildirim gönder.

### 6A — Log İzleme
- [ ] Claude Code çıktısı real-time izleniyor
- [ ] Log dosyası `~/.irq/logs/` altında tutuluyor
- [ ] `bot/core/log_watcher.py` yazıldı (async tail mantığı)

### 6B — Loop Tespiti
- [ ] Loop kriterleri tanımlandı:
  - Aynı hata mesajı **3+ kez** tekrarlanırsa
  - **5 dakika** boyunca yeni çıktı yoksa
  - Çıktı dosyası boyutu **10MB**'ı aşarsa
- [ ] `bot/handlers/watchdog.py` yazıldı
- [ ] Loop tespit edilince Telegram mesajı gidiyor
- [ ] Mesajda **Devam Et / Atla / Durdur** inline butonları var

### 6C — Süreç Kontrolü
- [ ] `/pause` komutu: çalışan Claude Code process'ini durdurur (SIGSTOP)
- [ ] `/resume` komutu: devam ettirir (SIGCONT)
- [ ] `/kill` komutu: process'i sonlandırır
- [ ] Inline buton callback'leri çalışıyor

---

## Faz 7 — Maliyet Kontrolü

> Hedef: Claude Code API maliyetlerini takip et, limiti aşınca uyar.

- [ ] Maliyet takip yöntemi kararlaştırıldı:
  - Option A: Claude Code CLI çıktısından token/maliyet parse
  - Option B: Claude API yanıtlarından log dosyası
- [ ] `bot/core/cost_tracker.py` yazıldı
- [ ] `COST_LIMIT_USD` env değişkeni aktif, aşılınca uyarı gidiyor
- [ ] `/budget` komutu: günlük limit göster / değiştir
- [ ] `/cost` komutu: o güne ait harcama özeti
- [ ] Günlük maliyet raporu otomatik gönderiliyor
- [ ] Limit aşılınca Claude Code otomatik durdurulur, onay beklenir

---

## Faz 8 — Çok Kullanıcı & SaaS Altyapısı

> Hedef: Arkadaşlara özel alan, kullanıcı bazlı bot.
> Not: Bu fazda sunucu ihtiyacı tekrar değerlendirilecek.

### 8A — Kullanıcı Sistemi
- [ ] SQLite veritabanı eklendi
- [ ] `users` tablosu: `chat_id`, `username`, `plan`, `created_at`
- [ ] Admin (`ADMIN_CHAT_ID`) özel yetkiler alabiliyor
- [ ] `/invite <kullanici_adi>` komutu: belirli kişilere erişim ver

### 8B — Kullanıcı Bazlı İzolasyon
- [ ] Her kullanıcı sadece kendi projelerini görüyor
- [ ] Admin tüm kullanıcıların özetini görebiliyor: `/admin overview`

### 8C — Güvenlik
- [ ] Kayıtlı olmayan kullanıcıların komutları reddediliyor
- [ ] Rate limiting: kullanıcı başına dakikada max 10 mesaj

---

## Faz 9 — IRQ Admin (Flutter Mobil)

> Hedef: Telegram bot'un yaptığı her şeyi yapan, daha zengin arayüzlü mobil uygulama.
> Not: Bu fazda backend API sunucusu gerekecek.

### 9A — Backend API
- [ ] FastAPI servisi eklendi
- [ ] JWT tabanlı kimlik doğrulama
- [ ] Endpoints: `/projects`, `/run`, `/model`, `/costs`

### 9B — Flutter Uygulaması
- [ ] Flutter projesi oluşturuldu: `mobile/irq_admin/`
- [ ] API client yazıldı
- [ ] Ekranlar: Dashboard, Proje detay, Model yönetimi, Bütçe
- [ ] Push notification (Firebase FCM)

### 9C — Yayın
- [ ] TestFlight / Internal Test yayınlandı

---

## Teknik Borç & Genel İyileştirmeler

> Faz bağımsız, uygun zamanda yapılacaklar.

- [ ] Tüm handler'lar için unit test yazıldı (`tests/` klasörü)
- [ ] `Makefile` eklendi (sık komutlar için kısayollar)
- [ ] `~/.irq/logs/` otomatik rotasyon (boyut limiti)
- [ ] Bot'u `launchd` ile otomatik başlatma (Mac daemon)
- [ ] Otomatik yedekleme: `~/.irq/` günlük backup

---

## Versiyon Geçmişi

| Versiyon | Faz | Tarih | Notlar |
|----------|-----|-------|--------|
| v0.1.0 | Faz 0-1 | Mart 2026 | İlk çalışan bot (yerel) |
| v0.2.0 | Faz 2 | — | Proje registry & yönetim |
| v0.3.0 | Faz 3 | — | Claude Code entegrasyonu |
| v0.4.0 | Faz 4 | — | Model kontrolü |
| v0.5.0 | Faz 5 | — | Faz tamamlama bildirimleri |
| v0.6.0 | Faz 6 | — | Watchdog engine |
| v0.7.0 | Faz 7 | — | Maliyet kontrolü |
| v1.0.0 | Faz 8 | — | Çok kullanıcı |
| v2.0.0 | Faz 9 | — | Flutter mobil |
