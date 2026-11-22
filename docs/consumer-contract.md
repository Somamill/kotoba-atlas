# Atlas consumer contract, schema 2

Schema 2 is available in the Atlas beta catalogue. Stable browser and schema-1 native packages remain available.

One indexed lexical core contains canonical entry identities, source languages, valid source spelling/reading pairs, attribution and a multilingual reverse-search index. Sense/form payloads retain source-record references. Full original source records and their entry associations live once in an optional provenance package, with sources and licence notices. Language packs contain structured senses. A pack binds to the exact uncompressed core SHA-256 and dictionary revision. Consumers must reject mismatched generations. History, favorites and notes belong outside these replaceable packages.

JMdict entry IDs use `jmdict:ja:<upstream-id>`. Unchanged senses have content-addressed IDs; upstream JMdict does not provide immutable sense IDs, so changed senses receive new identities. WordNet senses retain the upstream Princeton WordNet 3.0 synset identity and explicit language. Unknown identity relationships are not merged by similar text. Original source records remain available for provenance.

Definitions, tags, forms, examples, cross-references and attribution are separate fields. A linked word’s explanation is never the current word’s definition. Fictional names carry work-specific scope and sourced factual identification; unverified readings/translations remain absent.

For each canonical entry, show only valid senses in the preferred definition language. If none are available, show English once and mark fallback. Preserve the underlying other-language senses and provenance in release packages. English displays normally when English is selected. Query-language candidates are independent: Han can represent Japanese or Chinese; Latin words retain multiple candidates.

`consumer-manifest.json` records schema/revision, source languages, package role/language/format, compatibility, URL, compressed/uncompressed sizes and SHA-256, and licensed sources. Exact primary-language counts distinguish explanatory definitions from translation equivalents. Support is partial and must never be advertised as all language pairs or universal coverage.

Reference producer/query modules: `scripts/contract.py`, `scripts/contract_lookup.py`. Pinned acquisition: `scripts/acquire_sources.py` with `data/sources-v2.lock.json`. Run the release gate in an environment installed from both requirements files; unexpected skipped tokenization/lookup tests fail.

Consumers stage downloads, validate both hashes and SQLite/schema/core binding, activate a generation atomically and retain the previous working generation for rollback. Interrupted/corrupt/out-of-space updates must preserve the active dictionary. App-data updates and desktop application updates are separate.

## Storage and generation checks

Package descriptors carry exact `compressedBytes` and `uncompressedBytes` and SHA-256 values for each representation. New bound descriptors also expose `coreSha256` before download. This optional schema-2 field duplicates the core's `uncompressedSha256`; it is absent on older manifests. Verify the installed package's `about.core_sha256` even when the field is present. A new core hash requires its own bound packs, even when the only core change is SQLite statistics or index layout.

Use the sizes for disk planning before staging a generation. Allow for compressed downloads, expanded staged files and any active generation retained for rollback at the same time. Reuse a completed package only after its bytes and generation have been checked. Package lengths and hashes support verification; interrupted transfer resumption depends on the consumer and transport.

## Reproduce locally

Install `requirements-analysis.txt` and `requirements-dev.txt` in one isolated Python environment. `ijson` streams the large upstream JSON snapshots; Sudachi is mandatory for analysis tests. Acquire data with `python scripts/acquire_sources.py`; all bytes and licence notices must match `data/sources-v2.lock.json`.

Run `python scripts/pipeline.py --output dist/<new-candidate> --revision <revision>` with the reviewed upstream Yomitan (`ce1b1bffa0e8819716317f3717932a7fe91e8d52`) and legacy Migaku (`0bc88ae46fbdc1df4d23752b3056cb25a2fd3ca0`) checkouts under `.cache/upstream/yomitan` and `.cache/upstream/migaku`. The output directory must be fresh. The pipeline writes into a sibling `.<name>.partial` directory on the same filesystem and renames it after all checks and output hashes are complete. After abrupt termination, a remaining partial directory is quarantined. Use a fresh output name to retry, or clear your own staging directory after confirming its writer has stopped. The pipeline checks downloadable bytes, SQLite integrity, real Japanese/German/fallback regressions, ordinary browser exports and the Chrome Base64 budget. A failure prevents a passing release packet. No publication or Actions dispatch is performed.

