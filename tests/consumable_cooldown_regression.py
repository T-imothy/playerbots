"""Compile native cooldown dispatch with controlled receivers (no running realm).

Run in an MSVC developer shell with --core PATH and --wrath for Wrath.
Tests item-free and real-item dispatch, ordinary spells, category overrides,
and Wrath's combat-end event retaining the original potion item ID.
"""
from pathlib import Path
import argparse, subprocess, tempfile
from behavior_regression import block

p=argparse.ArgumentParser()
p.add_argument('--core', type=Path, required=True)
p.add_argument('--wrath', action='store_true')
a=p.parse_args()
root=Path(__file__).resolve().parents[1]/'playerbot/strategy/actions'
header=(root/'UseItemAction.h').read_text()
use=(root/'UseItemAction.cpp').read_text()
core=(a.core/'src/game/Spells/Spell.cpp').read_text()
assert use.index('spell->SetCooldownItemPrototype(proto)') < use.index('spell->ForceSpellStart(&targets)')
assert 'if (!HasItemCooldown(itemId))' not in use
prefix=r'''
#include <cassert>
#include <cstdint>
#include <map>
using uint32=uint32_t;using uint8=uint8_t;
enum { SPELL_ATTR_COOLDOWN_ON_EVENT=1, SPELL_ATTR_PASSIVE=2, TYPEID_PLAYER=1,
       SMSG_SPELL_COOLDOWN=1, SPELL_COOLDOWN_FLAG_NONE=0,
       ITEM_CLASS_CONSUMABLE=0, ITEM_SUBCLASS_POTION=1 };
enum class SpellCategoryFlags { CooldownEventOnLeaveCombat=4 };
struct ItemSpell { uint32 SpellId,SpellCategory; int SpellCooldown,SpellCategoryCooldown; };
struct ItemPrototype { uint32 ItemId,Class=0,SubClass=1; ItemSpell Spells[1]; };
struct Item { ItemPrototype const* proto; auto GetProto()const{return proto;} uint32 GetEntry()const{return proto->ItemId;} };
struct SpellEntry { uint32 Id,Category,flags=0; bool HasAttribute(uint32 f)const{return flags&f;} };
struct SpellCategoryEntry { uint32 flags; };
struct Categories { std::map<uint32,SpellCategoryEntry> rows; auto LookupEntry(uint32 id)const { auto i=rows.find(id);return i==rows.end()?nullptr:&i->second; } } sSpellCategory;
struct ObjectMgr { static std::map<uint32,ItemPrototype> rows;static ItemPrototype const* GetItemPrototype(uint32 id){auto i=rows.find(id);return i==rows.end()?nullptr:&i->second;} };
std::map<uint32,ItemPrototype> ObjectMgr::rows;
struct SpellStore { std::map<uint32,SpellEntry> rows; template<class T> T const* LookupEntry(uint32 id){auto i=rows.find(id);return i==rows.end()?nullptr:&i->second;} } sSpellTemplate;
struct WorldPacket { WorldPacket(int,int){} template<class T>WorldPacket& operator<<(T){return *this;} };
struct Session { void SendPacket(WorldPacket*){} void SendPacket(WorldPacket const&){} };
struct Spell;
struct Player {
  ItemPrototype const* received=nullptr;bool held=false,combat=true;unsigned calls=0;
  uint32 m_lastPotionId=0,m_triggerCoooldownOnLeaveCombatSpellId=0;
  bool IsPlayer(){return true;}int GetTypeId(){return TYPEID_PLAYER;}int GetObjectGuid(){return 1;}
  Session* GetSession(){static Session s;return &s;}
  void AddCooldown(SpellEntry const&,ItemPrototype const* p=nullptr,bool permanent=false){received=p;held=permanent;++calls;}
  void SetLastPotionId(uint32 id){m_lastPotionId=id;}
  void SetCooldownEventOnLeaveCombatSpellId(uint32 id){m_triggerCoooldownOnLeaveCombatSpellId=id;}
  bool IsInCombat(){return combat;}
  void UpdatePotionCooldown(Spell* spell=nullptr);
};
struct Spell {
  Item* m_CastItem=nullptr;Player* m_trueCaster;Player* m_caster;
  SpellEntry const* m_spellInfo;bool m_channelOnly=false;
  Spell(Player* p,SpellEntry const* s):m_trueCaster(p),m_caster(p),m_spellInfo(s){}
  virtual ~Spell()=default;
  virtual ItemPrototype const* GetCooldownItemPrototype()const;
  void SendSpellCooldown();
};
'''
derived='struct BotUseItemSpell : Spell { using Spell::Spell; ItemPrototype const* cooldownItemPrototype=nullptr;\n'
derived+=block(header,'void SetCooldownItemPrototype(')+'\n'
derived+=block(header,'ItemPrototype const* GetCooldownItemPrototype() const override')+'\n};\n'
code=prefix+derived+block(core,'ItemPrototype const* Spell::GetCooldownItemPrototype() const')+'\n'+block(core,'void Spell::SendSpellCooldown()')
if a.wrath:
    code+='\n'+block((a.core/'src/game/Entities/Player.cpp').read_text(),'void Player::UpdatePotionCooldown(')
