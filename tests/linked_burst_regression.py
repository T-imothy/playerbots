"""Actual debuff ownership, spread geometry, dispatch and movement arbitration."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
value=(root/'playerbot/strategy/values/LinkedBurstPositionValue.cpp').read_text()
action=(root/'playerbot/strategy/actions/LinkedBurstAction.cpp').read_text()
multiplier=(root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods=block(value,'namespace\n')+'\n'+'\n'.join(block(value,s) for s in ('bool ai::LinkedBurstThreats(', 'EncounterPosition LinkedBurstPositionValue::Calculate('))
methods+='\n'+'\n'.join(block(action,'bool LinkedBurstAction::'+s+'(') for s in ('GetPlan','isUseful','ShouldReactionInterruptCast','Execute'))
methods+='\n'+block(multiplier,'float PreserveLinkedBurstMultiplier::GetValue(')
code=r'''
#include <cassert>
#include <iostream>
#include <map>
#include "__GEOMETRY__"
using uint32=unsigned;using uint64=uint64_t;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned v=0):id(v){}operator unsigned()const{return id;}bool IsEmpty()const{return !id;}unsigned GetCounter()const{return id;}};
struct Unit{unsigned entry=22947,map=564,instance=1,phase=1;ObjectGuid guid;float x=0,y=0,z=0;
 bool world=true,alive=true,combat=true,charmed=false;Unit*victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}unsigned GetMapId(){return map;}Unit*GetVictim(){return victim;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
};
struct SpellAuraHolder{Unit*caster;Unit*GetCaster()const{return caster;}};
struct Player;struct GroupReference{Player*member;GroupReference*following=nullptr;Player*getSource(){return member;}GroupReference*next(){return following;}};
struct Group{GroupReference*first=nullptr;GroupReference*GetFirstMember(){return first;}};
enum{IDLE_MOTION_TYPE=0};struct Motion{unsigned type=1;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Player:Unit{bool teleport=false,stopped=true;Group*group=nullptr;Motion motion;std::map<unsigned,SpellAuraHolder>auras;
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 unsigned GetInstanceId(){return instance;}Group*GetGroup(){return group;}const SpellAuraHolder*GetSpellAuraHolder(unsigned id){auto i=auras.find(id);return i==auras.end()?nullptr:&i->second;}
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}float GetDistance(float a,float b,float c){return std::sqrt((a-x)*(a-x)+(b-y)*(b-y)+(c-z)*(c-z));}
};
namespace ai{struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};}
using namespace ai;
template<class T>struct Cached{T data;T Get(){return data;}};
struct Context{Cached<EncounterPosition>position;template<class T>Cached<T>*GetValue(const char*){return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool real=false,canMove=true,path=true,unsafe=false;unsigned paths=0,moves=0,stops=0;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}Context*GetAiObjectContext(){return &context;}
 void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
};
bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&p){++ai->paths;if(ai->unsafe)p.destination={0,0,0};return ai->path;}
float NativeEncounterSpellRadius(unsigned spell){switch(spell){case 40870:return 25;case 40871:case 30697:case 39298:return 15;case 33686:return 20;default:assert(false);return 0;}}
struct Event{};struct Action{virtual~Action()=default;};struct MovementAction:Action{};struct AttackAction:MovementAction{};struct MoveAwayFromHazard:MovementAction{};struct BossCastPositionAction:MovementAction{};
struct CastSpellAction:Action{bool moving=false;bool HasMovementEffect(){return moving;}};
namespace ai{
 bool LinkedBurstThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
 struct LinkedBurstPositionValue{PlayerbotAI*ai;Player*bot;EncounterPosition Calculate();};
 struct LinkedBurstAction:MovementAction{PlayerbotAI*ai;Player*bot;LinkedBurstAction(PlayerbotAI*a):ai(a),bot(a->bot){}
 static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
 bool IsReaction(){return false;}void SetDuration(unsigned){}bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}};
 struct PreserveLinkedBurstMultiplier{PlayerbotAI*ai;float GetValue(Action*);};
}
__METHODS__
int main(){
 Player bot,member;bot.guid=10;member.guid=11;Group group;GroupReference memberRef{&member},botRef{&bot,&memberRef};group.first=&botRef;bot.group=member.group=&group;
 Unit boss;boss.guid=1;bot.auras[41001]={&boss};member.auras=bot.auras;
 PlayerbotAI ai{&bot},memberAi{&member};LinkedBurstPositionValue planner{&ai,&bot},otherPlanner{&memberAi,&member};LinkedBurstAction action(&ai);Event event;
 auto calculate=[&](){ai.paths=0;ai.context.position.data=planner.Calculate();return ai.context.position.data;};
#ifndef MANGOSBOT_ZERO
 auto p=calculate();assert(p.active&&ai.paths<=8&&action.ShouldReactionInterruptCast());
 std::vector<encounter::Circle> threats;EncounterPosition current;assert(LinkedBurstThreats(&ai,current,threats)&&threats.size()==1&&threats[0].radius==27);
 auto other=otherPlanner.Calculate();assert(other.active&&encounter::Distance2d(p.destination,other.destination)>27);
 assert(action.Execute(event)&&ai.moves==1);
 PreserveLinkedBurstMultiplier multiplier{&ai};MovementAction chase;AttackAction attack;MoveAwayFromHazard hazard;BossCastPositionAction boom;CastSpellAction heal,blink;blink.moving=true;
 assert(multiplier.GetValue(&chase)==0&&multiplier.GetValue(&blink)==0&&multiplier.GetValue(&heal)==1&&multiplier.GetValue(&attack)==1&&multiplier.GetValue(&hazard)==1&&multiplier.GetValue(&boom)==1);
 bot.x=p.destination.x;bot.y=p.destination.y;calculate();assert(action.isUseful()&&!action.ShouldReactionInterruptCast());assert(action.Execute(event)&&ai.stops==1&&!action.isUseful());
 member.x=bot.x;member.y=bot.y;assert(!action.Execute(event)); // stale destination now occupied
 bot.x=bot.y=member.x=member.y=0;assert(calculate().active);bot.auras.clear();assert(!action.Execute(event));
 threats.clear();current={};assert(LinkedBurstThreats(&ai,current,threats)&&threats[0].radius==17); // unlinked player avoids splash only
 member.auras.clear();assert(!calculate().active);
 auto set=[&](unsigned map,unsigned entry,unsigned aura){bot.x=bot.y=member.x=member.y=0;bot.map=member.map=boss.map=map;boss.entry=entry;bot.auras.clear();member.auras.clear();member.auras[aura]={&boss};};
 for(unsigned aura:{30695,37566}){set(543,17308,aura);assert(calculate().active&&action.Execute(event));}
 for(unsigned aura:{33711,38794}){set(555,18708,aura);p=calculate();assert(p.active&&action.Execute(event));threats.clear();current={};assert(LinkedBurstThreats(&ai,current,threats)&&threats[0].radius==22);}
 boss.victim=&bot;assert(!calculate().active);boss.victim=nullptr;
 boss.combat=false;assert(!calculate().active);boss.combat=true;
 boss.entry=22947;assert(!calculate().active);boss.entry=18708;
 boss.phase=2;assert(!calculate().active);boss.phase=1;
 member.teleport=true;assert(!calculate().active);member.teleport=false;
 bot.teleport=true;assert(!calculate().active);bot.teleport=false;
 ai.real=true;assert(!calculate().active);ai.real=false;
 ai.path=false;assert(!calculate().active&&ai.paths==8);ai.path=true;
 ai.unsafe=true;assert(!calculate().active);ai.unsafe=false;
 assert(calculate().active);member.alive=false;assert(!action.Execute(event)&&multiplier.GetValue(&chase)==1);
 std::cout<<"PASS: actual link/payload radii, distinct escape directions, stale movement, holds, tank and lifecycle gates\n";
#else
 assert(!calculate().active&&!action.Execute(event));
#endif
}
'''.replace('__GEOMETRY__',str(root/'playerbot/strategy/EncounterGeometry.h').replace('\\','/')).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-linked-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
