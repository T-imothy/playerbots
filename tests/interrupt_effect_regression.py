"""Actual interrupt predicate: unrelated immune effects must not veto a valid interrupt."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/PlayerbotAI.cpp').read_text(), 'bool PlayerbotAI::IsInterruptableSpellCasting(')
code=r'''
#include <cassert>
#include <iostream>
#include <string>
using uint32=unsigned;using uint8=unsigned char;
enum SpellEffectIndex {EFFECT_INDEX_0=0,EFFECT_INDEX_1=1,EFFECT_INDEX_2=2,MAX_EFFECT_INDEX=3};
enum {SPELL_EFFECT_INTERRUPT_CAST=68,SPELL_EFFECT_APPLY_AURA=6,SPELL_AURA_MOD_SILENCE=27,SPELL_AURA_MOD_STUN=12};
struct SpellEntry {unsigned Effect[3]={68,6,0},EffectApplyAuraName[3]={0,27,0};};
struct Unit {
 bool world=true,alive=true,casting=true,interruptible=true,teleport=false;
 unsigned map=1,instance=1,phase=1;bool immuneSpell[3]={false,false,false},immuneEffect[3]={false,false,false};
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit* t){return world&&t->world&&map==t->map&&instance==t->instance
#ifndef MANGOSBOT_ZERO
  &&phase==t->phase
#endif
 ;}
 bool IsNonMeleeSpellCasted(bool){return casting;}bool IsInterruptible(){return interruptible;}
 bool IsImmuneToSpell(const SpellEntry*,bool,unsigned mask,Unit*){
  for(unsigned i=0;i<3;++i)if((mask&(1u<<i))&&immuneSpell[i])return true;return false;}
 bool IsImmuneToSpellEffect(const SpellEntry*,SpellEffectIndex i,bool){return immuneEffect[i];}
};
struct {SpellEntry entry;bool exists=true;const SpellEntry* LookupSpellInfo(unsigned){return exists?&entry:nullptr;}} sServerFacade;
struct IdValue {unsigned id=1;unsigned Get(){return id;}};
struct Context {IdValue value;template<class T>IdValue* GetValue(std::string,std::string){return &value;}};
struct PlayerbotAI {Unit* bot;Context* aiObjectContext;bool IsInterruptableSpellCasting(Unit*,std::string);};
__METHOD__
int main(){
 Unit bot,target;Context ctx;PlayerbotAI ai{&bot,&ctx};
 target.immuneEffect[1]=true;
 assert(ai.IsInterruptableSpellCasting(&target,"fixture")); // BEFORE FIX: immune bonus silence vetoes a valid kick
 target.immuneEffect[0]=true;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));
 target.immuneEffect[1]=false;assert(ai.IsInterruptableSpellCasting(&target,"fixture")); // silence still works
 target.immuneSpell[1]=true;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));
 target.immuneEffect[0]=false;assert(ai.IsInterruptableSpellCasting(&target,"fixture"));
 target.immuneEffect[2]=true;assert(ai.IsInterruptableSpellCasting(&target,"fixture")); // unused effect ignored
 sServerFacade.entry.Effect[0]=2;assert(!ai.IsInterruptableSpellCasting(&target,"fixture")); // damage isn't an interrupt
 target.immuneSpell[1]=false;sServerFacade.entry.EffectApplyAuraName[1]=SPELL_AURA_MOD_STUN;
 assert(ai.IsInterruptableSpellCasting(&target,"fixture"));
 target.interruptible=false;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));target.interruptible=true;
 target.casting=false;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));target.casting=true;
 ctx.value.id=0;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));ctx.value.id=1;
 sServerFacade.exists=false;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));sServerFacade.exists=true;
 assert(!ai.IsInterruptableSpellCasting(nullptr,"fixture"));
 target.world=false;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));target.world=true;
 target.alive=false;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));target.alive=true;
 target.instance=2;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));target.instance=1;
#ifndef MANGOSBOT_ZERO
 target.phase=2;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));target.phase=1;
#endif
 bot.teleport=true;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));bot.teleport=false;
 bot.world=false;assert(!ai.IsInterruptableSpellCasting(&target,"fixture"));
 std::cout<<"PASS: actual native per-effect interrupt immunity, live cast and lifecycle checks\n";
}
'''.replace('__METHOD__',method)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-interrupt-effects-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}',
                        'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
