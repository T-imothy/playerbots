"""Native head thresholds use the incoming damage and preserve final-stage handling."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
fixture=r'''
#include <cassert>
#include <algorithm>
#include <iostream>
using uint32=unsigned;using DamageEffectType=unsigned;
struct SpellEntry{};struct Unit{};
enum{UNIT_FIELD_FLAGS,UNIT_FLAG_UNINTERACTIBLE};
struct Creature{unsigned health=300,maxHealth=300;bool flag=false;
 unsigned GetHealth(){return health;}unsigned GetMaxHealth(){return maxHealth;}
 bool HasFlag(unsigned,unsigned){return flag;}};
struct ScriptedAI{unsigned finalCalls=0;void DamageTaken(Unit*,unsigned&,unsigned,const SpellEntry*){++finalCalls;}};
struct AI:ScriptedAI{Creature*m_creature;unsigned m_uiHeadPhase=1,rejoins=0;
 void DoRejoinHead(bool forced){assert(!forced);++rejoins;m_creature->flag=true;}
 __METHOD__
};
int main(){
 Creature head;AI ai{};ai.m_creature=&head;unsigned damage=50;ai.DamageTaken(nullptr,damage,0,nullptr);
 assert(damage==50&&ai.m_uiHeadPhase==1&&ai.rejoins==0);head.health-=damage;
 damage=1000;ai.DamageTaken(nullptr,damage,0,nullptr);assert(damage==50&&ai.m_uiHeadPhase==2&&ai.rejoins==1);
 head.health-=damage;assert(head.health==200);damage=1000;ai.DamageTaken(nullptr,damage,0,nullptr);
 assert(damage==0&&ai.m_uiHeadPhase==2&&ai.rejoins==1); // Late projectile while reattached.
 head.flag=false;damage=1000;ai.DamageTaken(nullptr,damage,0,nullptr);assert(damage==100&&ai.m_uiHeadPhase==3&&ai.rejoins==2);
 head.health-=damage;head.flag=false;damage=1000;ai.DamageTaken(nullptr,damage,0,nullptr);
 assert(damage==1000&&ai.finalCalls==1&&ai.rejoins==2); // Native final-stage handler owns completion.
 Creature tiny;tiny.health=tiny.maxHealth=1;AI small{};small.m_creature=&tiny;damage=~0u;
 small.DamageTaken(nullptr,damage,0,nullptr);assert(damage==0&&small.m_uiHeadPhase==2);
 std::cout<<"PASS: Horseman incoming-hit thresholds, overkill boundary, stale projectile and native final phase\n";
}
'''
for era in ('tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/scarlet_monastery/boss_headless_horseman.cpp').read_text()
    actor=block(source,'struct boss_head_of_horsemanAI')
    code=fixture.replace('__METHOD__',block(actor,'void DamageTaken(').replace(' override',''))
    with tempfile.TemporaryDirectory(prefix='horseman-threshold-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
