"""Run Wrath's native Soul Leech proc against rank and callback-lifetime cases."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
native=root.parent/'mangos-wotlk-behavior/src/game/Spells/Scripts/Scripting/ClassScripts/Warlock.cpp'
method=block(native.read_text(),'struct SoulLeech')+';'
code=r'''
#include <cassert>
#include <functional>
#include <iostream>
#include <vector>
using uint32=unsigned;using int32=int;
enum{TRIGGERED_IGNORE_GCD=1,TRIGGERED_IGNORE_CURRENT_CASTED_SPELL=2,TRIGGERED_HIDE_CAST_IN_COMBAT_LOG=4,EFFECT_INDEX_1=1};
enum SpellAuraProcResult{SPELL_AURA_PROC_OK};
struct Unit;
struct Aura{unsigned id=0;int amount=0;Unit*target=nullptr;bool valid=true;
 unsigned GetId(){assert(valid);return id;}int GetAmount(){assert(valid);return amount;}Unit*GetTarget(){assert(valid);return target;}};
struct ProcExecutionData{unsigned damage=0;};
struct Unit{bool player=true;std::vector<unsigned>casts;std::vector<int>heals;std::function<void()>onHeal,onMana;
 bool IsPlayer(){return player;}
 void CastCustomSpell(Unit*u,unsigned id,int*amount,int*two,int*three,unsigned flags){
  assert(!u&&id==30294&&amount&&!two&&!three&&flags==7);heals.push_back(*amount);if(onHeal)onHeal();}
 void CastSpell(Unit*u,unsigned id,unsigned flags){assert(!u&&id&&flags==7);casts.push_back(id);if(onMana)onMana();}
};
struct Player:Unit{Aura*improved=nullptr;unsigned lookups=0;
 Aura*GetKnownTalentRankAuraById(unsigned talent,unsigned effect){assert(talent==1889&&effect==EFFECT_INDEX_1);++lookups;return improved;}};
struct AuraScript{virtual SpellAuraProcResult OnProc(Aura*,ProcExecutionData&)const{return SPELL_AURA_PROC_OK;}};
bool rolled=true;std::vector<int>chances;
bool roll_chance_i(int chance){chances.push_back(chance);return rolled;}
__METHOD__
int main(){
 SoulLeech proc;ProcExecutionData data{1000};
 for(unsigned soulRank:{30293u,30295u,30296u})for(unsigned improvedRank:{54117u,54118u})for(bool replenish:{false,true}){
  Player target;Aura base{soulRank,30,&target},improved{improvedRank,improvedRank==54117?50:100,&target};
  target.improved=&improved;rolled=replenish;chances.clear();
  assert(proc.OnProc(&base,data)==SPELL_AURA_PROC_OK);
  assert(target.heals==std::vector<int>{300}&&target.lookups==1);
  const unsigned self=improvedRank==54117?54300:59117,pet=improvedRank==54117?54607:59118;
  std::vector<unsigned>expected{self,pet};if(replenish)expected.push_back(57669);
  assert(target.casts==expected&&chances==std::vector<int>{improved.amount});
 }
 // Base Soul Leech is unchanged without the extra talent or on nonplayers.
 {Player target;Aura base{30296,20,&target};chances.clear();proc.OnProc(&base,data);
  assert(target.heals==std::vector<int>{200}&&target.casts.empty()&&chances.empty());
  target.player=false;target.lookups=0;proc.OnProc(&base,data);assert(target.lookups==0&&target.casts.empty());}
 // Unexpected talent rank must never dispatch spell zero.
 {Player target;Aura base{30296,20,&target},improved{99999,100,&target};target.improved=&improved;chances.clear();
  proc.OnProc(&base,data);assert(target.heals==std::vector<int>{200}&&target.casts.empty()&&chances.empty());}
 // Triggered casts may alter aura state. Capture rank/chance before those calls.
 {Player target;Aura base{30296,20,&target},improved{54118,100,&target};target.improved=&improved;
  target.onHeal=[&](){base.valid=false;};target.onMana=[&](){improved.valid=false;};chances.clear();rolled=true;
  proc.OnProc(&base,data);assert((target.casts==std::vector<unsigned>{59117,59118,57669}));
  assert(chances==std::vector<int>{100});}
 std::cout<<"PASS: native Soul Leech rank-specific mana returns, replenishment and aura callback lifetime\n";
}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mantech-soul-leech-') as directory:
    tmp=Path(directory);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
