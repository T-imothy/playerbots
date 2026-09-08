"""Compile production potion cache/selection and inventory matching bodies."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]/'playerbot'
cache=(root/'RandomItemMgr.cpp').read_text();visitors=(root/'strategy/ItemVisitors.h').read_text()
code=r"""
#include <cassert>
#include <cstdint>
#include <vector>
#include <map>
#include <algorithm>
using uint32=uint32_t;
enum {SPELL_EFFECT_HEAL=10,SPELL_EFFECT_ENERGIZE=30,POWER_MANA=0,MAX_ITEM_PROTO_SPELLS=5,ITEM_CLASS_CONSUMABLE=0,ITEM_SUBCLASS_POTION=1,ITEM_SUBCLASS_FLASK=4,NO_BIND=0,CONFIG_UINT32_MAX_PLAYER_LEVEL=0};
struct SpellEntry {uint32 Effect[3]={},EffectMiscValue[3]={};};
struct ItemSpell {uint32 SpellId=0;};
struct ItemPrototype {uint32 ItemId=0,Class=0,SubClass=1,Bonding=0,RequiredLevel=0,RequiredSkill=0,Area=0,Map=0,RequiredCityRank=0,RequiredHonorRank=0,Duration=0;ItemSpell Spells[5];};
struct ObjectMgr {std::map<uint32,ItemPrototype> items;const ItemPrototype* GetItemPrototype(uint32 id){auto i=items.find(id);return i==items.end()?nullptr:&i->second;}}sObjectMgr;
struct Storage {uint32 GetMaxEntry(){return 20;}}sItemStorage;
struct Facade {std::map<uint32,SpellEntry> spells;const SpellEntry* LookupSpellInfo(uint32 id){auto i=spells.find(id);return i==spells.end()?nullptr:&i->second;}}sServerFacade;
struct Config {uint32 randomBotMaxLevel=80;}sPlayerbotAIConfig;
struct World {uint32 maximum=80;uint32 getConfig(int){return maximum;}}sWorld;
struct Log {template<class...T>void outBasic(const char*,T...){}template<class...T>void outDetail(const char*,T...){}template<class...T>void outString(const char*,T...){}}sLog;
uint32 urand(uint32 low,uint32 high){static uint32 n=0;return low+(n++%(high-low+1));}
struct RandomItemMgr {std::map<uint32,std::map<uint32,std::vector<uint32>>> potionCache;void BuildPotionCache();uint32 GetRandomPotion(uint32,uint32);};
struct FindPotionVisitor {uint32 effectId;explicit FindPotionVisitor(uint32 e):effectId(e){}bool Accept(const ItemPrototype*);};
"""
code+=block(cache,'void RandomItemMgr::BuildPotionCache()')+'\n'+block(cache,'uint32 RandomItemMgr::GetRandomPotion(uint32 level, uint32 effect)')+'\n'
body=block(block(visitors,'class FindPotionVisitor'),'bool Accept(const ItemPrototype* proto)').replace('bool Accept(const ItemPrototype* proto) override','bool FindPotionVisitor::Accept(const ItemPrototype* proto)')
code+=body+r"""
int main(){
#ifdef MANGOSBOT_ZERO
 sWorld.maximum=60;
#elif defined(MANGOSBOT_ONE)
 sWorld.maximum=70;
#else
 sWorld.maximum=80;
#endif
 sServerFacade.spells[101]={{SPELL_EFFECT_ENERGIZE,0,0},{POWER_MANA,0,0}};
 sServerFacade.spells[102]={{SPELL_EFFECT_ENERGIZE,0,0},{1,0,0}}; // rage
 sServerFacade.spells[103]={{SPELL_EFFECT_ENERGIZE,0,0},{3,0,0}}; // energy
 sServerFacade.spells[104]={{SPELL_EFFECT_HEAL,0,0},{0,0,0}};
 sServerFacade.spells[105]={{SPELL_EFFECT_HEAL,SPELL_EFFECT_ENERGIZE,0},{0,POWER_MANA,0}};
 auto add=[](uint32 id,uint32 level,uint32 spell){ItemPrototype p;p.ItemId=id;p.RequiredLevel=level;p.Spells[0].SpellId=spell;sObjectMgr.items[id]=p;};
 add(1,5,101);add(2,14,101);add(3,4,102);add(4,0,103);add(5,0,104);add(6,35,105);
 add(7,5,0);sObjectMgr.items[7].Spells[1].SpellId=101;
 add(8,5,101);sObjectMgr.items[8].Class=2;
 add(9,5,101);sObjectMgr.items[9].RequiredSkill=171;
 add(10,5,101);sObjectMgr.items[10].Area=1;
 add(11,65,101);add(12,22,101);
 FindPotionVisitor mana(SPELL_EFFECT_ENERGIZE),healing(SPELL_EFFECT_HEAL);
 assert(mana.Accept(&sObjectMgr.items[1]));assert(!mana.Accept(&sObjectMgr.items[3]));assert(!mana.Accept(&sObjectMgr.items[4]));
 assert(mana.Accept(&sObjectMgr.items[6])&&healing.Accept(&sObjectMgr.items[6]));assert(mana.Accept(&sObjectMgr.items[7]));assert(!mana.Accept(&sObjectMgr.items[8]));
 RandomItemMgr mgr;mgr.BuildPotionCache();
 assert(mgr.GetRandomPotion(0,SPELL_EFFECT_ENERGIZE)==0);
 auto contains=[&](uint32 level,uint32 id){auto v=mgr.potionCache[(level-1)/10][SPELL_EFFECT_ENERGIZE];return std::find(v.begin(),v.end(),id)!=v.end();};
 assert(contains(5,1)&&contains(5,7));assert(contains(14,2));assert(contains(22,12));
 for(uint32 level=1;level<=sWorld.maximum;++level){
  for(int i=0;i<20;++i){uint32 id=mgr.GetRandomPotion(level,SPELL_EFFECT_ENERGIZE);
   if(level<5){assert(id==0);continue;}
   if(id){const auto* p=sObjectMgr.GetItemPrototype(id);assert(p&&p->RequiredLevel<=level&&mana.Accept(p));assert(id!=3&&id!=4&&id!=8&&id!=9&&id!=10);}
  }
 }
 for(uint32 level=1;level<5;++level)assert(mgr.GetRandomPotion(level,SPELL_EFFECT_HEAL)==5);
}
"""
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mana-cache-') as temp:
  p=Path(temp);(p/'test.cpp').write_text(code)
  result=subprocess.run(['cl','/nologo','/std:c++20','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
 print('PASS potion cache and inventory: mana versus rage/energy, sparse spell slots, level 5/14/22 boundaries and native era level caps',era,flush=True)
