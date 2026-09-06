"""Exercise hunter/priest mana-target choices against the real resource values."""
from pathlib import Path
import re
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1] / 'playerbot/strategy'
stats = (root / 'values/StatsValues.cpp').read_text()
methods = '\n'.join(block(stats, key) for key in ('uint8 ManaValue::Calculate(', 'bool HasManaValue::Calculate('))
hunter = (root / 'hunter/HunterActions.cpp').read_text()
methods += '\n' + '\n'.join(block(hunter, f'bool {name}::isUseful(') for name in ('CastSerpentStingAction', 'CastViperStingAction'))
trigger = block((root / 'hunter/HunterTriggers.h').read_text(), 'class ViperStingTrigger') + ';'
macro = re.search(r'#define SPELL_ACTION_U\(.*?(?=\n\s*#define)', (root / 'AiObject.h').read_text(), re.S).group(0)
burn = re.search(r'    SPELL_ACTION_U\(CastManaBurnAction,.*', (root / 'priest/PriestActions.h').read_text()).group(0)
code = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
#include <type_traits>
using uint8=uint8_t;using uint32=uint32_t;using uint64=uint64_t;
enum {POWER_MANA};enum class BotState {BOT_STATE_COMBAT};
struct Unit {uint32 current=100,maximum=100;uint8 health=100;
 uint32 GetPower(int){return current;}uint32 GetMaxPower(int){return maximum;}};
struct ManaValue {Unit* target;Unit* GetTarget(){return target;}uint8 Calculate();};
struct HasManaValue {Unit* target;Unit* GetTarget(){return target;}bool Calculate();};
struct PlayerbotAI {Unit* self;Unit* enemy;bool serpent=false,eligible=true;
 bool HasStrategy(const char*,BotState){return serpent;}
 template<class T>T value(const char* name,const std::string& qualifier){
  Unit* unit=qualifier=="self target"?self:enemy;
  if constexpr(std::is_same_v<T,bool>)return HasManaValue{unit}.Calculate();
  else return std::string(name)=="health"?(unit?unit->health:0):ManaValue{unit}.Calculate();
 }};
#define AI_VALUE2(type,name,qualifier) ai->value<type>(name,qualifier)
struct CastSpellAction {PlayerbotAI* ai;CastSpellAction(PlayerbotAI* a,const char*):ai(a){}
 virtual bool isUseful(){return ai->eligible && ai->enemy;}std::string GetTargetName(){return "current target";}};
struct CastRangedDebuffSpellAction:CastSpellAction {using CastSpellAction::CastSpellAction;};
struct CastSerpentStingAction:CastRangedDebuffSpellAction {using CastRangedDebuffSpellAction::CastRangedDebuffSpellAction;bool isUseful() override;};
struct CastViperStingAction:CastRangedDebuffSpellAction {using CastRangedDebuffSpellAction::CastRangedDebuffSpellAction;bool isUseful() override;};
struct DebuffTrigger {PlayerbotAI* ai;DebuffTrigger(PlayerbotAI* a,const char*):ai(a){}virtual bool IsActive(){return ai->eligible && ai->enemy;}};
__MACRO__
__BURN__
__TRIGGER__
__METHODS__
int main(){
 Unit self,target;self.current=25;PlayerbotAI ai{&self,&target};
 CastSerpentStingAction serpent(&ai,"serpent sting");CastViperStingAction viper(&ai,"viper sting");
 ViperStingTrigger trigger(&ai);CastManaBurnAction burn(&ai);
 assert(viper.isUseful() && trigger.IsActive() && burn.isUseful() && !serpent.isUseful());
 target.maximum=0;target.current=0;assert(serpent.isUseful());
 assert(!viper.isUseful() && !trigger.IsActive() && !burn.isUseful());
 target.maximum=100;assert(serpent.isUseful() && !viper.isUseful() && !burn.isUseful());
 target.current=9;assert(serpent.isUseful() && !viper.isUseful() && !trigger.IsActive());
 target.current=10;assert(!serpent.isUseful() && viper.isUseful() && trigger.IsActive() && !burn.isUseful());
 target.current=20;assert(burn.isUseful());self.current=50;assert(!burn.isUseful());
 ai.serpent=true;assert(serpent.isUseful());target.health=50;assert(!serpent.isUseful());
 ai.eligible=false;assert(!viper.isUseful() && !trigger.IsActive());
 ai.enemy=nullptr;assert(!viper.isUseful() && !trigger.IsActive() && !burn.isUseful());
 std::cout<<"PASS: hunter sting and priest mana-burn choices with mana/non-mana/empty/absent targets\n";
}
'''.replace('__MACRO__', macro).replace('__BURN__', burn).replace('__TRIGGER__', trigger).replace('__METHODS__', methods)
with tempfile.TemporaryDirectory(prefix='mantech-mana-target-') as folder:
    tmp = Path(folder)
    (tmp / 'test.cpp').write_text(code)
    for era in ('ZERO', 'ONE', 'TWO'):
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/DMANGOSBOT_' + era, 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
