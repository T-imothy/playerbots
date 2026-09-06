"""Exercise the real non-damage immunity fold, not a copied policy implementation."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/PlayerbotAI.cpp').read_text(),
             'bool PlayerbotAI::CanCastSpell(uint32 spellid, Unit* target,')
fold=block(method,'if (!damage)')
code=r'''
#include <cassert>
#include <iostream>
using int32=int;
enum SpellEffectIndex {EFFECT_INDEX_0=0,EFFECT_INDEX_1=1,EFFECT_INDEX_2=2};
enum {SPELL_FAILED_IMMUNE=1};
struct SpellEntry {unsigned Effect[3]={6,0,0};};
struct Unit {bool effects[3]={true,false,false};unsigned checks=0;
 bool IsImmuneToSpellEffect(const SpellEntry*,SpellEffectIndex i,bool){++checks;return effects[i];}};
bool useful(Unit* target,const SpellEntry* spellInfo,bool immune,int* checkResult){
 bool damage=false;
 unsigned checkedEffectMask=7;
 __FOLD__
 return true;
}
int main(){
 Unit target;SpellEntry spell;int result=0;
 assert(!useful(&target,&spell,false,&result)&&result==SPELL_FAILED_IMMUNE); // BEFORE FIX: empty final slot overwrites immunity
 assert(!useful(&target,&spell,false,nullptr));
 spell.Effect[1]=6;assert(useful(&target,&spell,false,nullptr)); // a real second effect can still work
 target.effects[1]=true;assert(!useful(&target,&spell,false,nullptr));
 spell.Effect[2]=6;assert(useful(&target,&spell,false,nullptr));target.effects[2]=true;
 assert(!useful(&target,&spell,false,nullptr));
 unsigned checks=target.checks;assert(!useful(&target,&spell,true,nullptr)&&checks==target.checks);
 for(unsigned populated=0;populated<3;++populated){
  for(unsigned i=0;i<3;++i){spell.Effect[i]=i==populated?6:0;target.effects[i]=i==populated;}
  assert(!useful(&target,&spell,false,nullptr));target.effects[populated]=false;
  assert(useful(&target,&spell,false,nullptr));
 }
 for(unsigned i=0;i<3;++i)spell.Effect[i]=0;
 assert(useful(&target,&spell,false,nullptr)); // preserve empty/script-only handling
 std::cout<<"PASS: actual non-damage fold ignores empty slots, preserves usable partial effects and native immunity\n";
}
'''.replace('__FOLD__',fold)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-nondamage-immunity-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}',
                        'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
