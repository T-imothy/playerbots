"""Execute Arlokk's actual spell handler and AI event with its native effect layout."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
variants=[]
for era in ['classic','tbc','wotlk']:
 core=root/f'mangos-{era}-behavior'
 s=(core/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/zulgurub/boss_arlokk.cpp').read_text()
 variants.append((block(s,'struct ArlokkVanish'),block(s,'    void ReceiveAIEvent(')))
 sql=(core/'sql/scriptdev2/spell.sql').read_text();assert "(24223,'spell_arlokk_vanish')" in sql and "(24228,'spell_arlokk_vanish')" not in sql
assert variants[0]==variants[1]==variants[2], 'Review expansion-specific handlers before sharing a fixture'
handler,event=variants[0]
code=r"""
#include <cassert>
#include <vector>
#include <map>
#include <iostream>
using uint32=unsigned;using SpellEffectIndex=unsigned;using AIEventType=unsigned;
enum{EFFECT_INDEX_1=1,TRIGGERED_OLD_TRIGGERED=2,AI_EVENT_CUSTOM_A=3,ARLOKK_INVIS_SELECT=4,ARLOKK_INVIS_TIMER=5,SPELL_VANISH_TELEPORT=24228,SPELL_SUPER_INVIS=24235};
struct Unit;
struct BossAI{unsigned resets=0;bool scripted=false,melee=true;std::map<unsigned,unsigned>timers;
 void DoResetThreat(){++resets;}void SetCombatScriptStatus(bool b){scripted=b;}void SetMeleeEnabled(bool b){melee=b;}void ResetTimer(unsigned id,unsigned ms){timers[id]=ms;}
 __EVENT__
 void SendAIEvent(unsigned event,Unit*sender,Unit*invoker){ReceiveAIEvent(event,sender,invoker,0);}
};
struct Unit{BossAI*ai;std::vector<unsigned>casts;BossAI*AI(){return ai;}void CastSpell(Unit*,unsigned id,unsigned){casts.push_back(id);assert(casts.size()<=2);}};
struct Spell{Unit*caster;Unit*GetCaster(){return caster;}};struct SpellScript{};
__HANDLER__;
int main(){
 BossAI boss;Unit caster{&boss};Spell spell{&caster};ArlokkVanish vanish;
 // 24223: aura in effect 0, script effect in 1, dummy in 2.
 vanish.OnEffectExecute(&spell,0);assert(caster.casts.empty()&&!boss.scripted);
 vanish.OnEffectExecute(&spell,1);vanish.OnEffectExecute(&spell,2);
 assert((caster.casts==std::vector<unsigned>{24228,24235}));assert(boss.scripted&&!boss.melee&&boss.resets==1);
 assert(boss.timers[ARLOKK_INVIS_SELECT]==10000&&boss.timers[ARLOKK_INVIS_TIMER]==50000);
 // Old binding targeted 24228, whose only effect is index 0: no phase event.
 BossAI old;Unit payload{&old};Spell oldSpell{&payload};vanish.OnEffectExecute(&oldSpell,0);assert(payload.casts.empty()&&!old.scripted);
 std::cout<<"PASS: corrected Vanish dispatch triggers teleport/invisibility/threat reset/timers; old payload binding reproduces missing callback; all era handlers identical\n";
}
""".replace('__EVENT__',event.replace(' override','')).replace('__HANDLER__',handler.replace(' override',''))
with tempfile.TemporaryDirectory(prefix='arlokk-vanish-') as directory:
 path=Path(directory);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
