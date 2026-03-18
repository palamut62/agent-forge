# Claude Forge v2 — Design Spec

## Problem

Claude Code kullanırken:
1. Her projede aynı setup tekrarı (CLAUDE.md, hooks, rules, memory)
2. Çok fazla skill/plugin var, hangisini ne zaman kullanacağı belirsiz
3. Claude context kaybediyor, aynı şeyleri tekrar açıklamak gerekiyor
4. Hook/rule/skill yazmak ve yönetmek zor
5. Projeler arası tutarlılık yok
6. Büyük projelerde Claude dosya yapısını kavrayamıyor

## Çözüm Özeti

claude-forge'a 4 yeni modül eklenir:

1. **Profile System** — Proje tipine göre hazır setup şablonları
2. **Skill Navigator** — Projeyi tarayıp hangi skill'lerin kullanılacağını öneren rehber
3. **Big Project Module** — Codemap, modüler CLAUDE.md, akıllı context yönetimi
4. **Cross-Project Sync** — Projeler arası öğrenme ve setup taşıma

---

## Modül 1: Profile System

### Amaç
Proje tipine göre hazır, test edilmiş setup şablonları. AI'a bağımlı değil, offline çalışır.

### Dosya Yapısı
```
claude_forge/
  profiles/
    __init__.py
    base.yaml           # Tüm profillere ortak (git hooks, temel rules)
    fastapi.yaml
    react.yaml
    fullstack.yaml
    telegram_bot.yaml
    cli_tool.yaml
    data_pipeline.yaml
```

### Profil YAML Formatı
```yaml
name: fastapi
description: "FastAPI + Python async projesi"
extends: base
languages: [python]
frameworks: [fastapi]

claude_md:
  tech_stack: "Python 3.12, FastAPI, httpx, pydantic, SQLAlchemy"
  coding_standards: |
    - Type hints zorunlu
    - async/await tercih et
    - Pydantic model kullan
  test_command: "pytest tests/ -v"
  lint_command: "ruff check --fix && ruff format"

hooks:
  pre_commit:
    - name: format
      command: "ruff format --check ."
    - name: test
      command: "pytest tests/ -x -q"

rules:
  - name: async-io
    content: "I/O işlemlerinde her zaman async kullan. requests yerine httpx.AsyncClient."
  - name: pydantic-models
    content: "API request/response için Pydantic model kullan, raw dict kullanma."

skills_include:
  - tdd-workflow
  - security-review
  - api-design
  - python-review

skills_exclude:
  - "threejs-*"
  - "kotlin-*"
  - "swift-*"
  - "golang-*"

memory_templates:
  - name: architecture
    content: "## Mimari Kararlar\n\n(Buraya ekle)"
  - name: api-contracts
    content: "## API Sözleşmeleri\n\n(Buraya ekle)"
```

### CLI Komutları
```bash
claude-forge init --profile fastapi          # Hazır profil uygula
claude-forge profiles                        # Mevcut profilleri listele
claude-forge profiles create <isim>          # Mevcut projeden profil çıkar
claude-forge profiles export <isim> <path>   # Profili dışa aktar
```

### Davranış
1. `--profile` verilirse AI'a gitmeden direkt uygular (hızlı, güvenilir)
2. `--profile` verilmezse mevcut AI analiz sistemi çalışır (fallback)
3. `profiles create` mevcut projedeki .claude/ yapısını YAML'a dönüştürür
4. `base.yaml` her zaman uygulanır, spesifik profil üstüne eklenir (extends)

---

## Modül 2: Skill Navigator

### Amaç
Yüzlerce skill arasından projeye uygun olanları filtrele, sırala, öner.

### Dosya Yapısı
```
claude_forge/
  navigator.py          # Ana modül
  skill_registry.json   # Skill metadata cache
```

### Skill Registry
İlk çalıştırmada tüm skill'leri tarar ve metadata'larını cache'ler:
```json
{
  "tdd-workflow": {
    "description": "Test-driven development workflow",
    "tags": ["testing", "python", "javascript", "go"],
    "use_when": ["yeni feature", "bug fix", "refactoring"],
    "conflicts_with": ["tdd"]
  },
  "threejs-fundamentals": {
    "description": "Three.js scene setup",
    "tags": ["threejs", "javascript", "3d"],
    "use_when": ["3d proje"]
  }
}
```

