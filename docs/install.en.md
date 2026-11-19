# Install Kotoba Atlas

Choose a **browser ZIP** or **native app package** from the [download table](../README.md#download). These formats are different.

## Migaku / Yomitan

1. Download one complete English or German ZIP. German includes English fallback when the entry has no German material.
2. Keep the file compressed. If your browser automatically expands ZIPs, turn that option off or download the ZIP again.
3. In the extension's dictionary settings, choose **Install from file** / **Import** and select the ZIP. Let the import finish before closing settings.
4. Check that the dictionary appears in the installed list. Try 物ノ怪 and ノリのいい. Import progress by itself does not prove installation finished.

Both complete beta ZIPs are checked with the pinned Yomitan parser and the public legacy Migaku importer. Current extension versions and their presentation of pitch, frequency and kanji features still need live verification. A dictionary file cannot add capabilities its host does not implement.

## Native consumers

Schema-2 consumers use one shared core, the English pack and any chosen primary pack from the same manifest. Do not import native `.sqlite.gz` files into a browser extension or manually replace a running app's database. A supporting app verifies hashes and generation compatibility before activation and keeps learning data separately.

Ten definition-language families are available with partial, source-specific coverage. Chinese, Arabic and Portuguese currently provide equivalents rather than full explanatory definitions. See the [coverage matrix](releases/atlas-v1.1.0-beta.2.md). App-default adoption is tracked separately from dictionary publication.
