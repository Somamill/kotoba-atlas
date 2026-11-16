# Complete-edition preparation — 1.0.2

There is exactly **one complete ZIP per definition language**. The smaller word-only profiles from 1.0.1 are retired. Full native data is included alongside readable reference notes; no extra packs are needed.

| Edition | Lookup pairs | Download | Expanded |
|---|---:|---:|---:|
| German, with English gap fallback | 1,566,695 | 61.19 MB | 397.44 MB |
| English | 1,080,167 | 51.60 MB | 341.29 MB |

Every 1.0.1 word, metadata, kanji and tag bank is byte-identical. New filenames use underscores and an explicit version; existing full-edition internal titles remain stable. Sources, licences and examples remain included.

## Import evidence

Both complete archives were imported through the pinned public legacy Migaku Anki importer core using real SQLite table/index creation and insertion. German imported all 1,566,695 records in 14.724 seconds; English imported all 1,080,167 in 10.846 seconds. Process peak RSS was approximately 1,767 MB and 1,214 MB respectively. The legacy importer selects ordinary word banks and ignores native metadata/kanji/tag banks. GUI/language registry behavior is represented by a façade; optional external frequency lists are outside scope.

The pinned upstream Yomitan parser checks complete archives with a counting storage façade. Representative fixtures exercise the actual database adapter with fake IndexedDB and 14 deinflection cases. All data banks also pass upstream schemas. Exact scopes and input hashes are in [release evidence](releases/1.0.2/).

These verification runs are **not installed extension UI, browser indexing or lookup-latency benchmarks**. Other checks ran on the same Mac, so elapsed times are observations rather than a controlled comparison with earlier versions. Full persistent browser imports, native UI presentation and current Migaku Early Access remain unverified.

Each data bank is at most 2 MiB, but that does not cap importer memory. Allow room for expanded data plus temporary copies, indexes and databases. The complete ZIP is larger than the retired word-only profile because native feature data is included. Hosts determine which native features they can display; readable reference notes remain available to word-only importers.

Historical split-profile measurements and the original stalled-import investigation are retained in [1.0.1 evidence](releases/1.0.1/) and [the investigation](migaku-1.0.1.md). They do not establish that the current browser preparation stall is fixed.
