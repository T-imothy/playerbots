"""Exercise group membership transitions and complete qualified-member counts."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

source = (Path(__file__).resolve().parents[1] / 'playerbot/strategy/values/GroupValues.cpp').read_text()
methods = '\n'.join(block(source, key) for key in ('std::list<ObjectGuid> GroupMembersValue::Calculate(', 'uint32 GroupBoolCountValue::Calculate('))
code = r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <list>
#include <map>
using ObjectGuid=unsigned;using uint32=uint32_t;
struct Player;struct GroupReference {Player* member;GroupReference* following;
 Player* getSource(){return member;}GroupReference* next(){return following;}};
struct Group {GroupReference* first;GroupReference* GetFirstMember(){return first;}};
struct PlayerbotAI {std::list<ObjectGuid> members;bool IsSafe(Player*);};
struct Player {ObjectGuid guid;Group* group=nullptr;PlayerbotAI* ai=nullptr;bool safe=true,qualified=false;
 ObjectGuid GetObjectGuid(){return guid;}Group* GetGroup(){return group;}PlayerbotAI* GetPlayerbotAI(){return ai;}};
bool PlayerbotAI::IsSafe(Player* p){return p->safe;}
struct {std::map<ObjectGuid,Player*> players;Player* GetPlayer(ObjectGuid id){return players[id];}} sObjectMgr;
#define AI_VALUE(type,name) ai->members
#define PAI_VALUE2(type,name,qualifier) player->qualified
struct GroupMembersValue {Player* bot;std::list<ObjectGuid> Calculate();};
struct GroupBoolCountValue {PlayerbotAI* ai;uint32 Calculate();};
__METHODS__
int main(){
 PlayerbotAI ai;Player bot{1,nullptr,&ai},other{2,nullptr,&ai},human{3},departed{4,nullptr,&ai};
 GroupMembersValue members{&bot};assert(members.Calculate()==std::list<ObjectGuid>{1});
 GroupReference last{&other,nullptr},missing{nullptr,&last},first{&bot,&missing};Group group{&first};bot.group=&group;
 assert((members.Calculate()==std::list<ObjectGuid>{1,2})); // A departing reference must not crash or stop traversal.
 ai.members={1,2,3,4,5};sObjectMgr.players={{1,&bot},{2,&other},{3,&human},{4,&departed}};
 GroupBoolCountValue count{&ai};assert(count.Calculate()==0);
 bot.qualified=true;assert(count.Calculate()==1);other.qualified=true;assert(count.Calculate()==2);
 human.qualified=true;departed.qualified=true;departed.safe=false;assert(count.Calculate()==2);
 bot.qualified=false;assert(count.Calculate()==1);ai.members.clear();assert(count.Calculate()==0);
 std::cout<<"PASS: solo/group/departing membership and zero/one/multiple eligible bot counts\n";
}
'''.replace('__METHODS__', methods)
with tempfile.TemporaryDirectory(prefix='mantech-group-membership-') as folder:
    tmp = Path(folder)
    (tmp / 'test.cpp').write_text(code)
    subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
    subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
