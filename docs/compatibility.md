# Compatibility and included features

Each edition is one ZIP with an `index.json`, ordinary eight-field Yomichan v3 `term_bank_*.json`, native `term_meta_bank_*.json` for pitch/frequency, native `kanji_bank_*.json`, and character tag banks at the root. It is not a ZIP of nested feature dictionaries. Glossaries are strings, and individual banks are at most 2 MiB. The filename, internal revision, release title and reports identify version 1.0.0.

| Tool / capability | Status |
|---|---|
| Yomitan word-dictionary structure | All word, metadata, kanji, tag and index banks validated against pinned upstream schemas; live import untested |
| Migaku plain Yomichan word import | Legacy format is documented; current browser Early Access live import untested |
| Other Yomichan v3 word-dictionary importers | Standard structure supplied; no blanket runtime guarantee |
| Anki | Mine selected words/senses via the host's integration; this ZIP is not a native Anki deck |
| MDict, StarDict, Kobo and arbitrary proprietary formats | Not their native format; conversion would be required |
| Pronunciation audio, OCR, sentence parsing, hover boundaries | Host features, not dictionary-file features |

Both editions include vocabulary, slang where covered by the sources, phrases, source usage notes/examples, grammar patterns, names, kanji readings/meanings, folklore, pitch positions/devoicing and global frequency ranks. Pitch and frequency appear as plain notes and are also supplied in native metadata banks. Supporting Yomichan importers can use native pitch graphs and frequency columns; word-only tools may ignore those banks. Native kanji/tag banks are included alongside character reference text. Current Migaku Early Access behavior with this combined archive remains unverified.

The German edition uses German definitions when available for the exact term/reading pair. Otherwise it uses English. Both editions retain Japanese-only reference explanations and source names. The English edition excludes German lexical sources. Newer JMdict fills pairs absent from Jitendex; it does not silently replace every overlapping Jitendex sense with a newer JMdict sense.

No images, font packages, audio files, card-template scripts or executable code are inside the dictionary archives. Source metadata and licence notices are included once, outside the term banks. Sources retain their own terms and attribution.

## If preparation seems stuck

1. Avoid running two dictionary imports at once. Cancel the old personal-file operation before trying a new edition.
2. Confirm the complete download matches the published checksum, and leave the ZIP compressed.
3. Allow space for uncompressed data plus the host's database/index and temporary copies. The compressed download size is not the runtime memory requirement.
4. Check that the host extension is current and retry its normal import action. Preserve your existing installed dictionaries until the new one works.
5. Report the exact edition filename, extension version, stage/message, and whether a small ordinary dictionary imports successfully. Do not delete a browser profile or learning database as a troubleshooting shortcut.

This project could inspect and measure its own files, but could not access the protected Migaku extension page. The reported preparation stall was therefore not observed or reproduced live. Offline preparation improvements are measured separately in `performance.md`.
