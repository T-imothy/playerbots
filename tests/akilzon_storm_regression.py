"""Compile actual storm source selection, ground shelter planning and dispatch."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root = Path(__file__).resolve().parents[1]
value = (root/'playerbot/strategy/values/AkilzonStormPositionValue.cpp').read_text()
action = (root/'playerbot/strategy/actions/AkilzonStormAction.cpp').read_text()
methods = '\n'.join(block(value, s) for s in ('Unit* ai::AkilzonStormBoss(', 'EncounterPosition AkilzonStormPositionValue::Calculate('))
methods += '\n' + '\n'.join(block(action, 'bool AkilzonStormAction::'+s+'(') for s in ('GetPlan', 'isUseful', 'ShouldReactionInterruptCast', 'Execute'))
code = r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
using uint32=unsigned; using ObjectGuid=unsigned;
enum{IDLE_MOTION_TYPE=0};
struct Unit{unsigned guid=1,entry=23574,map=568,instance=1,phase=1;float x=0,y=0,z=0;
 bool world=true,alive=true,combat=true,charmed=false,player=false;
 bool IsPlayer(){return player;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}unsigned GetMapId(){return map;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(float a,float b,float c){return std::sqrt((a-x)*(a-x)+(b-y)*(b-y)+(c-z)*(c-z));}
 float GetDistance(Unit*u){return GetDistance(u->x,u->y,u->z);}
};
struct DynamicObject:Unit{unsigned spell=44007,duration=8000;float radius=6;Unit*caster=nullptr;
 unsigned GetSpellId(){return spell;}unsigned GetDuration(){return duration;}float GetRadius(){return radius;}Unit*GetCaster(){return caster;}};
struct Map{DynamicObject*eye=nullptr;DynamicObject*GetDynamicObject(unsigned g){return eye&&eye->guid==g?eye:nullptr;}};
struct Aura{Unit*caster;Unit*GetCaster()const{return caster;}};
using SpellAuraHolder=Aura;
struct Motion{unsigned type=1;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Player;
struct GroupReference{Player*member;GroupReference*following=nullptr;Player*getSource(){return member;}GroupReference*next(){return following;}};
struct Group{GroupReference*first=nullptr;GroupReference*GetFirstMember(){return first;}};
struct Player:Unit{Player(){player=true;}bool teleport=false,stopped=true;Group*group=nullptr;Map*worldMap=nullptr;Aura*storm=nullptr;DynamicObject*eye=nullptr;Motion motion;
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 unsigned GetInstanceId(){return instance;}Group*GetGroup(){return group;}Map*GetMap(){return worldMap;}
 const Aura*GetSpellAuraHolder(unsigned id){return id==43648?storm:nullptr;}DynamicObject*GetDynObject(unsigned id){return id==44007?eye:nullptr;}
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}
};
namespace encounter{struct Point{float x=0,y=0,z=0;};}
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0,boss=0,source=0;encounter::Point destination;};
template<class T>struct Cached{T data;T Get(){return data;}};
struct Context{Cached<EncounterPosition>position;template<class T>Cached<T>*GetValue(const char*){return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool real=false,canMove=true,path=true;float adjustment=0,lastZ=-99;unsigned moves=0,stops=0;bool deleteOnValidate=false;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}Context*GetAiObjectContext(){return &context;}
 void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
};
bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&p){p.destination.z+=ai->adjustment;if(ai->deleteOnValidate)ai->bot->worldMap->eye=nullptr;return ai->path&&std::isfinite(p.destination.x);}
struct Event{};
namespace ai{
 Unit*AkilzonStormBoss(Player*,DynamicObject*);
 struct AkilzonStormPositionValue{PlayerbotAI*ai;Player*bot;EncounterPosition Calculate();};
 struct AkilzonStormAction{PlayerbotAI*ai;Player*bot;static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
  bool IsReaction(){return false;}void SetDuration(unsigned){}
  bool MoveTo(unsigned,float,float,float z,bool,bool,bool,bool){++ai->moves;ai->lastZ=z;return true;}
 };
}
using namespace ai;
__METHODS__
int main(){
 Player bot,member;bot.guid=10;member.guid=11;member.x=20;member.z=15;Group group;GroupReference memberRef{&member},botRef{&bot,&memberRef};group.first=&botRef;bot.group=member.group=&group;
 Unit boss;Aura storm{&boss};member.storm=&storm;DynamicObject eye;eye.guid=3;eye.x=20;eye.caster=&member;member.eye=&eye;Map map;map.eye=&eye;bot.worldMap=&map;
 PlayerbotAI ai{&bot};AkilzonStormPositionValue planner{&ai,&bot};AkilzonStormAction action{&ai,&bot};Event event;
 auto calculate=[&](){ai.context.position.data=planner.Calculate();return ai.context.position.data;};
#ifndef MANGOSBOT_ZERO
 auto p=calculate();assert(p.active&&p.destination.x==20&&p.destination.z==0&&action.ShouldReactionInterruptCast());
 assert(action.Execute(event)&&ai.moves==1&&ai.lastZ==0); // ground eye, not airborne player
 ai.adjustment=1;assert(action.Execute(event)&&ai.lastZ==1); // preserve validated terrain adjustment
 ai.adjustment=10;assert(!action.Execute(event));ai.adjustment=0;
 ai.deleteOnValidate=true;assert(!action.Execute(event));ai.deleteOnValidate=false;map.eye=&eye;
 bot.x=18;calculate();assert(action.isUseful()&&!action.ShouldReactionInterruptCast());assert(action.Execute(event)&&ai.stops==1&&!action.isUseful());
 bot.x=0;assert(calculate().active);eye.duration=0;assert(!action.Execute(event)&&!calculate().active);eye.duration=8000;
 eye.radius=std::numeric_limits<float>::quiet_NaN();assert(!calculate().active);eye.radius=6;
 eye.phase=2;assert(!calculate().active);eye.phase=1;
 member.storm=nullptr;assert(!calculate().active);member.storm=&storm;
 boss.combat=false;assert(!calculate().active);boss.combat=true;
 Group strangers;member.group=&strangers;assert(!calculate().active);member.group=&group;
 member.teleport=true;assert(!calculate().active);member.teleport=false;
 bot.teleport=true;assert(!calculate().active);bot.teleport=false;
 ai.real=true;assert(!calculate().active);ai.real=false;
 ai.canMove=false;assert(!calculate().active);ai.canMove=true;
 ai.path=false;assert(!calculate().active);ai.path=true;
 DynamicObject second=eye;second.guid=4;second.caster=&bot;bot.eye=&second;bot.storm=&storm;assert(!calculate().active);
#else
 assert(!calculate().active&&!action.isUseful()&&!action.Execute(event));
#endif
 std::cout<<"PASS: native storm eye, ground position, fresh lifetime/phase/group gates, terrain adjustment and safe hold\n";
}
'''.replace('__METHODS__', methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-storm-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in ('tbc','wotlk'):
    core=root.parent/f'mangos-{era}-behavior'
    effects=(core/'src/game/Spells/SpellEffects.cpp').read_text()
    assert 'unitTarget->CastSpell(nullptr, 44007, TRIGGERED_OLD_TRIGGERED)' in effects
    spells=(core/'src/game/Spells/Spell.cpp').read_text()
    assert 'case 43657:' in spells and 'HasAura(44007)' in spells
