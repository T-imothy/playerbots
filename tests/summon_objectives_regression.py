"""Execute dungeon objective ownership, split-phase and pre-pull safeguards."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/actions/SummonObjectiveTargetAction.cpp').read_text(),'Unit* DungeonAddTargetAction::GetSummonObjectiveTarget(')
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <set>
#include <string>
#include <iostream>
#include <algorithm>
#include <iterator>
using uint32=unsigned;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned v=0):id(v){}operator unsigned()const{return id;}bool IsEmpty()const{return !id;}};
enum{UNIT_CREATED_BY_SPELL};
struct Unit{unsigned entry=0,guid=0,phase=1,created=0,spawner=0;
 bool world=true,alive=true,charmed=false,combat=true,player=false,valid=true,cc=false;float x=0;Unit* victim=nullptr;std::set<unsigned>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}bool IsPlayer(){return player;}
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}bool HasAura(unsigned id){return auras.count(id);}
 unsigned GetUInt32Value(unsigned field){assert(field==UNIT_CREATED_BY_SPELL);return created;}ObjectGuid GetSpawnerGuid(){return spawner;}
 float GetDistance(Unit*u){return std::abs(x-u->x);}Unit* GetVictim(){return victim;}};
struct Group{};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Player:Unit{Player(){player=true;}unsigned map=553;bool teleport=false;Group* group=nullptr;
 Map instance;Map* GetMap(){return &instance;}
 unsigned GetMapId(){return map;}Group* GetGroup(){return group;}bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&u->phase==phase;}};
struct PlayerbotAI{Player* bot;Unit* current=nullptr;std::map<unsigned,Unit*> units;std::list<ObjectGuid> near;bool ranged=true;
 bool IsRanged(Player*){return ranged;}
 Unit* GetUnit(ObjectGuid id){return units.count(id)?units[id]:nullptr;}
 template<class T>T value(std::string name){assert(name=="current target");return current;}
 template<class T>T qualified(std::string name,std::string qualifier){assert(name=="possible targets"&&qualifier=="100:1");return near;}};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*,bool){return u->valid;}};
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*b,float range,bool ignore){assert(!ignore);return !u->cc&&b->GetDistance(u)<=range;}};
struct DungeonAddTargetAction{PlayerbotAI* ai;Player* bot;Unit* GetSummonObjectiveTarget();};
#define AI_VALUE(type,key) ai->value<type>(key)
#define AI_VALUE2(type,key,q) ai->qualified<type>(key,q)
__METHOD__
int main(){
 struct Row{unsigned map,boss,add;};
 for(Row row: {Row{230,9156,9178},{509,15340,15527},{531,15299,15667},{531,15510,15630},{553,17977,19949},{557,18344,18431},{556,18472,19203},{558,18373,18441},{558,18373,18478},{576,26731,26928},{608,29313,29321},{619,29310,30385},{632,36497,36535},{650,34928,34942}}){
  Group group,other;Player bot,tank,source;bot.map=row.map;bot.group=tank.group=source.group=&group;source.guid=4;
  Unit boss,add,duplicate;boss.guid=1;boss.entry=row.boss;boss.victim=&tank;boss.valid=false;
  add.guid=2;add.entry=row.add;add.spawner=1;add.combat=false;add.x=20;
  if(row.map==619)boss.auras.insert(56100);
  if(row.map==650)boss.auras.insert(66515);
  if(row.map==576)boss.auras.insert(47710);
  if(row.add==18441){add.spawner=4;add.created=32360;}
  if(row.map==632){add.spawner=4;add.created=68846;}
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&add},{4,&source}};ai.near={1,2};DungeonAddTargetAction a{&ai,&bot};
#ifdef MANGOSBOT_ZERO
  if(row.map!=230&&row.map!=509&&row.map!=531){assert(!a.GetSummonObjectiveTarget());continue;}
#elif defined(MANGOSBOT_ONE)
  if(row.map!=230&&row.map!=509&&row.map!=531&&row.map!=553&&row.map!=557&&row.map!=556&&row.map!=558){assert(!a.GetSummonObjectiveTarget());continue;}
#endif
  assert(a.GetSummonObjectiveTarget()==&add);ai.current=&add;
  duplicate=add;duplicate.guid=3;duplicate.x=5;ai.units[3]=&duplicate;ai.near.push_back(3);
  assert(a.GetSummonObjectiveTarget()==(row.map==230?&duplicate:&add));
  if(row.map==230){
   duplicate.x=20;assert(a.GetSummonObjectiveTarget()==&add); // Equal urgency preserves current target.
   duplicate.x=25;assert(a.GetSummonObjectiveTarget()==&add);
   duplicate.x=5;duplicate.spawner=99;assert(a.GetSummonObjectiveTarget()==&add);duplicate.spawner=1;
   duplicate.cc=true;assert(a.GetSummonObjectiveTarget()==&add);duplicate.cc=false;
  }
  add.alive=false;assert(a.GetSummonObjectiveTarget()==&duplicate);add.alive=true;ai.near.pop_back();
  add.cc=true;assert(!a.GetSummonObjectiveTarget());add.cc=false;add.valid=false;assert(!a.GetSummonObjectiveTarget());add.valid=true;
  add.x=61;assert(!a.GetSummonObjectiveTarget());add.x=20;add.phase=2;assert(!a.GetSummonObjectiveTarget());add.phase=1;
  unsigned spawner=add.spawner;add.spawner=99;assert(!a.GetSummonObjectiveTarget());add.spawner=spawner;
  boss.combat=false;assert(!a.GetSummonObjectiveTarget());boss.combat=true;boss.victim=&bot;assert(!a.GetSummonObjectiveTarget());boss.victim=&tank;
  bot.teleport=true;assert(!a.GetSummonObjectiveTarget());bot.teleport=false;
  duplicate=boss;duplicate.guid=3;ai.near.push_back(3);assert(!a.GetSummonObjectiveTarget());ai.near.pop_back();
  if(row.map==557){
   add.spawner=0;assert(!a.GetSummonObjectiveTarget());add.combat=true;add.victim=&tank;assert(a.GetSummonObjectiveTarget()==&add);
   tank.group=&other;assert(!a.GetSummonObjectiveTarget());tank.group=&group;
   add.spawner=99;assert(!a.GetSummonObjectiveTarget());add.spawner=0;assert(a.GetSummonObjectiveTarget()==&add);
  }
  if(row.map==619){
   add.auras.insert(56102);assert(!a.GetSummonObjectiveTarget());add.auras.clear();assert(a.GetSummonObjectiveTarget()==&add);
   boss.auras.clear();assert(!a.GetSummonObjectiveTarget());boss.auras.insert(56100);
  }
  if(row.map==632){
   add.created=68848;assert(!a.GetSummonObjectiveTarget());add.created=68846;
   source.group=&other;assert(!a.GetSummonObjectiveTarget());source.group=&group;
   source.world=false;assert(!a.GetSummonObjectiveTarget());source.world=true;
   source.teleport=true;assert(!a.GetSummonObjectiveTarget());source.teleport=false;
   assert(a.GetSummonObjectiveTarget()==&add); // Corrupt Soul already expired when actual summon happens.
  }
  if(row.map==556||row.map==576){
   unsigned first=row.map==556?19203:26928,last=row.map==556?19206:26930;
   for(unsigned entry=first;entry<=last;++entry){add.entry=entry;assert(a.GetSummonObjectiveTarget()==&add);}
   add.entry=last+1;assert(!a.GetSummonObjectiveTarget());add.entry=first;
   if(row.map==576){boss.auras.clear();assert(!a.GetSummonObjectiveTarget());boss.auras.insert(47710);}
  }
  if(row.add==18441){
   add.created=32361;assert(!a.GetSummonObjectiveTarget());add.created=32360;
   source.group=&other;assert(!a.GetSummonObjectiveTarget());source.group=&group;
   source.teleport=true;assert(!a.GetSummonObjectiveTarget());source.teleport=false;
   // Switching between player-owned soul and boss-owned avatar must not leak ownership mode.
   duplicate=add;duplicate.guid=3;duplicate.entry=18478;duplicate.spawner=1;duplicate.created=32424;
   ai.near.push_back(3);add.alive=false;assert(a.GetSummonObjectiveTarget()==&duplicate);add.alive=true;
   assert(a.GetSummonObjectiveTarget()==&add);ai.near.pop_back();
  }
  if(row.map==650){
   for(unsigned entry:{34942u,35028u,35029u,35030u,35031u,35032u,35033u,35034u,35036u,35037u,35038u,35039u,35040u,35041u,35042u,35043u,35044u,35045u,35046u,35047u,35048u,35049u,35050u,35051u,35052u}){
    add.entry=entry;assert(a.GetSummonObjectiveTarget()==&add);
   }
   add.entry=35035;assert(!a.GetSummonObjectiveTarget());add.entry=34942;
   boss.auras.clear();assert(!a.GetSummonObjectiveTarget());boss.auras.insert(66515);assert(a.GetSummonObjectiveTarget()==&add);
  }
 }
#ifndef MANGOSBOT_ZERO
 {
  Group group;Player bot,tank;bot.map=548;bot.group=tank.group=&group;
  Unit boss,tainted,enchanted,strider,elite;boss.guid=1;boss.entry=21212;boss.auras.insert(38112);boss.victim=&tank;
  tainted.guid=2;tainted.entry=22009;tainted.spawner=1;tainted.x=35;
  enchanted.guid=3;enchanted.entry=21958;enchanted.spawner=1;enchanted.x=5;
  strider.guid=4;strider.entry=22056;strider.spawner=1;strider.x=15;
  elite.guid=5;elite.entry=22055;elite.spawner=1;elite.x=10;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&tainted},{3,&enchanted},{4,&strider},{5,&elite}};ai.near={1,5,4,3,2};
  ai.current=&elite;DungeonAddTargetAction a{&ai,&bot};assert(a.GetSummonObjectiveTarget()==&tainted);
  tainted.cc=true;assert(a.GetSummonObjectiveTarget()==&enchanted);enchanted.alive=false;
  assert(a.GetSummonObjectiveTarget()==&strider);ai.ranged=false;assert(a.GetSummonObjectiveTarget()==&elite);
  elite.spawner=99;assert(!a.GetSummonObjectiveTarget());elite.spawner=1;
  boss.auras.clear();assert(!a.GetSummonObjectiveTarget());boss.auras.insert(38112);
  tainted.cc=false;assert(a.GetSummonObjectiveTarget()==&tainted);
 }
#endif
#ifdef MANGOSBOT_TWO
 {
  Group group;Player bot,tank;bot.map=576;bot.group=tank.group=&group;bot.instance.regular=false;
  Unit boss,add,other;boss.entry=26794;boss.guid=1;boss.victim=&tank;
  add.entry=32665;add.guid=2;add.spawner=1;add.auras.insert(61555);
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&add},{3,&other}};ai.near={1,2};DungeonAddTargetAction a{&ai,&bot};
  assert(a.GetSummonObjectiveTarget()==&add);
  bot.instance.regular=true;assert(!a.GetSummonObjectiveTarget());bot.instance.regular=false;
  add.auras.clear();assert(!a.GetSummonObjectiveTarget());add.auras.insert(61555);
  add.spawner=3;assert(!a.GetSummonObjectiveTarget());add.spawner=1;
  add.cc=true;assert(!a.GetSummonObjectiveTarget());add.cc=false;
  boss.victim=&bot;assert(!a.GetSummonObjectiveTarget());boss.victim=&tank;
  boss.combat=false;assert(!a.GetSummonObjectiveTarget());boss.combat=true;
  add.phase=2;assert(!a.GetSummonObjectiveTarget());add.phase=1;
  for(unsigned entry:{26928u,26929u,26930u}){add.entry=entry;assert(!a.GetSummonObjectiveTarget());}add.entry=32665;
  other=boss;other.guid=3;other.entry=26731;other.auras.insert(47710);ai.near.push_back(3);
  assert(!a.GetSummonObjectiveTarget()); // Ambiguous simultaneous encounters are not guessed.
  other.auras.clear();assert(a.GetSummonObjectiveTarget()==&add);
 }
#endif
 std::cout<<"PASS: fourteen objectives, Vashj wave priorities and 25 memories; ownership, phases and lifecycle\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-summon-objectives-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
dispatcher=(root/'playerbot/strategy/actions/DungeonAddTargetAction.cpp').read_text()
for gate in ('ai->IsHeal(bot)','ai->IsTank(bot)','commanded(ai->GetUnit'):
    assert dispatcher.index(gate)<dispatcher.index('GetSummonObjectiveTarget()')
print('PASS: healer/tank/manual-target dispatcher controls')
