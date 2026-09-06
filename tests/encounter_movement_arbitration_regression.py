"""Actual Onyxia/Mechanar arbitration must also preserve holds against movement spells."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
base=root/'playerbot/strategy/generic'
methods='\n'.join(block((base/'DungeonMultipliers.cpp').read_text(),sig) for sig in (
 'float PreserveMechanarPositionMultiplier::GetValue(', 'float PreserveOnyxiaPositionMultiplier::GetValue('))
code=r'''
#include <cassert>
#include <string>
#include <iostream>
struct PlayerbotAI{bool active=true,exclusive=true;};
struct Action{virtual ~Action()=default;virtual std::string getName(){return "action";}};
struct MovementAction:Action{};struct AttackAction:MovementAction{};struct MoveAwayFromHazard:MovementAction{};struct SetBehindTargetAction:MovementAction{};
struct CastSpellAction:Action{bool moves=false;bool HasMovementEffect(){return moves;}};
struct EncounterPosition{bool exclusive=true;};
struct MechanarPositionAction:MovementAction{static bool GetPlan(PlayerbotAI* ai,EncounterPosition&){return ai->active;}};
struct OnyxiaPositionAction:MovementAction{static bool GetPlan(PlayerbotAI* ai,EncounterPosition& p){p.exclusive=ai->exclusive;return ai->active;}};
struct PathaleonAddsAction{PathaleonAddsAction(PlayerbotAI*){}void* GetTarget(){return nullptr;}};
struct OnyxiaAddsAction{OnyxiaAddsAction(PlayerbotAI*){}void* GetTarget(){return nullptr;}};
struct PreserveMechanarPositionMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
struct PreserveOnyxiaPositionMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
__METHODS__
int main(){
 PlayerbotAI ai;PreserveMechanarPositionMultiplier mechanar{&ai};PreserveOnyxiaPositionMultiplier onyxia{&ai};
 CastSpellAction blink,heal;blink.moves=true;MovementAction chase;AttackAction attack;MoveAwayFromHazard escape;
 MechanarPositionAction reposition;OnyxiaPositionAction onyxiaReposition;SetBehindTargetAction behind;
 assert(mechanar.GetValue(&blink)==0&&onyxia.GetValue(&blink)==0);
 assert(mechanar.GetValue(&heal)==1&&onyxia.GetValue(&heal)==1);
 assert(mechanar.GetValue(&chase)==0&&onyxia.GetValue(&chase)==0);
 assert(mechanar.GetValue(&attack)==1&&onyxia.GetValue(&attack)==1);
 assert(mechanar.GetValue(&escape)==1&&onyxia.GetValue(&escape)==1);
 assert(mechanar.GetValue(&reposition)==1&&onyxia.GetValue(&onyxiaReposition)==1);
 ai.exclusive=false;assert(onyxia.GetValue(&blink)==1&&onyxia.GetValue(&chase)==1&&onyxia.GetValue(&behind)==0);
 ai.active=false;assert(mechanar.GetValue(&blink)==1&&onyxia.GetValue(&blink)==1);
 assert(mechanar.GetValue(nullptr)==1&&onyxia.GetValue(nullptr)==1);
 std::cout<<"PASS: movement-spell holds preserve healing, attacks, hazard escape, non-exclusive flank guidance and expiry\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='mantech-encounter-arbitration-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for filename,cls,policy in (
 ('MoltenCoreDungeonStrategies','MoltenCoreDungeonStrategy','PreserveMoltenCorePositionMultiplier'),
 ('BlackwingLairDungeonStrategies','BlackwingLairDungeonStrategy','PreserveBlackwingLairPositionMultiplier'),
 ('NaxxramasDungeonStrategies','NaxxramasDungeonStrategy','PreserveNaxxramasPositionMultiplier'),
 ('MechanarDungeonStrategies','MechanarDungeonStrategy','PreserveMechanarPositionMultiplier'),
 ('OnyxiasLairDungeonStrategies','OnyxiaFightStrategy','PreserveOnyxiaPositionMultiplier')):
    source=(base/(filename+'.cpp')).read_text()
    for hook in ('InitCombatMultipliers','InitReactionMultipliers'):
        assert policy in block(source,'void '+cls+'::'+hook+'(')
    assert 'void InitReactionMultipliers(' in (base/(filename+'.h')).read_text()
print('PASS: encounter holds wired into combat and reaction engines for MC/BWL/Naxx/Mechanar/Onyxia')
