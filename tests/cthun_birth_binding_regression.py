"""Execute native C'Thun summon -> Birth -> portal/rupture chains with era bindings."""
from pathlib import Path
import subprocess,tempfile,re
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
classes=['BirthTentacles','SummonHookTentacle','SummonGiantHookTentacles','SummonEyeTentacle','SummonGiantEyeTentacles'];bodies=[]
for era in ['classic','tbc','wotlk']:
 base=root/f'mangos-{era}-behavior';s=(base/'src/game/AI/ScriptDevAI/scripts/kalimdor/temple_of_ahnqiraj/boss_cthun.cpp').read_text()
 bodies.append('\n'.join(block(s,'struct '+name).replace(' override','')+';' for name in classes))
 sql=(base/'sql/scriptdev2/spell.sql').read_text()
 for id,name in [(26586,'birth_tentacles'),(26140,'summon_hook_tentacle'),(26216,'summon_giant_hook_tentacles'),(26150,'summon_eye_tentacle'),(26768,'summon_giant_eye_tentacles')]:assert f"({id},'spell_{name}')" in sql
assert bodies[0]==bodies[1]==bodies[2]
code=r"""
#include <cassert>
#include <vector>
#include <iostream>
using SpellEffectIndex=unsigned;
enum{NPC_EYE_TENTACLE=15726,NPC_CLAW_TENTACLE=15725,NPC_GIANT_CLAW_TENTACLE=15728,NPC_GIANT_EYE_TENTACLE=15334,SPELL_SUMMON_PORTAL=26396,SPELL_GROUND_RUPTURE=26139,SPELL_SUMMON_GIANT_PORTAL=26477,SPELL_BIRTH_TENTACLE=26586,TRIGGERED_IGNORE_CURRENT_CASTED_SPELL=1};
struct Unit{bool creature=true;unsigned entry;std::vector<unsigned>casts;bool IsCreature(){return creature;}unsigned GetEntry(){return entry;}void CastSpell(Unit*,unsigned,unsigned);};
struct Creature:Unit{};struct Spell{Unit*caster;Unit*GetCaster(){return caster;}};struct SpellScript{};
__METHODS__
void Unit::CastSpell(Unit*,unsigned id,unsigned){casts.push_back(id);assert(casts.size()<=3);if(id==SPELL_BIRTH_TENTACLE){Spell spell{this};BirthTentacles birth;birth.OnEffectExecute(&spell,0);}}
int main(){
 SummonHookTentacle claw;SummonEyeTentacle eye;SummonGiantHookTentacles giantClaw;SummonGiantEyeTentacles giantEye;
 for(unsigned entry:{NPC_EYE_TENTACLE,NPC_CLAW_TENTACLE,NPC_GIANT_CLAW_TENTACLE,NPC_GIANT_EYE_TENTACLE}){
  Creature summon;summon.entry=entry;
  if(entry==NPC_EYE_TENTACLE)eye.OnSummon(nullptr,&summon);else if(entry==NPC_CLAW_TENTACLE)claw.OnSummon(nullptr,&summon);else if(entry==NPC_GIANT_CLAW_TENTACLE)giantClaw.OnSummon(nullptr,&summon);else giantEye.OnSummon(nullptr,&summon);
  if(entry==NPC_EYE_TENTACLE||entry==NPC_CLAW_TENTACLE)assert((summon.casts==std::vector<unsigned>{26586,26396,26139}));
  else assert((summon.casts==std::vector<unsigned>{26586,26477})); // Giant rupture remains owned by its existing AI timer.
 }
 Unit player;player.creature=false;player.entry=NPC_EYE_TENTACLE;Spell spell{&player};BirthTentacles birth;birth.OnEffectExecute(&spell,0);assert(player.casts.empty());
 Creature other;other.entry=1;spell.caster=&other;birth.OnEffectExecute(&spell,0);assert(other.casts.empty());
 std::cout<<"PASS: native small/giant spawn chains, one portal, correct rupture ownership and unrelated-unit exclusions; all era bindings and handlers match\n";
}
""".replace('__METHODS__',bodies[0])
with tempfile.TemporaryDirectory(prefix='cthun-birth-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
