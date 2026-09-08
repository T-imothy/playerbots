"""Compile real shared heal admission/AOE selection and class target routes in all eras."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
base=root/'playerbot/strategy'
methods=block((base/'actions/EncounterHealingPolicy.cpp').read_text(),'bool CastHealingSpellAction::isUseful(')
methods+='\n'+block((base/'values/AoeHealValues.cpp').read_text(),'uint8 AoeHealValue::Calculate(')
routes='\n'.join(block((base/file).read_text(),signature)+';' for file,signature in [
 ('paladin/PaladinActions.h','class CastHolyShockOnSelfAction'),
 ('druid/DruidActions.h','class CastTranquilityAction'),
 ('druid/DruidActions.h','class CastLifebloomAction')])
code=r'''
#include <cassert>
#include <string>
#include <vector>
#include <iostream>
using uint8=unsigned char;using uint32=unsigned;
enum{SPELL_EFFECT_HEAL=10,SPELL_AURA_MOD_HEALING_PCT=118,CLASS_PRIEST=5,CLASS_SHAMAN=7};
struct Unit{bool world=true,alive=true,friendly=true;unsigned map=1,instance=1,phase=1,maxHealth=100;float hp=30,distance=0;int reduction=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}unsigned GetMaxHealth(){return maxHealth;}
 float GetHealthPercent(){return hp;}int GetMaxNegativeAuraModifier(unsigned){return reduction;}};
struct Group{struct Slot{unsigned guid;};using MemberSlotList=std::vector<Slot>;using member_citerator=MemberSlotList::const_iterator;MemberSlotList slots;
 const MemberSlotList&GetMemberSlots(){return slots;}};
struct Player:Unit{bool teleport=false,window=false;unsigned klass=5,subgroup=0;Group*group=nullptr;
 bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}unsigned getClass(){return klass;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 bool IsInGroup(Player*p,bool){return p->subgroup==subgroup;}};
struct PlayerbotAI{};
struct SpellEntry{bool heal=true;};
bool IsSpellHaveEffect(const SpellEntry*s,unsigned){return s->heal;}
struct Facade{SpellEntry spell;bool known=true;const SpellEntry*LookupSpellInfo(unsigned){return known?&spell:nullptr;}
 bool IsAlive(Unit*p){return p->alive;}bool IsFriendlyTo(Unit*,Unit*p){return p->friendly;}
 float GetDistance2d(Unit*,Unit*p){return p->distance;}}sServerFacade;
struct {float lowHealth=50,mediumHealth=75,criticalHealth=20;}sPlayerbotAIConfig;
struct Objects{std::vector<Player*>players;Player*GetPlayer(unsigned id){return players.at(id);}}sObjectMgr;
bool CanPrecastEncounterHeal(Player*,Unit*,const SpellEntry*){return false;}
unsigned UpcomingEncounterHealingWindow(Player*,Player*p){return p->window?2000:0;}
struct CastSpellAction{Player*bot=nullptr;Unit*target=nullptr;bool allowed=true;std::string spell;
 CastSpellAction(PlayerbotAI*,std::string s):spell(s){}virtual ~CastSpellAction()=default;
 virtual std::string getName(){return spell;}virtual std::string GetTargetName(){return "current target";}
 virtual bool isUseful(){return allowed;}void RefreshSpellId(){}unsigned GetSpellID(){return 1;}Unit*GetTarget(){return target;}};
struct CastAuraSpellAction:CastSpellAction{using CastSpellAction::CastSpellAction;bool aura=false;bool isUseful()override{return allowed&&!aura;}};
struct CastHealingSpellAction:CastAuraSpellAction{bool allowAuraRefresh;
 CastHealingSpellAction(PlayerbotAI*a,std::string s,uint8=15,bool refresh=false):CastAuraSpellAction(a,s),allowAuraRefresh(refresh){}
 std::string GetTargetName()override{return "self target";}bool isUseful()override;};
struct CastAoeHealSpellAction:CastHealingSpellAction{using CastHealingSpellAction::CastHealingSpellAction;
 std::string GetTargetName()override{return "party member to heal";}};
struct AoeHealValue{Player*bot;std::string qualifier="low";uint8 Calculate();};
__METHODS__
__ROUTES__
int main(){Player bot,patient;CastHealingSpellAction heal(nullptr,"regrowth");heal.bot=&bot;heal.target=&patient;heal.aura=true;
 // Existing Regrowth/Riptide HoT must not block a rescue's immediate heal.
 assert(heal.isUseful());patient.hp=75;assert(!heal.isUseful());patient.hp=30;
 sServerFacade.spell.heal=false;assert(!heal.isUseful());heal.aura=false;assert(heal.isUseful());heal.aura=true;
 sServerFacade.spell.heal=true;heal.allowed=false;assert(!heal.isUseful());heal.allowed=true;
 patient.reduction=-100;assert(!heal.isUseful());patient.reduction=0;
 sServerFacade.known=false;assert(!heal.isUseful());sServerFacade.known=true;
 CastHolyShockOnSelfAction shock(nullptr);assert(shock.GetTargetName()=="self target"&&shock.spell=="holy shock"&&shock.getName()=="holy shock on self");
 CastTranquilityAction tranquility(nullptr);assert(tranquility.GetTargetName()=="self target");
 CastLifebloomAction bloom(nullptr);bloom.bot=&bot;bloom.target=&patient;bloom.aura=true;patient.hp=100;
 assert(bloom.GetTargetName()=="party tank without lifebloom"&&bloom.isUseful());patient.reduction=-100;assert(!bloom.isUseful());patient.reduction=0;
 bloom.allowed=false;assert(!bloom.isUseful());
 Group group;group.slots={{0},{1}};bot.group=&group;sObjectMgr.players={&bot,&patient};bot.hp=100;patient.hp=30;AoeHealValue aoe{&bot};
 for(unsigned klass:{2u,5u,7u,11u}){bot.klass=klass;assert(aoe.Calculate()==1);
  patient.map=2;assert(aoe.Calculate()==0);patient.map=1;
  patient.instance=2;assert(aoe.Calculate()==0);patient.instance=1;
  patient.phase=2;assert(aoe.Calculate()==0);patient.phase=1;
  patient.world=false;assert(aoe.Calculate()==0);patient.world=true;
  patient.alive=false;assert(aoe.Calculate()==0);patient.alive=true;
  patient.teleport=true;assert(aoe.Calculate()==0);patient.teleport=false;
  patient.friendly=false;assert(aoe.Calculate()==0);patient.friendly=true;
  patient.maxHealth=0;assert(aoe.Calculate()==0);patient.maxHealth=100;
  patient.reduction=-100;assert(aoe.Calculate()==0);patient.window=true;assert(aoe.Calculate()==1);patient.window=false;patient.reduction=0;
  patient.distance=41;assert(aoe.Calculate()==0);patient.distance=35;assert(aoe.Calculate()==(klass==7));patient.distance=0;
 }
 bot.klass=5;patient.subgroup=1;assert(aoe.Calculate()==0);patient.subgroup=0;
 bot.teleport=true;assert(aoe.Calculate()==0);bot.teleport=false;bot.group=nullptr;assert(aoe.Calculate()==0);
 std::cout<<"PASS: direct-plus-HoT rescue, pure HoT suppression, shared safety, stacking, Holy Shock/Tranquility routes and cross-class AOE eligibility\n";
}
'''.replace('__METHODS__',methods).replace('__ROUTES__',routes)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='healer-integration-') as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
holy=(base/'paladin/HolyPaladinStrategy.cpp').read_text()
assert holy.count('new NextAction("holy shock on self", ACTION_MEDIUM_HEAL + 2)')==3
assert 'new NextAction("holy shock", ACTION_MEDIUM_HEAL + 2)' not in holy
context=(base/'paladin/PaladinAiObjectContext.cpp').read_text()
assert 'creators["holy shock on self"]' in context and 'creators["holy shock"]' in context
for klass in ('priest','druid','shaman','paladin'):
 assert 'Heal' in (base/klass/(klass.capitalize()+'Actions.h')).read_text()

# A useful Regrowth refresh must not starve the available instant rescue.
restoration=(base/'druid/RestorationDruidStrategy.cpp').read_text()
for suffix in ('',' on party'):
 assert restoration.count(f'new NextAction("swiftmend{suffix}", ACTION_CRITICAL_HEAL + 2)')==6
 assert f'new NextAction("regrowth{suffix}"), new NextAction("healing touch{suffix}")' in restoration
