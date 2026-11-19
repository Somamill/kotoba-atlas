# Atlas 1.1.0 beta 2 — structured multilingual preview

This beta replaces the flattened lexical path with pinned JMdict/JMnedict and OMW records. Historical stable/beta archives are unchanged. It is a producer preview; app-default migration remains in progress.

## Japanese-source primary coverage

Counts are canonical entries with primary-language material, not unique words or universal coverage. Names are counted separately by sense kind in the manifest. Missing primary material uses English once.

| Definition family | Japanese-source entries | Primary senses | Material |
|---|---:|---:|---|
| en | 1,056,822 | 1,156,630 | definitions + proper-name translations |
| zh | 50,927 | 73,765 | translation equivalents only |
| es | 118,384 | 175,226 | definitions + equivalents |
| ar | 31,166 | 47,409 | translation equivalents only |
| id | 68,404 | 118,155 | definitions + equivalents |
| pt | 70,259 | 110,006 | translation equivalents only |
| fr | 91,746 | 142,758 | definitions + equivalents |
| ja | 94,003 | 158,070 | definitions |
| ru | 69,419 | 69,457 | definitions |
| de | 129,159 | 166,106 | definitions |

The core contains 1,056,822 Japanese-source entries (including 743,690 name entries) and 156,584 auxiliary English-source entries. These are not 1.2 million unique Japanese vocabulary words. Japanese definitions come from actual Japanese WordNet definition rows. Chinese, Arabic and Portuguese currently supply equivalents, not full native-language explanations. The full manifest also reports example references and source-language partitions.

## Packages and compatibility

Native: one shared lexical core, English fallback pack, and optional selected-language packs. Raw source records are a separate optional archive. Do not download ten lexical cores. Every pack binds the exact core hash and revision.

Browser: one standard ZIP per definition language (English or German), with frequency/pitch/kanji data and embedded source notices. Reading-only rows are compacted without removing written forms, source senses or reading-column lookup. Keep the ZIP compressed.

Both full ZIPs pass the pinned Yomitan parser/import pipeline and the public legacy Migaku SQLite importer. A representative fixture passes the actual Yomitan database adapter with fake-indexeddb, including kana-only names and written-name reading lookup. **Current live Migaku and Yomitan browser installations are not certified by these checks.**

## Corrections and evidence

- ノリのいい is canonical JMdict 2238120; definitions exclude format labels and linked-entry glosses. Metadata remains separate.
- 公儀隠密局 / 隠密局 share an attributable BLACK TORCH identification. Reading and an official translated organization name are intentionally unset.
- Stable entry/sense IDs preserve examples and legitimate homographs. ワンチャン dog/chance entries remain separate; rare-spelling tags affect ranking.
- 50 producer tests pass with required tokenizer dependencies and zero skips. All 12 native packages pass final-byte integrity/structure/regression checks.
- Final beta-2 consumer fixtures pass the native reader/installer contract checks and immersed's contract/install checks. The combined native app suite currently fails OCR recovery checks; this dictionary release does not certify camera reliability or app readiness.
- Production default activation, immersed Store migration, camera permission behavior, UI language review and new Store captures remain release gates for the apps.

See [consumer contract](../consumer-contract.md), [source lock](../../data/sources-v2.lock.json) and the release verification bundle. Actions remain disabled.

## What changed since beta 1

- Source-scoped spelling/reading restrictions survive native and browser export. English 今日 separates きょう from こんにち meanings; reverse lookup returns a valid form. German keeps its own broader source senses rather than inheriting invented English restrictions.
- Sparse form restrictions live in the shared core, independently of the installed display language. Updated readers must support the manifest's `form-restrictions` capability.
- Removed unused duplicate reverse indexes from language packs. English is 249.0 MB compressed / 1.245 GB installed, down from 313.2 MB / 1.527 GB in the beta-2 prepublication build, with identical entries, senses and source identities. The shared core is 473.7 MB compressed / 1.884 GB installed.
- One English native installation requires about 723 MB of downloads and 3.13 GB installed, plus temporary staging/rollback capacity. Optional provenance is a separate download. Language packs share the core.
- Pinned upstream parser tests cover both full browser ZIPs; 14 deinflection cases and a representative 80-row actual database-adapter fixture are included. Full final archives carry 1,297,412 term rows, 1,006,753 metadata rows, 10,384 kanji and 74 tags. Rows are not distinct words.

Stable 1.0.3 and beta 1 remain unchanged. Beta 2 is a prerelease. Current live browser-extension import, native camera calibration, app localization and Store readiness remain separate gates. No GitHub Actions were run.
