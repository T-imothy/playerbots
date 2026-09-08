"""Execute native clone class profiles and combat timing, including healer isolation."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]/'mangos-wotlk-behavior'
s=(root/'src/game/AI/ScriptDevAI/scripts/northrend/azjol-nerub/ahnkahet/boss_volazj.cpp').read_text()
profile=s[s.index('enum VolazjAbilityTarget'):s.index('/*######\n## boss_volazj')].replace(' override','')
code=r'''
#include <cassert>
#include <array>
#include <map>
#include <list>
#include <vector>
#include <iostream>
using uint32=unsigned;
enum{CLASS_WARRIOR=1,CLASS_PALADIN=2,CLASS_HUNTER=3,CLASS_ROGUE=4,CLASS_PRIEST=5,CLASS_DEATH_KNIGHT=6,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11,PLAYERSPELL_REMOVED=2,NPC_TWISTED_VISAGE_1=30621,NPC_TWISTED_VISAGE_5=30625,TYPE_VOLAZJ=0,SPECIAL=3,CAST_TRIGGERED=1,CAST_OK=0,TYPE_FULL_CASTER=1,TYPE_NONE=0};
unsigned tabs[]={100,200,300};const unsigned*GetTalentTabPages(unsigned){return tabs;}
struct Talent{unsigned TalentTab;};struct PlayerTalent{unsigned state=0;Talent*talentEntry=nullptr;unsigned currentRank=0;};
struct Player{unsigned cls;std::map<unsigned,PlayerTalent>talents;unsigned getClass(){return cls;}const auto&GetActiveTalents(){return talents;}};
struct InstanceData{unsigned state=SPECIAL;unsigned GetData(unsigned){return state;}};
struct Unit{virtual ~Unit()=default;};
struct Creature:Unit{
 unsigned entry=30621,phase=16;float health=100,distance=10;bool alive=true,busy=false,dual=false;Unit*victim=nullptr;InstanceData instance;unsigned despawns=0;
 bool IsAlive(){return alive;}bool IsInMap(Creature*other){return phase==other->phase;}float GetHealthPercent(){return health;}
 bool SelectHostileTarget(){return victim!=nullptr;}Unit*GetVictim(){return victim;}bool IsNonMeleeSpellCasted(bool){return busy;}
 bool IsWithinCombatDist(Unit*,float radius){return distance<=radius;}void SetCanDualWield(bool b){dual=b;}InstanceData*GetInstanceData(){return &instance;}void ForcedDespawn(){++despawns;}
};
std::vector<Creature*> nearby;
void GetCreatureListWithEntryInGrid(std::list<Creature*>&out,Creature*,unsigned entry,float){for(auto*p:nearby)if(p->entry==entry)out.push_back(p);}
unsigned urand(unsigned lo,unsigned){return lo;}
struct ScriptedAI{
 Creature*m_creature;bool ranged=false,fail=false;unsigned melee=0;struct Cast{Unit*target;unsigned spell;};std::vector<Cast>casts;
 ScriptedAI(Creature*c):m_creature(c){}virtual ~ScriptedAI()=default;
 void SetRangedMode(bool b,float,unsigned){ranged=b;}int DoCastSpellIfCan(Unit*t,unsigned spell,unsigned=0){casts.push_back({t,spell});return fail?1:0;}void DoMeleeAttackIfReady(){++melee;}
};
__PROFILE__
int main(){
 for(unsigned cls:{1,2,3,4,5,6,7,8,9,11})for(unsigned spec=0;spec<3;++spec){auto p=GetVolazjProfile(cls,spec);assert(p.abilities[0].spell);for(auto a:p.abilities)if(a.spell){assert(a.initial>0);assert(a.repeatMin<=a.repeatMax);assert(a.target<=VISAGE_FRIENDLY);}}
 assert(!GetVolazjProfile(0,0).abilities[0].spell);
 Talent first{100},second{200},third{300};Player healer{CLASS_PRIEST};healer.talents={{1,{0,&first,2}},{2,{0,&third,0}},{3,{PLAYERSPELL_REMOVED,&third,4}}};assert(GetVolazjPlayerSpec(&healer)==0);
 healer.talents[4]={0,&third,4};assert(GetVolazjPlayerSpec(&healer)==2);healer.talents.clear();assert(GetVolazjPlayerSpec(&healer)==0);
 Creature clone,friendClone,otherPhase,boss;Unit enemy;clone.victim=&enemy;friendClone.health=25;otherPhase.health=1;otherPhase.phase=32;boss.entry=29311;boss.health=10;nearby={&clone,&friendClone,&otherPhase,&boss};
 npc_volazj_visageAI ai(&clone);ai.Configure(&healer);assert(ai.ranged&&ai.SelectHealingTarget()==&friendClone);
 ai.UpdateAI(2000);assert(ai.casts.size()==1&&ai.casts[0].spell==57777&&ai.casts[0].target==&friendClone);
 ai.UpdateAI(2000);assert(ai.casts.back().spell==57775&&ai.casts.back().target==&friendClone);
 friendClone.health=100;assert(!ai.SelectHealingTarget());clone.health=50;assert(ai.SelectHealingTarget()==&clone);clone.health=100;
 Player mage{CLASS_MAGE};npc_volazj_visageAI caster(&clone);caster.Configure(&mage);caster.fail=true;caster.UpdateAI(2000);assert(caster.casts.size()==1&&caster.m_timers[1]==1000);caster.fail=false;caster.UpdateAI(999);assert(caster.casts.size()==1);caster.UpdateAI(1);assert(caster.casts.size()==2&&caster.m_timers[1]==3000);
 clone.busy=true;caster.UpdateAI(10000);assert(caster.casts.size()==2);clone.busy=false;caster.UpdateAI(1);assert(caster.casts.size()>2);
 Player warrior{CLASS_WARRIOR};warrior.talents={{1,{0,&second,4}}};npc_volazj_visageAI fighter(&clone);fighter.Configure(&warrior);clone.distance=4;fighter.UpdateAI(2000);assert(fighter.casts.empty());clone.distance=10;fighter.UpdateAI(1000);assert(fighter.casts.front().spell==61490);
 Player rogue{CLASS_ROGUE};npc_volazj_visageAI rogueAI(&clone);rogueAI.Configure(&rogue);assert(clone.dual&&!rogueAI.ranged);
 ai.EnterEvadeMode();assert(clone.despawns==0);clone.instance.state=0;ai.EnterEvadeMode();assert(clone.despawns==1);
 std::cout<<"PASS: all clone class/spec profiles, active talent selection, friendly-clone healing isolation, native cast rejection retry, busy casts, range conditions and empty-phase lifetime\n";
}
'''.replace('__PROFILE__',profile)
with tempfile.TemporaryDirectory(prefix='volazj-clone-combat-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True,timeout=60)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True,timeout=20)
