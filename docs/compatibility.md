# Compatibility and included features — 1.0.1

Choose **one ZIP per definition language and tool**. The English and German editions each have two alternative exports. Their word banks are byte-for-byte identical; installing both exports in one tool duplicates the words.

| Export / tool | Included | Verification |
|---|---|---|
| Yomitan full export | Plain eight-field Yomichan v3 words, native pitch/frequency, kanji and tags | All banks schema-validated; complete upstream importer parser tested; representative IndexedDB fixtures tested |
| Migaku word export | Same words, definitions, usage examples and plain-text pitch/frequency/kanji references; index and word-bank JSON only | Complete pinned public **legacy** Migaku importer core tested with real SQLite; current browser Early Access import awaits user test |
| Other Yomichan v3 importers | Standard plain-string word banks | No blanket runtime guarantee; test the host |
| Anki | Selected words/senses through the host integration | Not a native Anki deck |
| MDict, StarDict, Kobo / proprietary formats | Conversion required | Not native exports |

The full export includes 1,006,753 native term metadata records (409,568 pitch and 597,185 frequency), 10,384 kanji records and 74 tag definitions. Native pitch graphs, frequency sorting, kanji panels, audio, scanning, deinflection, OCR and Anki integration depend on the host. The Migaku word export preserves readable reference notes but does not supply native metadata-bank features.

Both editions include vocabulary, source-covered slang, phrases, grammar patterns, names, kanji references and folklore. German uses German definitions for an exact term/reading pair when available, with English gap fallback. English excludes German lexical sources. Both retain Japanese-only reference text and source names. Newer JMdict fills pairs absent from Jitendex; it does not replace every overlapping sense.

Archives contain no images, SVG, fonts, audio, executable code or nested dictionary ZIPs. Individual word banks are at most 2 MiB; this does **not** cap an importer's total memory. Sources and licence notices accompany both exports. A dictionary cannot control every application's tokenizer, selected phrase boundary or contextual interpretation.

## If preparation seems stuck

1. Cancel the old operation before starting another. Keep working installed dictionaries.
2. Use the versioned **Migaku** ZIP, leave it compressed and verify its checksum.
3. Allow space for expanded data plus database/index and temporary copies. Download size is not memory usage.
4. Update through Migaku's normal extension controls. Its official changelog documents past fixes for stalled custom imports and large-dictionary memory use; the installed version here is unknown.
5. If it still stalls, record the exact filename, extension version, elapsed time and error/report code; compare a small ordinary dictionary import. Do not delete the browser profile or learning database.

See [investigation and test scopes](migaku-1.0.1.md) and [measurements](performance.md). The reported current Early Access stall was not reproduced or observed live; protected extension UI access was unavailable.
