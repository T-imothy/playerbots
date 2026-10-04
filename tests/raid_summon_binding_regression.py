"""Exercise actual public-bot raid-save reconciliation for each expansion API."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
body = block((root / 'playerbot/strategy/actions/UseMeetingStoneAction.cpp').read_text(),
             'void SummonAction::PrepareRaidBinding(')
code = r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
using uint32=uint32_t;
enum Difficulty {Normal, Heroic};
struct State {uint32 instance;uint32 GetInstanceId(){return instance;}};
struct InstancePlayerBind {State* state=nullptr;bool perm=true;};
struct InstanceGroupBind {State* state=nullptr;};
struct Data {bool active=false;bool IsEncounterInProgress(){return active;}};
struct Map {bool raid=true;Difficulty difficulty=Normal;State* state=nullptr;Data data;
 bool IsRaid(){return raid;}Difficulty GetDifficulty(){return difficulty;}
 State* GetPersistentState(){return state;}Data* GetInstanceData(){return &data;}};
struct DungeonMap:Map {uint32 count=1,maximum=40;
 uint32 GetPlayersCountExceptGMs(){return count;}uint32 GetMaxPlayers(){return maximum;}};
struct Group {bool raid=true;InstanceGroupBind bind;
 bool IsRaidGroup(){return raid;}
 InstanceGroupBind* GetBoundInstance(uint32 map){assert(map==409);return bind.state?&bind:nullptr;}
 InstanceGroupBind* GetBoundInstance(Map* map,Difficulty d){assert(map->GetDifficulty()==d);return bind.state?&bind:nullptr;}};
struct Session {uint32 account=1000;uint32 GetAccountId(){return account;}};
struct Player {bool real=false,world=true,transfer=false,ai=true;uint32 id=2,map=0,instance=0;
 Session session;Group* group=nullptr;DungeonMap* destination=nullptr;
 InstancePlayerBind binds[2];unsigned unbinds=0;Difficulty lastDifficulty=Normal;
 bool isRealPlayer(){return real;}void* GetPlayerbotAI(){return ai?this:nullptr;}
 Session* GetSession(){return &session;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}
 Group* GetGroup(){return group;}Map* GetMap(){return destination;}
 uint32 GetMapId(){return map;}uint32 GetInstanceId(){return instance;}uint32 GetGUIDLow(){return id;}
 InstancePlayerBind* GetBoundInstance(uint32 m){assert(m==409);return binds[0].state?&binds[0]:nullptr;}
 InstancePlayerBind* GetBoundInstance(uint32 m,Difficulty d){assert(m==409);return binds[d].state?&binds[d]:nullptr;}
 void UnbindInstance(uint32 m){assert(m==409);binds[0].state=nullptr;++unbinds;}
 void UnbindInstance(uint32 m,Difficulty d){assert(m==409);binds[d].state=nullptr;lastDifficulty=d;++unbinds;}
 State* NativeDestination(Difficulty d){return binds[d].state&&binds[d].perm?binds[d].state:group->bind.state;}
};
struct Config {bool IsInRandomAccountList(uint32 a){return a==1000;}}sPlayerbotAIConfig;
struct Log {template<class... A>void outString(const char*,A...) {}}sLog;
struct SummonAction {static void PrepareRaidBinding(Player*,Player*);};
__BODY__
int main(){
 State oldSave{38},raidSave{40},unrelatedSave{77};DungeonMap raid;Group group,other;Player leader,bot;
 auto reset=[&](){raid= {};raid.state=&raidSave;group={};group.bind.state=&raidSave;
  leader={};leader.real=true;leader.id=1;leader.map=409;leader.instance=40;leader.destination=&raid;leader.group=&group;
  bot={};bot.group=&group;bot.binds[0].state=&oldSave;bot.binds[1].state=&unrelatedSave;};
 auto keep=[&](){SummonAction::PrepareRaidBinding(&leader,&bot);assert(bot.unbinds==0&&bot.binds[0].state==&oldSave);};
 reset();assert(bot.NativeDestination(Normal)==&oldSave);
 SummonAction::PrepareRaidBinding(&leader,&bot);
 assert(bot.unbinds==1&&bot.NativeDestination(Normal)==&raidSave&&bot.binds[1].state==&unrelatedSave);
 SummonAction::PrepareRaidBinding(&leader,&bot);assert(bot.unbinds==1);
 reset();bot.real=true;keep();reset();bot.session.account=123;keep(); // Real players/private alts retain lockouts.
 reset();leader.real=false;keep();reset();bot.ai=false;keep();
 reset();bot.world=false;keep();reset();leader.world=false;keep();
 reset();bot.transfer=true;keep();reset();leader.transfer=true;keep();
 reset();bot.group=&other;keep();reset();group.raid=false;keep();reset();raid.raid=false;keep();
 reset();bot.map=409;bot.instance=38;keep(); // A bot inside another copy is never rebound.
 reset();bot.map=409;bot.instance=40;keep(); // Same-map death/near summon never resets the save.
 reset();group.bind.state=&oldSave;keep();reset();group.bind.state=nullptr;keep();
 reset();raid.count=40;keep();reset();raid.data.active=true;keep();
 reset();bot.binds[0].state=&raidSave;SummonAction::PrepareRaidBinding(&leader,&bot);assert(!bot.unbinds);
 reset();bot.binds[0].state=nullptr;SummonAction::PrepareRaidBinding(&leader,&bot);assert(!bot.unbinds);
 SummonAction::PrepareRaidBinding(nullptr,&bot);SummonAction::PrepareRaidBinding(&leader,nullptr);
#ifndef MANGOSBOT_ZERO
 reset();raid.difficulty=Heroic;bot.binds[1].state=&oldSave;
 SummonAction::PrepareRaidBinding(&leader,&bot);
 assert(bot.unbinds==1&&bot.lastDifficulty==Heroic&&bot.binds[0].state==&oldSave&&bot.NativeDestination(Heroic)==&raidSave);
#endif
 // One human + 39 public bots: only nine initially match; all 39 must resolve
 // the group save after reconciliation. Population is below the native cap.
 reset();std::vector<Player> roster(39);unsigned before=0;
 for(unsigned i=0;i<roster.size();++i){auto& p=roster[i];p=bot;p.id=i+2;
  p.binds[0].state=i<9?&raidSave:&oldSave;
  if(p.NativeDestination(Normal)==&raidSave)++before;
  SummonAction::PrepareRaidBinding(&leader,&p);
  assert(p.NativeDestination(Normal)==&raidSave&&p.unbinds==(i<9?0:1));}
 assert(before==9);
 std::cout<<"PASS: actual raid bind reconciliation, mixed 40-person roster, repeat, public/private boundaries, current instances, native capacity/combat and expansion difficulties\n";
}
'''.replace('__BODY__', body)
with tempfile.TemporaryDirectory(prefix='pb-raid-summon-binds-') as temp:
    temp = Path(temp)
    (temp / 'test.cpp').write_text(code, encoding='utf-8')
    for macro in ('MANGOSBOT_ZERO', 'MANGOSBOT_ONE', 'MANGOSBOT_TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/D'+macro,'test.cpp','/Fe:test.exe'],cwd=temp,check=True)
        subprocess.run([str(temp / 'test.exe')],cwd=temp,check=True)
