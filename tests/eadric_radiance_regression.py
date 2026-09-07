"""Exercise Radiance target facing, bot turning, arbitration and cast lifecycle."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/EadricRadianceAction.cpp').read_text()
native=(root.parent/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/crusaders_coliseum/trial_of_the_champion/boss_argent_challenge.cpp').read_text()
mult=(root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <string>
#include <iostream>
using ObjectGuid=unsigned;constexpr float M_PI_F=3.14159265f;
enum{CURRENT_GENERIC_SPELL,SPELL_STATE_PREPARING,SPELL_STATE_FINISHED,SPELL_STATE_DELAYED,IDLE_MOTION_TYPE};
enum class BotState{BOT_STATE_COMBAT};using SpellEffectIndex=int;
struct Unit;
struct SpellInfo{unsigned Id=66935;};
struct Spell{SpellInfo*m_spellInfo;int state=SPELL_STATE_PREPARING;Unit*caster=nullptr;int getState()const{return state;}Unit*GetCaster()const{return caster;}};
struct Unit{unsigned entry=35119,phase=1;bool world=true,alive=true,combat=true,charmed=false,friendly=false;float x=0,y=0,facing=0;Spell*cast=nullptr;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}
 bool HasInArc(Unit*u,float arc){return std::fabs(std::remainder(GetAngle(u)-facing,2*M_PI_F))<=arc/2;}
 Spell*GetCurrentSpell(int){return cast;}};
struct Group{};struct Motion{int mode=IDLE_MOTION_TYPE;int GetCurrentMovementGeneratorType(){return mode;}};
struct Player:Unit{Group group;unsigned map=650;bool teleport=false,stopped=true;Motion motion;
 unsigned GetMapId(){return map;}Group*GetGroup(){return &group;}bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&u->phase==phase;}
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}};
template<class T>struct Value{T data;T Get(){return data;}};
struct Context{Value<std::list<unsigned>>near;template<class T>Value<T>*GetValue(std::string name,std::string q){assert(name=="possible targets"&&q=="100:1");return &near;}};
struct PlayerbotAI{Player*bot;Context context;std::map<unsigned,Unit*>units;bool dungeon=true,canMove=true;unsigned stopped=0,interrupts=0;
 Player*GetBot(){return bot;}bool HasStrategy(std::string name,BotState){assert(name=="dungeon");return dungeon;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}
 bool CanMove(){return canMove;}void StopMoving(){++stopped;bot->stopped=true;bot->motion.mode=IDLE_MOTION_TYPE;}
 void InterruptSpell(){++interrupts;}};
struct Event{};struct Action{virtual ~Action(){}Unit*target=nullptr;virtual Unit*GetTarget(){return target;}};
struct MovementAction:Action{};struct AttackAction:MovementAction{};struct MoveAwayFromHazard:MovementAction{};
struct CastSpellAction:Action{bool movement=false;bool HasMovementEffect(){return movement;}};
struct EadricRadianceAction:Action{PlayerbotAI*ai;Player*bot;unsigned duration=0;
 static Unit*GetBoss(PlayerbotAI*);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);void SetDuration(unsigned ms){duration=ms;}};
struct PreserveEadricFacingMultiplier{PlayerbotAI*ai;float GetValue(Action*);};
struct Facade{void SetFacingTo(Player*b,float angle,bool){b->facing=std::remainder(angle,2*M_PI_F);}
 bool IsFriendlyTo(Player*b,Unit*t){return t==b||t->friendly;}}sServerFacade;
struct SpellScript{virtual bool OnCheckTarget(const Spell*,Unit*,int)const{return true;}};
__NATIVE__;
__METHODS__
__MULT__
int main(){Player bot;Unit boss;boss.x=10;SpellInfo info;Spell cast{&info};cast.caster=&boss;boss.cast=&cast;
 PlayerbotAI ai;ai.bot=&bot;ai.units[1]=&boss;ai.context.near.data={1};EadricRadianceAction action;action.ai=&ai;action.bot=&bot;Event event;
 EadricRadiance native;assert(native.OnCheckTarget(&cast,&bot,0)&&native.OnCheckTarget(&cast,&bot,1));
 bot.facing=M_PI_F;assert(!native.OnCheckTarget(&cast,&bot,0)&&!native.OnCheckTarget(&cast,&bot,1));
 bot.facing=0;
#ifndef MANGOSBOT_TWO
 assert(!action.GetBoss(&ai)&&!action.isUseful()&&!action.Execute(event));return 0;
#else
 assert(action.GetBoss(&ai)==&boss&&action.isUseful()&&action.ShouldReactionInterruptCast());
 assert(action.Execute(event)&&ai.interrupts==1&&ai.stopped==1&&action.duration==100);
 assert(!native.OnCheckTarget(&cast,&bot,0)&&!action.isUseful()&&!action.ShouldReactionInterruptCast());
 bot.motion.mode=5;assert(action.isUseful());assert(action.Execute(event)&&ai.interrupts==1); // Safe heal needn't be canceled.
 PreserveEadricFacingMultiplier m{&ai};AttackAction attack;MovementAction move;MoveAwayFromHazard escape;CastSpellAction heal,damage;
 damage.target=&boss;Unit ally;ally.x=-10;ally.friendly=true;heal.target=&ally;
 assert(m.GetValue(&attack)==0&&m.GetValue(&move)==0&&m.GetValue(&damage)==0);
 assert(m.GetValue(&escape)==1&&m.GetValue(&action)==1&&m.GetValue(&heal)==1);
 ally.x=10;assert(m.GetValue(&heal)==0);heal.target=&bot;assert(m.GetValue(&heal)==1);
 heal.movement=true;assert(m.GetValue(&heal)==0);heal.movement=false;
 for(int state:{SPELL_STATE_FINISHED,SPELL_STATE_DELAYED}){cast.state=state;assert(!action.GetBoss(&ai)&&m.GetValue(&attack)==1);}
 cast.state=SPELL_STATE_PREPARING;info.Id=66862;assert(!action.GetBoss(&ai));info.Id=66935;
 boss.x=41;assert(!action.GetBoss(&ai));boss.x=10;
 boss.alive=false;assert(!action.GetBoss(&ai));boss.alive=true;boss.phase=2;assert(!action.GetBoss(&ai));boss.phase=1;
 bot.teleport=true;assert(!action.GetBoss(&ai));bot.teleport=false;ai.dungeon=false;assert(!action.GetBoss(&ai));ai.dungeon=true;
 assert(action.GetBoss(&ai)==&boss);ai.canMove=false;assert(!action.Execute(event));
 std::cout<<"PASS: Radiance damage/stun facing, turn/hold, safe heals, hazard escape and lifecycle\n";
#endif
}
'''
methods='\n'.join(block(source,name) for name in ('Unit* EadricRadianceAction::GetBoss(', 'bool EadricRadianceAction::isUseful(', 'bool EadricRadianceAction::ShouldReactionInterruptCast(', 'bool EadricRadianceAction::Execute('))
code=code.replace('__NATIVE__',block(native,'struct EadricRadiance')).replace('__METHODS__',methods).replace('__MULT__',block(mult,'float PreserveEadricFacingMultiplier::GetValue('))
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='eadric-facing-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
for method in ('InitCombatTriggers','InitReactionTriggers'):
    assert 'eadric face away' in block(strategy,'void DungeonStrategy::'+method)
for method in ('InitCombatMultipliers','InitReactionMultipliers'):
    assert 'PreserveEadricFacingMultiplier' in block(strategy,'void DungeonStrategy::'+method)
face=block((root/'playerbot/PlayerbotAI.cpp').read_text(),'void PlayerbotAI::UpdateFaceTarget(')
assert face.index('EadricRadianceAction::GetBoss(this)')<face.index('sServerFacade.SetFacingTo')
print('PASS: combat/reaction bindings and periodic automatic-facing guard')
