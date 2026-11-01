"""Execute the actual Classic banner action with controlled native interfaces."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
body=block((root/'playerbot/strategy/actions/ClassicBattlegroundActions.cpp').read_text(),'bool BGTactics::CheckClassicBanner(')
code=r'''
#include <cassert>
#include <list>
#include <map>
#include <cmath>
#include <iostream>
#include <string>
using ObjectGuid=unsigned;
enum { BATTLEGROUND_AB=3,BATTLEGROUND_AV=1,STATUS_IN_PROGRESS=3,ALLIANCE=469,HORDE=67,GO_STATE_READY=1,CURRENT_GENERIC_SPELL=1,SPELL_CAST_OK=0 };
enum {BG_AB_MAX_NODES=5,BG_AB_NODE_STATUS_NEUTRAL=0,BG_AB_NODE_STATUS_ALLY_CONTESTED=1,BG_AB_NODE_STATUS_HORDE_CONTESTED=2,BG_AB_NODE_STATUS_ALLY_OCCUPIED=3,BG_AB_NODE_STATUS_HORDE_OCCUPIED=4};
enum {BG_AV_MAX_NODES=15,BG_AV_NODE_STATUS_ALLY_CONTESTED=0,BG_AV_NODE_STATUS_ALLY_OCCUPIED=1,BG_AV_NODE_STATUS_HORDE_CONTESTED=2,BG_AV_NODE_STATUS_HORDE_OCCUPIED=3,BG_AV_NODE_STATUS_NEUTRAL_OCCUPIED=5};
const float INTERACTION_DISTANCE=5;
const unsigned SPELL_CAPTURE_BANNER=21651;
struct Player; using Unit=Player; struct Spell; struct GameObject;
struct SpellEntry{unsigned Id=21651;};
SpellEntry info; bool reject=false; unsigned casts=0;
struct Facade{bool IsHostileTo(Player*,Player*);const SpellEntry*LookupSpellInfo(unsigned id){return id==21651?&info:nullptr;}}sServerFacade;
struct Targets{unsigned guid=0;void setGOTarget(GameObject*);unsigned getGOTargetGuid(){return guid;}};
struct Spell {Targets m_targets;Spell(Player*,const SpellEntry*,bool){} unsigned SpellStart(Targets*){++casts;return reject?1:0;}};
struct Event{unsigned event1=0,event2=0;};
struct Map{Event event;std::map<unsigned,Player*>players;Map&GetMapDataContainer(){return *this;} Event&GetGameObjectEventIndex(unsigned){return event;}Player*GetPlayer(unsigned g){return players[g];}};
struct BattleGround {unsigned type=3,status=3;bool eventActive=true;Map map;std::map<unsigned,unsigned>players;unsigned GetStatus(){return status;}bool IsActiveEvent(unsigned,unsigned){return eventActive;}const auto&GetPlayers(){return players;}Map*GetBgMap(){return &map;}};
struct GameObject{unsigned guid=10,lock=1479;float x=3,y=0,z=0;bool spawned=true,inuse=false,locked=true;GameObject*GetGOInfo(){return this;}unsigned GetLockId(){return lock;}bool IsSpawned(){return spawned;}bool IsInUse(){return inuse;}unsigned GetGoState(){return GO_STATE_READY;}unsigned GetDbGuid(){return guid;}unsigned GetObjectGuid(){return guid;}const SpellEntry*GetSpellForLock(Player*){return locked?&info:nullptr;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
void Targets::setGOTarget(GameObject*g){guid=g->guid;}
struct Player{BattleGround*bg;float x=0;bool IsInMap(Player*p){return bg==p->bg;}bool IsWithinDistInMap(Player*p,float d){return std::abs(x-p->x)<=d;}bool IsWithinLOSInMap(Player*p){return p->los;}bool world=true,transfer=false,usable=true,cast=false,combat=false,mounted=false,form=false,los=true,staticLos=true,poleLos=false,alive=true;unsigned team=ALLIANCE;Spell*current=nullptr;BattleGround*GetBattleGround(){return bg;}Map*GetMap(){return &bg->map;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}bool CanUseBattleGroundObject(){return usable;}bool IsNonMeleeSpellCasted(bool,bool,bool){return cast;}unsigned GetTeam(){return team;}float GetDistance(GameObject*g){return g->x;}bool IsAlive(){return alive;}Spell*GetCurrentSpell(unsigned){return current;}bool IsWithinDistInMap(GameObject*g,float d){return std::abs(x-g->x)<=d;}bool IsInCombat(){return combat;}unsigned GetMapId(){return 529;}bool IsWithinLOSInMap(GameObject*,bool ignoreModel=false){return ignoreModel?staticLos:los;}bool IsWithinLOS(float,float,float z,bool ignoreModel){assert(z==2&&ignoreModel);return poleLos;}bool IsMounted(){return mounted;}bool IsInDisallowedMountForm(){return form;}};
bool Facade::IsHostileTo(Player*a,Player*b){return a->team!=b->team;}
unsigned ActualBattlegroundType(Player*p){return p->bg->type;}
struct AI{Player*bot;GameObject*go;std::map<unsigned,Player*>units;Player*GetUnit(unsigned g){return units[g];}unsigned stopped=0,waited=0;GameObject*GetGameObject(unsigned){return go;}void Unmount(){bot->mounted=false;}void RemoveShapeshift(){bot->form=false;}void StopMoving(){++stopped;}void WaitForSpellCast(Spell*){++waited;}};
struct BGTactics{Player*bot;AI*ai;std::list<unsigned>banners={10},attackers,possible;template<class T>T&GetValue(const char*n){return std::string(n)=="bg banners"?banners:std::string(n)=="attackers"?attackers:possible;}unsigned moves=0;bool route=true;bool MoveTo(unsigned,float,float,float){++moves;return route;}bool CheckClassicBanner();};
#define AI_VALUE(type,name) GetValue<type>(name)
__BODY__
int main(){
 BattleGround bg;Player bot{&bg},friendBot{&bg};GameObject go;go.locked=false;AI ai{&bot,&go};BGTactics action{&bot,&ai};
 bg.players={{1,0},{2,0}};bg.map.players={{1,&bot},{2,&friendBot}};
 go.x=15;assert(action.CheckClassicBanner()&&action.moves==1&&casts==0);
 go.x=3;bot.mounted=true;assert(action.CheckClassicBanner()&&casts==1&&!bot.mounted&&ai.waited==1);
 bot.los=false;assert(action.CheckClassicBanner());bot.los=true; // own banner model is not a static wall
 unsigned c=casts;
 go.lock=0;assert(!action.CheckClassicBanner());go.lock=1479;
 bot.transfer=true;assert(!action.CheckClassicBanner());bot.transfer=false;
 bot.usable=false;assert(!action.CheckClassicBanner());bot.usable=true;
 // Placed tower flags can fail bot LOS while the native player cast accepts.
 bot.staticLos=false;assert(action.CheckClassicBanner());
 reject=true;auto previousWait=ai.waited;assert(!action.CheckClassicBanner()&&ai.waited==previousWait);
 reject=false;bot.staticLos=true;c=casts;
 bot.cast=true;assert(!action.CheckClassicBanner());bot.cast=false;
 bg.eventActive=false;assert(!action.CheckClassicBanner());bg.eventActive=true;
 bg.map.event.event2=BG_AB_NODE_STATUS_ALLY_OCCUPIED;assert(!action.CheckClassicBanner());
 bg.map.event.event2=BG_AB_NODE_STATUS_ALLY_CONTESTED;assert(!action.CheckClassicBanner());
 assert(casts==c);
 bg.map.event.event2=BG_AB_NODE_STATUS_HORDE_OCCUPIED;
 Spell other{&friendBot,&info,false};friendBot.current=&other;other.m_targets.guid=99;
 assert(action.CheckClassicBanner());c=casts;
 other.m_targets.guid=go.guid;assert(!action.CheckClassicBanner()&&casts==c);
 friendBot.current=nullptr;reject=true;auto w=ai.waited;assert(!action.CheckClassicBanner()&&ai.waited==w);reject=false;
 for(unsigned team:{ALLIANCE,HORDE}){
  bot.team=team;bg.type=BATTLEGROUND_AV;
  bg.map.event.event2=team==ALLIANCE?BG_AV_NODE_STATUS_HORDE_CONTESTED:BG_AV_NODE_STATUS_ALLY_CONTESTED;
  assert(action.CheckClassicBanner());
  bg.map.event.event2=team==ALLIANCE?BG_AV_NODE_STATUS_ALLY_CONTESTED:BG_AV_NODE_STATUS_HORDE_CONTESTED;
  assert(!action.CheckClassicBanner());
 }
 // Execute the reported interrupted-capture retry case for both factions/BGs.
 friendBot.current=nullptr;go.x=3;bot.x=0;bot.combat=true;
 Player enemy{&bg};enemy.x=2;ai.units[99]=&enemy;
 for(unsigned type:{BATTLEGROUND_AB,BATTLEGROUND_AV})for(unsigned team:{ALLIANCE,HORDE}){
  bg.type=type;bot.team=team;enemy.team=team==ALLIANCE?HORDE:ALLIANCE;
  bg.map.event.event2=type==BATTLEGROUND_AB?(team==ALLIANCE?BG_AB_NODE_STATUS_HORDE_OCCUPIED:BG_AB_NODE_STATUS_ALLY_OCCUPIED):(team==ALLIANCE?BG_AV_NODE_STATUS_HORDE_OCCUPIED:BG_AV_NODE_STATUS_ALLY_OCCUPIED);
  action.attackers={99};action.possible={99};enemy.x=2;enemy.alive=true;enemy.los=true;
  const auto before=casts,waited=ai.waited,stopped=ai.stopped,moves=action.moves;
  for(unsigned retry=0;retry<5;++retry)assert(!action.CheckClassicBanner());
  assert(casts==before&&ai.waited==waited&&ai.stopped==stopped&&action.moves==moves);
  enemy.x=35;assert(!action.CheckClassicBanner()); // active ranged attacker
  action.attackers.clear();assert(action.CheckClassicBanner()); // merely visible at range
  enemy.x=2;assert(!action.CheckClassicBanner()); // nearby defender even before a hit
  enemy.alive=false;assert(action.CheckClassicBanner());enemy.alive=true;
  enemy.world=false;assert(action.CheckClassicBanner());enemy.world=true;
  BattleGround another;enemy.bg=&another;assert(action.CheckClassicBanner());enemy.bg=&bg;
  enemy.team=team;assert(action.CheckClassicBanner());enemy.team=team==ALLIANCE?HORDE:ALLIANCE;
  enemy.los=false;assert(action.CheckClassicBanner());enemy.los=true;
  action.attackers={99};enemy.x=70;assert(action.CheckClassicBanner()); // remote fight
  action.attackers.clear();action.possible.clear();assert(action.CheckClassicBanner()); // stale combat tag
 }
 std::cout<<"PASS repeated captures yield to local melee/ranged threats, clear nodes resume, both teams in AB/AV\n";
 std::cout<<"PASS actual Classic banner approach/cast, faction and active-event checks, native capture rejection and visibility semantics, immunity, transfer, cast preservation, teammate ownership\n";
}
'''.replace('__BODY__',body)
with tempfile.TemporaryDirectory(prefix='classic-bg-banner-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
