"""Actual paladin aura and mage conjure selection with native HasSpell predicates."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
paladin=(root/'playerbot/strategy/paladin/PaladinActions.cpp').read_text()
trigger=(root/'playerbot/strategy/paladin/PaladinTriggers.cpp').read_text()
generic=(root/'playerbot/strategy/actions/GenericSpellActions.cpp').read_text()
aura_methods='\n'.join([block(paladin,key) for key in ('std::string ai::SelectPaladinAura(',
    'bool CastPaladinAuraAction::isUseful(', 'bool CastPaladinAuraAction::isPossible(',
    'bool CastPaladinAuraAction::Execute(')] + [block(trigger,'bool NoPaladinAuraTrigger::IsActive(')])
conjure=block(generic,'if (spellName == "conjure food" || spellName == "conjure water")')
code=r'''
#include <cassert>
#include <algorithm>
#include <cctype>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>
using uint32=unsigned;
enum{PLAYERSPELL_REMOVED=2,SPELL_EFFECT_CREATE_ITEM=24,EQUIP_ERR_OK=0};
struct PlayerSpell{unsigned state=0;bool disabled=false;};using PlayerSpellMap=std::map<uint32,PlayerSpell>;
struct ItemPrototype{bool usable=true;};
struct Player{PlayerSpellMap m_spells;bool alive=true,world=true,charmed=false,teleport=false;
 bool HasSpell(uint32 spell)const;PlayerSpellMap& GetSpellMap(){return m_spells;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}
 unsigned CanUseItem(const ItemPrototype* p){return p->usable?0:1;}};
__HAS_SPELL__
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{std::map<std::string,Value<uint32>> spells;
 template<class T>Value<T>* GetValue(const char* key,std::string name){assert(std::string(key)=="spell id");return &spells[name];}};
enum class BotCheatMask{attackspeed};
struct PlayerbotAI{Player* bot;Context context;std::set<std::string> own,other;bool canCast=true,castOK=true,fast=false;
 unsigned attempts=0,castId=0;std::string castName;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}
 bool HasMyAura(std::string name,Player*){return own.count(name);}
 bool HasAura(std::string name,Player*){return own.count(name)||other.count(name);}
 bool HasCheat(BotCheatMask){return fast;}bool CanCastSpell(std::string,Player*){return canCast;}
 bool CastSpell(std::string name,Player*,void*,bool triggered,unsigned* duration){assert(!triggered);++attempts;castName=name;
 if(!castOK)return false;assert(duration);*duration=1777;own.insert(name);return true;}
 bool CastSpell(unsigned id,Player*,void*,bool triggered,unsigned* duration){assert(!triggered);++attempts;castId=id;*duration=2200;return castOK;}};
struct Config{unsigned globalCoolDown=1500;}sPlayerbotAIConfig;struct Event{};
namespace ai{std::string SelectPaladinAura(PlayerbotAI*);
 struct CastPaladinAuraAction{PlayerbotAI* ai;Player* bot;unsigned duration=0;
 bool isUseful();bool isPossible();bool Execute(Event&);void SetDuration(unsigned value){duration=value;}};
 struct NoPaladinAuraTrigger{PlayerbotAI* ai;bool IsActive();};}
using namespace ai;
__AURA_METHODS__
struct SpellEntry{unsigned Id=0,Effect[1]{24},EffectItemType[1]{1};std::string SpellName[1]{"Conjure Food"};bool passive=false;};
bool IsPassiveSpell(const SpellEntry* spell){return spell->passive;}
struct Facade{std::map<unsigned,SpellEntry> spells;const SpellEntry* LookupSpellInfo(unsigned id){
 auto i=spells.find(id);return i==spells.end()?nullptr:&i->second;}}sServerFacade;
struct ObjectMgr{std::map<unsigned,ItemPrototype> items{{1,{}}};const ItemPrototype* GetItemPrototype(unsigned id){
 auto i=items.find(id);return i==items.end()?nullptr:&i->second;}}sObjectMgr;
void strToLower(std::string& text){std::transform(text.begin(),text.end(),text.begin(),[](unsigned char c){return char(std::tolower(c));});}
bool Conjure(PlayerbotAI* ai,Player* bot,std::string spellName){
 bool executed=false;unsigned observedSpellId=0,spellDuration=sPlayerbotAIConfig.globalCoolDown;
 __CONJURE__
 return executed;
}
int main(){
 Player bot;PlayerbotAI ai{&bot};CastPaladinAuraAction action{&ai,&bot};NoPaladinAuraTrigger trigger{&ai};Event event;
 auto learn=[&](std::string name,unsigned id){ai.context.spells[name].value=id;bot.m_spells[id]={};};
 assert(!trigger.IsActive()&&!action.isPossible()&&!action.isUseful()&&!action.Execute(event)&&ai.attempts==0);
 learn("devotion aura",1);learn("retribution aura",2);assert(trigger.IsActive()&&action.isPossible());
 ai.canCast=false;assert(!action.isPossible());ai.canCast=true;
 ai.castOK=false;assert(!action.Execute(event)&&action.duration==0);ai.castOK=true;
 assert(action.Execute(event)&&ai.castName=="devotion aura"&&action.duration==1777);
 unsigned attempts=ai.attempts;assert(!trigger.IsActive()&&!action.isUseful()&&!action.Execute(event)&&ai.attempts==attempts);
 ai.own.clear();ai.other={"devotion aura"};assert(action.Execute(event)&&ai.castName=="retribution aura");
 ai.own.clear();ai.other={"devotion aura","retribution aura"};assert(!trigger.IsActive()&&!action.Execute(event));
 ai.other.clear();bot.m_spells[1].state=PLAYERSPELL_REMOVED;assert(SelectPaladinAura(&ai)=="retribution aura");
 bot.m_spells[2].disabled=true;assert(!trigger.IsActive());bot.m_spells[1]={};bot.m_spells[2]={};
 ai.fast=true;assert(action.Execute(event)&&action.duration==1);ai.fast=false;ai.own.clear();
 bot.teleport=true;assert(!trigger.IsActive()&&!action.Execute(event));bot.teleport=false;
 bot.charmed=true;assert(!trigger.IsActive());bot.charmed=false;bot.alive=false;assert(!trigger.IsActive());bot.alive=true;
 ai.context.spells.clear();bot.m_spells.clear();learn("sanctity aura",10);learn("crusader aura",11);
#ifdef MANGOSBOT_TWO
 assert(SelectPaladinAura(&ai)=="crusader aura");
#else
 assert(SelectPaladinAura(&ai)=="sanctity aura");
#endif
 bot.m_spells[10].disabled=true;
#ifdef MANGOSBOT_ZERO
 assert(SelectPaladinAura(&ai).empty());
#else
 assert(SelectPaladinAura(&ai)=="crusader aura");
#endif
 bot.m_spells.clear();ai.attempts=0;
 for(unsigned id:{100u,200u,300u}){bot.m_spells[id]={};sServerFacade.spells[id].Id=id;}
 bot.m_spells[300].state=PLAYERSPELL_REMOVED;bot.m_spells[200].disabled=true;
 assert(Conjure(&ai,&bot,"conjure food")&&ai.castId==100); // not 300/200 pending cleanup
 bot.m_spells[200].disabled=false;assert(Conjure(&ai,&bot,"conjure food")&&ai.castId==200);
 sServerFacade.spells[200].passive=true;assert(Conjure(&ai,&bot,"conjure food")&&ai.castId==100);
 sServerFacade.spells[100].EffectItemType[0]=99;attempts=ai.attempts;assert(!Conjure(&ai,&bot,"conjure food")&&ai.attempts==attempts);
 sServerFacade.spells[100].EffectItemType[0]=1;sObjectMgr.items[1].usable=false;assert(!Conjure(&ai,&bot,"conjure food"));
 sObjectMgr.items[1].usable=true;sServerFacade.spells[100].SpellName[0]="Conjure Water";
 assert(!Conjure(&ai,&bot,"conjure food")&&Conjure(&ai,&bot,"conjure water")&&ai.castId==100);
 bot.m_spells[100].state=PLAYERSPELL_REMOVED;assert(!Conjure(&ai,&bot,"conjure water"));
 std::cout<<"PASS: native learned spellbook state; aura stale-action/era/duration policy; conjure rank availability\n";
}
'''.replace('__AURA_METHODS__',aura_methods).replace('__CONJURE__',conjure)
for era,realm in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk')):
    native=(root.parent/f'mangos-{realm}-behavior/src/game/Entities/Player.cpp').read_text()
    actual=block(native,'bool Player::HasSpell(uint32 spell) const')
    with tempfile.TemporaryDirectory(prefix='mantech-support-spells-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code.replace('__HAS_SPELL__',actual))
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
