"""Verify actual owner/group/master aggregation without the malformed donor cache."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/values/AttackersValue.cpp').read_text()
method = block(source, 'std::list<ObjectGuid> AttackersValue::Calculate(')
code = r'''
#include <cassert>
#include <list>
#include <set>
#include <string>
#include <iostream>
using ObjectGuid=unsigned;using std::stoi;
enum {ALL_ACTIVITY,UNIT_FIELD_FLAGS,UNIT_FLAG_CLIENT_CONTROL_LOST};
namespace BotState {enum {BOT_STATE_COMBAT};}
struct Unit {ObjectGuid guid=0;bool world=true;unsigned map=0;
 bool IsInWorld(){return world;}unsigned GetMapId(){return map;}ObjectGuid GetObjectGuid(){return guid;}};
struct Group {};
struct Player:Unit {bool teleport=false,flying=false,controlLost=false,bg=false;Group* group=nullptr;
 bool IsBeingTeleported(){return teleport;}bool IsFlying(){return flying;}
 bool HasFlag(int,int){return controlLost;}bool InBattleGround(){return bg;}Group* GetGroup(){return group;}};
struct WorldPosition {WorldPosition(Player*){}float currentHeight(){return 20;}};
struct PlayerbotAI {bool activity=true,focus=false;Unit* marked=nullptr;
 bool AllowActivity(int){return activity;}bool HasStrategy(const char*,int){return focus;}};
namespace ai {
struct AttackersValue {Player* bot;PlayerbotAI* ai;Player* master=nullptr;std::string qualifier;
 std::set<Unit*> own,groupTargets,masterTargets;unsigned ownCalls=0,groupCalls=0,masterCalls=0;
 Player* GetMaster(){return master;}std::list<ObjectGuid> Calculate();
 void AddTargetsOf(Player* p,std::set<Unit*>& out,std::set<ObjectGuid>&,bool one){
  if(p==bot)++ownCalls;else ++masterCalls;auto& incoming=p==bot?own:masterTargets;
  for(Unit* u:incoming){out.insert(u);if(one)break;}}
 void AddTargetsOf(Group*,std::set<Unit*>& out,std::set<ObjectGuid>&,bool one){
  ++groupCalls;for(Unit* u:groupTargets){out.insert(u);if(one)break;}}
};
}
using namespace ai;
#define AI_VALUE(type,key) ai->marked
__METHOD__
int main(){
 // The original expression conditions on a non-null pointer, so even an empty
 // qualifier produces "::". No valid attackers key was ever selected by it.
 for(const std::string qualifier:{std::string{},std::string{"1"},std::string{"0"}}){
  const std::string legacy = "attackers" + !qualifier.empty() ? "::" + qualifier : "";
  assert(legacy=="::"+qualifier);
  assert(legacy!=(std::string("attackers")+(qualifier.empty()?"":"::"+qualifier)));
 }
 Player bot,master;PlayerbotAI ai;AttackersValue value{&bot,&ai};Group group,otherGroup;
 Unit direct,petOrDuel,party,leader;direct.guid=1;petOrDuel.guid=2;party.guid=3;leader.guid=4;
 value.own={&direct,&petOrDuel};value.groupTargets={&party};value.masterTargets={&leader};
 auto ids=[&](){auto result=value.Calculate();return std::set<unsigned>(result.begin(),result.end());};
 assert(ids()==(std::set<unsigned>{1,2}));
 bot.group=&group;value.master=&master;master.group=&otherGroup;
 assert(ids()==(std::set<unsigned>{1,2,3,4}));
 master.group=&group;assert(ids()==(std::set<unsigned>{1,2,3}));
 bot.bg=true;assert(ids()==(std::set<unsigned>{1,2}));bot.bg=false;
 value.qualifier="1";value.groupCalls=value.masterCalls=0;assert(ids().size()==1);
 assert(value.groupCalls==0&&value.masterCalls==0);
 value.own.clear();assert(ids()==(std::set<unsigned>{3}));
 value.groupTargets.clear();master.group=&otherGroup;assert(ids()==(std::set<unsigned>{4}));
 value.masterTargets.clear();assert(ids().empty());value.qualifier.clear();value.own={&direct};
 bot.world=false;assert(ids().empty());bot.world=true;
 bot.teleport=true;assert(ids().empty());bot.teleport=false;
 bot.controlLost=true;assert(ids().empty());bot.controlLost=false;
 bot.flying=true;assert(ids().empty());bot.flying=false;
 ai.activity=false;assert(ids().empty());ai.activity=true;
 ai.focus=true;ai.marked=&party;assert(ids()==(std::set<unsigned>{3}));ai.marked=nullptr;assert(ids().empty());
 std::cout<<"PASS: actual attacker aggregation retains own/group/master, one-target fallback and activity gates without foreign cache reads\n";
}
'''.replace('__METHOD__', method)
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-attacker-aggregation-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{era}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
assert 'GetUntypedValue' not in method and 'nearest friendly players' not in method
# Individual collection still includes native attackers, duel opponents and pet attackers.
individual = block(source, 'void AttackersValue::AddTargetsOf(Player*')
for marker in ('player->getAttackers()', 'bot->duel->opponent', 'pet->getAttackers()',
               '"current target"', '"old target"', '"pull target"', '"attack target"'):
    assert marker in individual
