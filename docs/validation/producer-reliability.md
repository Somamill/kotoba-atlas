# Atlas producer reliability and performance

## Scope

The baseline is audited commit `031f72188030390256b7757f7f38d4713830ea64`. Current Atlas main `5ad07efd11fa0df4006d48ff6326bc6fac7bb906` adds presentation and managed guidance. Its producer, fixtures and source locks match the audit. The separate local `codex/structured-multilingual-contract` branch has further colloquial inflection work. That work is outside this comparison. Atlas had no open PRs at the time of the check. Existing issues [#5](https://github.com/Somamill/kotoba-atlas/issues/5) and [#6](https://github.com/Somamill/kotoba-atlas/issues/6) cover structured fallback and the work-scoped name. Both are in the release regression workload.

The exporter now creates four lookup indexes after bulk insertion, then runs `ANALYZE` on the final core. Bulk creation lets SQLite order index keys before constructing the index. The final core retains table layouts, row identities, payloads and reverse-search implementation. The export keeps a raw-spelling index on `text` and drops its redundant reading and entry-ID keys. The intermediate build keeps the wider index. The inspected readers use normalized/reading indexes and the form primary key for their ordinary lookups. No required capability was added. The new optional descriptor field `coreSha256` exposes the same binding already stored in each dependent SQLite package. A distinct artifact revision is required because the expanded core SHA changes. See the [consumer contract](../consumer-contract.md).

## Reproduce

Use separate Git worktrees for the audited commit and the candidate. Install the pinned development and analysis requirements, and provision the two reviewed browser importer checkouts listed in the consumer contract. Run from each worktree root with the same Python, source lock and cache state. Both runs must use the same candidate revision in separate output directories for strict database comparison. Preserve the existing source licence and zero-skipped-test gates.

```sh
# Run each command from the appropriate worktree. Capture logs outside the final release directory.
mkdir -p dist
/usr/bin/time -l python scripts/pipeline.py --output dist/measurement --revision 1.1.0-beta.3 > dist/build.log 2>&1
/usr/bin/time -l python scripts/consumer_fixtures.py dist/measurement-fixtures > dist/fixtures.log 2>&1

# Run both comparisons from the candidate worktree.
python scripts/benchmark_core.py /path/to/audit/dist/measurement dist/measurement --report dist/full-reliability.json
python scripts/benchmark_core.py /path/to/audit/dist/measurement-fixtures dist/measurement-fixtures --report dist/fixture-reliability.json
```

The benchmark verifies compressed and expanded sizes and SHA-256, and compares rowids and values of every ordinary and FTS shadow table. It excludes SQLite planner metadata and the expected new core-binding value. The fixture benchmark reconstructs the deterministic gzip files and verifies their hashes. The optional provenance archive is compared in the full workload. The timed installation unit is local hash verification and inflation into a staged file. SQLite integrity and package checks are run separately by the pipeline. Transfer time and device activation are separate operations.

`dbstat` accounts for B-tree and overflow pages by object. It excludes free pages and other file overhead. The SQL probes use dict. Swift's exact/reading, prefix, reverse, canonical form ordering and reading-scoped metadata statements and binding patterns. The 16-query Python reader workload retains original case, full result projections and matched-form context. The separate ANALYZE-only arm applies statistics to the baseline core after lookup parity checks, then reopens it for SQL measurement. Timings are host-specific warm medians. The benchmark records individual timings and query plans. Use repeated serial runs on an idle host for performance thresholds. [SQLite ANALYZE](https://sqlite.org/lang_analyze.html), [DBSTAT virtual table](https://sqlite.org/dbstat.html).

## Full beta-2 core experiment

The locked beta-2 core was expanded and checked from its published-format gzip. The scratch experiment ran in this order on the same file: baseline; `ANALYZE`; then `DROP INDEX spelling_lookup; CREATE INDEX spelling_lookup ON forms(text); ANALYZE;`. This measured B-tree bytes directly and kept free pages in the scratch file. The ordinary exporter starts with a fresh file.

| Measurement | Baseline | Analyze only | Narrow spelling index |
| --- | ---: | ---: | ---: |
| Spelling index | 144,879,616 B | 144,879,616 B | 50,139,136 B |
| Swift exact/reading, median | 0.473 ms | 0.469 ms | 0.466 ms |
| Swift reverse, median | 0.440 ms | 0.437 ms | 0.418 ms |
| Changed plans out of five probes | — | 0 | 0 |

The spelling index used 94,740,480 fewer bytes, a 65.4% reduction. SQLite integrity passed. The timings are in the same range and establish no general lookup speedup. The separate bulk-copy prototype returned the same index bytes with variable timings; it established no reliable build-time gain.

`dbstat` attributed 522,399,744 bytes to `reverse_keys` and 450,965,504 bytes to `forms`. Textual entry IDs account for 158,080,503 bytes and sense IDs for 291,233,353 bytes inside `reverse_keys`. The corresponding form hints account for 6,411,824 bytes. These fields remain directly queryable in schema 2. The full experiment includes planner output and all page allocations. [Raw beta-2 evidence](atlas-beta2-core-experiment.json).

## Fixture before and after

The comparison used Python 3.13.5, SQLite 3.47.1, zlib 1.2.12, Node 26.13.1 and 7-Zip 26.06 on an Apple Silicon MacBook Pro (`MacBookPro18,3`, 16 GiB, macOS 27.2.1). All row and result projections were equal, and all 11 English browser member hashes matched. Compressed core bytes were 213,738 → 212,948. Expanded core bytes were 1,286,144 → 1,282,048. Local verification and inflation took 2.62 → 2.33 ms. Single-run fixture generation was 0.50 → 0.88 seconds and sibling-process load varied during measurement. The peak resident set was 68,304,896 → 66,551,808 bytes. These small wall-time and RSS samples are descriptive. [Raw fixture evidence](atlas-producer-fixture-evidence.json).

## Paired full-corpus export

Both arms use the same locked source database and dictionary revision `1.1.0-beta.3`. The audited pipeline regenerated the source database and the candidate export reused the finished intermediate to control for ingestion. The native exports overlapped on this Mac. The baseline interval from first core creation through its manifest was 1,181 seconds. The candidate exporter logged 1,179 seconds. Those intervals include all native packaging and establish no native export speedup at this sample size.

| Bytes | Audited export | Candidate export | Saved |
| --- | ---: | ---: | ---: |
| Core compressed | 473,708,496 | 446,970,096 | 26,738,400 |
| Core expanded | 1,884,286,976 | 1,789,546,496 | 94,740,480 |
| Core + English + German compressed | 750,785,841 | 724,047,512 | 26,738,329 |
| Core + English + German expanded | 3,315,191,808 | 3,220,451,328 | 94,740,480 |
| All 12 native packages compressed | 1,524,092,701 | 1,497,354,404 | 26,738,297 |
| All 12 native packages expanded | 7,564,021,760 | 7,469,281,280 | 94,740,480 |

Row-for-row comparison verified all 12 native packages, including 1,056,822 Japanese and 156,584 English canonical entries, 2,314,207 forms, 3,184,003 senses and 1,954,384 original source records. All 16 lookup projections matched. Both full browser ZIPs had 492 members each and identical member and archive SHA-256. Tiny differences in compressed language and provenance pack sizes follow from rebinding to the candidate core hash.

The five full-corpus query plans were equal across the baseline, the ANALYZE-only copy and the candidate. ANALYZE took 6.82 seconds on the baseline scratch database. Exact/reading medians were 0.576 → 0.523 ms and reverse 0.645 → 0.501 ms. The single local core verification/inflation sample was 5.26 → 8.18 seconds with both export jobs active. The benchmark itself peaked at 51,625,984 resident bytes. The timings do not establish a reliable change in lookup or install latency. [Raw full-corpus evidence](atlas-producer-full-evidence.json).

## Consumer verification

- dict. public main `fea82704`: 9 Swift contract tests with regenerated candidate bytes. Overlapping runtime branch `22ba0c76`: 14 passing tests including completed-package resumption, corrupt downloads and preserving history through interrupted activation.
- narai community schema-2 branch `9ea7e855`: 10 reader, installer and updater tests with regenerated candidate SQL fixtures. It is tracked in [narai PR #24](https://github.com/Somamill/narai/pull/24). Public main `f8b7c1b` still documents the independent bundled Store dictionary path.
- The producer verifies both browser editions with the pinned Yomitan parser and legacy Migaku importer. The fixture additionally uses the real Yomitan IndexedDB adapter.
- A SIGKILL against a process holding the staging directory left the final directory absent. The partial tree was quarantined, a same-name retry was refused, and a fresh-name retry completed.

No physical-iPhone performance conclusion follows from these checks. Remaining release checks include physical-iPhone full-generation install, interrupted-download recovery and offline lookup under storage pressure, deployment of the narai catalogue and the private Store integration, and current browser-extension import. GitHub reported Actions disabled. No candidate package or catalogue was published.
