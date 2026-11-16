# Changelog

## Kotoba Atlas 1.0.1 — 2026-11-16

- Add one-file Migaku word exports in English and German. All word banks and readable reference notes are identical to their full exports; only native Yomitan bank families are omitted from the Migaku profile.
- Use ASCII/underscore Migaku names, put the index first, preserve source notices, and retain the existing full-export update identities.
- Merge exact duplicate lexical explanations while retaining source credit and keeping register differences separate. Preserve POS and usage tags, and compact pitch notes without removing native metadata.
- Add nine bilingual usage entries with original examples, including てぇてぇ, 沼る and the inflectable phrase 推し活する. Distinguish narrower/broader 蛙化現象 usage.
- Add full public legacy Migaku-to-SQLite import checks, full upstream Yomitan parser checks, representative IndexedDB checks, and 14 real upstream deinflection cases. Verify that every 1.0.0 lookup pair remains available.
- Current Migaku Early Access live import is not certified; user verification is pending. Graphs/sorting, scanning and Anki integration depend on the host. The public Migaku code exercised here is the legacy Anki importer, not current browser EA source.

## Kotoba Atlas 1.0.0 — 2026-11-16

- Name the dictionary resource Kotoba Atlas, with exactly one complete English edition and one complete German edition.
- Include version 1.0.0 in both dictionary filenames and provide stable update manifests.
- Remove overlapping English-core explanations and use English fallback for gaps in the German edition.
- Rank names below vocabulary, omit metadata-only word results, and bound term-bank preparation allocations.
- Add licensed Jiten global frequency data, native kanji/pitch/frequency banks for supporting tools, and readable word-bank notes for word-only tools.
- Preserve inflection rules and test real reading examples. Include source provenance, hashes, compatibility notes, and scoped offline preparation measurements.

Earlier `dict.` prototype releases remain in GitHub history under their original tags. They are not the Kotoba Atlas product version series.
