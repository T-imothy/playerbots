"""Execute actual Valithria assignment, native Dream stacks and lifecycle guards."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/RaidHealingObjective.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('bool ai::NeedsRaidObjectiveHealing(', 'Unit* ai::FindRaidHealingObjective('))
code=r'''
#include <cassert>
#include <list>
#include <map>
#include <string>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;
enum{POWER_MANA};enum class BotState{BOT_STATE_COMBAT};
struct SpellAuraHolder{unsigned stacks=0;unsigned GetStackAmount()const{return stacks;}};
struct Unit{unsigned guid=0,map=631,phase=1,entry=0,hp=50,maxhp=100;float x=0;
 bool alive=true,world=true,combat=true,charmed=false,friendly=true;
 unsigned GetObjectGuid(){return guid;}unsigned GetMapId(){return map;}unsigned GetEntry(){return entry;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetHealth(){return hp;}unsigned GetMaxHealth(){return maxhp;}
 bool IsInMap(Unit*u){return u&&u->world&&world&&u->map==map&&u->phase==phase;}
 float GetDistance(Unit*u){return std::abs(x-u->x);}};
struct PlayerbotAI;struct Group;
struct Player:Unit{bool teleport=false,healer=true;unsigned mana=100;Group*group=nullptr;PlayerbotAI*ai=nullptr;std::map<unsigned,SpellAuraHolder>auras;
 bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}unsigned GetPower(unsigned){return mana;}
 PlayerbotAI*GetPlayerbotAI(){return ai;}const SpellAuraHolder*GetSpellAuraHolder(unsigned id){auto i=auras.find(id);return i==auras.end()?nullptr:&i->second;}};
struct GroupReference{Player*player;GroupReference*nextRef=nullptr;Player*getSource(){return player;}GroupReference*next(){return nextRef;}};
struct Group{GroupReference*first;GroupReference*GetFirstMember(){return first;}};
struct Stored{std::list<ObjectGuid>items;std::list<ObjectGuid>Get(){return items;}};
struct Context{Stored near;template<class T>Stored*GetValue(const char*,const char*){return &near;}};
struct PlayerbotAI{Player*bot;bool human=false,focus=false;Context context;std::map<unsigned,Unit*>units;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return human;}bool IsHeal(Player*p){return p->healer;}
 bool HasStrategy(std::string s,BotState){assert(s=="focus heal targets");return focus;}
 float GetRange(std::string s){assert(s=="heal");return 40;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}};
struct Facade{bool IsFriendlyTo(Unit*,Unit*u){return u->friendly;}}sServerFacade;
namespace ai{bool NeedsRaidObjectiveHealing(Unit*);Unit*FindRaidHealingObjective(PlayerbotAI*);}
__METHODS__
int main(){
 Player bot,reserve;bot.guid=2;reserve.guid=1;GroupReference second{&reserve},first{&bot,&second};Group group{&first};
 bot.group=reserve.group=&group;PlayerbotAI ai{&bot},other{&reserve};bot.ai=&ai;reserve.ai=&other;
 Unit dragon;dragon.guid=3;dragon.entry=36789;ai.units={{3,&dragon}};ai.context.near.items={3};
#ifdef MANGOSBOT_TWO
 assert(ai::FindRaidHealingObjective(&ai)==&dragon);
 bot.guid=0;assert(!ai::FindRaidHealingObjective(&ai));bot.guid=2;
 reserve.auras[70873]={5};assert(!ai::FindRaidHealingObjective(&ai));
 bot.auras[71941]={6};assert(ai::FindRaidHealingObjective(&ai)==&dragon);
 bot.auras.clear();reserve.auras.clear();
 reserve.alive=false;assert(ai::FindRaidHealingObjective(&ai)==&dragon);reserve.alive=true; // Re-elect after death.
 reserve.phase=16;assert(ai::FindRaidHealingObjective(&ai)==&dragon);reserve.phase=1;
 ai.focus=true;assert(!ai::FindRaidHealingObjective(&ai));ai.focus=false;
 ai.human=true;assert(!ai::FindRaidHealingObjective(&ai));ai.human=false;
 bot.healer=false;assert(!ai::FindRaidHealingObjective(&ai));bot.healer=true;
 bot.mana=0;assert(!ai::FindRaidHealingObjective(&ai));bot.mana=100;
 bot.teleport=true;assert(!ai::FindRaidHealingObjective(&ai));bot.teleport=false;
 bot.combat=false;assert(!ai::FindRaidHealingObjective(&ai));bot.combat=true;
 dragon.combat=false;assert(!ai::FindRaidHealingObjective(&ai));dragon.combat=true; // No automated pull by healing.
 dragon.hp=100;assert(!ai::FindRaidHealingObjective(&ai));dragon.hp=99;assert(ai::FindRaidHealingObjective(&ai)==&dragon);
 dragon.phase=16;assert(!ai::FindRaidHealingObjective(&ai));dragon.phase=1;
 dragon.friendly=false;assert(!ai::FindRaidHealingObjective(&ai));dragon.friendly=true;
 dragon.x=41;assert(!ai::FindRaidHealingObjective(&ai));dragon.x=0;
 dragon.charmed=true;assert(!ai::FindRaidHealingObjective(&ai));dragon.charmed=false;
 Unit duplicate=dragon;duplicate.guid=4;ai.units[4]=&duplicate;ai.context.near.items.push_back(4);
 assert(!ai::FindRaidHealingObjective(&ai));ai.context.near.items.pop_back();
 bot.map=632;assert(!ai::FindRaidHealingObjective(&ai));
#else
 assert(!ai::FindRaidHealingObjective(&ai)&&!ai::NeedsRaidObjectiveHealing(&dragon));
#endif
 std::cout<<"PASS: native-friendly raid objective, healer reservation, Dream stacks, focus/role/phase/reset/full-health gates\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-raid-healing-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],check=True)
