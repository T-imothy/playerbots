"""Compile actual changed class bodies with controlled core interfaces on MSVC."""
import subprocess
import tempfile
from pathlib import Path
from behavior_regression import block

ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / 'playerbot' / path).read_text()


def run(code, label, defines=()):
    with tempfile.TemporaryDirectory(prefix='mantech-class-') as tmp:
        tmp = Path(tmp)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/W3', *[f'/D{x}' for x in defines], 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
    print('PASS:', label, *defines, flush=True)


common = r'''
#include <cassert>
#include <cstdint>
#include <map>
#include <string>
#include <vector>
using uint8=uint8_t;using uint32=uint32_t;
struct Event{};
'''

ammo = block(source('strategy/hunter/HunterActions.cpp'), 'bool HunterEquipAmmoAction::Execute')
run(common + r'''
enum {ITEM_SUBCLASS_WEAPON_GUN=1,ITEM_SUBCLASS_WEAPON_BOW,ITEM_SUBCLASS_WEAPON_CROSSBOW,ITEM_SUBCLASS_BULLET,ITEM_SUBCLASS_ARROW,ITEM_CLASS_PROJECTILE,PLAYER_AMMO_ID,EQUIP_ERR_OK=0};
enum {INVENTORY_SLOT_BAG_0=0,EQUIPMENT_SLOT_RANGED=2,INVENTORY_SLOT_ITEM_START=10,INVENTORY_SLOT_ITEM_END=14,INVENTORY_SLOT_BAG_START=20,INVENTORY_SLOT_BAG_END=22};
struct ItemPrototype{uint32 ItemId=0,Class=0,SubClass=0,ItemLevel=0;};
struct Item{ItemPrototype proto;const ItemPrototype* GetProto(){return &proto;}};
struct Bag:Item{std::vector<Item*> items;uint32 GetBagSize(){return items.size();}Item* GetItemByPos(uint32 i){return items.at(i);}};
struct Player{std::map<int,Item*> slots;std::map<int,bool> usable;uint32 ammo=0,sets=0;bool reject=false;Item* GetItemByPos(int,int slot){return slots[slot];}uint32 GetUInt32Value(int){return ammo;}int CanUseAmmo(int id){return usable[id]?0:1;}void SetAmmo(uint32 id){++sets;if(!reject)ammo=id;}};
struct HunterEquipAmmoAction{Player* bot;bool Execute(Event&);};
''' + ammo + r'''
int main(){Player bot;Event e;HunterEquipAmmoAction action{&bot};
 assert(!action.Execute(e));Item weapon{{1,0,ITEM_SUBCLASS_WEAPON_BOW,1}};bot.slots[2]=&weapon;
 Item low{{101,ITEM_CLASS_PROJECTILE,ITEM_SUBCLASS_ARROW,10}},high{{102,ITEM_CLASS_PROJECTILE,ITEM_SUBCLASS_ARROW,50}},bullet{{103,ITEM_CLASS_PROJECTILE,ITEM_SUBCLASS_BULLET,99}};
 bot.slots[10]=&low;bot.slots[11]=&high;bot.slots[12]=&bullet;bot.usable[101]=true;bot.usable[103]=true;
 assert(action.Execute(e)&&bot.ammo==101&&bot.sets==1);assert(!action.Execute(e));
 bot.usable[102]=true;assert(action.Execute(e)&&bot.ammo==102);
 bot.slots[11]=nullptr;Bag bag;bag.items={&high};bot.slots[20]=&bag;bot.ammo=101;assert(action.Execute(e)&&bot.ammo==102);
 weapon.proto.SubClass=99;assert(!action.Execute(e));weapon.proto.SubClass=ITEM_SUBCLASS_WEAPON_GUN;assert(action.Execute(e)&&bot.ammo==103);
 bot.ammo=0;bot.reject=true;assert(!action.Execute(e)&&bot.ammo==0);
 bot.usable.clear();assert(!action.Execute(e));
}
''', 'hunter backpack/bags, usable ammo, correct projectile, unsupported weapon, core setter rejection')

