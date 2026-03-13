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
- [x] Bot kullanıcı adı alındı: `@ireque_bot`
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
- [x] `~/.irq/projects.json` konfigürasyon formatı tasarlandı:
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
- [x] `bot/core/project_registry.py` yazıldı — proje CRUD işlemleri
- [x] Telegram'dan `/projects` komutu: kayıtlı projeleri inline butonlarla listele
- [x] Telegram'dan `/addproject <isim> <path>` komutu: yeni proje kaydet
- [x] Telegram'dan `/removeproject <id>` komutu: proje sil

### 2B — ROADMAP Parser
- [x] `bot/core/roadmap_parser.py` yazıldı:
  - Markdown ROADMAP.md'yi parse et
  - Faz isimlerini, adımları ve `[ ]`/`[x]` durumlarını çıkar
  - İlerleme yüzdesini hesapla
- [x] Telegram'dan `/roadmap` komutu: seçili projenin faz durumunu göster
- [x] Her faz için inline butonlar: `📊 Detay`, `▶️ İlerlet`
- [x] `/phase <faz_no>` komutu: belirli fazın detaylarını göster

### 2C — Proje Seçim Akışı
- [x] Telegram inline butonlarla proje seçim menüsü
- [x] Seçili proje oturumda aktif olarak tutulur (conversation state)
- [x] `/current` komutu: şu an hangi proje aktif göster
- [x] Her komut çalışmadan önce aktif proje kontrolü yapılır

### 2D — CLI Onboarding & Bağlam Komutları

> Hedef: Kullanıcı bilgisayar başındayken projeyi terminalde bir komutla sisteme kaydeder,
> sonrasında her şey Telegram üzerinden uzaktan yönetilir.
>
> **Kurulum / Uzaktan Kontrol ayrımı:**
> - `irq init` → terminalde, bir kere, bilgisayar başında
> - `/where`, `/overview` → Telegram'dan, her zaman, her yerden

- [x] `bot/cli.py` yazıldı — `irq init [path]` terminal komutu:
  - Mevcut dizini otomatik algılar (argümansız kullanım)
  - ROADMAP.md varlığını kontrol eder
  - `~/.irq/projects.json`'a ekler, aktif proje olarak ayarlar
  - Zaten kayıtlıysa aktif olarak işaretler
- [x] Aktif proje kalıcılığı: `active` flag `projects.json`'da saklandığı için
  bot yeniden başlayınca da korunuyor (zaten doğru çalışıyor)
- [x] `/where` komutu: hızlı bağlam özeti
  - Aktif proje adı, genel ilerleme çubuğu, mevcut faz, sıradaki adım
- [x] `/overview` komutu: tüm kayıtlı projelerin tek mesajda özeti
  - Her proje için ilerleme çubuğu + mevcut faz + inline proje seçim butonları

---

## Faz 3 — Claude Code Entegrasyonu

> Hedef: Telegram'dan Claude Code CLI'a prompt göndermek,
> sonuçları geri almak. Her şey Mac'te, aynı process'te.

### 3A — Claude Code CLI Runner
- [x] Claude Code CLI komut yapısı belirlendi:
  - `claude -p "<prompt>" --model <model> --add-dir <path>`
  - Non-interactive mode (`-p` flag) ile çalışma doğrulandı
- [x] `bot/core/claude_runner.py` yazıldı:
  - CLI'ı `asyncio.create_subprocess_exec` ile çalıştır
  - stdout/stderr'ı async yakala
  - Timeout ve hata yönetimi
- [x] Telegram'dan `/run <prompt>` komutu:
  - Aktif projeye Claude Code prompt'u gönder
  - "⏳ Çalışıyor..." mesajı göster
  - Tamamlanınca sonucu gönder
- [x] Uzun çalışan işlemler için ilerleme bildirimi (mesaj güncelleme)

### 3B — Güvenlik & Kontrol
- [x] Sadece `ADMIN_CHAT_ID`'den gelen komutlar kabul edilir
- [x] Hassas komutlar için onay mekanizması (inline butonlarla Evet/Hayır)
- [x] Rate limiting: dakikada max 5 Claude Code komutu
- [x] Çalışan komutu iptal etme: `/cancel` komutu
- [x] Eşzamanlı çalışma koruması: aynı anda sadece 1 prompt

---

## Faz 4 — Claude Code Model Kontrolü

> Hedef: Telegram'dan Claude Code'un hangi modeli kullandığını görebilme
> ve değiştirebilme.

- [x] Claude Code desteklenen modeller listesi alınıyor
  - claude-sonnet-4-20250514
  - claude-opus-4-20250514
  - claude-haiku-4-5-20251001
  - (ve diğer güncel modeller)
- [x] `/model` komutu: şu an aktif modeli göster
- [x] `/model <model_adı>` komutu: modeli değiştir
- [x] Model değişikliği inline butonlarla (liste halinde seçim)
- [x] Model bilgisi `~/.irq/config.json`'da saklanır
- [x] Model limitleri ve maliyetleri hakkında bilgi gösterme