## Consumer examples and verified boundary

`python scripts/consumer_fixtures.py <directory>` builds small release-format indexes from attributed real JMdict records and curated fiction/usage annotations. `dict.` loads them through its Swift `DictionaryStore(core:packs:language:coreSHA256:)`; its tests cover the same canonical identities, primary-only presentation, English fallback, reverse lookup, constrained inflections, generation mismatch, staged activation, rollback and corrupt-package rejection. `immersed` loads identical bytes through `server/atlas-contract.cjs` and projects selected senses into its existing entry interface. The community migration branch also implements a staged background installer, checks the package bytes and core binding, and retains the previous generation for rollback ([narai PR #24](https://github.com/Somamill/narai/pull/24)). Public narai main still documents a separate bundled 1.0.0 Store dictionary. The private Store build and any deployed catalogue switch require independent verification. The producer candidate leaves the existing release catalogues intact.

See the [producer reliability report](validation/producer-reliability.md) for regenerated consumer fixtures, full-corpus checks and remaining device verification.

## Coverage boundaries

All ten definition-language families have explicit package and reverse-index capabilities. Headword adapters currently cover Japanese and English; reverse queries search all included definition-language glosses and equivalents. Arabic and Portuguese WordNet records provide labelled translation equivalents, not full explanatory native definitions. Japanese includes actual Japanese WordNet definitions. JMdict supplies German/Russian and other available language senses; source coverage varies by entry. No UI translation or English fallback is counted as native-definition coverage.

Curated slang annotations attach to explicitly reviewed JMdict identities where verified (`data/usage-identities.json`). ワンチャン as “one chance/maybe” stays distinct from the dog homograph. Upstream records are not merged merely because gloss text looks alike. Unchanged sense IDs survive example enrichment; changed semantic content receives a new sense identity.

## Form-specific meanings (1.1.0 beta 2)

The core advertises required `form-restrictions` capability in `about` and the
manifest. Readers reject required capabilities they do not implement. Each sense
can restrict `spellings` and `readings`; absent lists or `*` mean unrestricted.
Match source spelling/reading pairs before choosing primary senses or fallback.
Alias chains resolve to source forms, bounded to eight links. Width normalization
does not erase case when choosing a source spelling.

Conditions belong to the individual source sense and language. Do not copy an
English condition onto a German or Russian translation: those sources can group
meanings differently. The English 今日 / ＆ examples below test English senses;
the German edition is checked against its own broader source conditions.

A written query without an explicit reading retains valid meanings for the
spelling's source readings, with reading conditions displayed. A reading query
or explicit reading excludes other readings' meanings: きょう must not inherit
the “these days” sense of こんにち. “＆” and lowercase “and” must not inherit the
Boolean-operator sense restricted to ＡＮＤ. Source sense order is display metadata,
not part of stable identity; adding examples does not change that identity.

`reverse_keys.form_hint` carries sparse spelling/reading conditions for every
indexed language, independently of installed display packs. Choose an applicable
source form for a reverse hit (“nowadays” → 今日 / こんにち), then apply the preferred
definition-language policy. Preserve reading context in details and history.

Frequency and pitch remain separate references. Keep each frequency source and
scale; do not take a minimum across unrelated lists. Pitch belongs to its attested
reading and must not be copied from a legacy entry to another reading. Browser
exports filter senses for each spelling/reading row; native readers enforce the
same rule at lookup time.

## Matching and browser projection

The Japanese-focused consumers retain ambiguous candidates, prefer Japanese-source
entries, and boost exact displayed-language equivalents over incidental full-text
matches. Source-marked irregular/rare spellings receive a small penalty; an alias
cannot erase the upstream spelling's tags. Both ワンチャン identities remain.
Canonical display forms prefer actual headwords and common source forms over
redirect aliases. Script candidates are hints, never a destructive filter.

The browser projection omits redundant reading-only rows when the same entry
already has a written form with that reading, retaining kana-only entries and
usually-kana (`uk`) forms. The reading column remains searchable. A pinned real
Yomitan IndexedDB fixture checks written-name reading and kana-only-name lookup;
full-edition parser checks cover every bank. These do not certify the current
Migaku browser extension.
