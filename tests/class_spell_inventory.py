"""Read-only class spell-name inventory against each dev realm's own Spell.dbc.

This inventories literal action spell names, not whether every action is reachable.
Missing names can be dynamic/pseudo actions and require source review, not deletion.
"""
import argparse
import json
import re
import struct
from pathlib import Path

CLASSES = ('warrior', 'paladin', 'hunter', 'rogue', 'priest', 'shaman', 'mage', 'warlock', 'druid', 'deathknight')


def read_spells(path, name_field):
    data = path.read_bytes()
    magic, count, fields, record_size, string_size = struct.unpack_from('<4s4I', data)
    assert magic == b'WDBC' and record_size == fields * 4
    strings = data[20 + count * record_size:]
    assert len(strings) == string_size
    spells = {}
    for index in range(count):
        row = struct.unpack_from(f'<{fields}I', data, 20 + index * record_size)
        offset = row[name_field]
        name = strings[offset:strings.index(b'\0', offset)].decode('utf-8').lower()
        spells[row[0]] = (name, row)
    return spells


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dev', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    all_names = set()
    realm_names = {}
    result = {}
    for realm in ('classic', 'tbc', 'wotlk'):
        structure = (args.work / f'mangos-{realm}-behavior/src/game/Server/DBCStructure.h').read_text()
        name_field = int(re.search(r'char\*\s+SpellName\[\d+\];\s*//\s*(\d+)', structure)[1])
        spells = read_spells(args.dev / realm / 'data/dbc/Spell.dbc', name_field)
        names = {item[0] for item in spells.values()}
        realm_names[realm] = names
        all_names.update(names)
        result[realm] = {'dbc_records': len(spells), 'name_field': name_field, 'classes': {}}
        result[realm]['selected_spells'] = {str(key): spells[key][0] for key in (7744, 759, 3552, 10053, 10054, 27101, 42985, 19465) if key in spells}
    pattern = r'(?:Cast\w*Action\(ai,|\w*ACTION\w*\(\w+,)\s*"([^"]+)"'
    for classname in CLASSES:
        names = set()
        for path in (root / 'playerbot/strategy' / classname).glob('*'):
            if path.suffix in ('.cpp', '.h'):
                names.update(re.findall(pattern, path.read_text()))
        for realm, available in realm_names.items():
            if classname == 'deathknight' and realm != 'wotlk':
                continue
            result[realm]['classes'][classname] = {
                'literal_names': len(names),
                'absent_here': sorted(names - available),
                'absent_all_realms': sorted(names - all_names),
            }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
