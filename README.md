<p align="center"><img src="docs/banner.svg" alt="dict. — Japanese, with more context. German first, English alongside. Part of dot." width="100%"></p>

<p align="center">
  <a href="https://github.com/Somamill/dict/releases/latest/download/dict-master.zip"><strong>Download the master dictionary ↓</strong></a>
  &nbsp; · &nbsp;
  <a href="#install">Install</a>
  &nbsp; · &nbsp;
  <a href="docs/coverage.md">Coverage & compatibility</a>
  &nbsp; · &nbsp;
  <a href="DATA-LICENSES.md">Sources & licences</a>
</p>

<p align="center">
  <img alt="German first, English backup" src="https://img.shields.io/badge/definitions-DE%20%2B%20EN-906530?style=flat-square">
  <img alt="Yomichan v3 plain-text format" src="https://img.shields.io/badge/format-Yomichan%20v3-42684B?style=flat-square">
  <a href="https://github.com/Somamill/dict/actions/workflows/check.yml"><img alt="Project checks" src="https://github.com/Somamill/dict/actions/workflows/check.yml/badge.svg"></a>
</p>

**One ZIP for Japanese words, phrases, names, and reference material.** German definitions appear first, followed by English and, where available, Japanese explanations. Each contribution names its source so you can compare senses rather than mistake one combined paragraph for a single authority.

The initial public build contains **1,566,691 term-and-reading entries** in about **61 MB**. That count includes names, spelling variants, kanji reference entries, and pronunciation-only entries; it is not a count of distinct Japanese words.

## What is inside

| Layer | Sources | What it adds |
|---|---|---|
| German | **WaDoku · JMdict German** | Everyday vocabulary, compounds, phrases, and German explanations |
| English | **Jitendex · JMdict · Wiktionary** | Additional senses, terminology, usage labels, and examples supplied by the source |
| Expressions | **NINJAL grammar-pattern bank** | Japanese explanations, connection patterns, and example sentences |
| Names | **JMnedict** | People, places, organizations, and other proper names |
| Character reference | **KANJIDIC** | Character meanings and on/kun readings, rendered as lookup text |
| Folklore | **Yōkai encyclopedia** | Japanese descriptions of spirits and supernatural phenomena |
| Pronunciation | **WaDoku pitch data** | Labeled numeric pitch notes; no native pitch graph |
| Spelling and phrases | **Project supplement** | Explicit phrase fixes and transparent の → ノ spelling aliases between kanji |

Jitendex and JMdict overlap substantially. They are retained with separate source labels; the entry total is not advertised as independent dictionary coverage. Definitions are converted to plain text. The archive contains no executable code, audio, fonts, or images.

## Install

1. **[Download `dict-master.zip`](https://github.com/Somamill/dict/releases/latest/download/dict-master.zip)** and leave it zipped.
2. In **Yomitan**, open Settings → Dictionaries → Configure installed and enabled dictionaries → Import, then select the ZIP.
3. In **Migaku**, open its dictionary settings and use its import-from-file option to select the same ZIP. Labels vary by version. The build uses the legacy Yomichan word-dictionary structure documented by Migaku.
4. Enable the imported dictionary and test a **manual search** for `羅睺`, `物ノ怪`, and `鎌かけて` before testing hover lookup.

For an update, keep the old dictionary until the replacement has imported and the examples work. If the app rejects a duplicate title, use its normal dictionary removal/replacement controls after backing up any app-specific customization. Browser import stores the data locally and may require substantially more space than the compressed download.

**Format compatibility has been checked against the upstream Yomitan schemas for every entry. Browser imports and Migaku Early Access rendering have not been verified.** This deliberately conservative plain-text format avoids Yomitan-specific rich glossary objects. It cannot change either host's parser, scan length, word boundaries, OCR, or handling of colloquial speech.

## Built around real misses

| Text encountered | Included handling |
|---|---|
| `羅睺` | English source entries with `らご` and `らごう` readings |
| `物ノ怪` | Exact lookup alias for `物の怪` / `もののけ` |
| `鎌かけて` | Explicit colloquial phrase entry linked to `鎌を掛ける` |
| `鎌かける` | Dictionary form carrying the `v1` deinflection rule |

Other source verb/adjective rules are preserved during merging. Orthographic aliases copy the source meaning and show the original spelling. The builder does **not** invent a definition for every possible string or delete particles from arbitrary expressions.

Slang changes, names are open-ended, and context can change a phrase's meaning. This is a growing reference collection rather than a guarantee of every word or every nuance. [Report a missed word](https://github.com/Somamill/dict/issues/new?template=missing-word.yml) with a short, non-private context snippet; distinguish “manual search has no entry” from “hover did not recognize it.”

## Build and verify

Python 3.11 or later builds the archive with the standard library. Source files are downloaded to an ignored cache and checked against pinned SHA-256 hashes.

```sh
python3 scripts/build.py
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests
python3 scripts/validate.py dist/dict-master.zip
python3 branding/dot/check.py
```

The validation report records all-bank schema checks, ZIP integrity, exact example entries, and retained deinflection rules. It does not claim to simulate a browser import. Public releases include the archive, checksum, build report, and validation report. Sources are refreshed deliberately, not silently during a user's lookup.

An optional personal build can include additional source files you already use:

```sh
python3 scripts/build.py --personal --local-dir /path/to/your/dictionaries
```

**Keep `dict-personal.zip` private.** It can contain sources without verified redistribution permission and local commercial data. It is excluded from git and from the release workflow. [Folder audit](docs/folder-audit.md) · [Data licences](DATA-LICENSES.md).

## Part of dot.

A quieter way to read, listen, and learn.

[read. — Books, articles, and highlights](https://github.com/Somamill/read) · [listen. — Find your next audiobook](https://github.com/Somamill/listen) · [Immersed — Japanese worth watching](https://github.com/Somamill/immersed)

Identity follows the [shared dot. brand kit](https://github.com/Somamill/dot-brand-kit), vendored at a recorded source commit. Brand assets retain their own licence. The builder is MIT-licensed; dictionary data retains its source-specific licences.
