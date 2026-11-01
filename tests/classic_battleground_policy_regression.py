"""Execute the production Classic BG assignment policy, no server or DB writes."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
code=r'''
#include "playerbot/strategy/values/ClassicBattlegroundPolicy.h"
#include <cassert>
#include <iostream>
using namespace ai::ClassicBattlegroundPolicy;
int main() {
 std::array<Node,5> neutral; neutral.fill(Node::Neutral);
 // Exact mirrored opening: home 2, BS 5, LM 4, mine 4; nobody sent to enemy home.
 for(bool alliance:{true,false}) {
  unsigned assigned[5]={};
  for(unsigned slot=0;slot<15;++slot) ++assigned[Arathi(slot,15,alliance,0,neutral)];
  assert(assigned[alliance?0:2]==2 && assigned[alliance?2:0]==0);
  assert(assigned[1]==5 && assigned[3]==4 && assigned[4]==4);
  for(unsigned count=4;count<=15;++count) {
   unsigned seen=0;
   for(unsigned slot=0;slot<count;++slot) seen|=1u<<Arathi(slot,count,alliance,1000,neutral);
   assert((seen & (1u<<(alliance?0:2))) && (seen&2) && (seen&8) && (seen&16));
  }
 }
 for(unsigned mask=0;mask<3125;++mask) {
  unsigned n=mask; std::array<Node,5> a,h;
  for(unsigned i=0;i<5;++i){a[i]=Node(n%5); n/=5; h[i]=a[i];}
  std::swap(h[0],h[2]);
  for(unsigned slot=0;slot<15;++slot) {
   unsigned x=Arathi(slot,15,true,100000,a), y=Arathi(slot,15,false,100000,h);
   assert(x<5 && y<5);
  }
 }
 std::array<Node,5> contested={Node::Ours,Node::EnemyAssault,Node::Theirs,Node::Ours,Node::Theirs};
 unsigned defend=0,attack=0;
 for(unsigned slot=0;slot<15;++slot) { unsigned n=Arathi(slot,15,true,100000,contested); defend+=n==1;attack+=(n==2||n==4); }
 assert(defend>=6 && attack>=3); // retain an offensive group while relieving a flag
 std::array<Node,4> towers; towers.fill(Node::Destroyed);
 assert(GeneralReady(towers,Node::Ours));
 assert(!GeneralReady(towers,Node::OurAssault));
 for(unsigned i=0;i<4;++i) {
  towers[i]=Node::OurAssault; assert(!GeneralReady(towers,Node::Ours));
  towers[i]=Node::Theirs; assert(!GeneralReady(towers,Node::Ours));
  towers[i]=Node::Destroyed;
 }
 assert(TowerSquadSize(40)==6 && TowerSquadSize(20)==3 && TowerSquadSize(4)==0);
 for(bool a:{true,false}) {
  unsigned instance=0,step=0;ApproachPoint p;
  const float start=a?700.f:-1000.f,goal=a?-600.f:77.f;
  assert(AlteracApproach(a,12,instance,step,start,-400,50,goal,p)&&step==0);
  auto first=p;
  assert(AlteracApproach(a,12,instance,step,first.x,first.y,first.z,goal,p)&&step==1);
  auto second=p;
  assert(!AlteracApproach(a,12,instance,step,second.x,second.y,second.z,goal,p)&&step==2);
  // Repeated calls after completion cannot reverse the route.
  assert(!AlteracApproach(a,12,instance,step,second.x,second.y,second.z,goal,p));
  // A death/return to our half and a new match both start a fresh approach.
  assert(AlteracApproach(a,12,instance,step,start,-400,50,goal,p)&&step==0);
  step=2;assert(AlteracApproach(a,12,instance,step,a?73.f:-612.f,-400,50,goal,p)&&step==0);
  step=2;assert(AlteracApproach(a,13,instance,step,start,-400,50,goal,p)&&step==0);
  // Home defense and already-crossed players get no detour back across midfield.
  assert(!AlteracApproach(a,13,instance,step,start,-400,50,start,p));
  assert(!AlteracApproach(a,13,instance,step,a?-700.f:200.f,-300,50,goal,p));
 }
 std::cout<<"PASS Classic AB opening coverage, both teams, mixed defense/attack; AV tower squad and completed-objective general gate\n";
}
'''
with tempfile.TemporaryDirectory(prefix='classic-bg-policy-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/I'+str(root),'test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
 # Core callers lack MANGOSBOT_ZERO, while the module defines it. Exercise the
 # actual new header declaration region in both TUs, including inline access.
 header=(root/'playerbot/PlayerbotAI.h').read_text()
 declarations=header.split('    void PrepareCompletedMovement();',1)[1].split('    bool ProcessPendingTransition();',1)[0]
 (p/'layout.h').write_text('#include <cstdint>\nusing uint32=uint32_t;\nstruct AI {\n'+declarations+'\nvoid* bot; void* GetBot() { return bot; } };\n')
 (p/'module.cpp').write_text('#define MANGOSBOT_ZERO\n#include "layout.h"\nextern "C" unsigned moduleSize(){return sizeof(AI);}\nextern "C" void initialize(AI* p,void* b){new(p) AI{};p->bot=b;}\n'.replace('#include "layout.h"','#include <new>\n#include "layout.h"'))
 (p/'caller.cpp').write_text('#include "layout.h"\n#include <cassert>\nextern "C" unsigned moduleSize();extern "C" void initialize(AI*,void*);\nint main(){assert(moduleSize()==sizeof(AI));AI p;int b;initialize(&p,&b);assert(p.GetBot()==&b);}\n')
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','module.cpp','caller.cpp','/Fe:layout.exe'],cwd=p,check=True)
 subprocess.run([str(p/'layout.exe')],cwd=p,check=True)

# Execute the actual gate/respawn wake hook. Waiting sleeps must be discarded,
# while accepted casts and activity outside battlegrounds remain untouched.
wake=block((root/'playerbot/strategy/actions/ClassicBattlegroundActions.cpp').read_text(),'void PlayerbotAI::PrepareForBattlegroundStart(')
code=r'''
#include <cassert>
#include <map>
#include <string>
using uint32=unsigned;
const unsigned STATUS_IN_PROGRESS=3;
struct BattleGround{unsigned status=2,instance=1;unsigned GetStatus(){return status;}unsigned GetInstanceId(){return instance;}};
struct Player{BattleGround*bg=nullptr;bool world=true,transfer=false,alive=true,cast=false;
bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool IsAlive(){return alive;}
bool IsNonMeleeSpellCasted(bool,bool,bool){return cast;}BattleGround*GetBattleGround(){return bg;}};
struct Position{unsigned resets=0;void Reset(){++resets;}};
using PositionMap=std::map<std::string,Position>;
struct Value{PositionMap value;PositionMap&Get(){return value;}};
struct Context{Value value;template<class T>Value*GetValue(const char*){return &value;}};
struct PlayerbotAI{Player*bot;Context*aiObjectContext;bool real=false,isWaiting=true;
unsigned aiInternalUpdateDelay=20000,observedBattlegroundInstance=0;
bool observedBattlegroundActive=false,observedBattlegroundAlive=false;
bool IsRealPlayer(){return real;}void PrepareForBattlegroundStart();};
__WAKE__
int main(){
 Player bot;Context ctx;PlayerbotAI ai{&bot,&ctx};BattleGround bg;
 ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==20000); // world/dungeon is not a BG
 bot.bg=&bg;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==20000);
 bg.status=3;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==0&&!ai.isWaiting);
 assert(ctx.value.value["bg objective"].resets==1);
 ai.aiInternalUpdateDelay=1000;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==1000);
 bot.alive=false;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==1000);
 bot.alive=true;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==0);
 ai.aiInternalUpdateDelay=1500;bg.instance=2;bot.cast=true;
 ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==1500); // preserve accepted cast
 bot.cast=false;bot.transfer=true;bg.instance=3;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==1500);
 bot.transfer=false;bot.world=false;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==1500);
 bot.world=true;ai.real=true;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==1500);
 ai.real=false;ai.PrepareForBattlegroundStart();assert(ai.aiInternalUpdateDelay==0);
}
'''.replace('__WAKE__',wake)
with tempfile.TemporaryDirectory(prefix='classic-bg-wake-') as tmp:
 p=Path(tmp);(p/'wake.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','wake.cpp','/Fe:wake.exe'],cwd=p,check=True)
 subprocess.run([str(p/'wake.exe')],cwd=p,check=True)
