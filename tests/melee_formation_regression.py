"""Actual formation geometry versus native follow and settled regroup, all eras.

The world/terrain interfaces are flat unobstructed mocks. This verifies the
coordinate contract, not native pathfinding or avoidance of hostile packs.
--baseline-ref REF runs the same checks against that revision's Formations.cpp
and requires the known geometry failure, providing a reproducible old-code test.
"""
from pathlib import Path
import argparse, subprocess, tempfile
from behavior_regression import block

args=argparse.ArgumentParser()
args.add_argument('--baseline-ref')
args=args.parse_args()
root=Path(__file__).resolve().parents[1]
path='playerbot/strategy/values/Formations.cpp'
source=(root/path).read_text()
if args.baseline_ref:
    source=subprocess.run(['git','show',args.baseline_ref+':'+path],cwd=root,check=True,capture_output=True,text=True).stdout
follow=(root/'playerbot/strategy/actions/FollowActions.cpp').read_text()
ai_source=(root/'playerbot/PlayerbotAI.cpp').read_text()
methods='\n'.join(block(source,m) for m in (
    'bool IsSameLocation(', 'bool Formation::IsNullLocation(', 'float Formation::GetAngle(',
    'WorldLocation FollowFormation::GetLocation(', 'float Formation::GetFollowAngle('))
