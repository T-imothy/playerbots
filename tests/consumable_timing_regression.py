"""Exercise actual rest bodies and healthstone selection for each era."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
ROOT=Path(__file__).resolve().parents[1]/'playerbot/strategy'
source=(ROOT/'actions/UseItemAction.h').read_text(encoding='utf-8')
def run(code,era):
 with tempfile.TemporaryDirectory(prefix='consumable-regression-') as td:
  p=Path(td);(p/'test.cpp').write_text(code,encoding='utf-8')
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True,timeout=20)
 print('PASS rest cast failure, combat gate, stand state, native inventory path and healthstone era ranks',era,flush=True)
common=r'''
#include <cassert>
#include <cstdio>
#include <cstdlib>
#undef assert
#define assert(x) do { if(!(x)){fprintf(stderr,"assertion line %d: %s\n",__LINE__,#x);exit(1);} } while(0)
#include <cstdint>
#include <string>
#include <list>
using uint32=uint32_t;
struct Event{};struct SpellEntry{};
enum {UNIT_STAT_CHASE=2,UNIT_STAT_FOLLOW=4,UNIT_STAND_STATE_SIT=1,FOLLOW_MOTION_TYPE=3};
enum class BotCheatMask{item};
struct Motion{int type=0;int GetCurrentMovementGeneratorType(){return type;}};
struct Player{Motion motion;bool combat=false,moving=false,casting=false,mana=true;int stand=0,state=0;uint32 level=1;
 bool HasMana(){return mana;}bool IsNonMeleeSpellCasted(bool){return casting;}void clearUnitState(int x){state&=~x;}
 Motion* GetMotionMaster(){return &motion;}void SetStandState(int s){stand=s;}void RemoveSpellCooldown(const SpellEntry&){}uint32 GetLevel(){return level;}};
struct ItemPrototype{uint32 ItemId=0;};struct Item{ItemPrototype proto;const ItemPrototype* GetProto(){return &proto;}};
struct PlayerbotAI{Player bot;bool cheat=true,cast=true;uint32 casts=0;
 bool HasCheat(BotCheatMask){return cheat;}Player* GetBot(){return &bot;}void StopMoving(){bot.moving=false;}void InterruptSpell(){}void Unmount(){}
 bool CastSpell(int,Player*){++casts;return cast;}void AddAura(Player*,int){}};
struct Facade{SpellEntry spell;bool IsInCombat(Player* p){return p->combat;}bool isMoving(Player* p){return p->moving;}const SpellEntry* LookupSpellInfo(int){return &spell;}}sServerFacade;
struct Config{uint32 globalCoolDown=1500;}sPlayerbotAIConfig;
struct UseAction{PlayerbotAI* ai;Player* bot;std::string name;uint32 duration=0;std::list<Item*> items;bool native=false;
 UseAction(PlayerbotAI* a):ai(a),bot(&a->bot){}virtual bool Execute(Event&){native=true;return true;}virtual uint32 GetItemId(){return 0;}void SetDuration(float n){duration=(uint32)n;}};
#define AI_VALUE(type,key) (std::string(key).find("duration")!=std::string::npos?12000:0)
#define AI_VALUE2(type,key,name) (this->items)
'''
for era in ('ZERO','ONE','TWO'):
 code=common
 for name in ('DrinkAction','EatAction'):
  body=block(block(source,'class '+name),'bool Execute(Event& event)')
  code+='struct '+name+':UseAction{using UseAction::UseAction;'+body+'};\n'
 hs=block(block(source,'class UseHealthstoneAction'),'uint32 GetItemId()')
 code+='struct Healthstone:UseAction{using UseAction::UseAction;std::string getName(){return "healthstone";}'+hs+'};\n'
 code+=r'''
int main(){PlayerbotAI ai;Event e;DrinkAction drink(&ai);EatAction eat(&ai);
 ai.cast=false;assert(!drink.Execute(e)&&drink.duration==0);assert(!eat.Execute(e)&&eat.duration==0);assert(ai.bot.stand==1&&ai.bot.state==0);
 ai.cast=true;assert(drink.Execute(e)&&drink.duration==12000);assert(eat.Execute(e)&&eat.duration==12000);
 ai.bot.combat=true;uint32 before=ai.casts;assert(!drink.Execute(e)&&!eat.Execute(e)&&ai.casts==before);ai.bot.combat=false;
 ai.bot.mana=false;assert(!drink.Execute(e));assert(eat.Execute(e));ai.bot.mana=true;
 ai.cheat=false;assert(!drink.Execute(e));Item item{{19013}};drink.items.push_back(&item);assert(drink.Execute(e)&&drink.native);
 Healthstone hs(&ai);ai.bot.level=1;assert(hs.GetItemId()==5512);ai.bot.level=12;assert(hs.GetItemId()==5511);ai.bot.level=24;assert(hs.GetItemId()==5509);
 ai.bot.level=36;assert(hs.GetItemId()==5510);ai.bot.level=48;assert(hs.GetItemId()==9421);ai.bot.level=59;assert(hs.GetItemId()==9421);
 ai.bot.level=60;
#ifdef MANGOSBOT_ZERO
 assert(hs.GetItemId()==9421);
#else
 assert(hs.GetItemId()==22103);ai.bot.level=63;
#ifdef MANGOSBOT_ONE
 assert(hs.GetItemId()==22103);ai.bot.level=70;assert(hs.GetItemId()==22103);
#else
 assert(hs.GetItemId()==36889);ai.bot.level=69;assert(hs.GetItemId()==36892);ai.bot.level=80;assert(hs.GetItemId()==36892);
#endif
#endif
 hs.items.push_back(&item);assert(hs.GetItemId()==19013);
}
'''
 run(code,era)
for name in ('UsePotionAction','UseHealthstoneAction'):
 execute=block(block(source,'class '+name),'bool Execute(Event& event)')
 assert execute.rstrip().endswith('return false;\n        }')
assert 'bot->InArena()' in block(block(source,'class UsePotionAction'),'bool isUseful()')
assert 'SPELL_AURA_PERIODIC_LEECH' in block(block(source,'class UseBandageAction'),'virtual bool isUseful()')
