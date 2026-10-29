"""Execute saved-preset restoration and objective routing from production source.

No realm or production DB is started. Run in an MSVC developer shell.
"""
from pathlib import Path
import subprocess, tempfile, sys
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
db=(root/'playerbot/PlayerbotDbStore.cpp').read_text(encoding='utf-8')
tactics=(root/'playerbot/strategy/actions/BattleGroundTactics.cpp').read_text(encoding='utf-8')
restore=block(db,'    void RestoreBattlegroundStrategies(')
loader=block(db,'void PlayerbotDbStore::Load(')
route=block(tactics,'bool BGTactics::selectObjectiveWp(')
cast_guard=block(tactics,'    if (SupportsBattlegroundObjectiveRecovery(bot))')
code=r'''
#include <algorithm>
#include <cassert>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <list>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>
#include <cstdlib>
#undef assert
#define assert(value) do { if (!(value)) { std::cerr<<"failed assertion line "<<__LINE__<<"\n"; std::exit(88); } } while(false)
using uint32=uint32_t;using uint64=uint64_t;using BattleGroundTypeId=unsigned;
enum{BATTLEGROUND_WS=2,BATTLEGROUND_AB=3,BATTLEGROUND_AV=1,BATTLEGROUND_EY=7,BATTLEGROUND_IC=30,BATTLEGROUND_RB=32};
enum{ALLIANCE,HORDE,DIST_CALC_NONE};
enum class BotState{BOT_STATE_COMBAT,BOT_STATE_NON_COMBAT,BOT_STATE_DEAD,BOT_STATE_REACTION};
struct Position{float x=0,y=0,z=0,o=0;Position()=default;Position(float x,float y,float z,float o):x(x),y(y),z(z),o(o){}float GetDistance(Position b){return (x-b.x)*(x-b.x)+(y-b.y)*(y-b.y)+(z-b.z)*(z-b.z);}};
using BattleBotWaypoint=Position;using BattleBotPath=std::vector<Position>;
std::vector<BattleBotPath*>vPaths_AllyMine,vPaths_HordeMine,vPaths_NoReverseAllowed;
struct Guid{uint64 GetRawValue(){return 123;}};
struct BattleGround{unsigned type=BATTLEGROUND_WS,actual=BATTLEGROUND_WS;unsigned GetTypeId(bool real=false){return real?actual:type;}};
struct Player:Position{BattleGround bg;bool inBg=true,world=true,transfer=false,alive=true,cast=false,channel=false,automatic=false;unsigned team=ALLIANCE;
 BattleGround*GetBattleGround(){return inBg?&bg:nullptr;}Guid GetObjectGuid(){return {};}
 bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}
 bool IsNonMeleeSpellCasted(bool,bool skipChannel=false,bool skipAuto=false){return cast||(!skipChannel&&channel)||(!skipAuto&&automatic);}
 unsigned GetTeam(){return team;}unsigned GetMapId(){return 489;}
 float GetDistance(float a,float b,float c,int){return Position::GetDistance({a,b,c,0});}};
namespace ai{struct PositionEntry{float x=0,y=0,z=0;bool set=true;bool isSet(){return set;}void Reset(){set=false;}};using PositionMap=std::map<std::string,PositionEntry>;struct WarsongObjective{};}
using namespace ai;
struct PosValue{PositionMap data;PositionMap&Get(){return data;}};
struct GoalValue{int resets=0;void Reset(){++resets;}};
struct Context{PosValue pos;GoalValue goal;int loaded=0;void Load(std::list<std::string>const&){++loaded;}
 template<class T>auto*GetValue(const char*){if constexpr(std::is_same_v<T,WarsongObjective>)return &goal;else return &pos;}};
#define AI_VALUE(type,name) context->GetValue<type>(name)->Get()
struct PlayerbotAI{Player bot;Context context;std::map<BotState,std::set<std::string>> strategies;
 Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &context;}
 void ClearStrategies(BotState s){strategies[s].clear();}
 void ChangeStrategy(std::string const&str,BotState s){std::istringstream in(str);std::string item;while(std::getline(in,item,',')){if(item.empty())continue;if(item[0]=='-')strategies[s].erase(item.substr(1));else strategies[s].insert(item.substr(1));}}
};
unsigned ActualBattlegroundType(Player* p){return p->inBg?(p->bg.type==BATTLEGROUND_RB?p->bg.actual:p->bg.type):0;}
bool SupportsBattlegroundObjectiveRecovery(Player*p){unsigned t=ActualBattlegroundType(p);return t==BATTLEGROUND_WS||t==BATTLEGROUND_AB||t==BATTLEGROUND_AV;}
struct Field{std::string v;std::string GetString(){return v;}};
struct Rows{std::vector<std::vector<Field>> rows;size_t index=0;Field*Fetch(){return rows.at(index).data();}bool NextRow(){return ++index<rows.size();}};
struct Database{std::shared_ptr<Rows>rows;void escape_string(std::string&){}std::shared_ptr<Rows>PQuery(const char*,uint64,const char*){if(rows)rows->index=0;return rows;}}CharacterDatabase;
struct PlayerbotDbStore{void Load(PlayerbotAI*,std::string);};
__RESTORE__
__LOAD__
struct BGTactics{Player*bot;Context*context;unsigned battlegroundObjectiveCheck=1;std::string name="move to objective";int movement=0;Position destination;
 std::string getName(){return name;}bool wsgRoofJump(){return false;}bool wsgPaths(){return false;}bool eotsJump(){return false;}
 bool MoveTo(unsigned,float x,float y,float z){++movement;destination={x,y,z,0};return true;}
 bool moveToObjectiveWp(BattleBotPath*const&p,uint32 current,bool reverse){unsigned next=reverse?current-1:current+1;destination=p->at(reverse?(next?next-1:0):std::min(next+1,unsigned(p->size()-1)));++movement;return true;}
 bool selectObjectiveWp(std::vector<BattleBotPath*>const&);
 bool executeProbe(){__GUARD__++movement;return true;}
};
__ROUTE__
int main(){
 PlayerbotDbStore store;
 for(unsigned type:std::initializer_list<unsigned>{BATTLEGROUND_WS,BATTLEGROUND_AB,BATTLEGROUND_AV,999u,0u}){
  PlayerbotAI ai;ai.bot.bg.type=type;ai.bot.inBg=type!=0;
  CharacterDatabase.rows=std::make_shared<Rows>();
  CharacterDatabase.rows->rows={{{"co"},{"+frost,+heal,+stay,+follow"}},{{"nc"},{"+follow,+travel,+rpg"}},{{"dead"},{"+dead"}},{{"value"},{"formation=melee"}}};
  store.Load(&ai,"");bool supported=type==1||type==2||type==3;
  auto&co=ai.strategies[BotState::BOT_STATE_COMBAT];auto&nc=ai.strategies[BotState::BOT_STATE_NON_COMBAT];
  assert(co.count("frost")&&co.count("heal")&&co.count("stay"));assert(ai.context.loaded==1);
  assert(bool(co.count("battleground"))==supported&&bool(nc.count("battleground"))==supported);
  assert(bool(co.count("pvp"))==supported&&bool(nc.count("pvp"))==supported);
  assert(bool(co.count("default"))==supported&&bool(nc.count("default"))==supported);
  assert(bool(nc.count("follow"))==!supported&&bool(nc.count("travel"))==!supported);
  assert(bool(ai.strategies[BotState::BOT_STATE_DEAD].count("battleground"))==supported);
  if(supported){const char*goal=type==2?"warsong":type==3?"arathi":"alterac";assert(co.count(goal)&&nc.count(goal));}
  auto original=ai.strategies;store.Load(&ai,"");assert(ai.strategies==original); // repeated resets remain usable
  CharacterDatabase.rows.reset();store.Load(&ai,"missing");assert(ai.strategies==original);
 }
 for(unsigned type:{BATTLEGROUND_WS,BATTLEGROUND_AB,BATTLEGROUND_AV}){
  Player bot;bot.bg.type=type;Context context;BGTactics action{&bot,&context};
  for(auto kind:{0,1,2}){bot.cast=kind==0;bot.channel=kind==1;bot.automatic=kind==2;
   action.name="move to objective";assert(action.executeProbe()==(kind==2));
   action.name="check flag";assert(!action.executeProbe()); // never replace a banner channel/shot with capture
  }
  bot.cast=bot.channel=bot.automatic=false;bot.transfer=true;assert(!action.executeProbe());bot.transfer=false;
  bot.world=false;assert(!action.executeProbe());bot.world=true;bot.alive=false;action.name="reset objective";
  assert(action.executeProbe());assert(!context.pos.data["bg objective"].isSet());assert(!action.executeProbe());
  bot.alive=true;action.name="move to objective";assert(action.executeProbe());
  action.movement=0;context.pos.data["bg objective"]={100,0,0,true};
  BattleBotPath completed{{-20,0,0,0},{0,0,0,0}}, onward{{0,0,0,0},{30,20,0,0},{90,30,0,0}};
  // The finished leg wins endpoint scoring in the old code and then returns false.
  // Use an onward route whose end is temporarily farther from the objective.
  onward.back()={-20,80,0,0};vPaths_NoReverseAllowed={&completed,&onward};
  assert(action.selectObjectiveWp({nullptr,&completed,&onward}));assert(action.destination.y>0&&action.movement==1);
  BattleBotPath endAhead{{-50,0,0,0},{20,0,0,0}};vPaths_NoReverseAllowed={&endAhead};
  action.movement=0;assert(action.selectObjectiveWp({&endAhead}));assert(action.destination.x==20&&action.movement==1);
  BattleBotPath reverseAhead{{20,0,0,0},{-50,0,0,0}};vPaths_NoReverseAllowed.clear();
  action.movement=0;assert(action.selectObjectiveWp({&reverseAhead}));assert(action.destination.x==20&&action.movement==1);
  BattleBotPath empty;assert(!action.selectObjectiveWp({&empty}));
 }
 std::cout<<"PASS saved PvE preset retains roles and BG objectives; cast/channel vs auto-repeat; transfer/death; completed route and both endpoint directions\n";
}
'''.replace('__RESTORE__',restore).replace('__LOAD__',loader).replace('__ROUTE__',route).replace('__GUARD__',cast_guard)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='bg-liveness-') as td:
  p=Path(td);(p/'test.cpp').write_text(code,encoding='utf-8')
  result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(era+'\n'+result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
 print('PASS',era,flush=True)
if '--prove-regressions' in sys.argv:
 old=subprocess.check_output(['git','show','24dc8609917f370a72a867caa1f13f4abb063cb8:playerbot/strategy/actions/BattleGroundTactics.cpp'],cwd=root).decode('utf-8')
 variants={
  'saved preset removes BG handlers':code.replace(restore,'void RestoreBattlegroundStrategies(PlayerbotAI*){}'),
  'auto-repeat blocks objective movement':code.replace(cast_guard,block(old,'    if (SupportsBattlegroundObjectiveRecovery(bot))')),
  'completed route blocks connected leg':code.replace(route,block(old,'bool BGTactics::selectObjectiveWp(')).replace('{nullptr,&completed,&onward}','{&completed,&onward}'),
 }
 for label,variant in variants.items():
  with tempfile.TemporaryDirectory(prefix='bg-before-') as td:
   p=Path(td);(p/'test.cpp').write_text(variant,encoding='utf-8')
   result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_ZERO','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
   if result.returncode:raise RuntimeError(result.stdout+result.stderr)
   result=subprocess.run([str(p/'test.exe')],cwd=p,capture_output=True,text=True)
   assert result.returncode==88,(label,result.returncode,result.stdout,result.stderr)
   print('REPRODUCED BEFORE FIX:',label,result.stderr.strip(),flush=True)
