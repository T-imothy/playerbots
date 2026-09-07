"""Verify exact native item slots, target kinds and consumption-safe dispatch."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/EncounterItemUse.cpp').read_text()
code=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
using uint32=unsigned;using uint8=uint8_t;
enum{EQUIP_ERR_OK=0,GAMEOBJECT_FLAGS,GO_FLAG_NO_INTERACT=4,GO_FLAG_IN_USE=1,MAX_ITEM_PROTO_SPELLS=5,ITEM_SPELLTRIGGER_ON_USE=0};
struct Unit{bool world=true,alive=true,player=false;unsigned phase=1;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsPlayer(){return player;}};
struct GameObject:Unit{bool spawned=true;unsigned flags=0;bool IsSpawned(){return spawned;}bool HasFlag(int,unsigned mask){return (flags&mask)!=0;}};
struct Slot{unsigned SpellId=0,SpellTrigger=0;};struct ItemPrototype{unsigned ItemId=0;Slot Spells[5];};
struct Item{unsigned owner=1,guid=2;bool trade=false,targetValid=true,consumed=false;ItemPrototype proto;
 unsigned GetOwnerGuid(){assert(!consumed);return owner;}unsigned GetObjectGuid(){assert(!consumed);return guid;}bool IsInTrade(){assert(!consumed);return trade;}
 const ItemPrototype*GetProto(){assert(!consumed);return &proto;}bool IsTargetValidForItemUse(Unit*){assert(!consumed);return targetValid;}};
struct SpellCastTargets{Unit*unit=nullptr;GameObject*object=nullptr;void setUnitTarget(Unit*u){unit=u;}void setGOTarget(GameObject*g){object=g;}};
struct Player:Unit{bool charm=false,teleport=false,casting=false;unsigned guid=1,casts=0,selected=999,error=0;Item*inventory=nullptr;SpellCastTargets last;
 Player(){player=true;}bool HasCharmer(){return charm;}bool IsBeingTeleported(){return teleport;}bool IsNonMeleeSpellCasted(bool){return casting;}
 unsigned GetObjectGuid(){return guid;}Item*GetItemByGuid(unsigned id){return inventory&&inventory->guid==id?inventory:nullptr;}
 unsigned CanUseItem(Item*){return error;}bool IsInMap(Unit*u){return u&&u->phase==phase;}
 void Used(Item*i,SpellCastTargets&t,unsigned pick){++casts;last=t;selected=pick;i->consumed=true;inventory=nullptr;}
 void CastItemUseSpell(Item*i,SpellCastTargets&t,uint8 slot){Used(i,t,slot);}
 void CastItemUseSpell(Item*i,SpellCastTargets&t,uint8 count,uint8 slot){assert(count==0);Used(i,t,slot);}
 void CastItemUseSpell(Item*i,SpellCastTargets&t,uint8 count,unsigned glyph,unsigned spell){assert(count==0&&glyph==0);Used(i,t,spell);}};
namespace ai{bool IsNativeEncounterItem(uint32);bool UseNativeEncounterItem(Player*,Item*,Unit*,GameObject*);}
__METHODS__
int main(){Player bot,receiver;GameObject generator;
 for(unsigned id:{19183u,24494u,31088u,32408u})for(bool object:{false,true}){
  if(object&&id!=31088)continue;
  Item item;item.proto.ItemId=id;bot.inventory=&item;unsigned spell=id==19183?23645:id==24494?32028:id==32408?39948:object?3366:38134;
  // Deliberately place the selected spell outside slot zero.
  item.proto.Spells[0].SpellId=38132;item.proto.Spells[3].SpellId=spell;
  Unit*target=id==19183||id==24494?nullptr:object?nullptr:&receiver;
  unsigned before=bot.casts;assert(ai::UseNativeEncounterItem(&bot,&item,target,object?&generator:nullptr));
  assert(bot.casts==before+1&&item.consumed&&bot.inventory==nullptr);
#ifdef MANGOSBOT_TWO
  assert(bot.selected==spell);
#else
  assert(bot.selected==3);
#endif
  assert(bot.last.object==(object?&generator:nullptr));
  assert(bot.last.unit==(object?nullptr:target?target:&bot));
 }
 Item core;core.proto.ItemId=31088;core.proto.Spells[0].SpellId=38134;core.proto.Spells[1].SpellId=3366;bot.inventory=&core;
 assert(!ai::UseNativeEncounterItem(&bot,&core,&bot,nullptr)); // No self-throw fallback.
 assert(!ai::UseNativeEncounterItem(&bot,&core,nullptr,nullptr));
 assert(!ai::UseNativeEncounterItem(&bot,&core,&receiver,&generator));
 Unit creature;assert(!ai::UseNativeEncounterItem(&bot,&core,&creature,nullptr));
 core.owner=99;assert(!ai::UseNativeEncounterItem(&bot,&core,&receiver,nullptr));core.owner=1;
 bot.inventory=nullptr;assert(!ai::UseNativeEncounterItem(&bot,&core,&receiver,nullptr));bot.inventory=&core;
 core.trade=true;assert(!ai::UseNativeEncounterItem(&bot,&core,&receiver,nullptr));core.trade=false;
 core.targetValid=false;assert(!ai::UseNativeEncounterItem(&bot,&core,&receiver,nullptr));core.targetValid=true;
 receiver.phase=2;assert(!ai::UseNativeEncounterItem(&bot,&core,&receiver,nullptr));receiver.phase=1;
 bot.casting=true;assert(!ai::UseNativeEncounterItem(&bot,&core,&receiver,nullptr));bot.casting=false;
 bot.teleport=true;assert(!ai::UseNativeEncounterItem(&bot,&core,&receiver,nullptr));bot.teleport=false;
 generator.flags=GO_FLAG_NO_INTERACT;assert(!ai::UseNativeEncounterItem(&bot,&core,nullptr,&generator));generator.flags=0;
 generator.spawned=false;assert(!ai::UseNativeEncounterItem(&bot,&core,nullptr,&generator));generator.spawned=true;
 core.proto.Spells[1].SpellTrigger=1;assert(!ai::UseNativeEncounterItem(&bot,&core,nullptr,&generator));core.proto.Spells[1].SpellTrigger=0;
 assert(ai::UseNativeEncounterItem(&bot,&core,nullptr,&generator));
 assert(!ai::IsNativeEncounterItem(13444)&&ai::IsNativeEncounterItem(31088));
 std::cout<<"PASS: one native slot/ID per use, exact targets, real inventory, consumption and lifecycle\n";
}
'''
methods='\n'.join(block(source,name) for name in ('bool ai::IsNativeEncounterItem(', 'bool ai::UseNativeEncounterItem('))
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='native-encounter-item-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code.replace('__METHODS__',methods))
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
use=block((root/'playerbot/strategy/actions/UseItemAction.cpp').read_text(),'bool UseAction::UseItemInternal(')
assert use.index('HasItemCooldown(itemId)')<use.index('UseNativeEncounterItem(bot, itemUsed, unit, gameObject)')<use.index('for (uint8 i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)')
