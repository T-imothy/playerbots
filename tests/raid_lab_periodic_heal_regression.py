"""Execute native periodic-health mutation with local tracing enabled and disabled."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root.parent/'classic/src/game/Spells/SpellAuras.cpp').read_text()
start=source.index('            // Periodic healing does not pass through Unit::DealHeal.')
end=source.index('            SpellPeriodicAuraLogInfo pInfo',start)
segment=source[start:end]
code=r'''
#include <algorithm>
#include <cassert>
#include <string>
#include <iostream>
using uint32=unsigned;using int32=int;
struct Unit{uint32 health=60,maximum=100,calls=0;uint32 GetHealth(){return health;}
 int32 ModifyHealth(uint32 amount){++calls;uint32 gain=std::min(amount,maximum-health);health+=gain;return gain;}};
struct Spell{uint32 Id=25315;};
namespace RaidLab{unsigned records=0;Unit*caster=nullptr,*patient=nullptr;unsigned before=0,amount=0,spell=0;int gain=0;
 void Impact(Unit*c,Unit*t,const char*kind,uint32 s,uint32 a,uint32 b,int32 g){assert(std::string(kind)=="heal");++records;caster=c;patient=t;before=b;amount=a;spell=s;gain=g;}}
int Tick(Unit*pCaster,Unit*target,Spell*spellProto,uint32 pdamage){
'''+segment+r'''
 return gain;
}
int main(){Unit caster,target;Spell spell;
 assert(Tick(&caster,&target,&spell,80)==40&&target.health==100&&target.calls==1);
#ifdef MANTECH_RAID_LAB
 assert(RaidLab::records==1&&RaidLab::caster==&caster&&RaidLab::patient==&target);
 assert(RaidLab::before==60&&RaidLab::amount==80&&RaidLab::gain==40&&RaidLab::spell==25315);
#else
 assert(RaidLab::records==0);
#endif
 target.health=10;assert(Tick(&caster,&target,&spell,20)==20&&target.health==30&&target.calls==2);
 assert(Tick(&caster,&target,&spell,0)==0&&target.health==30&&target.calls==3);
 std::cout<<"PASS native periodic heal: exact source/spell/pre-health/actual gain; unchanged single mutation with tracing disabled\n";
}
'''
for enabled in (False,True):
 with tempfile.TemporaryDirectory(prefix='raid-periodic-heal-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  command=['cl','/nologo','/EHsc','/std:c++17']+(['/DMANTECH_RAID_LAB'] if enabled else [])+['test.cpp','/Fe:test.exe']
  subprocess.run(command,cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
