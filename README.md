<p align="center"><img src="docs/banner.svg" alt="Kotoba Atlas — Japanese words, more context. English and German editions. Part of dot." width="100%"></p>

<p align="center">
  <a href="https://github.com/Somamill/kotoba-atlas/releases/latest"><strong>Kotoba Atlas 1.0.1</strong></a>
  &nbsp; · &nbsp; <a href="#install">Install</a>
  &nbsp; · &nbsp; <a href="docs/compatibility.md">Compatibility</a>
  &nbsp; · &nbsp; <a href="docs/research.md">Research</a>
</p>

**One complete dictionary file for your definition language.** Read Japanese with vocabulary, phrases, usage notes, names, kanji, grammar references, folklore, and pitch/frequency information in the same ZIP.

## Choose your edition

| Edition | Definitions | Entries¹ | Migaku word export | Full Yomitan export |
|---|---|---:|---|---|
| **Deutsch** | German first; English fallback for uncovered term/readings | **1,566,695** | **[v1.0.1 · 47.9 MB ↓](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.1/Kotoba_Atlas_German_Migaku_v1_0_1.zip)** | [v1.0.1 · 61.2 MB ↓](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.1/Kotoba-Atlas-German-v1.0.1.zip) |
| **English** | English, plus Japanese reference material | **1,080,167** | **[v1.0.1 · 38.3 MB ↓](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.1/Kotoba_Atlas_English_Migaku_v1_0_1.zip)** | [v1.0.1 · 51.6 MB ↓](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.1/Kotoba-Atlas-English-v1.0.1.zip) |

**Choose one ZIP for your tool and definition language. There are no required feature packs.** German already includes English fallback. Both exports have byte-identical word banks containing all words, names, grammar, kanji references and readable pitch/frequency notes. The full Yomitan export additionally supplies native character, pitch, frequency and POS/tag banks. The Migaku export uses ordinary word banks only, following the public word-import format; native graphs/sorting are host features. Its underscore filename (`v1_0_1`) also avoids the legacy importer's SQL-name restrictions.

¹ Entries are term-and-reading pairs, including names, spellings and reference entries—not that many distinct words. All data retains its source-specific licence. No claim of every Japanese word or every possible nuance is made.

## What is inside each file

| Layer | Included sources and handling |
|---|---|
| Vocabulary and slang | **Jitendex**, with newer **JMdict** filling missing term/reading pairs, plus **Wiktionary**; German edition adds **WaDoku** and **JMdict German** |
| Phrases and nuance | Source usage labels, notes and supplied examples; **NINJAL grammar-pattern bank**; reviewed phrase supplements |
| Names | **JMnedict**, ranked below ordinary vocabulary |
| Kanji | **KANJIDIC** meanings and on/kun readings |
| Folklore | Attributed Japanese yōkai reference text |
| Pronunciation | **WaDoku** native pitch data plus readable pitch/devoicing notes |
| Frequency | **Jiten global** native frequency data plus rank notes, built from multiple kinds of Japanese media |
| Written variants | Explicit aliases for forms such as **物ノ怪**; labeled の → ノ aliases between kanji |

Pitch, frequency and kanji references are readable word notes in **both exports**. The full Yomitan export also includes native banks for supporting graphs/ranks/kanji views; the Migaku export omits those extra banks. Audio playback, OCR and card export remain host features; audio/images are not bundled. [Feature matrix →](docs/compatibility.md)

## Smaller preparation, broad coverage

The Migaku exports expand to **245.3 MB** for English and **301.5 MB** for German. Each avoids about **96 MB** of native-bank preparation compared with its full Yomitan export, while retaining byte-identical word banks and all readable references. Full exports expand to **341.3 MB** and **397.4 MB** respectively.

- One primary English explanation per overlapping Jitendex/JMdict pair.
- English fallback appears in the German edition only when German definitions are absent for that term/reading.
- Names have lower result scores than ordinary vocabulary.
- Pitch/frequency data never creates a misleading result with no definition.
- Word, native metadata and character JSON banks are capped at **2 MiB** to limit individual parsing allocations.
- Plain text avoids rich-layout dependencies and keeps source labels visible.

