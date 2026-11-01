"""Run the actual Classic Horsemen SetData branch with reentrant boss resets."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root.parent/'classic/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/naxxramas/naxxramas.cpp').read_text()
start=source.index('case TYPE_FOUR_HORSEMEN:',source.index('void instance_naxxramas::SetData'))
branch=block(source[start:],'case TYPE_FOUR_HORSEMEN:')
code=r'''
#include <cassert>
#include <vector>
#include <iostream>
using uint32=unsigned;
enum{NOT_STARTED,IN_PROGRESS,FAIL,DONE};
enum{TYPE_FOUR_HORSEMEN,NPC_BLAUMEUX=10,NPC_MOGRAINE,NPC_ZELIEK,NPC_THANE,NPC_SPIRIT_OF_BLAUMEUX=20,NPC_SPIRIT_OF_MOGRAINE,NPC_SPIRIT_OF_KORTHAZZ,NPC_SPIRIT_OF_ZELIREK};
enum{GO_MILI_HORSEMEN_DOOR,GO_MILI_EYE_RAMP,GO_MILI_EYE_BOSS,GO_MILI_PORTAL,GO_CHEST_HORSEMEN_NORM,GO_FLAG_NO_INTERACT,MINUTE=60};
struct Instance;
struct Creature{Instance*instance;bool combat=true;unsigned resets=0,despawns=0;
 bool IsInCombat(){return combat;}Creature*AI(){return this;}void EnterEvadeMode();void ForcedDespawn(){++despawns;}};
struct Instance{
 unsigned m_auiEncounter[1]={IN_PROGRESS},m_horsemenKilled=2,m_tauntTimer=0,depth=0,maxDepth=0,door=0,rewards=0;
 bool missing=false;Creature actors[8]={{this},{this},{this},{this},{this},{this},{this},{this}};
 Creature*GetSingleCreatureFromStorage(unsigned e){if(missing)return nullptr;return &actors[e>=20?e-20+4:e-10];}
 void DoUseDoorOrButton(unsigned e){if(e==GO_MILI_HORSEMEN_DOOR)++door;}
 void DoRespawnGameObject(unsigned,unsigned){++rewards;}void DoToggleGameObjectFlags(unsigned,unsigned,bool){}
 void SetData(uint32 type,uint32 data){++depth;maxDepth=std::max(depth,maxDepth);assert(depth<4);Apply(type,data);--depth;}
 void Apply(uint32 type,uint32 data){switch(type){
'''+branch+r'''
 }}
};
void Creature::EnterEvadeMode(){++resets;instance->SetData(TYPE_FOUR_HORSEMEN,FAIL);combat=false;}
int main(){
 Instance instance;instance.SetData(0,FAIL);
 assert(instance.m_auiEncounter[0]==FAIL&&instance.m_horsemenKilled==0&&instance.maxDepth==2&&instance.door==1);
 for(unsigned i=0;i<4;++i)assert(instance.actors[i].resets==1&&!instance.actors[i].combat);
 for(unsigned i=4;i<8;++i)assert(instance.actors[i].despawns==1);
 instance.SetData(0,FAIL);assert(instance.door==1);for(unsigned i=0;i<4;++i)assert(instance.actors[i].resets==1);
 instance.SetData(0,IN_PROGRESS);assert(instance.m_auiEncounter[0]==IN_PROGRESS&&instance.door==2);
 for(unsigned i=0;i<3;++i){instance.SetData(0,DONE);assert(instance.m_auiEncounter[0]==IN_PROGRESS&&instance.rewards==0);}
 instance.SetData(0,DONE);assert(instance.m_auiEncounter[0]==DONE&&instance.rewards==2&&instance.m_tauntTimer==5000);
 instance.SetData(0,DONE);assert(instance.rewards==2&&instance.m_horsemenKilled==4);
 Instance missing;missing.missing=true;missing.SetData(0,FAIL);assert(missing.m_auiEncounter[0]==FAIL&&missing.door==1);
 std::cout<<"PASS actual Horsemen branch: reentrant wipe, repeated reset, repull, four deaths, missing actors\n";
}
'''
with tempfile.TemporaryDirectory(prefix='horsemen-reset-') as directory:
 path=Path(directory);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
