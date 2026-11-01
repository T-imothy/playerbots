"""Execute Classic's actual Gothik instance transition case, including wipe/re-pull."""
from pathlib import Path
import argparse,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,required=True);args=p.parse_args()
s=(args.core/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/naxxramas/naxxramas.cpp').read_text()
start=s.index('        case TYPE_GOTHIK:',s.index('void instance_naxxramas::SetData('))
body=s[start:s.index('        case TYPE_FOUR_HORSEMEN:',start)]
code=r'''
#include <cassert>
#include <vector>
#include <iostream>
using uint32=unsigned;
enum {TYPE_GOTHIK=7,NOT_STARTED=0,IN_PROGRESS=1,FAIL=2,DONE=3,SPECIAL=4,
 GO_MILI_GOTH_ENTRY_GATE=10,GO_MILI_GOTH_COMBAT_GATE,GO_MILI_GOTH_EXIT_GATE,GO_MILI_HORSEMEN_DOOR,
 SPELL_SPECTRAL_ASSAULT=20,SPELL_UNRELENTING_ASSAULT,TRIGGERED_OLD_TRIGGERED,NPC_THANE};
struct Creature{void CastSpell(void*,unsigned,unsigned){}};
struct Map{Creature*GetCreature(unsigned){return nullptr;}};
struct Instance{unsigned m_auiEncounter[15]={};std::vector<unsigned>m_spectralSideList,m_unrelentingSideList;
 Map map;Map*instance=&map;bool entryOpen=true,centralOpen=true,exitOpen=false,horseOpen=false;
 void DoUseDoorOrButton(unsigned id){switch(id){case GO_MILI_GOTH_ENTRY_GATE:entryOpen=!entryOpen;break;
 case GO_MILI_GOTH_COMBAT_GATE:centralOpen=!centralOpen;break;
 case GO_MILI_GOTH_EXIT_GATE:exitOpen=!exitOpen;break;case GO_MILI_HORSEMEN_DOOR:horseOpen=!horseOpen;break;}}
 void StartNextDialogueText(unsigned){}
 void SetData(unsigned type,unsigned data){switch(type){__CASE__}}
};
int main(){Instance i;i.SetData(TYPE_GOTHIK,IN_PROGRESS);assert(!i.entryOpen&&!i.centralOpen);
 i.SetData(TYPE_GOTHIK,FAIL);assert(i.entryOpen&&i.centralOpen&&!i.exitOpen);
 i.SetData(TYPE_GOTHIK,IN_PROGRESS);assert(!i.entryOpen&&!i.centralOpen);
 i.SetData(TYPE_GOTHIK,DONE);assert(i.entryOpen&&i.centralOpen&&i.exitOpen&&i.horseOpen);
 Instance afterOpen;afterOpen.SetData(TYPE_GOTHIK,IN_PROGRESS);afterOpen.SetData(TYPE_GOTHIK,SPECIAL);
 assert(afterOpen.centralOpen);afterOpen.SetData(TYPE_GOTHIK,FAIL);assert(afterOpen.centralOpen&&afterOpen.entryOpen);
 Instance lateKill;lateKill.SetData(TYPE_GOTHIK,IN_PROGRESS);lateKill.SetData(TYPE_GOTHIK,SPECIAL);
 lateKill.SetData(TYPE_GOTHIK,DONE);assert(lateKill.centralOpen&&lateKill.entryOpen&&lateKill.exitOpen);
 std::cout<<"PASS native Gothik wipe/re-pull, early kill and already-open central gate transitions\n";
}
'''.replace('__CASE__',body)
with tempfile.TemporaryDirectory(prefix='gothik-gate-reset-') as directory:
 d=Path(directory);(d/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=d,check=True)
 subprocess.run([str(d/'test.exe')],cwd=d,check=True)
