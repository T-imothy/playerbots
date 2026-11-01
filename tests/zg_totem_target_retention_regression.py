"""Actual invalid-target validation retains only the elected native ZG totem."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/values/InvalidTargetValue.cpp').read_text()
code=r'''
#include <cassert>
#include <algorithm>
#include <list>
#include <string>
#include <type_traits>
#include <iostream>
using ObjectGuid=unsigned;
enum class BotState{BOT_STATE_COMBAT};
struct Unit{unsigned entry=15112,guid=7;unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}};
struct Player{unsigned map=309,selection=7;unsigned GetMapId(){return map;}unsigned GetSelectionGuid(){return selection;}};
Unit target,other;Unit*objective=&target;bool basic=true,protectedCC=false,attackable=false;
struct PlayerbotAI{bool dungeon=true;Unit*GetUnit(unsigned g){return g==target.guid?&target:nullptr;}bool HasStrategy(const char*,BotState){return dungeon;}};
struct PossibleTargetsValue{static bool IsValid(Unit*,Player*,bool){return basic;}};
struct PossibleAttackTargetsValue{static bool IsValid(Unit*,Player*){return attackable;}static bool IsPossibleTarget(Unit*,Player*,float,bool){return false;}};
struct MeleeCcCheck{MeleeCcCheck(PlayerbotAI*){}bool Protected(Unit*){return protectedCC;}};
struct DungeonAddTargetAction{DungeonAddTargetAction(PlayerbotAI*){}Unit*GetTarget(){return objective;}};
Unit*RazorgoreDefenseTarget(PlayerbotAI*,bool&defense){defense=false;return nullptr;}
Unit*KelthuzadOpeningTarget(PlayerbotAI*){return nullptr;}
bool RaidLabMovementResult(Player*,const char*,unsigned,bool b){return b;}
struct{float sightDistance=60;}sPlayerbotAIConfig;
template<class T>T Value(const std::string&key){if constexpr(std::is_same_v<T,unsigned>)return key=="duel target"?0:target.guid;else return {};}
#define AI_VALUE(type,key) Value<type>(key)
struct InvalidTargetValue{PlayerbotAI*ai;Player*bot;std::string qualifier="current target";bool Calculate();};
'''+block(source,'bool InvalidTargetValue::Calculate()')+r'''
int main(){
 Player bot;PlayerbotAI ai;InvalidTargetValue value{&ai,&bot};
 for(unsigned entry:{15112u,14987u,10218u}){
  target.entry=entry;
#ifdef MANGOSBOT_ZERO
  assert(!value.Calculate());
#else
  assert(value.Calculate());
#endif
 }
 target.entry=15112;objective=&other;assert(value.Calculate());objective=&target;
 ai.dungeon=false;assert(value.Calculate());ai.dungeon=true;
 basic=false;assert(value.Calculate());basic=true;
 protectedCC=true;assert(value.Calculate());protectedCC=false;
 bot.selection=99;assert(value.Calculate());bot.selection=7;
 value.qualifier="attack target";assert(value.Calculate());value.qualifier="current target";
 target.entry=14986;assert(value.Calculate());target.entry=15112;
 bot.map=533;assert(value.Calculate());bot.map=209;target.entry=8179;assert(!value.Calculate());
 bot.map=70;target.entry=3560;assert(!value.Calculate());
 std::cout<<"PASS exact Classic ZG totem retained; changed objective, CC, selection, lifecycle, other entries/eras remain rejected\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='zg-totem-retention-') as folder:
  path=Path(folder);(path/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
  if r.returncode:print(r.stdout,r.stderr)
  r.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
