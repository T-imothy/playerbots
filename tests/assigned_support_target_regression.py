"""Assigned support trigger/action agreement across native world/group transitions."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

work = Path(__file__).resolve().parents[2]
root = work / 'playerbots-behavior/playerbot/strategy'
methods = '\n'.join(block((root / path).read_text(), marker) for path, marker in (
    ('actions/GenericSpellActions.cpp', 'bool CastSpellTargetAction::IsTargetValid('),
    ('triggers/GenericTriggers.cpp', 'bool SpellTargetTrigger::IsTargetValid(')))
code = r'''
#include <cassert>
#include <iostream>
#include <string>
struct Unit {
 bool world=true,dead=false,friendly=true,group=true,safe=true,aura=false;int map=1,phase=1;float distance=0;
 bool IsInWorld()const{return world;}int GetMap()const{return map;}
 bool InSamePhase(const Unit* other)const{return (phase & other->phase)!=0;}
 bool IsDead(){return dead;}bool IsInGroup(Unit* other){return other==this||other->group;}
 bool IsInMap(const Unit* obj)const;
};
__NATIVE_MAP__
struct PlayerbotAI {bool IsSafe(Unit* target){return target->safe;}
 bool HasAura(unsigned,Unit* target){return target->aura;}bool HasAura(std::string,Unit* target){return target->aura;}};
struct {bool IsFriendlyTo(Unit*,Unit* target){return target->friendly;}
 float GetDistance2d(Unit*,Unit* target){return target->distance;}}sServerFacade;
struct {float sightDistance=100;}sPlayerbotAIConfig;
struct CastSpellTargetAction {PlayerbotAI* ai;Unit* bot;bool aliveCheck=true,auraCheck=true;
 unsigned GetSpellID(){return 1;}bool IsTargetValid(Unit*);};
struct SpellTargetTrigger {PlayerbotAI* ai;Unit* bot;bool aliveCheck=true,auraCheck=true;std::string spell="support";
 bool IsTargetValid(Unit*);};
__METHODS__
int main(){
 Unit bot,target;PlayerbotAI ai;CastSpellTargetAction action{&ai,&bot};SpellTargetTrigger trigger{&ai,&bot};
 auto check=[&](bool expected){assert(action.IsTargetValid(&target)==expected);assert(trigger.IsTargetValid(&target)==expected);};
 check(true);target.world=false;check(false);target.world=true;bot.world=false;check(false);bot.world=true;
 target.map=2;check(false);target.map=1;
#ifdef MANGOSBOT_TWO
 target.phase=2;check(false);target.phase=1;
#endif
 target.friendly=false;check(false);target.friendly=true; // A hostile mind-controlled member is not a support target.
 target.group=false;check(false);target.group=true;target.safe=false;check(false);target.safe=true;
 target.distance=100;check(false);target.distance=0;target.aura=true;check(false);target.aura=false;
 target.dead=true;check(false);action.aliveCheck=trigger.aliveCheck=false;check(true); // Rebirth must still select a corpse.
 target.world=false;check(false);target.world=true;target.dead=false;
 assert(action.IsTargetValid(&bot)&&trigger.IsTargetValid(&bot));
 assert(!action.IsTargetValid(nullptr)&&!trigger.IsTargetValid(nullptr));
 std::cout<<"PASS: assigned support world/map/phase/faction/group/aura transitions and resurrection eligibility\n";
}
'''
with tempfile.TemporaryDirectory(prefix='mantech-assigned-support-') as folder:
    tmp = Path(folder)
    for era, define in (('classic', 'ZERO'), ('tbc', 'ONE'), ('wotlk', 'TWO')):
        native = block((work / ('mangos-' + era + '-behavior') / 'src/game/Entities/Object.h').read_text(), 'bool IsInMap(')
        native = native.replace('bool IsInMap(', 'bool Unit::IsInMap(').replace('WorldObject', 'Unit')
        (tmp / 'test.cpp').write_text(code.replace('__NATIVE_MAP__', native).replace('__METHODS__', methods))
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/DMANGOSBOT_' + define, 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