mage = block(source('strategy/mage/MageActions.h'), 'class CastConjureManaGemAction') + ';'
for expansion in ('ZERO', 'ONE', 'TWO'):
    run(common + r'''
enum class BotCheatMask{item,attackspeed};
struct Config{uint32 globalCoolDown=1000;}sPlayerbotAIConfig;
struct Player{};
struct PlayerbotAI{Player bot;bool cheat=false;bool possible=true;std::map<std::string,uint32> ids;int castCalls=0;uint32 last=0;bool HasCheat(BotCheatMask mask){return mask==BotCheatMask::item&&cheat;}bool CanCastSpell(uint32 id,Player*,int){return id&&possible;}bool CastSpell(uint32 id,Player*,void*,bool,uint32*){++castCalls;last=id;return id&&possible;}};
struct Action{PlayerbotAI* ai;Player* bot;Action(PlayerbotAI* ai,std::string):ai(ai),bot(&ai->bot){}virtual bool Execute(Event&){return false;}virtual bool isPossible(){return false;}void SetDuration(uint32){}};
#define AI_VALUE2(type,key,name) (ai->ids[name])
''' + mage + r'''
int main(){PlayerbotAI ai;Event e;CastConjureManaGemAction action(&ai);assert(!action.isPossible());assert(!action.Execute(e)&&ai.castCalls==0);
#ifdef MANGOSBOT_TWO
 ai.ids["conjure mana gem"]=759;assert(action.Execute(e)&&ai.last==759);ai.ids["conjure mana gem"]=42985;assert(action.Execute(e)&&ai.last==42985);
#else
 ai.ids["conjure mana agate"]=759;assert(action.Execute(e)&&ai.last==759);ai.ids["conjure mana ruby"]=10054;assert(action.Execute(e)&&ai.last==10054);
 ai.ids["conjure mana emerald"]=27101;
#ifdef MANGOSBOT_ONE
 assert(action.Execute(e)&&ai.last==27101);
#else
 assert(action.Execute(e)&&ai.last==10054);
#endif
#endif
 ai.ids.clear();assert(!action.Execute(e));ai.cheat=true;assert(!action.Execute(e));
}
''', 'mage unlearned/direct execution/rank changes/expansion gem selection', (f'MANGOSBOT_{expansion}',))

refresh = block(source('strategy/actions/GenericSpellActions.cpp'), 'void CastSpellAction::RefreshSpellId')
run(common + r'''
struct Context{uint32 id=0;std::string last;template<class T>struct Value{T value;T Get(){return value;}};template<class T>Value<T>* GetValue(std::string key,std::string){last=key;static Value<T> result;result.value=id;return &result;}};
struct PlayerbotAI{Context ctx;Context* GetAiObjectContext(){return &ctx;}};
struct CastSpellAction{PlayerbotAI* ai;uint32 spellId=0;std::string spellIdContext="spell id",spellName="test";void RefreshSpellId();};
''' + refresh + r'''
int main(){PlayerbotAI ai;CastSpellAction action{&ai};action.RefreshSpellId();assert(action.spellId==0);ai.ctx.id=50;action.RefreshSpellId();assert(action.spellId==50);ai.ctx.id=100;action.RefreshSpellId();assert(action.spellId==100);ai.ctx.id=0;action.RefreshSpellId();assert(action.spellId==0);action.spellIdContext="vehicle spell id";ai.ctx.id=200;action.RefreshSpellId();assert(action.spellId==200&&ai.ctx.last=="vehicle spell id");}
''', 'existing resolver refresh after learn/rank/remove and vehicle-context preservation')

wotf = block(source('strategy/triggers/GenericTriggers.h'), 'class WOtFTrigger') + ';'
run(common + r'''
enum{MAX_EFFECT_INDEX=3,SPELL_AURA_MECHANIC_IMMUNITY=77};
struct SpellEntry{int EffectApplyAuraName[3]={77,77,77};int EffectMiscValue[3]={5,10,1};}immunity;
struct Facade{const SpellEntry* LookupSpellInfo(uint32 id){return id?&immunity:nullptr;}}sServerFacade;
struct Holder{uint32 mask;uint32 GetId(){return 1;}bool HasMechanicMask(uint32 m){return mask&m;}};
bool IsPositiveSpell(uint32){return false;}
struct Player{bool ready=true;std::map<int,Holder*> holders;bool IsSpellReady(uint32){return ready;}auto& GetSpellAuraHolderMap(){return holders;}};
struct PlayerbotAI{uint32 id=7744;bool known=true;Player bot;bool HasSpell(uint32){return known;}};
struct Trigger{PlayerbotAI* ai;Player* bot;Trigger(PlayerbotAI* a,std::string):ai(a),bot(&a->bot){}virtual bool IsActive(){return false;}};
#define AI_VALUE2(type,key,name) (ai->id)
''' + wotf + r'''
int main(){PlayerbotAI ai;WOtFTrigger trigger(&ai);Holder holder{0};ai.bot.holders[1]=&holder;assert(!trigger.IsActive());for(int mechanic:{1,5,10}){holder.mask=1u<<(mechanic-1);assert(trigger.IsActive());}holder.mask=1u<<11;assert(!trigger.IsActive());holder.mask=1;ai.bot.ready=false;assert(!trigger.IsActive());ai.bot.ready=true;ai.known=false;assert(!trigger.IsActive());ai.known=true;ai.id=0;assert(!trigger.IsActive());}
''', 'racial immunity effects: fear/charm/sleep, not stun, and cooldown/unlearned guards')

