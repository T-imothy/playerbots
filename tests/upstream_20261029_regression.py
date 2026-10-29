"""Exercise the upstream recovery admission and native ownership fixes."""
from pathlib import Path
import subprocess, tempfile, sys
root=Path(__file__).resolve().parents[1]
core=Path(sys.argv[1]).resolve()
def run(code,label):
    with tempfile.TemporaryDirectory(prefix='upstream-20261029-') as tmp:
        p=Path(tmp);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++20',str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True)
        subprocess.run([str(p/'test.exe')],check=True)
    print('PASS',label)
run('''#include <cassert>
struct Map {bool dungeon=false,raid=false;bool IsDungeon(){return dungeon;}bool IsRaid(){return raid;}};
struct Bot {Map map;bool world=true,alive=true,transfer=false,charm=false,group=false,bg=false,casting=false;
bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return transfer;}
bool HasCharmer(){return charm;}bool GetGroup(){return group;}bool InBattleGround(){return bg;}
Map* GetMap(){assert(world && !transfer);return &map;}
bool IsNonMeleeSpellCasted(bool,bool,bool){return casting;}};
struct AI {Bot bot;bool real=false,master=false,movable=true;bool IsRealPlayer(){return real;}
bool HasRealPlayerMaster(){return master;}Bot* GetBot(){return &bot;}bool CanMove(){return movable;}};
#include "'''+(root/'playerbot/strategy/SoloMovementRecovery.h').as_posix()+'''"
int main(){AI ai;assert(ai::CanUseSoloMovementRecovery(&ai));assert(!ai::CanUseSoloMovementRecovery<AI>(nullptr));
bool* blocks[]={&ai.real,&ai.master,&ai.bot.transfer,&ai.bot.charm,&ai.bot.group,&ai.bot.bg,&ai.bot.casting,&ai.bot.map.dungeon,&ai.bot.map.raid};
for(bool* flag:blocks){*flag=true;assert(!ai::CanUseSoloMovementRecovery(&ai));*flag=false;assert(ai::CanUseSoloMovementRecovery(&ai));}
bool* required[]={&ai.bot.world,&ai.bot.alive,&ai.movable};
for(bool* flag:required){*flag=false;assert(!ai::CanUseSoloMovementRecovery(&ai));*flag=true;}
}''','recovery excludes groups, raids, dungeons, BGs, humans, transfers, CC and active casts')
actions=(root/'playerbot/strategy/actions/UnstuckAction.cpp').read_text()
for name in ('DropStandoffAction','ReleaseStuckMovementAction'):
    part=actions.split('bool '+name+'::Execute(Event& event)',1)[1].split('\n}',1)[0]
    assert part.index('CanUseSoloMovementRecovery(ai)')<part.index('SET_AI_VALUE'),name
cc=(root/'playerbot/strategy/values/CcTargetValue.cpp').read_text()
assert cc.index('if (GarrBanishAssignment(ai, qualifier, assigned))')<cc.index('    FindTargetForCcStrategy strategy(ai, qualifier);')
callback=core/'src/framework/Utilities/Callback.h'
if 'requires(std::invocable' in callback.read_text():
    run('''#include <cassert>
#include <functional>
struct QueryResult {static inline int alive=0;QueryResult(){++alive;}~QueryResult(){--alive;}};
#include "'''+callback.as_posix()+'''"
int main(){int calls=0;
 {auto fn=[&](std::unique_ptr<QueryResult> p){++calls;assert(p);};MaNGOS::QueryCallback cb(std::move(fn));cb.SetResult(std::make_unique<QueryResult>());cb.Execute();assert(calls==1 && QueryResult::alive==0);}
 {auto fn=[&](std::unique_ptr<QueryResult> p){++calls;};MaNGOS::QueryCallback cb(std::move(fn));cb.SetResult(std::make_unique<QueryResult>());assert(QueryResult::alive==1);}assert(calls==1 && QueryResult::alive==0);
 {auto fn=[&](QueryResult* p){++calls;delete p;};MaNGOS::QueryCallback cb(std::move(fn));cb.SetResult(std::make_unique<QueryResult>());cb.Execute();}assert(calls==2 && QueryResult::alive==0);
}''','TBC owned/raw query callbacks release results on execution and cancellation')
    db=(core/'src/shared/Database/DatabaseImpl.h').read_text()
    priority=db.split('Database::AsyncPQueryPriority(Callable callback',1)[1].split('\n}',1)[0]
    assert 'AsyncQuery(std::move(callback), szQuery, true)' in priority
    enum=(core/'src/game/Entities/CharacterHandler.cpp').read_text().split('void WorldSession::HandleCharEnumOpcode',1)[1].split('\n}',1)[0]
    assert 'AsyncPQueryPriority(std::move(queryCallback)' in enum
else:
    print('SKIP owned callback variant: native core retains its existing callback API')
loot=(core/'src/game/Loot/LootMgr.cpp').read_text()
if '    // Stop any ongoing group loot rolls.' in loot:
    destructor=loot.split('Loot::~Loot()\n',1)[1].split('\n}\n',1)[0]+'\n}'
    run('''#include <cassert>
#include <vector>
#include <map>
struct Item {static inline int alive=0;Item(){++alive;}~Item(){--alive;}};
struct Roll {~Roll(){assert(Item::alive>0);}};
struct Loot {std::map<int,Roll> m_roll;std::vector<Item*> m_lootItems;void SendReleaseForAll(){}~Loot();};
Loot::~Loot()\n'''+destructor+'''
int main(){{Loot loot;loot.m_lootItems.push_back(new Item);loot.m_roll.try_emplace(1);}assert(Item::alive==0);}''','Classic loot rolls are destroyed before their referenced items')
print('PASS upstream integration guards')
