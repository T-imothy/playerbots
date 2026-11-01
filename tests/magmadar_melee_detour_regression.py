"""Replay the recorded post-fear fire barrier through the actual Magmadar planner."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
code=r'''
#define _USE_MATH_DEFINES
#include <algorithm>
#include <cassert>
#include <cmath>
#include <list>
#include <vector>
#include <iostream>
constexpr unsigned CLASS_HUNTER=3;
namespace encounter { struct Point {float x=0,y=0,z=0;}; }
struct Unit {unsigned entry=11982,map=409,guid=1;bool world=true,alive=true,combat=true;Unit* victim=nullptr;
 float x=1115.49f,y=-987.304f,z=-185.204f,reach=8,o=2.38823f;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 unsigned GetMapId(){return map;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetCombatReach(){return reach;}float GetOrientation(){return o;}unsigned GetObjectGuid(){return guid;}Unit*GetVictim(){return victim;}};
struct Spline {bool done=true;encounter::Point end;bool Finalized(){return done;}auto FinalDestination(){return end;}};
struct Player:Unit {bool teleport=false,charmed=false,group=true;unsigned cls=1,instance=5;Spline* movespline=nullptr;
 bool IsInMap(Unit*u){return u->map==map;}bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}
 bool GetGroup(){return group;}unsigned getClass(){return cls;}unsigned GetInstanceId(){return instance;}};
struct PlayerbotAI {Player* bot;bool tank=true,ranged=false,heal=false;Player*GetBot(){return bot;}
 bool IsTank(Player*){return tank;}bool IsRanged(Player*){return ranged;}bool IsHeal(Player*){return heal;}};
struct EncounterPosition {bool active=false,anchored=false;unsigned spell=0,boss=0,map=0,instance=0;encounter::Point anchor,destination;};
struct Position {float x,y,z;float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
using HazardPosition=std::pair<Position,float>;
std::list<HazardPosition> nativeFire;
void AppendMoltenCoreGroundHazards(PlayerbotAI*,std::list<HazardPosition>&out){out=nativeFire;}
float NativeEncounterSpellRadius(unsigned id){assert(id==19272);return 35;}
bool navAvailable=true,extraHazard=false;unsigned checks=0;
bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&plan){
 ++checks;if(!navAvailable || extraHazard)return false;
 // Native path stub: complete straight walk on this recorded open floor.
 // The real validator also checks navigation, all hazards and fresh packs.
 auto b=ai->bot;auto p=plan.destination;
 double dx=p.x-b->x,dy=p.y-b->y,dz=p.z-b->z;
 double ex=b->x-1136.95,ey=b->y+1008.13,ez=b->z+185.805;
 double n=dx*dx+dy*dy+dz*dz,t=n?std::clamp(-(ex*dx+ey*dy+ez*dz)/n,0.0,1.0):0;
 double closest=std::sqrt((ex+t*dx)*(ex+t*dx)+(ey+t*dy)*(ey+t*dy)+(ez+t*dz)*(ez+t*dz));
 return closest>=8.236 && std::hypot(p.x-1136.95,p.y+1008.13)>9.236;
}
__FACING__
__DETOUR__
int main(){
 Player bot;bot.entry=0;bot.guid=2;bot.x=1144.99f;bot.y=-1021.86f;bot.z=-185.494f;bot.reach=1.5f;
 Unit boss;PlayerbotAI ai{&bot};EncounterPosition p;
 nativeFire={{{1136.95f,-1008.13f,-185.805f},5}};
 // This exact direct waypoint from native telemetry crosses the fire.
 p.destination={1125.92f,-1007.29f,-185.924f};assert(!ValidateEncounterDestination(&ai,p));
#ifdef MANGOSBOT_ZERO
 checks=0;assert(PlanMagmadarMeleeDetour(&ai,&boss,p));assert(checks<=24);
 assert(p.active && p.spell==19272 && p.boss==1 && p.map==409 && p.instance==5);
 assert(ValidateEncounterDestination(&ai,p));
 assert(std::hypot(p.destination.x-boss.x,p.destination.y-boss.y)<std::hypot(bot.x-boss.x,bot.y-boss.y)-1);
 Spline spline;spline.done=false;spline.end=p.destination;bot.movespline=&spline;
 EncounterPosition retained;assert(PlanMagmadarMeleeDetour(&ai,&boss,retained));
 assert(retained.destination.x==p.destination.x && retained.destination.y==p.destination.y);bot.movespline=nullptr;
 navAvailable=false;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));navAvailable=true;
 extraHazard=true;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));extraHazard=false;
 ai.tank=false;assert(PlanMagmadarMeleeDetour(&ai,&boss,p));
 ai.ranged=true;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));ai.ranged=false;
 ai.heal=true;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));ai.heal=false;
 bot.cls=CLASS_HUNTER;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));bot.cls=1;ai.tank=true;
#else
 assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));
#endif
 for(unsigned map:{0u,249u,469u,489u,533u}){bot.map=map;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));}bot.map=409;
 for(unsigned entry:{12056u,12057u,12259u,11502u}){boss.entry=entry;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));}boss.entry=11982;
 boss.victim=&bot;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));boss.victim=nullptr;
 bot.teleport=true;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));bot.teleport=false;
 boss.combat=false;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));boss.combat=true;
 bot.charmed=true;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));bot.charmed=false;
 nativeFire.front().first.z+=20;assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));nativeFire.clear();assert(!PlanMagmadarMeleeDetour(&ai,&boss,p));
 std::cout<<"PASS actual Magmadar post-fear melee detour, native path admission and encounter/role/era guards\n";
}
'''.replace('__FACING__',block(source,'bool MagmadarFacingSafe(')).replace('__DETOUR__',block(source,'bool PlanMagmadarMeleeDetour('))
assert 'if (PlanMagmadarMeleeDetour(ai,boss,plan)) return true;' in block(source,'bool PlanMagmadarFormation(')
with tempfile.TemporaryDirectory(prefix='magmadar-detour-') as directory:
    p=Path(directory);(p/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
