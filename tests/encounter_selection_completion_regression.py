"""Exercise the actual native encounter selection blocks, including stale references."""
from pathlib import Path
import subprocess
import sys
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
assert mode in ('all', 'aran', 'prince', 'mount', 'static', 'beatdown')
for era in ('tbc', 'wotlk'):
    scripts = root.parent / f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts'
    def read(path):
        return (scripts / path).read_text()
    aran = block(read('eastern_kingdoms/karazhan/boss_shade_of_aran.cpp'), 'case ARAN_ACTION_PRIMARY_SPELL:')
    prince = block(read('eastern_kingdoms/karazhan/boss_prince_malchezaar.cpp'), 'void Aggro(').replace(' override', '')
    beatdown = block(read('outland/hellfire_citadel/shattered_halls/boss_warbringer_omrogg.cpp'), 'struct Beatdown') + ';'
    mount = static = ''
    if era == 'wotlk':
        mount = block(read('northrend/crusaders_coliseum/trial_of_the_champion/boss_grand_champions.cpp'), 'void MovementInform(').replace(' override', '')
        static = block(read('northrend/ulduar/ulduar/assembly_of_iron.cpp'), 'struct StaticDisruption') + ';'
    code = r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <list>
#include <map>
#include <random>
#include <stdexcept>
#include <vector>
using uint32=unsigned; using SpellEffectIndex=unsigned; using SpellCastResult=unsigned;
enum { ARAN_ACTION_PRIMARY_SPELL, ATTACKING_TARGET_RANDOM, SELECT_FLAG_PLAYER,
 NORMAL_SPELL_COUNT=3, CAST_OK=0, SAY_AGGRO=10, TYPE_MALCHEZZAR, IN_PROGRESS,
 POINT_MOTION_TYPE, POINT_ID_MOUNT, POINT_ID_EXIT, SPELL_RIDE_ARGENT_VEHICLE,
 CAST_TRIGGERED, TYPE_GRAND_CHAMPIONS, TYPE_ARENA_CHALLENGE, DONE,
 EFFECT_INDEX_0=0, SPELL_STATIC_DISRUPTION=20, SPELL_STATIC_DISRUPTION_H,
 TRIGGERED_IGNORE_CURRENT_CASTED_SPELL=1, TRIGGERED_IGNORE_GCD=2,
 TRIGGERED_HIDE_CAST_IN_COMBAT_LOG=4, TRIGGERED_IGNORE_CASTER_AURA_STATE=8,
 SPELL_FAILED_CASTER_DEAD=30, SPELL_SUPERCHARGE, SPELL_FAILED_CASTER_AURASTATE,
 SPELL_CAST_OK=0 };
unsigned randomIndex=0;
unsigned urand(unsigned lo,unsigned hi){if(hi>10000||lo>hi)throw std::logic_error("invalid random range");return std::min(randomIndex,hi);}
struct ObjectGuid {unsigned value=0;ObjectGuid()=default;ObjectGuid(unsigned v):value(v){} void Clear(){value=0;} bool IsEmpty()const{return value==0;} operator unsigned()const{return value;}};
struct Unit;
using Creature=Unit;
struct Map {bool regular=true;std::map<unsigned,Unit*> units;Unit*GetCreature(unsigned id){return units.count(id)?units.at(id):nullptr;} Unit*GetUnit(unsigned id){return GetCreature(id);}bool IsRegularDifficulty(){return regular;}};
struct Threat {unsigned resets=0;void modifyAllThreatPercent(int value){assert(value==-100);++resets;}};
struct Unit {Map*map=nullptr;unsigned id=0;float z=0;bool occupied=false;unsigned ready=7;Unit*victim=nullptr;Unit*attacked=nullptr;std::vector<unsigned> spells;std::vector<Unit*>castTargets;Threat threat;
 Map*GetMap(){return map;}float GetPositionZ(){return z;}unsigned GetObjectGuid(){return id;}
 Unit*SelectAttackingTarget(unsigned,unsigned,void*,unsigned){return victim;}
 bool IsSpellReady(unsigned spell){return ready&(1u<<(spell-100));}
 bool HasAura(unsigned){return occupied;}unsigned GetEntry(){return id;}Unit*GetVictim(){return victim;}
 Unit*AI(){return this;}void AttackStart(Unit*target){attacked=target;}void ForcedDespawn(){}
 void CastSpell(Unit*target,unsigned spell,unsigned){assert(target);spells.push_back(spell);castTargets.push_back(target);}
 unsigned GetAuraCount(unsigned){return 1;}Threat&getThreatManager(){return threat;}
};
struct ScriptedInstance {virtual ~ScriptedInstance(){}unsigned state=0;void SetData(unsigned,unsigned value){state=value;}
 unsigned GetMountEntryForChampion(){return 44;}unsigned GetData(unsigned){return state;}};
