# GEMINI.md — Project IRQ

> Bu dosya Gemini CLI ve diğer AI agent'lar için temel yönerge (foundational mandate) dosyasıdır.
> Sistem talimatlarım gereği, bu dosyadaki kurallar genel çalışma prensiplerimin üzerindedir.
> **Her oturuma başlamadan önce mutlaka oku ve uygula.**

## 🎯 Proje Özeti
**Project IRQ** — Telegram üzerinden Claude Code/Gemini CLI'ya uzaktan komut veren, birden fazla projeyi yöneten ve faz ilerlemesini takip eden bir akıllı geliştirme asistanıdır.
- **Bot:** `@ireque_bot` (Telegram)
- **Çalışma Ortamı:** Yerel Mac (Sunucusuz, polling tabanlı)
- **Hedef:** Tek kullanıcıdan çok kullanıcıya ölçeklenebilir bir yapı.

## 🔄 Oturum Başlangıç Ritüeli
1. **ROADMAP.md** dosyasını oku.
2. Mevcut fazı ve tamamlanmamış sıradaki adımı belirle.
3. Kullanıcıya mevcut durum özetiyle başla.
4. Tamamlanan adımları `ROADMAP.md` içinde `[x]` olarak işaretle.

## 🏗️ Mimari ve Teknoloji
- **Dil/Framework:** Python 3.11+ (Asyncio), `python-telegram-bot` v20+
- **Runner:** Claude Code CLI subprocess üzerinden çalıştırılır.
- **Config:** `~/.irq/` dizininde JSON dosyaları (`projects.json`, `config.json`).
- **Aktif Proje:** `project_registry.py` üzerinden yönetilir.

## 🛠️ Geliştirme Standartları (Gemini Özel)
- **Kod Stili:** PEP8 standartları, zorunlu Type Hinting, asenkron handler yapısı.
- **Loglama:** Her dosyada `logger = logging.getLogger(__name__)` kullanılmalı, exception'lar yutulmamalı.
- **Surgical Updates:** Sadece ilgili fonksiyonu veya bloğu değiştir (Tüm dosyayı baştan yazmaktan kaçın).
- **Test-Driven:** Önemli değişikliklerde `pytest` veya ilgili test script'lerini çalıştır/oluştur.
- **Inline Navigasyon:** Telegram butonları için `callback_data` yapılarına sadık kal.

## 📋 Git Commit Kuralları
- `feat: ...`, `fix: ...`, `chore: ...`, `docs: ...` formatını kullan.

## 🚀 Mevcut Durum (Faz 5'e Geçiş)
Şu an **Faz 4 (Model Kontrolü)** tamamlandı. Sıradaki hedef **Faz 5: Canlı Çıktı ve Bildirimler**.

---
*Bu dosya projenin kalbidir. Değişiklik yapmadan önce kullanıcıdan onay al.*
