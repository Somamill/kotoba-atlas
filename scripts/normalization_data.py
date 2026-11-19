"""Export Python's explicit Unicode case-fold mapping for non-Python consumers."""
import json
from pathlib import Path
import unicodedata

if __name__ == '__main__':
    value = {'unicodeVersion': unicodedata.unidata_version,
             'casefold': {chr(code): chr(code).casefold() for code in range(0x110000)
                          if chr(code) != chr(code).casefold()}}
    Path('data/unicode-casefold.json').write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n')
