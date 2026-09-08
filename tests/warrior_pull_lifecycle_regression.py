"""Focused production-method tests; native spell tables supply per-era fixtures."""
from pathlib import Path
import subprocess,tempfile,re,json,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
def extract(file,signature):
 s=(root/file).read_text();a=s.index(signature);i=s.index('{',a)+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
prefix=r'''
#include <cassert>
#include <cstdint>
#include <map>
#include <list>
#include <string>
#include <vector>
using uint32=uint32_t;using uint64=uint64_t;using time_t=long long;
time_t clockNow=100;time_t time(std::nullptr_t){return clockNow;}time_t time(int){return clockNow;}
enum SpellCastResult{SPELL_CAST_OK,SPELL_FAILED_ONLY_SHAPESHIFT,SPELL_FAILED_NOT_SHAPESHIFT,SPELL_FAILED_NO_POWER,SPELL_FAILED_NOT_READY};
constexpr int POWER_RAGE=1;enum AuraState{PROC=1};constexpr int CLASS_WARRIOR=1,FORM_BATTLESTANCE=17,FORM_DEFENSIVESTANCE=18,FORM_BERSERKERSTANCE=19;
struct SpellEntry{uint32 Id=1;uint64 Stances=0;uint32 CasterAuraState=0;int powerType=1;};
SpellCastResult GetErrorAtShapeshiftedCast(const SpellEntry* s,uint32 form){return !s->Stances||(s->Stances&(uint64(1)<<(form-1)))?SPELL_CAST_OK:SPELL_FAILED_ONLY_SHAPESHIFT;}
struct Unit {bool alive=true,world=true,combat=false,casting=false;Unit* victim=nullptr;float distance=20;bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsInCombat(){return combat;}Unit* GetVictim(){return victim;}float GetDistance(Unit*,bool=false,int=0){return distance;}float GetDistance(float,float,float){return distance;}};
struct UnitAI{int react=2;void SetReactState(int state){react=state;}};
struct Creature:Unit{UnitAI controller;UnitAI* AI(){return &controller;}};using Pet=Creature;
struct Player:Unit{int rage=30;int GetPower(int){return rage;}int klass=CLASS_WARRIOR,form=FORM_BERSERKERSTANCE;bool proc=false;Pet* pet=nullptr;Unit* ally=nullptr;bool sameMap=true;
 int getClass(){return klass;}int GetShapeshiftForm(){return form;}bool HasAuraState(AuraState){return proc;}Pet* GetPet(){return pet;}
 bool IsInMap(Unit*){return sameMap;}bool IsInGroup(Unit* u){return u==ally;}bool IsNonMeleeSpellCasted(bool){return casting;}};
struct Spell{static uint32 CalculatePowerCost(const SpellEntry*,Player*){return 10;}};
struct ObjectGuid{int n=0;void Clear(){n=0;}};
struct Context{uint32 id=1;template<class T>Context* GetValue(const char*,const std::string&){return this;}uint32 Get(){return id;}};
struct Facade{SpellEntry spell;const SpellEntry* LookupSpellInfo(uint32 id){return id?&spell:nullptr;}}sServerFacade;
namespace BotState {int BOT_STATE_COMBAT=1;}
struct PlayerbotAI{Player* bot;Context context;bool pullBack=false,known=true,stanceUsable=true;SpellCastResult castResult=SPELL_FAILED_ONLY_SHAPESHIFT;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}bool HasSpell(const char*){return known;}
 bool CanCastSpell(const std::string& name,Unit*,int,void*=nullptr,bool=false,bool=false,bool=false,SpellCastResult* result=nullptr){bool stance=name.find("stance")!=std::string::npos;auto r=stance?(stanceUsable?SPELL_CAST_OK:SPELL_FAILED_NOT_READY):castResult;if(result)*result=r;return r==SPELL_CAST_OK;}
 bool HasStrategy(const char*,int){return pullBack;}float GetRange(const char*){return 5;} };
namespace ai{std::string WarriorStancePrerequisite(PlayerbotAI*,const SpellEntry*);bool CanPlanWarriorSpell(PlayerbotAI*,const std::string&,Unit*);}
using namespace ai;
struct PositionEntry{float x=0,y=0,z=0;bool set=true;bool isSet(){return set;}};using PositionMap=std::map<std::string,PositionEntry>;PositionMap positions;
#define AI_VALUE(T,N) positions
const float ATTACK_DISTANCE=5,BASE_MELEERANGE_OFFSET=1;
struct PullStrategy{PlayerbotAI* ai;Unit* target=nullptr;bool pendingToStart=false,petReactStateSaved=false;time_t pullStartTime=0,pullActionTime=0;int petReactState=2;ObjectGuid requesterGuid;
 static PullStrategy* active;static PullStrategy* Get(PlayerbotAI*){return active;}Unit* GetTarget()const{return target;}void SetTarget(Unit* u){target=u;}bool HasTarget()const{return target!=nullptr;}
 bool HasPullStarted()const{return pullStartTime>0;}bool HasPullActionIssued()const{return pullActionTime>0;}bool IsPullPendingToStart()const{return pendingToStart;}
 time_t GetPullStartTime()const{return pullStartTime;}time_t GetPullActionTime()const{return pullActionTime;}int GetMaxPullTime()const{return 15;}
 void RetryPullAction(){pullActionTime=0;pendingToStart=true;}void OnPullStarted();void OnPullActionIssued();void OnPullEnded();void RequestPull(Unit*,bool=true);
};PullStrategy* PullStrategy::active=nullptr;
struct PullStartTrigger{PlayerbotAI* ai;Player* bot;bool IsActive();};struct PullEndTrigger{PlayerbotAI* ai;Player* bot;bool IsActive();};
struct ReturnToPullPositionTrigger{PlayerbotAI* ai;Player* bot;bool IsActive();};
'''.replace('void*=','void* =')
code=prefix
for name in ['WarriorStancePrerequisite','CanPlanWarriorSpell']:
 code+=extract('playerbot/strategy/warrior/WarriorCombatPolicy.cpp',('std::string' if name=='WarriorStancePrerequisite' else 'bool')+' ai::'+name)+'\n'
