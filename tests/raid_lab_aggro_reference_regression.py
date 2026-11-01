"""Exercise native-aggression admission in the isolated staging helper."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#define _USE_MATH_DEFINES
#include <cassert>
#include <iostream>
#include <cmath>
struct Player;
struct Ref{Player*p;Ref*n=nullptr;Player*getSource(){return p;}Ref*next(){return n;}};
struct Group{Ref*head;Ref*GetFirstMember(){return head;}};
struct Player{bool world=true,alive=true,tp=false,gm=false;unsigned level=60,team=1;Group*group=nullptr;
 Group*GetGroup(){return group;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return tp;}
 bool IsGameMaster(){return gm;}unsigned GetTeam(){return team;}unsigned GetLevel(){return level;}float GetCollisionHeight(){return 2;}};
constexpr unsigned REACT_AGGRESSIVE=2,RANDOM_MOTION_TYPE=1;
struct Brain{bool aggressive=true;bool HasReactState(unsigned state){assert(state==2);return aggressive;}};
struct Creature{bool world=true,alive=true,pet=false,totem=false,critter=false,neutral=false,canAttack=true,enemy=true,hasBrain=true;
 Brain brain;bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsPet(){return pet;}bool IsTotem(){return totem;}
 bool IsCritter(){return critter;}bool IsNeutralToAll(){return neutral;}bool CanInitiateAttack(){return canAttack;}
 bool visible=false,edgeVisible=false;unsigned losCalls=0;
 unsigned motion=0;float wander=0,homeX=0,homeY=0,homeZ=0;
 unsigned GetDefaultMovementType(){return motion;}float GetRespawnRadius(){return wander;}
 void GetRespawnCoord(float&x,float&y,float&z){x=homeX;y=homeY;z=homeZ;}
 bool IsWithinLOS(float x,float y,float z,bool native){++losCalls;assert(native&&z==2);return visible||(edgeVisible&&std::hypot(x,y)>4);}
 Brain*AI(){return hasBrain?&brain:nullptr;}bool IsEnemy(Player*p){assert(!p->gm);return enemy;}};
'''
code+=block(source,'Player* RaidLabAggroReference(')
code+=block(source,'bool RaidLabBodyPullRisk(')
code+=block(source,'float RaidLabLandingRadius(')
code+=block(source,'bool RaidLabInsideWanderEnvelope(')
code+=block(source,'bool RaidLabFormationVisible(')
code+=r'''
int main(){
 assert(std::fabs(RaidLabLandingRadius(20,5,.4f)-27.4f)<.001f);
 assert(RaidLabLandingRadius(20,0,0)==22);
 for(float bad:{-1.f,31.f,NAN})assert(RaidLabLandingRadius(20,bad,.4f)<0);
 assert(RaidLabLandingRadius(NAN,5,.4f)<0&&RaidLabLandingRadius(20,5,6)<0);
 Player leader,bad,good;leader.gm=true;bad.gm=true;Ref last{&good},mid{&bad,&last},first{&leader,&mid};Group group{&first};
 assert(!RaidLabAggroReference(&leader));leader.group=&group;assert(RaidLabAggroReference(&leader)==&good);
 good.tp=true;assert(!RaidLabAggroReference(&leader));good.tp=false;good.level=59;assert(!RaidLabAggroReference(&leader));good.level=60;
 good.team=2;assert(!RaidLabAggroReference(&leader));good.team=1;good.alive=false;assert(!RaidLabAggroReference(&leader));good.alive=true;
 Creature mob;assert(!RaidLabBodyPullRisk(nullptr,&good));assert(!RaidLabBodyPullRisk(&mob,nullptr));assert(RaidLabBodyPullRisk(&mob,&good));
 for(bool* field:{&mob.pet,&mob.totem,&mob.critter,&mob.neutral}){*field=true;assert(!RaidLabBodyPullRisk(&mob,&good));*field=false;}
 for(bool* field:{&mob.world,&mob.alive,&mob.canAttack,&mob.enemy,&mob.hasBrain,&mob.brain.aggressive}){*field=false;assert(!RaidLabBodyPullRisk(&mob,&good));*field=true;}
 assert(RaidLabBodyPullRisk(&mob,&good));
 // Native spawn grace in a GM-only grid expires after group delivery. Preserve
 // the current-state corridor check, but never call that future landing safe.
 mob.canAttack=false;assert(!RaidLabBodyPullRisk(&mob,&good));assert(RaidLabBodyPullRisk(&mob,&good,true));
 for(bool* field:{&mob.world,&mob.alive,&mob.enemy,&mob.hasBrain,&mob.brain.aggressive}) {
  *field=false;assert(!RaidLabBodyPullRisk(&mob,&good,true));*field=true;
 }
 mob.neutral=true;assert(!RaidLabBodyPullRisk(&mob,&good,true));mob.neutral=false;mob.canAttack=true;
 mob.losCalls=0;assert(!RaidLabFormationVisible(&mob,&good,0,0,0,5)&&mob.losCalls==17);
 mob.visible=true;mob.losCalls=0;assert(RaidLabFormationVisible(&mob,&good,0,0,0,5)&&mob.losCalls==1);mob.visible=false;
 mob.edgeVisible=true;assert(RaidLabFormationVisible(&mob,&good,0,0,0,5));mob.edgeVisible=false;
 for(float invalid:{-1.f,36.f,NAN})assert(RaidLabFormationVisible(&mob,&good,0,0,0,invalid));
 assert(!RaidLabInsideWanderEnvelope(&mob,0,0,0,30));mob.motion=RANDOM_MOTION_TYPE;mob.wander=5;
 assert(RaidLabInsideWanderEnvelope(&mob,32,0,0,30));assert(!RaidLabInsideWanderEnvelope(&mob,36,0,0,30));
 mob.homeX=20;assert(RaidLabInsideWanderEnvelope(&mob,36,0,0,30));
 mob.wander=NAN;assert(RaidLabInsideWanderEnvelope(&mob,100,0,0,30));mob.wander=0;assert(!RaidLabInsideWanderEnvelope(&mob,0,0,0,30));
 std::cout<<"PASS GM-off level/faction reference and aggressive native enemy admission; passive/neutral/trigger-like actors excluded\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-aggro-reference-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