### Eşleştirme Algoritması
1. Projedeki diller ve framework'leri tespit et (scanner.py zaten yapıyor)
2. Skill tag'lerini proje bilgisiyle eşleştir
3. Skor hesapla: tag eşleşme sayısı + use_when eşleşme
4. Çakışan skill'leri (conflicts_with) işaretle
5. Sonucu 3 gruba ayır: **Önerilen**, **Opsiyonel**, **İlgisiz**

### CLI Komutları
```bash
claude-forge skills                   # Proje için skill analizi
claude-forge skills --apply           # Önerilen skill profilini .claude/skill-profile.json'a yaz
claude-forge skills --rebuild-cache   # Registry'yi yeniden oluştur
```

### Çıktı Örneği
```
📋 Skill Analizi: my-fastapi-project
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Önerilen (8):
  tdd-workflow        Test-driven development
  security-review     Güvenlik taraması
  api-design          REST API pattern'leri
  python-review       Python kod review
  python-patterns     Pythonic idiom'lar
  python-testing      pytest stratejileri
  postgres-patterns   PostgreSQL optimizasyon
  docker-patterns     Docker/Compose

⚡ Opsiyonel (3):
  deployment-patterns   CI/CD pipeline
  backend-patterns      Backend mimari
  django-patterns       Django (eğer kullanırsan)

🚫 İlgisiz (devre dışı bırakılabilir): 45 skill
  threejs-*, kotlin-*, swift-*, golang-*, perl-* ...

[A] Önerilenleri uygula  [S] Seç/düzenle  [Q] Çık
```

### .claude/skill-profile.json
```json
{
  "generated_by": "claude-forge",
  "generated_at": "2026-03-18",
  "project_type": "fastapi",
  "active_skills": ["tdd-workflow", "security-review", "api-design"],
  "excluded_patterns": ["threejs-*", "kotlin-*", "swift-*"]
}
```

> **Not:** Bu dosya Claude Code'a "hangi skill'leri kullan" demez — Claude Code skill seçimini otomatik yapar. Bu dosya **kullanıcıya referans** olması ve `CLAUDE.md`'ye "Bu projede şu skill'leri tercih et" notu yazılması içindir.

---

## Modül 3: Big Project Module

### Amaç
Büyük projelerde Claude'un context'i verimli kullanmasını sağla.

### Dosya Yapısı
```
claude_forge/
  mapper.py             # Proje haritası çıkarma
  context_manager.py    # Memory ve context yönetimi
```

### 3a: Codemap Generator (`mapper.py`)

Projeyi tarar ve `docs/CODEMAP.md` üretir:

```markdown
# Project Codemap

## Modüller
- `src/auth/` — Kimlik doğrulama (JWT, OAuth2)
- `src/api/routes/` — API endpoint'leri
- `src/services/` — İş mantığı
- `src/models/` — SQLAlchemy modelleri
- `src/core/` — Config, dependencies, exceptions

## Entry Points
- `src/main.py` → FastAPI app factory
- `src/cli.py` → CLI komutları

## Kritik Dosyalar
- `src/core/config.py` — Tüm env/settings
- `src/core/deps.py` — Dependency injection
- `alembic/` — DB migration'ları

## Bağımlılık Grafiği
routes → services → repositories → models
routes → core/deps → services
```

**Nasıl çalışır:**
1. Dosya ağacını tara (node_modules, .venv vb. hariç)
2. Import'ları analiz et (Python: ast modülü, JS: regex)
3. Modül bazında özet çıkar
4. Entry point'leri bul (main.py, app.py, index.ts, package.json scripts)
5. Bağımlılık grafiği oluştur

### 3b: Modüler CLAUDE.md

Büyük projelerde tek CLAUDE.md yerine hiyerarşik yapı:

```
project/
  CLAUDE.md                    # Ana: genel kurallar, mimari özet
  src/
    auth/
      CLAUDE.md                # Auth modülü: JWT flow, token format
    api/
      CLAUDE.md                # API: endpoint kuralları, validation
    services/
      CLAUDE.md                # Business logic kuralları
```

`claude-forge map --split` komutu ile:
1. Codemap'ten modülleri tespit et
2. Her modül için kısa CLAUDE.md oluştur (max 50 satır)
3. Ana CLAUDE.md'ye modül referanslarını ekle

### 3c: Context Manager (`context_manager.py`)

Memory dosyalarını akıllıca yönetir:

