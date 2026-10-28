"""Compile the entire production BWL support selector with controlled native interfaces."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('bool BwlMember(', 'unsigned BwlAfflictions('))
select=block(source,'bool BlackwingLairSupportAction::Select(').replace('bool BlackwingLairSupportAction::Select(std::string& spell, Unit*& target)',
 'bool Select(PlayerbotAI* ai, std::string& spell, Unit*& target)').replace('{\n    if (!BwlReady(ai))','{\n    if (!BwlReady(ai))')
select=select.replace('{\n    if (!BwlReady(ai) ||','{\n    Player* bot=ai->bot;\n    if (!BwlReady(ai) ||').replace('[this]','[ai]')
code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <type_traits>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
enum{CLASS_WARLOCK=9,CLASS_MAGE=8,CLASS_PRIEST=5,DISPEL_MAGIC=1,DISPEL_CURSE=2,DISPEL_DISEASE=3,DISPEL_POISON=4,
 MAX_EFFECT_INDEX=3,SPELL_AURA_MOD_DAMAGE_PERCENT_TAKEN=87,SPELL_SCHOOL_MASK_FIRE=4,SPELL_SCHOOL_MASK_FROST=16,
 SPELL_SCHOOL_MASK_SHADOW=32,SPELL_SCHOOL_MASK_NATURE=8,SPELL_SCHOOL_MASK_ARCANE=64,SPELL_STATE_FINISHED=3};
enum CurrentSpellTypes{CURRENT_GENERIC_SPELL,CURRENT_CHANNELED_SPELL};
struct SpellEntry{unsigned Id=0,Dispel=0,EffectApplyAuraName[3]={},EffectMiscValue[3]={};int EffectBasePoints[3]={};};
struct Spell{SpellEntry*m_spellInfo;int state=0;int getState()const{return state;}};
struct PlayerbotAI;struct Group;
struct Unit{virtual ~Unit(){}unsigned guid=0,entry=0,instance=1;bool world=true,alive=true,combat=true,cc=false,friendly=false;
 std::set<unsigned> auras;Unit*victim=nullptr;Spell*cast=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return false;}
 bool IsInMap(Unit*u){return u&&instance==u->instance;}unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}
 Unit*GetVictim(){return victim;}virtual bool IsPlayer(){return false;}Unit*GetCharmer(){return nullptr;}
 bool HasAura(unsigned id){return auras.count(id);}float GetDistance(Unit*){return 10;}float GetHealthPercent(){return 80;}
 Spell*GetCurrentSpell(CurrentSpellTypes slot){return slot==CURRENT_GENERIC_SPELL?cast:nullptr;}};
struct Player:Unit{Group*group;PlayerbotAI*brain=nullptr;unsigned cls=CLASS_WARLOCK;bool casting=false,tank=false,healer=false,ranged=true;
 bool IsPlayer()override{return true;}bool IsBeingTeleported(){return false;}Group*GetGroup(){return group;}
 PlayerbotAI*GetPlayerbotAI(){return brain;}unsigned getClass(){return cls;}bool HasSpell(unsigned){return true;}
 bool IsNonMeleeSpellCasted(bool){return casting;}};
struct GroupReference{Player*p;GroupReference*n=nullptr;Player*getSource(){return p;}GroupReference*next(){return n;}};
struct Group{GroupReference*first;GroupReference*GetFirstMember(){return first;}};
struct PlayerbotAI{Player*bot;bool real=false;std::set<std::string>known;std::map<unsigned,Unit*>units;std::list<unsigned>nearby;unsigned current=0;Unit*assignment=nullptr;
 bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p&&p->tank;}bool IsHeal(Player*p){return p->healer;}bool IsRanged(Player*p){return p->ranged;}
 bool HasAura(const char*name,Unit*u){return std::string(name)=="banish"&&u->HasAura(710);}
 bool CanCastSpell(const char*name,Unit*,int){return known.count(name);}
 Unit*GetUnit(unsigned id){return units[id];}
 template<class T>T Value(const char*){if constexpr(std::is_same_v<T,ObjectGuid>)return current;else return nearby;}};
#define AI_VALUE(type,key) ai->Value<type>(key)
#define AI_VALUE2(type,key,qual) ai->Value<type>(key)
struct Facade{std::map<unsigned,SpellEntry>spells;SpellEntry*LookupSpellInfo(unsigned id){auto it=spells.find(id);return it==spells.end()?nullptr:&it->second;}
 bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct Config{float sightDistance=100;}sPlayerbotAIConfig;
struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*,float,bool,bool){return !u->cc;}
 static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->HasAura(710);}};
struct BlackwingLairPriorityTargetAction{PlayerbotAI*ai;BlackwingLairPriorityTargetAction(PlayerbotAI*a):ai(a){}Unit*GetTarget(){return ai->assignment;}};
bool BwlReady(PlayerbotAI*ai){return ai->bot->world&&ai->bot->alive&&ai->bot->combat&&!ai->real;}
bool IsProtectedBlackwingTarget(Player*,Unit*){return false;}bool RazorgoreEggPhase(PlayerbotAI*){return false;}
Unit*RazorgoreCreature(Player*,unsigned){return nullptr;}
__METHODS__
__SELECT__
int main(){
 Player a,b;a.guid=1;b.guid=2;PlayerbotAI aa{&a},bb{&b};a.brain=&aa;b.brain=&bb;
 GroupReference r2{&b},r1{&a,&r2};Group group{&r1};a.group=b.group=&group;
 Unit x,y,other;x.guid=10;x.entry=14101;y.guid=11;y.entry=14668;other.guid=12;other.entry=12459;
 aa.units=bb.units={{10,&x},{11,&y},{12,&other}};aa.nearby=bb.nearby={10,11,12};aa.known=bb.known={"banish"};
 std::string spell;Unit*target=nullptr;
 assert(Select(&aa,spell,target)&&spell=="banish"&&target==&x);
 assert(Select(&bb,spell,target)&&target==&y);x.auras.insert(710);assert(!Select(&aa,spell,target));
 other.alive=false;x.auras.clear();assert(Select(&aa,spell,target)&&target==&y);assert(!Select(&bb,spell,target));
 x.alive=false;assert(!Select(&aa,spell,target)&&!Select(&bb,spell,target));
 x.alive=true;other.alive=true;b.alive=false;assert(Select(&aa,spell,target)&&target==&x);b.alive=true;
 aa.nearby={12};a.cls=CLASS_MAGE;aa.known={"counterspell"};SpellEntry heal;heal.Id=22458;Spell cast{&heal};other.cast=&cast;
 assert(Select(&aa,spell,target)&&spell=="counterspell"&&target==&other);cast.state=SPELL_STATE_FINISHED;assert(!Select(&aa,spell,target));other.cast=nullptr;
 aa.known={"tranquilizing shot"};other.entry=12464;other.auras.insert(22428);assert(Select(&aa,spell,target));other.auras.clear();
 aa.known={"dispel magic"};a.auras.insert(22438);sServerFacade.spells[22438].Dispel=DISPEL_MAGIC;
 assert(Select(&aa,spell,target)&&target==&a);a.auras.clear();
 aa.current=12;other.entry=14020;other.auras.insert(22277);auto&shield=sServerFacade.spells[22277];
 shield.EffectApplyAuraName[1]=SPELL_AURA_MOD_DAMAGE_PERCENT_TAKEN;shield.EffectBasePoints[1]=1099;shield.EffectMiscValue[1]=SPELL_SCHOOL_MASK_FIRE;
 aa.known={"fireball","frostbolt"};assert(Select(&aa,spell,target)&&spell=="fireball");
 a.healer=true;assert(!Select(&aa,spell,target));a.healer=false;a.tank=true;assert(!Select(&aa,spell,target));a.tank=false;
 a.casting=true;assert(!Select(&aa,spell,target));a.casting=false;
 a.ranged=false;assert(!Select(&aa,spell,target));a.ranged=true;
 shield.EffectMiscValue[1]=SPELL_SCHOOL_MASK_FROST;assert(Select(&aa,spell,target)&&spell=="frostbolt");
 aa.known.clear();assert(!Select(&aa,spell,target));
 std::cout<<"PASS actual BWL support: coordinated banish/release, interrupts, enrage, dispels, DPS schools and cast/role guards\n";
}
'''.replace('__METHODS__',methods).replace('__SELECT__',select)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='bwl-support-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
