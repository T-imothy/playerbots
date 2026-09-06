"""Execute actual hazard predicates with controlled core objects, not a live raid."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1] / 'playerbot/strategy'
hazard = (root / 'values/HazardsValue.cpp').read_text()
area = (root / 'triggers/HostileGroundDamageTrigger.cpp').read_text()
predicates = '\n'.join(block(hazard, name) for name in (
    'bool Hazard::GetPosition(', 'bool Hazard::IsValid('))
check = block(area, 'struct HostileDamageAreaCheck') + ';'
code = r'''
#include <cassert>
#include <iostream>
#include <cstdint>
enum {TYPEID_DYNAMICOBJECT=1, DYNAMIC_OBJECT_AREA_SPELL=2, MAX_EFFECT_INDEX=3,
 SPELL_AURA_PERIODIC_DAMAGE=4, SPELL_AURA_PERIODIC_DAMAGE_PERCENT=5, SPELL_AURA_PERIODIC_LEECH=6};
struct Map {};
struct WorldObject {
 Map* map=nullptr; bool world=true; int type=TYPEID_DYNAMICOBJECT;
 bool IsInWorld() const {return world;} Map* GetMap() const {return map;}
 int GetTypeId() const {return type;}
};
struct Player:WorldObject {};
struct SpellEntry {int EffectApplyAuraName[3]={SPELL_AURA_PERIODIC_DAMAGE,0,0};};
struct Facade {SpellEntry spell; bool found=true;
 const SpellEntry* LookupSpellInfo(int) {return found ? &spell : nullptr;}
} sServerFacade;
struct DynamicObject:WorldObject {
 int kind=DYNAMIC_OBJECT_AREA_SPELL, duration=5000, effect=0; float radius=8;
 bool enemy=true, attackable=true;
 int GetType() {return kind;} float GetRadius() {return radius;}
 int GetDuration() {return duration;} bool IsEnemy(Player*) {return enemy;}
 int GetSpellId() {return 1;} int GetEffIndex() {return effect;}
 bool CanAttackSpell(Player*,const SpellEntry*,bool) {return attackable;}
};
struct WorldPosition {
 bool valid=false; const WorldObject* source=nullptr;
 WorldPosition()=default; WorldPosition(const WorldObject* o):valid(true),source(o){}
 explicit operator bool() const {return valid;}
};
struct Guid {bool empty=false;bool IsEmpty() const {return empty;}};
struct PlayerbotAI {Player bot;Player* GetBot(){return &bot;}};
struct Hazard {
 Guid guid; WorldPosition position; WorldObject* object=nullptr; bool expired=false;
 const WorldObject* GetObject(PlayerbotAI*) const {return object;}
 bool IsExpired() const {return expired;}
 bool GetPosition(PlayerbotAI*,WorldPosition&);
 bool IsValid(PlayerbotAI*) const;
};
__PREDICATES__
__CHECK__
int main() {
 Map first,second; PlayerbotAI ai; ai.bot.map=&first;
 Hazard hazard; WorldObject object; object.map=&first; hazard.object=&object;
 WorldPosition position; assert(hazard.IsValid(&ai));assert(hazard.GetPosition(&ai,position));
 hazard.object=nullptr;
 assert(!hazard.IsValid(&ai));assert(!hazard.GetPosition(&ai,position)); // cached point is NOT a live object
 hazard.guid.empty=true; assert(hazard.IsValid(&ai));assert(hazard.GetPosition(&ai,position));
 hazard.expired=true; assert(!hazard.IsValid(&ai));hazard.expired=false;
 hazard.guid.empty=false;hazard.object=&object;object.map=&second;assert(!hazard.IsValid(&ai));
 object.map=&first;object.world=false;assert(!hazard.IsValid(&ai));object.world=true;
 DynamicObject ground;ground.map=&first;HostileDamageAreaCheck check{&ai.bot};
 assert(&check.GetFocusObject()==&ai.bot);assert(check(&ground));assert(!check(nullptr));
 ground.world=false;assert(!check(&ground));ground.world=true;
 ground.map=&second;assert(!check(&ground));ground.map=&first;
 ground.type=99;assert(!check(&ground));ground.type=TYPEID_DYNAMICOBJECT;
 ground.kind=99;assert(!check(&ground));ground.kind=DYNAMIC_OBJECT_AREA_SPELL;
 ground.duration=0;assert(!check(&ground));ground.duration=-1;assert(!check(&ground));ground.duration=5000;
 ground.radius=0;assert(!check(&ground));ground.radius=26;assert(!check(&ground));ground.radius=8;
 ground.enemy=false;assert(!check(&ground));ground.enemy=true;
 ground.attackable=false;assert(!check(&ground));ground.attackable=true;
 ground.effect=MAX_EFFECT_INDEX;assert(!check(&ground));ground.effect=0;
 sServerFacade.found=false;assert(!check(&ground));sServerFacade.found=true;
 sServerFacade.spell.EffectApplyAuraName[0]=99;assert(!check(&ground));
 sServerFacade.spell.EffectApplyAuraName[0]=SPELL_AURA_PERIODIC_DAMAGE_PERCENT;assert(check(&ground));
 sServerFacade.spell.EffectApplyAuraName[0]=SPELL_AURA_PERIODIC_LEECH;assert(check(&ground));
 std::cout<<"PASS: actual hazard lifetime, map/world validity, phase focus, hostile damage/native attack predicate\n";
}
'''.replace('__PREDICATES__', predicates).replace('__CHECK__', check)
with tempfile.TemporaryDirectory(prefix='mantech-encounter-runtime-') as tmp:
    tmp = Path(tmp)
    (tmp / 'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/W4','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp / 'test.exe')],cwd=tmp,check=True)

# Wiring checks supplement runtime tests; they are not encounter completion tests.
actions = (root / 'actions/KarazhanDungeonActions.cpp').read_text()
assert 'AddAura(' not in actions and 'RemoveAurasDueToSpell(' not in actions
for key in ('netherspite beam position','onyxia safe position','onyxia attack adds'):
    assert key in (root / 'actions/ActionContext.h').read_text()
assert 'hostile ground damage' in (root / 'triggers/TriggerContext.h').read_text()
assert 'GetMap()->IsDungeon()' in area and 'IsInCombat()' in area
print('PASS: encounter registration and native-only Netherspite action contracts')
