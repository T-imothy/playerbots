"""Actual mage selection/dispatch plus native spellsteal-pool contracts."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/mage/MageActions.cpp').read_text()
trigger=(root/'playerbot/strategy/mage/MageTriggers.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('bool CastSpellstealAction::HasStealableAura(',
    'bool CastSpellstealAction::isUseful(', 'bool CastSpellstealAction::Execute('))
methods+='\n'+block(trigger,'bool SpellstealTrigger::IsActive(')
code=r'''
#include <cassert>
#include <map>
#include <iostream>
using uint32=unsigned;using int32=int;
enum DispelType{DISPEL_NONE=0,DISPEL_MAGIC=1,DISPEL_CURSE=2,DISPEL_ALL=7,DISPEL_ZG_TICKET=10};
constexpr unsigned MAX_EFFECT_INDEX=3,SPELL_EFFECT_STEAL_BENEFICIAL_BUFF=126,SPELL_ATTR_EX4_CANNOT_BE_STOLEN=1;
unsigned GetDispellMask(DispelType t){return t==DISPEL_ALL?0x1e:1u<<t;}
struct SpellEntry{unsigned Dispel=1,Effect[3]={0};int EffectMiscValue[3]={0};bool prohibited=false;
 bool HasAttribute(unsigned a)const{assert(a==SPELL_ATTR_EX4_CANNOT_BE_STOLEN);return prohibited;}};
struct SpellAuraHolder{SpellEntry* info;bool positive=true,passive=false;int duration=20000;
 const SpellEntry* GetSpellProto()const{return info;}bool IsPositive()const{return positive;}
 bool IsPassive()const{return passive;}int GetAuraDuration()const{return duration;}};
struct Unit{unsigned map=1,phase=1;bool world=true,alive=true;std::map<unsigned,SpellAuraHolder*> auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}const auto& GetSpellAuraHolderMap(){return auras;}};
struct Player:Unit{bool charmed=false,teleport=false,attack=true;
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit* u){return u&&map==u->map&&phase==u->phase;}
 bool CanAttackSpell(Unit*,const SpellEntry*){return attack;}};
struct PlayerbotAI{Player* bot;Unit* target=nullptr;bool useful=true;unsigned casts=0,refreshes=0;
 Player* GetBot(){return bot;}};
struct Event{};
struct{unsigned dispelAuraDuration=2000;}sPlayerbotAIConfig;
struct{SpellEntry* spell=nullptr;const SpellEntry* LookupSpellInfo(unsigned id){return id?spell:nullptr;}}sServerFacade;
struct CastSpellAction{PlayerbotAI* ai;CastSpellAction(PlayerbotAI* a):ai(a){};bool isUseful(){++ai->refreshes;return ai->useful;}
 bool Execute(Event&){++ai->casts;return true;}void RefreshSpellId(){++ai->refreshes;}unsigned GetSpellID(){return 30449;}
 Unit* GetTarget(){return ai->target;}};
struct CastSpellstealAction:CastSpellAction{CastSpellstealAction(PlayerbotAI* a):CastSpellAction(a){}
 static bool HasStealableAura(PlayerbotAI*,Unit*,const SpellEntry*);bool isUseful();bool Execute(Event&);};
struct SpellstealTrigger{PlayerbotAI* ai;bool IsActive();};
__METHODS__
int main(){
 Player bot;Unit enemy;PlayerbotAI ai{&bot,&enemy};SpellEntry steal,buff,second;
 steal.Effect[0]=SPELL_EFFECT_STEAL_BENEFICIAL_BUFF;steal.EffectMiscValue[0]=DISPEL_MAGIC;sServerFacade.spell=&steal;
 SpellAuraHolder holder{&buff},other{&second};CastSpellstealAction action(&ai);SpellstealTrigger trigger{&ai};Event event;
 enemy.auras={{1,&holder}};
#ifdef MANGOSBOT_ZERO
 assert(!trigger.IsActive()&&!action.isUseful()&&!action.Execute(event));
#else
 assert(trigger.IsActive()&&action.isUseful()&&action.Execute(event)&&ai.casts==1);
 buff.prohibited=true;assert(!trigger.IsActive()&&!action.isUseful()&&!action.Execute(event)&&ai.casts==1);buff.prohibited=false;
 holder.passive=true;assert(!action.isUseful());holder.passive=false;holder.positive=false;assert(!action.isUseful());holder.positive=true;
 buff.Dispel=0;assert(!action.isUseful());buff.Dispel=2;assert(!action.isUseful());buff.Dispel=32;assert(!action.isUseful());buff.Dispel=1;
 holder.duration=1000;assert(!action.isUseful());enemy.auras[2]=&other;assert(action.isUseful());enemy.auras.erase(2);
 holder.duration=-1;assert(action.isUseful());holder.duration=0;assert(action.isUseful());holder.duration=2000;assert(action.isUseful());
 holder.duration=1000;sPlayerbotAIConfig.dispelAuraDuration=0;assert(action.isUseful());sPlayerbotAIConfig.dispelAuraDuration=2000;holder.duration=20000;
 // The native holder says whether an applied buff is positive; no name-based
 // ban list or context-free spell positivity classifier replaces it.
 assert(action.isUseful());enemy.auras.clear();assert(!action.Execute(event)&&ai.casts==1);enemy.auras={{1,&holder}};
 ai.useful=false;assert(!trigger.IsActive());ai.useful=true;
 bot.attack=false;assert(!action.isUseful());bot.attack=true;bot.charmed=true;assert(!action.isUseful());bot.charmed=false;
 bot.teleport=true;assert(!action.isUseful());bot.teleport=false;bot.alive=false;assert(!action.isUseful());bot.alive=true;
 enemy.world=false;assert(!action.isUseful());enemy.world=true;enemy.alive=false;assert(!action.isUseful());enemy.alive=true;
 enemy.map=2;assert(!action.isUseful());enemy.map=1;enemy.phase=2;assert(!action.isUseful());enemy.phase=1;
 ai.target=&bot;assert(!action.isUseful());ai.target=nullptr;assert(!action.isUseful());ai.target=&enemy;
 steal.Effect[0]=0;assert(!action.isUseful());steal.Effect[2]=SPELL_EFFECT_STEAL_BENEFICIAL_BUFF;steal.EffectMiscValue[2]=DISPEL_MAGIC;
 assert(action.isUseful());steal.EffectMiscValue[2]=-1;assert(!action.isUseful());steal.EffectMiscValue[2]=32;assert(!action.isUseful());
 steal.EffectMiscValue[2]=DISPEL_ALL;buff.Dispel=2;assert(action.isUseful());buff.Dispel=1;
 sServerFacade.spell=nullptr;assert(!action.isUseful());sServerFacade.spell=&steal;
 enemy.auras={{1,nullptr}};assert(!action.isUseful());holder.info=nullptr;enemy.auras[1]=&holder;assert(!action.isUseful());
#endif
 std::cout<<"PASS: actual Spellsteal holder policy, era gates, native masks, lifecycle, trigger and fresh dispatch\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-spellsteal-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for realm in ('tbc','wotlk'):
    core=root.parent/f'mangos-{realm}-behavior'
    native=(core/'src/game/Spells/SpellEffects.cpp').read_text()
    effect=block(native,'void Spell::EffectStealBeneficialBuff(')
    for predicate in ('GetDispellMask(', 'holder->IsPositive()', '!holder->IsPassive()',
                      'SPELL_ATTR_EX4_CANNOT_BE_STOLEN', 'RemoveAurasDueToSpellBySteal'):
        assert predicate in effect
print('PASS: TBC/Wrath native steal pool contracts; normal core casting/stealing remains authoritative')
