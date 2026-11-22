<p align="center"><img src="docs/media/atlas-icon.svg" width="112" height="112" alt="Kotoba Atlas icon"></p>

<h1 align="center">Kotoba Atlas</h1>

<p align="center">A Japanese dictionary for the reading tools you already use.</p>

<p align="center">
  <a href="https://github.com/Somamill/kotoba-atlas/releases"><img src="https://img.shields.io/badge/Download-Releases-255B63?style=flat&amp;logo=github&amp;logoColor=white" alt="GitHub releases"></a>
  <a href="https://www.reddit.com/user/dot-app/"><img src="https://img.shields.io/badge/Reddit-dot.%20apps-AD3000?style=flat&amp;logo=reddit&amp;logoColor=white" alt="dot. on Reddit"></a>
</p>

<p align="center">
  <a href="#download">Download</a> |
  <a href="#install">Install</a> |
  <a href="docs/compatibility.md">Compatibility</a> |
  <a href="DATA-LICENSES.md">Source licences</a>
</p>

Kotoba Atlas combines Japanese vocabulary, phrases, names, and kanji with pitch accent and frequency data. Choose an English dictionary or a German dictionary with English fallback.

## Download

| Edition | English | German with English fallback |
| --- | --- | --- |
| [**Stable · 1.0.3**](https://github.com/Somamill/kotoba-atlas/releases/tag/atlas-v1.0.3) | [Download ZIP](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.3/Kotoba_Atlas_English_v1_0_3.zip) | [Download ZIP](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.3/Kotoba_Atlas_German_v1_0_3.zip) |
| [**Preview · 1.1.0 beta 2**](https://github.com/Somamill/kotoba-atlas/releases/tag/atlas-v1.1.0-beta.2) | [Download ZIP](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.1.0-beta.2/Kotoba_Atlas_English_v1_1_0_beta_2.zip) | [Download ZIP](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.1.0-beta.2/Kotoba_Atlas_German_v1_1_0_beta_2.zip) |

The preview corrects formatting and cross-reference text found in older downloads, including ノリのいい. Use the stable edition if your workflow depends on it. [Stable checksums](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.0.3/SHA256SUMS) | [Preview notes and verification](docs/releases/atlas-v1.1.0-beta.2.md)

## Install

1. Download one ZIP for your preferred definition language.
2. Keep the ZIP compressed and import it in Yomitan, Migaku, or another compatible Yomichan-format reader.
3. Enable Kotoba Atlas in your reader’s dictionary settings.

[English](docs/install.en.md) | [Deutsch](docs/install.de.md) | [日本語](docs/install.ja.md)

The preview ZIPs passed the pinned Yomitan parser and the legacy Migaku importer. Live installs in current browser extensions remain unverified. Pitch graphs, frequency sorting, and kanji display depend on your reader. [Compatibility details](docs/compatibility.md)

## Look inside

<img src="docs/media/entry-preview.png" width="100%" alt="Examples from the German dictionary showing definitions, pitch accent, frequency notes, and English fallback.">

Examples from the German 1.0.3 dictionary, presented as a readable preview.

| What you can look up | What the dictionary supplies |
| --- | --- |
| Words and phrases | Definitions, spelling variants, and source-covered slang, usage notes, and examples. |
| Names and kanji | Proper-name entries, meanings, and on/kun readings. |
| Pronunciation and frequency | Pitch accent and frequency records where sources supply them. |

[Coverage and counts](docs/coverage.md) | [Dictionary sources and licences](DATA-LICENSES.md)

## Integrate or build

The native preview provides one shared lexical core, an English fallback pack, and optional language packs. Use a schema-2 reader that supports the manifest’s declared capabilities. The ten definition families have different coverage, and some supply translation equivalents only. [Consumer manifest](https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v1.1.0-beta.2/consumer-manifest.json) | [Consumer contract](docs/consumer-contract.md) | [Coverage by language](docs/releases/atlas-v1.1.0-beta.2.md#japanese-source-primary-coverage)

To build the browser ZIPs locally, use Python 3.11+ and 7-Zip 26.06:

```sh
python3 scripts/build.py
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests
```

The build verifies pinned inputs and checks the transfer budget. [Release reports](docs/releases/1.0.3) | [Source audit](docs/folder-audit.md) | [Historical releases](https://github.com/Somamill/kotoba-atlas/releases)

## Part of dot.

Kotoba Atlas powers Japanese lookup in **dict.** and is part of the [dot. app family](https://github.com/Somamill/dot-brand-kit/blob/main/CATALOGUE.md). Project code is MIT-licensed. Dictionary data and artwork retain their respective licences.

Got a question, a missing entry, or a correction? [Email Max](mailto:max@miller-max.com) or [open an issue](https://github.com/Somamill/kotoba-atlas/issues/new/choose). [Support on Ko-fi](https://ko-fi.com/somamill)
