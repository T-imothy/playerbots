"""Execute actual suppression station policy and the enclosing formation branch.

Native spell/terrain/path interfaces are controlled fixtures. This does not
establish a successful live suppression-room run. --baseline-ref reproduces
the old forced outward-spread failure against that revision's actual branch.
"""
from pathlib import Path
import argparse, subprocess, tempfile
from behavior_regression import block

args=argparse.ArgumentParser();args.add_argument('--baseline-ref');args=args.parse_args()
root=Path(__file__).resolve().parents[1]
path='playerbot/strategy/actions/ClassicRaidActions.cpp'
source=(root/path).read_text()
if args.baseline_ref:
    source=subprocess.run(['git','show',args.baseline_ref+':'+path],cwd=root,check=True,capture_output=True,text=True).stdout
helpers='\n'.join(block(source,m) for m in ('    float Range(', '    bool PositionLegal(', '    bool KeepFormationRoute('))
if '    bool SuppressionCombatStation(' in source:
    helpers+='\n'+'\n'.join(block(source,m) for m in ('    bool SuppressionTrash(', '    bool SuppressionStationActive(', '    Player* SuppressionLeader(', '    std::vector<encounter::Circle> SuppressionFlames(', '    bool SuppressionCombatStation('))
calc=block(source,'ClassicRaidPlan ClassicRaidPlanValue::Calculate(')
marker='    if (BroodlordFormationPlan' if '    if (BroodlordFormationPlan' in calc else '    if (SuppressionCombatStation' if '    if (SuppressionCombatStation' in calc else '    const bool ranged = ai->IsRanged(bot) || ai->IsHeal(bot);'
tail=calc[calc.index(marker):]
arrival=block((root/'playerbot/strategy/values/EncounterPositionValue.cpp').read_text(),'bool ai::EncounterMovementRequired(')
chase=block(source,'bool ai::BlackwingSuppressionChaseAllowed(') if 'bool ai::BlackwingSuppressionChaseAllowed(' in source else 'bool ai::BlackwingSuppressionChaseAllowed(PlayerbotAI*,Unit*){return true;}'
code=r'''
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <vector>
#include "__GEOMETRY__"
#include "__POLICY__"
using namespace ai;using uint32=unsigned;constexpr float M_PI_F=3.14159265358979323846f;
constexpr double M_PI=3.14159265358979323846;
long long clockNow=100;long long testTime(void*){return clockNow;}
#define time testTime
constexpr unsigned CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_HUNTER=3,CLASS_PRIEST=5,CLASS_DRUID=11,CLASS_SHAMAN=7,CLASS_PALADIN=2;
struct Guid{unsigned id=0;bool IsEmpty()const{return !id;}bool operator==(Guid b)const{return id==b.id;}};using ObjectGuid=Guid;
struct Group{Guid leader{5};Guid GetLeaderGuid(){return leader;}};
constexpr unsigned IN_PROGRESS=1,DONE=2;
struct InstanceData{unsigned state=0;unsigned GetData(unsigned){return state;}};
struct Map{InstanceData instance;InstanceData*GetInstanceData(){return &instance;}};
struct Spline{bool done=true;encounter::Point end{};bool Finalized(){return done;}auto FinalDestination(){return end;}};
struct Unit{float x=0,y=0,z=0,orientation=0;unsigned entry=12458;Guid guid{1};bool los=true,engaged=true,live=true,player=false;Unit*victim=nullptr;
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return orientation;}
 unsigned GetEntry(){return entry;}Guid GetObjectGuid(){return guid;}Unit*GetVictim(){return victim;}bool IsPlayer(){return player;}Unit*GetCharmer(){return nullptr;}
 float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}float GetCombatReach(){return 1.5f;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit*u){return GetDistance(u->x,u->y,u->z);}bool IsWithinLOS(float,float,float,bool){return los;}};
struct Player:Unit{unsigned map=469,instance=3,cls=CLASS_MAGE;bool ranged=true,heal=false,tank=false,real=false,authorized=true;Group group;Spline spline;Spline*movespline=&spline;
 Map native;Map*GetMap(){return &native;}Player(){player=true;guid={2};}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}unsigned getClass(){return cls;}
 float GetCollisionHeight(){return 2;}bool CanReachWithMeleeAttack(Unit*u){return GetDistance(u)<=3;}Group*GetGroup(){return &group;}bool isRealPlayer(){return real;}};
struct EncounterPosition{bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0;Guid boss,source;encounter::Point destination{};};
struct ClassicRaidPlan{EncounterPosition position;Guid boss,target;bool emergency=false,holdDamage=false;};
namespace ai{bool EncounterMovementRequired(Player*,const encounter::Point&,float=1.5f);}
struct Context{std::list<Guid>nearby;struct Value{std::list<Guid>list;auto Get(){return list;}};
 template<class T>Value*GetValue(const char*,const char*){static Value v;v.list=nearby;return &v;}};
struct PlayerbotAI{Player bot,neighbor,tank,leader;Unit boss,hatcher;Context context;std::vector<Player*>members;
 float spellMax=40,hunterMin=5;bool room=true,pathAllowed=true,hunterSpell=true;std::vector<encounter::Circle>ground;unsigned validations=0;
 PlayerbotAI(){bot.x=neighbor.x=1;tank.x=5;boss.x=5;boss.victim=&tank;hatcher.entry=12468;hatcher.guid={4};hatcher.engaged=false;leader.guid={5};leader.real=true;
 members={&bot,&neighbor,&leader};context.nearby={{1},{4}};}
 Player*GetBot(){return &bot;}bool IsRanged(Player*p){return p->ranged;}bool IsHeal(Player*p){return p->heal;}bool IsTank(Player*p){return p->tank;}float GetRange(const char*){return spellMax;}
 bool GetSpellRange(const char*spell,float*maximum,float*minimum=nullptr){*maximum=spellMax;if(minimum)*minimum=hunterMin;return std::string(spell)!="auto shot"||hunterSpell;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(Guid g){return g.id==1?&boss:g.id==4?&hatcher:g.id==5?&leader:nullptr;}};
namespace ai{bool BlackwingSuppressionChaseAllowed(PlayerbotAI*,Unit*);}
struct PullStrategy{static PullStrategy*active;bool allowed=false,started=false;long long start=100;Unit*target=nullptr;Guid requester{5};
 static PullStrategy*Get(PlayerbotAI*){return active;}bool IsEncounterPreparationAllowed(){return allowed;}bool HasPullStarted(){return started;}
 Unit*GetTarget(){return target;}long long GetPullStartTime(){return start;}unsigned GetMaxPullTime(){return 15;}Guid GetRequester(){return requester;}};
PullStrategy*PullStrategy::active=nullptr;
struct WaitForAttackStrategy{static Unit*target;static WaitForAttackStrategy*Get(PlayerbotAI*){static WaitForAttackStrategy strategy;return &strategy;}Unit*GetExplicitAttackTarget(PlayerbotAI*){return target;}};Unit*WaitForAttackStrategy::target=nullptr;
bool Member(Player*b,Player*p){return p&&p->live&&p->map==b->map;}
bool CanManageBotCommands(PlayerbotAI*,Player*p){return p&&p->authorized;}
bool Live(Player*,Unit*u){return u&&u->live;}bool Engaged(Player*,Unit*u){return u&&u->engaged&&u->live;}
bool BlackwingSuppressionMovementActive(PlayerbotAI*a){return a->room&&a->bot.map==469;}
float NativeEncounterSpellRadius(unsigned id){return id==22442?15:0;}
std::vector<Player*>Members(PlayerbotAI*a){return a->members;}
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&p,bool=true){++a->validations;
 return a->pathAllowed&&p.map==a->bot.map&&p.instance==a->bot.instance&&encounter::OutsideCircles(p.destination,a->ground);}
bool circleRoute=true;
bool LocalCircleRoute(PlayerbotAI*,const EncounterPosition&,const std::vector<encounter::Circle>&){return circleRoute;}
bool BroodlordFormationPlan(PlayerbotAI*,Unit*,Unit*,ClassicRaidPlan&){return false;}
__ARRIVAL__
__HELPERS__
__CHASE__
ClassicRaidPlan CombatSlice(PlayerbotAI*ai,Unit*boss,Unit*target){Player*bot=ai->GetBot();ClassicRaidPlan plan;plan.boss=boss->guid;const uint32 entry=boss->entry;
__TAIL__
void check(bool ok,const char*message){if(!ok){std::cerr<<message<<"\n";std::exit(42);}}
int main(){
 PlayerbotAI a;
 auto at=[](const ClassicRaidPlan&p,float x,float y){return p.position.active&&std::hypot(p.position.destination.x-x,p.position.destination.y-y)<0.01f;};
 for(unsigned entry:{12458u,12468u,14022u,14023u,14024u,14025u})for(bool healer:{false,true}){
 a.boss.entry=entry;a.boss.x=entry==12468?20:5;a.bot.heal=healer;
 auto p=CombatSlice(&a,&a.boss,&a.boss);
 check(at(p,a.bot.x,a.bot.y),"UNNECESSARY_SPREAD: safe compact leader station moved outward");
 check(!p.holdDamage&&!p.emergency,"safe leader station suppresses combat");}
 a.boss.entry=12458;a.boss.x=5;a.bot.heal=false;
 // Safe casting range is insufficient: a far follower returns toward leader.
 a.bot.x=30;auto p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,0,0),"distant in-range caster did not return to human leader");
 a.bot.x=1;a.bot.spline.done=false;a.bot.spline.end={38,0,0};p=CombatSlice(&a,&a.boss,&a.boss);
 check(at(p,1,0)&&p.position.spell==179784,"obsolete outward formation retained");
 check(!p.holdDamage&&!p.emergency,"ordinary hold cancelled damage/casts");a.bot.spline.done=true;
 // Distant mobs must be brought back; the whole raid must not chase a pickup.
 a.boss.x=50;a.bot.x=1;p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,1,0),"caster chased a distant engaged mob");
 a.bot.ranged=false;p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,1,0),"melee chased a distant engaged mob");
 a.bot.x=30;p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,0,0),"stranded melee did not regroup");
 // Tank holder actually pulls the distant pack toward the bounded leader area.
 a.bot.tank=true;a.bot.x=30;a.boss.victim=&a.bot;p=CombatSlice(&a,&a.boss,&a.boss);
 check(p.position.active&&std::hypot(p.position.destination.x,p.position.destination.y)<=6.01f,"tank holder did not bring pack back");
 a.bot.x=5;p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,5,0),"nearby holder moved away for a decorative ring");
 a.boss.entry=12468;a.boss.x=a.bot.x=1;p=CombatSlice(&a,&a.boss,&a.boss);
 check(p.position.active&&std::hypot(p.position.destination.x,p.position.destination.y)-a.boss.GetCombatReach()-a.bot.GetCombatReach()>17,"Hatcher melee stop would retain pulse on leader");
 a.bot.x=22;a.boss.x=16;p=CombatSlice(&a,&a.boss,&a.boss);
 check(p.position.active&&p.position.destination.x>a.bot.x,"Hatcher still on leader did not get bounded extra pullback");
 a.boss.x=a.bot.x=20;p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,20,0),"separated Hatcher holder needlessly moved");
 a.boss.entry=12458;a.boss.x=50;a.bot.x=5;
 a.boss.victim=&a.tank;p=CombatSlice(&a,&a.boss,&a.boss);check(!p.position.active,"spare tank pickup blocked by leader hold");
 a.bot.tank=false;a.bot.ranged=false;a.boss.x=6;a.bot.x=1;p=CombatSlice(&a,&a.boss,&a.boss);
 check(p.position.active&&a.boss.GetDistance(p.position.destination.x,p.position.destination.y,p.position.destination.z)<=2.01f,"local melee contact missing");
 a.bot.x=5;p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,5,0),"local melee contact displaced");
 // Hunters can shoot from a legal leader-area station without forced max range.
 a.bot.ranged=true;a.bot.cls=CLASS_HUNTER;a.hunterMin=8;a.spellMax=35;a.boss.x=20;a.bot.x=1;
 p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,1,0),"safe hunter forced outward");
 a.boss.x=5;p=CombatSlice(&a,&a.boss,&a.boss);check(p.position.active,"hunter dead zone ignored");
 float d=a.boss.GetDistance(p.position.destination.x,p.position.destination.y,p.position.destination.z);
 check(d>=8&&std::hypot(p.position.destination.x,p.position.destination.y)<=6.01f,"hunter minimum-range correction abandoned leader");
 a.hunterSpell=false;p=CombatSlice(&a,&a.boss,&a.boss);check(!p.position.active&&!p.holdDamage,"unknown native range fabricated");a.hunterSpell=true;
 // Every engaged Hatcher matters independently of current damage/heal anchor.
 a.bot.cls=CLASS_MAGE;a.spellMax=40;a.hatcher.engaged=true;a.hatcher.x=15;
 p=CombatSlice(&a,&a.boss,&a.boss);check(p.position.active,"mixed-pack Hatcher pulse ignored");
 d=a.hatcher.GetDistance(p.position.destination.x,p.position.destination.y,p.position.destination.z);
 check(d>=17&&std::hypot(p.position.destination.x,p.position.destination.y)<4,"Hatcher correction needlessly abandoned leader area");
 check(p.emergency,"inside Growing Flames did not request escape");
 a.hatcher.x=0;p=CombatSlice(&a,&a.boss,&a.boss);check(p.position.active,"Hatcher on leader wrongly forced stack");
 check(std::hypot(p.position.destination.x,p.position.destination.y)>=17&&std::hypot(p.position.destination.x,p.position.destination.y)<18,"Hatcher exception not nearest bounded safe station");
 circleRoute=false;p=CombatSlice(&a,&a.boss,&a.boss);check(!p.emergency,"unsafe Hatcher route admitted");circleRoute=true;
 a.hatcher.engaged=false;p=CombatSlice(&a,&a.boss,&a.boss);check(at(p,1,0),"unpulled Hatcher provoked escape");
 // Healers keep real reach to a temporarily distant tank while staying as
 // close to leader as a safe cast permits; no forced40yd ring around the tank.
 a.bot.heal=true;a.tank.x=50;p=CombatSlice(&a,&a.boss,&a.boss);
 check(p.position.active&&a.tank.GetDistance(p.position.destination.x,p.position.destination.y,p.position.destination.z)<=40,"healer station lost tank cast range");
 check(std::hypot(p.position.destination.x,p.position.destination.y)<=10.01f,"healer needlessly spread beyond nearest cast station");
 a.bot.heal=false;a.tank.x=5;
 // Exact native path/ground rejection remains authoritative; no safe path
 // does not grant permission for a fresh-pack chase or suppress class actions.
 a.ground={{{0,0,0},3}};p=CombatSlice(&a,&a.boss,&a.boss);
 check(p.position.active&&encounter::OutsideCircles(p.position.destination,a.ground),"Flamestrike leader station retained");a.ground.clear();
 a.pathAllowed=false;p=CombatSlice(&a,&a.boss,&a.boss);check(!p.position.active&&!p.holdDamage,"rejected path forced through fresh pack");a.pathAllowed=true;
 // Bosses, frontal dragonkin and other maps retain previous geometry. Losing
 // the human leader must hold class actions in place instead of scattering.
 a.bot.x=a.neighbor.x=10;a.boss.x=0;
 for(unsigned entry:{12017u,12467u,12461u,12460u}){a.boss.entry=entry;p=CombatSlice(&a,&a.boss,&a.boss);check(p.position.active&&p.position.spell!=179784,"boss/front geometry relaxed");}
 a.boss.entry=12458;a.room=false;p=CombatSlice(&a,&a.boss,&a.boss);check(p.position.active&&p.position.spell!=179784,"room gate bypassed");
 a.room=true;a.bot.map=533;p=CombatSlice(&a,&a.boss,&a.boss);check(p.position.active&&p.position.spell!=179784,"non-BWL formation changed");
 a.bot.map=469;a.leader.real=false;p=CombatSlice(&a,&a.boss,&a.boss);
 check(at(p,a.bot.x,a.bot.y)&&p.position.source.IsEmpty()&&!p.holdDamage,"missing leader resumed outward formation");
 check(!BlackwingSuppressionChaseAllowed(&a,&a.boss),"missing leader allowed outward chase");
 a.hatcher.engaged=true;a.hatcher.x=a.bot.x;p=CombatSlice(&a,&a.boss,&a.boss);
 check(p.position.active&&p.emergency&&p.position.source.IsEmpty()&&a.hatcher.GetDistance(p.position.destination.x,p.position.destination.y,p.position.destination.z)>=17,"leader loss suppressed Growing Flames escape");
 circleRoute=false;p=CombatSlice(&a,&a.boss,&a.boss);check(!p.emergency,"leader-loss escape crossed unsafe Hatcher route");circleRoute=true;a.hatcher.engaged=false;
 a.leader.real=true;a.bot.native.instance.state=IN_PROGRESS;p=CombatSlice(&a,&a.boss,&a.boss);check(p.position.spell!=179784,"trash policy displaced active Broodlord");
 a.bot.native.instance.state=DONE;p=CombatSlice(&a,&a.boss,&a.boss);check(p.position.spell!=179784,"trash policy survived Broodlord completion");a.bot.native.instance.state=0;
 // Actual native-chase admission cannot override leader geometry. Only tanks
 // retrieve engaged mobs; explicit fresh-target Attack/Pull retains liveness.
 a.bot.x=1;a.boss.x=30;a.bot.ranged=false;
 check(!BlackwingSuppressionChaseAllowed(&a,&a.boss),"melee chase escaped leader area");
 a.boss.x=6;check(BlackwingSuppressionChaseAllowed(&a,&a.boss),"local melee native attack prevented");
 a.bot.ranged=true;check(!BlackwingSuppressionChaseAllowed(&a,&a.boss),"ranged chase overrode safe station");
 a.bot.tank=true;a.boss.x=40;check(BlackwingSuppressionChaseAllowed(&a,&a.boss),"tank pickup prevented");
 a.boss.engaged=false;check(!BlackwingSuppressionChaseAllowed(&a,&a.boss),"tank autonomously pulled fresh pack");
 WaitForAttackStrategy::target=&a.boss;check(BlackwingSuppressionChaseAllowed(&a,&a.boss),"accepted explicit Attack tank pickup prevented");WaitForAttackStrategy::target=nullptr;
 PullStrategy pull;PullStrategy::active=&pull;pull.target=&a.boss;pull.allowed=pull.started=true;a.bot.tank=false;
 check(BlackwingSuppressionChaseAllowed(&a,&a.boss),"explicit Pull prevented");clockNow=115;
 check(!BlackwingSuppressionChaseAllowed(&a,&a.boss),"expired Pull allowed chase");clockNow=100;
 a.leader.authorized=false;check(!BlackwingSuppressionChaseAllowed(&a,&a.boss),"unauthorized Pull allowed chase");a.leader.authorized=true;
 pull.allowed=false;check(!BlackwingSuppressionChaseAllowed(&a,&a.boss),"autonomous Pull bypassed leader anchor");
 PullStrategy::active=nullptr;a.boss.entry=12017;check(BlackwingSuppressionChaseAllowed(&a,&a.boss),"Broodlord native chase changed");
 std::cout<<"PASS actual leader-anchored suppression stations: tank pullback, melee regroup, hunter/Hatcher/healer ranges, path rejection and boss exclusions\n";
}
'''
code=code.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix())
code=code.replace('__POLICY__',(root/'playerbot/strategy/ClassicRaidPolicy.h').as_posix())
code=code.replace('__ARRIVAL__',arrival).replace('__HELPERS__',helpers).replace('__TAIL__',tail).replace('__CHASE__',chase)
with tempfile.TemporaryDirectory(prefix='suppression-stations-') as folder:
    p=Path(folder);(p/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        compiled=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
        if compiled.returncode:raise RuntimeError(compiled.stdout+compiled.stderr)
        result=subprocess.run([str(p/'test.exe')],cwd=p,capture_output=True,text=True)
        if args.baseline_ref:
            assert result.returncode==42 and 'UNNECESSARY_SPREAD' in result.stderr,(result.returncode,result.stdout,result.stderr)
            print(f'REPRODUCED {era}: {args.baseline_ref} forces safe suppression caster outward')
        else:
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            print(era+': '+result.stdout.strip())
