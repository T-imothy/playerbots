"""Recorded Magmadar overlapping fires and actual planner's bounded native admission."""
from pathlib import Path
import sys,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]) if len(sys.argv)>1 else root/'playerbot/strategy/values/MoltenCorePositionValue.cpp'
code=r'''
#include <cassert>
#include <iostream>
#include "playerbot/strategy/EncounterGeometry.h"
using namespace ai;
struct Guid{bool empty=true;bool IsEmpty()const{return empty;}};
namespace BotState{enum {BOT_STATE_COMBAT};}
struct Player {float x=1144.71f,y=-1029.47f,z=-184.221f;float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}bool HasAura(unsigned){return false;}};
struct PlayerbotAI{Player*bot;bool mag=true,nativeAdmit=true;unsigned calls=0;bool HasStrategy(const char*,int){return mag;}};
struct EncounterPosition{bool active=false,groundOnly=true;unsigned spell=0;Guid source;encounter::Point destination;};
std::vector<encounter::Circle> scene={
 {{1125.78f,-1015.35f,-186.309f},9.208f},{{1143.53f,-1030.97f,-184.382f},9.208f},
 {{1148.16f,-1021.79f,-184.734f},9.208f},{{1131.07f,-1002.44f,-185.693f},9.208f},
 {{1157.67f,-1025.19f,-183.636f},9.208f},{{1159.89f,-1025.47f,-184.19f},9.208f},
 {{1130.25f,-1028.77f,-185.416f},9.208f}};
bool pureGround=true;unsigned hazardSpell=0;bool sourceEmpty=true;bool secondScene=false;
bool MoltenCoreThreats(PlayerbotAI*,EncounterPosition&p,std::vector<encounter::Circle>&c){p.groundOnly=pureGround;p.spell=hazardSpell;p.source.empty=sourceEmpty;c=scene;return true;}
bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&){return false;}
// Model a native walkable exit only between the recorded coarse rings. This
// does NOT assert that live navmesh admits it: that remains a native retest.
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&p){++a->calls;
 const float dx=p.destination.x-a->bot->x,dy=p.destination.y-a->bot->y;
 const float distance=std::hypot(dx,dy),angle=std::atan2(dy,dx);
 if(secondScene)return a->nativeAdmit&&distance>5&&distance<6&&angle>2.1f&&angle<2.22f;
 return a->nativeAdmit&&distance>9&&distance<10&&angle>-.60f&&angle<-.45f;}
struct MoltenCorePositionValue{PlayerbotAI*ai;Player*bot;EncounterPosition Calculate();};
__METHOD__
int main(){Player bot;PlayerbotAI brain{&bot};MoltenCorePositionValue value{&brain,&bot};
 const encounter::Point here{bot.x,bot.y,bot.z};
 auto narrow=encounter::MagmadarFireEscapeCandidates(here,scene);assert(narrow.size()==2);
 assert(encounter::Distance2d(here,narrow.front())>9&&encounter::Distance2d(here,narrow.front())<10);
 for(const auto&p:encounter::EscapeCircles(here,scene)){
  EncounterPosition q;q.destination=p;assert(!ValidateEncounterDestination(&brain,q));}
 brain.calls=0;
#ifdef MANGOSBOT_ZERO
 assert(value.Calculate().active&&brain.calls<=16);
#else
 assert(!value.Calculate().active&&brain.calls<=32);
#endif
 brain.nativeAdmit=false;brain.calls=0;assert(!value.Calculate().active&&brain.calls<=64);
 brain.nativeAdmit=true;brain.mag=false;assert(!value.Calculate().active);brain.mag=true;
 pureGround=false;assert(!value.Calculate().active);pureGround=true;
 hazardSpell=20475;assert(!value.Calculate().active);hazardSpell=0;
 sourceEmpty=false;assert(!value.Calculate().active);sourceEmpty=true;
 scene={{{0,0,0},5}};assert(encounter::MagmadarFireEscapeCandidates({10,0,0},scene).empty());
 // Every proposed route must leave containing circles monotonically and
 // avoid entering another circle. The complete native route is checked later.
 auto exits=encounter::MagmadarFireEscapeCandidates({1,0,0},scene);assert(!exits.empty());
 for(auto p:exits){assert(p.x>=1&&encounter::OutsideCircles(p,scene));}
 // Native attempt20354574: after fear, mage142395 cast in fire until death.
 // The extra planner yard closes the gap; the full native margin8.208 does not.
 secondScene=true;bot.x=1124.06f;bot.y=-1017.93f;bot.z=-186.458f;
 scene={{{1120.06f,-996.878f,0},9.208f},{{1127.18f,-1019.08f,0},9.208f},
 {{1127.87f,-1032.85f,0},9.208f},{{1139.69f,-1026.4f,0},9.208f},
 {{1128.82f,-1009.67f,0},9.208f},{{1136.12f,-994.64f,0},9.208f},
 {{1118.33f,-1021.97f,0},9.208f}};
 assert(encounter::MagmadarFireEscapeCandidates({bot.x,bot.y,bot.z},scene).empty());
 brain.calls=0;auto escape=value.Calculate();
#ifdef MANGOSBOT_ZERO
 assert(escape.active&&brain.calls<=64);
 auto native=scene;for(auto&c:native)c.radius-=1.0f;
 assert(encounter::OutsideCircles(escape.destination,native));
 // Destination is still rejected if the native path validator refuses it.
 brain.nativeAdmit=false;assert(!value.Calculate().active);brain.nativeAdmit=true;
 brain.mag=false;assert(!value.Calculate().active);brain.mag=true;
 pureGround=false;assert(!value.Calculate().active);pureGround=true;
 hazardSpell=20475;assert(!value.Calculate().active);hazardSpell=0;
 sourceEmpty=false;assert(!value.Calculate().active);sourceEmpty=true;
#else
 assert(!escape.active);
#endif
 std::cout<<"PASS recorded narrow fire exit, native refusal, scope and bounded search\n";
}
'''.replace('__METHOD__',block(source.read_text(),'EncounterPosition MoltenCorePositionValue::Calculate('))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mag-narrow-exit-') as folder:
  d=Path(folder);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/I{root}',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