```bash
claude-forge context update          # Memory'yi güncelle
claude-forge context status          # Memory durumu
claude-forge context compact         # Eski/gereksiz memory'leri temizle
```

**`context update` ne yapar:**
1. `docs/CODEMAP.md`'yi yeniden üret (dosya değişmişse)
2. `memory/architecture.md`'nin güncel olup olmadığını kontrol et
3. Son git commit'lere bakıp önemli değişiklikleri memory'ye ekle
4. Kullanılmayan memory dosyalarını uyar

**`context compact` ne yapar:**
1. Memory dosyalarını oku
2. 30 günden eski, artık geçerli olmayan entry'leri kaldır
3. Tekrar eden bilgileri birleştir

---

## Modül 4: Cross-Project Sync

### Amaç
Bir projede işe yarayan setup'ı diğerine taşı. Mevcut lesson sistemi güçlendirilir.

### Mevcut Sistem (learner.py)
- Lesson kaydet (mistake → fix → rule)
- Lesson'ları rule olarak uygula

### Eklenenler

```bash
claude-forge sync export              # Mevcut projenin setup'ını dışa aktar
claude-forge sync import <path>       # Başka projeden setup al
claude-forge sync diff <path1> <path2> # İki projenin setup'ını karşılaştır
```

**`sync export` çıktısı:** `claude-forge-export.json`
```json
{
  "exported_at": "2026-03-18",
  "source_project": "my-fastapi-app",
  "claude_md_hash": "abc123",
  "hooks": [...],
  "rules": [...],
  "memory_files": [...],
  "lessons": [...],
  "skill_profile": {...}
}
```

**`sync import` davranışı:**
1. Export dosyasını oku
2. Mevcut setup ile karşılaştır
3. Çakışmaları göster, kullanıcıya sor (merge / overwrite / skip)
4. Seçilenleri uygula

**Lesson sistemi güçlendirme:**
- Lesson'lara `project_type` tag'i ekle (sadece ilgili projelere uygulansın)
- Lesson önem skoru (sık uygulanan = daha önemli)
- `claude-forge learn auto` → son git commit'lerden otomatik lesson çıkar (AI destekli, opsiyonel)

---

## CLI Komut Özeti (Güncel + Yeni)

```bash
# Mevcut (iyileştirilmiş)
claude-forge                          # İnteraktif menü
claude-forge <path>                   # Hızlı init
claude-forge init --profile <name>    # Profil ile init (YENİ)

# Profil Yönetimi (YENİ)
claude-forge profiles                 # Profil listesi
claude-forge profiles create <name>   # Projeden profil çıkar
claude-forge profiles export <n> <p>  # Dışa aktar

# Skill Navigator (YENİ)
claude-forge skills                   # Skill analizi
claude-forge skills --apply           # Önerileri uygula

# Büyük Proje (YENİ)
claude-forge map                      # Codemap üret
claude-forge map --split              # Modüler CLAUDE.md üret
claude-forge context update           # Memory güncelle
claude-forge context status           # Memory durumu
claude-forge context compact          # Temizle

# Cross-Project (YENİ)
claude-forge sync export              # Setup dışa aktar
claude-forge sync import <path>       # Setup içe aktar
claude-forge sync diff <p1> <p2>      # Karşılaştır

# Mevcut (değişmez)
claude-forge release                  # Release workflow
claude-forge learn                    # Lesson kaydet
```

---

## Dosya Yapısı (Güncel)

```
claude_forge/
  __init__.py
  cli.py                # Ana CLI (güncellenir)
  config.py             # Config yönetimi (mevcut)
  models.py             # OpenRouter model (mevcut)
  scanner.py            # Proje tarama (mevcut)
  analyzer.py           # AI analiz (mevcut)
  generator.py          # Proje üretme (mevcut)
  learner.py            # Lesson sistemi (güncellenir)
  release.py            # Release workflow (mevcut)
  versioning.py         # Versiyon yönetimi (mevcut)
  navigator.py          # Skill Navigator (YENİ)
  mapper.py             # Codemap generator (YENİ)
  context_manager.py    # Context/memory yönetimi (YENİ)
  sync.py               # Cross-project sync (YENİ)
  profiles/             # Hazır profil YAML'ları (YENİ)
    __init__.py
    base.yaml
    fastapi.yaml
    react.yaml
    fullstack.yaml
    telegram_bot.yaml
    cli_tool.yaml
    data_pipeline.yaml
```

