"""Exercise actual reaction selection and item eligibility for all mana classes."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]/'playerbot'
header=(root/'strategy/actions/UseItemAction.h').read_text()
items=(root/'strategy/actions/UseItemAction.cpp').read_text()
reaction=(root/'strategy/ReactionEngine.cpp').read_text()
stats=(root/'strategy/triggers/GenericTriggers.cpp').read_text()
prefix=r"""
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
#include <list>
#include <deque>
#include <set>
#include <map>
#include <memory>
#include <algorithm>
using uint32=uint32_t;using uint64=uint64_t;using uint8=uint8_t;
enum {POWER_MANA=0,CLASS_MAGE=8,EQUIP_ERR_OK=0,MAX_ITEM_PROTO_SPELLS=5,ITEM_SPELLTRIGGER_ON_USE=0,ITEM_SPELLTRIGGER_ON_NO_DELAY_USE=5};
enum class BotCheatMask {item};
struct _Spell {uint32 SpellId=0,SpellTrigger=0;};
struct SpellEntry {uint32 Id=0;};
struct ItemPrototype {uint32 ItemId=0,RequiredLevel=0;_Spell Spells[5];};
struct ObjectMgr {std::map<uint32,ItemPrototype> items;const ItemPrototype* GetItemPrototype(uint32 id){auto i=items.find(id);return i==items.end()?nullptr:&i->second;}}sObjectMgr;
struct Spells {std::map<uint32,SpellEntry> entries;template<class T>const T* LookupEntry(uint32 id){auto i=entries.find(id);return i==entries.end()?nullptr:&i->second;}}sSpellTemplate;
struct Player {uint32 level=60,health=2000,maximum=1000,mana=100,cls=5;bool arena=false,combat=true;std::set<uint32> owned{2455};
 uint32 GetMaxPower(int){return maximum;}uint32 GetPower(int){return mana;}uint32 GetHealth(){return health;}uint32 getClass(){return cls;}
 bool InArena(){return arena;}bool HasItemCount(uint32 id,int){return owned.count(id);}int CanUseItem(const ItemPrototype* p){return p->RequiredLevel<=level?0:1;}};
struct PlayerbotAI {Player bot;bool cheat=true;std::set<uint32> skip,cooldowns;bool HasCheat(BotCheatMask){return cheat;}void HandleCommands(){}};
struct Config {uint32 lowMana=20;int iterationsPerTick=10;}sPlayerbotAIConfig;
struct Log {template<class...T>void outError(const char*,T...){}}sLog;
template<class T>T value(PlayerbotAI* ai,const char* key){std::string k=key;if(k=="combat")return T(ai->bot.combat);if(k=="has mana")return T(ai->bot.maximum!=0);return T(ai->bot.maximum?uint64(ai->bot.mana)*100/ai->bot.maximum:100);}
#define AI_VALUE2(type,key,target) value<type>(ai,key)
#define AI_VALUE(type,key) (ai->skip)
struct Event{};
struct Action {PlayerbotAI* ai;Player* bot;Action(PlayerbotAI* a):ai(a),bot(&a->bot){}virtual ~Action()=default;
 virtual bool isUseful(){return true;}virtual bool isPossible(){return true;}virtual bool ShouldTryAlternativesWhenUseless(){return false;}virtual bool isUsefulWhenStunned(){return false;}void setRelevance(float){}
};
struct UseItemIdAction:Action {using Action::Action;virtual uint32 GetItemId(){return 2455;}bool isUseful()override;bool isPossible()override;
 bool HasItemCooldown(uint32 id){return ai->cooldowns.count(id);}std::string getQualifier(){return "";}std::string getMultiQualifierStr(std::string,int,const char*){return "";}};
struct UsePotionAction:UseItemIdAction {using UseItemIdAction::UseItemIdAction;bool isUseful()override;};
struct UseManaPotionAction:UsePotionAction {using UsePotionAction::UsePotionAction;bool isUseful()override;};
struct UseDarkRuneAction:UseItemIdAction {using UseItemIdAction::UseItemIdAction;uint32 GetItemId()override{return 20520;}bool isUseful()override;bool ShouldTryAlternativesWhenUseless()override;};
struct LowManaTrigger {PlayerbotAI* ai;bool IsActive();};
struct ActionNode {Action* action;Action* alternative;Action* getAlternatives(){return alternative;}Action* getPrerequisites(){return nullptr;}};
struct ActionBasket {ActionNode* node;float relevance=50;Event event;bool isSkipPrerequisites(){return false;}float getRelevance(){return relevance;}const Event& getEvent(){return event;}};
struct Queue {std::deque<std::unique_ptr<ActionBasket>> active;std::vector<std::unique_ptr<ActionBasket>> retired;
 size_t Size(){return active.size();}ActionBasket* Peek(){return active.empty()?nullptr:active.front().get();}
 ActionNode* Pop(ActionBasket*){auto p=std::move(active.front());active.pop_front();auto n=p->node;retired.push_back(std::move(p));return n;}
 void Add(Action* a,Action* alt=nullptr){active.push_back(std::make_unique<ActionBasket>(ActionBasket{new ActionNode{a,alt}}));}
 void RemoveExpired(){} };
