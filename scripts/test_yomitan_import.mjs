/** Test the pinned upstream parser, optionally its real IndexedDB adapter on a small fixture.
 * Full mode validates every record with the actual importer and a counting storage facade.
 * Neither mode installs or certifies a live browser extension.
 */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const [sourceArg, archiveArg, reportArg, mode = 'parser'] = process.argv.slice(2);
if (!sourceArg || !archiveArg || !reportArg || !['parser', 'indexeddb'].includes(mode)) throw Error('Usage: node test_yomitan_import.mjs SOURCE ARCHIVE REPORT [parser|indexeddb]');
const source = path.resolve(sourceArg), archive = path.resolve(archiveArg);
const revision = execFileSync('git', ['-C', source, 'rev-parse', 'HEAD'], {encoding: 'utf8'}).trim();
assert.equal(revision, 'ce1b1bffa0e8819716317f3717932a7fe91e8d52', 'Review a changed upstream revision before execution');
const upstream = relative => import(pathToFileURL(path.join(source, relative)));
const {DictionaryImporter} = await upstream('ext/js/dictionary/dictionary-importer.js');
const {configure} = await upstream('ext/lib/zip.js');
configure({useWebWorkers: false});
const {LanguageTransformer} = await upstream('ext/js/language/language-transformer.js');
const {japaneseTransforms} = await upstream('ext/js/language/ja/japanese-transforms.js');
const selected = new Map(), storedCounts = {};
const wanted = new Set(['ノリのいい', '隠密局', '公儀隠密局', '羅睺', '物ノ怪', '鎌かけて', '鎌かける', '鎌を掛ける', 'ぬまる', '沼る', '推し活する', '食べる', '楽しい', 'てぇてぇ', '日本語']);
let database;
if (mode === 'indexeddb') {
  const require = createRequire(path.join(source, 'package.json'));
  const fake = require('fake-indexeddb');
  globalThis.indexedDB = fake.indexedDB;
  globalThis.IDBKeyRange = fake.IDBKeyRange;
  globalThis.self = {constructor: {name: 'Window'}};
  globalThis.Worker = class { addEventListener() {} terminate() {} }; // Same worker stub used by upstream database tests.
  const {DictionaryDatabase} = await upstream('ext/js/dictionary/dictionary-database.js');
  database = new DictionaryDatabase();
  await database.prepare();
} else {
  database = {
    isPrepared: () => true,
    dictionaryExists: async () => false,
    async addWithResult() {
      const request = {result: 1};
      setTimeout(() => request.onsuccess?.(), 0);
      return request;
    },
    async bulkAdd(store, entries, start, count) {
      storedCounts[store] = (storedCounts[store] || 0) + count;
      if (store === 'terms') for (let i = start; i < start + count; i++) {
        const row = entries[i];
        if (wanted.has(row.expression)) selected.set(row.term ?? row.expression, [...(selected.get(row.term ?? row.expression) ?? []), row]);
      }
    },
    async bulkUpdate() {},
  };
}
const buffer = fs.readFileSync(archive);
const started = performance.now();
const importer = new DictionaryImporter({getImageDetails: async () => { throw Error('Unexpected media in text-only Atlas'); }});
const {result, errors} = await importer.importDictionary(database, buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength), {prefixWildcardsSupported: false, yomitanVersion: '0.0.0.0'});
assert.deepEqual(errors.map(error => error.message), []);
assert.ok(result?.importSuccess, 'Import did not finish');
if (mode === 'indexeddb') {
  const rows = await database.findTermsBulk([...wanted], new Set([result.title]), 'exact');
  for (const row of rows) selected.set(row.term ?? row.expression, [...(selected.get(row.term ?? row.expression) ?? []), row]);
  assert.ok((await database.findTermMetaBulk(['日本語'], new Set([result.title]))).length, 'Native metadata did not reach IndexedDB');
  assert.ok((await database.findKanjiBulk(['語'], new Set([result.title]))).length, 'Native kanji did not reach IndexedDB');
  const names = await database.findTermsBulk(['ちゅせん', 'あーみん'], new Set([result.title]), 'exact');
  assert.ok(names.some(row => (row.term ?? row.expression) === 'ゝ泉' && row.reading === 'ちゅせん'), 'Written-name reading lookup was lost');
  assert.ok(names.some(row => (row.term ?? row.expression) === 'あーみん'), 'Kana-only name lookup was lost');
}
for (const term of wanted) assert.ok(selected.has(term), 'No imported entry: ' + term);
const transformer = new LanguageTransformer();
transformer.addDescriptor(japaneseTransforms);
const cases = [
  ['鎌かけて', '鎌かける', 'v1'], ['鎌かけた', '鎌かける', 'v1'], ['鎌かけない', '鎌かける', 'v1'],
  ['鎌かけられた', '鎌かける', 'v1'], ['鎌かけました', '鎌かける', 'v1'], ['鎌かけてる', '鎌かける', 'v1'],
  ['鎌を掛けていた', '鎌を掛ける', 'v1'], ['沼った', '沼る', 'v5'], ['沼ってる', '沼る', 'v5'],
  ['ぬまらない', 'ぬまる', 'v5'], ['ぬまった', 'ぬまる', 'v5'], ['推し活した', '推し活する', 'vs'],
  ['食べていました', '食べる', 'v1'], ['楽しくなかった', '楽しい', 'adj-i'],
];
for (const [surface, term, rule] of cases) {
  const rows = selected.get(term);
  assert.ok(rows.some(row => (Array.isArray(row.rules) ? row.rules : row.rules.split(' ')).includes(rule)), 'Lost dictionary rule: ' + term + '/' + rule);
  const mask = transformer.getConditionFlagsFromConditionType(rule);
  assert.ok(transformer.transform(surface).some(candidate => candidate.text === term && LanguageTransformer.conditionsMatch(candidate.conditions, mask)), surface + ' did not resolve with its dictionary rule');
}
const clean = selected.get('ノリのいい').find(row => row.sequence === 2238120);
const cleanGlossary = clean?.glossary ?? clean?.definitions;
assert.ok(cleanGlossary && cleanGlossary.some(gloss => typeof gloss === 'string' && gloss.includes('easily getting into')), 'Clean canonical definition missing after import');
assert.doesNotMatch(cleanGlossary.join(' '), /expadjectivekana|See also|query=|edrdg/);
const report = {archive: path.basename(archive), revision: result.revision, upstream_revision: revision,
  scope: mode === 'indexeddb' ? 'Upstream importer and database adapter with fake-indexeddb on a representative fixture' : 'Full upstream parser/schema/import pipeline with a counting storage facade; no persistent IndexedDB writes',
  structured_regressions: {clean_entry_sequence: clean.sequence, clean_glossary: cleanGlossary, fiction_aliases_present: true},
  counts: result.counts, storedCounts, deinflection_cases: cases.length, elapsed_seconds: Math.round((performance.now() - started) / 10) / 100,
  peak_rss_bytes: process.resourceUsage().maxRSS * 1024,
  archive_sha256: crypto.createHash('sha256').update(buffer).digest('hex'), live_extension_tested: false};
fs.writeFileSync(reportArg, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
if (mode === 'indexeddb') database.close();
