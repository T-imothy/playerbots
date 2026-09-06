"""Compile real cleansing actions, factory mappings and water-totem trigger per era."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
folder=root/'playerbot/strategy/shaman'
actions=(folder/'ShamanActions.h').read_text()
trigger=block((folder/'ShamanTriggers.h').read_text(),'class WaterTotemTrigger')+';'
factory=(folder/'ShamanAiObjectContext.cpp').read_text()
start=factory.index('                creators["disease cleansing totem"]')
mapping=factory[start:factory.index('                creators["wind shear"]',start)]
assert 'CastDiseaseCleansingTotemAction' in mapping and 'CastCleansingTotemAction' in mapping
for key in ('totem water cleansing','totem water poison'):
    assert f'creators["{key}"]' in factory
classes='\n'.join(block(actions,f'class {name}')+';' for name in ('CastDiseaseCleansingTotemAction','CastPoisonCleansingTotemAction'))
classes+='\n#ifdef MANGOSBOT_TWO\n'+block(actions,'class CastCleansingTotemAction')+';\n#endif\n'
code=r'''
#include <cassert>
#include <functional>
#include <map>
#include <set>
#include <string>
#include <iostream>
#include "__HELPERS__"
using namespace ai;
enum class BotState{BOT_STATE_COMBAT};enum{IDLE_MOTION_TYPE=0};
struct MotionMaster{int GetCurrentMovementGeneratorType(){return 1;}};
struct Player{bool moving=false;MotionMaster mm;bool IsMoving(){return moving;}MotionMaster* GetMotionMaster(){return &mm;}};
struct PlayerbotAI{Player bot;std::string strategy;std::set<std::string> totems;bool HasStrategy(const char* s,BotState){return strategy==s;}};
struct Trigger{PlayerbotAI* ai;Player* bot;Trigger(PlayerbotAI* a,const char*,int):ai(a),bot(&a->bot){}virtual bool IsActive(){return false;}};
struct CastTotemAction{PlayerbotAI* ai;std::string name;CastTotemAction(PlayerbotAI* a,std::string n):ai(a),name(n){}virtual ~CastTotemAction()=default;};
#define AI_VALUE2(type,key,name) (ai->totems.count(name)!=0)
__CLASSES__
__TRIGGER__
int main(){
 std::map<std::string,std::function<CastTotemAction*(PlayerbotAI*)>> creators;
 __FACTORY__
 PlayerbotAI ai;WaterTotemTrigger trigger(&ai),stationary(&ai,false);
 const std::string disease=DiseaseCleansingTotemName(),poison=PoisonCleansingTotemName();
#ifdef MANGOSBOT_TWO
 assert(disease=="cleansing totem"&&poison==disease&&creators.count("cleansing totem"));
#else
 assert(disease=="disease cleansing totem"&&poison=="poison cleansing totem"&&!creators.count("cleansing totem"));
#endif
 for(const auto& command:{"disease cleansing totem","poison cleansing totem"}){
  auto* action=creators.at(command)(&ai);assert(action->name==(std::string(command)=="disease cleansing totem"?disease:poison));delete action;}
 ai.strategy="totem water cleansing";assert(trigger.IsActive());ai.totems.insert(disease);assert(!trigger.IsActive());
 ai.strategy="totem water poison";ai.totems.clear();assert(trigger.IsActive());ai.totems.insert(poison);assert(!trigger.IsActive());
 ai.strategy.clear();assert(!trigger.IsActive());ai.totems.clear();assert(trigger.IsActive());
 for(const auto& totem:{"healing stream totem","mana spring totem","mana tide totem","fire resistance totem"}){
  ai.totems.insert(totem);assert(!trigger.IsActive());ai.totems.clear();}
 ai.bot.moving=true;assert(!stationary.IsActive()&&trigger.IsActive());
 std::cout<<"PASS: actual per-era cleansing actions/factory and no recast while matching water totem exists\n";
}
'''.replace('__HELPERS__',(folder/'ShamanTotemSpells.h').as_posix()).replace('__CLASSES__',classes).replace('__TRIGGER__',trigger).replace('__FACTORY__',mapping)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-shaman-cleansing-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
