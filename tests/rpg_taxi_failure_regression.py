"""Exercise the production taxi action's failure cleanup in all three cores."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
body = block((root/'playerbot/strategy/actions/RpgSubActions.cpp').read_text(),
             'bool RpgTaxiAction::Execute(Event& event)')
stubs = r'''
#include <cassert>
#include <cstdint>
#include <vector>
#include <string>
#include <initializer_list>
using uint32 = uint32_t;
constexpr unsigned UNIT_NPC_FLAG_FLIGHTMASTER=1;
constexpr unsigned UNIT_FIELD_FLAGS=1,UNIT_FLAG_CLIENT_CONTROL_LOST=2;
struct Event{}; struct Creature{};
struct GuidPosition {float getX(){return 0;} float getY(){return 0;} float getZ(){return 0;} unsigned getMapId(){return 0;}};
struct TaxiPathEntry {unsigned from=1,to=2;};
struct TaxiNodesEntry {const char* name[1]={"node"};unsigned map_id=0;float x=0,y=0,z=0;};
struct Paths {bool empty=false; TaxiPathEntry entry; unsigned GetNumRows(){return empty?0:1;} TaxiPathEntry* LookupEntry(unsigned){return &entry;}} sTaxiPathStore;
struct Nodes {bool missing=false;TaxiNodesEntry entry;TaxiNodesEntry* LookupEntry(unsigned){return missing?nullptr:&entry;}} sTaxiNodesStore;
struct ObjMgr {unsigned GetNearestTaxiNode(float,float,float,unsigned,unsigned){return 1;}} sObjectMgr;
struct Log {template<class...T>void outError(const char*,T...){} template<class...T>void outDetail(const char*,T...){} } sLog;
unsigned urand(unsigned lo,unsigned){return lo;}
struct Bot {
 struct Taxi {bool IsTaximaskNodeKnown(unsigned){return true;}}m_taxi;
 unsigned money=777,attempts=0; bool master=true,success=false; Creature creature;
 unsigned GetMoney(){return money;} void SetMoney(unsigned n){money=n;}
 unsigned GetTeam(){return 0;} bool isTaxiCheater(){return false;}
 const char* GetName(){return "bot";} unsigned GetGUIDLow(){return 1;}
 unsigned GetMapId(){return 0;}float GetPositionX(){return 0;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}
 bool IsInCombat(){return false;}bool IsNonMeleeSpellCasted(bool){return false;}unsigned GetMountID(){return 0;}bool HasFlag(unsigned,unsigned){return false;}
 Creature* GetNPCIfCanInteractWith(GuidPosition,unsigned){return master?&creature:nullptr;}
 void OnTaxiFlightEject(bool){} void ResolvePendingMount(){}
 bool ActivateTaxiPathTo(std::initializer_list<unsigned>,Creature*,unsigned){++attempts; if(success)money-=10;return success;}
};
struct AI {void Unmount(){}};
struct Rpg {std::string next;void BeforeExecute(){} GuidPosition guidP(){return {};}
 void AfterExecute(bool=true,bool=false,std::string action="rpg"){next=action;}};
struct RpgTaxiAction {Bot* bot;AI* ai;Rpg* rpg;unsigned delays=0;void DoDelay(){++delays;}bool Execute(Event&);};
'''
tests = r'''
int main(){Event e;AI ai;
 for(int mode=0;mode<6;++mode){Bot bot;Rpg rpg;RpgTaxiAction action{&bot,&ai,&rpg};
 sTaxiPathStore.empty=mode==0;sTaxiNodesStore.missing=mode==1;bot.master=mode!=2;
 bot.success=mode>=4;if(mode==5)bot.money=UINT32_MAX-5;unsigned before=bot.money;
 bool result=action.Execute(e);assert(result==(mode>=4));assert(bot.money==before);
 assert(action.delays==1);assert(rpg.next==(result?"rpg":"rpg cancel"));
 assert(bot.attempts==(mode>=3?1u:0u));}
}
'''
with tempfile.TemporaryDirectory(prefix='pb-taxi-') as folder:
    path=Path(folder); cpp=path/'test.cpp'; exe=path/'test.exe'
    cpp.write_text(stubs+body+tests)
    for macro in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/D'+macro,str(cpp),'/Fe:'+str(exe),'/Fo:'+str(path/'test.obj')],check=True)
        subprocess.run([str(exe)],check=True)
        print('PASS:',macro,'taxi refusal cleanup, invalid endpoints, money preservation, success and overflow')
