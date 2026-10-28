"""Actual pet admission and native PetAI attack/cast/current-victim hooks.

Compile each core's own functions. UpdateAI is cut immediately before retreat
movement; its real owner/admission/stop/chase cleanup prefix executes unchanged.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--core',type=Path)
parser.add_argument('--era',choices=('ZERO','ONE','TWO'))
args=parser.parse_args()
if bool(args.core) != bool(args.era):
    parser.error('--core and --era must be supplied together')
helper=(root/'playerbot/strategy/actions/RaidPetAdmission.cpp').read_text()
helper='\n'.join(line for line in helper.splitlines() if not line.startswith('#include'))
base=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <tuple>
#include <vector>
using uint32=unsigned;using SpellEffectIndex=unsigned;using SpellCastResult=int;
constexpr unsigned MAX_EFFECT_INDEX=3,CURRENT_GENERIC_SPELL=0,CURRENT_CHANNELED_SPELL=1,CURRENT_AUTOREPEAT_SPELL=2,SPELL_STATE_FINISHED=2;
constexpr unsigned SPELL_EFFECT_APPLY_AURA=6,CHASE_MOTION_TYPE=1;
constexpr int SPELL_CAST_OK=0,SPELL_FAILED_UNIT_NOT_INFRONT=1;
constexpr unsigned TRIGGERED_NORMAL_COMBAT_CAST=1,TRIGGERED_PET_CAST=2;
#define MANGOS_ASSERT assert
struct PlayerbotAI;struct Pet;struct Unit;
struct SpellEntry{unsigned Id=0;bool damage=false,positive=false;unsigned Effect[3]={},StackAmount=0;};
struct Targets{Unit*target=nullptr;Unit*getUnitTarget(){return target;}void setUnitTarget(Unit*u){target=u;}};
using SpellCastTargets=Targets;
unsigned nativeSpellStarts=0;int nativeSpellResult=SPELL_CAST_OK;
struct Spell{const SpellEntry*m_spellInfo;Targets m_targets;unsigned state=0;
 Spell(const SpellEntry*s,Targets t,unsigned state=0):m_spellInfo(s),m_targets(t),state(state){}
 Spell(Unit*,const SpellEntry*s,unsigned):m_spellInfo(s){}
 unsigned getState(){return state;}int SpellStart(Targets*){++nativeSpellStarts;const auto result=nativeSpellResult;delete this;return result;}};
struct Aura{unsigned GetStackAmount(){return 1;}};
struct CombatManager{bool IsEvadingHome(){return false;}};
struct MotionMaster{unsigned type=CHASE_MOTION_TYPE,expired=0;unsigned GetCurrentMovementGeneratorType(){return type;}
 void MovementExpired(){++expired;type=0;}};
struct CharmInfo{unsigned GetPetLastAttackCommandTime(){return 0;}bool GetIsRetreating(){return false;}};
struct Unit{Unit*owner=nullptr,*victim=nullptr;bool world=true,alive=true,sameMap=true,charmed=false,player=false,combat=true;
 unsigned map=533,stops=0,starts=0;Spell*casts[3]={};std::vector<unsigned>interrupts;MotionMaster motion;CombatManager manager;CharmInfo charmInfo;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}unsigned GetMapId(){return map;}
 Unit*GetOwner(){return owner;}Unit*GetMaster(){return owner;}bool IsPlayer(){return player;}
 bool IsInMap(Unit*u){return u&&u->sameMap&&map==u->map;}bool IsInCombat(){return combat;}
 Unit*GetVictim(){return victim;}Spell*GetCurrentSpell(unsigned slot){return casts[slot];}
 void InterruptSpell(unsigned slot){interrupts.push_back(slot);casts[slot]=nullptr;}
 void AttackStop(bool,bool){++stops;victim=nullptr;}bool Attack(Unit*target,bool){++starts;victim=target;return target!=nullptr;}
 CharmInfo*GetCharmInfo(){return &charmInfo;}CombatManager&GetCombatManager(){return manager;}
 bool IsCrowdControlled(){return false;}bool HasAuraPetShouldAvoidBreaking(Pet*,unsigned){return false;}
 bool IsPlayerControlled(){return true;}bool HasInArc(Unit*){return true;}void SetFacingToObject(Unit*){}
 MotionMaster*GetMotionMaster(){return &motion;}bool HasAura(unsigned,SpellEffectIndex){return false;}
 Aura*GetAura(unsigned,SpellEffectIndex){return nullptr;}};
struct Pet:Unit{bool disabled=false;bool HasActionsDisabled(){return disabled;}void CheckLearning(unsigned){}};
struct Player:Unit{PlayerbotAI*brain=nullptr;Pet*pet=nullptr;bool transfer=false;void*group=this;
 Player(){player=true;}Pet*GetPet(){return pet;}bool IsBeingTeleported(){return transfer;}
 PlayerbotAI*GetPlayerbotAI(){return brain;}void*GetGroup(){return group;}};
namespace ai{struct ClassicRaidPlan{bool holdDamage=false;};}
struct Context{ai::ClassicRaidPlan plan;template<class T>struct Value{T value;T Get(){return value;}};
 template<class T>Value<T>*GetValue(const char*){static Value<T>v;v.value=plan;return &v;}};
struct PlayerbotAI{Player bot;Context context;bool real=false,offenseAllowed=true;unsigned offenseQueries=0;
 PlayerbotAI(){bot.brain=this;}bool IsRealPlayer(){return real;}Context*GetAiObjectContext(){return &context;}};
bool IsPositiveSpell(const SpellEntry*s,Unit*,Unit*){return s->positive;}
namespace ai{
 bool ClassicRaidDamageSpell(const SpellEntry*s){return s&&s->damage;}
 bool ClassicRaidOffenseAllowed(PlayerbotAI*a,const SpellEntry*s,Unit*){++a->offenseQueries;return s&&!s->damage?true:a->offenseAllowed;}
 bool RaidPetOffenseAllowed(Unit*,const SpellEntry*,Unit*);void StopUnsafeRaidPetCasts(Unit*);
 void StopUnsafeEncounterOffense(Player*,Unit*){};bool HasEncounterDamagePause(Player*){return false;}
 bool HasMajordomoDamageShield(Player*,Unit*){return false;}
 bool ShouldAvoidEncounterOffense(Player*,Unit*,const SpellEntry*,Unit*){return false;}
}
__HELPER__
Player*EncounterBotOwner(Unit*u){return u->owner&&u->owner->IsPlayer()?static_cast<Player*>(u->owner):nullptr;}
struct CreatureAI{void UpdateAI(unsigned){}};
struct PetAI:CreatureAI{Pet*m_pet;Unit*m_unit,*m_creature;bool m_inCombat=false,m_meleeEnabled=true,script=false;
 mutable unsigned nativeChecks=0;int nativeResult=SPELL_CAST_OK;unsigned moves=0;
 PetAI(Pet*p):m_pet(p),m_unit(p),m_creature(p){};bool GetCombatScriptStatus(){return script;}
 bool CanHandleCharm(){return false;}void UpdateTimers(unsigned,bool){};void HandleMovementOnAttackStart(Unit*,bool){++moves;}
 bool CanAutoCastAreaAura(const SpellEntry*,Unit*)const{return true;}
 int CheckPetCast(const SpellEntry*,Unit*)const{++nativeChecks;return nativeResult;}
 void AttackStart(Unit*);void UpdateAI(unsigned);bool CanAutoCast(const SpellEntry*,Unit*)const;
 bool Cast(std::tuple<const SpellEntry*,Unit*,bool>);};
__NATIVE__
int main(){PlayerbotAI owner;Pet pet;Unit enemy;pet.owner=&owner.bot;owner.bot.pet=&pet;PetAI native(&pet);
 SpellEntry damage{1,true,false},heal{2,false,true},buff{3,false,true},cc{4,false,false};
 owner.context.plan.holdDamage=true;
 assert(!ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));native.AttackStart(&enemy);assert(!pet.victim&&pet.starts==0);
 assert(!native.CanAutoCast(&damage,&enemy)&&native.nativeChecks==0);
 assert(!native.Cast({&damage,nullptr,false})&&!nativeSpellStarts); // AoE/DB-list path bypasses CanAutoCast.
 assert(native.Cast({&heal,&owner.bot,false})&&nativeSpellStarts==1);
 nativeSpellResult=2;assert(!native.Cast({&heal,&owner.bot,false}));nativeSpellResult=SPELL_CAST_OK;
 assert(native.CanAutoCast(&heal,&owner.bot)&&native.CanAutoCast(&buff,&pet)&&native.CanAutoCast(&cc,&enemy));
 native.nativeResult=2;assert(!native.CanAutoCast(&heal,&owner.bot));native.nativeResult=SPELL_CAST_OK;
 // Owner has no victim; native autonomous owner-assist attempts still cannot restart attack.
 assert(!owner.bot.victim);native.AttackStart(&enemy);assert(pet.starts==0);
 pet.victim=&enemy;native.m_inCombat=true;Spell cast{&damage,{&enemy}},healing{&heal,{&owner.bot}},finished{&damage,{&enemy},SPELL_STATE_FINISHED};
 pet.casts[0]=&cast;pet.casts[1]=&healing;pet.casts[2]=&finished;
 native.UpdateAI(100);assert(!pet.victim&&!native.m_inCombat&&pet.stops==1&&pet.motion.expired==1);
 assert(pet.interrupts==std::vector<unsigned>({0})&&pet.casts[1]==&healing&&pet.casts[2]==&finished);
 const auto stops=pet.stops;native.UpdateAI(100);assert(pet.stops==stops); // Settled hold cannot repeat native stop work.
 owner.context.plan.holdDamage=false;owner.offenseAllowed=false;
 assert(!ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy)&&!native.CanAutoCast(&damage,&enemy)); // Reserved actor without global hold.
 const auto starts=nativeSpellStarts;assert(!native.Cast({&damage,nullptr,false})&&nativeSpellStarts==starts);
 native.AttackStart(&enemy);assert(!pet.victim);assert(native.CanAutoCast(&heal,&owner.bot));
 owner.offenseAllowed=true;native.AttackStart(&enemy);assert(pet.victim==&enemy&&pet.starts==1);
 assert(native.CanAutoCast(&damage,&enemy)); // Hold end restores native attacks without react-state bookkeeping.
 assert(native.Cast({&damage,&enemy,true})&&nativeSpellStarts==starts+1);
 owner.context.plan.holdDamage=true;
 owner.real=true;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));owner.real=false;
 pet.map=409;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));pet.map=533;
 owner.bot.map=409;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));owner.bot.map=533;
 owner.bot.pet=nullptr;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));owner.bot.pet=&pet;
 pet.charmed=true;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));pet.charmed=false; // Never govern possessed encounter actors.
 owner.bot.transfer=true;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));owner.bot.transfer=false;
 owner.bot.alive=false;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));owner.bot.alive=true;
 owner.bot.combat=false;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));owner.bot.combat=true;
 owner.bot.group=nullptr;assert(ai::RaidPetOffenseAllowed(&pet,nullptr,&enemy));owner.bot.group=&owner;
 enemy.sameMap=false;const auto queries=owner.offenseQueries;assert(ai::RaidPetOffenseAllowed(&pet,&damage,&enemy)&&owner.offenseQueries==queries);
 std::cout<<"PASS actual native pet attack/autocast/final-cast/current-victim admission, no reacquire, preserved support/control/other maps and native reset\n";
}
'''.replace('__HELPER__',helper)
variants=[(args.era,args.core)] if args.core else [(era,root.parent/core) for era,core in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk'))]
for era,core in variants:
    # This admission reads the same-map owner's mutable AI context. Keep the
    # native map ownership barriers explicit: discovery workers collect only,
    # idle AI finishes first, and no AI/native object ticks run in parallel.
    maps=(core/'src/game/Maps/Map.cpp').read_text()
    update_map=block(maps,'void Map::Update(')
    idle=update_map.index('taskGroup.Wait("idle bot batch")')
    grid=update_map.index('taskGroup.Wait("grid objects")')
    objects=update_map.index('object->Update(accumulatedDiff);') if era=='ZERO' else update_map.index('PerformObjectUpdate(t_diff, objToUpdate)')
    assert update_map.index('plr->UpdateAI(')<idle<grid<objects
    if era!='ZERO':
        object_loop=block(maps,'uint64 Map::PerformObjectUpdate(')
        assert 'for (WorldObject* object : objToUpdate)' in object_loop and 'object->Update(accumulatedDiff);' in object_loop
    for path,signature in (('GridNotifiers.cpp','void ObjectUpdater::Visit(GridRefManager<T>& m)'),
                           ('GridNotifiersImpl.h','inline void MaNGOS::ObjectUpdater::Visit(CreatureMapType& m)')):
        collector=block((core/'src/game/Grids'/path).read_text(),signature)
        assert 'm_objectToUpdateSet.emplace(iter.getSource())' in collector and '->Update(' not in collector
    world=(core/'src/game/World/World.cpp').read_text()
    assert world.index('UpdateSessions(diff);')<world.index('sMapMgr.Update(diff);')
    assert 'm_updater.wait();' in block((core/'src/game/Maps/MapManager.cpp').read_text(),'void MapManager::Update(uint32 diff)')
    opcodes=(core/'src/game/Server/Opcodes.cpp').read_text().splitlines()
    for command in ('CMSG_PET_ACTION','CMSG_PET_CAST_SPELL','CMSG_PET_SPELL_AUTOCAST'):
        assert 'PROCESS_THREADUNSAFE' in next(line for line in opcodes if '"'+command+'"' in line)
    native=(core/'src/game/AI/BaseAI/PetAI.cpp').read_text()
    update=block(native,'void PetAI::UpdateAI(')
    update=update[:update.index('    if (charmInfo->GetIsRetreating())')]+'}\n'
    bodies=block(native,'void PetAI::AttackStart(')+'\n'+update+'\n'+block(native,'bool PetAI::CanAutoCast(')+'\n'+block(native,'bool PetAI::Cast(')
    code=base.replace('__NATIVE__',bodies)
    with tempfile.TemporaryDirectory(prefix='raid-pet-admission-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DENABLE_PLAYERBOTS','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
