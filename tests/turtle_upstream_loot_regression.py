"""Execute the actual RPG/travel loot-admission tails from the Turtle port."""
from pathlib import Path
from behavior_regression import block
from turtle_cpp_fixture import run
root=Path(__file__).resolve().parents[1]
tails=[]
for file,cls,name in [('MoveToRpgTargetAction.cpp','MoveToRpgTargetAction','Rpg'),('MoveToTravelTargetAction.cpp','MoveToTravelTargetAction','Travel')]:
 text=(root/'playerbot/strategy/actions'/file).read_text()
 method=block(text,'bool '+cls+'::isUseful()')
 tail=method[method.index('    if (AI_VALUE(bool, "has available loot"))'):]
 tails.append('bool '+name+'(AI* ai, Player* bot, TravelTarget* travelTarget) {\n'+tail)
code=r'''
#include <cassert>
#include <string>
#include <type_traits>
#include <cstdio>
struct Player{};
struct LootObject{bool possible=false;bool IsLootPossible(Player*){return possible;}};
struct LootObjectStack{LootObject current;LootObject GetLoot(float){return current;}};
struct Config{float lootDistance=10;}sPlayerbotAIConfig;
struct TravelTarget{bool forced=false;int pos=0;bool IsForced(){return forced;}int*GetPosition(){return &pos;}};
struct AI{bool hasAvailable=false,freeMove=true;LootObject selected;LootObjectStack available;
 template<class T>T Value(std::string key){if constexpr(std::is_same_v<T,bool>)return hasAvailable;
 else if constexpr(std::is_same_v<T,LootObjectStack*>)return &available;else return selected;}
};
struct CanFreeMoveValue{static bool CanFreeMoveTo(AI* ai,int){return ai->freeMove;}};
#define AI_VALUE(type,key) ai->Value<type>(key)
'''+'\n'.join(tails)+r'''
int main(){Player bot;TravelTarget target;
 for(bool available:{false,true})for(bool availablePossible:{false,true})for(bool selectedPossible:{false,true}){
  AI ai;ai.hasAvailable=available;ai.available.current.possible=availablePossible;ai.selected.possible=selectedPossible;
  bool admitted=!(available&&availablePossible)&&!selectedPossible;
  assert(Rpg(&ai,&bot,&target)==admitted);assert(Travel(&ai,&bot,&target)==admitted);
 }
 AI ai;ai.selected.possible=true;assert(!Travel(&ai,&bot,&target));
 ai.selected.possible=false;assert(Travel(&ai,&bot,&target)&&Rpg(&ai,&bot,&target));
 ai.freeMove=false;assert(!Travel(&ai,&bot,&target));target.forced=true;assert(Travel(&ai,&bot,&target));
 ai.selected.possible=true;assert(!Travel(&ai,&bot,&target));
 puts("PASS actual RPG/travel loot admission: selected loot blocks movement even without available-stack entries; completed/invalid loot releases it; native free-move and forced-target policies retained");
}
'''
run(code)
