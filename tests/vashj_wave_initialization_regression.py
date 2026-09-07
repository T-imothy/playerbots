"""Native wave callbacks must tolerate the move to the phase-two center."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root = Path(__file__).resolve().parents[1]
for era in ('tbc', 'wotlk'):
    source = (root.parent / f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland/coilfang_reservoir/serpent_shrine/boss_lady_vashj.cpp').read_text()
    methods = '\n'.join(block(source, 'void ' + name + '(') for name in ('HandleCoilfangElite', 'HandleCoilfangStrider', 'HandleTaintedElemental'))
    validation = block(source, 'if (m_triggerGuidsNorth.empty()')
    code = r'''
#include <cassert>
#include <map>
#include <stdexcept>
#include <vector>
using uint8=unsigned char; using uint32=unsigned;
enum{SPELL_WAVE_B=1,SPELL_WAVE_C,SPELL_WAVE_D,TRIGGERED_OLD_TRIGGERED,VASHJ_COILFANG_ELITE,VASHJ_COILFANG_STRIDER,VASHJ_TAINTED_ELEMENTAL};
unsigned urand(unsigned low,unsigned high){if(high>10000||low>high)throw std::logic_error("wave selected before triggers initialized");return low;}
struct Creature;struct Map{Creature*trigger=nullptr;Creature*GetCreature(unsigned){return trigger;}};
struct Creature{Map*map;std::vector<unsigned>casts;Map*GetMap(){return map;}void CastSpell(Creature*target,unsigned spell,unsigned){assert(target);casts.push_back(spell);}};
void script_error_log(const char*){}
struct AI{Creature*m_creature;std::vector<unsigned>m_triggerGuidsAll;std::map<unsigned,unsigned>timers;
 std::vector<unsigned>m_triggerGuidsNorth,m_triggerGuidsSouth,m_triggerGuidsWest,m_triggerGuidsEast;
 bool evaded=false;void EnterEvadeMode(){evaded=true;}void Validate(){__VALIDATE__}
 void ResetTimer(unsigned timer,unsigned delay){timers[timer]=delay;}
 __METHODS__
};
int main(){Map map;Creature boss{&map},trigger{&map};AI ai{&boss};
 ai.HandleCoilfangElite();ai.HandleCoilfangStrider();ai.HandleTaintedElemental();
 assert(boss.casts.empty());assert(ai.timers.size()==3);for(auto timer:ai.timers)assert(timer.second==1000);
 map.trigger=&trigger;ai.m_triggerGuidsAll={1};ai.timers.clear();
 ai.HandleCoilfangElite();ai.HandleCoilfangStrider();ai.HandleTaintedElemental();
 assert((boss.casts==std::vector<unsigned>{SPELL_WAVE_B,SPELL_WAVE_C,SPELL_WAVE_D}));
 assert(ai.timers[VASHJ_COILFANG_ELITE]==46000&&ai.timers[VASHJ_COILFANG_STRIDER]==60000);
 assert(!ai.timers.count(VASHJ_TAINTED_ELEMENTAL));
 for(unsigned mask=0;mask<16;++mask){
  ai.m_triggerGuidsNorth.resize((mask&1)?1:0);ai.m_triggerGuidsSouth.resize((mask&2)?1:0);
  ai.m_triggerGuidsWest.resize((mask&4)?1:0);ai.m_triggerGuidsEast.resize((mask&8)?1:0);
  ai.evaded=false;ai.Validate();assert(ai.evaded==(mask!=15));
 }
}
'''.replace('__METHODS__', methods).replace('__VALIDATE__', validation)
    with tempfile.TemporaryDirectory(prefix='mantech-vashj-wave-') as directory:
        tmp = Path(directory)
        (tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
    print('PASS Vashj wave initialization:', era)
