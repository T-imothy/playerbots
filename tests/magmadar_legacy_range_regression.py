"""Do not let the old fixed boss-distance action override the Classic tank-anchored healer plan."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
signature='bool MagmadarMoveAwayAction::isPossible('
body=block(source,signature) if signature in source else 'bool MagmadarMoveAwayAction::isPossible(){return MoveAwayFromCreature::isPossible();}'
code=r'''
#include <cassert>
#include <string>
enum class BotState {BOT_STATE_COMBAT};
struct Player {unsigned map=409;unsigned GetMapId(){return map;}};
struct AI {bool mc=true;bool HasStrategy(const char*name,BotState){assert(std::string(name)=="molten core");return mc;}};
struct MoveAwayFromCreature {bool base=true;bool isPossible(){return base;}};
struct MagmadarMoveAwayAction:MoveAwayFromCreature {Player*bot;AI*ai;bool isPossible();};
'''+body+r'''
int main(){
 Player player;AI ai;MagmadarMoveAwayAction action;action.bot=&player;action.ai=&ai;
#ifdef MANGOSBOT_ZERO
 assert(!action.isPossible());
#else
 assert(action.isPossible());
#endif
 // An explicit legacy-only configuration retains its original behavior.
 ai.mc=false;assert(action.isPossible());ai.mc=true;
 player.map=469;assert(action.isPossible());player.map=0;assert(action.isPossible());
 action.base=false;assert(!action.isPossible());
}
'''
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='magmadar-range-owner-') as folder:
        path=Path(folder);(path/'test.cpp').write_text(code)
        result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
        if result.returncode:print(result.stdout,result.stderr)
        result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
print('PASS Classic Magmadar formation owns healer/caster range; legacy-only, other maps and eras preserved')
