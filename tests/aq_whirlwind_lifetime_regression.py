"""Execute native AQ whirlwind ticks after the parent aura/effect disappears."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;
enum SpellEffectIndex{EFFECT_INDEX_0,EFFECT_INDEX_1};
enum{SPELL_OTHER_WHIRLWIND_TRIGGER=26686,ATTACKING_TARGET_RANDOM,SELECT_FLAG_PLAYER};
unsigned randomResult=0;unsigned urand(unsigned,unsigned){return randomResult;}
struct Aura{unsigned ticks=1,maxTicks=5;unsigned GetAuraTicks(){return ticks;}unsigned GetAuraMaxTicks(){return maxTicks;}};
struct SpellEntry{unsigned Id;};
struct Unit{virtual ~Unit()=default;bool canThreat=true;Aura*periodic=nullptr;
 struct Threat{bool empty=false;unsigned resets=0,adds=0;bool isThreatListEmpty(){return empty;}void modifyAllThreatPercent(int n){assert(n==-100);++resets;}void addThreat(Unit*,float){++adds;}}threat;
 bool CanHaveThreatList(){return canThreat;}Threat&getThreatManager(){return threat;}
 Aura*GetAura(unsigned id,SpellEffectIndex eff){assert(id==26083&&eff==EFFECT_INDEX_0);return periodic;}};
struct Creature:Unit{Unit*target=nullptr;Unit*SelectAttackingTarget(int,int,void*,int){return target;}};
struct Spell{Unit*caster;SpellEntry*m_spellInfo;SpellEntry*parent;Unit*GetCaster(){return caster;}SpellEntry*GetTriggeredByAuraSpellInfo(){return parent;}};
struct SpellScript{virtual void OnEffectExecute(Spell*,SpellEffectIndex)const{}};
__SCRIPT__;
int main(){Creature caster;Unit target;Aura aura;SpellEntry damage{26084},parent{26083};Spell spell{&caster,&damage,&parent};AQWhirlwind script;
 script.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(caster.threat.resets==0); // Parent/effect removed before queued payload executes.
 caster.periodic=&aura;caster.target=&target;script.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(caster.threat.resets==1&&caster.threat.adds==1);
 caster.target=nullptr;script.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(caster.threat.resets==2&&caster.threat.adds==1);
 aura.ticks=aura.maxTicks;caster.target=&target;script.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(caster.threat.resets==3&&caster.threat.adds==1);
 script.OnEffectExecute(&spell,EFFECT_INDEX_0);assert(caster.threat.resets==3);
 spell.parent=nullptr;script.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(caster.threat.resets==3);spell.parent=&parent;
 caster.threat.empty=true;script.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(caster.threat.resets==3);caster.threat.empty=false;
 aura.ticks=1;damage.Id=SPELL_OTHER_WHIRLWIND_TRIGGER;randomResult=1;script.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(caster.threat.resets==3);
 randomResult=0;script.OnEffectExecute(&spell,EFFECT_INDEX_1);assert(caster.threat.resets==4&&caster.threat.adds==2);
 std::cout<<"PASS: AQ whirlwind missing aura/effect, final tick, empty target and guard randomization\n";
}
'''
for era in ('classic','tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/kalimdor/temple_of_ahnqiraj/boss_sartura.cpp').read_text()
    code=fixture.replace('__SCRIPT__',block(source,'struct AQWhirlwind'))
    with tempfile.TemporaryDirectory(prefix='mantech-aq-whirlwind-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
