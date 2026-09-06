"""Suppression-room policy must not permanently remove avoidance strategies."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]/'playerbot/strategy/generic'
source=(root/'BlackwingLairDungeonStrategies.cpp').read_text()
cls=block(source,'class SuppressionRoomPassiveMultiplier')+';'
code=r'''
#include <cassert>
#include <string>
#include <iostream>
enum {CLASS_ROGUE=4};
struct Player {unsigned map=469;int cls=CLASS_ROGUE;bool world=true;
 int getClass(){return cls;}bool IsInWorld(){return world;}unsigned GetMapId(){return map;}};
struct PlayerbotAI {Player bot;Player* GetBot(){return &bot;}};
struct Action {std::string name;const std::string& getName(){return name;}};
struct Multiplier {PlayerbotAI* ai;Multiplier(PlayerbotAI* a,const char*):ai(a){}virtual float GetValue(Action*){return 1;}};
__CLASS__
int main(){PlayerbotAI ai;SuppressionRoomPassiveMultiplier policy(&ai);Action fight{"melee"},device{"disarm suppression device"},follow{"follow"};
 assert(policy.GetValue(&fight)==0);assert(policy.GetValue(&device)==1);assert(policy.GetValue(&follow)==1);
 ai.bot.map=0;assert(policy.GetValue(&fight)==1);ai.bot.map=469;
 ai.bot.cls=1;assert(policy.GetValue(&fight)==1);ai.bot.cls=CLASS_ROGUE;
 ai.bot.world=false;assert(policy.GetValue(&fight)==1);assert(policy.GetValue(nullptr)==1);
 std::cout<<"PASS: suppression-room multiplier is scoped to a live BWL rogue\n";
}
'''.replace('__CLASS__',cls)
assert 'ChangeStrategy(' not in source
assert 'OnStrategyAdded' not in (root/'BlackwingLairDungeonStrategies.h').read_text()
with tempfile.TemporaryDirectory(prefix='mantech-suppression-') as folder:
 tmp=Path(folder);(tmp/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
 subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
print('PASS: adding/removing room mode cannot delete configured avoidance strategies')
