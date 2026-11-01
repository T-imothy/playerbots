"""Actual phase-one pursuit guard: intercept at the raid, don't chase alcoves."""
from pathlib import Path
import ast,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'tests/kelthuzad_opening_target_regression.py').read_text())
prefix=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and '#include <cassert>' in n.value)
prefix=prefix.replace('unsigned GetMapId(){return map;}','bool IsInMap(Player*p){return p&&map==p->map&&ptr==p->ptr;}unsigned GetMapId(){return map;}')
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=prefix+r'''
struct Action{virtual ~Action()=default;Unit*target=nullptr;std::string name;Unit*GetTarget(){return target;}std::string getName(){return name;}};
struct ReachTargetAction:Action{};
struct CastSpellAction:Action{bool movement=false;bool HasMovementEffect(){return movement;}};
struct PreserveKelthuzadOpening{PlayerbotAI*ai;float GetValue(Action*);};
using namespace ai;
namespace ai { bool KelthuzadOpeningApproachAllowed(PlayerbotAI*,Unit*,bool pet=false); }
'''+block(source,'bool ai::KelthuzadDormantAdd(')+'\n'+block(source,'bool ai::KelthuzadOpeningApproachAllowed(')+'\n'+block(source,'float PreserveKelthuzadOpening::GetValue(')+r'''
int main(){
 Player bot,leader;Unit boss,soldier;ScriptedInstance instance;Map map{&instance};instance.boss=&boss;bot.ptr=leader.ptr=&map;
 soldier.entry=16427;soldier.owner=10;soldier.spell=28421;soldier.distance=55;
 PlayerbotAI brain{&bot};brain.master=&leader;PreserveKelthuzadOpening guard{&brain};
 ReachTargetAction reach;reach.name="reach spell";reach.target=&soldier;
 CastSpellAction cast,charge;cast.name="frostbolt";cast.target=&soldier;charge.name="intercept";charge.movement=true;charge.target=&soldier;
 Action behind;behind.name="set behind";behind.target=&soldier;
#ifdef MANGOSBOT_ZERO
 assert(guard.GetValue(&reach)==0&&guard.GetValue(&charge)==0&&guard.GetValue(&behind)==0);
 assert(guard.GetValue(&cast)==1&&guard.GetValue(nullptr)==1); // no cast interruption from approach policy
 brain.heal=true;assert(guard.GetValue(&reach)==0);brain.heal=false;
 leader.alive=false;assert(guard.GetValue(&reach)==0);leader.alive=true;
 soldier.distance=15;assert(guard.GetValue(&reach)==1&&guard.GetValue(&charge)==1);
 assert(!KelthuzadOpeningApproachAllowed(&brain,&soldier,true)); // Native Soldier contact detonates even near the raid.
 soldier.entry=16429;assert(!KelthuzadOpeningApproachAllowed(&brain,&soldier,true)); // Wail of Souls remains ranged work.
 boss.channel=false;assert(KelthuzadOpeningApproachAllowed(&brain,&soldier,true));boss.channel=true;
 soldier.entry=16428;assert(KelthuzadOpeningApproachAllowed(&brain,&soldier,true));
 soldier.distance=55;assert(!KelthuzadOpeningApproachAllowed(&brain,&soldier,true));
 boss.channel=false;assert(KelthuzadOpeningApproachAllowed(&brain,&soldier,true));boss.channel=true;
 soldier.entry=16427;soldier.distance=15;
 soldier.owner=boss.guid;soldier.spell=0;assert(guard.GetValue(&reach)==0); // nearby alcove population is still protected
 soldier.victim=&leader;leader.player=true;assert(guard.GetValue(&reach)==1);soldier.victim=nullptr;
 soldier.owner=10;soldier.spell=28421;soldier.distance=55;
 for(unsigned fault=0;fault<12;++fault){
  if(fault==0)bot.map=469;if(fault==1)bot.world=false;if(fault==2)bot.alive=false;if(fault==3)bot.transfer=true;
  if(fault==4)bot.charmed=true;if(fault==5)brain.real=true;if(fault==6)instance.state=0;if(fault==7)boss.channel=false;
  if(fault==8)leader.map=409;if(fault==9)leader.transfer=true;if(fault==10)leader.group=false;if(fault==11)brain.master=nullptr;
  assert(guard.GetValue(&reach)==1);
  bot.map=533;bot.world=bot.alive=true;bot.transfer=bot.charmed=brain.real=false;instance.state=1;boss.channel=true;
  leader.map=533;leader.transfer=false;leader.group=true;brain.master=&leader;
 }
 for(unsigned entry:{16427u,16428u,16429u}){soldier.entry=entry;assert(guard.GetValue(&reach)==0);}
 soldier.entry=15990;assert(guard.GetValue(&reach)==1);
#else
 assert(guard.GetValue(&reach)==1&&guard.GetValue(&charge)==1&&guard.GetValue(&behind)==1);
 assert(KelthuzadOpeningApproachAllowed(&brain,&soldier,true));
#endif
 std::cout<<"PASS actual KT phase-one approach guard: healer/damage pursuit, ranged cast preservation, corpse anchor, native phase and other-era scope\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='kt-opening-movement-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
strategy=(root/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
for state in ('Combat','NonCombat','Reaction'):
 assert 'new PreserveKelthuzadOpening(ai)' in block(strategy,'void DungeonStrategy::Init'+state+'Multipliers(')
