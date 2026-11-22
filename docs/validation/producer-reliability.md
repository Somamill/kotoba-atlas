# Atlas producer reliability and performance

## Scope

The baseline is audited commit `031f72188030390256b7757f7f38d4713830ea64`. Current Atlas main `5ad07efd11fa0df4006d48ff6326bc6fac7bb906` adds presentation and managed guidance. Its producer, fixtures and source locks match the audit. The separate local `codex/structured-multilingual-contract` branch has further colloquial inflection work. That work is outside this comparison. Atlas had no open PRs at the time of the check. Existing issues [#5](https://github.com/Somamill/kotoba-atlas/issues/5) and [#6](https://github.com/Somamill/kotoba-atlas/issues/6) cover structured fallback and the work-scoped name. Both are in the release regression workload.

The exporter now creates four unchanged lookup indexes after bulk insertion, then runs `ANALYZE` on the final core. Bulk creation lets SQLite order index keys before constructing the index. The final core retains table layouts, row identities, payloads, index definitions and reverse-search implementation. No required capability was added. The new optional descriptor field `coreSha256` exposes the same binding already stored in each dependent SQLite package. A distinct artifact revision is required because the expanded core SHA changes. See the [consumer contract](../consumer-contract.md).

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

## Consumer verification

- dict. public main `fea82704`: 9 Swift contract tests with regenerated candidate bytes. Overlapping runtime branch `22ba0c76`: 14 passing tests including completed-package resumption, corrupt downloads and preserving history through interrupted activation.
- narai community schema-2 branch `9ea7e855`: 10 reader, installer and updater tests with regenerated candidate SQL fixtures. It is tracked in [narai PR #24](https://github.com/Somamill/narai/pull/24). Public main `f8b7c1b` still documents the independent bundled Store dictionary path.
- The producer verifies both browser editions with the pinned Yomitan parser and legacy Migaku importer. The fixture additionally uses the real Yomitan IndexedDB adapter.
- A SIGKILL against a process holding the staging directory left the final directory absent. The partial tree was quarantined, a same-name retry was refused, and a fresh-name retry completed.

No physical-iPhone performance conclusion follows from these checks. Remaining release checks include physical-iPhone full-generation install, interrupted-download recovery and offline lookup under storage pressure, deployment of the narai catalogue and the private Store integration, and current browser-extension import. GitHub reported Actions disabled. No candidate package or catalogue was published.
