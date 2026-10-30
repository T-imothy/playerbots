"""Execute both production AV selectors and their bounded refresh in all cores."""
from pathlib import Path
import re, subprocess, tempfile, sys
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
av = (root/'playerbot/strategy/actions/BattleGroundTacticsAV.cpp').read_text()
tactics = (root/'playerbot/strategy/actions/BattleGroundTactics.cpp').read_text()
helpers = block(av, 'namespace\n{')
arrays = av[av.index('static std::tuple'):av.index('bool BGTactics::SelectAvObjectiveAlliance')]
methods = av[av.index('bool BGTactics::SelectAvObjectiveAlliance'):av.index('std::vector<uint32> const FlagEntries')]
avcase = block(block(tactics,'bool BGTactics::selectObjective('), '    case BATTLEGROUND_AV:')
refresh = block(tactics,'bool BGTactics::resetObjective(')
refresh = refresh[:refresh.index('    // sometimes change role')]+'return false;\n}'
names = sorted(set(re.findall(r'\b(?:BG_AV_\w+|TEAM_INDEX_\w+)\b',arrays+methods)))
constants = 'enum {'+','.join(n+'='+str(i+100) for i,n in enumerate(names))+'};'
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <tuple>
#include <type_traits>
#include <vector>
#include <cstdlib>
#undef assert
#define assert(value) do { if (!(value)) { std::cerr<<"assertion line "<<__LINE__<<"\n";std::exit(88); } } while(false)
using uint32=uint32_t;using BattleGroundTypeId=unsigned;
enum{ALLIANCE,HORDE,BATTLEGROUND_AV=3,BATTLEGROUND_WS=2,STATUS_IN_PROGRESS=1,DEAD=1,MINUTE=60,IN_MILLISECONDS=1000,VISIBILITY_DISTANCE_LARGE=100,VISIBILITY_DISTANCE_GIGANTIC=400};
__CONSTANTS__
struct Position{float x=0,y=0,z=0,o=0;Position()=default;Position(float x,float y,float z,float o=0):x(x),y(y),z(z),o(o){}};
struct WorldLocation{unsigned mapid=30;float coord_x=0,coord_y=0,coord_z=0,orientation=0;WorldLocation()=default;WorldLocation(unsigned m,Position p):mapid(m),coord_x(p.x),coord_y(p.y),coord_z(p.z),orientation(p.o){}};
namespace ai{struct PositionEntry{float x=0,y=0,z=0;unsigned mapId=0;bool set=false;bool isSet(){return set;}void Reset(){set=false;}void Set(float a,float b,float c,unsigned m){x=a;y=b;z=c;mapId=m;set=true;}};using PositionMap=std::map<std::string,PositionEntry>;}
using namespace ai;
struct Creature:Position{unsigned health=100;bool combat=false;unsigned GetMapId(){return 30;}Position GetPosition(){return *this;}unsigned GetHealth(){return health;}int GetDeathState(){return health?0:DEAD;}};
struct Map{std::map<unsigned,Creature*>creatures;Creature*GetCreature(unsigned id){return creatures[id];}};
struct BattleGround{std::set<std::pair<unsigned,unsigned>>events;unsigned status=STATUS_IN_PROGRESS;bool IsActiveEvent(unsigned a,unsigned b){return events.count({a,b});}unsigned GetSingleCreatureGuid(unsigned a,unsigned){return a;}unsigned GetStartTime(){return 1;}unsigned GetStatus(){return status;}};
struct Player:Position{BattleGround*bg=nullptr;Map map;unsigned team=ALLIANCE;bool alive=true,world=true,transfer=false,cast=false;BattleGround*GetBattleGround(){return bg;}Map*GetMap(){return &map;}bool IsWithinDist(Creature*,unsigned){return false;}unsigned GetTeam(){return team;}bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool IsNonMeleeSpellCasted(bool,bool,bool){return cast;}};
struct WorldPosition{WorldPosition(Player*){}WorldPosition(WorldLocation const&){}bool IsWithinDist(WorldPosition,unsigned){return false;}};
struct Facade{bool IsInCombat(Creature*c){return c->combat;}}sServerFacade;
struct Manager{std::map<std::string,WorldLocation>locations;bool GetNamedLocation(std::string n,WorldLocation&out){auto i=locations.find(n);if(i==locations.end())return false;out=i->second;return true;}}sRandomPlayerbotMgr;
template<class T>struct Value{std::remove_reference_t<T>data{};T Get(){return data;}};
struct Context{Value<uint32>role;Value<PositionMap&>position;template<class T>Value<T>*GetValue(const char*){if constexpr(std::is_same_v<T,uint32>)return &role;else return &position;}};
#define AI_VALUE(type,name) context->GetValue<type>(name)->Get()
unsigned randomCounter=0;unsigned urand(unsigned a,unsigned b){return a+(++randomCounter%(b-a+1));}
namespace WorldTimer{unsigned now=1;unsigned getMSTime(){return now;}unsigned getMSTimeDiff(unsigned a,unsigned b){return b-a;}}
unsigned ActualBattlegroundType(Player*){return BATTLEGROUND_AV;}bool SupportsBattlegroundObjectiveRecovery(Player*){return true;}
struct BGTactics{Player*bot;Context*context;unsigned defenders=0,battlegroundObjectiveCheck=0;bool SelectAvObjectiveAlliance(WorldLocation&);bool SelectAvObjectiveHorde(WorldLocation&);bool resetObjective();bool refreshWarsongObjective(){return false;}unsigned getDefendersCount(Position,float,bool){return defenders;}
 bool selectObjective(bool){PositionEntry pos=AI_VALUE(PositionMap&,"position")["bg objective"];auto&posMap=AI_VALUE(PositionMap&,"position");switch(BATTLEGROUND_AV){__AVCASE__ default:break;}return false;}};
