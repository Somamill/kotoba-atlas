# Research and applied lessons

Reviewed for Kotoba Atlas 1.0.0 on 2026-11-16. Community reports are experience, not controlled evidence or a substitute for importer documentation. Changes below are explicit project decisions.

## Current coverage without stacking the same dictionary

A [LearnJapanese discussion about dictionary priority](https://www.reddit.com/r/LearnJapanese/comments/1uzge8z/daily_thread_for_simple_questions_minor_posts/) describes using a bilingual dictionary first and specialist references as supplements. Another [discussion of dictionary updates](https://www.reddit.com/r/LearnJapanese/comments/1i970wk/) notes the value of refreshed JMdict slang coverage and differing preferences for concise versus richer entries.

**Applied:** keep Jitendex's richer notes/examples as the primary overlapping English record, use newer JMdict for missing pairs, and retain independent Wiktionary material. German meanings take priority in the German edition, with English filling coverage gaps. Names have a lower score than vocabulary. These choices reduce repeated explanations; they do not claim that all source senses are identical.

## Migaku formatting and import friction

A recent [Migaku community discussion](https://www.reddit.com/r/ImmerseWithMigaku/comments/1wqr7oj/migakus_pros_and_cons/) reports custom-dictionary formatting friction. [Migaku's published legacy format documentation](https://github.com/migaku-official/Migaku-legacy-guides/blob/master/content/en/tools-guides/migaku-dictionary/manual.md#supported-file-formats) distinguishes word dictionaries from kanji/frequency formats.

**Applied:** plain Yomichan v3 word banks, no modern structured glossary objects, bounded word-bank sizes, and pitch/frequency/kanji information rendered as ordinary text. Native metadata/kanji banks are also retained for tools supporting them; their file types are validated separately. Native metadata and character banks are included in the same ZIP for supporting tools. Current Early Access import is still a separate runtime check; the old Anki add-on documentation cannot certify it. Obsolete forum advice about downgrading Anki is not adopted.

## Anki context and formatting

An [Anki forum report about Yomitan glossary formatting](https://forums.ankiweb.net/t/help-with-typeans-not-displaying-ordered-lists-yomitan/50754) shows how list markup and line boundaries can produce confusing typed-answer display. The [official Anki text-import manual](https://docs.ankiweb.net/manual/importing/text-files) describes importing notes, which is different from installing a lookup dictionary.

**Applied:** preserve separators when flattening structured definitions, tables and furigana. Recommend saving the encountered sentence and a relevant sense through the host's mining integration. Do not export a million-word dictionary as a default Anki deck or change the user's templates unasked.

## Frequency and pronunciation

[Jiten's official guide](https://jiten.moe/guides/yomitan-frequency-dictionaries) explains global/media-specific ranks and explicitly permits redistribution under CC BY-SA 4.0. [Yomitan's official advanced guide](https://yomitan.wiki/advanced/) treats audio playback as a host feature.

**Applied:** add a pinned, attributed global Jiten rank snapshot to both editions. Keep WaDoku pitch/devoicing data as readable notes and native metadata. Include native Jiten frequency and KANJIDIC character/tag banks in each archive. External audio and support for native graphs/sorting remain tool-dependent; no unsupported universal-feature claim is made.

## Performance checked on the actual files

The old personal ZIP expanded to 769.4 MB. Language selection, overlap removal, omission of metadata-only results, compact rank/pitch notes and bounded word and native-metadata banks reduce the payload without splitting features into separate installations. [Performance report](performance.md) contains exact sizes and scoped offline preparation measurements. It does not claim to benchmark the Migaku browser importer.


## 1.0.1 importer and usage research

See [the dated investigation, primary sources and applied changes](migaku-1.0.1.md). The result is one ZIP per language/tool, identical word coverage across profiles, exact-body deduplication, portable POS/register tags and nine bilingual usage records. Current Migaku Early Access live import awaits user testing. Forum advice is treated as anecdotal; scanner/Anki/audio functions remain host responsibilities.


## 1.0.2: simplify the recommendation

The split profiles in 1.0.1 added a confusing choice. The canonical recommendation is now one complete language edition for every supporting Yomichan-format host. The pinned public legacy Migaku importer ignores native-bank families while reading the ordinary word banks; tests now use the complete 1.0.2 ZIPs. Native data stays available to Yomitan and other supporting hosts. Current Migaku Early Access still awaits live verification; the original source investigation and its limits remain above and in `migaku-1.0.1.md`.


## 1.0.3 transfer fix

All decoded 1.0.2 records and source notices are retained. Lossless clustering and stronger standard Deflate keep the complete language editions below Chrome/Migaku's Base64 message budget. See [the confirmed failure, remedy and evidence](transfer-limit.md).
