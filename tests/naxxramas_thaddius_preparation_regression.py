"""Execute actual Classic Thaddius request, role staging and safe native-route admission."""
from pathlib import Path
import ast,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'tests/naxxramas_roles_regression.py').read_text())
fixture=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fixture' for t in n.targets)).split('__SOURCE__')[0]
fixture=fixture.replace('#include <algorithm>','#include <algorithm>\n#include <ctime>\n#include <memory>')
fixture=fixture.replace('struct Player:Unit{','float floorDropBelowY=-10000;\nstruct Player:Unit{')
fixture=fixture.replace('bool IsBeingTeleported(){','void UpdateAllowedPositionZ(float,float y,float&z){if(y<floorDropBelowY)z-=20;}bool IsNonMeleeSpellCasted(bool){return cast!=nullptr;}bool IsBeingTeleported(){')
fixture=fixture.replace('struct Creature:Unit{','struct Creature:Unit{float GetAttackDistance(Player*){return 19;}')
fixture=fixture.replace('unsigned validations=0;','unsigned validations=0,moves=0;bool authorize=true;')
fixture=fixture.replace('struct Context{',r'''
using int32=int;
struct PositionEntry{float x=0,y=0,z=0;unsigned mapId=0;bool set=false;bool isSet(){return set;}
 void Set(float a,float b,float c,unsigned map){x=a;y=b;z=c;mapId=map;set=true;}};
using PositionMap=std::map<std::string,PositionEntry>;
template<>struct Value<PositionMap&>{PositionMap value;PositionMap&Get(){return value;}};
struct Context{Value<PositionMap&>positions;std::map<std::string,Value<int32>>ints;
''')
fixture=fixture.replace('const std::string& = ""){if constexpr(std::is_same_v<T,ObjectGuid>)',
    'const std::string& key = ""){if constexpr(std::is_same_v<T,PositionMap&>)return &positions;else if constexpr(std::is_same_v<T,int32>)return &ints[key];else if constexpr(std::is_same_v<T,ObjectGuid>)')
