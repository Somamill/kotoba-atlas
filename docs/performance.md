# Import measurements — 1.0.1

Decimal MB below describe the frozen release files. One ZIP per tool/language retains every 1.0.0 lookup pair.

| Edition / export | Lookup pairs | Download MB | Expanded MB |
|---|---:|---:|---:|
| German / Migaku | 1,566,695 | 47.91 | 301.46 |
| German / full Yomitan | 1,566,695 | 61.19 | 397.44 |
| English / Migaku | 1,080,167 | 38.32 | 245.31 |
| English / full Yomitan | 1,080,167 | 51.60 | 341.29 |

The Migaku profile removes approximately **95.97 MB** of expanded native-bank data from each full export. Every word bank is byte-identical between profiles. Plain-text pitch, frequency and kanji references remain. This reduces preparation work for word-only importers; it does not guarantee the current browser extension will complete.

## Measured importer paths

Single local runs on a 16 GB Mac; reports record source commits, input hashes and scope. Timings exclude dependency setup.

| Path | German | English | What was exercised |
|---|---:|---:|---|
| Public legacy Migaku core + SQLite | 15.149 s / 1,369.75 MB peak RSS | 9.556 s / 1,202.85 MB | All word records converted and inserted using reviewed upstream functions; GUI/language registry façade |
| Current upstream Yomitan importer parser | 5.51 s / 408.75 MB peak RSS | 4.72 s / 363.69 MB | Every full-archive bank parsed and validated; counting storage façade |

Representative fixtures also exercised Yomitan's actual DictionaryDatabase adapter using fake IndexedDB: 14 words, 23 metadata records, 4 kanji and 74 tags per language. Both passed 14 Japanese deinflection cases. This is narrower than importing the complete archives into a persistent browser database.

**These are not live current Migaku Early Access or installed Yomitan UI benchmarks.** Memory includes the local harness process, not a browser's full overhead; hardware, extension version, storage, indexing and simultaneous operations affect actual performance. The legacy Migaku source accumulates all word records, so a 2 MiB bank limit does not mean a 2 MiB import memory limit. Lookup latency after browser installation has not been measured.

Reports: [release evidence](releases/1.0.1/). Older sequential JSON parsing measurements remain in [1.0.0 reports](releases/1.0.0/); those measured a different path and are not importer timings.
