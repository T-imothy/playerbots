"""Execute native attacker admission and discovery for an unmarked AV captain."""
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/values/AttackersValue.cpp').read_text()
helper=block(source,'bool AttackersValue::EngagedAlteracNpc(')
if '--before' in sys.argv:
    source=subprocess.check_output(['git','-C',str(root),'show','HEAD:playerbot/strategy/values/AttackersValue.cpp'],text=True)
methods='\n'.join(block(source,m) for m in ('bool AttackersValue::InCombat(', 'bool AttackersValue::IsValid(', 'std::list<ObjectGuid> AttackersValue::Calculate('))
code=r'''
#include <cassert>
#include <map>
#include <list>
#include <set>
#include <vector>
#include <string>
#include <cmath>
#include <iostream>
using uint32=unsigned;constexpr unsigned ALL_ACTIVITY=1,UNIT_FIELD_FLAGS=0,UNIT_FLAG_CLIENT_CONTROL_LOST=1;
enum{BATTLEGROUND_AV=1,BATTLEGROUND_WS=2,STATUS_IN_PROGRESS=1};namespace BotState{enum{BOT_STATE_COMBAT};}
struct ObjectGuid{unsigned id=0;bool pet=false;ObjectGuid(unsigned n=0):id(n){}operator unsigned()const{return id;}bool IsPet()const{return pet;}bool operator<(const ObjectGuid&o)const{return id<o.id;}};
struct Player;struct PlayerbotAI;struct Group;struct BattleGround;
struct Threat{std::map<Player*,float>values;float getThreat(Player*p){return values[p];}};
struct Unit{virtual ~Unit()=default;ObjectGuid guid;unsigned map=30,instance=100,phase=1;bool world=true,alive=true,combat=true,charm=false,friendly=false,possible=true,cc=false,hardCC=false;
 float x=0;Threat threat;Unit*victim=nullptr;virtual bool IsCreature(){return true;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}
 ObjectGuid GetObjectGuid(){return guid;}Unit*GetVictim(){return victim;}Threat&getThreatManager(){return threat;}unsigned GetMapId(){return map;}};
struct CombatManager{bool evading=false;bool IsInEvadeMode()const{return evading;}};
struct Creature:Unit{CombatManager manager;const CombatManager&GetCombatManager()const{return manager;}};
struct Duel{Player*opponent=nullptr;};
struct Player:Unit{unsigned team=1;bool transfer=false,flying=false,lost=false,tank=false;Duel*duel=nullptr;Player*pet=nullptr;PlayerbotAI*ai=nullptr;BattleGround*bg=nullptr;Group*group=nullptr;
 bool IsCreature()override{return false;}bool IsBeingTeleported(){return transfer;}bool InBattleGround(){return bg!=nullptr;}BattleGround*GetBattleGround(){return bg;}unsigned GetBGTeam(){return team;}
 Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}Player*GetPet(){return pet;}bool IsFlying(){return flying;}bool HasFlag(unsigned,unsigned){return lost;}
 bool IsInMap(Unit*u){return world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 bool IsWithinDistInMap(Unit*u,float r){return IsInMap(u)&&std::fabs(x-u->x)<=r;}bool IsWithinDist(Player*p,float r,bool){return std::fabs(x-p->x)<=r;}};
using Pet=Player;
struct Slot{ObjectGuid guid;};struct Group{std::vector<Slot>slots;auto&GetMemberSlots(){return slots;}bool IsMember(ObjectGuid g){for(auto&s:slots)if(s.guid==g)return true;return false;}};
struct BattleGround{unsigned type=BATTLEGROUND_AV,status=STATUS_IN_PROGRESS;Group*raid=nullptr;unsigned GetStatus(){return status;}Group*GetBgRaid(unsigned team){return team==1?raid:nullptr;}};
unsigned ActualBattlegroundType(Player*p){return p->bg?p->bg->type:0;}
struct ObjectMgr{std::map<unsigned,Player*>players;Player*GetPlayer(ObjectGuid g){return players.count(g)?players[g]:nullptr;}}sObjectMgr;
struct Facade{unsigned GetAreaId(Unit*){return 0;}bool IsFriendlyTo(Player*,Player*p){return !p->friendly;}}sServerFacade;
struct Config{float sightDistance=50;bool IsInPvpProhibitedZone(unsigned){return false;}}sPlayerbotAIConfig;
struct WorldPosition{WorldPosition(Player*){}float currentHeight(){return 0;}};
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*p){return u&&u->possible&&u->world&&u->alive&&p->IsInMap(u)&&!u->friendly;}};
struct PossibleAttackTargetsValue{static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
struct EnemyPlayerValue{static float GetMaxAttackDistance(Player*){return 50;}};struct EnemyPlayersValue{static bool IsReachable(Player*,Player*){return true;}};
struct PlayerbotAI{Player*bot;bool activity=true,focus=false,pvp=true,owned=false;Unit*rti=nullptr;ObjectGuid order;
 bool AllowActivity(unsigned){return activity;}bool IsTank(Player*p){return p->tank;}bool HasStrategy(const char*n,int){return std::string(n)=="focus rti targets"?focus:pvp;}
 bool HasActivePlayerMaster(){return owned;}Unit*GetUnit(ObjectGuid g){return rti&&rti->guid==g?rti:nullptr;}ObjectGuid Value(const char*){return order;}};
#define AI_VALUE(type,key) (ai->rti?ai->rti->GetObjectGuid():ObjectGuid())
#define PAI_VALUE(type,key) player->GetPlayerbotAI()->Value(key)
struct AttackersValue{PlayerbotAI*ai;Player*bot;std::string qualifier;std::vector<Unit*>nearby;Player*master=nullptr;
 Player*GetMaster(){return master;}std::list<ObjectGuid>Calculate();static bool InCombat(Unit*,Player*,bool=true);static bool EngagedAlteracNpc(Unit*,Player*);
 static bool IsValid(Unit*,Player*,Player*=nullptr,bool=true,bool=true);static bool IgnoreTarget(Unit*,Player*){return false;}
 void AddTargetsOf(Player*p,std::set<Unit*>&out,std::set<ObjectGuid>&,bool one){for(auto*u:nearby)if(IsValid(u,p,bot)){out.insert(u);if(one)break;}}
 void AddTargetsOf(Group*,std::set<Unit*>&,std::set<ObjectGuid>&,bool){} };
__HELPER__
__METHODS__
int main(){Player bot,human;bot.guid=1;human.guid=2;PlayerbotAI ai{&bot};bot.ai=&ai;Group raid;raid.slots={{1},{2}};BattleGround av;av.raid=&raid;
 bot.bg=human.bg=&av;bot.group=human.group=&raid;sObjectMgr.players={{1,&bot},{2,&human}};Creature captain;captain.guid=10;captain.victim=&human;captain.threat.values[&human]=1;
 AttackersValue attackers{&ai,&bot};attackers.nearby={&captain};
 assert(AttackersValue::IsValid(&captain,&bot,&bot));assert(attackers.Calculate()==std::list<ObjectGuid>{10}); // no marker, leadership or controller
 ai.focus=true;assert(attackers.Calculate()==std::list<ObjectGuid>{10}); // marker-only mode still permits this team's real AV NPC combat
 Creature marked;marked.guid=11;ai.rti=&marked;assert(attackers.Calculate()==std::list<ObjectGuid>{11});ai.rti=nullptr;
 for(unsigned f=0;f<15;++f){captain.world=captain.alive=captain.combat=captain.possible=true;captain.cc=captain.hardCC=captain.friendly=false;
 captain.instance=100;human.instance=100;human.x=0;human.world=human.alive=human.combat=true;human.transfer=human.charm=false;human.team=1;human.bg=&av;
 captain.victim=&human;captain.threat.values[&human]=1;av.status=STATUS_IN_PROGRESS;av.type=BATTLEGROUND_AV;
 if(f==0)captain.world=false;if(f==1)captain.alive=false;if(f==2)captain.combat=false;if(f==3)captain.possible=false;
 if(f==4)captain.cc=true;if(f==5)captain.hardCC=true;if(f==6)captain.friendly=true;if(f==7)captain.instance=200;
 if(f==8)human.instance=200;if(f==9)human.x=80;if(f==10)human.transfer=true;if(f==11)human.team=2;
 if(f==12)human.bg=nullptr;if(f==13)av.status=0;if(f==14)av.type=BATTLEGROUND_WS;
 assert(!AttackersValue::EngagedAlteracNpc(&captain,&bot));}
 av.type=BATTLEGROUND_AV;av.status=STATUS_IN_PROGRESS;captain.world=captain.alive=captain.combat=captain.possible=true;
 captain.instance=human.instance=100;human.x=0;human.bg=&av;human.team=1;human.transfer=false;
 captain.victim=nullptr;captain.threat.values.clear();assert(!AttackersValue::EngagedAlteracNpc(&captain,&bot)); // mere proximity/selection cannot pull
 ai.activity=false;assert(attackers.Calculate().empty());ai.activity=true;bot.lost=true;assert(attackers.Calculate().empty());bot.lost=false;
 captain.victim=&bot;assert(AttackersValue::IsValid(&captain,&bot,&bot)); // own native defense remains
 Player enemy;enemy.guid=20;ai.pvp=false;assert(!AttackersValue::IsValid(&enemy,&bot,&bot)); // PvP policy unchanged
 bot.bg=nullptr;ai.focus=true;assert(attackers.Calculate().empty());
 std::cout<<"PASS unmarked same-team AV NPC engagement, skull precedence, instance/range/CC/ended guards, unpulled safety and unchanged PvP\n";
}
'''.replace('Player*=','Player* =').replace('__HELPER__',helper).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='alterac-engagement-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
