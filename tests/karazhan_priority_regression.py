"""Actual boss-owned Karazhan target selection and arbitration, with native contracts."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/KarazhanDungeonActions.cpp').read_text()
multiplier=(root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods='\n'.join([block(source,'Unit* KarazhanPriorityTargetAction::GetTarget('),
                   block(source,'bool KarazhanPriorityTargetAction::isUseful('),
                   block(multiplier,'float PreserveKarazhanTargetMultiplier::GetValue(')])
attack=(root/'playerbot/strategy/actions/AttackAction.cpp').read_text()
assert 'Unit* target = GetTarget();' in block(attack,'bool AttackAction::Execute(')
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <type_traits>
using uint32=unsigned;using ObjectGuid=unsigned;
struct Aura{ObjectGuid caster=0;ObjectGuid GetCasterGuid()const{return caster;}};
struct Unit {virtual ~Unit()=default;unsigned entry=0,map=1,phase=1;ObjectGuid guid=0,spawner=0;
 bool world=true,alive=true,combat=true,charmed=false,attackable=true,freeAttack=true,assignedCC=false,breakCC=false,hardCC=false;
 float x=0;Unit* victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}ObjectGuid GetSpawnerGuid(){return spawner;}
 Unit* GetVictim(){return victim;}float GetDistance(Unit* unit){return std::fabs(x-unit->x);}
};
struct Group;
struct Player:Unit{bool teleport=false;Group* group=nullptr;unsigned mapId=532;
 bool IsBeingTeleported(){return teleport;}Group* GetGroup(){return group;}unsigned GetMapId(){return mapId;}
 bool IsInMap(Unit* unit){return unit&&map==unit->map&&phase==unit->phase;}};
struct GroupReference{Player* source=nullptr;GroupReference* following=nullptr;Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct PlayerbotAI{Player* bot;bool healer=false,tank=false;std::list<ObjectGuid> attackers,possible;std::map<ObjectGuid,Unit*> units;
 std::map<Player*,Aura> auras;ObjectGuid commanded=0;Unit* current=nullptr;Unit* marked=nullptr;
 bool IsHeal(Player*){return healer;}bool IsTank(Player*){return tank;}
 Unit* GetUnit(ObjectGuid id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}
 const Aura* GetAura(unsigned id,Player* p){assert(id==30115);auto i=auras.find(p);return i==auras.end()?nullptr:&i->second;}
 template<class T>T Value(std::string key){
  if constexpr(std::is_same_v<T,ObjectGuid>)return commanded;
  else if constexpr(std::is_same_v<T,Unit*>)return key=="rti target"?marked:current;
  else return key=="attackers"?attackers:possible;}
};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue{static bool IsValid(Unit* u,Player*,bool ignoreLos){assert(!ignoreLos);return u->attackable&&u->freeAttack;}};
struct PossibleAttackTargetsValue{
 static bool IsPossibleTarget(Unit* u,Player* p,float range,bool ignoreCC){assert(!ignoreCC);return !u->assignedCC&&p->GetDistance(u)<=range;}
 static bool HasBreakableCC(Unit* u,Player*){return u->breakCC;}static bool HasUnBreakableCC(Unit* u,Player*){return u->hardCC;}
};
struct Action{std::string name;std::string getName(){return name;}};
struct KarazhanPriorityTargetAction{PlayerbotAI* ai;Player* bot;KarazhanPriorityTargetAction(PlayerbotAI* a):ai(a),bot(a->bot){}
 Unit* GetTarget();bool isUseful();};
struct PreserveKarazhanTargetMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
#define AI_VALUE(type,key) ai->Value<type>(key)
__METHODS__
int main(){
 Player bot,ally;Group group,otherGroup;GroupReference ref{&ally};group.first=&ref;bot.group=ally.group=&group;
 Unit boss,chains,second,otherBoss;boss.entry=15688;boss.guid=1;chains.entry=second.entry=17248;
 chains.guid=2;second.guid=3;chains.spawner=second.spawner=1;chains.x=1;second.x=20;
 chains.combat=second.combat=false;otherBoss.entry=15691;otherBoss.guid=4;
 PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&chains},{3,&second},{4,&otherBoss}};ai.attackers={1};ai.possible={2,3};
 ai.auras[&ally]={1};KarazhanPriorityTargetAction action(&ai);PreserveKarazhanTargetMultiplier multiplier{&ai};
 Action assist{"dps assist"},tankAssist{"tank assist"},cast{"fireball"};
#ifdef MANGOSBOT_ZERO
 assert(!action.GetTarget()&&!action.isUseful()&&multiplier.GetValue(&assist)==1);
#else
 assert(action.GetTarget()==&chains&&action.isUseful()); // Passive chains do not need a threat victim.
 assert(multiplier.GetValue(&assist)==0&&multiplier.GetValue(&tankAssist)==1&&multiplier.GetValue(&cast)==1);
 ai.current=&chains;chains.x=25;assert(action.GetTarget()==&chains&&!action.isUseful());chains.x=1;
 ai.commanded=1;assert(!action.GetTarget()&&multiplier.GetValue(&assist)==1);ai.commanded=0;
 ai.marked=&second;assert(!action.GetTarget());ai.marked=nullptr;
 ai.possible={2};
 auto none=[&](){assert(!action.GetTarget()&&!action.isUseful()&&multiplier.GetValue(&assist)==1);};
 chains.world=false;none();chains.world=true;chains.alive=false;none();chains.alive=true;
 chains.spawner=99;none();chains.spawner=1;chains.entry=17267;none();chains.entry=17248;
 chains.map=2;none();chains.map=1;chains.phase=2;none();chains.phase=1;
 chains.attackable=false;none();chains.attackable=true;chains.freeAttack=false;none();chains.freeAttack=true;
 chains.assignedCC=true;none();chains.assignedCC=false;chains.breakCC=true;none();chains.breakCC=false;chains.hardCC=true;none();chains.hardCC=false;
 chains.x=61;none();chains.x=1;boss.victim=&bot;none();boss.victim=nullptr;
 boss.alive=false;none();boss.alive=true;boss.combat=false;none();boss.combat=true;
 boss.map=2;none();boss.map=1;boss.charmed=true;none();boss.charmed=false;
 ai.attackers={1,4};none();ai.attackers={1};ai.auras[&ally].caster=99;none();ai.auras[&ally].caster=1;
 ally.group=&otherGroup;none();ally.group=&group;ally.alive=false;none();ally.alive=true;
 ally.map=2;none();ally.map=1;ally.teleport=true;none();ally.teleport=false;ally.charmed=true;none();ally.charmed=false;
 ai.auras.clear();none();ai.auras[&ally]={1};
 ai.healer=true;none();ai.healer=false;ai.tank=true;none();ai.tank=false;
 bot.mapId=0;none();bot.mapId=532;bot.teleport=true;none();bot.teleport=false;bot.charmed=true;none();bot.charmed=false;
 bot.group=nullptr;none();bot.group=&group;bot.combat=false;none();bot.combat=true;
 ai.current=nullptr;boss.entry=15691;ai.auras.clear();
 for(unsigned flare:{17096,19781,19782,19783}){chains.entry=flare;assert(action.GetTarget()==&chains);}
 chains.entry=17248;none();chains.entry=17096;assert(action.GetTarget()==&chains);
 ai.units.erase(2);none(); // Despawn between feasibility and execution is safe.
#endif
 std::cout<<"PASS: actual Karazhan passive chains/flare selection, ownership, lifecycle, manual/CC and tank/healer policy\n";
}
'''.replace('__METHODS__',methods)
for era,realm in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk')):
    if realm!='classic':
        scripts=root.parent/f'mangos-{realm}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/karazhan'
        illhoof=(scripts/'boss_terestian_illhoof.cpp').read_text();curator=(scripts/'boss_curator.cpp').read_text()
        for native in ('NPC_DEMONCHAINS             = 17248','SetReactState(REACT_PASSIVE)',
                       'RemoveAurasDueToSpell(SPELL_SACRIFICE)'):
            assert native in illhoof,(realm,native)
        for entry in (17096,19781,19782,19783):assert str(entry) in curator
        native=(root.parent/f'mangos-{realm}-behavior/src/game/Entities/TemporarySpawn.h').read_text()
        assert 'GetSpawnerGuid() const override { return m_spawner' in native
    with tempfile.TemporaryDirectory(prefix='mantech-karazhan-priority-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/KarazhanDungeonStrategies.cpp').read_text()
assert 'karazhan priority target' in block(strategy,'void KarazhanDungeonStrategy::InitCombatTriggers(')
assert 'PreserveKarazhanTargetMultiplier' in block(strategy,'void KarazhanDungeonStrategy::InitCombatMultipliers(')
