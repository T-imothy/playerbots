"""Actual boss/instance methods reproduce and guard Devourer's ignored wipe update."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
folder=root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/icecrown_citadel/frozen_halls/forge_of_souls'
boss=(folder/'boss_devourer_of_souls.cpp').read_text()
instance=(folder/'forge_of_souls.cpp').read_text()
header=(folder/'forge_of_souls.h').read_text()
enum=header[header.index('enum\n'):header.index('struct sIntoEventNpcSpawnLocations')]
home=block(boss,'    void JustReachedHome() override').replace(' override','')
methods=block(instance,'void instance_forge_of_souls::SetData(')+'\n'+block(instance,'uint32 instance_forge_of_souls::GetData(')
code=r'''
#include <cassert>
#include <list>
#include <sstream>
#include <string>
#include <iostream>
using uint32=unsigned;
enum{NOT_STARTED=0,IN_PROGRESS=1,FAIL=2,DONE=3};
#define OUT_SAVE_INST_DATA
#define OUT_SAVE_INST_DATA_COMPLETE
__ENUM__
struct Creature{void ForcedDespawn(){}};
struct Map{Creature*GetCreature(unsigned){return nullptr;}};
struct instance_forge_of_souls{
 unsigned m_auiEncounter[2]={0,0};bool m_bCriteriaPhantomBlastFailed=false;
 std::list<unsigned>m_luiSoulFragmentAliveGUIDs;std::string m_strInstData;
 Map map;Map*instance=&map;unsigned saves=0,events=0;
 void SetData(uint32,uint32);uint32 GetData(uint32)const;
 void*GetPlayerInMap(){return nullptr;}void ProcessEventNpcs(void*){++events;}
 void SaveToDB(){++saves;}
};
__METHODS__
struct Boss{
 instance_forge_of_souls*m_pInstance;
 __HOME__
};
int main(){
 instance_forge_of_souls data;Boss boss{&data};
 data.SetData(TYPE_BRONJAHM,DONE);unsigned saves=data.saves;
 data.SetData(TYPE_DEVOURER_OF_SOULS,IN_PROGRESS);
 data.SetData(NPC_DEVOURER_OF_SOULS,FAIL);
 assert(data.GetData(TYPE_DEVOURER_OF_SOULS)==IN_PROGRESS); // Reproduce old key.
 for(unsigned pull=0;pull<100;++pull){
  data.SetData(TYPE_DEVOURER_OF_SOULS,IN_PROGRESS);
  data.SetData(TYPE_ACHIEV_PHANTOM_BLAST,FAIL);
  assert(data.m_bCriteriaPhantomBlastFailed);
  boss.JustReachedHome();
  assert(data.GetData(TYPE_DEVOURER_OF_SOULS)==FAIL);
  assert(data.GetData(TYPE_BRONJAHM)==DONE&&!data.m_bCriteriaPhantomBlastFailed);
  assert(data.saves==saves&&data.events==0);
 }
 boss.m_pInstance=nullptr;boss.JustReachedHome();
 data.SetData(TYPE_DEVOURER_OF_SOULS,DONE);
 assert(data.GetData(TYPE_DEVOURER_OF_SOULS)==DONE&&data.saves==saves+1&&data.events==1);
 std::cout<<"PASS: actual Devourer wipe key,100 resets, achievement reset, unrelated encounter and completion\n";
}
'''.replace('__ENUM__',enum).replace('__METHODS__',methods).replace('__HOME__',home)
with tempfile.TemporaryDirectory(prefix='devourer-reset-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=path,check=True)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