## İmplementasyon Sırası

1. **Profile System** — En hızlı fayda, AI'a bağımlı değil
2. **Skill Navigator** — Günlük kullanımda en çok işe yarar
3. **Big Project Module** — Büyük projelere geçince kritik
4. **Cross-Project Sync** — Birden fazla proje olunca değer kazanır

## Bağımlılıklar

- Mevcut: click, rich, httpx
- Eklenen: PyYAML (profil YAML'ları), pydantic (profil validasyonu)
- Stdlib: ast (Python import analizi), json, pathlib

## Açıklamalar (Review Sonrası)

### Skill Registry Metadata Kaynağı
Skill'lerin frontmatter'ından `description` zaten çekiliyor (scanner.py). Ek metadata (tags, use_when) için:
- **Otomatik:** Skill adı ve description'dan keyword çıkarma (regex, AI yok)
- **Manuel override:** `skill_overrides.yaml` ile kullanıcı tag ekleyebilir
- Eşleştirme basit keyword matching: skill description'da "python" geçiyorsa python projeleriyle eşleş

### Context Compact Güvenlik
`context compact` asla otomatik silmez. Davranış:
1. Memory dosyalarını listele, son erişim tarihini göster
2. 30 günden eski olanları **uyarı** olarak göster
3. Kullanıcı onayı olmadan hiçbir şey silinmez
4. `--dry-run` varsayılan, `--apply` ile silme aktif

### Learn Auto Model/Maliyet
`learn auto` opsiyonel ve şu kurallara tabi:
- Kullanıcının config'deki default model'ini kullanır
- Max 20 commit analiz eder, max_tokens: 2048
- API unreachable → sessizce atla, uyarı göster
- `--no-ai` flag'i ile tamamen devre dışı

### JS/TS Import Analizi
JS/TS desteği **best-effort** olarak belgelenir:
- Statik `import/require` statement'ları regex ile
- Dynamic import, barrel file, path alias desteklenmez
- Yetersiz sonuçlarda kullanıcıya "codemap'i manuel düzenle" uyarısı

### Profil Validasyonu
- Profil YAML'ları pydantic model ile validate edilir (`ProfileSchema`)
- Schema: name (required), description (required), extends (optional), languages (list), frameworks (list), claude_md (dict), hooks (list), rules (list), skills_include (list), skills_exclude (list)
- `version: 1` alanı eklenir, ileriye dönük uyumluluk için
- Hatalı YAML → net hata mesajı, crash yok

### Sync Import Çakışma Kuralları
Çakışma = aynı dosya adı/isimde farklı içerik. Kurallar:
- **Rule:** Aynı isimde rule varsa → diff göster, seç: kaynak / hedef / birleştir
- **Hook:** Aynı event'te farklı komut → diff göster, seç
- **Memory:** Aynı dosya adında farklı içerik → diff göster, seç
- **CLAUDE.md:** Hiçbir zaman overwrite etme, sadece eksik bölümleri öner

### Modüler CLAUDE.md Değer Önerisi
Claude Code alt dizindeki CLAUDE.md'leri okur ama kullanıcı bunları yazmaz. claude-forge:
- Codemap'ten otomatik üretir (kullanıcı yazmak zorunda kalmaz)
- İçeriği modüle özel tutar (genel kurallar değil, modül bağlamı)
- `claude-forge map --split --dry-run` ile önce gösterir, onay alır

### Test Stratejisi
Her yeni modül için `tests/test_<modül>.py`:
- `test_navigator.py` — skill eşleştirme, registry oluşturma
- `test_mapper.py` — codemap üretimi, import analizi
- `test_context_manager.py` — memory CRUD, compact güvenliği
- `test_sync.py` — export/import, çakışma tespiti
- `test_profiles.py` — YAML yükleme, validasyon, extends mantığı
- Fixture'lar `conftest.py`'da, mock sadece dosya sistemi için
- Hedef: %80 coverage

## Riskler

- Codemap üretimi büyük projelerde yavaş olabilir → dosya sayısı limiti (max 500) + cache
- Skill registry bakımı gerekir → ilk seferde otomatik oluştur, sonra cache kullan
- Modüler CLAUDE.md çok parçalanırsa Claude karışabilir → max 5-6 alt CLAUDE.md, dry-run varsayılan
