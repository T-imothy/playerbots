"""Actual Onyxia/Mechanar arbitration must also preserve holds against movement spells."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
base=root/'playerbot/strategy/generic'
methods='\n'.join(block((base/'DungeonMultipliers.cpp').read_text(),sig) for sig in (
 'float PreserveMoltenCorePositionMultiplier::GetValue(', 'float PreserveMechanarPositionMultiplier::GetValue(', 'float PreserveOnyxiaPositionMultiplier::GetValue('))
code=r'''
#include <cassert>
#include <string>
#include <iostream>
struct Unit{bool air=false;float z=0;unsigned guid=1;bool IsLevitating(){return air;}float GetPositionZ(){return z;}unsigned GetObjectGuid(){return guid;}};
struct PlayerbotAI{bool active=true,exclusive=true,stack=false,ranged=false,healer=false,add=false;unsigned spell=0,source=0;Unit bot;Unit*boss=nullptr;
 Unit*GetBot(){return &bot;}bool IsRanged(Unit*){return ranged;}bool IsHeal(Unit*){return healer;}};
Unit* FindOnyxiaBoss(PlayerbotAI*a){return a->boss;}bool OnyxiaMeleeAirAdd(PlayerbotAI*a,Unit*){return a->add;}
bool MoltenCorePackStackRequired(PlayerbotAI*a){return a->stack;}bool MoltenCoreImpUnderPressure(PlayerbotAI*){return false;}
struct Action{virtual ~Action()=default;virtual std::string getName(){return "action";}};
struct MovementAction:Action{};struct NamedMove:MovementAction{std::string name;NamedMove(const char*n):name(n){}std::string getName()override{return name;}};struct AttackAction:MovementAction{};struct MoveAwayFromHazard:MovementAction{};struct SetBehindTargetAction:MovementAction{};
struct CastSpellAction:Action{bool moves=false;bool HasMovementEffect(){return moves;}};
struct EncounterPosition{bool exclusive=true;unsigned spell=0,source=0;};
struct MoltenCorePositionAction:MovementAction{static bool GetPlan(PlayerbotAI* ai,EncounterPosition&){return ai->active;}};
struct MechanarPositionAction:MovementAction{static bool GetPlan(PlayerbotAI* ai,EncounterPosition&){return ai->active;}};
struct OnyxiaPositionAction:MovementAction{static bool GetPlan(PlayerbotAI* ai,EncounterPosition& p){p.exclusive=ai->exclusive;p.spell=ai->spell;p.source=ai->source;return ai->active;}};
struct MoltenCorePriorityTargetAction{MoltenCorePriorityTargetAction(PlayerbotAI*){}void* GetTarget(){return nullptr;}};
struct PathaleonAddsAction{PathaleonAddsAction(PlayerbotAI*){}void* GetTarget(){return nullptr;}};
struct OnyxiaAddsAction{OnyxiaAddsAction(PlayerbotAI*){}void* GetTarget(){return nullptr;}};
struct PreserveMoltenCorePositionMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
struct PreserveMechanarPositionMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
struct PreserveOnyxiaPositionMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
__METHODS__
int main(){
 PlayerbotAI ai;PreserveMechanarPositionMultiplier mechanar{&ai};PreserveOnyxiaPositionMultiplier onyxia{&ai};
 PreserveMoltenCorePositionMultiplier mc{&ai};
 CastSpellAction blink,heal;blink.moves=true;MovementAction chase;AttackAction attack;MoveAwayFromHazard escape;
 MechanarPositionAction reposition;OnyxiaPositionAction onyxiaReposition;SetBehindTargetAction behind;
 assert(mechanar.GetValue(&blink)==0&&onyxia.GetValue(&blink)==0);
 assert(mechanar.GetValue(&heal)==1&&onyxia.GetValue(&heal)==1);
 assert(mechanar.GetValue(&chase)==0&&onyxia.GetValue(&chase)==0);
 assert(mechanar.GetValue(&attack)==1&&onyxia.GetValue(&attack)==1);
 assert(mechanar.GetValue(&escape)==1&&onyxia.GetValue(&escape)==1);
 assert(mechanar.GetValue(&reposition)==1&&onyxia.GetValue(&onyxiaReposition)==1);
 assert(mc.GetValue(&attack)==1&&mc.GetValue(&heal)==1&&mc.GetValue(&chase)==0&&mc.GetValue(&blink)==0);
 assert(mc.GetValue(&escape)==1);MoltenCorePositionAction mcReposition;assert(mc.GetValue(&mcReposition)==1);
 ai.active=false;ai.stack=true;
 for(const char* name : {"flee","flee with pet","runaway","flee to master","wait for attack keep safe distance"}){
  NamedMove unwanted(name);assert(mc.GetValue(&unwanted)==0);ai.stack=false;assert(mc.GetValue(&unwanted)==1);ai.stack=true;}
 assert(mc.GetValue(&escape)==1&&mc.GetValue(&attack)==1&&mc.GetValue(&heal)==1);ai.stack=false;
 ai.active=false;assert(mc.GetValue(&chase)==1&&mc.GetValue(&blink)==1);ai.active=true;
 ai.exclusive=false;assert(onyxia.GetValue(&blink)==1&&onyxia.GetValue(&chase)==1&&onyxia.GetValue(&behind)==0);
 ai.active=false;assert(mechanar.GetValue(&blink)==1&&onyxia.GetValue(&blink)==1);
 assert(mechanar.GetValue(nullptr)==1&&onyxia.GetValue(nullptr)==1);
#ifdef MANGOSBOT_ZERO
 Unit dragon;dragon.air=true;ai.boss=&dragon;NamedMove melee("reach melee"),healReach("reach party member to heal");
 assert(onyxia.GetValue(&melee)==0&&onyxia.GetValue(&blink)==0); // Failed plan cannot restart aerial chase.
 ai.add=true;assert(onyxia.GetValue(&melee)==1&&onyxia.GetValue(&blink)==1);ai.add=false;
 ai.ranged=true;assert(onyxia.GetValue(&melee)==1);ai.ranged=false;
 dragon.air=false;assert(onyxia.GetValue(&melee)==1);dragon.air=true;
 ai.active=true;ai.exclusive=true;ai.healer=true;ai.spell=18392;
 assert(onyxia.GetValue(&healReach)==1&&onyxia.GetValue(&chase)==0&&onyxia.GetValue(&heal)==1);
 ai.spell=17086;assert(onyxia.GetValue(&healReach)==0&&onyxia.GetValue(&heal)==1);
 ai.spell=18392;ai.source=1;assert(onyxia.GetValue(&healReach)==0);
#endif
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
