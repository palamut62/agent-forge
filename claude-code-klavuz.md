# Claude Code — Tam Geliştirme Ortamı Kılavuzu
*Local Windows/Mac için, tüm projeler genelinde geçerli*

---

## Bu Kılavuz Hakkında

Bu kılavuz 3 temel kaynak üzerine kurulu:
1. **Hooks** — deterministik otomasyon katmanı
2. **Skills + Rules + CLAUDE.md** — AI davranış katmanı  
3. **3-Layer Memory Architecture** — oturumlararası hafıza sistemi

Her bölüm: **ne**, **neden**, **nasıl** sırasıyla açıklanıyor. Hazır kopyala-yapıştır dosyaları ekte.

---

## Dizin Yapısı (Hedef)

Kurulum bittikten sonra her projenin şu yapıda olmasını istiyoruz:

```
proje-klasoru/
├── CLAUDE.md                    ← proje hafızası (her session yüklenir)
├── .claude/
│   ├── settings.json            ← hooks konfigürasyonu
│   ├── skills/
│   │   ├── commit/
│   │   │   └── SKILL.md
│   │   ├── review/
│   │   │   └── SKILL.md
│   │   └── deploy/
│   │       └── SKILL.md
│   ├── rules/
│   │   ├── no-any.md
│   │   ├── no-console-log.md
│   │   └── test-before-commit.md
│   └── hooks/
│       ├── format.sh
│       ├── protect-env.sh
│       └── dangerous-check.sh
└── memory/                      ← oturumlararası hafıza
    ├── MEMORY.md                ← routing belgesi (max 200 satır)
    ├── debugging.md
    ├── patterns.md
    ├── architecture.md
    └── preferences.md
```

Ve global (tüm projeler için):
```
~/.claude/
├── settings.json                ← global hooks
└── skills/                      ← tüm projelerde kullanılacak skills
```

---

## BÖLÜM 1: CLAUDE.md — Proje Hafızası

### Neden?
Claude her session'da sıfırlanır. CLAUDE.md bu sorunu çözer — projeyi, kararları, kuralları Claude'a her seferinde öğreten belgedir. Config dosyası değil, **öğretim belgesi**.

### Kritik Kurallar
- **200 satır altında tut** — Claude'un ~150 talimat slotu var, kendi system prompt'u 50'sini harcıyor, sana 100 kalıyor
- **Vague yazmа** — "iyi kod yaz" işe yaramaz, "snake_case kullan, camelCase kullanma" işe yarar
- **Değişmeyen kararları yaz** — haftalık değişen şeyleri koyma

### Şablon

```markdown
# [Proje Adı] — Claude için Proje Rehberi

## Sen Kimsin
Bu projede senior full-stack developer rolündesin.
Python backend, React frontend. Türkçe yorum yaz, İngilizce kod yaz.

## Tech Stack
- Backend: Python 3.11+, FastAPI
- Frontend: React 18, TypeScript
- DB: PostgreSQL
- Package manager: pip (backend), npm (frontend)
- Test: pytest (backend), Jest (frontend)

## Mimari Kararlar
- API versiyonlama: /api/v1/ prefix zorunlu
- Auth: JWT, refresh token pattern
- Error handling: custom exception sınıfları, HTTP status code standartları

## Kod Standartları
- Python: snake_case, type hints zorunlu, docstring her public fonksiyona
- TypeScript: strict mode, any yasak, interface > type
- Commit: conventional commits (feat/fix/chore/docs)
- Console.log bırakma — logger kullan

## Kesin Sınırlar (Asla Yapma)
- .env dosyasını düzenleme, sadece oku
- main/master branch'e direkt commit etme
- Test yazmadan yeni feature ekleme
- npm audit high/critical uyarısı olan paket yükleme

## Sık Yapılan Hatalar (Gotchas)
- [Proje büyüdükçe buraya ekle]

## Önemli Dosyalar
- `docs/architecture.md` — sistem mimarisi detayı
- `docs/api.md` — API endpoint listesi
- `.env.example` — gerekli environment variables

## Test Komutları
- Backend: `pytest tests/ -v`
- Frontend: `npm test`
- Full: `make test`
```

