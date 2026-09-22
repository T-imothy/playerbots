"""Source-only guard for Turtle's raw synchronous database result API.

Run with Python; does not compile, connect to a database, or start a server.
Async callbacks and SqlQueryHolder results have separate ownership contracts.
"""
from pathlib import Path
import re
import sys

TOKENS = re.compile(r'R"([^ ()\\\t\r\n]*)\(.*?\)\1"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\r\n]*|/\*.*?\*/', re.S)
CALL = re.compile(r'\b(?:World|Character|Login)Database\.(?:PQuery|Query)\s*\(')

def mask(text):
    return TOKENS.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), text)

def unowned(text):
    code = mask(text)
    bad = []
    # A query that already had a separate guard must not keep a second owner.
    owned = set(re.findall(r'auto\s+(\w+)\s*=\s*std::unique_ptr<QueryResult>\(', code))
    for guard in re.finditer(r'std::unique_ptr<QueryResult>\s+\w+\s*\(\s*(\w+)\s*\)', code):
        if guard[1] in owned:
            bad.append(text[:guard.start()].count('\n') + 1)
    for call in CALL.finditer(code):
        prefix = code[max(0, call.start()-180):call.start()]
        if re.search(r'std::unique_ptr\s*<\s*QueryResult\s*>\s*(?:\w+\s*)?\(\s*$', prefix):
            continue
        reset = re.search(r'\b(\w+)\.reset\s*\(\s*$', prefix)
        if reset and re.search(r'std::unique_ptr\s*<\s*QueryResult\s*>\s+'+re.escape(reset[1])+r'\b', code[:call.start()]):
            continue
        bad.append(text[:call.start()].count('\n') + 1)
    return bad

def main():
    assert unowned('auto r = CharacterDatabase.Query("SELECT 1");') == [1]
    assert unowned('if (auto r = WorldDatabase.PQuery("SELECT (%u)", 1)) {}') == [1]
    assert not unowned('auto r = std::unique_ptr<QueryResult>(CharacterDatabase.Query("SELECT 1"));')
    assert not unowned('std::unique_ptr<QueryResult> r; r.reset(WorldDatabase.Query("SELECT 1"));')
    assert not unowned('// auto r = WorldDatabase.Query("not code");')
    assert not unowned('/* WorldDatabase.Query("not code"); */')
    assert unowned('auto r = std::unique_ptr<QueryResult>(WorldDatabase.Query("SELECT 1")); std::unique_ptr<QueryResult> guard(r);')
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
    failures=[]; calls=0
    for folder in ('playerbot', 'cmangos-ahbot'):
        for path in (root/folder).rglob('*.cpp'):
            text=path.read_text(encoding='utf-8-sig')
            calls += len(CALL.findall(mask(text)))
            failures += [f'{path.relative_to(root)}:{line}' for line in unowned(text)]
    if failures:
        raise SystemExit('Unowned synchronous results:\n'+'\n'.join(failures))
    print(f'PASS: {calls} active synchronous database calls have explicit result ownership; guard fixtures passed.')

if __name__ == '__main__':
    main()
