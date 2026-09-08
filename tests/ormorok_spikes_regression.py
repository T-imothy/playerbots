"""Execute native normal/heroic spike-cycle reset and four-direction dispatch."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/nexus/nexus/boss_ormorok.cpp').read_text()
methods='\n'.join(block(source,s).replace(' override','') for s in ('    void Reset()', '    void OnSpellCast('))
dispatch=block(source,'struct CrystalSpikes').replace(' override','')+';'
code=r'''
#include <cassert>
#include <vector>
#include <iostream>
using uint32=unsigned;using uint8=unsigned char;using SpellEffectIndex=unsigned;
enum{EFFECT_INDEX_0,TRIGGERED_OLD_TRIGGERED};
__ENUM__
struct SpellEntry{unsigned Id;};
struct Unit{std::vector<unsigned>casts;void CastSpell(std::nullptr_t,unsigned id,unsigned){casts.push_back(id);}};
struct Spell{Unit*target=nullptr;SpellEntry*m_spellInfo;Unit*GetUnitTarget(){return target;}};
struct SpellScript{};
struct BossAI{void Reset(){}};
unsigned broadcasts=0;void DoBroadcastText(unsigned,Unit*){++broadcasts;}
struct Boss:BossAI{Unit*m_creature=nullptr;uint8 m_uiSpikeCount=0;__METHODS__};
__DISPATCH__
int main(){
 Boss boss;CrystalSpikes script;Unit target;
 for(unsigned spellId:{47958u,57082u,57083u}){
  SpellEntry entry{spellId};Spell spell{&target,&entry};
  for(unsigned cycle=0;cycle<100;++cycle){
   boss.m_uiSpikeCount=20;boss.OnSpellCast(&entry,nullptr);assert(boss.m_uiSpikeCount==0);
   target.casts.clear();script.OnEffectExecute(&spell,EFFECT_INDEX_0);
   assert(target.casts==(spellId==47958?std::vector<unsigned>{47954,47955,47956,47957}:std::vector<unsigned>{57077,57078,57080,57081}));
   script.OnEffectExecute(&spell,1);assert(target.casts.size()==4);
   spell.target=nullptr;script.OnEffectExecute(&spell,EFFECT_INDEX_0);assert(target.casts.size()==4);spell.target=&target;
  }
 }
 assert(broadcasts==300);SpellEntry unrelated{47981};boss.m_uiSpikeCount=19;boss.OnSpellCast(&unrelated,nullptr);assert(boss.m_uiSpikeCount==19);
 boss.Reset();assert(boss.m_uiSpikeCount==0);
 std::cout<<"PASS: 100 repeated normal and both heroic spike cycles, native payload directions, reset and unrelated casts\n";
}
'''.replace('__ENUM__',block(source,'enum\n')+';').replace('__METHODS__',methods).replace('__DISPATCH__',dispatch)
with tempfile.TemporaryDirectory(prefix='ormorok-spikes-') as directory:
    path=Path(directory);(path/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
    subprocess.run([str(path/'test.exe')],cwd=path,check=True)