---

## BÖLÜM 2: Memory Sistemi — Oturumlararası Hafıza

### Neden?
CLAUDE.md statik bilgi içerir. Memory sistemi **dinamik öğrenmeyi** yakalar — Claude bir şey keşfettiğinde, hata yaptığında, sen düzelttikçe bunlar birikerek sonraki session'larda kullanılır.

### Yapı

**memory/MEMORY.md** (routing belgesi, max 200 satır):
```markdown
# Proje Hafızası — Routing

Son güncelleme: [tarih]

## Kritik Notlar
- [en önemli 3-5 şey buraya]

## Detaylı Bilgi İçin
- Tekrarlayan hatalar ve çözümleri: `memory/debugging.md`
- Codebase pattern'leri: `memory/patterns.md`  
- Mimari kararlar: `memory/architecture.md`
- Çalışma tercihleri: `memory/preferences.md`
```

**memory/debugging.md**:
```markdown
# Debugging Hafızası

## [Tarih] — [Hata Başlığı]
**Belirti:** ...
**Sebep:** ...
**Çözüm:** ...
**Tekrar Olursa:** ...

---
```

**memory/preferences.md**:
```markdown
# Çalışma Tercihleri

## Kod Stili
- Açıklama satırı: Türkçe
- Değişken/fonksiyon: İngilizce
- Kısa fonksiyonlar tercih edilir (max 30 satır)

## İletişim
- Teknik detayları göster, süreci gizleme
- Hata mesajlarını tam göster
- Önce çözümü yaz, sonra açıkla

## Araçlar
- Terminal komutlarını tercih et (GUI yerine)
- pip install --break-system-packages (VPS için)
```

### CLAUDE.md'ye Ekle
```markdown
## Hafıza Sistemi
Her session başında `memory/MEMORY.md` dosyasını oku.
Önemli keşifler, hatalar veya kararlar için ilgili memory dosyasını güncelle.
Her session sonunda öğrendiklerini ilgili memory dosyasına yaz.
```

---

## BÖLÜM 3: Hooks — Deterministik Kontrol

### Neden?
Rules ve CLAUDE.md ile koyduğun kurallar ~%70-80 oranında uygulanır. Hooks **%100** uygulanır — Claude karar vermez, sistem zorlar.

### .claude/settings.json

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/format.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/protect-env.sh",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/dangerous-check.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/notify.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### Hook Dosyaları

**.claude/hooks/format.sh** — Otomatik formatlama:
```bash
#!/bin/bash
# Dosya tipine göre otomatik formatla
FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('path',''))" 2>/dev/null)

if [[ "$FILE_PATH" == *.py ]]; then
  command -v black &>/dev/null && black "$FILE_PATH" --quiet 2>/dev/null
  command -v isort &>/dev/null && isort "$FILE_PATH" --quiet 2>/dev/null
elif [[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.tsx ]] || [[ "$FILE_PATH" == *.js ]]; then
  command -v prettier &>/dev/null && prettier --write "$FILE_PATH" --log-level silent 2>/dev/null
fi

exit 0
```

**.claude/hooks/protect-env.sh** — .env koruma:
```bash
#!/bin/bash
# .env dosyasına yazmayı engelle
FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('path',''))" 2>/dev/null)

if [[ "$FILE_PATH" == *".env" ]] && [[ "$FILE_PATH" != *".env.example" ]]; then
  echo '{"block": true, "message": "ENGELLENDI: .env dosyasına yazma yasak. Sadece .env.example düzenlenebilir."}' >&2
  exit 2
fi

exit 0
```

