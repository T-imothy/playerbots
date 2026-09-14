from pathlib import Path
import sys
r=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(r/'modules/ManTechPlayerbots/tests'))
from turtle_cpp_fixture import run
s=(r/'modules/ManTechPlayerbots/playerbot/strategy/actions/ChooseTravelTargetAction.cpp').read_text()
def body(needle):
 start=s.index(needle);i=s.index('{',start);depth=1;j=i+1
 while depth:
  depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[start:j]
classes=['ChooseTravelTargetAction','ChooseGroupTravelTargetAction','RefreshTravelTargetAction','ResetTargetAction','RequestTravelTargetAction']
methods=[]
for cls in classes:
 b=body('bool '+cls+'::RequiresWorldOwner() const')
 assert 'futureDestinations' not in b and 'IsTravelSearchPending' not in b
 methods.append(b)
 useful=body('bool '+cls+'::isUseful()')
 assert useful[useful.index('{')+1:].lstrip().startswith('if (!RequiresWorldOwner())\n        return false;')
for cls in classes[1:4]:
 assert 'IsTravelUseful()' in body('bool '+cls+'::isUseful()')
assert 'bool ChooseTravelTargetAction::IsTravelUseful()' in s
run(r'''
#include <cassert>
#include <string>
#include <cstdio>
enum class TravelStatus {TRAVEL_STATUS_NONE,TRAVEL_STATUS_PREPARE,TRAVEL_STATUS_READY,TRAVEL_STATUS_TRAVEL,TRAVEL_STATUS_WORK,TRAVEL_STATUS_COOLDOWN,TRAVEL_STATUS_EXPIRED};
struct TravelTarget {TravelStatus status;TravelStatus GetStatus()const{return status;}} target;
struct Bot {bool bg=false,group=false,overworld=false;bool InBattleGround()const{return bg;}bool GetGroup()const{return group;}} actor;
struct WorldPosition {Bot* b;WorldPosition(Bot*p):b(p){}bool isOverworld()const{return b->overworld;}};
bool active=false,noDest=false;
template<class T>T value(char const*);
template<>TravelTarget* value<TravelTarget*>(char const*){return &target;}
template<>bool value<bool>(char const*){return active;}
#define AI_VALUE(T,N) value<T>(N)
#define AI_VALUE2(T,N,Q) noDest
struct ChooseTravelTargetAction {Bot*bot=&actor;bool RequiresWorldOwner()const;};
struct ChooseGroupTravelTargetAction:ChooseTravelTargetAction {bool RequiresWorldOwner()const;};
struct RefreshTravelTargetAction:ChooseTravelTargetAction {bool RequiresWorldOwner()const;};
struct ResetTargetAction:ChooseTravelTargetAction {bool RequiresWorldOwner()const;};
struct RequestTravelTargetAction:ChooseTravelTargetAction {std::string getQualifier()const{return "quest";}bool RequiresWorldOwner()const;};
'''+ '\n'.join(methods)+r'''
int main(){unsigned checked=0;
 for(int status=0;status<7;++status)for(unsigned flags=0;flags<32;++flags){
 target.status=TravelStatus(status);actor.bg=flags&1;actor.group=flags&2;actor.overworld=flags&4;active=flags&8;noDest=flags&16;
 bool preparing=target.status==TravelStatus::TRAVEL_STATUS_PREPARE;
 assert(ChooseTravelTargetAction{}.RequiresWorldOwner()==(preparing&&!active));
 assert(ChooseGroupTravelTargetAction{}.RequiresWorldOwner()==(!actor.bg&&actor.group&&!preparing&&!active));
 assert(RefreshTravelTargetAction{}.RequiresWorldOwner()==(!actor.bg&&!preparing&&actor.overworld&&!active));
 assert(ResetTargetAction{}.RequiresWorldOwner()==(!actor.bg&&!preparing&&!active));
 assert(RequestTravelTargetAction{}.RequiresWorldOwner()==(!actor.bg&&!preparing&&!active&&!noDest));
 ++checked;
 }
 printf("PASS %u travel-state combinations; every rejected handoff exits usefulness before group/world checks; viable work still requires world owner\n",checked);
}
''')