All word, native metadata, kanji, tag and index banks passed the pinned upstream Yomitan v3 schemas. Edition-policy checks verify language selection, deduplication, bank limits, real definitions, and preserved inflection rules. [Measured preparation results →](docs/performance.md)

These are archive/format checks and offline preparation measurements. **Current Migaku Early Access and installed Yomitan extension UIs are not live-certified.** The pinned public legacy Migaku importer core imported both complete editions into SQLite. The current upstream Yomitan parser processed both full archives; representative fixtures also passed its IndexedDB adapter and 14 deinflection checks. [Exact test scopes and results →](docs/migaku-1.0.1.md) A million-entry initial import can still take time; the payload is smaller, not a guarantee of an instant browser import.

## Install

1. Download **English** or **Deutsch** for the tool you use. Keep the ZIP compressed.
2. **Yomitan:** Settings → Dictionaries → Configure installed and enabled dictionaries → Import.
3. **Migaku:** use the dictionary settings' import-from-file action. Exact labels vary by version. The archive uses plain Yomichan v3 word banks; current Early Access runtime compatibility remains unverified.
4. Enable the imported edition and try a manual lookup for **羅睺**, **物ノ怪**, and **鎌かけて**. Then test hover or selected-phrase lookup.

If the old **Dict Personal** import is still preparing, cancel that operation before starting a new one. Keep an already-installed dictionary until the replacement works. Use the host's normal replacement/removal controls if it rejects a duplicate title. Source update manifests are supplied for Yomitan-compatible update checking; actual update behavior depends on the host.

## Built around reading examples

| Encountered text | Handling |
|---|---|
| `羅睺` | English definitions and readings `らご` / `らごう` |
| `物ノ怪` | Exact alias for `物の怪` / `もののけ` |
| `鎌かけて` | Colloquial phrase entry linked to `鎌を掛ける` |
| `鎌かける` | Base form with the `v1` inflection rule |

Source verb/adjective rules are retained even where duplicate explanations are removed. Explicit phrase fixes do not generalize particle deletion to arbitrary Japanese. Different spellings/readings can remain separate results because merging them indiscriminately can erase distinctions.

For Anki mining, save the sentence you actually encountered and the relevant sense, rather than treating a dictionary's whole entry as one fact. This is a lookup resource, **not a million-card Anki deck**. [Community lessons and source notes →](docs/research.md)

## Build and verify

Python 3.11+ builds both language editions and their tool-specific exports with standard-library code. Inputs are pinned by hash. The changing Jiten resource is kept as an attributed, immutable source snapshot; users do not install it separately.

```sh
python3 scripts/build.py
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests
python3 scripts/validate.py dist/Kotoba-Atlas-English-v1.0.1.zip
python3 scripts/validate.py dist/Kotoba-Atlas-German-v1.0.1.zip
python3 scripts/validate.py dist/Kotoba_Atlas_German_Migaku_v1_0_1.zip
python3 scripts/validate.py dist/Kotoba_Atlas_English_Migaku_v1_0_1.zip
python3 branding/dot/check.py
```

The release includes SHA-256 checksums and reports for both editions. [Source licences](DATA-LICENSES.md) · [Local-folder audit](docs/folder-audit.md) · [Release reports](docs/releases/1.0.1)

The old personal build remains local and can include commercial or unclear-licence material; it is not a public edition. Earlier `dict.` prototype tags remain in release history. **Kotoba Atlas starts at version 1.0.0.**

## Part of dot.

A quieter way to read, listen, and learn.

[read. — Books, articles, and highlights](https://github.com/Somamill/read) · [listen. — Find your next audiobook](https://github.com/Somamill/listen) · [Immersed — Japanese worth watching](https://github.com/Somamill/immersed)

Identity follows the [shared dot. brand kit](https://github.com/Somamill/dot-brand-kit). Project code is MIT-licensed; dictionary data and brand assets retain their own licences.