**.claude/hooks/dangerous-check.sh** — Tehlikeli komut kontrolü:
```bash
#!/bin/bash
# Tehlikeli bash komutlarını yakala
COMMAND=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('command',''))" 2>/dev/null)

# rm -rf kontrolü
if echo "$COMMAND" | grep -qE "rm\s+-rf\s+/|rm\s+-rf\s+~"; then
  echo '{"block": true, "message": "ENGELLENDI: Kök dizin silme komutu tespit edildi. Bu komutu gerçekten çalıştırmak istiyorsan manuel yap."}' >&2
  exit 2
fi

# Tehlikeli git komutları
if echo "$COMMAND" | grep -qE "git\s+push\s+--force\s+origin\s+main|git\s+push\s+--force\s+origin\s+master"; then
  echo '{"block": true, "message": "ENGELLENDI: main/master branch force push yasak."}' >&2
  exit 2
fi

# DROP TABLE koruması
if echo "$COMMAND" | grep -qiE "DROP\s+TABLE|DROP\s+DATABASE"; then
  echo '{"block": true, "message": "ENGELLENDI: Destructive SQL komutu tespit edildi. Manuel onay gerekli."}' >&2
  exit 2
fi

exit 0
```

**.claude/hooks/notify.sh** — Masaüstü bildirimi (Windows için):
```bash
#!/bin/bash
# Claude input beklediğinde bildirim gönder
# Windows (WSL içinden):
if command -v powershell.exe &>/dev/null; then
  powershell.exe -Command "
    [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null
    \$notify = New-Object System.Windows.Forms.NotifyIcon
    \$notify.Icon = [System.Drawing.SystemIcons]::Information
    \$notify.Visible = \$true
    \$notify.ShowBalloonTip(3000, 'Claude Code', 'Onayın bekleniyor!', [System.Windows.Forms.ToolTipIcon]::Info)
    Start-Sleep -Seconds 3
    \$notify.Dispose()
  " 2>/dev/null
fi

# Mac için:
# osascript -e 'display notification "Onayın bekleniyor!" with title "Claude Code"'

exit 0
```

### Özel On-Demand Hook'lar (Skills İçinde)

Bu hook'lar sadece ilgili skill çağrıldığında aktif olur:

```bash
# /careful skill çağrıldığında — prod'a dokunurken
# .claude/skills/careful/SKILL.md içinde hook tanımı
```

---

## BÖLÜM 4: Skills — Tekrarlayan İş Akışları

### Neden?
Aynı prompt'u defalarca yazmak yerine, bir kere iyi yaz, her projede kullan.

### /commit — Akıllı Commit

**.claude/skills/commit/SKILL.md**:
```markdown
---
name: commit
description: Kod değişikliklerini analiz edip semantic commit mesajı oluştur ve commit at. "commit yap", "değişiklikleri kaydet", "commit" kelimelerinde tetikle.
allowed-tools: Bash, Read
---

# Commit Skill

## Adımlar

1. `git diff --staged` ve `git status` çalıştır
2. Değişikliklerin kapsamını analiz et
3. Conventional Commits formatında mesaj oluştur:
   - feat: yeni özellik
   - fix: hata düzeltme
   - refactor: kod düzenleme (davranış değişmez)
   - docs: sadece dokümantasyon
   - test: test ekleme/düzenleme
   - chore: build, bağımlılık güncelleme
4. Test suite çalıştır — BAŞARISIZ ise commit yapma, kullanıcıya bildir
5. Onay al, commit at

## Format
```
<tip>(<kapsam>): <kısa açıklama>

[isteğe bağlı gövde]

[isteğe bağlı footer]
```

## Gotchas
- Staged değişiklik yoksa kullanıcıya sor: "git add mı yapalım?"
- Breaking change varsa footer'a "BREAKING CHANGE:" ekle
- Test çalıştırma komutu CLAUDE.md'den oku
```

### /review — Kod İnceleme

