# Atlas consumer contract, schema 2 (implementation draft)

This format is under validation. Existing schema-1 native and browser releases remain available; do not point production consumers at this draft until artifact and integration gates pass.

One indexed lexical core contains canonical entry identities, source languages, valid source spelling/reading pairs, attribution, compact source-record locators and a multilingual reverse-search index. Full original source records live once in an optional provenance package. Language packs contain structured senses. A pack binds to the exact uncompressed core SHA-256 and dictionary revision. Consumers must reject mismatched generations. History, favorites and notes belong outside these replaceable packages.

JMdict entry IDs use `jmdict:ja:<upstream-id>`. Unchanged senses have content-addressed IDs; upstream JMdict does not provide immutable sense IDs, so changed senses receive new identities. WordNet senses retain the upstream Princeton WordNet 3.0 synset identity and explicit language. Unknown identity relationships are not merged by similar text. Original source records remain available for provenance.

Definitions, tags, forms, examples, cross-references and attribution are separate fields. A linked word’s explanation is never the current word’s definition. Fictional names carry work-specific scope and sourced factual identification; unverified readings/translations remain absent.

For each canonical entry, show only valid senses in the preferred definition language. If none are available, show English once and mark fallback. Preserve the underlying other-language senses and provenance in release packages. English displays normally when English is selected. Query-language candidates are independent: Han can represent Japanese or Chinese; Latin words retain multiple candidates.

`consumer-manifest.json` records schema/revision, source languages, package role/language/format, compatibility, URL, compressed/uncompressed sizes and SHA-256, and licensed sources. Exact primary-language counts distinguish explanatory definitions from translation equivalents. Support is partial and must never be advertised as all language pairs or universal coverage.

Reference producer/query modules: `scripts/contract.py`, `scripts/contract_lookup.py`. Pinned acquisition: `scripts/acquire_sources.py` with `data/sources-v2.lock.json`. Run the release gate in an environment installed from both requirements files; unexpected skipped tokenization/lookup tests fail.

Consumers stage downloads, validate both hashes and SQLite/schema/core binding, activate a generation atomically and retain the previous working generation for rollback. Interrupted/corrupt/out-of-space updates must preserve the active dictionary. App-data updates and desktop application updates are separate.

## Reproduce locally

Install `requirements-analysis.txt` and `requirements-dev.txt` in one isolated Python environment. `ijson` streams the large upstream JSON snapshots; Sudachi is mandatory for analysis tests. Acquire data with `python scripts/acquire_sources.py`; all bytes and licence notices must match `data/sources-v2.lock.json`.

Run `python scripts/pipeline.py --output dist/<new-candidate> --revision <revision>` with the reviewed upstream Yomitan (`ce1b1bffa0e8819716317f3717932a7fe91e8d52`) and legacy Migaku (`0bc88ae46fbdc1df4d23752b3056cb25a2fd3ca0`) checkouts under `.cache/upstream/yomitan` and `.cache/upstream/migaku`. The output directory must be fresh. The pipeline checks downloadable bytes, SQLite integrity, real Japanese/German/fallback regressions, ordinary browser exports and the Chrome Base64 budget. A failure prevents a passing release packet. No publication or Actions dispatch is performed.

## Consumer examples and verified boundary

`python scripts/consumer_fixtures.py <directory>` builds small release-format indexes from attributed real JMdict records and curated fiction/usage annotations. `dict.` loads them through its Swift `DictionaryStore(core:packs:language:coreSHA256:)`; its tests cover the same canonical identities, primary-only presentation, English fallback, reverse lookup, constrained inflections, generation mismatch, staged activation, rollback and corrupt-package rejection. `immersed` loads identical bytes through `server/atlas-contract.cjs` and projects selected senses into its existing entry interface. Its community server can read an activated schema-2 generation; the Store edition and updater migration remain pending. Production defaults remain on their existing catalogues until final corpus and app integration gates pass.

The Swift tests pass on the Mac, including the existing full offline English package and real horizontal/vertical OCR. This is not an iPhone/iPad UI or full schema-2 corpus performance result. The phone is excluded for this run.

## Coverage boundaries

All ten definition-language families have explicit package and reverse-index capabilities. Headword adapters currently cover Japanese and English; reverse queries search all included definition-language glosses and equivalents. Arabic and Portuguese WordNet records provide labelled translation equivalents, not full explanatory native definitions. Japanese includes actual Japanese WordNet definitions. JMdict supplies German/Russian and other available language senses; source coverage varies by entry. No UI translation or English fallback is counted as native-definition coverage.

Curated slang annotations attach to explicitly reviewed JMdict identities where verified (`data/usage-identities.json`). ワンチャン as “one chance/maybe” stays distinct from the dog homograph. Upstream records are not merged merely because gloss text looks alike. Unchanged sense IDs survive example enrichment; changed semantic content receives a new sense identity.
