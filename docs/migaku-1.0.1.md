# Migaku investigation and 1.0.1 release evidence

## Report and response

The user reported an indefinite “preparing files” screen while importing German 1.0.0. Protected extension UI access was unavailable, so the live failure and installed extension version remain unknown. The user will test the replacement later. **1.0.1 is not certified against the current browser Early Access importer.**

The [official Migaku changelog](https://migaku.com/blog/changelog) records custom dictionary installs hanging or appearing installed without working in the April 19, 2026 Early Access 12 fixes, and lower-memory, more reliable large-dictionary installs in the May 5 Early Access 13 / standard 1.29.4 notes. These are dated evidence of relevant fixes, not a claim that those versions are latest or installed here.

The [official organization](https://github.com/migaku-official) contains both current Anki bridge code and a separate legacy dictionary add-on. Public current browser importer code/contract was not located. The deprecated [legacy manual](https://github.com/migaku-official/Migaku-legacy-guides/blob/master/content/en/tools-guides/migaku-dictionary/manual.md) documents Yomichan word imports and excludes native Yomichan frequency/kanji imports. Its standards must not be presented as current Early Access certification.

The reviewed [legacy importer](https://github.com/migaku-official/Migaku-Dictionary-Addon/blob/0bc88ae46fbdc1df4d23752b3056cb25a2fd3ca0/src/dictionaryManager.py) accumulates word banks into one list, converts plain-string glossaries and writes SQLite. Its filename-derived dictionary name reaches SQL table creation with only spaces normalized. The Migaku export therefore uses ASCII letters, digits and underscores, with the version in its download filename and a stable internal title. Full Yomitan titles retain their 1.0.0 identity for updates.

## Changes

- Alternative **single-file Migaku exports** retain identical word banks but omit native metadata/kanji/tag JSON that word-only importers do not need. Source manifests are text; notices and licences remain. Full Yomitan exports retain native features.
- `index.json` is first; every word bank stays within 2 MiB. These reduce avoidable work but cannot cap total importer memory.
- Exact duplicate definition bodies share source credit; distinct sense/register text remains separate. Portable part-of-speech and register tags are added while original inflection rules are preserved.
- Nine attributed bilingual usage records cover てぇてぇ, ぬまる, 沼る, 推し活, 推し活する, ワンチャン, ガチ恋, リアコ and 蛙化現象. Original examples illustrate register and distinguish narrow/broader usage. This is targeted coverage, not an exhaustive slang claim.
- All old lookup pairs remain. German gains four pairs and English six because several new usage records enrich existing pairs.

## Reproducible checks

Pinned upstream sources:

- Migaku legacy dictionary add-on: `0bc88ae46fbdc1df4d23752b3056cb25a2fd3ca0`.
- [Yomitan](https://github.com/yomidevs/yomitan): `ce1b1bffa0e8819716317f3717932a7fe91e8d52`.

`scripts/test_migaku_import.py --help` documents the harness. It loads reviewed legacy importer functions and actual SQLite creation/insertion functions without starting Anki. Both complete word exports imported into real SQLite. GUI, language registry and optional external frequency-list behavior are outside that scope. This does not exercise the current browser extension.

`scripts/test_yomitan_import.mjs` runs the actual upstream parser/validator over the complete full archives with a counting storage façade. `scripts/import_fixture.py` supplies a small representative archive for a second run through the actual DictionaryDatabase adapter and fake IndexedDB. This second path tests database conversion and queries, not full persistent browser installation. Both languages pass 14 transformations including 鎌かけて, 鎌を掛けていた, 沼った, ぬまらない, 推し活した, 食べていました and 楽しくなかった. Source/host deinflection enables these forms; it is not a guarantee of hover segmentation in every app.

All four ZIPs pass index/word-bank schemas and profile-policy checks. Full exports additionally pass native-bank schemas. Coverage comparisons assert no old term/reading pair disappeared and every word bank is byte-identical between tool profiles. Sixteen project unit tests and the existing brand check pass. Machine-readable [release reports](releases/1.0.1/) include hashes and test scopes; [performance](performance.md) separates measured paths from untested browser behavior.

## Research decisions

[Jitendex](https://jitendex.org/) informed readable grouped definitions and avoiding repeated source metadata; only exact duplicate bodies are combined. [Yomitan's advanced options](https://yomitan.wiki/advanced/) and [Anki integration](https://yomitan.wiki/anki/) distinguish dictionary content from scanner, audio and mining functions. [Jiten's frequency guidance](https://jiten.moe/guides/yomitan-frequency-dictionaries) explains corpus-specific ranks: keep the attributed global list rather than mix incomparable ranks.

Learner discussions on [dictionary clutter](https://www.reddit.com/r/LearnJapanese/comments/1u9ml3c/daily_thread_for_simple_questions_minor_posts/), [coverage and slang](https://www.reddit.com/r/LearnJapanese/comments/1uzge8z/daily_thread_for_simple_questions_minor_posts/) and [Migaku storage/import experience](https://www.reddit.com/r/ImmerseWithMigaku/comments/1n1blde/) are anecdotal design input, not technical specifications. They support concise definitions and explicit register labels rather than importing every available commercial source. Redistribution rights still govern public editions.

Usage references are attached per entry in `data/usage-notes.json`, including [てぇてぇ](https://en.wiktionary.org/wiki/てぇてぇ), [ぬまる](https://en.wiktionary.org/wiki/ぬまる), [推し活](https://en.wiktionary.org/wiki/推し活), [ワンチャン](https://en.wiktionary.org/wiki/ワンチャン), and the broader/narrower senses of [蛙化現象](https://ja.wiktionary.org/w/index.php?title=蛙化現象&oldid=1964483). Original examples and German adaptations are identified in the licence notices.
