"""Compile actual Loatheb window admission and single/AOE heal dispatch gates."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/EncounterHealingPolicy.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('uint32 ai::UpcomingEncounterHealingWindow(', 'bool ai::CanPrecastEncounterHeal(', 'bool CastHealingSpellAction::isUseful(', 'bool CastHealingSpellAction::Execute('))
methods+='\n'+block((root/'playerbot/strategy/actions/GenericSpellActions.cpp').read_text(),'bool CastAoeHealSpellAction::isUseful(')
code=r'''
#include <cassert>
#include <iostream>
#include <vector>
using uint32=unsigned;
enum{SPELL_AURA_MOD_HEALING_PCT=118,SPELL_EFFECT_HEAL=10};
struct Modifier{int m_amount=-100;};struct Aura{unsigned id=55593;Modifier modifier;unsigned GetId()const{return id;}const Modifier*GetModifier()const{return &modifier;}};
struct Unit;
struct SpellAuraHolder{Unit*caster;int duration=2000;Unit*GetCaster()const{return caster;}int GetAuraDuration()const{return duration;}};
struct Unit{unsigned entry=16011,map=533,phase=1;bool world=true,alive=true,combat=true,charmed=false;int reduction=-100;SpellAuraHolder*holder=nullptr;std::vector<Aura*>modifiers;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}unsigned GetEntry(){return entry;}
 const SpellAuraHolder*GetSpellAuraHolder(unsigned id){return id==55593?holder:nullptr;}const std::vector<Aura*>&GetAurasByType(unsigned){return modifiers;}
 int GetMaxNegativeAuraModifier(unsigned){return reduction;}
};
struct Player:Unit{bool teleport=false;bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return map;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}};
struct SpellEntry{bool heal=true,channel=false;unsigned cast=2500;};
bool IsSpellHaveEffect(const SpellEntry*s,unsigned){return s->heal;}bool IsChanneledSpell(const SpellEntry*s){return s->channel;}unsigned GetSpellCastTime(const SpellEntry*s,Player*){return s->cast;}
struct Facade{SpellEntry spell;const SpellEntry*LookupSpellInfo(unsigned){return &spell;}}sServerFacade;
struct Event{};
struct CastSpellAction{Player*bot;Unit*target;unsigned casts=0;void RefreshSpellId(){}unsigned GetSpellID()const{return spellId;}Unit*GetTarget(){return target;}bool isUseful(){return true;}bool Execute(Event&){++casts;return true;}private:unsigned spellId=1;};
struct CastAuraSpellAction:CastSpellAction{};
namespace ai{
 unsigned UpcomingEncounterHealingWindow(Player*,Unit*);bool CanPrecastEncounterHeal(Player*,Unit*,const SpellEntry*);
 struct CastHealingSpellAction:CastAuraSpellAction{bool isUseful();bool Execute(Event&);};
 struct CastAoeHealSpellAction:CastHealingSpellAction{bool isUseful();};
}
using namespace ai;
__METHODS__
int main(){Player bot;Unit target,boss;SpellAuraHolder holder{&boss};target.holder=&holder;Aura aura,other;target.modifiers={&aura};Event event;
 CastHealingSpellAction heal;heal.bot=&bot;heal.target=&target;CastAoeHealSpellAction aoe;aoe.bot=&bot;aoe.target=&target;
#ifdef MANGOSBOT_TWO
 assert(UpcomingEncounterHealingWindow(&bot,&target)==2000&&heal.isUseful()&&aoe.isUseful());assert(heal.Execute(event)&&heal.casts==1);
 holder.duration=2600;assert(!heal.isUseful()&&!heal.Execute(event)&&!aoe.isUseful());holder.duration=2400;assert(heal.isUseful());
 holder.duration=2500;assert(!heal.isUseful());holder.duration=2000;
 sServerFacade.spell.cast=1000;assert(!heal.isUseful());sServerFacade.spell.cast=5000;assert(!heal.isUseful());sServerFacade.spell.cast=2500;
 sServerFacade.spell.channel=true;assert(!heal.isUseful());sServerFacade.spell.channel=false;sServerFacade.spell.heal=false;assert(!heal.isUseful());sServerFacade.spell.heal=true;
 holder.duration=16000;assert(!heal.Execute(event));holder.duration=2000; // aura refreshed while queued
 holder.duration=-1;assert(!heal.isUseful());holder.duration=2000;
 other.id=123;target.modifiers.push_back(&other);assert(!heal.isUseful());target.modifiers.pop_back();
 boss.combat=false;assert(!heal.isUseful());boss.combat=true;boss.entry=999;assert(!heal.isUseful());boss.entry=16011;
 boss.phase=2;assert(!heal.isUseful());boss.phase=1;
 bot.teleport=true;assert(!heal.isUseful());bot.teleport=false;
 target.holder=nullptr;assert(!heal.isUseful());target.holder=&holder;
#else
 assert(!UpcomingEncounterHealingWindow(&bot,&target)&&!heal.isUseful()&&!heal.Execute(event)&&!aoe.isUseful());
#endif
 target.reduction=0;target.holder=nullptr;assert(heal.isUseful()&&aoe.isUseful()&&heal.Execute(event));
 std::cout<<"PASS: native aura expiry and haste-aware precast, no premature instant/channel casts, queued refresh and ordinary healing\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-heal-window-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