struct Multiplier {float GetValue(Action*){return 1;}};
struct Context {void Update(){}};
struct Reaction {Action* action=nullptr;void SetAction(Action* a){action=a;}void SetEvent(const Event&){}bool IsValid(){return action!=nullptr;}};
struct ReactionEngine {PlayerbotAI* ai;Context context;Context* aiObjectContext=&context;Queue queue;std::list<Multiplier*> multipliers;Reaction incomingReaction;
 Action* primary;Action* fallback;ReactionEngine(PlayerbotAI* a,Action* p,Action* f):ai(a),primary(p),fallback(f){}
 bool IsReacting(){return false;}void ProcessTriggers(bool){LowManaTrigger t{ai};if(t.IsActive())queue.Add(primary,fallback);}
 Action* InitializeAction(ActionNode* n){return n->action;}
 bool MultiplyAndPush(Action* a,float,bool,const Event&,const char*){if(!a)return false;queue.Add(a);return true;}
 void PushAgain(ActionNode*,float,const Event&){}bool FindReaction(bool);
};
"""
code=prefix
for marker in ('bool UseItemIdAction::isUseful()','bool UseItemIdAction::isPossible()'):code+=block(items,marker)+'\n'
for name in ('UsePotionAction','UseManaPotionAction','UseDarkRuneAction'):
 body=block(block(header,'class '+name),'bool isUseful()').replace('bool isUseful() override','bool '+name+'::isUseful()')
 code+=body+'\n'
code+=block(block(header,'class UseDarkRuneAction'),'bool ShouldTryAlternativesWhenUseless()').replace('bool ShouldTryAlternativesWhenUseless() override','bool UseDarkRuneAction::ShouldTryAlternativesWhenUseless()')+'\n'
code+=block(stats,'bool LowManaTrigger::IsActive()')+'\n'+block(reaction,'bool ReactionEngine::FindReaction(bool isStunned)')+'\n'
code+=r"""
int main(){
 ItemPrototype potion;potion.ItemId=2455;potion.RequiredLevel=5;potion.Spells[0].SpellId=1;sObjectMgr.items[2455]=potion;
 ItemPrototype rune;rune.ItemId=20520;rune.RequiredLevel=55;rune.Spells[0].SpellId=2;sObjectMgr.items[20520]=rune;
 sSpellTemplate.entries[1]={1};sSpellTemplate.entries[2]={2};
 PlayerbotAI ai;UseDarkRuneAction dark(&ai);UseManaPotionAction mana(&ai);
 auto choose=[&](bool stun=false){ReactionEngine engine(&ai,&dark,&mana);engine.FindReaction(stun);return engine.incomingReaction.action;};
 for(uint32 cls:{2,3,5,7,8,9,11}){
  ai.bot.cls=cls;ai.bot.level=20;ai.bot.health=2000;assert(!dark.isPossible());assert(choose()==&mana);
  ai.bot.level=60;ai.bot.health=900;assert(!dark.isUseful());assert(choose()==&mana);
  ai.bot.health=2000;ai.cheat=false;assert(choose()==&mana);ai.cheat=true;
  ai.skip.insert(2);assert(choose()==&mana);ai.skip.clear();
  ai.cooldowns.insert(20520);assert(choose()==&mana);ai.cooldowns.insert(2455);assert(choose()==nullptr);ai.cooldowns.clear();
  assert(choose()==(cls==CLASS_MAGE?static_cast<Action*>(&mana):static_cast<Action*>(&dark)));
 }
 ai.bot.cls=5;ai.bot.health=900;assert(choose(true)==nullptr);
 ai.bot.mana=500;assert(!mana.isUseful()&&choose()==nullptr);ai.bot.mana=100;
 ai.bot.combat=false;assert(!mana.isUseful());ai.bot.combat=true;
 for(uint32 cls:{1,4,6}){ai.bot.cls=cls;ai.bot.maximum=0;assert(!mana.isUseful()&&choose()==nullptr);}ai.bot.maximum=1000;ai.bot.cls=5;
#ifndef MANGOSBOT_ZERO
 ai.bot.arena=true;assert(choose()==nullptr);ai.bot.arena=false;
#endif
 struct Useless:Action{using Action::Action;bool isUseful()override{return false;}}ordinary(&ai);
 ReactionEngine engine(&ai,&ordinary,&mana);assert(!engine.FindReaction(false));
 ai.bot.level=4;assert(!mana.isPossible());ai.bot.level=5;assert(mana.isPossible());
 ai.cheat=false;ai.bot.owned.clear();assert(!mana.isPossible());ai.cheat=true;assert(mana.isPossible());
}
"""
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mana-reaction-') as temp:
  p=Path(temp);(p/'test.cpp').write_text(code)
  result=subprocess.run(['cl','/nologo','/std:c++20','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
 print('PASS mana fallback: all seven mana classes, rune eligibility, health, skips, cooldowns, arena, stun and stale mana',era,flush=True)