**.claude/skills/review/SKILL.md**:
```markdown
---
name: review
description: Kodu 5 açıdan incele ve rapor üret. "review", "kod incele", "kontrol et" ifadelerinde tetikle.
allowed-tools: Read, Bash, Grep
---

# Code Review Skill

## 5 İnceleme Boyutu

### 1. Güvenlik
- SQL injection, XSS, CSRF açıkları
- Hardcoded secret/credential
- Input validasyon eksiklikleri

### 2. Performans  
- N+1 sorgu problemi
- Gereksiz döngü içi hesaplama
- Bellek sızıntısı riski

### 3. Kod Kalitesi
- DRY ihlalleri (tekrar eden kod)
- Fonksiyon karmaşıklığı (max 30 satır önerisi)
- Anlamlı isimlendirme

### 4. Test Kapsamı
- Kritik fonksiyonlar test edilmiş mi?
- Edge case'ler var mı?
- Mock kullanımı doğru mu?

### 5. Proje Kuralları
- CLAUDE.md kurallarına uyum
- Naming convention
- Import düzeni

## Çıktı Formatı
Her boyut için: ✅ Sorun yok / ⚠️ Dikkat / ❌ Kritik
Sonunda: öncelikli düzeltme listesi
```

### /debug — Sistematik Hata Ayıklama

**.claude/skills/debug/SKILL.md**:
```markdown
---
name: debug
description: Hata mesajı veya beklenmedik davranış için sistematik debug yap. "hata", "çalışmıyor", "debug", "neden" ifadelerinde düşün.
allowed-tools: Read, Bash, Grep
---

# Debug Skill

## Adımlar

1. Hatayı tam olarak anla — stack trace ve hata mesajını oku
2. `memory/debugging.md` dosyasını kontrol et — benzer hata daha önce yaşandı mı?
3. Minimal reproductible case oluştur
4. Hipotez kur, test et, doğrula
5. Çözümü `memory/debugging.md` dosyasına kaydet

## Gotchas
- Önce environment kontrol et (Python version, env vars, dependencies)
- "Works on my machine" durumunda Docker farkı olabilir
- Type error genellikle upstream'de başlar, downstream'de görünür
```

---

## BÖLÜM 5: Rules — Bağlamsal Kurallar

### Önemli Uyarı
Rules deterministik DEĞİL (~%70-80 uyum). Mutlak olmasını istediğin şeyler için hook kullan.
Rules = "Claude'a bağlam verme", Hooks = "sisteme zorlama".

**.claude/rules/code-quality.md**:
```markdown
---
description: Python ve TypeScript kod yazarken her zaman uygula.
---

# Kod Kalite Kuralları

## Python
- Type hints zorunlu: `def func(name: str) -> dict:`
- `any` tipi yasak TypeScript'te, Python'da da `Any` kullanma
- `print()` bırakma — `logger.info()` kullan
- Exception'ları sessizce yutma: `except Exception: pass` yasak

## TypeScript  
- `any` tipi yasak, `unknown` kullan
- Non-null assertion `!` kullanmaktan kaçın
- Optional chaining `?.` tercih et

## Genel
- Magic number kullanma, sabit tanımla
- Fonksiyon max 30 satır
- Commit'te console.log/print bırakma
```

**.claude/rules/git-workflow.md**:
```markdown
---
description: Git operasyonları yaparken uygula.
---

# Git Kuralları

- Test geçmeden commit yapma
- main/master'a direkt commit yasak — branch aç
- Commit mesajı: conventional commits formatı
- .env, secret, credential commit etme
- Binary dosya (.pyc, __pycache__, node_modules) commit etme
```

---

## BÖLÜM 6: Kurulum Sırası

