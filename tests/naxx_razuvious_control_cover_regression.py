"""Actual Classic control-station admission: native LOS/range/path dependencies."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
body=block((root/'playerbot/strategy/actions/NaxxramasControlCover.cpp').read_text(),'bool ai::RazuviousControlCover(')
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include "__GEOMETRY__"
using uint32=unsigned;constexpr float M_PI_F=3.14159265358979323846f;constexpr unsigned CLASS_PRIEST=5;
struct Unit{unsigned entry=16061,guid=1;bool world=true,alive=true,charmed=false,same=true,visible=true;
 float x=4,y=0,z=0,reach=1.5f;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}
 unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetCombatReach(){return reach;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit*u){return GetDistance(u->x,u->y,u->z);}
 bool IsWithinLOS(float a,float,float,bool ignoreM2){assert(ignoreM2);return visible&&(entry==16061?a>=0:true);}
};
struct Player:Unit{unsigned map=533,instance=7,cls=5;bool combat=true,transfer=false,group=true,transport=false;Unit*charm=nullptr;float floorDelta=0;
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}unsigned getClass(){return cls;}
 bool IsInCombat(){return combat;}bool IsBeingTeleported(){return transfer;}bool GetGroup(){return group;}bool GetTransport(){return transport;}
 Unit*GetCharm(){return charm;}bool IsInMap(Unit*u){return u&&u->same;}float GetCollisionHeight(){return 2;}
 void UpdateAllowedPositionZ(float,float,float&zz){zz+=floorDelta;}
};
struct PlayerbotAI{Player*bot;bool real=false,move=true,rangeKnown=true,path=true;float range=20;unsigned paths=0;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return move;}
 bool GetSpellRange(const char*,float*out){*out=range;return rangeKnown;}
};
namespace ai{
 struct EncounterPosition{bool active=false;unsigned map=0,instance=0,boss=0,source=0,spell=0;encounter::Point destination;};
 bool allowed=true,engaged=true;float shoutRadius=45;
 bool NaxxramasControlAllowed(PlayerbotAI*){return allowed;}
 bool NaxxramasEncounterEngaged(Player*,Unit*){return engaged;}
 float NativeEncounterSpellRadius(unsigned id){assert(id==29107);return shoutRadius;}
 bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&){++a->paths;return a->path;}
 bool RazuviousControlCover(PlayerbotAI*,Unit*,Unit*,EncounterPosition&);
}
using namespace ai;
__BODY__
int main(){
 Player bot;bot.x=2;Unit boss,student;student.entry=16803;student.guid=2;student.x=1;
 PlayerbotAI a{&bot};EncounterPosition p;
#ifdef MANGOSBOT_ZERO
 assert(RazuviousControlCover(&a,&boss,&student,p)&&p.active&&p.spell==29107&&p.source==2&&p.instance==7);
 assert(p.destination.x<0&&student.GetDistance(p.destination.x,p.destination.y,p.destination.z)<20&&a.paths==1);
 bot.x=-2;const auto n=a.paths;assert(RazuviousControlCover(&a,&boss,&student,p)&&a.paths==n); // already covered
 bot.x=2;a.path=false;a.paths=0;assert(!RazuviousControlCover(&a,&boss,&student,p)&&!p.active&&a.paths<=8);a.path=true;
 bot.floorDelta=4;assert(!RazuviousControlCover(&a,&boss,&student,p));bot.floorDelta=0;
 student.visible=false;assert(!RazuviousControlCover(&a,&boss,&student,p));student.visible=true;
 student.x=70;assert(!RazuviousControlCover(&a,&boss,&student,p));student.x=1;
 a.move=false;assert(!RazuviousControlCover(&a,&boss,&student,p));a.move=true;
 bot.transport=true;assert(!RazuviousControlCover(&a,&boss,&student,p));bot.transport=false;
 bot.charm=&student;assert(!RazuviousControlCover(&a,&boss,&student,p));bot.charm=nullptr;
 student.charmed=true;assert(!RazuviousControlCover(&a,&boss,&student,p));student.charmed=false;
 boss.same=false;assert(!RazuviousControlCover(&a,&boss,&student,p));boss.same=true;
 student.same=false;assert(!RazuviousControlCover(&a,&boss,&student,p));student.same=true;
 student.entry=16506;assert(!RazuviousControlCover(&a,&boss,&student,p));student.entry=16803;
 boss.entry=15953;assert(!RazuviousControlCover(&a,&boss,&student,p));boss.entry=16061;
 bot.cls=8;assert(!RazuviousControlCover(&a,&boss,&student,p));bot.cls=5;
 bot.map=469;assert(!RazuviousControlCover(&a,&boss,&student,p));bot.map=533;
 bot.combat=false;assert(!RazuviousControlCover(&a,&boss,&student,p));bot.combat=true;
 bot.transfer=true;assert(!RazuviousControlCover(&a,&boss,&student,p));bot.transfer=false;
 a.real=true;assert(!RazuviousControlCover(&a,&boss,&student,p));a.real=false;
 engaged=false;assert(!RazuviousControlCover(&a,&boss,&student,p));engaged=true;
 allowed=false;assert(!RazuviousControlCover(&a,&boss,&student,p));allowed=true;
 a.rangeKnown=false;assert(!RazuviousControlCover(&a,&boss,&student,p));a.rangeKnown=true;
 shoutRadius=0;assert(!RazuviousControlCover(&a,&boss,&student,p));shoutRadius=45;
 // A distant student can be controlled outside native Shout radius without cover.
 bot.x=60;student.x=58;assert(RazuviousControlCover(&a,&boss,&student,p)&&p.destination.x==60);
#else
 assert(!RazuviousControlCover(&a,&boss,&student,p)&&a.paths==0);
#endif
 std::cout<<"PASS: Classic Razuvious control cover, native LOS/range/route, authorization and era isolation\n";
}
'''.replace('__BODY__',body).replace('__GEOMETRY__',str(root/'playerbot/strategy/EncounterGeometry.h').replace('\\','/'))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mantech-razu-cover-')as folder:
  d=Path(folder);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
