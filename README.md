<p align="center"><img src="docs/banner.svg" alt="Kotoba Atlas — Japanese words, more context. English and German editions. Part of dot." width="100%"></p>

<p align="center">
  <a href="https://github.com/Somamill/kotoba-atlas/releases/latest"><strong>Kotoba Atlas 1.0.0</strong></a>
  &nbsp; · &nbsp; <a href="#install">Install</a>
  &nbsp; · &nbsp; <a href="docs/compatibility.md">Compatibility</a>
  &nbsp; · &nbsp; <a href="docs/research.md">Research</a>
</p>

**One complete dictionary file for your definition language.** Read Japanese with vocabulary, phrases, usage notes, names, kanji, grammar references, folklore, and pitch/frequency information in the same ZIP.

## Choose your edition

| Edition | Definitions | Entries¹ | Download |
|---|---|---:|---|
| **English** | English, with Japanese reference material | **1,080,161** | **[English v1.0.0 · 51.5 MB ↓](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.0/Kotoba-Atlas-English-v1.0.0.zip)** |
| **Deutsch** | German first; English fallback for uncovered term/readings | **1,566,691** | **[Deutsch v1.0.0 · 61.3 MB ↓](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.0/Kotoba-Atlas-German-v1.0.0.zip)** |

**Choose one ZIP. There are no extra feature packs to install.** Leave it compressed for import. Each file includes every feature layer listed below. The German edition contains more term/reading pairs because WaDoku contributes extensive additional German coverage.

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

Pitch, frequency and kanji are supplied as **native Yomichan banks and readable word notes in the same ZIP**. Supporting tools can use the native graphs/ranks/kanji data; word-only importers can use the notes and may ignore the extra banks. Audio playback, OCR and card export remain host features; audio/images are not bundled. [Feature matrix →](docs/compatibility.md)

## Smaller preparation, broad coverage

The earlier personal prototype expanded to **769.4 MB**. English now expands to **343.7 MB**, and German to **408.3 MB**—**55% and 47% less prepared data**, with all public feature layers retained.

- One primary English explanation per overlapping Jitendex/JMdict pair.
- English fallback appears in the German edition only when German definitions are absent for that term/reading.
- Names have lower result scores than ordinary vocabulary.
- Pitch/frequency data never creates a misleading result with no definition.
- Word, native metadata and character JSON banks are capped at **2 MiB** to limit individual parsing allocations.
- Plain text avoids rich-layout dependencies and keeps source labels visible.

All word, native metadata, kanji, tag and index banks passed the pinned upstream Yomitan v3 schemas. Edition-policy checks verify language selection, deduplication, bank limits, real definitions, and preserved inflection rules. [Measured preparation results →](docs/performance.md)

These are archive/format checks and offline preparation measurements. **Live Migaku Early Access and Yomitan imports have not been tested.** A million-entry initial import can still take time; the payload is smaller, not a guarantee of an instant browser import.

## Install

1. Download **English** or **Deutsch** above. Keep the ZIP compressed.
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

Python 3.11+ builds both public editions with standard-library code. Inputs are pinned by hash. The changing Jiten resource is kept as an attributed, immutable source snapshot; users do not install it separately.

```sh
python3 scripts/build.py
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests
python3 scripts/validate.py dist/Kotoba-Atlas-English-v1.0.0.zip
python3 scripts/validate.py dist/Kotoba-Atlas-German-v1.0.0.zip
python3 branding/dot/check.py
```

The release includes SHA-256 checksums and reports for both editions. [Source licences](DATA-LICENSES.md) · [Local-folder audit](docs/folder-audit.md) · [Release reports](docs/releases/1.0.0)

The old personal build remains local and can include commercial or unclear-licence material; it is not a public edition. Earlier `dict.` prototype tags remain in release history. **Kotoba Atlas starts at version 1.0.0.**

## Part of dot.

A quieter way to read, listen, and learn.

[read. — Books, articles, and highlights](https://github.com/Somamill/read) · [listen. — Find your next audiobook](https://github.com/Somamill/listen) · [Immersed — Japanese worth watching](https://github.com/Somamill/immersed)

Identity follows the [shared dot. brand kit](https://github.com/Somamill/dot-brand-kit). Project code is MIT-licensed; dictionary data and brand assets retain their own licences.
