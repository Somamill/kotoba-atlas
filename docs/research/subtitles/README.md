# Japanese subtitle audit, 2026-11-18

**Development-set measurements against the unchanged Kotoba Atlas 1.0.3 ZIPs.**

| Edition | Surface + kana-reading baseline | Experimental phrase/morphology lookup | Additional content tokens retrieved |
|---|---:|---:|---:|
| German, English fallback | 87.7144% (201,815) | 97.4926% (224,313) | 22,498 |
| English | 84.4764% (194,365) | 94.7414% (217,983) | 23,618 |

Common denominator: **230,082 Japanese content-POS tokens** from **63,635 distinct Japanese cues**.
These are candidate retrieval rates, not human-reviewed sense accuracy, comprehension scores,
or comparisons against installed Migaku/Yomitan engines.

## Corpus and scope

- 144 subtitle files, 18 titles: 80 files across ten anime and 64 across eight live-action dramas.
- 6,482,908 downloaded bytes, verified by individual SHA-256 hashes.
- 72,582 parsed cues; 2,205 non-Japanese cues and 6,742 duplicate Japanese cues excluded.
- No parsing errors reported for this sample.
- Jimaku API downloads; descriptive client ID, rate-limit handling and bounded responses.
- Raw subtitles and API credentials remain local. No dialogue is included here.
- The sample helped diagnose the implementation. These are development results, not an untouched test set.
  Future generalization claims require separate titles and human-reviewed sense/span accuracy.
- Runtime fields are local end-to-end observations, with both edition jobs sharing this Mac.
  They are not browser import or universal lookup-latency benchmarks.

[German report](german-1.0.3.json) · [English report](english-1.0.3.json) ·
[Source hashes and metadata](source-manifest.json) · [Method and reproduction](../../subtitle-lookup.md)

## What the unresolved strings teach us

The ranked queue contains several different problems:

| Examples | Review category | Next step |
|---|---|---|
| フリーレン, マルシル, アーニャ | Character names, sometimes misclassified as common nouns by the analyzer | Verify against official character sources; label as fiction/proper names and rank below vocabulary. |
| 別班 | Potential established expression, with specialized drama context | Check general and specialized senses, reading and source rights before adding bilingual definitions. |
| デスノート, ラボメン | Fiction-specific object/group terminology | Preserve title/world context; do not silently treat as general Japanese. |
| 5億, 120億 | Numeric quantities | Handle number/counter interpretation; do not add every amount as a dictionary word. |
| ハハッ, ッ, ううっ | Laughter, clipped sounds or caption fragments | Review the subtitle/parser context; do not invent lexical meanings. |

Kana forms such as やめる initially looked missing because the headword used kanji.
Reading-aware retrieval removed that false gap without duplicating entries.
Part-of-speech ranking and source-checked contraction rules fixed additional lookup failures.
The reports' "lexical candidates" still contain names and artifacts; they are a review queue,
not approved additions.

## Verification

32 local unit tests pass, covering subtitle formats, encoding/ruby handling, credential origin
restrictions, episode selection, kana readings, phrase boundaries, inflection recovery,
source-backed contractions and atomic index preservation.
Ten synthetic phrase/headword regressions pass against **both complete release indexes**.
The source ZIP hashes match 1.0.3; no dictionary content or public release assets were changed.
GitHub Actions remains disabled; no cloud CI was executed.
