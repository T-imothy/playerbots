"""Execute the current Classic AV planner against native-style event state."""
from pathlib import Path
import re,subprocess,tempfile
from native_bg_constants import variants
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
src=(root/'playerbot/strategy/actions/ClassicBattlegroundActions.cpp').read_text()
body=block(src,'bool BGTactics::SelectClassicAlteracObjective(')
helper=block(src,'    policy::Node AvState(')
adapter=src.split('// Keep expansion enum differences at this native API boundary.',1)[1].split('    policy::Node AvState',1)[0]
locations=re.findall(r'\{(BG_AV_NODES_\w+), "(AV_\w+)"\}',body)
code=r'''
#include "playerbot/strategy/values/ClassicBattlegroundPolicy.h"
#include <string>
#include <map>
#include <cassert>
#include <iostream>
namespace policy=ai::ClassicBattlegroundPolicy;
__CONSTANTS__
__ADAPTER__
enum {STATUS_IN_PROGRESS=3,ALLIANCE=469,HORDE=67};
struct Position {float x=0;};
struct WorldLocation{unsigned mapid=30;float coord_x=0;WorldLocation()=default;WorldLocation(unsigned m,Position p):mapid(m),coord_x(p.x){}};
struct GameObject {unsigned id;unsigned lock=1479;GameObject*GetGOInfo(){return this;}unsigned GetLockId(){return lock;} unsigned GetMapId(){return 30;}Position GetPosition(){return {float(id)};}};
struct Creature:GameObject {bool alive=true;bool IsAlive(){return alive;}};
struct Map {std::map<unsigned,GameObject>objects;Creature boss;GameObject*GetGameObject(unsigned id){auto it=objects.find(id);return it==objects.end()?nullptr:&it->second;}Creature*GetCreature(unsigned id){boss.id=id;return &boss;}};
struct BattleGround{unsigned status=STATUS_IN_PROGRESS;std::map<unsigned,unsigned>events;unsigned GetStatus(){return status;}bool IsActiveEvent(unsigned node,unsigned state){auto i=events.find(node);return i!=events.end()&&i->second==state;}unsigned GetSingleGameObjectGuid(unsigned n,unsigned){return n;}unsigned GetSingleCreatureGuid(unsigned n,unsigned){return n;}};
struct Player {BattleGround bg;Map map;unsigned team=ALLIANCE,slot=0,count=40;BattleGround*GetBattleGround(){return &bg;}unsigned GetTeam(){return team;}Map*GetMap(){return &map;}};
unsigned BattlegroundTeamSlot(Player*b,unsigned&count){count=b->count;return b->slot;}
struct Manager {std::map<std::string,unsigned>names;bool GetNamedLocation(std::string s,WorldLocation&l){auto i=names.find(s);if(i==names.end())return false;l.coord_x=float(i->second);return true;}}sRandomPlayerbotMgr;
struct BGTactics{Player*bot;bool SelectClassicAlteracObjective(WorldLocation&);};
__HELPER__
__BODY__
int main(){
 __LOCATIONS__
 for(unsigned team:{ALLIANCE,HORDE}){
  Player bot;bot.team=team;BGTactics planner{&bot};WorldLocation goal;
  const bool a=team==ALLIANCE;
  unsigned towers[4]={a?BG_AV_NODES_ICEBLOOD_TOWER:BG_AV_NODES_STONEHEART_BUNKER,a?BG_AV_NODES_TOWER_POINT:BG_AV_NODES_ICEWING_BUNKER,a?BG_AV_NODES_FROSTWOLF_ETOWER:BG_AV_NODES_DUNBALDAR_SOUTH,a?BG_AV_NODES_FROSTWOLF_WTOWER:BG_AV_NODES_DUNBALDAR_NORTH};
  unsigned graves[3]={a?BG_AV_NODES_ICEBLOOD_GRAVE:BG_AV_NODES_STONEHEART_GRAVE,a?BG_AV_NODES_FROSTWOLF_GRAVE:BG_AV_NODES_STORMPIKE_GRAVE,a?BG_AV_NODES_FROSTWOLF_HUT:BG_AV_NODES_FIRSTAID_STATION};
  const auto theirs=a?BG_AV_NODE_STATUS_HORDE_OCCUPIED:BG_AV_NODE_STATUS_ALLY_OCCUPIED;
  const auto ours=a?BG_AV_NODE_STATUS_ALLY_OCCUPIED:BG_AV_NODE_STATUS_HORDE_OCCUPIED;
  const auto assault=a?BG_AV_NODE_STATUS_ALLY_CONTESTED:BG_AV_NODE_STATUS_HORDE_CONTESTED;
  for(auto t:towers)bot.bg.events[t]=theirs;for(auto g:graves)bot.bg.events[g]=theirs;
  for(bot.slot=0;bot.slot<6;++bot.slot){assert(planner.SelectClassicAlteracObjective(goal));assert(goal.coord_x==towers[0]);}
  // A decorative event GO on the roof must never replace the named flag.
  bot.slot=0;bot.map.objects[towers[0]]={999,0};
  assert(planner.SelectClassicAlteracObjective(goal)&&goal.coord_x==towers[0]);
  bot.map.objects[towers[0]]={777,1479};
  assert(planner.SelectClassicAlteracObjective(goal)&&goal.coord_x==777);
  bot.map.objects.clear();
  bot.slot=6;assert(planner.SelectClassicAlteracObjective(goal)&&goal.coord_x==graves[0]);
  bot.bg.events[graves[0]]=assault;
  assert(planner.SelectClassicAlteracObjective(goal)&&goal.coord_x==graves[0]);
  bot.slot=8;assert(planner.SelectClassicAlteracObjective(goal)&&goal.coord_x==graves[1]);
  bot.bg.events[towers[0]]=assault;bot.slot=0;assert(planner.SelectClassicAlteracObjective(goal)&&goal.coord_x==towers[0]);
  bot.slot=2;assert(planner.SelectClassicAlteracObjective(goal)&&goal.coord_x==towers[1]);
  for(auto g:graves)bot.bg.events[g]=ours;
  for(auto t:towers)bot.bg.events[t]=assault;
  bot.slot=12;assert(planner.SelectClassicAlteracObjective(goal));assert(goal.coord_x!=BG_AV_BOSS_A&&goal.coord_x!=BG_AV_BOSS_H);
  for(auto t:towers)bot.bg.events[t]=ours;
  assert(planner.SelectClassicAlteracObjective(goal)&&goal.coord_x==(a?BG_AV_BOSS_H:BG_AV_BOSS_A));
  bot.bg.status=0;assert(!planner.SelectClassicAlteracObjective(goal));
 }
 std::cout<<"PASS shared AV mirrored squads, graveyard chain, assault guards, native tower completion, final general objective\n";
}
'''.replace('__ADAPTER__',adapter).replace('__HELPER__',helper).replace('__BODY__',body).replace('__LOCATIONS__','\n'.join(f'sRandomPlayerbotMgr.names["{s}"]={n};' for n,s in locations))
for era,constants in variants('AV'):
 with tempfile.TemporaryDirectory(prefix='shared-av-planner-') as tmp:
  p=Path(tmp);(p/'test.cpp').write_text(code.replace('__CONSTANTS__',constants))
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'/I'+str(root),'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
