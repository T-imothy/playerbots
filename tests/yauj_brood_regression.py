"""Run native Yauj summon dispatch without granting threat to the dying boss."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <cassert>
#include <iostream>
enum{NPC_YAUJ_BROOD=15621,ATTACKING_TARGET_RANDOM,SELECT_FLAG_PLAYER};
struct Unit{};
struct ActorAI{unsigned attacks=0;Unit* victim=nullptr;void AttackStart(Unit*u){++attacks;victim=u;}};
struct Creature:Unit{unsigned entry=NPC_YAUJ_BROOD,zone=0,threatCalls=0;float threat=0;Unit* target=nullptr;Unit*threatTarget=nullptr;ActorAI ai;
 unsigned GetEntry(){return entry;}void SetInCombatWithZone(){++zone;}
 Unit*SelectAttackingTarget(int,int,void*,int){return target;}
 void AddThreat(Unit*u,float n){++threatCalls;threat+=n;threatTarget=u;}ActorAI*AI(){return &ai;}};
struct Base{virtual void JustSummoned(Creature*){}};
struct Yauj:Base{Creature*m_creature;unsigned attacks=0;void AttackStart(Unit*){++attacks;}__METHOD__};
int main(){Creature boss,brood;Unit player;boss.target=&player;Yauj ai;ai.m_creature=&boss;
 ai.JustSummoned(&brood);assert(brood.zone==1&&brood.threatCalls==1&&brood.threat==1000000.f);
 assert(brood.threatTarget==&player&&brood.ai.attacks==1&&brood.ai.victim==&player);
 assert(boss.threatCalls==0&&ai.attacks==0);
 boss.target=nullptr;Creature depleted;ai.JustSummoned(&depleted);
 assert(depleted.zone==1&&depleted.threatCalls==0&&depleted.ai.attacks==0);
 Creature unrelated;unrelated.entry=42;boss.target=&player;ai.JustSummoned(&unrelated);
 assert(unrelated.zone==0&&unrelated.threatCalls==0&&unrelated.ai.attacks==0);
 std::cout<<"PASS: native Yauj brood owns threat/attack, no boss reactivation, empty target and unrelated spawn\n";
}
'''
for era in ('classic','tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/kalimdor/temple_of_ahnqiraj/boss_bug_trio.cpp').read_text()
    actor=block(source,'struct boss_yaujAI')
    code=fixture.replace('__METHOD__',block(actor,'void JustSummoned('))
    with tempfile.TemporaryDirectory(prefix='mantech-yauj-brood-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
