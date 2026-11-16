# Preparation measurements

The earlier personal prototype was a poor default for a browser import: 2.42 million word records and 769.4 MB expanded. The new editions keep every public feature layer in one file per definition language, with native metadata plus plain-text fallback notes.

| Archive | Download | Expanded | Largest data bank | Offline parse | Python process peak RSS |
|---|---:|---:|---:|---:|---:|
| Earlier personal prototype | 148.5 MB | 769.4 MB | 5.29 MiB | 4.557 s | 267.8 MB |
| English v1.0.0 | 51.5 MB | 343.7 MB | 2.00 MiB | 2.366 s | 155.3 MB |
| German v1.0.0 | 61.3 MB | 408.3 MB | 2.00 MiB | 2.889 s | 227.8 MB |

These are single sequential runs of the supplied `scripts/benchmark.py` on the same Mac. The script decompresses and parses every word, native metadata, kanji and tag bank, discarding a bank before moving on. It is **not a benchmark of Migaku import, Yomitan import, browser memory, indexing, lookup latency or network time**. Browsers can hold multiple copies and build additional indexes, so their timing and memory may differ substantially.

The English prepared payload is about 55% smaller than the earlier personal prototype, and the German payload about 47% smaller. All data banks are capped at 2 MiB; upstream Jiten's original 56.7 MB metadata bank is split without dropping records. The final archives include over one million native pitch/frequency records as well as their word-bank notes, so file preparation is not free or instant.

## Changes that reduce work

- Select a definition language; use German first and English only for uncovered pairs in German.
- Retain one primary overlapping English-core record, preserving all source inflection rules.
- Omit metadata-only word results. Native metadata remains available to supporting tools.
- Compact repeated metadata descriptions and keep source notices outside the search records.
- Bound word, metadata and character banks. Preserve reading variants rather than collapsing homographs.
- Use plain glossary strings rather than rich visual objects, fonts, image archives or audio files.

The stall reported in Migaku was not observed directly because access to extension pages was blocked. The file size and bank-allocation problems are confirmed offline; the new edition still needs a live import check in the installed Early Access version.
