"""Actual native-Frost-Aura self preservation gate, including all era boundaries."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/actions/RaidHealingObjective.cpp').read_text(),'bool ai::NeedsSapphironSelfHealing(')
code=r'''
#include <cassert>
#include <iostream>
#include <initializer_list>
enum{POWER_MANA,SPELL_AURA_MOD_HEALING_PCT};enum class BotState{BOT_STATE_COMBAT};
struct Unit{bool world=true,alive=true,combat=true,charm=false,friendly=false;unsigned map=533,instance=1,entry=15989;
bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}unsigned GetEntry(){return entry;}
bool IsInMap(Unit*u){assert(world&&u->world);return u->map==map&&u->instance==instance;}};
struct SpellAuraHolder{Unit*caster=nullptr;Unit*GetCaster()const{return caster;}};
struct Player:Unit{bool teleport=false,duel=false,heal=true,group=true;unsigned hp=19,maxhp=100,mana=100;int healing=0;SpellAuraHolder*aura=nullptr;
unsigned GetMapId(){return map;}bool IsBeingTeleported(){return teleport;}bool GetGroup(){return group;}unsigned GetMaxHealth(){return maxhp;}
float GetHealthPercent(){assert(maxhp);return 100.f*hp/maxhp;}unsigned GetPower(unsigned){return mana;}
int GetMaxNegativeAuraModifier(unsigned){return healing;}
const SpellAuraHolder*GetSpellAuraHolder(unsigned id){assert(id==28531);return aura;}};
struct PlayerbotAI{Player*bot;bool real=false,focus=false;Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsHeal(Player*p){return p->heal;}bool HasStrategy(const char*,BotState){return focus;}};
struct{unsigned criticalHealth=20;}sPlayerbotAIConfig;
struct{bool IsFriendlyTo(Unit*,Unit*u){return u->friendly;}}sServerFacade;
namespace ai{bool NeedsSapphironSelfHealing(PlayerbotAI*);}
__METHOD__
int main(){Player bot;Unit boss;SpellAuraHolder aura{&boss};bot.aura=&aura;PlayerbotAI brain{&bot};auto need=[&](){return ai::NeedsSapphironSelfHealing(&brain);};
#ifdef MANGOSBOT_ZERO
assert(need());bot.hp=20;assert(!need());bot.hp=19;
for(bool* flag:{&bot.world,&bot.alive,&bot.combat,&bot.heal,&bot.group,&boss.world,&boss.alive,&boss.combat}){*flag=false;assert(!need());*flag=true;}
for(bool* flag:{&bot.teleport,&bot.duel,&bot.charm,&brain.real,&brain.focus,&boss.friendly,&boss.charm}){*flag=true;assert(!need());*flag=false;}
bot.maxhp=0;assert(!need());bot.maxhp=100;bot.mana=0;assert(!need());bot.mana=100;
bot.healing=-100;assert(!need());bot.healing=0;bot.map=409;assert(!need());bot.map=533;
boss.instance=2;assert(!need());boss.instance=1;boss.entry=15953;assert(!need());boss.entry=15989;
bot.aura=nullptr;assert(!need());bot.aura=&aura;aura.caster=nullptr;assert(!need());aura.caster=&boss;
assert(need());assert(!ai::NeedsSapphironSelfHealing(nullptr));brain.bot=nullptr;assert(!need());
#else
assert(!need());
#endif
std::cout<<"PASS: critical healer self preservation requires native Sapphiron aura; identity, health, resources, focus and era guards intact\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='sapphiron-self-')as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
