# Coverage and compatibility

## Two builds, one import each

The public `dict-master.zip` combines the redistributable sources. The local `dict-personal.zip` also combines the previously downloaded Pixiv summaries and JPDB frequency data, plus the user's optional local Daijirin. Both are one standard Yomichan v3 word-dictionary archive. A ZIP of nested dictionary ZIPs would not meet this goal; this builder merges the actual entries.

The personal archive is not a public release asset. Its additional sources retain their own terms. An older commercial local dictionary does not automatically have broader or more current coverage than the public sources.

## What survives the merge

- Headwords, original readings, definition text, source labels, usage tags, links embedded in structured text, and source deinflection rules.
- German source contributions precede English ones, followed by Japanese references and names. Results for different readings can still be ordered by the host app.
- Exact duplicate rows within a source are removed. Distinct senses and different source explanations are retained.
- Character meanings and readings, pitch positions, and (in a personal build) frequency data appear as ordinary labeled text. They do not require native metadata support.
- Original dictionary index metadata, source hashes, and embedded attribution notices are kept in `SOURCES.json`. Source licences are bundled alongside it.

## What changes

Rich formatting becomes plain text. No images, image attribution-dependent media, font files, sound, pitch graphs, or native frequency sort/filter metadata are included. Text may still contain source URLs. The archive is a reference dataset and does not load websites or run code itself; host apps determine how links are displayed or opened.

Orthographic の → ノ variants are generated only when both adjacent characters are kanji (including 々). They are labeled aliases, not claims that each spelling is common. Particle omission is handled only through explicitly reviewed phrase supplements, not a global rewriting rule.

## Recognition depends on the host

1. Check manual search for the **exact written form**.
2. Try its dictionary spelling or base form.
3. If search works but hover fails, check the app's parser, selected text, scan-length setting, and language configuration. A dictionary alone cannot correct OCR or force every host to segment the same expression.
4. For phrases, try selecting the whole phrase and invoking the host's lookup action. Available controls vary by app version.

All archive entries are validated against pinned upstream Yomitan v3 schemas. The regression examples verify archive content and lexical rules. Neither a successful schema check nor the word “Yomichan” proves a successful Migaku Early Access import. Runtime import and hover behavior remain unverified because direct access to extension pages was blocked.

## Research used for this release

- [Migaku's documented dictionary formats](https://github.com/migaku-official/Migaku-legacy-guides/blob/master/content/en/tools-guides/migaku-dictionary/manual.md#supported-file-formats): legacy Yomichan word dictionaries; legacy kanji/frequency formats are separate and unsupported there. Metadata is therefore flattened into word text in this collection.
- [WaDoku official exports](https://www.wadoku.de/wiki/display/WAD/Downloads+und+Links): newer German coverage than the owner's old converted copy.
- [Jitendex](https://jitendex.org/pages/downloads.html) and [wty](https://yomidevs.github.io/wiktionary-to-yomitan/): English definitions and an independent Wiktionary supplement; rich objects converted to text.
- [NINJAL grammar-pattern database](https://www2.ninjal.ac.jp/bunkeibank/): connection patterns and Japanese phrase explanations.
- [Bee's Yomitan reference dictionaries](https://github.com/bee-san/yomitan-dictionaries): attributed yōkai reference material.
- [KireiCake quality concerns](https://github.com/FooSoft/yomichan/issues/1608): not added merely to increase the apparent source count.

No fabricated “complete Japanese” coverage claim, autonomous contextual interpretation, or guarantee about all slang is made. The improvement path is source updates, exact examples, and regression checks.