methods+='\n'+block(ai_source,'float PlayerbotAI::GetRange(')
methods+='\n'+block(follow,'bool ai::RaidRegroupNeeded(')
melee=block(source,'    class MeleeFormation')+';'
code=r'''
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <map>
#include <string>
#include <type_traits>
#include <vector>
constexpr float M_PI_F=3.14159265358979323846f;
constexpr double M_PI=3.14159265358979323846;
struct PlayerbotAI;struct Player;struct Unit;
using ObjectGuid=Unit*;
struct WorldLocation{int mapid=-1;float coord_x=0,coord_y=0,coord_z=0;WorldLocation(){}
 WorldLocation(int m,float x,float y,float z):mapid(m),coord_x(x),coord_y(y),coord_z(z){}};
struct Spline{bool finalized=true;struct Point{float x,y,z;};Point dest{0,0,0};
 bool Finalized(){return finalized;}Point CurrentDestination(){return dest;}};
struct Map{template<class...T>bool IsInLineOfSight(T...){return true;}};
struct GenericTransport{void CalculatePassengerPosition(float&,float&,float&){} };
struct GroupReference{Player*player=nullptr;GroupReference*tail=nullptr;Player*getSource(){return player;}GroupReference*next(){return tail;}};
struct Group{std::vector<GroupReference>refs;bool raid=true;bool IsRaidGroup(){return raid;}GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs[0];}};
struct Unit{float x=100,y=200,z=50,orientation=0,bounds=0.5f;bool alive=true,world=true;
 Spline spline;Spline*movespline=&spline;Map native;
 struct MovementInfo{float GetOrientationInMotion(float o){return o;}}m_movementInfo;
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return orientation;}
 void GetPosition(float&a,float&b,float&c){a=x;b=y;c=z;}float GetObjectBoundingRadius(){return bounds;}
 bool IsAlive(){return alive;}bool IsInWorld(){return world;}float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 bool IsInMap(Unit*){return true;}Map*GetMap(){return &native;}unsigned GetPhaseMask(){return 1;}
 GenericTransport*GetTransport(){return nullptr;}float GetSpeedInMotion(){return 0;}float GetCollisionHeight(){return 2;}
 void UpdateAllowedPositionZ(float&,float&,float&){}
 void GetNearPointAt(float tx,float ty,float tz,Unit*,float&a,float&b,float&c,float,float range,float angle){a=tx+std::cos(angle)*range;b=ty+std::sin(angle)*range;c=tz;}};
struct Manager{template<class F>void ForEachPlayerbot(F){}};
struct Player:Unit{PlayerbotAI*brain=nullptr;Group*group=nullptr;bool tank=false,heal=false;int map=469;
 Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return brain;}Manager*GetPlayerbotMgr(){return nullptr;}
 int GetMapId(){return map;}bool IsBeingTeleported(){return false;}bool HasCharmer(){return false;}
 bool IsNonMeleeSpellCasted(bool,bool,bool){return false;}bool IsTaxiFlying(){return false;}};
namespace ai{
enum BotState{BOT_STATE_COMBAT,BOT_STATE_NON_COMBAT};
class Formation{public:PlayerbotAI*ai;Player*bot;Formation(PlayerbotAI*,std::string);virtual~Formation(){}
 static WorldLocation NullLocation;static bool IsNullLocation(WorldLocation const&);
 virtual WorldLocation GetLocation(){return NullLocation;}virtual float GetAngle();virtual float GetOffset(){return 0;}
 virtual std::string GetTargetName(){return "";}protected:float GetFollowAngle();};
class FollowFormation:public Formation{public:FollowFormation(PlayerbotAI*a,std::string n):Formation(a,n){}WorldLocation GetLocation()override;};
bool RaidRegroupNeeded(PlayerbotAI*);
}
using namespace ai;
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{Value<ObjectGuid>follow;Value<Formation*>formation;std::map<std::string,Value<float>>ranges;
 template<class T>Value<T>*GetValue(std::string name,std::string qualifier=""){
 if constexpr(std::is_same_v<T,float>)return &ranges[qualifier];
 else if constexpr(std::is_same_v<T,Formation*>)return &formation;
 else return &follow;}};
struct PlayerbotAI{Player*bot;Context context;Context*aiObjectContext=&context;bool combat=false;
 PlayerbotAI(Player*p):bot(p){p->brain=this;}Player*GetBot(){return bot;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(ObjectGuid p){return p;}bool IsSafe(Unit*u){return u&&u->world;}bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->heal;}
 bool HasRealPlayerMaster(){return true;}bool IsRealPlayer(){return false;}bool IsStateActive(BotState){return combat;}bool CanMove(){return true;}
 bool HasStrategy(const char*s,BotState){return std::string(s)=="follow";}bool IsJumping(){return false;}float GetRange(std::string);};
Formation::Formation(PlayerbotAI*a,std::string):ai(a),bot(a->bot){}
WorldLocation Formation::NullLocation;
struct WorldPosition{Unit*unit;WorldPosition(Unit*u):unit(u){}
 float getAngleTo(WorldLocation p){return std::atan2(p.coord_y-unit->y,p.coord_x-unit->x);}};
struct Facade{bool IsAlive(Unit*u){return u&&u->alive;}}sServerFacade;
struct Config{float spellDistance=30,shootDistance=30,fleeDistance=10,healDistance=40,followDistance=1.5f,
 sightDistance=60,raidFollowDistance=5,wanderMinDistance=5,wanderMaxDistance=10;}sPlayerbotAIConfig;
bool RaidRestInProgress(PlayerbotAI*){return false;}
#define AI_VALUE(T,N) ai->GetAiObjectContext()->GetValue<T>(N)->Get()
__METHODS__
namespace ai { __MELEE__ }
struct TargetRef{Unit*unit;bool isValid()const{return unit!=nullptr;}Unit*operator->()const{return unit;}};
struct FollowMovementGenerator{TargetRef i_target;float offset,angle;
 float GetAngle()const{return angle;}float GetDynamicTargetDistance(Unit&owner,bool)const{return offset+owner.bounds+i_target->bounds;}
 bool _getLocation(Unit&,float&,float&,float&,bool)const;};
__NATIVE__
void check(bool condition,const char*message){if(!condition){std::cerr<<message<<"\n";std::exit(42);}}
int main(){
 Player members[40];Group group;group.refs.resize(40);
 for(unsigned i=0;i<40;++i){members[i].group=&group;members[i].tank=i>0&&i<5;members[i].heal=i>=5&&i<13;
 group.refs[i].player=&members[i];group.refs[i].tail=i<39?&group.refs[i+1]:nullptr;}
 Player&leader=members[0];unsigned cases=0;
 for(unsigned i=1;i<40;++i){Player&bot=members[i];PlayerbotAI brain(&bot);MeleeFormation formation(&brain);
 brain.context.follow.value=&leader;brain.context.formation.value=&formation;
 for(float radius:{1.0f,5.0f})for(float orientation:{0.0f,M_PI_F/2,M_PI_F,3*M_PI_F/2,2*M_PI_F-0.01f}){
 leader.orientation=orientation;brain.context.ranges["followraid"].value=radius;
 check(std::fabs(formation.GetOffset()-radius)<0.001f,"configured raid follow radius changed");
 auto station=formation.GetLocation();check(!Formation::IsNullLocation(station),"formation station missing");
 check(std::fabs(std::hypot(station.coord_x-leader.x,station.coord_y-leader.y)-radius)<0.001f,"formation station radius changed");
 // MovementAction::Follow subtracts the target's body radius before native
 // follow adds its normal contact radii. Keep that existing behavior intact.
 const float offset=radius<=leader.bounds?0:radius-leader.bounds;
 FollowMovementGenerator native{{&leader},offset,formation.GetAngle()};float x,y,z;
 check(native._getLocation(bot,x,y,z,false),"native stationary follow failed");
 const float expectedAngle=std::atan2(station.coord_y-leader.y,station.coord_x-leader.x);
 const float actualAngle=std::atan2(y-leader.y,x-leader.x);
 check(std::fabs(std::remainder(actualAngle-expectedAngle,2*M_PI_F))<0.0001f,"GEOMETRY_MISMATCH: native follow rotated the planned melee station");
 bot.x=x;bot.y=y;bot.z=z;check(!RaidRegroupNeeded(&brain),"settled native follow requests repeated regroup");
 bot.x=station.coord_x+4;bot.y=station.coord_y;check(RaidRegroupNeeded(&brain),"displaced follower does not regroup");
 ++cases;}
 brain.context.follow.value=nullptr;check(Formation::IsNullLocation(formation.GetLocation()),"null leader produced station");
 check(formation.GetAngle()==0&&!RaidRegroupNeeded(&brain),"null leader dereferenced or regrouped");
 }
 std::cout<<"PASS "<<cases<<" actual melee/native-follow geometries, raid range1/5, settled/displaced regroup, null leader\n";
}
'''
code=code.replace('__METHODS__',methods).replace('__MELEE__',melee)
for core,era in (('classic','ZERO'),('tbc','ONE'),('wotlk','TWO')):
    native=(root.parent/core/'src/game/MotionGenerators/TargetedMovementGenerator.cpp').read_text()
    body=block(native,'bool FollowMovementGenerator::_getLocation(')
    with tempfile.TemporaryDirectory(prefix='melee-formation-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code.replace('__NATIVE__',body))
        compiled=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
        if compiled.returncode:raise RuntimeError(compiled.stdout+compiled.stderr)
        result=subprocess.run([str(p/'test.exe')],cwd=p,capture_output=True,text=True)
        if args.baseline_ref:
            assert result.returncode==42 and 'GEOMETRY_MISMATCH' in result.stderr,(result.returncode,result.stdout,result.stderr)
            print(f'REPRODUCED {core}: {args.baseline_ref} fails actual melee/native-follow geometry')
        else:
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            print(core+': '+result.stdout.strip())
