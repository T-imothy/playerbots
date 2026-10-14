"""Native-shaped spline dependency for existing actual-body encounter tests."""
from pathlib import Path
import re
from behavior_regression import block

def arrival_fixture(code):
    needs_helper = 'EncounterMovementRequired(' in code
    needs_spline = needs_helper or 'bot->movespline' in code
    if not needs_spline:
        return code
    match = re.search(r'struct Player(?:\s*:\s*\w+)?\s*\{', code)
    assert match, 'Player fixture missing'
    start = match.end()
    level = 1
    end = start
    while level:
        level += (code[end] == '{') - (code[end] == '}')
        end += 1
    if 'movespline' not in code[start:end]:
        spline = '''struct ArrivalSpline {bool done=true;struct End{float x=0,y=0,z=0;};End end;
 bool Finalized(){return done;}End FinalDestination(){return end;}};
'''
        code = code[:start] + 'ArrivalSpline arrival;ArrivalSpline* movespline=&arrival;' + code[start:]
        code = code[:match.start()] + spline + code[match.start():]
        stop = re.search(r'void StopMoving\(\)\s*\{', code)
        if stop:
            code = code[:stop.end()] + 'bot->movespline->done=true;' + code[stop.end():]
    if needs_helper:
        root = Path(__file__).resolve().parents[1]
        body = block((root/'playerbot/strategy/values/EncounterPositionValue.cpp').read_text(),
                     'bool ai::EncounterMovementRequired(')
        dependency = '''namespace ai {bool EncounterMovementRequired(Player*, const encounter::Point&, float=1.5f);}
''' + body + '\nusing ai::EncounterMovementRequired;\n'
        first = re.search(r'\nbool \w+::isUseful\(', code)
        assert first, 'actual action body missing'
        code = code[:first.start()] + '\n' + dependency + code[first.start():]
    return code
