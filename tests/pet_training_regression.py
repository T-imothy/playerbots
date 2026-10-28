"""Compile actual pet training tables; assert expansion/level boundaries."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/PlayerbotFactory.cpp').read_text();s=s[s.index('void PlayerbotFactory::InitPetSpells()'):]
parts=s.split('#ifdef MANGOSBOT_ONE',1)
for era,source in zip(('classic','tbc'),parts):
 start=source.index('        if (petType == PET_BAT ||');opening=source.index('{',start);depth=0
 for i in range(opening,len(source)):
  depth+=(source[i]=='{')-(source[i]=='}')
  if not depth:cleanup=source[start:i+1];break
 tables=[]
 for family in ('BAT','CARRION_BIRD','OWL'):
  m=re.search(r'hunterPetSpells\[PET_'+family+r'\]\s*=\s*(\{.*?\});',source,re.S);assert m
  tables.append(m[1])
 code='''#include <cassert>
#include <vector>
#include <utility>
#include <set>
using uint32=unsigned;
enum {PET_BAT,PET_CARRION_BIRD,PET_OWL,PET_CAT};
struct Pet {unsigned level;std::set<unsigned> known;unsigned GetLevel(){return level;}bool HasSpell(unsigned id){return known.count(id);}void unlearnSpell(unsigned id,bool){known.erase(id);}};
void repair(int petType,Pet* pet){'''+cleanup+'''}
int main(){std::vector<std::vector<std::pair<unsigned,unsigned>>> tables={'''+','.join(tables)+'''};
 for(auto &table:tables){
  for(unsigned level=1;level<=70;++level){std::set<unsigned> known;
   for(auto row:table)if(level>=row.first)known.insert(row.second);
   assert(known.count(24423)==(level>=8));assert(known.count(24577)==(level>=24));
   assert(known.count(24578)==(level>=48));assert(known.count(24579)==(level>=56));
   assert(known.count(27051)==(TBC && level>=64));
   for(int family:{PET_BAT,PET_CARRION_BIRD,PET_OWL}){
    Pet pet{level,{24578,24579,16827}};if(TBC)pet.known.insert(27051);repair(family,&pet);
    assert(pet.known.count(16827));assert(pet.known.count(24578)==(level>=48));assert(pet.known.count(24579)==(level>=56));assert(pet.known.count(27051)==(TBC&&level>=64));
   }
  }
 }
}'''
 with tempfile.TemporaryDirectory(prefix='pet-training-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DTBC='+str(int(era=='tbc')),str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True)
  subprocess.run([str(p/'test.exe')],check=True)
 print('PASS:',era,'all three Screech families at levels 1-70')