---

## Faz 5 — Faz Tamamlama Bildirimleri

> Hedef: Claude Code bir faz/görev tamamladığında, neler yaptığının özetini
> otomatik olarak Telegram'a gönderme.

### 5A — Çıktı Yakalama
- [x] Claude Code çıktısı (stdout) real-time olarak yakalanıyor
- [x] Çıktı buffer'lanıyor ve log dosyasına yazılıyor (`~/.irq/logs/`)
- [x] Çalıştırma tamamlanma sinyali tespit ediliyor (returncode + elapsed)

### 5B — Özet Oluşturma
- [x] Her çalıştırmanın sonucu `RunRecord` olarak kaydediliyor (`~/.irq/history.json`)
- [x] Özet formatı belirlendi:
  ```
  ✅ Tamamlandı | ⏱️ 12dk 3s

  📂 Proje: project-irq
  💬 `<prompt önizleme>`

  📝 Çıktı:
  <claude çıktısı — ilk 400 karakter>
  ```
- [x] Log dosyaları `~/.irq/logs/<tarih>_<proje>.log` formatında kalıcı

### 5C — Bildirim Gönderme
- [x] `/run` tamamlanınca Telegram mesajı formatlanıp gönderiliyor (✅/❌/🚫)
- [x] Hata durumunda farklı format: ❌ ile birlikte hata detayı
- [x] `/history [n]` komutu: son N tamamlanan çalıştırmanın listesi

---

## Faz 6 — Watchdog Engine (Log İzleme)

> Hedef: Claude Code çalışırken logları izle, loop tespiti yap, bildirim gönder.

### 6A — Log İzleme
- [x] Claude Code çıktısı real-time izleniyor
- [x] Log dosyası `~/.irq/logs/` altında tutuluyor
- [x] `bot/core/log_watcher.py` yazıldı (async tail mantığı)

### 6B — Loop Tespiti
- [x] Loop kriterleri tanımlandı:
  - Aynı hata mesajı **3+ kez** tekrarlanırsa
  - **5 dakika** boyunca yeni çıktı yoksa
  - Çıktı dosyası boyutu **10MB**'ı aşarsa
- [x] `bot/handlers/watchdog.py` yazıldı
- [x] Loop tespit edilince Telegram mesajı gidiyor
- [x] Mesajda **Devam Et / Atla / Durdur** inline butonları var

### 6C — Süreç Kontrolü
- [x] `/pause` komutu: çalışan Claude Code process'ini durdurur (SIGSTOP)
- [x] `/resume` komutu: devam ettirir (SIGCONT)
- [x] `/kill` komutu: process'i sonlandırır
- [x] Inline buton callback'leri çalışıyor

### 6D — /menu Command Center

> Hedef: Tüm özelliklerin tek bir inline mesajdan kontrol edilebildiği
> ana panel. Faz 6A-6C tamamlanınca mevcut callback handler'ları
> zaten hazır olduğundan sadece UI katmanı eklenir (~1-2 saat).

- [x] `cmd_menu` ve `_build_menu_content()` helper'ı yazıldı
- [x] Ana panel mesajı:
  ```
  🏠 IRQ Command Center
  📂 <proje_adı>  <bar> %<ilerleme>

  [▶️ Çalıştır]    [⏹ İptal]
  [⏸ Duraklat]    [▶ Devam Et]
  [📊 Roadmap]    [📂 Projeler]
  [🤖 Model]      [📋 Geçmiş]
  ```
- [x] Tüm butonlar mevcut callback handler'larını tetikler (yeni iş mantığı gerekmez)
- [x] `/menu` BotFather komut listesine eklendi

---

## Faz 7 — Maliyet Kontrolü

> Hedef: Claude Code API maliyetlerini takip et, limiti aşınca uyar.

- [x] Maliyet takip yöntemi kararlaştırıldı:
  - Option A seçildi: Claude Code CLI çıktısından token/maliyet parse
  - `--verbose` flag ile Claude CLI'dan detaylı çıktı alınıyor
  - Model bazlı maliyet hesaplaması token sayısına göre yapılıyor
- [x] `bot/core/cost_tracker.py` yazıldı
- [x] Claude CLI runner'a maliyet takibi entegrasyonu yapıldı
- [x] `/budget` komutu: günlük limit göster / değiştir
- [x] `/cost` komutu: son N günün harcama özeti
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
| v0.4.0 | Faz 4 | Mart 2026 | Model kontrolü |
| v0.5.0 | Faz 5 | Mart 2026 | Çalıştırma geçmişi & bildirimler |
| v0.6.0 | Faz 6 | Mart 2026 | Watchdog engine + /menu Command Center |
| v0.7.0 | Faz 7 | — | Maliyet kontrolü |
| v1.0.0 | Faz 8 | — | Çok kullanıcı |
| v2.0.0 | Faz 9 | — | Flutter mobil |
