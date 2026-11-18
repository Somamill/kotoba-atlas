# Kotoba Atlas 1.0.4 beta 1

A prerelease for Lookup Lab verification and the native dict. app data pipeline.

## Download roles

- **One complete dictionary ZIP per definition language** for compatible importers. Data coverage is unchanged from 1.0.3; only version/update metadata changes.
- **Lookup Lab ZIP:** optional developer/source toolkit. It is not executed inside a Migaku/Yomitan dictionary import.
- **Native SQLite packages:** downloaded internally by dict.; not Migaku/Yomitan imports. They include indexed words/readings/meanings and all source fields, kanji, metadata, tags and notices.
- **native-beta.json:** versioned catalogue and SHA-256 hashes for checked native-app updates. Adding a new edition to this catalogue lets compatible dict. builds offer it without a hard-coded language menu.

The beta does not move the stable GitHub latest-release channel. Existing stable imports stay on their normal channel. Back up a working edition before replacing it with a beta in a host tool.

The complete native English package is bundled into dict. builds for offline installation; further definition languages download once and remain offline. Updates check the catalogue when the app is active and preserve the installed edition until verification succeeds. Updating repository documentation alone is not a dictionary data release: publish a new version and catalogue entry.

[Verification definitions and fresh results](../../accuracy.md).