struct instance_karazhan:ScriptedInstance {std::vector<unsigned>m_vInfernalRelays;};
void DoScriptText(unsigned,Unit*){}template<class...T>void script_error_log(const char*,T...){}
Unit*replacement=nullptr;unsigned fallbackCalls=0;
Unit*GetClosestCreatureWithEntry(Unit*,unsigned,float){++fallbackCalls;return replacement;}
struct Aran {Unit*m_creature;std::vector<unsigned>m_choiceVector;unsigned cooldown=0;
 unsigned GetNormalSpellId(unsigned i){return 100+i;}unsigned DoCastSpellIfCan(Unit*,unsigned spell){m_creature->spells.push_back(spell);return CAST_OK;}
 void ResetCombatAction(unsigned,unsigned delay){cooldown=delay;}
 void run(){unsigned action=ARAN_ACTION_PRIMARY_SPELL;switch(action){__ARAN__}}};
struct Prince {Unit*m_creature;ScriptedInstance*m_instance;ObjectGuid m_uiRelayGuidClose,m_uiRelayGuidFar;bool evaded=false;
 void EnterEvadeMode(){evaded=true;}__PRINCE__};
struct Mount {Unit*m_creature;ScriptedInstance*m_pInstance;unsigned m_newMountGuid=1;bool m_bDefeated=true;unsigned mounted=0;
 unsigned DoCastSpellIfCan(Unit*target,unsigned,unsigned){assert(target);mounted=target->id;return CAST_OK;}__MOUNT__};
struct Spell {struct TargetInfo{unsigned targetGUID;};Unit*caster=nullptr;Unit*target=nullptr;std::list<TargetInfo>targets;unsigned value=0;
 Unit*GetCaster(){return caster;}Unit*GetUnitTarget(){return target;}auto&GetTargetList(){return targets;}
 void SetScriptValue(unsigned v){value=v;}unsigned GetScriptValue(){return value;}};
