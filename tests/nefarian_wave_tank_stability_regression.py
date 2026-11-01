"""Exercise actual native-phase gate and stable wave pickup under changing peers/roster."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
code=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
using uint32=unsigned;constexpr unsigned IN_PROGRESS=1;
struct Guid{uint64_t raw=0;uint64_t GetRawValue(){return raw;}bool operator<(Guid g)const{return raw<g.raw;}};
struct Unit{virtual ~Unit()=default;Guid guid;unsigned entry=14265,map=469;bool alive=true,world=true,combat=true,charmed=false,barrier=true,engaged=true;Unit*victim=nullptr;float distance=10;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetEntry(){return entry;}Guid GetObjectGuid(){return guid;}Unit*GetVictim(){return victim;}float GetDistance(Unit*){return distance;}
 bool IsInMap(Unit*u){return u&&u->map==map;}bool HasAura(unsigned s){assert(s==22663);return barrier;}};
struct Instance{virtual ~Instance()=default;};
struct ScriptedInstance:Instance{unsigned state=1;Unit*boss=nullptr;unsigned GetData(unsigned k){assert(k==7);return state;}
 Unit*GetSingleCreatureFromStorage(unsigned e,bool){assert(e==10162);return boss;}};
struct Map{Instance*instance=nullptr;Instance*GetInstanceData(){return instance;}};
struct PlayerbotAI;
struct Player:Unit{void*group=nullptr;bool transfer=false,tank=true;Map*mapObject=nullptr;
 void*GetGroup(){return group;}unsigned GetMapId(){return map;}bool IsBeingTeleported(){return transfer;}Map*GetMap(){return mapObject;}};
struct PlayerbotAI{Player*bot;bool real=false;Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p&&p->tank;}};
bool BwlGroupEngaged(PlayerbotAI*a,Unit*u){return u&&u->world&&u->alive&&u->combat&&u->engaged&&a->bot->IsInMap(u);}
'''+block(source,'bool BwlReady(')+'\n'+block(source,'bool BwlMember(')+'\n'+block(source,'bool NefariusWaveEncounter(')+'\n'+block(source,'Unit* NefariusStableWaveTank(')+r'''
int main(){
 Player a,b,c,d,healer,human;int group=0;for(auto*p:{&a,&b,&c,&d,&healer,&human})p->group=&group;
 healer.tank=false;Unit boss;boss.entry=10162;ScriptedInstance instance;instance.boss=&boss;Map map{&instance};a.mapObject=&map;
 PlayerbotAI brain{&a};
#ifdef MANGOSBOT_ZERO
 assert(NefariusWaveEncounter(&brain));
 for(unsigned fault=0;fault<9;++fault){
  if(fault==0)a.map=533;if(fault==1)brain.real=true;if(fault==2)a.combat=false;if(fault==3)boss.barrier=false;
  if(fault==4)instance.state=0;if(fault==5)boss.engaged=false;if(fault==6)boss.alive=false;if(fault==7)a.transfer=true;if(fault==8)a.group=nullptr;
  assert(!NefariusWaveEncounter(&brain));a.map=469;brain.real=false;a.combat=true;boss.barrier=true;instance.state=1;boss.engaged=boss.alive=true;a.transfer=false;a.group=&group;
 }
#else
 assert(!NefariusWaveEncounter(&brain));
#endif
 std::vector<Player*> tanks{&a,&b,&c,&d};
 Unit x,y,z,old,peer,unrelated;x.guid.raw=100;y.guid.raw=104;z.guid.raw=108;peer.guid.raw=101;old.guid.raw=99;unrelated.guid.raw=112;unrelated.entry=12459;
 x.distance=40;y.distance=20;z.distance=2;peer.distance=3;
 for(auto*u:{&x,&y,&z,&old,&peer,&unrelated})u->victim=&healer;
 a.victim=&x;
 std::vector<Unit*> enemies{&old,&x,&y,&peer};
 assert(NefariusStableWaveTank(&brain,enemies,tanks)==&x); // finish existing approach
 enemies.erase(enemies.begin());assert(NefariusStableWaveTank(&brain,enemies,tanks)==&x); // earlier death cannot shift slots
 enemies.push_back(&z);assert(NefariusStableWaveTank(&brain,enemies,tanks)==&x); // newer/closer add cannot interrupt pickup
 peer.victim=&b;assert(NefariusStableWaveTank(&brain,enemies,tanks)==&x); // changing peer load cannot swap rescue
 x.victim=&human;assert(NefariusStableWaveTank(&brain,enemies,tanks)==&z); // preserve human tank
 z.victim=&c;assert(NefariusStableWaveTank(&brain,enemies,tanks)==&y); // preserve other bot tank
 y.victim=&a;assert(NefariusStableWaveTank(&brain,enemies,tanks)==&y); // continue held add when all pickups secured
 enemies={&unrelated};assert(!NefariusStableWaveTank(&brain,enemies,tanks));
 enemies={&peer};peer.victim=&healer;brain.bot=&b;assert(NefariusStableWaveTank(&brain,enemies,tanks)==&peer);
 tanks.erase(tanks.begin()+1);brain.bot=&a;assert(!NefariusStableWaveTank(&brain,enemies,tanks));
 brain.bot=&d;assert(NefariusStableWaveTank(&brain,enemies,tanks)==&peer); // dead tank's slot reassigned
 tanks.clear();assert(!NefariusStableWaveTank(&brain,enemies,tanks));
 std::cout<<"PASS Nefarius native barrier/instance/era gate, stable current pickup across spawn/death/peer threat, holder protection and tank death\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='nefarian-wave-tanks-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
