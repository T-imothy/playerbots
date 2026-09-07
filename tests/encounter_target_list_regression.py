"""Execute native boss selection with exhausted lists and despawned references."""
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
mode=sys.argv[1] if len(sys.argv)>1 else 'all'
assert mode in ('all','renataki','face','thorim')
for era in ('classic','tbc','wotlk'):
    scripts=root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts'
    renataki=block((scripts/'eastern_kingdoms/zulgurub/boss_renataki.cpp').read_text(),'struct ThousandBladesRenataki')+';'
    face=block((scripts/'outland/hellfire_citadel/hellfire_ramparts/boss_nazan_and_vazruden.cpp').read_text(),'struct FaceHighestThreat')+';' if era!='classic' else ''
    thorim=block((scripts/'northrend/ulduar/ulduar/boss_thorim.cpp').read_text(),'Creature* GetClosestLowerBunny(') if era=='wotlk' else ''
    code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <random>
#include <set>
#include <stdexcept>
#include <vector>
using uint32=unsigned;using SpellEffectIndex=unsigned;using GuidList=std::list<unsigned>;
enum{SPELL_THOUSAND_BLADES=24649,EFFECT_INDEX_1=1,ATTACKING_TARGET_ALL_SUITABLE=2,
 SELECT_FLAG_PLAYER=4,TRIGGERED_OLD_TRIGGERED=8,TRIGGERED_INSTANT_CAST=16};
template<class T>struct CheckedList:std::list<T>{T&front(){if(this->empty())throw std::logic_error("front() on an empty native target list");return std::list<T>::front();}
 const T&front()const{if(this->empty())throw std::logic_error("front() on an empty native target list");return std::list<T>::front();}};
struct Unit;
struct HostileReference{Unit*target=nullptr;Unit*getTarget(){return target;}};
using ThreatList=CheckedList<HostileReference*>;
struct ThreatManager{ThreatList refs;ThreatList&getThreatList(){return refs;}};
std::mt19937*GetRandomGenerator(){static std::mt19937 generator(42);return &generator;}
struct Unit{std::vector<Unit*> candidates,casts;ThreatManager threat;float angle=0;unsigned facings=0;
 void SelectAttackingTargets(std::vector<Unit*>&out,unsigned,unsigned offset,unsigned spell,unsigned flags){
  assert(offset==0&&spell==SPELL_THOUSAND_BLADES&&flags==SELECT_FLAG_PLAYER);out=candidates;}
 void CastSpell(Unit*target,unsigned spell,unsigned flags){assert(spell==SPELL_THOUSAND_BLADES&&flags==(TRIGGERED_OLD_TRIGGERED|TRIGGERED_INSTANT_CAST));casts.push_back(target);}
 ThreatManager&getThreatManager(){return threat;}
 float GetAngle(Unit*target){if(!target)throw std::logic_error("angle to missing threat target");return 1.25f;}
 void SetFacingTo(float value){angle=value;++facings;}
};
struct SpellTargets{Unit*primary=nullptr;Unit*getUnitTarget(){return primary;}};
struct Spell{bool m_IsTriggeredSpell=false;Unit*caster=nullptr;SpellTargets m_targets;Unit*GetCaster(){return caster;}};
struct SpellScript{virtual void OnEffectExecute(Spell*,SpellEffectIndex) const{}};
__RENATAKI__
__FACE__
struct Creature;
struct Map{std::map<unsigned,Creature*> creatures;Creature*GetCreature(unsigned id){auto i=creatures.find(id);return i==creatures.end()?nullptr:i->second;}};
struct Creature:Unit{Map*map=nullptr;float x=0;Map*GetMap(){return map;}};
using CreatureList=CheckedList<Creature*>;
struct ObjectDistanceOrder{Creature*source;explicit ObjectDistanceOrder(Creature*c):source(c){}
 bool operator()(Creature*a,Creature*b)const{return std::fabs(a->x-source->x)<std::fabs(b->x-source->x);}};
struct Thorim{Creature*m_creature;GuidList m_lLowerBunniesGuids;__THORIM__};
int main(){try{
#if !defined(FACE_ONLY) && !defined(THORIM_ONLY)
 for(unsigned count=0;count<=15;++count){
  Unit boss,primary;std::vector<Unit> players(count);boss.candidates.push_back(&primary);
  for(auto&player:players)boss.candidates.push_back(&player);
  Spell spell;spell.caster=&boss;spell.m_targets.primary=&primary;
  ThousandBladesRenataki action;action.OnEffectExecute(&spell,EFFECT_INDEX_1);
  assert(boss.casts.size()==std::min(count,9u));std::set<Unit*>unique;
  for(Unit*target:boss.casts){assert(target&&target!=&primary);unique.insert(target);}assert(unique.size()==boss.casts.size());
  boss.casts.clear();spell.m_IsTriggeredSpell=true;action.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(boss.casts.empty());
  spell.m_IsTriggeredSpell=false;action.OnEffectExecute(&spell,0);assert(boss.casts.empty());
 }
#endif
#if defined(HAS_FACE) && !defined(RENATAKI_ONLY) && !defined(THORIM_ONLY)
 {
  Unit boss,target;Spell spell;spell.caster=&boss;FaceHighestThreat action;
  action.OnEffectExecute(&spell,0);assert(boss.facings==0);
  boss.threat.refs.push_back(nullptr);action.OnEffectExecute(&spell,0);assert(boss.facings==0);
  HostileReference ref;boss.threat.refs.clear();boss.threat.refs.push_back(&ref);
  action.OnEffectExecute(&spell,0);assert(boss.facings==0);
  ref.target=&target;action.OnEffectExecute(&spell,0);assert(boss.facings==1&&boss.angle==1.25f);
  spell.caster=nullptr;action.OnEffectExecute(&spell,0);
 }
#endif
#if defined(HAS_THORIM) && !defined(RENATAKI_ONLY) && !defined(FACE_ONLY)
 {
  Map map;Creature boss,source,near,far;boss.map=&map;near.x=2;far.x=20;
  Thorim ai;ai.m_creature=&boss;
  assert(!ai.GetClosestLowerBunny(&source));ai.m_lLowerBunniesGuids={1,2,3};
  assert(!ai.GetClosestLowerBunny(&source)); // Nonempty GUID list, all actors despawned.
  map.creatures={{1,&far},{3,&near}};assert(ai.GetClosestLowerBunny(&source)==&near);
  map.creatures.erase(3);assert(ai.GetClosestLowerBunny(&source)==&far);
  map.creatures.clear();assert(!ai.GetClosestLowerBunny(&source));
 }
#endif
 std::cout<<"PASS: native depleted encounter target lists and despawned references\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''.replace('__RENATAKI__',renataki).replace('__FACE__',face).replace('__THORIM__',thorim)
    with tempfile.TemporaryDirectory(prefix=f'mantech-target-lists-{era}-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        flags=(['/DHAS_FACE'] if era!='classic' else [])+(['/DHAS_THORIM'] if era=='wotlk' else [])+([] if mode=='all' else ['/D'+mode.upper()+'_ONLY'])
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',*flags,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
