# Lookup verification, 1.0.4 beta 1

**Retrieval coverage is not meaning accuracy.** The helper retrieves existing source entries; neither a matched word nor a large corpus proves that the selected sense is correct.

| Evaluation | German baseline | German helper | English baseline | English helper |
|---|---:|---:|---:|---:|
| Development: 18 titles, 63,635 distinct Japanese cues | 87.71% | 97.49% | 84.48% | 94.74% |
| Held-out titles: 7 titles, 12,957 distinct Japanese cues | 87.62% | **98.40%** | 84.48% | **95.78%** |

The baseline includes surface headwords and kana readings. The denominator is Japanese content-POS tokens: 230,082 in development and 44,478 in the fresh sample. Names-only matches do not count as lexical coverage. The helper source was frozen at commit dcc852d before downloading the held-out titles. The sample is a convenience sample; common cue text shared with the development set was not excluded. No helper tuning followed these held-out results.

The fresh sample contains 28 files. One requested title lacked an exact Jimaku match and was skipped, rather than silently substituting another series. The source metadata, counts and hashes are included in the evidence. Raw subtitle dialogue and API credentials remain local.

## What is and is not verified

- 34 local Python unit tests pass, including native-export field preservation and safe beta filenames.
- Ten synthetic phrase/headword regressions pass against each complete language index.
- Both beta ZIPs pass the included schemas and Chrome Base64 transfer budget.
- Every non-index ZIP member is byte-identical to 1.0.3. All decoded word fields, native metadata duplicates, kanji, tags and source notices are also checked against the SQLite exports.
- These results apply to the Python Lookup Lab implementation. The native Swift dict. app has a separately tested implementation; these percentages must not be advertised as the app's accuracy.
- Human-reviewed word-boundary accuracy, selected-sense precision, arbitrary OCR accuracy and real handwriting accuracy are not yet measured.
- No current installed Migaku/Yomitan beta-import UI certification or cloud CI is claimed. Stable German 1.0.3 import and 物ノ怪 lookup were user-confirmed.

[Beta evidence](releases/1.0.4-beta.1/) · [Method](subtitle-lookup.md) · [Development evidence](research/subtitles/)
