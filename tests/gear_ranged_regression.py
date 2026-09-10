"""Run the production ranged level filter, ammo preparation and gear entrypoints."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/PlayerbotFactory.cpp').read_text()
header=(root/'playerbot/PlayerbotFactory.h').read_text()
start=source.index('                    const bool rangedUtility =')
end=source.index('                    // filter tank weapons',start)
selection=source[start:end]
code=r'''
#include <cassert>
#include <map>
#include <iostream>
#include <string>
using uint32=unsigned;
enum {CLASS_WARRIOR=1,CLASS_ROGUE=4,CLASS_HUNTER=3,CLASS_PRIEST=5,EQUIPMENT_SLOT_RANGED=17,
 INVENTORY_SLOT_BAG_0=0,ITEM_CLASS_WEAPON=2,ITEM_CLASS_PROJECTILE=6,
 ITEM_SUBCLASS_WEAPON_BOW=2,ITEM_SUBCLASS_WEAPON_GUN=3,ITEM_SUBCLASS_WEAPON_CROSSBOW=18,
 ITEM_SUBCLASS_WEAPON_THROWN=16,ITEM_SUBCLASS_BULLET=3,ITEM_SUBCLASS_ARROW=2,ITEM_SUBCLASS_THROWN=4,
 ITEM_QUALITY_LEGENDARY=5,PLAYER_AMMO_ID=0,PERF_MON_RNDBOT=0};
struct Config{int randomGearMaxDiff=5;bool randomGearProgression=true;}sPlayerbotAIConfig;
struct ItemPrototype{unsigned Class=ITEM_CLASS_WEAPON,SubClass=ITEM_SUBCLASS_WEAPON_BOW,RequiredLevel=20,Quality=3;};
struct Item{ItemPrototype proto;ItemPrototype*GetProto(){return &proto;}};
struct Player{unsigned cls=CLASS_WARRIOR,level=33,ammo=0;bool equipped=true;Item ranged;std::map<unsigned,unsigned>items;
 unsigned getClass(){return cls;}unsigned GetLevel(){return level;}Item*GetItemByPos(int,int){return equipped?&ranged:nullptr;}
 unsigned GetUInt32Value(int){return ammo;}unsigned GetItemCount(unsigned id){return items[id];}void SetAmmo(unsigned id){ammo=id;}};
struct Objects{std::map<unsigned,ItemPrototype>items;ItemPrototype*GetItemPrototype(unsigned id){auto it=items.find(id);return it==items.end()?nullptr:&it->second;}}sObjectMgr;
struct Random{unsigned GetAmmo(unsigned,unsigned sub){return sub==ITEM_SUBCLASS_ARROW?100:sub==ITEM_SUBCLASS_BULLET?200:0;}}sRandomItemMgr;
enum class BotCheatMask{item};
struct AI{bool HasCheat(BotCheatMask){return false;}};
struct Monitor{int start(int,const char*){return 0;}}sPerformanceMonitor;
struct PlayerbotFactory{Player*bot;AI*ai;unsigned level;bool supplyFailed=false;unsigned equips=0,gems=0,stores=0;
 void InitEquipment(bool,bool,bool=true,bool=false){++equips;}void InitGems(){++gems;}
 Item*StoreSupplyItem(unsigned id,unsigned count){++stores;bot->items[id]+=count;return &bot->ranged;}
 void InitAmmo();
 __ENTRYPOINTS__
};
bool acceptedByLevelGap(Player*bot,ItemPrototype*proto,unsigned slot,unsigned reqLevel){
 for(int once=0;once<1;++once){__FILTER__ return true;}return false;
}
__AMMO__
int main(){
 Player bot;ItemPrototype bow;
 // Exact production failure: level 33, five-level gap, cached bows at 20/27.
 for(unsigned req:{20u,27u})assert(acceptedByLevelGap(&bot,&bow,17,req));
 bot.cls=CLASS_ROGUE;assert(acceptedByLevelGap(&bot,&bow,17,20));
 bot.cls=CLASS_HUNTER;assert(!acceptedByLevelGap(&bot,&bow,17,27));
 bot.cls=CLASS_WARRIOR;assert(!acceptedByLevelGap(&bot,&bow,15,27));
 assert(acceptedByLevelGap(&bot,&bow,15,28));
 bow.Class=4;assert(!acceptedByLevelGap(&bot,&bow,17,27));bow.Class=2;
 bow.SubClass=19;assert(!acceptedByLevelGap(&bot,&bow,17,27));bow.SubClass=2;
 sObjectMgr.items[100]={ITEM_CLASS_PROJECTILE,ITEM_SUBCLASS_ARROW,10,1};
 sObjectMgr.items[200]={ITEM_CLASS_PROJECTILE,ITEM_SUBCLASS_BULLET,10,1};
 AI ai;PlayerbotFactory f{&bot,&ai,33};
 f.EquipGear();assert(f.equips==1&&f.gems==1&&bot.ammo==100&&bot.items[100]>0);
 // A reroll from bow to gun must not retain stocked arrows.
 bot.ranged.proto.SubClass=ITEM_SUBCLASS_WEAPON_GUN;f.EquipGearBest();
 assert(bot.ammo==200&&bot.items[200]>0&&f.equips==2);
 auto stores=f.stores;f.EquipGearPartialUpgrade();f.UpgradeGear(false);f.UpgradeGear(true);
 assert(f.equips==5&&f.stores==stores);
 // A now-unusable high-level ammo choice must be replaced after level sync.
 sObjectMgr.items[300]={ITEM_CLASS_PROJECTILE,ITEM_SUBCLASS_BULLET,60,1};bot.ammo=300;bot.items[300]=2000;
 f.InitAmmo();assert(bot.ammo==200);
 bot.equipped=false;stores=f.stores;f.InitAmmo();assert(f.stores==stores);
 bot.equipped=true;bot.cls=CLASS_PRIEST;f.InitAmmo();assert(f.stores==stores);
 std::cout<<"PASS ranged utility gaps, unchanged other slots/classes, all gear entrypoints, ammo swap and level sync\n";
}
'''
entrypoints='\n'.join(block(header,'    void '+name) for name in ('EquipGear()','EquipGearBest()','EquipGearPartialUpgrade()','UpgradeGear(bool'))
code=code.replace('__ENTRYPOINTS__',entrypoints).replace('__FILTER__',selection).replace('__AMMO__',block(source,'void PlayerbotFactory::InitAmmo()'))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='ranged-gear-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
