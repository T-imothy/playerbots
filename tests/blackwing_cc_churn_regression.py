"""Execute production BWL spell admission and target CC policy; not a raid clear."""
from pathlib import Path
import ast, subprocess, tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root/'playerbot/strategy/actions/EncounterDamagePolicy.cpp').read_text()
targets = (root/'playerbot/strategy/values/PossibleAttackTargetsValue.cpp').read_text()
# Reuse native-shaped spell/cast interfaces, without importing the separate
# Wrath pet suite or requiring another core worktree.
tree = ast.parse((root/'tests/encounter_damage_pause_regression.py').read_text())
code = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
            and isinstance(n.value, str) and '#include <cassert>' in n.value)
code = code.split('__METHODS__')[0]
code = code.replace('SPELL_AURA_PERIODIC_HEAL=8,', 'SPELL_AURA_MOD_FEAR=7,SPELL_AURA_PERIODIC_HEAL=8,')
code = code.replace('struct BotAI {', 'struct BotAI {bool room=false;')
code = code.replace('struct Unit {', 'struct Unit {virtual ~Unit(){} bool stunned=false,breakable=false,feared=false,rooted=false,assigned=false,immune=false,tapped=true,valid=true; bool IsStunned(){return stunned;} bool HasBreakableByDamageCrowdControlAura(){return breakable;}')
code = code.replace('bool IsBeingTeleported(){', 'bool IsWithinDistInMap(Unit*u,float range){return IsInMap(u)&&GetDistance(u)<=range;} bool IsBeingTeleported(){')
code += '\nnamespace ai { bool BlackwingSuppressionMovementActive(BotAI*a){return a->room&&!a->real;} }\n'
code += '\n'.join(block(source, name) for name in (
    'bool ai::HasMajordomoDamageShield(', 'bool ai::HasEncounterDamagePause(',
    'bool ai::HasEncounterThreatPause(', 'bool ai::HasEncounterSpellBomb(',
    'bool ai::HasEncounterWeaponPause(', 'bool ai::ShouldAvoidEncounterOffense(',
    'bool ai::HasUnsafeEncounterOffense(', 'bool ai::StopUnsafeEncounterOffense('))
code += r'''
struct Facade {bool IsFeared(Unit*u){return u->feared;}bool IsInRoots(Unit*u){return u->rooted;}} sServerFacade;
bool IsViscidusShatterTarget(Unit*,Player*){return false;}
bool gothikEngaged=false;
bool GothikGroupEngagedAdd(Player*,Unit*){return gothikEngaged;}
bool KelthuzadDormantAdd(Player*,Unit*){return false;} // This fixture exercises BWL admission.
bool RaidLabMovementResult(Player*,const char*,int,bool result){return result;}
struct PossibleTargetsValue {static bool IsValid(Unit*u,Player*p,bool){return u&&u->valid&&p->IsInMap(u);}};
struct PossibleAttackTargetsValue {
 static bool HasUnBreakableCC(Unit*,Player*);
 static bool IsPossibleTarget(Unit*,Player*,float,bool);
 static bool HasBreakableCC(Unit*u,Player*){return u->breakable;}
 static bool HasIgnoreCCRti(Unit*,Player*){return false;}
 static bool IsCcTarget(Unit*u,Player*){return u->assigned;}
 static bool IsImmuneToDamage(Unit*u,Player*){return u->immune;}
 static bool IsTapped(Unit*u,Player*){return u->tapped;}
};
using ai::IsProtectedBlackwingTarget;
'''
code += block(targets, 'bool PossibleAttackTargetsValue::HasUnBreakableCC(')
code += '\n'+block(targets, 'bool PossibleAttackTargetsValue::IsPossibleTarget(')
code += r'''
int main(){
 BotAI ai;Player bot;bot.ai=&ai;Unit enemy;bot.map=enemy.map=469;
 SpellEntry fear,damage,heal;fear.periodic[0]=true;fear.EffectApplyAuraName[0]=SPELL_AURA_MOD_FEAR;heal.positive=true;
 ai.room=true;
 assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&fear,&enemy));
 assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&fear,nullptr)); // Psychic Scream
 assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&enemy));
 assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&heal,&bot));
 ai.room=false;assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&fear,&enemy));
 ai.room=true;ai.real=true;assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&fear,&enemy));ai.real=false;
 for(unsigned map:{409u,429u,489u,529u,30u}){
  bot.map=enemy.map=map;assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&fear,&enemy));
 }
 bot.map=enemy.map=469;enemy.stunned=true;
 assert(PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));
 enemy.breakable=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.breakable=false;
 enemy.assigned=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,true));enemy.assigned=false;
 enemy.feared=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.feared=false;
 enemy.rooted=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.rooted=false;
 enemy.immune=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,true));enemy.immune=false;
 enemy.tapped=false;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.tapped=true;
 enemy.instance=2;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.instance=1;
 enemy.dist=61;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.dist=5;
 for(unsigned map:{409u,429u,489u,529u,30u}){
  bot.map=enemy.map=map;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));
 }
 bot.map=enemy.map=533;gothikEngaged=false;
 assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));
 gothikEngaged=true;
#ifdef MANGOSBOT_ZERO
 assert(PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));
 enemy.breakable=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.breakable=false;
 enemy.assigned=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,true));enemy.assigned=false;
 enemy.feared=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.feared=false;
 enemy.rooted=true;assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));enemy.rooted=false;
#else
 assert(!PossibleAttackTargetsValue::IsPossibleTarget(&enemy,&bot,60,false));
#endif
 std::cout<<"PASS BWL fear admission and BWL/Classic Gothik damage-safe stun retention; breakable/reserved CC and other eras remain protected\n";
}
'''
with tempfile.TemporaryDirectory(prefix='bwl-cc-churn-') as folder:
    path=Path(folder);(path/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
        if result.returncode: print(result.stdout,result.stderr)
        result.check_returncode()
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
