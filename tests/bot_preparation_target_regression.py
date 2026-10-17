"""Run native preparation handlers and factory entry guards for all three eras."""
from pathlib import Path
import re,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
mgr=(root/'playerbot/PlayerbotMgr.cpp').read_text();factory=(root/'playerbot/PlayerbotFactory.cpp').read_text();header=(root/'playerbot/PlayerbotFactory.h').read_text()
names=('TrainLearn','FoodDrink','Potions','Consumes','Reagents','Prepare','Init','Enchants','Ammo','Pet','LevelUp','Refresh','Random')
handlers='\n'.join(block(mgr,'std::string PlayerbotHolder::HandleBot'+name+'(') for name in names)
constructor=re.search(r'    PlayerbotFactory\(Player\* bot, uint32 level[^\n]+\{\}',header)[0]
randomize=block(factory,'void PlayerbotFactory::Randomize(')
# Execute the real entry through Prepare and the existing disabled-level gate.
# The expensive loot/talent world dependencies after that point are unrelated.
randomize=randomize[:randomize.index('    bool isRealRandomBot')]+'    lastIncremental = incremental; lastSync = syncWithMaster; ++bot->randomized;\n}'
code=r'''
#include <cassert>
#include <string>
#include <vector>
#include <iostream>
using uint32=unsigned;
constexpr unsigned ITEM_QUALITY_NORMAL=1,ITEM_QUALITY_UNCOMMON=2,ITEM_QUALITY_RARE=3,ITEM_QUALITY_EPIC=4,ITEM_QUALITY_LEGENDARY=5,IN_MILLISECONDS=1000;
enum class BotCheatMask{item};
struct PlayerbotAI{bool itemCheat=true;unsigned cheatCalls=0;bool HasCheat(BotCheatMask){++cheatCalls;return itemCheat;}};
struct Session{bool logout=false;bool isLogingOut(){return logout;}};
struct Player{PlayerbotAI ownAi;PlayerbotAI*ai=&ownAi;Session session;bool connected=true,world=true,transfer=false,human=false;uint32 level=30;
 unsigned levelReads=0,prepared=0,randomized=0,supplies=0,equipment=0,spells=0,saves=0;
 PlayerbotAI*GetPlayerbotAI(){return ai;}Session*GetSession(){return connected?&session:nullptr;}bool isRealPlayer(){return human;}
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return transfer;}uint32 GetLevel(){++levelReads;return level;}
 void learnClassLevelSpells(){++spells;}void SaveToDB(){++saves;}
 unsigned changes(){return prepared+randomized+supplies+equipment+spells+saves;}};
struct Config{bool disableRandomLevels=false;}sPlayerbotAIConfig;
struct Log{template<class...T>void outDetail(const char*,T...){}}sLog;
struct RandomMgr{uint32 GetDatabaseDelay(const char*){return 0;}void Randomize(Player*b){++b->randomized;}}sRandomPlayerbotMgr;
struct PlayerbotFactory{uint32 level,itemQuality;Player*bot;PlayerbotAI*ai;
 __CONSTRUCTOR__
 static std::string CommandTargetReason(Player*);void Randomize(bool,bool);void Refresh();
 static bool lastIncremental,lastSync;void Prepare(){++bot->prepared;bot->level=level;}
 void InitAmmo(){++bot->supplies;}void InitFood(){++bot->supplies;}void InitPotions(){++bot->supplies;}void InitReagents(){++bot->supplies;}void AddConsumables(){++bot->supplies;}
 void EnchantEquipment(){++bot->equipment;}void InitPet(){++bot->equipment;}void InitPetSpells(){++bot->spells;}
 void BeginSupplyRequest(){}bool SupplyRequestFailed(){return false;}
 void AddFood(){InitFood();}void AddPotions(){InitPotions();}void AddConsumes(){AddConsumables();}void AddReagents(){InitReagents();}};
bool PlayerbotFactory::lastIncremental=false;bool PlayerbotFactory::lastSync=false;
__TARGET__
__RANDOMIZE__
__REFRESH__
struct PlayerbotHolder{__DECLARATIONS__};
__HANDLERS__
int main(){PlayerbotHolder holder;Player master;master.human=true;master.level=60;
 using Command=std::string(PlayerbotHolder::*)(Player*,Player*,const std::string);
 std::vector<Command>commands={__POINTERS__};
 for(auto command:commands){
  for(Player*owner:{static_cast<Player*>(nullptr),&master}){
   assert((holder.*command)(nullptr,owner,"")=="Player is offline");
   for(unsigned scenario=0;scenario<7;++scenario){Player bot;
    if(scenario==0)bot.connected=false;if(scenario==1)bot.ai=nullptr;if(scenario==2)bot.human=true;
    if(scenario==3)bot.world=false;if(scenario==4)bot.transfer=true;if(scenario==5)bot.session.logout=true;
    if(scenario==6){bot.ai=nullptr;bot.human=true;}
    auto response=(holder.*command)(&bot,owner,"");
    assert(!response.empty()&&response!="ok"&&bot.changes()==0&&bot.level==30&&bot.levelReads==0&&bot.ownAi.cheatCalls==0);
   }
  }
 }
 // Every existing init branch retains its forwarded incremental/sync choices.
 for(std::string param:{"","common","white","green","uncommon","blue","rare","epic","purple","legendary","yellow","sync"}){
  Player bot;auto response=holder.HandleBotInit(&bot,&master,param);assert(response=="ok"&&bot.prepared==1&&bot.randomized==1&&bot.level==60);
  assert(PlayerbotFactory::lastIncremental==param.empty());assert(PlayerbotFactory::lastSync==(param=="sync"));
 }
 {Player bot;assert(holder.HandleBotPrepare(&bot,nullptr,"")=="consumes/regs added"&&bot.supplies==5&&bot.saves==1);}
 {Player bot;bot.ownAi.itemCheat=false;assert(holder.HandleBotPrepare(&bot,nullptr,"")=="consumes/regs added"&&bot.changes()==0);}
 // A batch can reject unavailable/human targets and still prepare valid bots.
 {Player human,loading,first,last;human.human=true;loading.transfer=true;
  for(Player*bot:{&human,static_cast<Player*>(nullptr),&loading,&first,&last})holder.HandleBotInit(bot,&master,"");
  assert(human.changes()==0&&loading.changes()==0&&first.randomized==1&&last.randomized==1);}
 // Defensive factory callers also stop before Prepare or HasCheat.
 {PlayerbotFactory missing(nullptr,60);missing.Randomize(true,false);missing.Refresh();}
 {Player bot;bot.ai=nullptr;PlayerbotFactory missingAi(&bot,60);missingAi.Randomize(true,false);missingAi.Refresh();assert(bot.changes()==0&&bot.level==30);}
 {Player bot;PlayerbotFactory stale(&bot,60);PlayerbotAI replacement;bot.ai=&replacement;stale.Randomize(true,false);stale.Refresh();assert(bot.changes()==0&&bot.ownAi.cheatCalls==0);}
 {Player bot;assert(holder.HandleBotFoodDrink(&bot,nullptr,"")=="food added");assert(holder.HandleBotPotions(&bot,nullptr,"")=="potions added");
  assert(holder.HandleBotConsumes(&bot,nullptr,"")=="consumables added");assert(holder.HandleBotReagents(&bot,nullptr,"")=="reagents added");}
 std::cout<<"PASS 13 native preparation handlers: null/offline/non-bot/human/transfer/logout refusal with zero mutation; valid init/supply responses, mixed-batch isolation and defensive factory guards\n";
}
'''
code=code.replace('__CONSTRUCTOR__',constructor).replace('__TARGET__',block(factory,'std::string PlayerbotFactory::CommandTargetReason(')).replace('__RANDOMIZE__',randomize).replace('__REFRESH__',block(factory,'void PlayerbotFactory::Refresh('))
code=code.replace('__DECLARATIONS__',''.join('std::string HandleBot'+name+'(Player*,Player*,const std::string);' for name in names)).replace('__POINTERS__',','.join('&PlayerbotHolder::HandleBot'+name for name in names)).replace('__HANDLERS__',handlers)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='bot-preparation-target-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
