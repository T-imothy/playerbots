"""Execute Moam's phase/resource/class admission through standard spell actions."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/MoamManaControlAction.cpp').read_text()
methods='\n'.join(block(source,name) for name in ('MoamManaControlAction::MoamManaControlAction(', 'bool MoamManaControlAction::isUseful(', 'bool MoamManaControlAction::Execute('))
code=r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <iostream>
using uint64=uint64_t;
enum{POWER_MANA,CLASS_WARLOCK=9,CLASS_PRIEST=5,CLASS_HUNTER=3,CLASS_MAGE=8};
struct Unit{unsigned entry=15340,mana=6250,maxMana=25000,phase=1;bool world=true,alive=true,combat=true,charm=false,energize=false;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}
 unsigned GetEntry(){return entry;}unsigned GetPower(unsigned){return mana;}unsigned GetMaxPower(unsigned){return maxMana;}bool HasAura(unsigned id){assert(id==25685);return energize;}};
struct Group{};
struct Player:Unit{unsigned map=509,cls=CLASS_WARLOCK;bool teleport=false;Group*group=nullptr;
 unsigned GetMapId(){return map;}unsigned getClass(){return cls;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit*u){return u&&u->phase==phase;}Group*GetGroup(){return group;}};
struct PlayerbotAI{Player*bot;Unit*target;bool real=false,heal=false,tank=false,sting=false,baseUseful=true;unsigned casts=0;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsHeal(Player*){return heal;}bool IsTank(Player*){return tank;}
 bool HasAura(std::string name,Unit*u){assert(name=="viper sting"&&u==target);return sting;}};
struct Event{};
struct CastSpellAction{PlayerbotAI*ai;Player*bot;std::string spell;
 CastSpellAction(PlayerbotAI*a,std::string s):ai(a),bot(a->bot),spell(s){}std::string GetSpellName(){return spell;}Unit*GetTarget(){return ai->target;}
 bool isUseful(){return ai->baseUseful;}bool Execute(Event&){++ai->casts;return true;}};
struct MoamManaControlAction:CastSpellAction{MoamManaControlAction(PlayerbotAI*);bool isUseful();bool Execute(Event&);};
__METHODS__
int main(){Group group;Player bot;bot.group=&group;Unit boss;PlayerbotAI ai{&bot,&boss};Event event;
 for(unsigned cls:{CLASS_WARLOCK,CLASS_PRIEST,CLASS_HUNTER,CLASS_MAGE}){
  bot.cls=cls;MoamManaControlAction action(&ai);
  if(cls==CLASS_MAGE){assert(action.GetSpellName().empty()&&!action.isUseful());continue;}
  assert(action.GetSpellName()==(cls==CLASS_WARLOCK?"drain mana":cls==CLASS_PRIEST?"mana burn":"viper sting"));
  assert(action.isUseful());boss.mana=6249;assert(!action.isUseful());boss.mana=6250;
  boss.energize=true;unsigned casts=ai.casts;assert(!action.Execute(event)&&ai.casts==casts);boss.energize=false;
  ai.heal=true;assert(!action.isUseful());ai.heal=false;ai.tank=true;assert(!action.isUseful());ai.tank=false;
  ai.baseUseful=false;assert(!action.isUseful()&&!action.Execute(event));ai.baseUseful=true;
  ai.sting=true;assert(action.isUseful()==(cls!=CLASS_HUNTER));ai.sting=false;
  bot.teleport=true;assert(!action.isUseful());bot.teleport=false;boss.phase=2;assert(!action.isUseful());boss.phase=1;
  boss.entry=1;assert(!action.isUseful());boss.entry=15340;boss.combat=false;assert(!action.isUseful());boss.combat=true;
  boss.maxMana=0;assert(!action.isUseful());boss.maxMana=25000;bot.map=0;assert(!action.isUseful());bot.map=509;
  assert(action.Execute(event)&&ai.casts==casts+1);
 }
 std::cout<<"PASS: Moam class spells, mana threshold, fiend phase, sting preservation and cast rechecks\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-moam-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
