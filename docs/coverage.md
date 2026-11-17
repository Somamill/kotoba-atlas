# Coverage

See [the edition feature matrix](compatibility.md), [community research](research.md), and [release reports](releases/1.0.0).

The English and German archives each contain every public feature layer in one file. Counts represent term/reading pairs and include names, orthographic variants and reference entries. Names are retained but ranked below ordinary vocabulary. Source inflection rules are preserved when explanations merge.

There is no dictionary-only way to guarantee every possible slang term, new proper name, inflection, OCR error or contextual interpretation. Improvements are grounded in licensed source data, transparent spelling/phrase aliases and regression examples. A successful schema check proves file structure, not automatic recognition by every host.


## 1.0.1 additions

Every 1.0.0 lookup pair is retained: German 1,566,695 pairs (+4), English 1,080,167 (+6). Nine bilingual usage records enrich slang and natural phrasing, including てぇてぇ, ぬまる/沼る, 推し活/推し活する, ワンチャン, ガチ恋, リアコ and 蛙化現象. Existing pairs receive extra notes rather than being counted as new words. Both tool exports have byte-identical word banks. Reports are in [releases/1.0.1](releases/1.0.1/).


## 1.0.2: one complete file

German and English retain every 1.0.1 lookup pair and byte-identical word, metadata, kanji and tag banks. Only packaging/version/name change; tool-specific profiles are retired. Each language edition carries every included data layer in one ZIP.


## 1.0.3 transfer fix

All decoded 1.0.2 records and source notices are retained. Lossless clustering and stronger standard Deflate keep the complete language editions below Chrome/Migaku's Base64 message budget. See [the confirmed failure, remedy and evidence](transfer-limit.md).