__HELPERS__
__ARRAYS__
__METHODS__
__REFRESH__
int main(){
 for(unsigned team:{ALLIANCE,HORDE}){
  sRandomPlayerbotMgr.locations.clear();
  BattleGround bg;Player bot;bot.bg=&bg;bot.team=team;Context context;context.role.data=8;BGTactics action{&bot,&context};WorldTimer::now=1;
  auto&position=context.position.data["bg objective"];
  auto&attacks=team==ALLIANCE?AV_AllianceAttackObjectives:AV_HordeAttackObjectives;
  auto&defenses=team==ALLIANCE?AV_AllianceDefendObjectives:AV_HordeDefendObjectives;
  auto captainId=team==ALLIANCE?BG_AV_CAPTAIN_H:BG_AV_CAPTAIN_A;auto captainDead=team==ALLIANCE?BG_AV_NODE_CAPTAIN_DEAD_H:BG_AV_NODE_CAPTAIN_DEAD_A;
  unsigned i=0;for(auto const&[node,state,name]:attacks){bg.events.insert({node,state});if(!sRandomPlayerbotMgr.locations.count(name))sRandomPlayerbotMgr.locations[name]={30,Position{float(++i)*200,20,30}};}
  bg.events.insert({captainDead,0});
  assert(action.resetObjective());PositionEntry first=position;
  for(int n=0;n<80;++n){WorldTimer::now+=10001;assert(!action.resetObjective());assert(position.x==first.x&&position.y==first.y&&position.z==first.z);}
  // Capturing/changing the selected node makes a new objective necessary.
  for(auto const&[node,state,name]:attacks)if(MatchesAvObjective(first,sRandomPlayerbotMgr.locations[name]))bg.events.erase({node,state});
  WorldTimer::now+=10001;assert(action.resetObjective());assert(position.x!=first.x);
  // Both of the paired towers remain assigned despite repeated split rolls.
  auto paired=team==ALLIANCE?std::string("AV_EAST_FROSTWOLF_TOWER"):std::string("AV_DUNBALDAR_SOUTH");
  for(auto const&[node,state,name]:attacks)bg.events.insert({node,state});
  auto tower=sRandomPlayerbotMgr.locations.at(paired);position.Set(tower.coord_x,tower.coord_y,tower.coord_z,tower.mapid);
  for(int n=0;n<80;++n){WorldTimer::now+=10001;assert(!action.resetObjective());assert(MatchesAvObjective(position,tower));}
  // Defenders retain a still-contested assignment; no global cross-bot state.
  context.role.data=0;for(auto const&[node,state,name]:defenses){bg.events.insert({node,state});sRandomPlayerbotMgr.locations[name]={30,Position{float(++i)*200,70,30}};}
  WorldTimer::now+=10001;assert(action.resetObjective());first=position;
  for(int n=0;n<40;++n){WorldTimer::now+=10001;assert(!action.resetObjective());assert(position.x==first.x&&position.y==70);}
  // Captain readiness must replace a waiting position, even while it is set.
  Creature captain;captain.x=900;captain.y=80;captain.z=40;bot.map.creatures[captainId]=&captain;bg.events.erase({captainDead,0});context.role.data=8;
  auto waiting=team==ALLIANCE?"AV_ICEBLOOD_GARRISON_WAITING_ALLIANCE":"AV_STONEHEART_OUTPOST_WAITING_HORDE";sRandomPlayerbotMgr.locations[waiting]={30,Position{800,80,40}};
  WorldTimer::now+=10001;assert(action.resetObjective());assert(position.x==800);
  action.defenders=5;WorldTimer::now+=10001;assert(action.resetObjective());assert(position.x==900);
  // Endboss priority and death/loading/cast safety are still respected.
  bg.events.clear();Creature boss;boss.x=1200;bot.map.creatures[team==ALLIANCE?BG_AV_BOSS_H:BG_AV_BOSS_A]=&boss;
  bot.cast=true;WorldTimer::now+=10001;assert(!action.resetObjective()&&position.x==900);bot.cast=false;
  bot.transfer=true;assert(!action.resetObjective());bot.transfer=false;bot.alive=false;assert(!action.resetObjective());bot.alive=true;
  assert(action.resetObjective());assert(position.x==1200);
 }
 std::cout<<"PASS AV assignment persistence, ownership changes, paired towers, defense, captain readiness and boss transition\n";
}
'''.replace('__CONSTANTS__',constants).replace('__AVCASE__',avcase).replace('__HELPERS__',helpers).replace('__ARRAYS__',arrays).replace('__METHODS__',methods).replace('__REFRESH__',refresh)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='av-objective-') as td:
  p=Path(td);(p/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(era+'\n'+r.stdout+r.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
if '--prove-regressions' in sys.argv:
 variants={
  'periodic random assignment':code.replace(block(av,'    WorldLocation ChooseAvObjective('), 'WorldLocation ChooseAvObjective(const std::vector<WorldLocation>& locations, ai::PositionEntry){return locations[urand(0,locations.size()-1)];}'),
  'refresh discards previous assignment':code.replace('PositionEntry previous = objective;', 'PositionEntry previous = objective; objective.Reset();'),
 }
 for label,variant in variants.items():
  with tempfile.TemporaryDirectory(prefix='av-objective-before-') as td:
   p=Path(td);(p/'test.cpp').write_text(variant)
   r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_ZERO','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
   if r.returncode:raise RuntimeError(r.stdout+r.stderr)
   r=subprocess.run([str(p/'test.exe')],cwd=p,capture_output=True,text=True)
   assert r.returncode==88,(label,r.returncode,r.stdout,r.stderr)
   print('REPRODUCED:',label,r.stderr.strip(),flush=True)
