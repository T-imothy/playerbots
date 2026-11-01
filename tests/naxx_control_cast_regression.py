"""Native-control target cleanup must not cancel an active assigned raid cast."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <initializer_list>
#include <iostream>
using uint32=unsigned;
enum{CLASS_PRIEST=5,CURRENT_GENERIC_SPELL=0,CURRENT_CHANNELED_SPELL=1,SPELL_STATE_FINISHED=2};
struct Unit{unsigned entry=16803,owner=0;bool world=true,alive=true,same=true,engaged=true;float distance=10;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return owner!=0;}bool HasCharmer(unsigned g){return owner==g;}
 unsigned GetEntry(){return entry;}float GetDistance(Unit*){return distance;}};
struct SpellEntry{unsigned Id=10912;};
struct Targets{Unit*unit=nullptr;Unit*getUnitTarget()const{return unit;}};
struct Spell{SpellEntry*m_spellInfo=nullptr;Targets m_targets;unsigned state=0;unsigned getState()const{return state;}};
struct Player:Unit{unsigned map=533,cls=5,id=1;Spell*casts[2]={};unsigned GetMapId(){return map;}unsigned getClass(){return cls;}
 bool IsInMap(Unit*u){return u&&u->same;}unsigned GetObjectGuid(){return id;}Spell*GetCurrentSpell(unsigned slot){return casts[slot];}};
struct PlayerbotAI{Player bot;Unit boss;bool ready=true,allowed=true;PlayerbotAI(){boss.entry=16061;}Player*GetBot(){return &bot;}};
bool Ready(PlayerbotAI*a){return a->ready;}bool NaxxramasControlAllowed(PlayerbotAI*a){return a->allowed;}
Unit*FindBoss(PlayerbotAI*a,unsigned entry){return a->boss.entry==entry?&a->boss:nullptr;}
bool Engaged(Player*,Unit*u){return u&&u->engaged;}
namespace naxxnative{unsigned MindControl(){return 10912;}}
namespace ai{bool HasNaxxramasControlCast(PlayerbotAI*);}
__BODY__
int main(){PlayerbotAI a;Unit student;SpellEntry entry;Spell cast{&entry,{&student}};
 for(unsigned slot:{0u,1u}){a.bot.casts[0]=a.bot.casts[1]=nullptr;a.bot.casts[slot]=&cast;
#ifdef MANGOSBOT_ZERO
 assert(ai::HasNaxxramasControlCast(&a));student.owner=1;assert(ai::HasNaxxramasControlCast(&a));student.owner=0;
#else
 assert(!ai::HasNaxxramasControlCast(&a));
#endif
 }
 assert(!ai::HasNaxxramasControlCast(nullptr));
 a.ready=false;assert(!ai::HasNaxxramasControlCast(&a));a.ready=true;
 a.allowed=false;assert(!ai::HasNaxxramasControlCast(&a));a.allowed=true;
 a.bot.map=469;assert(!ai::HasNaxxramasControlCast(&a));a.bot.map=533;
 a.bot.cls=8;assert(!ai::HasNaxxramasControlCast(&a));a.bot.cls=5;
 cast.state=2;assert(!ai::HasNaxxramasControlCast(&a));cast.state=0;
 entry.Id=25314;assert(!ai::HasNaxxramasControlCast(&a));entry.Id=10912;
 student.owner=2;assert(!ai::HasNaxxramasControlCast(&a));student.owner=0;
 student.alive=false;assert(!ai::HasNaxxramasControlCast(&a));student.alive=true;
 student.world=false;assert(!ai::HasNaxxramasControlCast(&a));student.world=true;
 student.same=false;assert(!ai::HasNaxxramasControlCast(&a));student.same=true;
 student.distance=80;assert(!ai::HasNaxxramasControlCast(&a));student.distance=10;
 a.boss.engaged=false;assert(!ai::HasNaxxramasControlCast(&a));a.boss.engaged=true;
 student.entry=16506;a.boss.entry=15953;
#ifdef MANGOSBOT_ZERO
 assert(ai::HasNaxxramasControlCast(&a));
#endif
 student.entry=123;assert(!ai::HasNaxxramasControlCast(&a));
 cast.m_targets.unit=nullptr;assert(!ai::HasNaxxramasControlCast(&a));
 std::cout<<"PASS: Classic native control cast/channel survives target cleanup only while owned valid encounter duty remains\n";
}
'''.replace('__BODY__',block(source,'bool ai::HasNaxxramasControlCast('))
recovery=block((root/'playerbot/strategy/actions/ChooseTargetActions.cpp').read_text(),'bool SelectNewTargetAction::Execute(')
assert recovery.index('if (HasNaxxramasControlCast(ai)) return false;')<recovery.index('bot->SetSelectionGuid')
with tempfile.TemporaryDirectory(prefix='naxx-control-cast-')as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 for era in('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
