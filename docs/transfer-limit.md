# Chrome/Migaku transfer limit — 1.0.3

## Confirmed failure

The supplied console error from Migaku 1.33.0-earlyaccess.2 reports `Message exceeded maximum allowed size of 64MiB` during `runtime.sendMessage`. The current public package's file-install path calls `LangResourceMgr_installDataB64`; the ZIP is Base64-encoded before transfer. Chrome documents [JSON message serialization and a 64 MiB maximum](https://developer.chrome.com/docs/extensions/develop/concepts/messaging).

The limit is **67,108,864 bytes**. Base64 size is `4 × ceil(archive_bytes / 3)`, before the enclosing message. A compressed file smaller than 64 MiB can therefore still be too large.

| Complete edition | ZIP bytes | Base64 bytes |
|---|---:|---:|
| German 1.0.2 | 61,191,287 | 81,588,384 |
| German 1.0.3 | 50,255,727 | 67,007,636 |
| English 1.0.2 | 51,600,758 | 68,801,012 |
| English 1.0.3 | 42,461,611 | 56,615,484 |

Both new archives satisfy `base64_bytes + 65,536 <= 67,108,864`. The German integration check also serializes a representative request with an additional 64 KiB header reserve: 67,073,365 bytes. This guard prevents publishing the same oversized-transfer regression.

## Lossless remedy

Similar decoded records are grouped before ZIP compression. 7-Zip 26.06 produces standard Deflate entries; the dictionary remains an ordinary `.zip`. Word banks and native metadata banks stay bounded at 2 MiB. All 1.0.2 decoded records, including duplicate metadata records, are compared by canonical SHA-256 multisets. Every reading, definition, rule, score, pitch/frequency value, kanji and tag survives. Source/licence files remain byte-identical. Archive ordering and compressed bytes change; index.json remains at the root, as required by the format.

The builder requires [7-Zip](https://www.7-zip.org/download.html), and CI downloads the tested Linux 26.06 archive with a pinned SHA-256. Temporary databases and staging files use automatic cleanup. Compression is a build-time cost; users import the finished ZIP without installing the compressor.

## Runtime evidence and limits

The small representative same-format diagnostic installs. With the complete 1.0.3 German archive, the user confirms completed installation and a working 物ノ怪 lookup on Migaku 1.33.0-earlyaccess.2. This is user-reported verification, not independent inspection of the installed extension. Browser tool URL policy blocked direct extension-page access. English live import, native feature presentation and restart persistence remain unverified. The precise error is addressed; database/indexing work can still take time after transfer succeeds.

Both complete archives pass pinned upstream schemas, the upstream Yomitan importer/parser with a counting storage façade and 14 deinflection cases. These do not certify installed browser UIs or full persistent IndexedDB installation. Native graph/sorting/audio/scanning behavior depends on the host. [Machine-readable evidence](releases/1.0.3/) records exact scopes and hashes.

Disk-space exhaustion was a separate observed blocker during troubleshooting. Allow working space for expanded data and the host's database/index; a valid compressed archive alone does not guarantee sufficient space.
