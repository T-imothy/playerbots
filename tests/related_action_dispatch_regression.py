# Exercise actual dynamic dispatch gates and fallback branches against controlled game interfaces.
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
root=Path(__file__).resolve().parents[1];before='--before' in sys.argv
def source(f):
 if before:return subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),'show','0df8d31e45508c41fe04748ac7a493fd9c01cc51:'+f],text=True)
 return (root/f).read_text()
generic=source('playerbot/strategy/actions/GenericSpellActions.cpp');paladin=source('playerbot/strategy/paladin/PaladinActions.cpp');engine=source('playerbot/strategy/Engine.cpp')
fixture=(root/'tests/reflect_cast_regression.py').read_text().split("code = r'''\n",1)[1].split('int main(){',1)[0]
fixture=fixture.replace('#include <string>','#include <string>\n#include <atomic>')
fixture=fixture.replace('struct PlayerbotAI {bool learned=true;bool HasSpell(unsigned){return learned;}', 'struct PlayerbotAI {bool learned=true,vehicle=false;unsigned vehicleSpell=0,lastCast=0;bool HasSpell(unsigned id){return learned&&id!=0;}bool CanCastVehicleSpell(unsigned id,Unit*){return vehicle&&id&&id==vehicleSpell;}bool CastVehicleSpell(unsigned id,Unit*t,float,bool){lastCast=id;return CanCastVehicleSpell(id,t);}')
fixture=fixture.replace('return false;}};\nbool ShouldAvoidCorruptedHealing','return vehicle;}};\nbool ShouldAvoidCorruptedHealing')
start=fixture.index('struct CastSpellAction {');end=fixture.index('__METHOD__',start)
fixture=fixture[:start]+r'''
struct Event {std::string getSource(){return "trigger";}};
struct CastSpellAction {Player* bot;PlayerbotAI* ai;Unit* target;unsigned spellId=0,resolvedId=0;float range=30;
 std::string spellName="dispatcher",spellIdContext="spell id";bool useful=true;
 virtual ~CastSpellAction()=default;
 void RefreshSpellId(){spellId=spellIdContext=="vehicle spell id"?ai->vehicleSpell:resolvedId;}
 Unit* GetTarget(){return target;}virtual bool isUseful();bool ShouldTryAlternativesWhenUseless();
 void SetSpellName(std::string n){spellName=n;resolvedId=n.empty()?0:1;RefreshSpellId();}
 unsigned GetSpellID(){return spellId;}bool isUsefulWhenStunned(){return false;}std::string getName(){return spellName;}
};
#define AI_VALUE2(type,key,value) useful
'''+fixture[end:]
fixture=fixture.replace('__METHOD__',block(generic,'bool CastSpellAction::isUseful('))
if 'bool CastSpellAction::ShouldTryAlternativesWhenUseless(' in generic:fixture+=block(generic,'bool CastSpellAction::ShouldTryAlternativesWhenUseless(')
else:fixture+='bool CastSpellAction::ShouldTryAlternativesWhenUseless(){return false;}\n'
fixture+=r'''
struct CastBlessingOnPartyAction:CastSpellAction {std::string blessing="blessing of might";std::string GetBlessingForTarget(Unit*){return blessing;}__BLESS_DECL__};
struct CastVehicleSpellAction:CastSpellAction {float speed=30;bool needTurn=true;bool isUseful()override;bool isPossible();bool Execute(Event&);};
'''.replace('__BLESS_DECL__','bool isUseful()override;' if 'bool CastBlessingOnPartyAction::isUseful()' in paladin else '')
if 'bool CastBlessingOnPartyAction::isUseful()' in paladin:fixture+=block(paladin,'bool CastBlessingOnPartyAction::isUseful(')
for n in ('isUseful','isPossible','Execute'):fixture+=block(generic,'bool CastVehicleSpellAction::'+n+'(')+'\n'
fixture+=r'''
struct Node{const char* getAlternatives(){return "fallback";}};
struct CombatDiagnostics {static bool Select(PlayerbotAI*){return false;}template<class...T>static void Record(T...){}};
enum ActionResult{ACTION_RESULT_FAILED,ACTION_RESULT_IMPOSSIBLE};
struct Engine {PlayerbotAI* ai;CastSpellAction* action;Event event;float relevance=10;bool isStunned=false,collectDiagnostics=false;
 std::atomic<unsigned> suppressedImpossibleActions{0},suppressedFailedActions{0};struct {int suppressedImpossible=0,suppressedFailed=0;}diagnosticSample;
 unsigned alternatives=0;bool IsFailureBackedOff(CastSpellAction*,Event&,ActionResult){return true;}
 void MultiplyAndPush(const char*,float,bool,Event&,const char*){++alternatives;}
 void missing(){Node* actionNode=new Node;__MISSING__ delete actionNode;}
 void cachedImpossible(){Node* actionNode=new Node;for(bool once=true;once;once=false){__IMPOSSIBLE__}}
 void cachedFailed(){Node* actionNode=new Node;for(bool once=true;once;once=false){__FAILED__}}
};
'''
marker='if ((!isStunned || action->isUsefulWhenStunned()) && action->ShouldTryAlternativesWhenUseless())'
missing=engine[engine.index(marker):].split(';',1)[0]+';' if marker in engine else ''
fixture=fixture.replace('__MISSING__',missing).replace('__IMPOSSIBLE__',block(engine,'if (IsFailureBackedOff(action, event, ACTION_RESULT_IMPOSSIBLE))')).replace('__FAILED__',block(engine,'if (IsFailureBackedOff(action, event, ACTION_RESULT_FAILED))'))
fixture+=r'''
int main(){Player bot;Unit target;PlayerbotAI ai;CastBlessingOnPartyAction blessing;blessing.bot=&bot;blessing.ai=&ai;blessing.target=&target;
 bool ready=blessing.isUseful();
#ifdef EXPECT_BEFORE
 assert(!ready);
#else
 assert(ready);blessing.blessing="greater blessing of wisdom";assert(blessing.isUseful()&&blessing.spellName=="greater blessing of wisdom");
 blessing.blessing="";assert(!blessing.isUseful());blessing.blessing="blessing of might";ai.learned=false;assert(!blessing.isUseful());ai.learned=true;
 blessing.target=nullptr;assert(!blessing.isUseful());blessing.target=&target;
#endif
 CastVehicleSpellAction vehicle;vehicle.bot=&bot;vehicle.ai=&ai;vehicle.target=&target;vehicle.spellIdContext="vehicle spell id";Event event;
 ai.vehicle=true;ai.vehicleSpell=20;vehicle.isUseful();bool possible=vehicle.isPossible();
#ifdef EXPECT_BEFORE
 assert(!possible&&vehicle.spellId==0);
#else
 assert(possible&&vehicle.Execute(event)&&ai.lastCast==20);ai.vehicleSpell=30;assert(vehicle.isPossible()&&vehicle.spellId==30);
 ai.vehicleSpell=40;assert(vehicle.Execute(event)&&ai.lastCast==40);ai.vehicle=false;ai.vehicleSpell=0;assert(!vehicle.isUseful()&&!vehicle.isPossible());
#endif
 CastSpellAction unavailable;unavailable.bot=&bot;unavailable.ai=&ai;unavailable.target=&target;
 Engine e;e.ai=&ai;e.action=&unavailable;e.missing();e.cachedImpossible();e.cachedFailed();
#ifdef EXPECT_BEFORE
 assert(e.alternatives==0);std::cout<<"REPRODUCED: party blessing dispatcher blocked, vehicle ID stale, and missing/backed-off actions lose configured alternatives\n";
#else
 assert(e.alternatives==3);unavailable.resolvedId=1;e.missing();assert(e.alternatives==3); // learned but otherwise useless must not fallback
 unavailable.resolvedId=0;e.isStunned=true;e.missing();assert(e.alternatives==3);e.isStunned=false;
 unavailable.spellIdContext="vehicle spell id";e.missing();assert(e.alternatives==3);
 std::cout<<"PASS: selected party blessings, refreshed vehicle IDs, capability-only fallbacks, backoff alternatives, and no fallback for ordinary useless/stunned actions\n";
#endif
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='bot-related-dispatch-') as d:
  p=Path(d);(p/'test.cpp').write_text(fixture)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}',*(['/DEXPECT_BEFORE'] if before else []),'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
