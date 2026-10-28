"""Actual explicit-request Gothik preparation, formation, admission and cancellation."""
from pathlib import Path
import ast,subprocess,tempfile

root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'tests/naxxramas_roles_regression.py').read_text())
fixture=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fixture' for t in n.targets))
fixture=fixture.split('__SOURCE__')[0]
fixture=fixture.replace('#include <algorithm>','#include <algorithm>\n#include <ctime>\n#include <memory>')
fixture=fixture.replace('float GetDistance(Unit*u){','float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}float GetDistance(Unit*u){')
fixture=fixture.replace('bool IsBeingTeleported(){','bool IsNonMeleeSpellCasted(bool){return cast!=nullptr;}bool IsBeingTeleported(){')
fixture=fixture.replace('unsigned validations=0;','unsigned validations=0,moves=0;bool move=true,authorize=true;bool CanMove(){return move;}')
fixture=fixture.replace('struct Action{virtual ~Action()=default;};','struct Action{virtual ~Action()=default;std::string name;const std::string&getName(){return name;}};')
fixture+=r'''
bool CanManageBotCommands(PlayerbotAI*a,Player*){return a->authorize;}
struct PullStrategy{static std::map<PlayerbotAI*,PullStrategy*>registry;Unit*target=nullptr;bool allowed=true,pending=true,issued=false;time_t start=time(nullptr);ObjectGuid requester;
 static PullStrategy*Get(PlayerbotAI*a){return registry[a];}Unit*GetTarget(){return target;}bool IsEncounterPreparationAllowed(){return allowed;}
 bool IsPullPendingToStart(){return pending;}bool HasPullStarted(){return start!=0;}bool HasPullActionIssued(){return issued;}
 time_t GetPullStartTime(){return start;}unsigned GetMaxPullTime(){return 15;}ObjectGuid GetRequester(){return requester;}};
std::map<PlayerbotAI*,PullStrategy*>PullStrategy::registry;
namespace ai{
bool NaxxramasGothikPullReady(PlayerbotAI*);bool NaxxramasGothikPreparationPlan(PlayerbotAI*,EncounterPosition&,bool&);
bool EncounterMovementRequired(Player*p,const encounter::Point&q){return p->GetDistance(q.x,q.y,q.z)>1.5f;}
float RazuviousPreparationMultiplier(PlayerbotAI*,Action*){return 1;}
struct NaxxramasGothikPrepareAction{PlayerbotAI*ai;Player*bot;NaxxramasGothikPrepareAction(PlayerbotAI*a):ai(a),bot(a->GetBot()){}
 bool isUseful();bool Execute(unsigned&);bool IsReaction(){return false;}bool MoveTo(unsigned,float x,float y,float z,bool,bool,bool,bool){++ai->moves;bot->x=x;bot->y=y;bot->z=z;return true;}};
struct PreserveNaxxramasPreparation{PlayerbotAI*ai;float GetValue(Action*);};
}
using Event=unsigned;
__SOURCE__
int main(){
 Map map;ScriptedInstance instance;map.instance=&instance;Group group;GameObject gate;gate.guid=90;gate.map=&map;gate.state=1;instance.gate=&gate;
 Unit boss;boss.guid=50;boss.map=&map;boss.entry=16060;boss.combat=false;boss.x=-40;boss.y=-27;boss.z=18;
 Player t1,t2,h1,h2,d1,d2,human;Player*players[]={&t1,&t2,&h1,&h2,&d1,&d2,&human};unsigned id=1;
 std::vector<std::unique_ptr<PlayerbotAI>>brains;
 for(auto*p:players){p->guid=id++;p->map=&map;p->group=&group;p->combat=false;group.Add(p);if(p!=&human)brains.emplace_back(new PlayerbotAI(p));}
 t1.tank=t2.tank=true;h1.healer=h2.healer=true;
 for(auto&brain:brains){brain->units[boss.guid.id]=&boss;brain->units[human.guid.id]=&human;}
 PullStrategy pull;pull.target=&boss;pull.requester=human.guid;PullStrategy::registry[t1.ai]=&pull;
 EncounterPosition plan;bool ready=false;assert(NaxxramasGothikPreparationPlan(d1.ai,plan,ready)&&!ready&&plan.active);
 assert(!NaxxramasGothikPullReady(t1.ai));Action follow;follow.name="follow";PreserveNaxxramasPreparation keep{d1.ai};assert(keep.GetValue(&follow)==0);
 Action heal;heal.name="greater heal";assert(keep.GetValue(&heal)==1);
 Event event=0;NaxxramasGothikPrepareAction action(d1.ai);d1.ai->path=false;assert(!action.Execute(event)&&d1.ai->moves==0);d1.ai->path=true;
 Spell cast;d1.cast=&cast;assert(!action.Execute(event));d1.cast=nullptr;
 for(auto&brain:brains){NaxxramasGothikPrepareAction move(brain.get());assert(move.Execute(event));}
 assert(NaxxramasGothikPreparationPlan(t1.ai,plan,ready)&&ready&&NaxxramasGothikPullReady(t1.ai));
 assert(t1.y<0&&t2.y>0&&h1.y<0&&h2.y>0);assert(!action.isUseful());
 h2.alive=false;assert(NaxxramasGothikPreparationPlan(t1.ai,plan,ready)&&!ready);h2.alive=true;
 pull.allowed=false;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready)&&keep.GetValue(&follow)==1);pull.allowed=true;
 pull.pending=false;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready));pull.pending=true;
 pull.target=nullptr;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready));pull.target=&boss;
 boss.entry=15990;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready)&&NaxxramasGothikPullReady(t1.ai));boss.entry=16060;
 pull.start=time(nullptr)-15;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready)&&!NaxxramasGothikPullReady(t1.ai));pull.start=time(nullptr);
 gate.state=GO_STATE_READY;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready));gate.state=1;
 gate.instance=2;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready));gate.instance=1;
 t1.ai->authorize=false;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready));t1.ai->authorize=true;
 human.group=nullptr;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready));human.group=&group;
 boss.combat=true;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready));boss.combat=false;
 d1.transfer=true;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready));d1.transfer=false;
 d1.mapid=409;assert(!NaxxramasGothikPreparationPlan(d1.ai,plan,ready)&&NaxxramasGothikPullReady(d1.ai));
 std::cout<<"PASS actual Gothik explicit preparation, native gate, balanced roles, route, cancellation and deadline\n";
}
'''
source=(root/'playerbot/strategy/actions/NaxxramasPreparationActions.cpp').read_text()
fixture=fixture.replace('__SOURCE__',source[source.index('using namespace ai;'):])
for marker,path in [('__GEOMETRY__','playerbot/strategy/EncounterGeometry.h'),('__POLICY__','playerbot/strategy/ClassicRaidPolicy.h'),('__NATIVE__','playerbot/strategy/NaxxramasNativePolicy.h')]:
    fixture=fixture.replace(marker,(root/path).as_posix())
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='naxx-preparation-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(fixture)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
pull=(root/'playerbot/strategy/actions/PullActions.cpp').read_text()
assert '!NaxxramasGothikPullReady(ai)' in pull and 'Gothik pull stopped:' in pull
assert 'SetEncounterPreparationAllowed' in pull
strategy=(root/'playerbot/strategy/generic/PullStrategy.cpp').read_text()
assert '(action->getName() == "prepare gothik sides")' in strategy
assert strategy.count('encounterPreparationAllowed = false;') >= 2
