"""Execute the phase-scoped drakonid guard and verify formation ownership."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;
struct Unit{unsigned entry=14261;bool engaged=true,charmed=false;unsigned GetEntry(){return entry;}bool HasCharmer(){return charmed;}};
struct Player{};
struct PlayerbotAI{Player bot;bool active=true;Player*GetBot(){return &bot;}};
bool Engaged(Player*,Unit*u){return u&&u->engaged;}
bool NefariusImmolationUnsafe(PlayerbotAI*a){return a->active;}
__BODY__
int main(){PlayerbotAI ai;Unit target;
 for(unsigned entry:{14261u,14262u,14263u,14264u,14265u,14302u}){
  target.entry=entry;
#ifdef MANGOSBOT_ZERO
  assert(NefariusWaveTarget(&ai,&target));
#else
  assert(!NefariusWaveTarget(&ai,&target));
#endif
 }
 for(unsigned entry:{11583u,10162u,14605u,12435u,12416u,12017u}){
  target.entry=entry;assert(!NefariusWaveTarget(&ai,&target));
 }
 target.entry=14302;target.engaged=false;assert(!NefariusWaveTarget(&ai,&target));target.engaged=true;
 target.charmed=true;assert(!NefariusWaveTarget(&ai,&target));target.charmed=false;
 ai.active=false;assert(!NefariusWaveTarget(&ai,&target));
 assert(!NefariusWaveTarget(&ai,nullptr));
 std::cout<<"PASS: drakonid wave movement is phase/entry/engagement scoped; other encounters and eras unchanged\n";
}
'''.replace('__BODY__',block(source,'    bool NefariusWaveTarget('))
calculate=block(source,'ClassicRaidPlan ClassicRaidPlanValue::Calculate(')
guard='if (ai->IsTank(bot) && NefariusWaveTarget(ai, target)) return plan;'
assert calculate.index(guard)<calculate.index('if (KeepFormationRoute(')
assert 'target->GetDistance(bot) < NativeEncounterSpellRadius(22560)' in calculate
assert '(classicraid::Front(target->GetEntry()) || waveCone) && target->GetVictim() != bot' in calculate
assert 'ai->IsTank(ai->GetBot()) && NefariusWaveTarget(ai, boss)' in block(source,'bool ClassicRaidPositionAction::GetPlan(')
with tempfile.TemporaryDirectory(prefix='nef-wave-move-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
