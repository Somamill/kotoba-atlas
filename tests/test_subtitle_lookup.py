import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lookup import AtlasLookup, build_index, kana
from subtitle_audit import captions, clean_caption, decode
from download_subtitles import safe_url, select_files, save_manifest


class SubtitleTests(unittest.TestCase):
    def test_srt_and_vtt_do_not_include_timestamps_or_ruby_readings(self):
        s = 'WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.000\n<ruby>漢字<rt>かんじ</rt></ruby>を読む。\n\n'
        self.assertEqual(list(captions(s, '.vtt')), ['漢字を読む。'])

    def test_ass_keeps_commas_and_removes_overrides_and_drawings(self):
        s = '[Events]\nFormat: Layer, Start, End, Text\nDialogue: 0,0:00:01.00,0:00:02.00,{\\b1}そう,だね\\N本当。\nDialogue: 0,0:00:01.00,0:00:02.00,{\\p1}m 0 0 l 1 1'
        self.assertEqual(list(captions(s,'.ass')), ['そう,だね 本当。'])

    def test_speaker_labels_are_not_dialogue_but_internal_parentheses_remain(self):
        self.assertEqual(clean_caption('（太郎）そういうこと（多分）'), 'そういうこと（多分）')

    def test_cp932_and_utf16_decode_without_lossy_replacement(self):
        for encoding in ['cp932', 'utf-16']:
            self.assertEqual(decode('日本語'.encode(encoding)), '日本語')
        self.assertEqual(kana('ｶﾀｶﾅ'), 'かたかな')

    def test_api_credentials_cannot_follow_external_or_insecure_urls(self):
        self.assertEqual(safe_url('/api/entries/1/files'), 'https://jimaku.cc/api/entries/1/files')
        for url in ['http://jimaku.cc/api','https://evil.test/file','//evil.test/file','https://jimaku.cc@evil.test/','https://jimaku.cc:443/api']:
            with self.assertRaises(ValueError):
                safe_url(url)

    def test_manifest_replace_is_private_and_leaves_no_partial_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'manifest.json'
            save_manifest(path,{'files':[]})
            self.assertEqual(json.loads(path.read_text()),{'files':[]})
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertFalse(path.with_suffix('.part').exists())

    def test_file_selection_avoids_episode_variants_english_and_oversized(self):
        rows = [{'name':n,'size':100} for n in ['Show 01.ass','Show 01.srt','Show 02.srt','Show 03.en.srt']]
        rows.append({'name':'Show 04.srt','size':99999999})
        self.assertEqual([r['name'] for r in select_files(rows,8)],['Show 01.ass','Show 02.srt'])


@unittest.skipUnless(importlib.util.find_spec('sudachipy'), 'optional analysis requirements not installed')
class LookupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.archive = self.root / 'tiny.zip'
        rows = [
            ['物','もの','','',10,['a thing'],-1,''],
            ['怪','かい','','',10,['mystery'],-1,''],
            ['物ノ怪','もののけ','','',100,['spirit'],-1,''],
            ['食べる','たべる','','v1',100,['to eat'],-1,''],
            ['食べ','たべ','n','',100,['a noun fragment'],-1,''],
            ['沼る','ぬまる','v5','v5',100,['to become absorbed'],-1,''],
            ['猫','ねこ','','',100,['cat'],-1,''],
            ['辞める','やめる','v1','v1',100,['to quit'],-1,''],
            ['犬','いぬ','','',100,['dog'],-1,''],
            ['猫、犬','','','',100,['must not cross punctuation'],-1,''],
            ['猫','ねこ','','',1,['[Names • JMnedict]\na name'],-1,''],
            ['音','おと','','',100,['[Pitch • WaDoku]\nPitch: 2'],-1,''],
        ]
        with zipfile.ZipFile(self.archive,'w') as z:
            z.writestr('term_bank_1.json',json.dumps(rows,ensure_ascii=False))
        self.index = self.root / 'index.sqlite'
        build_index(self.archive,self.index)
        self.lookup = AtlasLookup(self.index)

    def tearDown(self):
        self.lookup.close()
        self.directory.cleanup()

    def test_prefers_phrase_without_losing_original_offsets(self):
        result=self.lookup.analyze('物ノ怪')
        self.assertEqual(len(result['matches']),1)
        match=result['matches'][0]
        self.assertEqual((match['entry']['term'],match['start'],match['end']),('物ノ怪',0,3))

    def test_dictionary_form_recovers_inflected_verb(self):
        result=self.lookup.analyze('食べました')
        match=next(x for x in result['matches'] if x['entry']['term']=='食べる')
        self.assertEqual((match['surface'],match['method']),('食べ','dictionary-form'))

    def test_does_not_cross_punctuation_or_treat_pitch_notes_as_definitions(self):
        self.assertFalse(self.lookup.entries('音'))
        self.assertNotIn('猫、犬',[x['entry']['term'] for x in self.lookup.analyze('猫、犬')['matches']])
        self.assertEqual(self.lookup.entries('猫')[0]['kind'],'lexical')


    def test_verified_verb_class_recovers_colloquial_verb_over_noun_fragments(self):
        matches = self.lookup.analyze('沼ってる')['matches']
        self.assertTrue(any(m['entry']['term']=='沼る' and m['method']=='source-checked-contraction' for m in matches))
        matches = self.lookup.analyze('食べちゃった')['matches']
        self.assertTrue(any(m['entry']['term']=='食べる' and m['surface']=='食べちゃった' for m in matches))

    def test_kana_query_matches_headword_reading(self):
        matches=self.lookup.analyze('やめる')['matches']
        self.assertTrue(any(m['entry']['term']=='辞める' and '+reading' in m['method'] for m in matches))

    def test_failed_build_preserves_existing_index(self):
        before=self.index.read_bytes()
        invalid=self.root/'broken.zip'
        invalid.write_text('not a ZIP')
        with self.assertRaises(zipfile.BadZipFile):
            build_index(invalid,self.index)
        self.assertEqual(before,self.index.read_bytes())


if __name__=='__main__':
    unittest.main()