fixture+=r'''
constexpr unsigned NOT_STARTED=0;
bool CanManageBotCommands(PlayerbotAI*a,Player*){return a->authorize;}
struct PullStrategy{static std::map<PlayerbotAI*,PullStrategy*>registry;Unit*target=nullptr;bool allowed=true,pending=true;time_t start=time(nullptr);ObjectGuid requester;
 static PullStrategy*Get(PlayerbotAI*a){return registry[a];}Unit*GetTarget(){return target;}bool IsEncounterPreparationAllowed(){return allowed;}
 bool IsPullPendingToStart(){return pending;}bool HasPullStarted(){return start!=0;}
 time_t GetPullStartTime(){return start;}unsigned GetMaxPullTime(){return 60;}ObjectGuid GetRequester(){return requester;}};
std::map<PlayerbotAI*,PullStrategy*>PullStrategy::registry;
using Event=unsigned;
namespace ai{
bool NaxxramasThaddiusPreparationPlan(PlayerbotAI*,EncounterPosition&,bool&);bool NaxxramasThaddiusPullReady(PlayerbotAI*);
struct NaxxramasThaddiusPrepareAction{PlayerbotAI*ai;Player*bot;NaxxramasThaddiusPrepareAction(PlayerbotAI*a):ai(a),bot(a->GetBot()){}
 bool isUseful();bool Execute(Event&);bool IsReaction(){return false;}bool MoveTo(unsigned,float x,float y,float z,bool,bool,bool,bool){++ai->moves;bot->x=x;bot->y=y;bot->z=z;return true;}};
}
__SOURCE__
int main(){
 Map map;ScriptedInstance instance;map.instance=&instance;Group group;
 Creature boss,left,right;boss.guid=50;boss.entry=15928;boss.y=100;left.guid=51;left.entry=15930;left.x=-50;right.guid=52;right.entry=15929;right.x=50;
 for(auto*u:{&boss,&left,&right}){u->map=&map;u->combat=false;}instance.stored={{15928,&boss},{15930,&left},{15929,&right}};
 Player t1,t2,h1,h2,d1,d2,human;Player*players[]={&t1,&t2,&h1,&h2,&d1,&d2,&human};unsigned id=1;
 std::vector<std::unique_ptr<PlayerbotAI>>brains;
 for(auto*p:players){p->guid=id++;p->map=&map;p->group=&group;p->combat=false;p->y=-60;group.Add(p);if(p!=&human)brains.emplace_back(new PlayerbotAI(p));}
 t1.tank=t2.tank=true;h1.healer=h2.healer=true;d1.cls=d2.cls=8;
 for(auto&b:brains)b->units[human.guid.id]=&human;
 PullStrategy pull;pull.target=&left;pull.requester=human.guid;PullStrategy::registry[t1.ai]=&pull;
 EncounterPosition plan;bool ready=false;Event event=0;NaxxramasThaddiusPrepareAction action(d1.ai);
#ifdef MANGOSBOT_ZERO
 assert(NaxxramasThaddiusPreparationPlan(d1.ai,plan,ready)&&!ready&&plan.active&&plan.boss==left.guid);
 assert(!NaxxramasThaddiusPullReady(t1.ai));
 navOkay=false;assert(!action.Execute(event)&&d1.ai->moves==0);navOkay=true;
 navType=4;assert(!action.Execute(event)&&d1.ai->moves==0);navType=PATHFIND_NORMAL;
 nativePath={{d1.x,d1.y,d1.z},{left.x,left.y,left.z},{plan.destination.x,plan.destination.y,plan.destination.z}};
 assert(!action.Execute(event)&&d1.ai->moves==0);nativePath.clear(); // full endpoint alone cannot admit a route through aggro
 d1.ai->path=false;assert(!action.Execute(event)&&d1.ai->moves==0);d1.ai->path=true;
 Spell cast;d1.cast=&cast;assert(!action.Execute(event));d1.cast=nullptr;
 floorDropBelowY=-25; // nominal outward points have no platform floor, as in native trace74646122
 for(auto&brain:brains){NaxxramasThaddiusPrepareAction move(brain.get());for(unsigned i=0;i<5 && move.isUseful();++i)assert(move.Execute(event));assert(!move.isUseful());assert(brain->bot->y>=-25);}
 assert(NaxxramasThaddiusPullReady(t1.ai));assert(t1.x<0&&t2.x>0&&h1.x<0&&h2.x>0&&d1.x<0&&d2.x>0);
 const auto originalStart=pull.start;pull.start+=1;assert(!NaxxramasThaddiusPullReady(t1.ai));pull.start=originalStart;
 d1.instance=2;assert(!NaxxramasThaddiusPreparationPlan(d1.ai,plan,ready));d1.instance=1;
 // The commanded puller is prepared for the actual selected add, including the other platform.
 pull.target=&right;assert(NaxxramasThaddiusPreparationPlan(t1.ai,plan,ready)&&plan.boss==right.guid&&!ready);pull.target=&left;
 pull.pending=false;assert(!NaxxramasThaddiusPreparationPlan(t1.ai,plan,ready));assert(NaxxramasThaddiusPreparationPlan(d1.ai,plan,ready));pull.pending=true;
 for(unsigned fault=0;fault<10;++fault){
  if(fault==0)pull.allowed=false;if(fault==1)pull.start=0;if(fault==2)pull.start=time(nullptr)-60;if(fault==3)t1.ai->authorize=false;
  if(fault==4)human.group=nullptr;if(fault==5)instance.thaddius=IN_PROGRESS;if(fault==6)left.combat=true;if(fault==7)d1.mapid=409;
  if(fault==8)d1.transfer=true;if(fault==9)d1.ai->real=true;
  assert(!NaxxramasThaddiusPreparationPlan(d1.ai,plan,ready));
  pull.allowed=true;pull.start=time(nullptr);t1.ai->authorize=true;human.group=&group;instance.thaddius=0;left.combat=false;d1.mapid=533;d1.transfer=false;d1.ai->real=false;
 }
 h2.healer=false;assert(!NaxxramasThaddiusPullReady(t1.ai));h2.healer=true;
#else
 assert(!NaxxramasThaddiusPreparationPlan(d1.ai,plan,ready)&&NaxxramasThaddiusPullReady(t1.ai));assert(!action.Execute(event));
#endif
 std::cout<<"PASS actual Thaddius preparation: both platforms, native paths, aggro segments, authorized request, cancellation/deadline and era scope\n";
}
'''
source=(root/'playerbot/strategy/actions/ThaddiusPreparationActions.cpp').read_text()
fixture=fixture.replace('__SOURCE__',source[source.index('using namespace ai;'):])
for marker,path in [('__GEOMETRY__','playerbot/strategy/EncounterGeometry.h'),('__POLICY__','playerbot/strategy/ClassicRaidPolicy.h'),('__NATIVE__','playerbot/strategy/NaxxramasNativePolicy.h')]:fixture=fixture.replace(marker,(root/path).as_posix())
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='thaddius-preparation-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(fixture)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
pull=(root/'playerbot/strategy/actions/PullActions.cpp').read_text()
assert '!NaxxramasThaddiusPullReady(ai)' in pull
strategy=(root/'playerbot/strategy/generic/PullStrategy.cpp').read_text()
assert '(action->getName() == "prepare thaddius sides")' in strategy
