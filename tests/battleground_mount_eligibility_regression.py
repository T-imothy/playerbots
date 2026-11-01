"""Execute native-map resolution and the production flag-carrier mount guard."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/CheckMountStateAction.cpp').read_text()
pvp=(root/'playerbot/strategy/values/PvpValues.cpp').read_text()
method=block(source,'bool CheckMountStateAction::CanMountInBg(')
resolve=block(pvp,'BattleGroundTypeId ai::ActualBattlegroundType(')
code=r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;
enum BattleGroundTypeId{BATTLEGROUND_TYPE_NONE,BATTLEGROUND_WS,BATTLEGROUND_EY,BATTLEGROUND_RB};
enum{HIGHGUID_GAMEOBJECT};
struct ObjectGuid{ObjectGuid(unsigned,unsigned,unsigned){}};
struct GameObject{};
struct Map{GameObject*GetGameObject(ObjectGuid){return nullptr;}};
struct BattleGround{BattleGroundTypeId type=BATTLEGROUND_WS,actual=BATTLEGROUND_WS;Map map;
 BattleGroundTypeId GetTypeId(bool native=false){return native?actual:type;}Map*GetBgMap(){return &map;}};
using BattleGroundWS=BattleGround;
struct Player{BattleGround*bg;unsigned flag=0;BattleGround*GetBattleGround(){return bg;}
 BattleGroundTypeId GetBattleGroundTypeId(){return bg?bg->type:BATTLEGROUND_TYPE_NONE;}
 bool HasAura(unsigned id){return id==flag;}bool IsWithinDistInMap(GameObject*go,float){assert(go);return false;}};
namespace ai{BattleGroundTypeId ActualBattlegroundType(Player*);}
using namespace ai;
__RESOLVE__
struct AI{Player*bot;Player*GetBot(){return bot;}};
struct CheckMountStateAction{Player*bot;AI*ai;bool CanMountInBg()const;};
__METHOD__
int main(){
 BattleGround bg;Player bot{&bg};AI ai{&bot};CheckMountStateAction action{&bot,&ai};
 assert(action.CanMountInBg());
 for(unsigned flag:{23333u,23335u}){bot.flag=flag;assert(!action.CanMountInBg());}
 bot.flag=0;assert(action.CanMountInBg());
#ifdef MANGOSBOT_TWO
 bg.type=BATTLEGROUND_RB;bg.actual=BATTLEGROUND_WS;
 for(unsigned flag:{23333u,23335u}){bot.flag=flag;assert(!action.CanMountInBg());}
 bot.flag=0;assert(action.CanMountInBg());
 bg.actual=BATTLEGROUND_EY;bot.flag=23333;assert(action.CanMountInBg()); // unrelated map's policy untouched
#endif
 bot.bg=nullptr;assert(action.CanMountInBg());
 std::cout<<"PASS flag-carrier mount guard and Wrath random-BG resolution\n";
}
'''.replace('__METHOD__',method).replace('__RESOLVE__',resolve)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='bg-mount-eligibility-') as directory:
  path=Path(directory);(path/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,check=True)
  subprocess.run([str(path/'test.exe')],cwd=path,check=True)
