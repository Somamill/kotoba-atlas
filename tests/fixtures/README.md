# Licensed source fixtures

`jitendex-2238120.json` is an unmodified source row from Jitendex,
`term_bank_119.json`, JMdict entry 2238120. Source archive:
https://github.com/stephenmk/stephenmk.github.io/releases/download/2026.10.03.0/jitendex-yomitan.zip

SHA-256: `e914c76596220dffc6ee0c069cd05992f03adb2988c12c3cebe817a3ac271356`.
Jitendex and JMdict contributors; CC BY-SA 4.0. The fixture retains original
structured content and attribution. Extraction changes are in `scripts/structured.py`.

`jmdict-2238120.json` and `jmdict-consumer-words.json` retain real records
from scriptin/jmdict-simplified release `3.6.2+20261116213322`, pinned in
`data/sources-v2.lock.json`. Lexical data: JMdict contributors / EDRDG,
CC BY-SA 4.0; JSON conversion: scriptin/jmdict-simplified contributors.
The selected records exercise primary-present/missing definitions, legitimate
homographs, verified aliases and slang annotation targets. They are source
fixtures, not independent new dictionary claims. Consumer fixtures generated
by `scripts/consumer_fixtures.py` also include attributed original Atlas usage
annotations (CC BY-SA 4.0) and the CC0 factual fiction-identification annotation.

`data/usage-identities.json` is an explicit identity review against those pinned
JMdict records. In particular 2831313 is the chance/maybe ワンチャン entry;
2794860 is the separate dog homograph and is never merged into it.

The names fixture retains two real JMnedict records (5000000, 5000085),
CC BY-SA 4.0. The examples fixture retains the corresponding pinned JMdict
English records; sentences remain Tatoeba CC BY 2.0 FR, with source fields.
`atlas-metadata.json` retains a small 日本語 frequency/pitch and 語 kanji
subset from the pinned Atlas metadata source, including original source
and licence notices (notice bytes are base64 encoded).
