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
#include <cmath>
#include <limits>
enum {TYPEID_DYNAMICOBJECT=1, DYNAMIC_OBJECT_AREA_SPELL=2, MAX_EFFECT_INDEX=3,
 SPELL_AURA_PERIODIC_DAMAGE=4, SPELL_AURA_PERIODIC_DAMAGE_PERCENT=5, SPELL_AURA_PERIODIC_LEECH=6,
 EFFECT_INDEX_0=0, SPELL_AURA_DUMMY=7, SPELL_EFFECT_SCHOOL_DAMAGE=8};
struct Map {};
struct WorldObject {
 Map* map=nullptr; bool world=true; int type=TYPEID_DYNAMICOBJECT;
 bool IsInWorld() const {return world;} Map* GetMap() const {return map;}
 int GetTypeId() const {return type;}
};
struct Unit:WorldObject {unsigned entry=17257;bool charmed=false;unsigned GetEntry(){return entry;}bool HasCharmer(){return charmed;}};
struct Player:WorldObject {unsigned mapId=544;unsigned GetMapId(){return mapId;}
 bool IsInMap(WorldObject* o){return world&&o&&o->world&&o->map==map;}};
struct SpellEntry {int EffectApplyAuraName[3]={SPELL_AURA_PERIODIC_DAMAGE,0,0};int Effect[3]={SPELL_EFFECT_SCHOOL_DAMAGE,0,0};};
struct Facade {SpellEntry spell,damage; bool found=true,damageFound=true;
 const SpellEntry* LookupSpellInfo(int id) {return id==30631 ? (damageFound?&damage:nullptr) : (found ? &spell : nullptr);}
} sServerFacade;
struct DynamicObject:WorldObject {
 int kind=DYNAMIC_OBJECT_AREA_SPELL, duration=5000, effect=0,spellId=1; float radius=8;Unit* caster=nullptr;
 bool enemy=true, attackable=true;
 int GetType() {return kind;} float GetRadius() {return radius;}
 int GetDuration() {return duration;} bool IsEnemy(Player*) {return enemy;}
 int GetSpellId() {return spellId;} int GetEffIndex() {return effect;}Unit* GetCaster(){return caster;}
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
 ground.radius=std::numeric_limits<float>::quiet_NaN();assert(!check(&ground));ground.radius=8;
 ground.enemy=false;assert(!check(&ground));ground.enemy=true;
 ground.attackable=false;assert(!check(&ground));ground.attackable=true;
 ground.effect=MAX_EFFECT_INDEX;assert(!check(&ground));ground.effect=0;
 sServerFacade.found=false;assert(!check(&ground));sServerFacade.found=true;
 sServerFacade.spell.EffectApplyAuraName[0]=99;assert(!check(&ground));
 sServerFacade.spell.EffectApplyAuraName[0]=SPELL_AURA_PERIODIC_DAMAGE_PERCENT;assert(check(&ground));
 sServerFacade.spell.EffectApplyAuraName[0]=SPELL_AURA_PERIODIC_LEECH;assert(check(&ground));
 Unit boss;boss.map=&first;ground.caster=&boss;ground.spellId=30632;
 sServerFacade.spell.EffectApplyAuraName[0]=SPELL_AURA_DUMMY;
#ifdef MANGOSBOT_ZERO
 assert(!check(&ground));
#else
 assert(check(&ground));ground.caster=nullptr;assert(!check(&ground));ground.caster=&boss;
 boss.entry=1;assert(!check(&ground));boss.entry=17257;boss.charmed=true;assert(!check(&ground));boss.charmed=false;
 boss.map=&second;assert(!check(&ground));boss.map=&first;
 ai.bot.mapId=1;assert(!check(&ground));ai.bot.mapId=544;ground.spellId=12345;assert(!check(&ground));ground.spellId=30632;
 sServerFacade.damageFound=false;assert(!check(&ground));sServerFacade.damageFound=true;
 sServerFacade.damage.Effect[0]=0;assert(!check(&ground));sServerFacade.damage.Effect[0]=SPELL_EFFECT_SCHOOL_DAMAGE;
 ground.attackable=false;assert(!check(&ground));ground.attackable=true;assert(check(&ground));
#endif
 std::cout<<"PASS: actual hazard lifetime, map/world validity, phase focus, hostile damage/native attack predicate\n";
}
'''.replace('__PREDICATES__', predicates).replace('__CHECK__', check)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-encounter-runtime-') as tmp:
        tmp = Path(tmp)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/W4',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp / 'test.exe')],cwd=tmp,check=True)

for era in ('tbc','wotlk'):
    native=(root.parents[2]/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland/hellfire_citadel/magtheridons_lair/boss_magtheridon.cpp').read_text()
    debris=block(native,'struct DebrisMagtheridon')
    assert 'OnPersistentAreaAuraEnd' in debris and '30631' in debris and 'dynGo->GetObjectGuid()' in debris

# Wiring checks supplement runtime tests; they are not encounter completion tests.
actions = (root / 'actions/KarazhanDungeonActions.cpp').read_text()
assert 'AddAura(' not in actions and 'RemoveAurasDueToSpell(' not in actions
for key in ('netherspite beam position','onyxia safe position','onyxia attack adds'):
    assert key in (root / 'actions/ActionContext.h').read_text()
assert 'hostile ground damage' in (root / 'triggers/TriggerContext.h').read_text()
assert 'GetMap()->IsDungeon()' in area and 'IsInCombat()' in area
print('PASS: encounter registration and native-only Netherspite action contracts')
