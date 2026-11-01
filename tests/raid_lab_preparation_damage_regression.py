"""Actual pre-combat diagnostics: bounded, group/instance isolated, no game mutation."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root.parent/'classic/src/game/World/RaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <map>
#include <string>
#include <mutex>
#include <cstdint>
#include <sstream>
using uint64=uint64_t;using uint32=uint32_t;using int32=int32_t;
#define UI64FMTD "%llu"
constexpr unsigned TYPEID_PLAYER=4;
struct Guid{uint64 id=10;uint64 GetRawValue()const{return id;}};
using ObjectGuid=Guid;
namespace BotState{constexpr unsigned BOT_STATE_NON_COMBAT=0;}
struct Value{Guid Get(){return {};}};
struct Context{Value v;template<class T>Value*GetValue(const char*){return &v;}};
struct Unit;struct AI{Context ctx;unsigned GetState(){return 0;}std::string GetLastExecutedActionName(unsigned){return "follow";}std::string GetLastActionDecision(unsigned){return "native";}bool HasStrategy(const char*,unsigned){return false;}Context*GetAiObjectContext(){return &ctx;}
 Unit*GetUnit(Guid){return nullptr;}Unit*GetMaster(){return nullptr;}float GetRange(const char*){return 5;}};
namespace G3D{struct Vector3{float x=0,y=0,z=0;};}
struct Spline{G3D::Vector3 FinalDestination(){return {};}};struct Motion{unsigned GetCurrentMovementGeneratorType(){return 0;}};
struct Map{};struct Group{Guid leader;Guid GetLeaderGuid(){return leader;}};
struct Unit{bool world=true;uint32 map=533,instance=5,type=4;Guid guid;Map native;
 Spline*movespline=nullptr;Motion motion;Motion*GetMotionMaster(){return &motion;}
 bool IsInWorld(){return world;}uint32 GetMapId(){return map;}uint32 GetInstanceId(){return instance;}
 Map*GetMap(){return &native;}uint32 GetTypeId(){return type;}Guid GetObjectGuid(){return guid;}
 unsigned GetEntry(){return 0;}float GetPositionX(){return 1;}float GetPositionY(){return 2;}float GetPositionZ(){return 3;}};
struct Player:Unit{Group group;bool grouped=true;AI*ai=nullptr;AI*GetPlayerbotAI(){return ai;}Group*GetGroup(){return grouped?&group:nullptr;}};
bool enabled=true;bool Enabled(){return enabled;}bool AllowedMap(uint32 m){return m==533;}
std::recursive_mutex guard;std::map<uint64,std::pair<uint32,uint32>>preparedLeaders;std::map<uint64,uint32>preparationImpacts,preparationCombats;
struct Attempt{unsigned combatTransitions=0,combatTransitionLimit=512;};Attempt attempt;bool active=false;Attempt*Find(Map*){return active?&attempt:nullptr;}
unsigned writes=0;std::string lastWrite;void Write(Attempt&,std::string s){++writes;lastWrite=s;}std::string Quote(std::string s){return s;}
struct Log{unsigned records=0;template<class...T>void outString(const char*,T...){++records;}}sLog;
__TRANSITION__
__IMPACT__
__COMBAT__
int main(){Player p;Unit enemy;enemy.type=3;
 Impact(&enemy,&p,"damage",1,50,100,-1);assert(sLog.records==0);
 preparedLeaders[10]={533,5};
 for(unsigned i=0;i<300;++i)Impact(&enemy,&p,"damage",1,50,100,-1);
 assert(sLog.records==256&&preparationImpacts[10]==256);
 preparationImpacts.clear();p.instance=6;Impact(&enemy,&p,"damage",1,50,100,-1);assert(preparationImpacts.empty());p.instance=5;
 p.group.leader.id=11;Impact(&enemy,&p,"damage",1,50,100,-1);assert(preparationImpacts.empty());p.group.leader.id=10;
 p.grouped=false;Impact(&enemy,&p,"damage",1,50,100,-1);assert(preparationImpacts.empty());p.grouped=true;
 Impact(&enemy,&p,"heal",1,50,100,50);Impact(&enemy,&p,"damage",1,0,100,-1);assert(preparationImpacts.empty());
 p.world=false;Impact(&enemy,&p,"damage",1,50,100,-1);p.world=true;assert(preparationImpacts.empty());
 enabled=false;Impact(&enemy,&p,"damage",1,50,100,-1);enabled=true;assert(preparationImpacts.empty());
 active=true;Impact(&enemy,&p,"damage",1,50,100,-1);assert(writes==1&&preparationImpacts.empty());active=false;
 Impact(nullptr,&p,"damage",0,50,100,-1);assert(preparationImpacts[10]==1);
 preparationImpacts.clear();AI brain;p.ai=&brain;const unsigned before=sLog.records;
 for(unsigned i=0;i<10;++i)Impact(&enemy,&p,"damage",1,50,100,-1);
 assert(sLog.records==before+18); // ten damage records, only eight action snapshots
 const unsigned beforeCombat=sLog.records;
 PreparationCombat(nullptr,&enemy);p.world=false;PreparationCombat(&p,&enemy);p.world=true;
 p.instance=6;PreparationCombat(&p,&enemy);p.instance=5;
 active=true;PreparationCombat(&p,&enemy);active=false;
 enabled=false;PreparationCombat(&p,&enemy);enabled=true;
 assert(sLog.records==beforeCombat && preparationCombats.empty());
 for(unsigned i=0;i<150;++i)PreparationCombat(&p,nullptr);
 assert(preparationCombats[10]==128 && sLog.records==beforeCombat+384); // Combat, AI and follow evidence share one bound.
 preparationCombats.clear();PreparationCombat(&enemy,&p);
 assert(preparationCombats[10]==1 && sLog.records==beforeCombat+385);
 active=true;attempt.combatTransitions=0;const unsigned beforeNative=writes;
 enemy.guid.id=123;PreparationCombat(&enemy,&p);
 assert(writes==beforeNative+1&&lastWrite.find("combat_enter")!=std::string::npos);
 assert(lastWrite.find("\"guid\":123")!=std::string::npos&&lastWrite.find("\"enemy\":10")!=std::string::npos);
 assert(lastWrite.find("\"from\":[1,2,3]")!=std::string::npos);
 PreparationCombat(&enemy,nullptr);assert(lastWrite.find("\"enemy\":0")!=std::string::npos);
 for(unsigned i=2;i<600;++i)PreparationCombat(&enemy,&p);
 assert(writes==beforeNative+513&&lastWrite.find("coverage_gap")!=std::string::npos);
 const unsigned capped=writes;PreparationCombat(&enemy,&p);assert(writes==capped);
 assert(sLog.records==beforeCombat+385); // Active observations never flood the console.
}
'''.replace('__TRANSITION__',block(source,'bool RecordCombatTransition(')).replace('__IMPACT__',block(source,'void Impact(')).replace('__COMBAT__',block(source,'void PreparationCombat('))
with tempfile.TemporaryDirectory(prefix='raidlab-preparation-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS pre-pull damage evidence bounds, identity/instance guards, active-trace separation and absent source')
