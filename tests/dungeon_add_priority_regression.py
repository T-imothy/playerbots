"""Execute boss-owned add selection, phase gates and manual-target arbitration."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/DungeonAddTargetAction.cpp').read_text()
multiplier=(root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods='\n'.join([block((root/'playerbot/strategy/values/InvalidTargetValue.cpp').read_text(),'bool InvalidTargetValue::Calculate('), block(source,'Unit* DungeonAddTargetAction::GetTarget('),
    block((root/'playerbot/strategy/actions/RaidTotemTargetAction.cpp').read_text(),'Unit* DungeonAddTargetAction::GetRaidTotemTarget('),
    block(source,'bool DungeonAddTargetAction::isUseful('),
    block(multiplier,'float PreserveDungeonAddTargetMultiplier::GetValue(')])
code=r'''
#include <cassert>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <type_traits>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
struct Unit {
 unsigned entry=0,map=545,instance=1,phase=1;ObjectGuid guid=0,spawner=0;
 bool world=true,alive=true,combat=true,charmed=false,friendly=false,attackable=true,freeAttack=true,player=false;
 bool IsPlayer(){return player;}
 bool immune=false,assignedCC=false,breakCC=false,hardCC=false;
 float x=0;Unit* victim=nullptr;std::set<unsigned> auras;std::set<std::pair<unsigned,ObjectGuid>> sourceAuras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetEntry(){return entry;}ObjectGuid GetSpawnerGuid(){return spawner;}ObjectGuid GetObjectGuid(){return guid;}
 bool GetSpellAuraHolder(unsigned spell,ObjectGuid caster){return sourceAuras.count({spell,caster});}
 Unit* GetVictim(){return victim;}bool HasAura(unsigned id){return auras.count(id);}
 float GetDistance(Unit*u){return std::fabs(x-u->x);}
};
struct Player;
struct GroupReference{Player*player=nullptr;GroupReference*following=nullptr;Player*getSource(){return player;}GroupReference*next(){return following;}};
struct Group{GroupReference*first=nullptr;GroupReference*GetFirstMember(){return first;}};
struct Map {bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Player:Unit {Player(){player=true;}bool teleport=false;Group*group=nullptr;ObjectGuid selection=0;ObjectGuid GetSelectionGuid(){return selection;}
 Map nativeMap;Map*GetMap(){return &nativeMap;}
 bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}unsigned GetMapId(){return map;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}};
struct PlayerbotAI {Player*bot;bool real=false,healer=false,tank=false,dungeon=true;bool HasStrategy(std::string,int){return dungeon;}
 std::list<ObjectGuid> possible;std::map<ObjectGuid,Unit*>units;ObjectGuid command=0;Unit*marked=nullptr;Unit*current=nullptr;Unit*objective=nullptr;
 bool IsRealPlayer(){return real;}bool IsHeal(Player*){return healer;}bool IsTank(Player*){return tank;}
 Unit* GetUnit(ObjectGuid id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}
 template<class T>T Value(std::string key){
  if constexpr(std::is_same_v<T,ObjectGuid>){assert(key=="attack target");return command;}
  else if constexpr(std::is_same_v<T,Unit*>){assert(key=="rti target"||key=="current target"||key=="duel target");return key=="duel target"?nullptr:key=="rti target"?marked:current;}
  else {assert(key=="possible targets"||key=="possible attack targets");return key=="possible targets"?possible:std::list<ObjectGuid>{};}}
};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue {
 static bool IsValid(Unit*u,Player*,bool ignoreLos){return u&&u->world&&u->alive&&u->attackable&&u->freeAttack&&!u->friendly;}
};
struct ServerFacade{bool IsFriendlyTo(Unit*u,Player*){return u->friendly;}}sServerFacade;
struct PossibleAttackTargetsValue {
 static bool IsValid(Unit*u,Player*){return u->victim!=nullptr;}
 static bool IsPossibleTarget(Unit*u,Player*p,float range,bool ignoreCC){assert(ignoreCC==(p->map==533||p->map==574||p->map==604||p->map==631));return !u->immune&&!u->assignedCC&&p->GetDistance(u)<=range;}
 static bool HasBreakableCC(Unit*u,Player*){return u->breakCC;}
 static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}
};
struct Action{std::string name;std::string getName(){return name;}};
struct InnerDemonAction{static Unit* GetDemon(PlayerbotAI*){return nullptr;}};
struct DungeonAddTargetAction {PlayerbotAI*ai;Player*bot;DungeonAddTargetAction(PlayerbotAI*a):ai(a),bot(a->bot){}
 Unit*GetTarget();bool isUseful();Unit*GetThekalTarget(){return nullptr;}Unit*GetGluthTarget(){return nullptr;}Unit*GetSummonObjectiveTarget(){return ai->objective;}Unit*GetRaidTotemTarget();Unit*GetTwinEmperorTarget(){return nullptr;}Unit*GetIcecrownAddTarget(){return nullptr;}};
struct PreserveDungeonAddTargetMultiplier{PlayerbotAI*ai;float GetValue(Action*);};
struct BotState{enum{BOT_STATE_COMBAT};};
struct MeleeCcCheck{MeleeCcCheck(PlayerbotAI*){}bool Protected(Unit*u){return u->assignedCC;}};
struct InvalidTargetValue{PlayerbotAI*ai;Player*bot;std::string qualifier="current target";bool Calculate();};
#define AI_VALUE(type,key) ai->Value<type>(key)
__METHODS__
int main(){
 {
  Group group;Player bot;bot.group=&group;bot.map=230;
  Unit spirit,boss;spirit.map=boss.map=230;boss.guid=1;
  PlayerbotAI ai{&bot};ai.objective=&spirit;ai.units={{1,&boss}};DungeonAddTargetAction action(&ai);
  assert(action.GetTarget()==&spirit);
  ai.healer=true;assert(!action.GetTarget());ai.healer=false;
  ai.tank=true;assert(!action.GetTarget());ai.tank=false;
  ai.command=1;assert(!action.GetTarget());ai.command=0;
  ai.marked=&boss;assert(!action.GetTarget());ai.marked=nullptr;
  bot.teleport=true;assert(!action.GetTarget());bot.teleport=false;
  bot.combat=false;assert(!action.GetTarget());bot.combat=true;
  ai.objective=nullptr;assert(!action.GetTarget());
 }

 // Passive ZF wards are selected and remain valid across the next AI tick.
 {
  Group group,other;Player bot,tank;bot.map=tank.map=209;bot.group=tank.group=&group;
  Unit doctor,ward,second;doctor.guid=1;doctor.map=209;doctor.entry=5650;doctor.victim=&tank;
  ward.guid=2;ward.map=209;ward.entry=8179;ward.spawner=1;ward.combat=false;ward.x=5;
  second=ward;second.guid=3;second.x=10;
  PlayerbotAI ai{&bot};ai.units={{1,&doctor},{2,&ward},{3,&second}};ai.possible={1,2,3};
  DungeonAddTargetAction action(&ai);PreserveDungeonAddTargetMultiplier preserve{&ai};
  Action assist{"dps assist"},heal{"heal"},tankAssist{"tank assist"};
  InvalidTargetValue invalid{&ai,&bot};
  assert(action.GetTarget()==&ward&&action.isUseful());
  ai.current=&ward;bot.selection=ward.guid;
  assert(!invalid.Calculate()&&!action.isUseful());
  assert(preserve.GetValue(&assist)==0&&preserve.GetValue(&heal)==1&&preserve.GetValue(&tankAssist)==1);
  ai.current=&second;bot.selection=second.guid;assert(action.GetTarget()==&second&&!invalid.Calculate());
  ai.current=&ward;bot.selection=ward.guid;ai.possible={1,2};
  auto rejected=[&](){assert(!action.GetTarget()&&invalid.Calculate()&&preserve.GetValue(&assist)==1);};
  ai.healer=true;rejected();ai.healer=false;ai.tank=true;rejected();ai.tank=false;
  doctor.spawner=0;doctor.victim=&bot;assert(action.GetTarget()==&ward);doctor.victim=&tank;
  doctor.victim=nullptr;rejected();doctor.victim=&tank;
  doctor.entry=8127;rejected();doctor.entry=5650;
  doctor.combat=false;rejected();doctor.combat=true;
  tank.group=&other;rejected();tank.group=&group;
  ward.spawner=99;rejected();ward.spawner=1;
  ward.map=1;rejected();ward.map=209;ward.instance=2;rejected();ward.instance=1;
  ward.x=61;rejected();ward.x=5;
  for(bool Unit::*field:{&Unit::world,&Unit::alive,&Unit::attackable,&Unit::freeAttack}){
   ward.*field=false;rejected();ward.*field=true;
  }
  for(bool Unit::*field:{&Unit::friendly,&Unit::charmed,&Unit::assignedCC,&Unit::immune}){
   ward.*field=true;rejected();ward.*field=false;
  }
  ai.command=1;rejected();ai.command=0;ai.marked=&doctor;rejected();ai.marked=nullptr;
  ai.dungeon=false;assert(invalid.Calculate());ai.dungeon=true;
  bot.selection=doctor.guid;assert(invalid.Calculate());bot.selection=ward.guid;
  bot.combat=false;rejected();bot.combat=true;
  bot.teleport=true;rejected();bot.teleport=false;
  ward.alive=false;assert(preserve.GetValue(&assist)==1);ward.alive=true;
  assert(action.GetTarget()==&ward&&!invalid.Calculate());
 }
 struct TotemCase{unsigned map,owner,entry;};
 for(TotemCase row:{TotemCase{548,21965,22091},{548,21214,22091},{568,23577,24224}}){
  Group group,other;Player bot,tank;bot.group=tank.group=&group;bot.map=tank.map=row.map;
  Unit boss,totem;boss.guid=1;boss.entry=row.owner;boss.map=row.map;boss.victim=&tank;
  totem.guid=2;totem.entry=row.entry;totem.map=row.map;totem.spawner=1;totem.combat=false;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&totem}};ai.possible={1,2};DungeonAddTargetAction action(&ai);
#ifdef MANGOSBOT_ZERO
  assert(!action.GetTarget());continue;
#endif
  assert(action.GetTarget()==&totem);totem.spawner=99;assert(!action.GetTarget());totem.spawner=1;
  boss.entry=1;assert(!action.GetTarget());boss.entry=row.owner;
  tank.group=&other;assert(!action.GetTarget());tank.group=&group;boss.victim=&bot;assert(!action.GetTarget());boss.victim=&tank;
  boss.combat=false;assert(!action.GetTarget());boss.combat=true;totem.phase=2;assert(!action.GetTarget());totem.phase=1;
  totem.assignedCC=true;assert(!action.GetTarget());totem.assignedCC=false;
  ai.healer=true;assert(!action.GetTarget());ai.healer=false;ai.tank=true;assert(!action.GetTarget());ai.tank=false;
  ai.command=1;assert(!action.GetTarget());ai.command=0;assert(action.GetTarget()==&totem);
 }
#ifdef MANGOSBOT_TWO
 for(unsigned entry:{33998u,34049u}){
  Group group;Player bot;bot.group=&group;bot.map=624;
  Unit boss,add;boss.guid=1;boss.entry=33993;boss.map=624;add.guid=2;add.entry=entry;add.map=624;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&add}};ai.possible={1,2};DungeonAddTargetAction action(&ai);
  assert(!action.GetTarget());add.sourceAuras={{64218,1}};assert(action.GetTarget()==&add);
  add.sourceAuras={{64218,99}};assert(!action.GetTarget());add.sourceAuras={{64218,1}};
  add.phase=2;assert(!action.GetTarget());add.phase=1;boss.combat=false;assert(!action.GetTarget());boss.combat=true;
  ai.command=1;assert(!action.GetTarget());ai.command=0;ai.healer=true;assert(!action.GetTarget());ai.healer=false;
  add.breakCC=true;assert(!action.GetTarget());add.breakCC=false;assert(action.GetTarget()==&add);
 }
 for(unsigned entry:{34813u,34825u}){
  Group group;Player bot;bot.group=&group;bot.map=649;
  Unit boss,add;boss.guid=1;boss.entry=34780;boss.map=649;add.guid=2;add.entry=entry;add.map=649;add.spawner=1;add.combat=false;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&add}};ai.possible={1,2};DungeonAddTargetAction action(&ai);
  assert(action.GetTarget()==&add);add.immune=true;assert(!action.GetTarget());add.immune=false;
  add.attackable=false;assert(!action.GetTarget());add.attackable=true;add.spawner=99;assert(!action.GetTarget());add.spawner=1;
  boss.combat=false;assert(!action.GetTarget());boss.combat=true;ai.tank=true;assert(!action.GetTarget());ai.tank=false;
  ai.marked=&boss;assert(!action.GetTarget());ai.marked=nullptr;assert(action.GetTarget()==&add);
 }
#endif
 {
  Group group;Player bot,member;bot.group=member.group=&group;bot.map=member.map=309;
  GroupReference memberRef{&member};group.first=&memberRef;
  Unit boss,son;boss.guid=1;boss.entry=14834;boss.map=309;son.guid=2;son.entry=11357;son.map=309;son.victim=&member;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&son}};ai.possible={1,2};DungeonAddTargetAction action(&ai);
  assert(action.GetTarget()==&son);son.victim=nullptr;assert(!action.GetTarget());son.victim=&member;
  son.combat=false;assert(!action.GetTarget());son.combat=true;
  bot.auras.insert(24321);assert(action.GetTarget()==&son);member.auras.insert(24321);assert(!action.GetTarget());member.auras.clear();
  member.group=nullptr;assert(!action.GetTarget());member.group=&group;
  son.breakCC=true;assert(!action.GetTarget());son.breakCC=false;
  ai.command=1;assert(!action.GetTarget());ai.command=0;
  boss.combat=false;assert(!action.GetTarget());boss.combat=true;
 }
 // Rescue objects are summoned by the trapped group member.
 struct Rescue{unsigned map,boss,add,aura;bool regular;};
 for(Rescue rescue: {Rescue{533,15952,16486,28622,true}
#ifdef MANGOSBOT_TWO
  ,Rescue{574,23953,23965,48400,true},Rescue{574,23953,23965,48400,false},
  Rescue{604,29304,29742,55126,true},Rescue{604,29304,29742,61476,false},
  Rescue{631,36612,36619,69065,true},Rescue{631,36612,38711,69065,true},Rescue{631,36612,38712,69065,true},
  Rescue{631,36612,36619,69065,false},Rescue{631,36612,38711,69065,false},Rescue{631,36612,38712,69065,false}
#endif
 }) {
  Group group,otherGroup;Player bot,member;bot.group=member.group=&group;bot.map=member.map=rescue.map;bot.nativeMap.regular=rescue.regular;
  member.guid=3;member.auras={rescue.aura};
  Unit boss,wrap,otherBoss;boss.guid=1;boss.entry=rescue.boss;boss.map=rescue.map;
  wrap.guid=2;wrap.entry=rescue.add;wrap.map=rescue.map;wrap.spawner=3;wrap.hardCC=true;wrap.combat=false;
  otherBoss=boss;otherBoss.guid=4;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&wrap},{3,&member},{4,&otherBoss}};ai.possible={1,2};
  DungeonAddTargetAction action(&ai);auto none=[&](){assert(!action.GetTarget());};
  assert(action.GetTarget()==&wrap);ai.current=&wrap;assert(!action.isUseful());ai.current=nullptr;
  member.auras.clear();none();member.auras={rescue.aura};member.group=&otherGroup;none();member.group=&group;
  member.alive=false;none();member.alive=true;member.world=false;none();member.world=true;
  member.charmed=true;none();member.charmed=false;member.teleport=true;none();member.teleport=false;
  member.instance=2;none();member.instance=1;member.phase=2;none();member.phase=1;
  member.player=false;none();member.player=true;wrap.spawner=1;none();wrap.spawner=3;
  wrap.breakCC=true;none();wrap.breakCC=false;wrap.assignedCC=true;none();wrap.assignedCC=false;
  wrap.immune=true;none();wrap.immune=false;wrap.alive=false;none();wrap.alive=true;
  wrap.world=false;none();wrap.world=true;wrap.phase=2;none();wrap.phase=1;
  wrap.charmed=true;none();wrap.charmed=false;wrap.friendly=true;none();wrap.friendly=false;
  boss.victim=&bot;none();boss.victim=nullptr;boss.combat=false;none();boss.combat=true;
  boss.phase=2;none();boss.phase=1;boss.alive=false;none();boss.alive=true;
  ai.possible.push_back(4);none();ai.possible.remove(4);
  ai.command=1;none();ai.command=0;ai.marked=&boss;none();ai.marked=nullptr;
  ai.healer=true;none();ai.healer=false;ai.tank=true;none();ai.tank=false;ai.real=true;none();ai.real=false;
  bot.group=nullptr;none();bot.group=&group;bot.teleport=true;none();bot.teleport=false;
  bot.alive=false;none();bot.alive=true;bot.combat=false;none();bot.combat=true;
  assert(action.GetTarget()==&wrap);ai.units.erase(3);none();
 }
 struct Case{unsigned map,boss,add,aura;};
 for(Case c: {Case{545,17796,17951,0},Case{553,17975,19953,34551},Case{556,23035,23132,42354},Case{576,26763,26918,47748}}){
  Player bot;Group group;bot.group=&group;bot.map=c.map;
  Unit boss,add,second,otherBoss;boss.guid=1;boss.entry=c.boss;boss.map=c.map;
  if(c.aura)boss.auras={c.aura};
  add.guid=2;add.entry=c.add;add.map=c.map;add.spawner=1;add.x=5;add.combat=false;
  second=add;second.guid=3;second.x=15;otherBoss=boss;otherBoss.guid=4;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&add},{3,&second},{4,&otherBoss}};ai.possible={2,3};
  DungeonAddTargetAction action(&ai);PreserveDungeonAddTargetMultiplier multiplier{&ai};
  Action assist{"dps assist"},tankAssist{"tank assist"},heal{"heal"};
#ifdef MANGOSBOT_ZERO
  assert(!action.GetTarget()&&!action.isUseful()&&multiplier.GetValue(&assist)==1);
#else
#ifndef MANGOSBOT_TWO
  if(c.map==576){assert(!action.GetTarget()&&!action.isUseful());continue;}
#endif
  assert(action.GetTarget()==&add&&action.isUseful()); // Passive summon still qualifies.
  assert(multiplier.GetValue(&assist)==0&&multiplier.GetValue(&tankAssist)==1&&multiplier.GetValue(&heal)==1);
  assert(multiplier.GetValue(nullptr)==1);
  ai.current=&second;assert(action.GetTarget()==&second&&!action.isUseful());ai.current=nullptr;
  second.spawner=4;assert(!action.GetTarget());second.spawner=1;
  ai.possible={2};
  auto none=[&](){assert(!action.GetTarget()&&!action.isUseful()&&multiplier.GetValue(&assist)==1);};
  ai.command=1;boss.immune=true;none();ai.command=0;ai.marked=&boss;none();
  // Explicit shielded-boss commands survive immunity. Stale commands do not.
  boss.world=false;none();boss.world=true;ai.marked=nullptr;boss.immune=false;
  ai.command=99;assert(action.GetTarget()==&add);ai.command=0;
  ai.marked=&otherBoss;otherBoss.instance=2;assert(action.GetTarget()==&add);otherBoss.instance=1;ai.marked=nullptr;
  for(bool Unit::*field:{&Unit::world,&Unit::alive,&Unit::attackable,&Unit::freeAttack}){
   add.*field=false;none();add.*field=true;
  }
  for(bool Unit::*field:{&Unit::charmed,&Unit::friendly,&Unit::immune,&Unit::assignedCC,&Unit::breakCC,&Unit::hardCC}){
   add.*field=true;none();add.*field=false;
  }
  add.map=0;none();add.map=c.map;add.instance=2;none();add.instance=1;add.phase=2;none();add.phase=1;
  add.spawner=99;none();add.spawner=1;add.entry=999;none();add.entry=c.add;
  add.x=61;none();add.x=5;
  boss.world=false;none();boss.world=true;boss.alive=false;none();boss.alive=true;
  boss.combat=false;none();boss.combat=true;boss.charmed=true;none();boss.charmed=false;
  boss.map=0;none();boss.map=c.map;boss.instance=2;none();boss.instance=1;boss.phase=2;none();boss.phase=1;
  boss.entry=999;none();boss.entry=c.boss;boss.victim=&bot;none();boss.victim=nullptr;
  if(c.aura){boss.auras.clear();none();boss.auras={c.aura};}
  ai.real=true;none();ai.real=false;ai.healer=true;none();ai.healer=false;ai.tank=true;none();ai.tank=false;
  bot.group=nullptr;none();bot.group=&group;bot.teleport=true;none();bot.teleport=false;
  bot.charmed=true;none();bot.charmed=false;bot.alive=false;none();bot.alive=true;
  bot.combat=false;none();bot.combat=true;bot.world=false;none();bot.world=true;
  bot.map=0;none();bot.map=c.map;
  assert(action.GetTarget()==&add);ai.units.erase(2);none(); // Despawn before Execute reselects.
#endif
 }
 // Vorpil travelers belong to his passive summoner, not directly to the boss.
 for(bool ritual:{false,true}) {
#ifndef MANGOSBOT_TWO
  if(ritual)continue;
#endif
  Group group,other;Player bot,member;GroupReference ref{&member};group.first=&ref;bot.group=member.group=&group;
  bot.map=member.map=ritual?575:509;Unit boss,add;boss.map=add.map=bot.map;
  boss.guid=1;boss.entry=ritual?26668:15369;add.guid=2;add.entry=ritual?27281:15555;add.spawner=1;add.victim=&member;
  unsigned aura=ritual?48278:25725;unsigned caster=ritual?2:1;member.sourceAuras={{aura,caster}};
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&add}};ai.possible={2};DungeonAddTargetAction action(&ai);
  assert(action.GetTarget()==&add);auto none=[&](){assert(!action.GetTarget());};
  member.sourceAuras={{aura,99}};none();member.sourceAuras={{aura,caster}};
  member.group=&other;none();member.group=&group;member.alive=false;none();member.alive=true;
  member.world=false;none();member.world=true;member.phase=2;none();member.phase=1;
  member.teleport=true;none();member.teleport=false;member.charmed=true;none();member.charmed=false;
  add.spawner=99;none();add.spawner=1;boss.combat=false;none();boss.combat=true;
  ai.command=1;none();ai.command=0;ai.healer=true;none();ai.healer=false;
  if(!ritual){add.victim=nullptr;none();add.victim=&member;}
  assert(action.GetTarget()==&add);
 }
 {
  Player bot;Group group;bot.group=&group;bot.map=555;
  Unit boss,summoner,add;boss.guid=1;boss.entry=18732;boss.map=555;
  summoner.guid=2;summoner.entry=19427;summoner.map=555;summoner.spawner=1;summoner.combat=false;
  add.guid=3;add.entry=19226;add.map=555;add.spawner=2;add.x=5;add.combat=false;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&summoner},{3,&add}};ai.possible={3};
  DungeonAddTargetAction action(&ai);
#ifdef MANGOSBOT_ZERO
  assert(!action.GetTarget());
#else
  assert(action.GetTarget()==&add);
  auto none=[&](){assert(!action.GetTarget());};
  summoner.world=false;none();summoner.world=true;summoner.alive=false;none();summoner.alive=true;
  summoner.charmed=true;none();summoner.charmed=false;
  summoner.map=0;none();summoner.map=555;summoner.instance=2;none();summoner.instance=1;
  summoner.phase=2;none();summoner.phase=1;summoner.entry=999;none();summoner.entry=19427;
  summoner.spawner=0;none();summoner.spawner=2;none();summoner.spawner=3;none();summoner.spawner=1;
  add.spawner=1;none();add.spawner=2; // A lookalike summoned directly is not this native chain.
  boss.combat=false;none();boss.combat=true;boss.alive=false;none();boss.alive=true;
  boss.instance=2;none();boss.instance=1;boss.phase=2;none();boss.phase=1;
  boss.entry=999;none();boss.entry=18732;boss.victim=&bot;none();boss.victim=nullptr;
  ai.command=1;none();ai.command=0;ai.marked=&boss;none();ai.marked=nullptr;
  ai.healer=true;none();ai.healer=false;ai.tank=true;none();ai.tank=false;
  add.breakCC=true;none();add.breakCC=false;add.immune=true;none();add.immune=false;
  ai.current=&add;assert(!action.isUseful());assert(action.GetTarget()==&add);
  ai.units.erase(2);none(); // Missing native summoner cannot fall back to a nearby boss.
#endif
 }
 // Static crystals and Nadox's guardian must be the actual source of the boss aura.
 for(auto c:{std::vector<unsigned>{545,17798,17954,31543},std::vector<unsigned>{585,24723,24722,44320},std::vector<unsigned>{619,29309,30176,56153}}){
  Player bot;Group group;bot.group=&group;bot.map=c[0];
  Unit boss,add,inactive,otherBoss;boss.guid=1;boss.entry=c[1];boss.map=c[0];
  add.guid=2;add.entry=c[2];add.map=c[0];add.x=10;add.combat=false;
  inactive=add;inactive.guid=3;inactive.x=2;otherBoss=boss;otherBoss.guid=4;
  PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&add},{3,&inactive},{4,&otherBoss}};ai.possible={1,2,3,4};
  DungeonAddTargetAction action(&ai);PreserveDungeonAddTargetMultiplier multiplier{&ai};Action assist{"dps assist"};
  boss.sourceAuras={{c[3],2}};
#ifdef MANGOSBOT_ZERO
  assert(!action.GetTarget());
#else
#ifndef MANGOSBOT_TWO
  if(c[0]==619){assert(!action.GetTarget());continue;}
#endif
  assert(action.GetTarget()==&add); // Closer inactive lookalike is ignored.
  auto none=[&](){assert(!action.GetTarget()&&multiplier.GetValue(&assist)==1);};
  if(c[0]==545){
   Unit repairBoss,repair;repairBoss.entry=17796;repairBoss.guid=5;repairBoss.map=545;
   repair.entry=17951;repair.guid=6;repair.map=545;repair.spawner=5;
   ai.units[5]=&repairBoss;ai.units[6]=&repair;ai.possible.push_back(6);
   none(); // Two engaged encounters in the same map remain ambiguous.
   ai.possible.remove(6);ai.units.erase(5);ai.units.erase(6);
  }
  boss.sourceAuras.clear();none();boss.sourceAuras={{c[3],99}};none();boss.sourceAuras={{999,2}};none();boss.sourceAuras={{c[3],2}};
  ai.current=&inactive;assert(action.GetTarget()==&add&&action.isUseful());ai.current=&add;assert(!action.isUseful());ai.current=nullptr;
  otherBoss.sourceAuras={{c[3],2}};none();otherBoss.sourceAuras.clear();
  boss.world=false;none();boss.world=true;boss.alive=false;none();boss.alive=true;
  boss.combat=false;none();boss.combat=true;boss.charmed=true;none();boss.charmed=false;
  boss.instance=2;none();boss.instance=1;boss.phase=2;none();boss.phase=1;
  boss.entry=999;none();boss.entry=c[1];boss.victim=&bot;none();boss.victim=nullptr;
  add.alive=false;none();add.alive=true;add.instance=2;none();add.instance=1;add.phase=2;none();add.phase=1;
  add.breakCC=true;none();add.breakCC=false;add.immune=true;none();add.immune=false;add.charmed=true;none();add.charmed=false;
  ai.command=1;boss.immune=true;none();ai.command=0;ai.marked=&boss;none();ai.marked=nullptr;boss.immune=false;
  ai.healer=true;none();ai.healer=false;ai.tank=true;none();ai.tank=false;ai.real=true;none();ai.real=false;
  bot.combat=false;none();bot.combat=true;assert(action.GetTarget()==&add);
  ai.units.erase(2);none();
#endif
 }
 std::cout<<"PASS: native-owned dungeon add priorities, phase/reset, manual/CC, role and era guards\n";
}
'''.replace('__METHODS__',methods)
for era,realm in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk')):
    if realm!='classic':
        scripts=root.parent/f'mangos-{realm}-behavior/src/game/AI/ScriptDevAI/scripts'
        expected={
            'boss_high_botanist_freywinn.cpp':['19953','34551','SummonedCreatureJustDied','InterruptTreeForm()'],
            'boss_mekgineer_steamrigger.cpp':['17951','31532','37936','MoveFollow(m_creature'],
            'boss_anzu.cpp':['42354','SummonedCreatureJustDied','SummonCreature(NPC_BROOD_OF_ANZU'],
            'sethekk_halls.h':['23132','23035'],
            'boss_grandmaster_vorpil.cpp':['19226','19427','33927','m_creature->GetSpawner()',
                'SPELL_EMPOWERING_SHADOWS_H      = 39364','MoveChase(vorpil','aTravelerSummonSpells[urand(0, 4)]'],
            'boss_selin_fireheart.cpp':['44320','44321','target->CastSpell(nullptr, SPELL_MANA_RAGE_CHANNEL','spell_mana_rage_selin'],
            'boss_warlord_kalithresh.cpp':['31543','37076','distiller->CastSpell(nullptr, SPELL_WARLORDS_RAGE_NAGA'],
            'magisters_terrace.h':['24723','24722'],
            'steam_vault.h':['17798','17954'],
            'shadow_labyrinth.h':['18732']}
        if realm=='wotlk':
            expected['boss_svala.cpp']=['27281','48278','pSummoned->CastSpell(pSummoned, SPELL_PARALIZE',
                'DoCastSpellIfCan(m_creature, SPELL_SUMMON_CHANNELER_1']
            expected['boss_lord_marrowgar.cpp']=['36619','38711','38712','69065','target->CastSpell(target, 69062',
                'playerTarget = m_creature->GetSpawner()', 'playerTarget->RemoveAurasDueToSpell(SPELL_IMPALED)']
            expected['boss_anomalus.cpp']=['26918','47748','SummonedCreatureJustDied','RemoveAurasDueToSpell(SPELL_RIFT_SHIELD)']
            expected['boss_nadox.cpp']=['30176','56151','pSummoned->CastSpell(pSummoned, SPELL_GUARDIAN_AURA']
            expected['ahnkahet.h']=['29309','30173']
        for name,contracts in expected.items():
            matches=list(scripts.rglob(name));assert len(matches)==1,(realm,name)
            native=matches[0].read_text()
            for contract in contracts:assert contract in native,(realm,name,contract)
        native=(root.parent/f'mangos-{realm}-behavior/src/game/Entities/TemporarySpawn.h').read_text()
        assert 'GetSpawnerGuid() const override { return m_spawner' in native
    with tempfile.TemporaryDirectory(prefix='mantech-dungeon-add-priority-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
assert 'dungeon priority add' in block(strategy,'void DungeonStrategy::InitCombatTriggers(')
assert 'PreserveDungeonAddTargetMultiplier' in block(strategy,'void DungeonStrategy::InitCombatMultipliers(')
assert 'Unit* target = GetTarget();' in block((root/'playerbot/strategy/actions/AttackAction.cpp').read_text(),'bool AttackAction::Execute(')
assert 'new DungeonAddTargetAction(ai)' in (root/'playerbot/strategy/actions/ActionContext.h').read_text()
assert 'new DungeonAddTargetTrigger(ai)' in (root/'playerbot/strategy/triggers/TriggerContext.h').read_text()