code+=r'''
int main(){
  SpellEntry healing{17534,4},mana{17531,4},rune{27869,30};
  ItemPrototype healItem{13446,0,1,{{17534,4,120000,120000}}};
  ItemPrototype manaItem{13444,0,1,{{17531,4,120000,120000}}};
  ItemPrototype runeItem{20520,0,5,{{27869,1153,0,120000}}};
  // All three spell-only cooldowns differ from item metadata in live Classic/TBC.
  for(auto pair : {std::pair<SpellEntry*,ItemPrototype*>{&healing,&healItem},{&mana,&manaItem},{&rune,&runeItem}}){
    Player owner;BotUseItemSpell cast(&owner,pair.first);cast.SetCooldownItemPrototype(pair.second);
    cast.SendSpellCooldown();assert(owner.calls==1 && owner.received==pair.second && !owner.held);
    Player realOwner;Item real{pair.second};Spell realCast(&realOwner,pair.first);realCast.m_CastItem=&real;
    realCast.SendSpellCooldown();assert(realOwner.received==owner.received && realOwner.held==owner.held);
  }
  Player owner;Spell normal(&owner,&healing);normal.SendSpellCooldown();assert(owner.received==nullptr);
  unsigned before=owner.calls;normal.m_channelOnly=true;normal.SendSpellCooldown();assert(owner.calls==before);
'''
if a.wrath:
    code+=r'''
  // Native potion category holds the cooldown during combat. The item ID must
  // survive until exit so the full item duration is restored, not spell 10s.
  sSpellCategory.rows[4]={4};healItem.Spells[0].SpellCooldown=0;
  healItem.Spells[0].SpellCategoryCooldown=60000;
  ObjectMgr::rows[healItem.ItemId]=healItem;sSpellTemplate.rows[healing.Id]=healing;
  Player wrath;BotUseItemSpell potion(&wrath,&healing);potion.SetCooldownItemPrototype(&healItem);
  potion.SendSpellCooldown();assert(wrath.held && wrath.received==&healItem);
  assert(wrath.m_lastPotionId==13446 && wrath.m_triggerCoooldownOnLeaveCombatSpellId==17534);
  wrath.UpdatePotionCooldown();assert(wrath.calls==1 && wrath.held);
  wrath.combat=false;wrath.UpdatePotionCooldown();assert(wrath.calls==2 && !wrath.held);
  assert(wrath.received && wrath.received->ItemId==13446 && wrath.received->Spells[0].SpellCategoryCooldown==60000);
  assert(wrath.m_lastPotionId==0 && wrath.m_triggerCoooldownOnLeaveCombatSpellId==0);
  wrath.UpdatePotionCooldown();assert(wrath.calls==2);
  rune.Category=0;runeItem.Spells[0].SpellCooldown=900000;
  Player runes;BotUseItemSpell darkRune(&runes,&rune);darkRune.SetCooldownItemPrototype(&runeItem);
  darkRune.SendSpellCooldown();assert(!runes.held && runes.received->Spells[0].SpellCooldown==900000);
  assert(runes.received->Spells[0].SpellCategory==1153);
  // Item category overrides the spell category before deciding combat hold.
  SpellEntry overrideSpell{999,30};ItemPrototype overrideItem{999,0,1,{{999,4,0,60000}}};
  Player overridden;BotUseItemSpell overrideCast(&overridden,&overrideSpell);overrideCast.SetCooldownItemPrototype(&overrideItem);
  overrideCast.SendSpellCooldown();assert(overridden.held && overridden.m_lastPotionId==999);
'''
code+='\n}\n'
with tempfile.TemporaryDirectory() as d:
    d=Path(d);(d/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/W4','test.cpp','/Fe:test.exe'],cwd=d,check=True)
    subprocess.run([str(d/'test.exe')],check=True)
print('PASS native item cooldown dispatch:',a.core.name)
