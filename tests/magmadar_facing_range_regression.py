"""Native-range facing admission: a distant caster need not circle a turning boss."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <limits>
namespace encounter {struct Point {float x,y,z;};}
struct Unit {float x=0,y=0,z=0,facing=0;
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetOrientation(){return facing;}};
struct Player {float reach=1.5f;float GetCombatReach(){return reach;}};
float radius=35;float NativeEncounterSpellRadius(unsigned id){assert(id==19272);return radius;}
'''+block(source,'bool MagmadarFacingSafe(')+r'''
int main(){Unit boss;Player bot;
 assert(MagmadarFacingSafe(&boss,&bot,{-20,0,0}));
 assert(!MagmadarFacingSafe(&boss,&bot,{20,0,0}));
#ifdef MANGOSBOT_ZERO
 assert(MagmadarFacingSafe(&boss,&bot,{40,0,0}));
 assert(!MagmadarFacingSafe(&boss,&bot,{36,0,0}));
 boss.facing=3.14159265f;assert(MagmadarFacingSafe(&boss,&bot,{-40,0,0}));
 assert(!MagmadarFacingSafe(&boss,&bot,{-20,0,0}));
 radius=0;assert(!MagmadarFacingSafe(&boss,&bot,{-40,0,0}));
 radius=std::numeric_limits<float>::quiet_NaN();assert(!MagmadarFacingSafe(&boss,&bot,{-40,0,0}));
#else
 assert(!MagmadarFacingSafe(&boss,&bot,{40,0,0}));
#endif
}
'''
with tempfile.TemporaryDirectory(prefix='mag-facing-') as t:
 p=Path(t);(p/'test.cpp').write_text(code)
 for era in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
  r=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/D'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  subprocess.run([str(p/'test.exe')],check=True)
print('PASS native35-yard breath, target reach/margin, boss turns, invalid radius and era isolation')
