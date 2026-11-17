# Transfer and preparation — 1.0.3

One complete ZIP per definition language retains all included features. German has 1,566,695 lookup pairs and English 1,080,167. Both retain 1,006,753 native metadata records, 10,384 kanji records and 74 tags.

| Edition | Download | Base64 transfer | Chrome ceiling |
|---|---:|---:|---:|
| German 1.0.3 | 50.26 MB | 67,007,636 bytes | 67,108,864 bytes |
| English 1.0.3 | 42.46 MB | 56,615,484 bytes | 67,108,864 bytes |

The guard reserves a further 65,536 bytes for the message envelope. German's representative serialized request, including this reserve, is 67,073,365 bytes. The previous complete 1.0.2 archives exceeded the ceiling after Base64 encoding. [Explanation and primary documentation](transfer-limit.md).

Decoded record multisets are identical to 1.0.2, including duplicates; source/licence files remain unchanged. Similar records are grouped, so compressed bytes and bank ordering differ. Word/native banks remain at most 2 MiB. Standard Deflate keeps the same ZIP format.

The full upstream Yomitan parser validates both archives with a counting storage façade and passes 14 deinflection cases. Exact timings, memory observations, input hashes and scopes are in [1.0.3 evidence](releases/1.0.3/). They are not installed browser indexing or lookup-latency benchmarks. Earlier legacy Migaku SQLite and representative IndexedDB checks are retained in [1.0.2 evidence](releases/1.0.2/).

The user reports German progressing beyond 0% on Migaku 1.33.0-earlyaccess.2. Full completion and native UI presentation are awaiting confirmation. Compression removes the transfer blocker; a large initial database import still requires time and working disk space. No lookup-latency claim is made.
