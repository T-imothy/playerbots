"""Actual MC nuke selector and spell admission; verify action/trigger wiring."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
s=(r/'playerbot/strategy/MoltenCoreTrashPolicy.h').read_text(encoding='utf-8')
methods='\n'.join(block(s,x) for x in ('inline bool MoltenCoreImpAoeOpening(','inline Unit* MoltenCoreNukeTarget(','inline bool MoltenCoreBossBurn(','inline bool MoltenCoreBroadAoeSpell(','inline bool MoltenCoreTrashSpellAllowed('))
code=r'''
#include <cassert>
#include <list>
#include <map>
#include <string>
#include <iostream>
#include <ctime>
using ObjectGuid=unsigned;
struct Unit{unsigned guid=0,entry=0,instance=1;float health=100;bool world=true,alive=true,combat=true,cc=false,hardCC=false,valid=true,charmed=false;bool HasCharmer(){return charmed;}
bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}float GetHealthPercent(){return health;}};
struct Player:Unit{bool teleport=false,charmed=false,tank=false;unsigned map=409;bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}unsigned GetMapId(){return map;}bool IsInMap(Unit*u){return u->instance==instance;}};
template<class T>struct Cached{T value;T Get(){return value;}};
struct Context{Cached<ObjectGuid>marked;Cached<std::list<ObjectGuid>>possible;template<class T>Cached<T>*GetValue(const char*){if constexpr(std::is_same_v<T,ObjectGuid>)return &marked;else return &possible;}};
struct PlayerbotAI{Player*bot;Context context;std::map<unsigned,Unit*>units;time_t started=time(0)-12;time_t GetCombatStartTime(){return started;}Player*GetBot(){return bot;}Context*GetAiObjectContext(){return &context;}bool IsTank(Player*p){return p->tank;}Unit*GetUnit(unsigned g){return units.count(g)?units[g]:nullptr;}};
struct{float sightDistance=60;}sPlayerbotAIConfig;
namespace ai{bool MoltenCoreImpTauntAllowed(PlayerbotAI*,const std::string&){return true;}struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*,float,bool,bool){return u->valid;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
bool MoltenCoreImpUnderPressure(PlayerbotAI*){return false;}
__METHODS__
}
int main(){using namespace ai;Player bot;PlayerbotAI a{&bot};Unit walker,guard,elemental;
walker.guid=10;walker.entry=11666;guard.guid=20;guard.entry=11667;elemental.guid=1;elemental.entry=11659;elemental.health=1;
a.units={{10,&walker},{20,&guard},{1,&elemental}};a.context.possible.value={1,20,10};
assert(MoltenCoreNukeTarget(&a)==&walker);guard.health=50;assert(MoltenCoreNukeTarget(&a)==&guard);
a.context.marked.value=1;assert(MoltenCoreNukeTarget(&a)==&guard);a.context.marked.value=10;assert(MoltenCoreNukeTarget(&a)==&walker);
assert(!MoltenCoreTrashSpellAllowed(&a,"blizzard")&&!MoltenCoreTrashSpellAllowed(&a,"seed of corruption")&&!MoltenCoreTrashSpellAllowed(&a,"whirlwind"));
assert(MoltenCoreTrashSpellAllowed(&a,"cleave")&&MoltenCoreTrashSpellAllowed(&a,"blade flurry")&&MoltenCoreTrashSpellAllowed(&a,"shadow bolt"));
bot.tank=true;assert(MoltenCoreTrashSpellAllowed(&a,"thunder clap"));bot.tank=false;
walker.alive=false;assert(MoltenCoreNukeTarget(&a)==&guard);guard.alive=false;assert(!MoltenCoreNukeTarget(&a)&&MoltenCoreTrashSpellAllowed(&a,"blizzard"));
walker.alive=true;guard.alive=true;walker.cc=true;guard.hardCC=true;assert(!MoltenCoreNukeTarget(&a));walker.cc=false;guard.hardCC=false;
walker.instance=2;guard.instance=2;assert(!MoltenCoreNukeTarget(&a));walker.instance=1;guard.instance=1;
walker.combat=false;guard.combat=false;assert(!MoltenCoreNukeTarget(&a));walker.combat=true;guard.combat=true;
walker.alive=guard.alive=false;elemental.entry=11988;assert(MoltenCoreBossBurn(&a)&&!MoltenCoreTrashSpellAllowed(&a,"blizzard"));elemental.alive=false;assert(!MoltenCoreBossBurn(&a)&&MoltenCoreTrashSpellAllowed(&a,"blizzard"));
elemental.alive=true;elemental.entry=12018;assert(!MoltenCoreTrashSpellAllowed(&a,"cleave")&&!MoltenCoreTrashSpellAllowed(&a,"multi-shot"));
bot.tank=true;assert(!MoltenCoreTrashSpellAllowed(&a,"thunder clap")&&MoltenCoreTrashSpellAllowed(&a,"shield slam")&&MoltenCoreTrashSpellAllowed(&a,"chain heal"));bot.tank=false;
elemental.alive=false;
elemental.alive=true;elemental.entry=11669;a.started=time(0)-9;
assert(!MoltenCoreTrashSpellAllowed(&a,"blizzard")&&!MoltenCoreTrashSpellAllowed(&a,"rain of fire")&&!MoltenCoreTrashSpellAllowed(&a,"multi-shot"));
assert(MoltenCoreTrashSpellAllowed(&a,"shadow bolt")&&MoltenCoreTrashSpellAllowed(&a,"flash heal"));
bot.tank=true;assert(MoltenCoreTrashSpellAllowed(&a,"thunder clap")&&MoltenCoreTrashSpellAllowed(&a,"consecration"));bot.tank=false;
a.started=time(0)-10;assert(MoltenCoreTrashSpellAllowed(&a,"blizzard"));
a.started=0;assert(MoltenCoreTrashSpellAllowed(&a,"blizzard")); // no indefinite opening timer; native action still checks readiness
elemental.combat=false;assert(MoltenCoreTrashSpellAllowed(&a,"blizzard"));
elemental.combat=true;elemental.instance=2;assert(MoltenCoreTrashSpellAllowed(&a,"blizzard"));elemental.instance=1;
elemental.alive=false;a.started=time(0)-12;
bot.map=0;assert(!MoltenCoreNukeTarget(&a)&&MoltenCoreTrashSpellAllowed(&a,"blizzard"));bot.map=409;bot.teleport=true;assert(!MoltenCoreNukeTarget(&a));
std::cout<<"PASS: Firewalker/Flameguard focus ahead of elementals, marked target, CC/map safety, broad AoE hold, cleave and tank threat\n";}
'''.replace('__METHODS__',methods)
mc=(r/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text(encoding='utf-8')
target=block(mc,'Unit* MoltenCorePriorityTargetAction::GetTarget(')
assert target.index('valid(commanded)') < target.index('MoltenCoreNukeTarget(ai)') < target.index('valid(marked) && (bossEntry')
generic=(r/'playerbot/strategy/actions/GenericSpellActions.cpp').read_text(encoding='utf-8')
for name in ('bool CastSpellAction::Execute(','bool CastSpellAction::isUseful('):assert 'MoltenCoreTrashSpellAllowed(ai, GetSpellName())' in block(generic,name)
assert 'MoltenCoreNukeTarget(ai)' in block((r/'playerbot/strategy/values/AoeValues.cpp').read_text(encoding='utf-8'),'bool ai::ControlledRaidAoe(')
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-nuke-') as folder:
  d=Path(folder);(d/'test.cpp').write_text(code,encoding='utf-8')
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
