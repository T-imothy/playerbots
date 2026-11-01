"""Execute actual Classic raid auto-racial guard, including unrelated scope."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/triggers/GenericTriggers.cpp').read_text()
code=r'''
#include <cassert>
#include "__POLICY__"
using namespace ai;
struct Player{unsigned map=533;bool grouped=true;unsigned GetMapId(){return map;}void*GetGroup(){return grouped?this:nullptr;}};
struct AI{bool tank=true;bool IsTank(Player*){return tank;}};
struct BoostTrigger{bool active=true;unsigned calls=0;bool IsActive(){++calls;return active;}};
struct BloodFuryTrigger:BoostTrigger{Player player;Player*bot=&player;AI state;AI*ai=&state;bool IsActive();};
__METHOD__
int main(){BloodFuryTrigger t;
 for(unsigned map:{249,309,409,469,509,531,533}){t.player.map=map;
#ifdef MANGOSBOT_ZERO
 assert(!t.IsActive());
#else
 assert(t.IsActive());
#endif
 t.state.tank=false;assert(t.IsActive());t.state.tank=true;
 t.player.grouped=false;assert(t.IsActive());t.player.grouped=true;
 }
 for(unsigned map:{0,1,33,48,230,289,489,529,30}){t.player.map=map;assert(t.IsActive());}
 t.active=false;assert(!t.IsActive());
}
'''.replace('__POLICY__',(root/'playerbot/strategy/ClassicRaidPolicy.h').as_posix()).replace('__METHOD__',block(source,'bool BloodFuryTrigger::IsActive()'))
code='#include <initializer_list>\n'+code
with tempfile.TemporaryDirectory(prefix='raid-racial-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 for era in ['ZERO','ONE','TWO']:
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS Classic raid tank healing penalty guard; DPS, dungeons, world, BG and other-era trigger admission preserved')
