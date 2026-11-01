"""Execute native stack admission for a mixed Surger/Imp pull."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
s=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
method=block(s,'bool ai::MoltenCorePackStackRequired(')
code=r'''
#include <cassert>
#include <list>
#include <vector>
#include <map>
#include <iostream>
using ObjectGuid=unsigned;
struct Group{};
struct Unit {virtual ~Unit()=default;unsigned entry=0,instance=1;bool world=true,alive=true,combat=true,charmed=false;Unit*victim=nullptr,*master=nullptr;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 virtual bool IsPlayer(){return false;}Unit*GetVictim(){return victim;}Unit*GetMaster(){return master;}};
struct Player:Unit{bool transfer=false,tank=false;unsigned map=409;Group*group=nullptr;bool IsPlayer()override{return true;}
 bool IsBeingTeleported(){return transfer;}unsigned GetMapId(){return map;}Group*GetGroup(){return group;}bool IsInMap(Unit*u){return u&&instance==u->instance;}};
template<class T>struct Value{T value;T Get(){return value;}};
struct Context{Value<std::list<ObjectGuid>>nearby;template<class T>Value<T>*GetValue(const char*){return &nearby;}};
struct PlayerbotAI{Player*bot;Context context;std::map<unsigned,Unit*>units;bool real=false;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned g){return units[g];}};
std::vector<Unit*> MoltenCorePack(PlayerbotAI*){return {};}
std::vector<Player*> MoltenCorePackTanks(PlayerbotAI*,const std::vector<Unit*>&){return {};}
namespace ai {bool MoltenCorePackStackRequired(PlayerbotAI*);}
__METHOD__
int main(){Group group,foreign;Player bot,tank;bot.group=tank.group=&group;tank.tank=true;
 Unit surger,imp;surger.entry=12101;surger.victim=&tank;imp.entry=11669;imp.victim=&tank;
 PlayerbotAI ai{&bot};ai.units={{1,&surger},{2,&imp}};ai.context.nearby.value={1};
 assert(ai::MoltenCorePackStackRequired(&ai));ai.context.nearby.value={1,2};
#ifdef MANGOSBOT_ZERO
 assert(!ai::MoltenCorePackStackRequired(&ai));
 bot.tank=true;assert(ai::MoltenCorePackStackRequired(&ai));bot.tank=false;
 for(unsigned fault=0;fault<5;++fault){imp.world=imp.alive=imp.combat=true;imp.charmed=false;imp.instance=1;
  if(fault==0)imp.world=false;if(fault==1)imp.alive=false;if(fault==2)imp.combat=false;if(fault==3)imp.charmed=true;if(fault==4)imp.instance=2;
  assert(ai::MoltenCorePackStackRequired(&ai));}
 imp.world=imp.alive=imp.combat=true;imp.charmed=false;imp.instance=1;
 Player outsider;outsider.group=&foreign;imp.victim=&outsider;assert(ai::MoltenCorePackStackRequired(&ai));
 Unit pet;pet.master=&tank;imp.victim=&pet;assert(!ai::MoltenCorePackStackRequired(&ai));
#else
 assert(ai::MoltenCorePackStackRequired(&ai));
#endif
 bot.map=489;assert(!ai::MoltenCorePackStackRequired(&ai));
 std::cout<<"PASS actual mixed-imp stack admission, ownership, native lifecycle and era scope\n";
}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mc-mixed-imp-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
