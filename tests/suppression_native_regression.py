"""Compile each core's actual device AI: pulse, rearm, boss completion, no repeated mutation."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
cores=Path(__file__).resolve().parents[2]
for era in ('classic','tbc','wotlk'):
    source=(cores/era/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/blackwing_lair/blackwing_lair.cpp').read_text()
    body=block(source,'struct go_ai_suppression')+';'
    code=r'''
#include <cassert>
#include <chrono>
#include <iostream>
using uint32=unsigned;
enum{GO_READY=0,GO_ACTIVATED=1,GO_JUST_DEACTIVATED=2,TYPE_LASHLAYER=2,DONE=3,IN_MILLISECONDS=1000,MINUTE=60,HOUR=3600,TRIGGERED_OLD_TRIGGERED=1};
unsigned urand(unsigned a,unsigned){return a?a:1;}
struct Unit{};
struct ScriptedInstance{unsigned phase=1;unsigned GetData(unsigned){return phase;}};
struct Map{ScriptedInstance instance;ScriptedInstance* GetInstanceData(){return &instance;}};
struct Info{struct{unsigned spellId=22247;}trap;};
struct GameObject{Map map;Info info;unsigned state=GO_READY,delay=0,casts=0,changes=0;
 Map* GetMap(){return &map;}unsigned GetLootState(){return state;}
 void SetLootState(unsigned s){state=s;++changes;}void SetRespawnTime(unsigned s){delay=s;}
 void SetRespawnTime(std::chrono::seconds s){delay=unsigned(s.count());}
 unsigned GetObjectGuid(){return 1;}void SendGameObjectCustomAnim(unsigned){}
 Info* GetGOInfo(){return &info;}void CastSpell(void*,void*,unsigned,unsigned){++casts;}};
struct GameObjectAI{GameObject* m_go;GameObjectAI(GameObject* go):m_go(go){}
 virtual void OnLootStateChange(Unit*){}virtual void UpdateAI(uint32){}};
__BODY__
int main(){
 GameObject go;go_ai_suppression ai(&go);ai.UpdateAI(5001);assert(go.casts==1);
 go.state=GO_ACTIVATED;ai.OnLootStateChange(nullptr);assert(go.delay==30);
 ai.UpdateAI(5001);assert(go.casts==1);
 go.map.instance.phase=DONE;ai.UpdateAI(1);
 assert(go.state==GO_JUST_DEACTIVATED&&go.delay==604800&&go.changes==1&&go.casts==1);
 ai.UpdateAI(100000);assert(go.changes==1&&go.casts==1);
 GameObject active;go_ai_suppression other(&active);active.map.instance.phase=DONE;
 other.UpdateAI(5001);assert(active.casts==0&&active.state==GO_JUST_DEACTIVATED);
 std::cout<<"PASS native suppression lifecycle\n";
}
'''.replace('__BODY__',body)
    with tempfile.TemporaryDirectory(prefix='bwl-device-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