struct SpellScript {virtual void OnCast(Spell*)const{}virtual void OnEffectExecute(Spell*,unsigned)const{}virtual unsigned OnCheckCast(Spell*,bool)const{return 0;}};
using UnitList=std::list<Unit*>;
struct TargetDistanceOrderFarAway{Unit*caster;explicit TargetDistanceOrderFarAway(Unit*c):caster(c){}bool operator()(Unit*a,Unit*b)const{return a->z>b->z;}};
std::mt19937*GetRandomGenerator(){static std::mt19937 random(42);return &random;}
__STATIC__
__BEATDOWN__
int main(){try{
#if defined(TEST_ALL) || defined(TEST_ARAN)
 for(unsigned mask=0;mask<8;++mask)for(randomIndex=0;randomIndex<3;++randomIndex){
  Unit boss,player;boss.victim=&player;boss.ready=mask;Aran ai{&boss};ai.run();
  assert(boss.spells.size()==(mask?1:0));if(mask){assert(mask&(1u<<(boss.spells[0]-100)));assert(ai.cooldown==2000);}
 }
#endif
#if defined(TEST_ALL) || defined(TEST_PRINCE)
 {Map map;Unit boss,low,high;boss.map=&map;low.z=10;high.z=20;map.units={{1,&low},{2,&high}};
 instance_karazhan instance;Prince ai{&boss,&instance};instance.m_vInfernalRelays={99,1,2,100};ai.Aggro(nullptr);
 assert(ai.m_uiRelayGuidClose==1&&ai.m_uiRelayGuidFar==2&&!ai.evaded);
 instance.m_vInfernalRelays={2,1};ai.Aggro(nullptr);assert(ai.m_uiRelayGuidClose==1&&ai.m_uiRelayGuidFar==2);
 map.units.clear();ai.Aggro(nullptr);assert(ai.evaded);}
#endif
#if defined(HAS_WRATH) && (defined(TEST_ALL) || defined(TEST_MOUNT))
 {Map map;Unit boss,vehicle,other;boss.map=&map;vehicle.id=1;other.id=2;ScriptedInstance instance;Mount ai{&boss,&instance};
 replacement=&other;ai.MovementInform(POINT_MOTION_TYPE,POINT_ID_MOUNT);assert(ai.mounted==2&&fallbackCalls==1);
 map.units[1]=&vehicle;ai.MovementInform(POINT_MOTION_TYPE,POINT_ID_MOUNT);assert(ai.mounted==1&&fallbackCalls==1);
 vehicle.occupied=true;ai.MovementInform(POINT_MOTION_TYPE,POINT_ID_MOUNT);assert(ai.mounted==2&&fallbackCalls==2);
 map.units.clear();replacement=nullptr;ai.mounted=0;ai.MovementInform(POINT_MOTION_TYPE,POINT_ID_MOUNT);assert(!ai.mounted);}
#endif
#if defined(HAS_WRATH) && (defined(TEST_ALL) || defined(TEST_STATIC))
 {Map map;Unit boss;boss.map=&map;Spell spell;spell.caster=&boss;spell.targets={{1},{2},{3}};StaticDisruption action;
 action.OnEffectExecute(&spell,0);assert(boss.spells.empty());
 Unit near,middle,far;near.z=1;middle.z=10;far.z=20;map.units={{1,&near},{2,&middle},{3,&far}};
 for(unsigned i=0;i<30;++i)action.OnEffectExecute(&spell,0);
 for(Unit*target:boss.castTargets)assert(target==&middle||target==&far);
 assert(boss.spells.size()==30);map.regular=false;action.OnEffectExecute(&spell,0);assert(boss.spells.back()==SPELL_STATIC_DISRUPTION_H);}
#endif
#if defined(TEST_ALL) || defined(TEST_BEATDOWN)
 {Unit boss,a,b,c;a.id=1;b.id=2;c.id=3;Spell spell;spell.caster=&boss;Beatdown action;
 action.OnCast(&spell);assert(boss.threat.resets==0);spell.targets={{1},{2},{3}};
 for(randomIndex=0;randomIndex<3;++randomIndex){boss.threat.resets=0;boss.attacked=nullptr;action.OnCast(&spell);
  for(Unit*target:{&a,&b,&c}){spell.target=target;action.OnEffectExecute(&spell,0);}
  assert(boss.threat.resets==1&&boss.attacked->id==randomIndex+1);
 }}
#endif
 std::cout<<"PASS native encounter selection\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''
    for key, value in {'ARAN': aran, 'PRINCE': prince, 'MOUNT': mount, 'STATIC': static, 'BEATDOWN': beatdown}.items():
        code = code.replace('__' + key + '__', value)
    with tempfile.TemporaryDirectory(prefix='mantech-encounter-selection-') as directory:
        tmp = Path(directory)
        (tmp / 'test.cpp').write_text(code)
        flags = ['/DTEST_' + mode.upper()] + (['/DHAS_WRATH'] if era == 'wotlk' else [])
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', *flags, 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
