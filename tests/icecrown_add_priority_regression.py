"""Exercise native-owned ICC objectives and live physical/magic protection changes."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/actions/IcecrownAddTargetAction.cpp').read_text(),'Unit* DungeonAddTargetAction::GetIcecrownAddTarget(')
fixture=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <string>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;constexpr unsigned CLASS_HUNTER=3;
struct Unit{unsigned guid=0,entry=0,spawner=0,phase=1;bool world=true,alive=true,combat=true,charm=false,valid=true,cc=false;
 bool flying=false;bool IsFlying(){return flying;}float x=0;Unit*victim=nullptr;std::map<unsigned,unsigned>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}
 unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}unsigned GetSpawnerGuid(){return spawner;}
 Unit*GetVictim(){return victim;}float GetDistance(Unit*u){return std::abs(x-u->x);}
 void*GetSpellAuraHolder(unsigned id,unsigned owner){return auras.count(id)&&auras[id]==owner?this:nullptr;}};
struct Group{};
struct Player:Unit{unsigned map=631,cls=8;bool teleport=false;Group*group=nullptr;
 unsigned GetMapId(){return map;}unsigned getClass(){return cls;}Group*GetGroup(){return group;}
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&u->phase==phase;}};
struct PlayerbotAI{Player*bot;bool real=false,ranged=true;Unit*current=nullptr;std::map<unsigned,Unit*>units;std::list<unsigned>near;
 bool IsRealPlayer(){return real;}bool IsRanged(Player*){return ranged;}
 Unit*GetUnit(unsigned id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}
 template<class T>T value(std::string){return current;}template<class T>T qualified(std::string,std::string){return near;}};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*,bool){return u->valid;}};
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*b,float range,bool ignore){assert(!ignore);return !u->cc&&b->GetDistance(u)<=range;}};
struct DungeonAddTargetAction{PlayerbotAI*ai;Player*bot;Unit*GetIcecrownAddTarget();};
#define AI_VALUE(type,key) ai->value<type>(key)
#define AI_VALUE2(type,key,q) ai->qualified<type>(key,q)
__METHOD__
int main(){
 Group group;Player bot,tank;bot.group=&group;Unit boss,add,other;
 boss.guid=1;boss.entry=36855;boss.victim=&tank;add.guid=2;add.spawner=1;add.entry=37890;add.x=15;
 PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&add},{3,&other}};ai.near={1,2};DungeonAddTargetAction action{&ai,&bot};
#ifndef MANGOSBOT_TWO
 assert(!action.GetIcecrownAddTarget());std::cout<<"PASS: ICC objective inactive outside Wrath\n";return 0;
#else
 for(unsigned entry:{37890u,37949u,38135u,38136u,38009u,38010u}){add.entry=entry;assert(action.GetIcecrownAddTarget()==&add);}
 add.entry=38222;assert(!action.GetIcecrownAddTarget()); // Never try killing a vengeful shade as a cultist.
 add.entry=38010;add.auras[71234]=2;assert(!action.GetIcecrownAddTarget());
 bot.cls=CLASS_HUNTER;assert(action.GetIcecrownAddTarget()==&add);ai.ranged=false;assert(action.GetIcecrownAddTarget()==&add);
 add.entry=38009;add.auras.clear();add.auras[71235]=2;assert(!action.GetIcecrownAddTarget());
 ai.ranged=true;assert(!action.GetIcecrownAddTarget());bot.cls=8;assert(action.GetIcecrownAddTarget()==&add);
 add.auras.clear();add.entry=38135;ai.ranged=false;assert(!action.GetIcecrownAddTarget());ai.ranged=true;
 add.entry=37890;other=add;other.guid=3;other.entry=38136;other.x=30;ai.near.push_back(3);ai.current=&add;
 assert(action.GetIcecrownAddTarget()==&other);other.entry=37890;assert(action.GetIcecrownAddTarget()==&add);ai.near.pop_back();
 boss.entry=37813;add.entry=38508;assert(action.GetIcecrownAddTarget()==&add);ai.ranged=false;assert(!action.GetIcecrownAddTarget());ai.ranged=true;
 add.spawner=99;assert(!action.GetIcecrownAddTarget());add.spawner=1;boss.entry=36855;assert(!action.GetIcecrownAddTarget());boss.entry=37813;
 add.cc=true;assert(!action.GetIcecrownAddTarget());add.cc=false;add.valid=false;assert(!action.GetIcecrownAddTarget());add.valid=true;
 add.phase=2;assert(!action.GetIcecrownAddTarget());add.phase=1;add.x=61;assert(!action.GetIcecrownAddTarget());add.x=15;
 boss.alive=false;assert(!action.GetIcecrownAddTarget());boss.alive=true;boss.combat=false;assert(!action.GetIcecrownAddTarget());boss.combat=true;
 boss.victim=&bot;assert(!action.GetIcecrownAddTarget());boss.victim=&tank;bot.teleport=true;assert(!action.GetIcecrownAddTarget());bot.teleport=false;
 ai.real=true;assert(!action.GetIcecrownAddTarget());ai.real=false;bot.map=0;assert(!action.GetIcecrownAddTarget());bot.map=631;
 boss.entry=36853;add.entry=36980;assert(action.GetIcecrownAddTarget()==&add);
 boss.flying=true;assert(!action.GetIcecrownAddTarget());boss.flying=false;assert(action.GetIcecrownAddTarget()==&add);
 boss.entry=37813;add.entry=38508;
 // One live boss cannot authorize another boss's adds.
 Unit secondBoss;secondBoss.guid=4;secondBoss.entry=36855;secondBoss.victim=&tank;
 other.entry=37890;other.spawner=4;ai.units[4]=&secondBoss;ai.near.push_back(3);assert(!action.GetIcecrownAddTarget());
 std::cout<<"PASS: ICC native ownership, transformed-target priorities, protection changes, hunter/melee assignment and lifecycle\n";
#endif
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='icc-priority-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(fixture)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
dispatcher=(root/'playerbot/strategy/actions/DungeonAddTargetAction.cpp').read_text()
for gate in ('ai->IsHeal(bot)','ai->IsTank(bot)','commanded(ai->GetUnit'):
    assert dispatcher.index(gate)<dispatcher.index('GetIcecrownAddTarget()')
