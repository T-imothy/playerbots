"""Execute the actual encounter aura filter; unrelated native proc rules stay unchanged."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]/'classic'
source=(root/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/naxxramas/boss_loatheb.cpp').read_text()
code=r'''
#include <cassert>
#include <initializer_list>
constexpr unsigned SPELL_EFFECT_HEAL=10,SPELL_EFFECT_DISPEL=38,SPELL_AURA_PERIODIC_HEAL=8;
struct SpellEntry{unsigned SpellFamilyName=6,effect=10,aura=0;};
bool IsSpellHaveEffect(const SpellEntry*s,unsigned e){return s->effect==e;}
bool IsSpellHaveAura(const SpellEntry*s,unsigned a){return s->aura==a;}
struct Unit{bool blocked=false;bool HasOverrideScript(unsigned id){assert(id==4327);return blocked;}};
struct Aura{Unit*target=nullptr;SpellEntry info;Unit*GetTarget(){return target;}const SpellEntry*GetSpellProto(){return &info;}};
struct ProcExecutionData{const SpellEntry*spellInfo=nullptr;};
struct AuraScript{virtual bool OnCheckProc(Aura*,ProcExecutionData&)const{return true;}};
__BODY__;
int main(){CorruptedMindCooldown script;Unit caster;Aura aura{&caster};SpellEntry spell;ProcExecutionData data{&spell};
 for(unsigned family:{6u,7u,10u,11u}){
  spell.SpellFamilyName=aura.info.SpellFamilyName=family;
  spell.effect=10;spell.aura=0;assert(script.OnCheckProc(&aura,data));
  spell.effect=38;assert(script.OnCheckProc(&aura,data));
  spell.effect=6;spell.aura=8;assert(script.OnCheckProc(&aura,data));
  caster.blocked=true;assert(!script.OnCheckProc(&aura,data));caster.blocked=false;
  spell.effect=2;spell.aura=0;assert(!script.OnCheckProc(&aura,data)); // Smite / Mind Blast.
  spell.effect=6;spell.aura=3;assert(!script.OnCheckProc(&aura,data)); // Shadow Word: Pain.
  spell.aura=69;assert(!script.OnCheckProc(&aura,data)); // Absorb shield.
  spell.effect=10;spell.SpellFamilyName=0;assert(!script.OnCheckProc(&aura,data)); // Consumable.
 }
 data.spellInfo=nullptr;assert(!script.OnCheckProc(&aura,data));data.spellInfo=&spell;
 aura.target=nullptr;assert(!script.OnCheckProc(&aura,data));assert(!script.OnCheckProc(nullptr,data));
}
'''.replace('__BODY__',block(source,'struct CorruptedMindCooldown : public AuraScript'))
assert 'RegisterSpellScript<CorruptedMindCooldown>("spell_loatheb_corrupted_mind_cooldown")' in source
sql=(root/'sql/scriptdev2/spell.sql').read_text()
for spell in (29185,29194,29196,29198):assert f"({spell},'spell_loatheb_corrupted_mind_cooldown')" in sql
with tempfile.TemporaryDirectory(prefix='loatheb-native-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],check=True,cwd=p)
print('PASS: actual Loatheb proc filter accepts class heals/dispels, rejects damage, shields, lockout renewal and invalid events')
