"""Execute boss-owned add selection, phase gates and manual-target arbitration."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/DungeonAddTargetAction.cpp').read_text()
multiplier=(root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods='\n'.join([block(source,'Unit* DungeonAddTargetAction::GetTarget('),
    block(source,'bool DungeonAddTargetAction::isUseful('),
    block(multiplier,'float PreserveDungeonAddTargetMultiplier::GetValue(')])
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <type_traits>
using uint32=unsigned;using ObjectGuid=unsigned;
struct Unit {
 unsigned entry=0,map=545,instance=1,phase=1;ObjectGuid guid=0,spawner=0;
 bool world=true,alive=true,combat=true,charmed=false,friendly=false,attackable=true,freeAttack=true;
 bool immune=false,assignedCC=false,breakCC=false,hardCC=false;
 float x=0;Unit* victim=nullptr;std::set<unsigned> auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetEntry(){return entry;}ObjectGuid GetSpawnerGuid(){return spawner;}
 Unit* GetVictim(){return victim;}bool HasAura(unsigned id){return auras.count(id);}
 float GetDistance(Unit*u){return std::fabs(x-u->x);}
};
struct Group{};
struct Player:Unit {bool teleport=false;Group*group=nullptr;
 bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}unsigned GetMapId(){return map;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}};
struct PlayerbotAI {Player*bot;bool real=false,healer=false,tank=false;
 std::list<ObjectGuid> possible;std::map<ObjectGuid,Unit*>units;ObjectGuid command=0;Unit*marked=nullptr;Unit*current=nullptr;
 bool IsRealPlayer(){return real;}bool IsHeal(Player*){return healer;}bool IsTank(Player*){return tank;}
 Unit* GetUnit(ObjectGuid id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}
 template<class T>T Value(std::string key){
  if constexpr(std::is_same_v<T,ObjectGuid>){assert(key=="attack target");return command;}
  else if constexpr(std::is_same_v<T,Unit*>){assert(key=="rti target"||key=="current target");return key=="rti target"?marked:current;}
  else {assert(key=="possible targets");return possible;}}
};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue {
 static bool IsValid(Unit*u,Player*,bool ignoreLos){assert(!ignoreLos);return u->attackable&&u->freeAttack&&!u->friendly;}
};
struct ServerFacade{bool IsFriendlyTo(Unit*u,Player*){return u->friendly;}}sServerFacade;
struct PossibleAttackTargetsValue {
 static bool IsPossibleTarget(Unit*u,Player*p,float range,bool ignoreCC){assert(!ignoreCC);return !u->immune&&!u->assignedCC&&p->GetDistance(u)<=range;}
 static bool HasBreakableCC(Unit*u,Player*){return u->breakCC;}
 static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}
};
struct Action{std::string name;std::string getName(){return name;}};
struct DungeonAddTargetAction {PlayerbotAI*ai;Player*bot;DungeonAddTargetAction(PlayerbotAI*a):ai(a),bot(a->bot){}
 Unit*GetTarget();bool isUseful();};
struct PreserveDungeonAddTargetMultiplier{PlayerbotAI*ai;float GetValue(Action*);};
#define AI_VALUE(type,key) ai->Value<type>(key)
__METHODS__
int main(){
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
            'shadow_labyrinth.h':['18732']}
        if realm=='wotlk':expected['boss_anomalus.cpp']=['26918','47748','SummonedCreatureJustDied','RemoveAurasDueToSpell(SPELL_RIFT_SHIELD)']
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
