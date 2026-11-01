"""Actual local-only cancellation recorder: lifecycle guards and hard capture/log bounds."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=root/'classic/src/game/World/RaidLab.cpp'
code=r'''
#include <cassert>
#include <cstdint>
#include <set>
#include <mutex>
#include <sstream>
#include <string>
using uint32=unsigned;using uint64=uint64_t;using DWORD=unsigned long;
bool enabled=true;unsigned captures=0,rows=0;DWORD hashValue=5;
unsigned CaptureStackBackTrace(unsigned,unsigned,void**p,DWORD*h){++captures;*h=hashValue;p[0]=reinterpret_cast<void*>(0x1234);return 1;}
void*GetModuleHandleW(void*){return reinterpret_cast<void*>(0x1000);}
bool Enabled(){return enabled;}bool AllowedMap(unsigned m){return m==469;}
struct Guid{uint64 GetRawValue(){return 1;}};
struct Unit{bool player=true,world=true;unsigned map=469;bool IsPlayer(){return player;}bool IsInWorld(){return world;}unsigned GetMapId(){return map;}void*GetMap(){return this;}Guid GetObjectGuid(){return {};}};
struct Attempt{bool limited=false;unsigned cancelStackSamples=0;std::set<std::pair<uint32,uint32>>cancelStacks;};
Attempt attempt;bool recorded=true;Attempt*Find(void*){return recorded?&attempt:nullptr;}
std::recursive_mutex guard;void Write(Attempt&,const std::string&){++rows;}
__METHOD__
int main(){Unit u;CancelStack(nullptr,10468,2,100);assert(!captures);
 enabled=false;CancelStack(&u,10468,2,100);enabled=true;u.player=false;CancelStack(&u,10468,2,100);u.player=true;
 u.world=false;CancelStack(&u,10468,2,100);u.world=true;u.map=0;CancelStack(&u,10468,2,100);u.map=469;
 recorded=false;CancelStack(&u,10468,2,100);recorded=true;attempt.limited=true;CancelStack(&u,10468,2,100);attempt.limited=false;assert(!captures);
 for(unsigned i=0;i<5000;++i)CancelStack(&u,10468,2,100);
 assert(captures==4096&&rows==1&&attempt.cancelStacks.size()==1);
 attempt={};captures=rows=0;for(unsigned i=0;i<100;++i){hashValue=i;CancelStack(&u,10468,2,100);}
 assert(rows==64&&captures==64&&attempt.cancelStacks.size()==64);
}
'''.replace('__METHOD__',block(source.read_text(),'void CancelStack('))
with tempfile.TemporaryDirectory(prefix='raid-cancel-bounds-') as folder:
 d=Path(folder);(d/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=d,check=True)
 subprocess.run([str(d/'test.exe')],cwd=d,check=True)
print('PASS actual native diagnostic actor guards, duplicate suppression, 64 rows / 4096 unwinds maximum')