### Adım 1 — Klasör Yapısını Oluştur
```bash
# Proje klasörünün içinde:
mkdir -p .claude/skills/commit
mkdir -p .claude/skills/review  
mkdir -p .claude/skills/debug
mkdir -p .claude/rules
mkdir -p .claude/hooks
mkdir -p memory

# Dosyaları oluştur (yukarıdaki içerikleri yapıştır)
touch CLAUDE.md
touch .claude/settings.json
touch memory/MEMORY.md
touch memory/debugging.md
touch memory/patterns.md
touch memory/architecture.md
touch memory/preferences.md
```

### Adım 2 — Hook Dosyalarını Çalıştırılabilir Yap
```bash
chmod +x .claude/hooks/*.sh
```

### Adım 3 — Formatlama Araçlarını Kur
```bash
# Python
pip install black isort

# JavaScript/TypeScript
npm install -g prettier
```

### Adım 4 — CLAUDE.md'yi Doldur
Proje bilgilerini yukarıdaki şablona göre yaz. **20 dakika harca, her session'da kazan.**

### Adım 5 — Memory Dosyalarını Başlat
Her dosyaya minimal başlangıç içeriği yaz. Boş dosya Claude'u karıştırır.

### Adım 6 — İlk Session'da Test Et
```
claude
> /commit  # skill çalışıyor mu?
> .envdosyasını düzenle  # hook engelliyor mu?
> memory/preferences.md dosyasını oku  # hafıza çalışıyor mu?
```

---

## BÖLÜM 7: Proje Tipine Göre Ek Ayarlar

### Python API Projeleri (FastAPI/Django)
CLAUDE.md'ye ekle:
```markdown
## Python Özel
- Virtual env: `source venv/bin/activate`
- Bağımlılık ekle: `pip install X && pip freeze > requirements.txt`
- Migration: alembic (FastAPI) veya django migrations
- Test çalıştır: `pytest tests/ -v --tb=short`
```

### React/TypeScript Projeleri
CLAUDE.md'ye ekle:
```markdown
## Frontend Özel
- Component: functional, hooks kullan, class component yasak
- State: useState/useReducer yerel, Zustand/Redux global
- Styling: [kullandığın sistem — Tailwind/CSS Modules/styled-components]
- Test: React Testing Library, user-event
```

### AI/Bot Projeleri (Polymarket gibi)
CLAUDE.md'ye ekle:
```markdown
## AI Proje Özel
- API key'leri asla hardcode etme, .env'den oku
- Rate limit koruması: her API çağrısında retry logic
- Log her AI kararını: input, output, confidence
- Gerçek para işlemleri: mock mode'da test et önce
- Model versiyonu sabitle: "claude-sonnet-4-20250514" gibi
```

---

## BÖLÜM 8: Bakım ve Geliştirme

### Her Hafta
- `memory/debugging.md` dosyasını incele — pattern var mı?
- CLAUDE.md'ye yeni gotchas ekle

### Her Ay
- Skills'leri gözden geçir — hangisi kullanılmıyor?
- Hook'lar gereksiz bir şeyi engelliyor mu?
- CLAUDE.md 200 satırı aştı mı? Kırp.

### Claude Hata Yaptığında
1. Düzelt
2. `memory/debugging.md` dosyasına yaz
3. CLAUDE.md'ye gotcha olarak ekle
4. Bir sonraki session'da aynı hatayı yapmaz

---

## Hızlı Başvuru

| İhtiyaç | Çözüm |
|---------|-------|
| Her session'da sıfırdan başlıyor | CLAUDE.md doldur |
| Aynı hatayı tekrarlıyor | memory/debugging.md'ye yaz |
| Kural dinlemiyor | Rule yerine Hook kullan |
| Slash komut kullanmak | Skills oluştur |
| .env korunmuyor | protect-env.sh hook'u |
| Bildirim almak istiyorum | notify.sh hook'u |
| Format tutarsız | format.sh hook'u (PostToolUse) |

---

*Bu kılavuz yaşayan bir belgedir. Claude hata yaptıkça, yeni projeler ekledikçe güncelle.*
