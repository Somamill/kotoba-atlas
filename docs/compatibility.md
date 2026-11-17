# One complete edition per definition language — 1.0.3

Download **German** (with English fallback) or **English**, then use that same ZIP in each supporting tool. No separate Migaku version or feature packs are required. Each includes ordinary Yomichan v3 word banks, native pitch/frequency metadata, kanji/tag banks, source notices and licences. Readable references are also included as ordinary word content.

| Capability | Supplied in the ZIP | Host requirement / verification |
|---|---|---|
| Words, readings, source-covered slang, phrases, examples, grammar, names and folklore | Complete plain-string word banks | Both full editions tested through the public legacy Migaku importer into SQLite and upstream Yomitan parser |
| Pitch, frequency, kanji | Native banks **and** readable references | Native graphs, rank columns and character panels require app support; word-only importers use the text |
| Inflected forms | Source rules and explicit phrase aliases | Upstream Yomitan deinflection tests cover 14 cases; exact hover/scan boundaries remain host-dependent |
| Anki | Lookup content for host mining integration | Not an Anki deck; app/add-on integration required |
| Audio, OCR and sentence analysis | Not bundled | Host feature or service |
| MDict, StarDict, Kobo and proprietary formats | Not native exports | Conversion required |

Each data bank is at most 2 MiB, but some importers load many banks together. No images, SVG, fonts or executable code are bundled. German selects German lexical definitions for an exact term/reading pair when available, otherwise English; both editions retain Japanese reference text and attribution.

## Verification limits

The public legacy Migaku importer identifies word banks and ignores native Yomichan bank families. Earlier complete 1.0.2 archives were tested against that legacy path. Version 1.0.3 retains every decoded record and passes new complete-archive schema, content-parity and upstream Yomitan parser checks. That source is the legacy Anki importer, not current browser Early Access. The upstream Yomitan parser checks all full-archive banks; representative fixtures exercise its actual database adapter with fake IndexedDB. The current Migaku console identified a Base64 message-size failure. Version 1.0.3 passes an encoded-size guard and the user confirms completed German installation and a working 物ノ怪 lookup on 1.33.0-earlyaccess.2. This is user-reported verification; direct inspection of the installed extension was blocked by the browser tool URL policy. English live import, installed pitch/frequency presentation and persistence after restart remain unverified. Full persistent Yomitan browser installation and native UI presentation remain untested. See [the transfer fix](transfer-limit.md). Reports and hashes: [1.0.3 evidence](releases/1.0.3/).

A complete ZIP supplies every included data layer, but cannot force an app to implement native graphs, sorting, audio or scanners. It also does not guarantee every Japanese expression/context.

## Upgrade and troubleshooting

1. Keep the ZIP compressed and verify its published checksum. Use **one** edition per definition language; German already contains English fallback.
2. Cancel a stalled earlier import before trying the replacement. Keep working installed dictionaries until success.
3. A 1.0.0/1.0.1 full edition retains the same internal title for updates. A 1.0.1 `_Migaku` profile has a different title: import the complete edition normally, then disable/remove the old profile after success. Do not install both together as permanent dictionaries.
4. Allow room for expanded data, database/index and temporary copies. If preparation still stalls, record filename, extension version, elapsed time and any error/report code. Use the app's normal update/retry controls; do not delete a browser profile or learning database.

The original stall investigation is retained as [1.0.1 history](migaku-1.0.1.md). The earlier split-export recommendation is superseded by this single-file release.
