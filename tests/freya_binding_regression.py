"""Run native Freya wave recovery through the bound spell handler, not direct events."""
from pathlib import Path
import ast,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'tests/freya_felmyst_wave_recovery_regression.py').read_text())
code=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='freya' for t in n.targets))
core=root.parent/'mangos-wotlk-behavior'
s=(core/'src/game/AI/ScriptDevAI/scripts/northrend/ulduar/ulduar/boss_freya.cpp').read_text();actor=block(s,'struct boss_freyaAI');update=block(actor,'void UpdateAI(')
code=code.replace('struct Unit{};', 'enum{NPC_FREYA=32906};using SpellEffectIndex=unsigned;struct AI;struct Unit{::AI*ai=nullptr;unsigned entry=NPC_FREYA;unsigned GetEntry(){return entry;}::AI*AI(){return ai;}};')
code=code.replace(' __METHOD__', ' void SendAIEvent(unsigned event,Unit*sender,Unit*target){ReceiveAIEvent(event,sender,target,0);}\n __METHOD__')
code=code.replace('int main(){', 'struct SpellScript{};struct Spell{Unit*caster,*target;Unit*GetCaster(){return caster;}Unit*GetUnitTarget(){return target;}};\n'+block(s,'struct SummonAlliesOfNature').replace(' override','')+';\nint main(){')
code=code.replace('AI ai{&boss};ai.result=CAST_FAIL;ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);', 'AI ai{&boss};boss.ai=&ai;Spell spell{&boss,&boss};SummonAlliesOfNature summon;ai.result=CAST_FAIL;summon.OnEffectExecute(&spell,0);')
code=code.replace('for(unsigned i=1;i<6;++i)ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);', 'for(unsigned i=1;i<6;++i)summon.OnEffectExecute(&spell,0);')
code=code.replace('for(unsigned extra=0;extra<10;++extra)ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);', 'for(unsigned extra=0;extra<10;++extra)summon.OnEffectExecute(&spell,0);')
code=code.replace('__METHOD__',block(actor,'void ReceiveAIEvent(').replace(' override','')).replace('__RETRY__',block(update,'if (m_uiAllyRetryTimer)'))
sql=(core/'sql/scriptdev2/spell.sql').read_text();assert all(f"({i},'spell_summon_allies_of_nature')" in sql for i in (62678,62873))
with tempfile.TemporaryDirectory(prefix='freya-bindings-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
print('PASS: both native spell bindings now enter the tested six-wave/retry handler')
