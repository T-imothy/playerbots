"""Actual Gothik ownership guard + IsValid: first attacks need no personal threat."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/values/NaxxramasPositionValue.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('bool ai::NaxxramasEncounterEngaged(', 'bool ai::GothikGroupEngagedAdd('))
methods+='\n'+block((root/'playerbot/strategy/values/PossibleAttackTargetsValue.cpp').read_text(),'bool PossibleAttackTargetsValue::IsValid(')
code=r'''
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <vector>
using uint32=unsigned;
constexpr unsigned IN_PROGRESS=1,GO_STATE_READY=1,UNIT_FIELD_TARGET=1;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned n=0):id(n){}bool IsPlayer()const{return false;}bool operator==(ObjectGuid g)const{return id==g.id;}};
struct Unit;struct Player;struct GameObject;struct Group;struct Map;
struct InstanceData{virtual ~InstanceData()=default;};
struct ScriptedInstance:InstanceData{unsigned state=IN_PROGRESS;Unit*boss=nullptr;GameObject*gate=nullptr;
 unsigned GetData(unsigned n){assert(n==7);return state;}Unit*GetSingleCreatureFromStorage(unsigned n,bool){assert(n==16060);return boss;}
 GameObject*GetSingleGameObjectFromStorage(unsigned n){assert(n==181170);return gate;}};
struct Map{InstanceData*instance=nullptr;InstanceData*GetInstanceData(){return instance;}};
struct Threat{std::set<Unit*>members;float getThreat(Unit*u){return members.count(u)?1:0;}Unit*getCurrentVictim(){return reinterpret_cast<Unit*>(1);}};
struct Unit{virtual ~Unit()=default;unsigned mapId=533,instance=1,entry=0;Map*map=nullptr;float y=0;
 bool world=true,alive=true,combat=true,charmed=false,player=false,personal=false,possible=true,cc=false;Unit*victim=nullptr,*master=nullptr;
 Threat threat;std::set<Unit*>attackers;ObjectGuid guid;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool IsPlayer(){return player;}unsigned GetMapId(){return mapId;}unsigned GetEntry(){return entry;}float GetPositionY(){return y;}
 Map*GetMap(){return map;}bool IsInMap(Unit*u){return u&&map==u->map&&mapId==u->mapId&&instance==u->instance;}
 Unit*GetVictim(){return victim;}Unit*GetMaster(){return master;}auto&getAttackers(){return attackers;}auto&getThreatManager(){return threat;}
 ObjectGuid GetObjectGuid(){return guid;}unsigned GetGuidValue(unsigned){return 0;}};
struct GameObject:Unit{unsigned state=GO_STATE_READY;unsigned GetGoState(){return state;}};
struct Brain{bool HasActivePlayerMaster(){return false;}};
struct Player:Unit{Player(){player=true;}bool transfer=false;Group*group=nullptr;
 bool IsBeingTeleported(){return transfer;}Group*GetGroup(){return group;}Brain*GetPlayerbotAI(){return nullptr;}};
struct Ref{Player*p;Ref*n=nullptr;Player*getSource(){return p;}Ref*next(){return n;}};
using GroupReference=Ref;
struct Group{std::vector<Ref>refs;Ref*GetFirstMember(){for(unsigned i=0;i<refs.size();++i)refs[i].n=i+1<refs.size()?&refs[i+1]:nullptr;return refs.empty()?nullptr:&refs[0];}};
struct Server{Threat&GetThreatManager(Unit*u){return u->threat;}}sServerFacade;
bool RaidLabMovementResult(Player*,const char*,unsigned,bool result){return result;}
#define PAI_VALUE(type,name) ObjectGuid()
namespace ai{
bool NaxxramasEncounterEngaged(Player*,Unit*);bool GothikGroupEngagedAdd(Player*,Unit*);
struct AttackersValue{static bool IsValid(Unit*u,Player*){return u&&u->personal;}};
unsigned possibleChecks=0;
struct PossibleAttackTargetsValue{
 static bool IsValid(Unit*,Player*,float=60,bool=false,bool=true);
 static bool IsPossibleTarget(Unit*u,Player*,float,bool){++possibleChecks;return u&&u->possible&&!u->cc;}
 static bool HasIgnoreCCRti(Unit*,Player*){return false;}static bool HasBreakableCC(Unit*,Player*){return false;}static bool HasUnBreakableCC(Unit*,Player*){return false;}
};}
using namespace ai;
__METHODS__
int main(){
 Map map;ScriptedInstance native;map.instance=&native;Group group,foreign;
 Player bot,tank,stranger;bot.map=tank.map=stranger.map=&map;bot.group=tank.group=&group;stranger.group=&foreign;
 group.refs={{&bot},{&tank}};foreign.refs={{&stranger}};bot.y=tank.y=-20;
 Unit boss,add,pet;boss.map=add.map=pet.map=&map;boss.entry=16060;add.entry=16124;add.y=-10;
 boss.victim=add.victim=&tank;native.boss=&boss;GameObject gate;gate.map=&map;native.gate=&gate;
 auto check=[&](){return PossibleAttackTargetsValue::IsValid(&add,&bot);};
#ifdef MANGOSBOT_ZERO
 assert(!add.personal&&check()&&possibleChecks==1);
 add.cc=true;assert(!check());add.cc=false;add.possible=false;assert(!check());add.possible=true;
 for(unsigned e:{16124u,16125u,16126u,16127u,16148u,16149u,16150u}){add.entry=e;assert(check());}
 add.entry=16028;assert(!check());add.entry=16124;
 add.y=10;assert(!check());gate.state=0;assert(check());gate.state=GO_STATE_READY;add.y=-10;
 add.victim=&stranger;assert(!check());add.victim=&pet;pet.master=&tank;assert(check());pet.master=&stranger;assert(!check());add.victim=&tank;
 native.state=0;assert(!check());native.state=IN_PROGRESS;
 boss.combat=false;assert(!check());boss.combat=true;boss.victim=&stranger;assert(!check());boss.victim=&tank;
 native.gate=nullptr;assert(!check());native.gate=&gate;gate.instance=2;assert(!check());gate.instance=1;
 add.instance=2;assert(!check());add.instance=1;add.alive=false;assert(!check());add.alive=true;
 tank.transfer=true;assert(!check());tank.transfer=false;bot.transfer=true;assert(!check());bot.transfer=false;
 add.combat=false;assert(!check());add.combat=true;bot.mapId=469;assert(!check());bot.mapId=533;
 assert(check());
#else
 assert(!check()&&possibleChecks==0);
#endif
 add.personal=true;assert(check());add.possible=false;assert(!check());
 std::cout<<"PASS actual Gothik first-attack ownership, native phase, sides, CC/range/LOS admission retained and other-era isolation\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='gothik-group-target-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
