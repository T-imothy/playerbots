"""Execute Jedoga's native constructor when the initial visual cast fails."""
from pathlib import Path
import re,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
native=(root.parent/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/azjol-nerub/ahnkahet/boss_jedoga.cpp').read_text()
constructor=block(native,'boss_jedogaAI(Creature* pCreature)')
initializers='\n'.join(re.findall(r'    (?:uint32 m_uiVisualTimer|bool m_bHasDoneIntro)[^;]*;',native))
code=r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;
enum{SPELL_SPHERE_VISUAL,CAST_OK};
struct instance_ahnkahet{};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Creature{Map map;Map*GetMap(){return &map;}void*GetInstanceData(){return nullptr;}};
bool castFails=false;
struct ScriptedAI{Creature*m_creature;ScriptedAI(Creature*c):m_creature(c){}int DoCastSpellIfCan(Creature*,int){return castFails?99:CAST_OK;}};
struct boss_jedogaAI:ScriptedAI{
 instance_ahnkahet*m_pInstance;bool m_bIsRegularMode;unsigned resets=0;void Reset(){++resets;}
 __INIT__
 __CTOR__
};
int main(){Creature creature;
 castFails=true;boss_jedogaAI failed(&creature);assert(failed.m_uiVisualTimer==0&&!failed.m_bHasDoneIntro&&failed.resets==1);
 castFails=false;boss_jedogaAI success(&creature);assert(success.m_uiVisualTimer==5000&&!success.m_bHasDoneIntro&&success.resets==1);
 success.m_bHasDoneIntro=true;success.Reset();assert(success.m_bHasDoneIntro); // Reset doesn't replay the one-time intro.
 std::cout<<"PASS: Jedoga initial visual success/failure states are defined\n";
}
'''.replace('__INIT__',initializers).replace('__CTOR__',constructor)
with tempfile.TemporaryDirectory(prefix='mantech-jedoga-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
