"""Native-pack evidence accounting: absence is not a kill, respawn revokes death."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <algorithm>
#include <map>
#include <vector>
#include <set>
#include <iostream>
using uint32=unsigned;
using ObjectGuid=unsigned;
struct Creature{unsigned guid;bool alive=true;unsigned GetObjectGuid(){return guid;}bool IsAlive(){return alive;}};
struct TestContext{std::set<ObjectGuid>raidLabPackMembers,raidLabPackDead;};
'''+block(source,'bool RaidLabObservePackDeath(')+block((root/'playerbot/strategy/tests/RaidLabPacks.h').read_text(),
 'inline std::map<uint32,std::vector<uint32>> RaidLabLinkedComponents(')+r'''
int main(){
 TestContext c;c.raidLabPackMembers={1,2};Creature one{1},two{2},foreign{3,false};
 assert(!RaidLabObservePackDeath(c,1,nullptr)&&c.raidLabPackDead.empty());
 assert(!RaidLabObservePackDeath(c,1,&foreign)&&c.raidLabPackDead.empty());
 assert(!RaidLabObservePackDeath(c,3,&foreign)&&c.raidLabPackDead.empty());
 assert(!RaidLabObservePackDeath(c,1,&one));one.alive=false;
 assert(RaidLabObservePackDeath(c,1,&one));assert(!RaidLabObservePackDeath(c,1,&one));
 assert(c.raidLabPackDead.size()==1);assert(!RaidLabObservePackDeath(c,2,nullptr));
 two.alive=false;assert(RaidLabObservePackDeath(c,2,&two));assert(c.raidLabPackDead==c.raidLabPackMembers);
 // Loot/removal after an observed death retains evidence; native respawn does not.
 assert(!RaidLabObservePackDeath(c,1,nullptr)&&c.raidLabPackDead.size()==2);
 one.alive=true;assert(!RaidLabObservePackDeath(c,1,&one)&&c.raidLabPackDead.size()==1);
 one.alive=false;assert(RaidLabObservePackDeath(c,1,&one)&&c.raidLabPackDead.size()==2);
 auto components=RaidLabLinkedComponents({{3,{2}},{2,{1,3}},{1,{2}},{7,{8}},{8,{7}},{9,{9}}});
 assert(components.size()==2&&components.at(1)==std::vector<unsigned>({1,2,3})&&components.at(7)==std::vector<unsigned>({7,8}));
 assert(RaidLabLinkedComponents({}).empty());
 std::map<unsigned,std::set<unsigned>> huge;
 for(unsigned n=1;n<65;++n){huge[n].insert(n+1);huge[n+1].insert(n);}
 assert(RaidLabLinkedComponents(huge).empty()); // Oversized linked event is not a small-pack fixture.
 std::cout<<"PASS native pack identity, missing actors, duplicate deaths and respawn invalidation\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-pack-evidence-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True)
command=block(source,'TestResult CommandRaidLabPack::Execute(')
for guard in ['RaidLab::Enabled()', 'RaidLab::AllowedMap', 'GetLeaderGuid()', 'ctx.testName!=',
              'IsWorldstateConditionSatisfied()', 'GetGuidEntry', 'creature->GetEntry()!=activeEntry',
              'creature->IsWorldBoss()', 'RaidLabPartyReady', 'bot->IsGameMaster()',
              'RaidLab::Controlled(bot)', 'GetMembersCount()!=expected']:
 assert guard in command,guard
assert command.count('HandleCommand(CHAT_MSG_WHISPER,"pull",*bot)')==1
assert 'ctx.combatSeen|=fighting' not in command
assert 'creature->GetObjectGuid()==guid && creature->IsInCombat()) ctx.combatSeen=true' in command
for forbidden in ['SetHealth(', 'AttackStart(', 'SetInCombat', 'SummonCreature(', 'SetData(', '.Spawn(', '->Spawn(']:
 assert forbidden not in command,forbidden
assert 'now-ctx.raidLabEventStarted>900000' in command
assert 'now-ctx.raidLabPostKillStarted>180000' in command
assert 'now-ctx.raidLabPostKillStarted<30000' in command
print('PASS isolated pack command guards and bounded ordinary-pull/recovery contract; native mechanics unvalidated')