boost = block(source('strategy/triggers/GenericTriggers.cpp'), 'bool BoostTrigger::IsActive')
run(common + r'''
enum class BotState{BOT_STATE_COMBAT};struct Player{bool ready=true;bool IsSpellReady(uint32){return ready;}};
struct PlayerbotAI{Player bot;uint32 id=10;bool known=true,combat=true,master=false;uint8 balance=50;bool HasSpell(uint32){return known;}bool IsStateActive(BotState){return combat;}bool HasRealPlayerMaster(){return master;}};
struct BuffTrigger{bool useful=true;bool IsActive(){return useful;}};
struct BoostTrigger:BuffTrigger{PlayerbotAI* ai;Player* bot;std::string spell="test";int balance=100;bool IsActive();};
#define AI_VALUE2(type,key,name) (ai->id)
#define AI_VALUE(type,key) (ai->balance)
''' + boost + r'''
int main(){PlayerbotAI ai;BoostTrigger trigger;trigger.ai=&ai;trigger.bot=&ai.bot;assert(trigger.IsActive());ai.bot.ready=false;assert(!trigger.IsActive());ai.bot.ready=true;ai.id=0;assert(!trigger.IsActive());ai.id=1;ai.known=false;assert(!trigger.IsActive());ai.known=true;ai.combat=false;assert(!trigger.IsActive());ai.combat=true;ai.balance=150;assert(!trigger.IsActive());ai.master=true;assert(trigger.IsActive());}
''', 'boost trigger cooldown/capability gating without changing combat or balance policy')

stealth = block(source('strategy/rogue/RogueActions.h'), 'class CastStealthAction') + ';'
run(common + r'''
enum class BotState{BOT_STATE_COMBAT,BOT_STATE_NON_COMBAT};enum{CURRENT_MELEE_SPELL};
struct Player{int interrupts=0;void InterruptSpell(int){++interrupts;}};
struct PlayerbotAI{Player bot;bool cast=false;int changes=0;bool HasAura(std::string,Player*){return false;}bool HasAura(int,Player*){return false;}bool CastSpell(std::string,Player*){return cast;}void ChangeStrategy(std::string,BotState){++changes;}};
struct CastBuffSpellAction{PlayerbotAI* ai;Player* bot;CastBuffSpellAction(PlayerbotAI* a,std::string):ai(a),bot(&a->bot){}virtual std::string GetTargetName(){return "self target";}virtual bool isUseful(){return true;}bool Execute(Event&){return ai->CastSpell("stealth",bot);}};
''' + stealth + r'''
int main(){PlayerbotAI ai;Event e;CastStealthAction action(&ai);assert(!action.Execute(e));assert(ai.changes==0&&ai.bot.interrupts==0);ai.cast=true;assert(action.Execute(e));assert(ai.changes==2&&ai.bot.interrupts==1);}
''', 'rogue stealth changes strategy only after a successful core cast')

# Source contracts complement native decision tests, not replace realm compilation.
dk = source('strategy/deathknight/DKActions.h')
assert '"scorgue strike"' not in dk and '"death coill"' not in dk
assert 'CastDarkCommandAction : public CastSpellAction' in dk
assert 'CastSummonGargoyleAction : public CastSpellAction' in dk
assert 'CastDancingWeaponAction : public CastSpellAction' in dk
assert '"pet target"' in block(dk, 'class CastGhoulFrenzyAction')
assert '"repentance or shield"]' in source('strategy/paladin/RetributionPaladinStrategy.cpp')
assert 'CastBuffSpellAction(ai, "barkskin")' in source('strategy/druid/DruidActions.h')
assert 'TRIGGERED_OLD_TRIGGERED' not in block(source('strategy/rogue/RogueActions.h'), 'class CastShadowstepAction')
print('PASS: class action registration/target/spell-name source contracts')