for name in ['OnPullStarted','OnPullActionIssued','OnPullEnded','RequestPull']:
 code+=extract('playerbot/strategy/generic/PullStrategy.cpp','void PullStrategy::'+name)+'\n'
for name in ['PullStartTrigger','PullEndTrigger']:
 code+=extract('playerbot/strategy/triggers/PullTriggers.cpp','bool '+name+'::IsActive')+'\n'
code+=extract('playerbot/strategy/triggers/GenericTriggers.cpp','bool ReturnToPullPositionTrigger::IsActive')+'\n'
code+=r'''
int main(){
 Player tank;Unit mob,ally;PlayerbotAI ai{&tank};tank.ally=&ally;
 auto& spell=sServerFacade.spell;spell.Stances=uint64(1)<<(FORM_BATTLESTANCE-1);
 assert(WarriorStancePrerequisite(&ai,&spell)=="battle stance");
 assert(CanPlanWarriorSpell(&ai,"overpower",&mob));spell.CasterAuraState=PROC;assert(!CanPlanWarriorSpell(&ai,"overpower",&mob));tank.proc=true;assert(CanPlanWarriorSpell(&ai,"overpower",&mob));
 tank.rage=0;assert(!CanPlanWarriorSpell(&ai,"overpower",&mob));tank.rage=30;
 ai.castResult=SPELL_FAILED_NO_POWER;assert(!CanPlanWarriorSpell(&ai,"overpower",&mob));ai.castResult=SPELL_FAILED_ONLY_SHAPESHIFT;
 ai.stanceUsable=false;assert(!CanPlanWarriorSpell(&ai,"overpower",&mob));ai.stanceUsable=true;ai.known=false;assert(WarriorStancePrerequisite(&ai,&spell).empty());ai.known=true;
 tank.form=FORM_BATTLESTANCE;assert(WarriorStancePrerequisite(&ai,&spell).empty());tank.form=FORM_BERSERKERSTANCE;
 // Sweeping Strikes allows Battle only in Classic, Battle/Berserker in TBC/Wrath.
 for(int era=0;era<3;++era){spell.Stances=(uint64(1)<<(FORM_BATTLESTANCE-1))|(era?(uint64(1)<<(FORM_BERSERKERSTANCE-1)):0);assert(WarriorStancePrerequisite(&ai,&spell).empty()==bool(era));}
 // Wrath Berserker Rage requires no forced stance change.
 spell.Stances=0;assert(WarriorStancePrerequisite(&ai,&spell).empty());tank.klass=2;spell.Stances=uint64(1)<<16;assert(WarriorStancePrerequisite(&ai,&spell).empty());tank.klass=1;
 PullStrategy pull{&ai};PullStrategy::active=&pull;PullStartTrigger start{&ai,&tank};PullEndTrigger end{&ai,&tank};ReturnToPullPositionTrigger back{&ai,&tank};
 pull.RequestPull(&mob);assert(start.IsActive());pull.OnPullStarted();assert(!start.IsActive());assert(!end.IsActive());assert(!back.IsActive());
 clockNow=101;pull.OnPullActionIssued();assert(!start.IsActive());assert(pull.GetPullStartTime()==100);tank.casting=true;assert(!end.IsActive()&&!back.IsActive());
 tank.casting=false;mob.combat=true;mob.victim=&ally;assert(end.IsActive()); // immediate ally rescue, no ten-second wait
 mob.victim=&tank;ai.pullBack=true;tank.distance=20;mob.distance=20;assert(!end.IsActive()&&back.IsActive());tank.distance=2;assert(end.IsActive());
 tank.distance=20;ai.pullBack=false;assert(end.IsActive()); // ordinary tank commits once engaged
 mob.combat=false;clockNow=104;assert(start.IsActive());assert(!pull.HasPullActionIssued()&&pull.GetPullStartTime()==100);pull.OnPullStarted();pull.OnPullActionIssued();assert(pull.GetPullStartTime()==100);
 clockNow=115;assert(end.IsActive());assert(!start.IsActive());
 Pet pet;pet.controller.react=0;tank.pet=&pet;pull.petReactStateSaved=true;pull.petReactState=2;pull.OnPullEnded();assert(pet.controller.react==2&&!pull.HasTarget()&&!pull.IsPullPendingToStart());
 clockNow=200;pull.RequestPull(&mob);pull.petReactStateSaved=true;pull.RequestPull(&mob);assert(pull.petReactStateSaved); // repeated command retains saved pet state
 mob.alive=false;assert(end.IsActive());mob.alive=true;tank.sameMap=false;assert(end.IsActive());tank.sameMap=true;
 pull.OnPullEnded();assert(!start.IsActive()&&!end.IsActive()&&!back.IsActive());
}
'''
with tempfile.TemporaryDirectory(prefix='warrior-pull-regression-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS: native stance planning, proc/resource/GCD guards; pull phases, ally rescue, pull-back, retries, deadlines, cancellation and pet restoration')
