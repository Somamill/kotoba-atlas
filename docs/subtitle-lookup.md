# Subtitle-driven lookup research

This is next-release research against the unchanged **Kotoba Atlas 1.0.3** archives.
The experimental lookup helper runs locally. It is not injected into Migaku or Yomitan,
and importing a dictionary ZIP does not install a new scanning engine.

## Corpus

The sample uses the [official Jimaku API](https://jimaku.cc/api/docs):
18 selected titles, eight files per title, covering anime and live-action dramas.
Titles and file selection are specified in [the sampling configuration](../data/corpus-titles.json).
The downloader authenticates using a private key, identifies its client, obeys rate-limit headers,
resumes verified files and bounds each response and the total download size.
Credentials are never forwarded outside Jimaku HTTPS, including through redirects.

Raw subtitle files remain local and are not committed or included in a dictionary.
Published reports contain aggregates, headword candidates and source-file hashes, not dialogue.
The catalogue's availability is not a redistribution licence for the subtitle text.
Every downloaded file is hashed; Jimaku URLs may subsequently change or disappear.

ASS/SSA, SRT and VTT parsing removes timing, override tags, drawing cues and ruby-reading tags.
Leading speaker labels are removed; internal parentheses remain.
UTF-8, UTF-16 and CP932/EUC-JP are decoded without silently replacing invalid characters.
Repeated Japanese cues are deduplicated across the sample.
English-only cues and oversized cues are skipped and counted.
Subtitle errors, OCR mistakes, songs and caption conventions can still affect the results.

## Atlas Lookup Lab

The helper retrieves existing entries; it does not generate meanings.

1. Build a compact, read-only SQLite index directly from the released ZIP.
   The ZIP is unchanged and its SHA-256 binds the index to that edition.
   Pitch/frequency-only reference rows cannot masquerade as lexical definitions.
2. Tokenize with pinned [SudachiPy and its core dictionary](https://github.com/WorksApplications/sudachi.rs).
   Preserve the original character offsets and inspect dictionary form, normalized form,
   reading and part of speech.
3. Search exact headwords and kana readings, then dictionary-form and analyzer-normalized candidates.
   Matching a kana reading is distinguished from matching the written headword.
4. Search a bounded lattice of phrases, up to eight tokens and 32 characters,
   without crossing whitespace or punctuation. Dynamic programming chooses a sequence
   that favors lexical coverage, supported phrases and grammatical fit.
5. Reverse a small, explicit set of colloquial endings such as ってる and ちゃった.
   Accept a result only when the existing headword has the required source verb rule.
   This is a bounded supplement, not a replacement for Yomitan's full deinflection engine.
6. Return the matched span, headword, method, original source definitions when requested,
   and alternative headword/readings. Names are distinguished from lexical entries.

Exact fragments receive a penalty when they do not fit the analyzer's verb/adjective evidence.
This avoids treating an inflected verb stem as an unrelated noun just because it is an exact string.
Homophones and source disagreements remain ambiguous: ranking is a heuristic, not sense disambiguation.
No unrestricted fuzzy matching, arbitrary particle deletion or automatic dictionary insertion is used.

## How to interpret the measurements

The baseline retrieves entries for each original content token by headword **or kana reading**.
The experimental path additionally uses phrase spans, dictionary forms, normalization and checked contractions.
The denominator is Japanese content-POS tokens, not every character or every subtitle.
Names-only matches are not credited as lexical coverage. Analyzer POS classifications can be wrong.

These are **candidate retrieval rates**. A retrieved entry is not proof of a correct sense,
translation, reading comprehension or faithful subtitle text.
This is not a comparison against Migaku's or Yomitan's installed lookup engines, which already
perform their own segmentation and deinflection.
The 18 titles are a convenience sample, not a representative census of Japanese.
The same corpus helped diagnose the helper, so final rates are development-set measurements;
an untouched title-level holdout is required before generalizing improvement claims.

Reports and hashes are in [the research evidence folder](research/subtitles/).
Ten short synthetic examples, not copied subtitle dialogue, are
[regression fixtures](../data/lookup-regressions.json).
Both complete edition indexes must pass them.

## Next-release decisions

Review the ranked misses in their original local contexts before adding anything:

| Candidate class | Action |
|---|---|
| Existing headword under a kana reading or inflected form | Fix retrieval; do not duplicate the dictionary entry. |
| Established missing lexical expression | Verify meaning, reading, register and distributable source before adding German/English content. |
| Fixed phrase or spelling variant | Add a narrowly scoped, labeled alias with its canonical expression and regression test. |
| Character names, invented world terms | Consider a separately labeled source-attributed name layer; never present them as ordinary vocabulary. |
| Laughter, breaths, truncation, OCR and SDH labels | Improve parsing/classification or leave unresolved; do not invent a definition. |

Do not turn every unresolved string into an entry. New definitions still need source/licence review.
A future ZIP must pass the existing record-retention, schema and Chrome Base64-budget checks.
The German archive is already close to the transport cap, so corpus expansion cannot bypass that guard.
The dictionary release remains **1.0.3** until the resulting content and host behavior are verified.

## Run locally

Python 3.13 is used for the tested optional analysis environment.
The tokenizer and its dictionary are development dependencies, not extra dictionary imports.

```sh
python3.13 -m venv .cache/analysis-venv
.cache/analysis-venv/bin/pip install -r requirements-analysis.txt -r requirements-dev.txt

# Save only your key in ~/.config/kotoba-atlas/jimaku-api-key.
# Keep the directory private (700) and the key file private (600).
.cache/analysis-venv/bin/python scripts/download_subtitles.py \
  --output .cache/subtitle-audit/corpus

.cache/analysis-venv/bin/python scripts/lookup.py \
  --archive dist/atlas-v1.0.3/Kotoba_Atlas_German_v1_0_3.zip \
  --index .cache/subtitle-audit/german.sqlite --build

.cache/analysis-venv/bin/python scripts/lookup.py \
  --index .cache/subtitle-audit/german.sqlite \
  --check-regressions data/lookup-regressions.json

.cache/analysis-venv/bin/python scripts/lookup.py \
  --index .cache/subtitle-audit/german.sqlite \
  --archive dist/atlas-v1.0.3/Kotoba_Atlas_German_v1_0_3.zip \
  --text '鎌かけてるんじゃねえよ。'

.cache/analysis-venv/bin/python scripts/subtitle_audit.py \
  --corpus .cache/subtitle-audit/corpus \
  --index .cache/subtitle-audit/german.sqlite \
  --output .cache/subtitle-audit/german-report.json
```

Use the English ZIP and a separate index to reproduce the English report.
The index is rebuilt atomically; failed builds preserve an existing index.
The released ZIP and installed browser dictionaries are never modified.
