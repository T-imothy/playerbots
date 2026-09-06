"""Actual pet feasibility/dispatch with controlled native CheckCast outcomes.

This tests AI admission, not actual server spell execution or pet path success.
Each core's native handler and flags are checked for the APIs being reused.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/PlayerbotAI.cpp').read_text()
methods = '\n'.join(block(source, marker) for marker in
                    ('bool PlayerbotAI::CanCastPetSpell(', 'bool PlayerbotAI::CastPetSpell('))
unit = block(source, 'bool PlayerbotAI::CanCastSpell(uint32 spellid, Unit* target,')
assert 'return CanCastPetSpell(spellid, target ? target : bot, checkResult);' in unit
for marker in ('bool PlayerbotAI::CanCastSpell(uint32 spellid, GameObject*',
               'bool PlayerbotAI::CanCastSpell(uint32 spellid, float',
               'bool PlayerbotAI::CastSpell(uint32 spellId, float'):
    method = block(source, marker)
    pet = block(method, 'if (pet && pet->HasSpell(')
    assert 'return false;' in pet and 'return true;' not in pet and 'CastPetSpell' not in pet

code = r'''
#include <cassert>
#include <iostream>
#include <vector>
#include <set>
using uint32=unsigned;using uint8=unsigned char;
enum SpellCastResult {SPELL_CAST_OK,SPELL_FAILED_NOT_KNOWN,SPELL_FAILED_CASTER_DEAD,
 SPELL_FAILED_NOT_IN_CONTROL,SPELL_FAILED_NOT_READY,SPELL_FAILED_SPELL_IN_PROGRESS,
 SPELL_FAILED_BAD_TARGETS,SPELL_FAILED_UNIT_NOT_INFRONT,SPELL_FAILED_NOT_INFRONT,
 SPELL_FAILED_OUT_OF_RANGE,SPELL_FAILED_LINE_OF_SIGHT,SPELL_FAILED_NO_POWER,
 SPELL_FAILED_STUNNED,SPELL_FAILED_IMMUNE};
enum {SPELL_ATTR_EX4_ALLOW_CAST_WHILE_CASTING=1,UNIT_STAT_POSSESSED=2,
 TARGET_ENUM_UNITS_ENEMY_AOE_AT_SRC_LOC=3,TARGET_ENUM_UNITS_ENEMY_AOE_AT_DEST_LOC=4,
 TARGET_ENUM_UNITS_ENEMY_AOE_AT_DYNOBJ_LOC=5,TRIGGERED_NORMAL_COMBAT_CAST=0x100,
 TRIGGERED_PET_CAST=0x80,ACT_PASSIVE=1,ACT_ENABLED=0xc1,ACT_DISABLED=0x81,CMSG_PET_ACTION=7};
struct ObjectGuid {unsigned id=0;ObjectGuid(unsigned i=0):id(i){}bool operator!=(ObjectGuid o)const{return id!=o.id;}};
struct Unit {bool world=true,alive=true;unsigned map=1,phase=1;ObjectGuid guid{1};
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}ObjectGuid GetObjectGuid(){return guid;}
 bool IsInMap(Unit* u){return world&&u&&u->world&&map==u->map&&phase==u->phase;}};
struct SpellEntry {unsigned rangeIndex=1,EffectImplicitTargetA[3]{};bool passive=false,positive=false,need=true,allowConcurrent=false;
 bool HasAttribute(unsigned)const{return allowConcurrent;}} entry;
struct Facade {bool exists=true;const SpellEntry* LookupSpellInfo(unsigned){return exists?&entry:nullptr;}} sServerFacade;
struct RangeStore {bool exists=true;const int* LookupEntry(unsigned){static int i=1;return exists?&i:nullptr;}} sSpellRangeStore;
bool IsPassiveSpell(const SpellEntry* s){return s->passive;}
bool IsSpellRequireTarget(const SpellEntry* s){return s->need;}
bool IsPositiveSpell(const SpellEntry* s,Unit*,Unit*){return s->positive;}
struct CreatureAI {bool scripted=false;bool GetCombatScriptStatus(){return scripted;}};
using AutoSpellList=std::vector<unsigned>;
struct Pet:Unit {ObjectGuid master{1};bool known=true,ready=true,disabled=false,casting=false,possessed=false,
 assist=true,attack=true,attackNow=true,charm=true,hasAI=true;CreatureAI nativeAI;AutoSpellList m_autospells;
 bool HasSpell(unsigned){return known;}bool IsSpellReady(unsigned){return ready;}
 ObjectGuid GetMasterGuid(){return master;}void* GetCharmInfo(){return charm?this:nullptr;}
 bool HasActionsDisabled(){return disabled;}CreatureAI* AI(){return hasAI?&nativeAI:nullptr;}
 bool IsNonMeleeSpellCasted(bool){return casting;}bool hasUnitState(unsigned){return possessed;}
 bool CanAssistSpell(Unit*,const SpellEntry*){return assist;}bool CanAttack(Unit*){return attack;}
 bool CanAttackNow(Unit*){return attackNow;}};
struct WorldPacket {unsigned opcode;std::vector<unsigned> values;WorldPacket(unsigned o):opcode(o){}
 WorldPacket& operator<<(ObjectGuid g){values.push_back(g.id);return *this;}
 WorldPacket& operator<<(unsigned v){values.push_back(v);return *this;}};
struct Session {unsigned calls=0;std::vector<unsigned> values;void HandlePetAction(WorldPacket& p){assert(p.opcode==CMSG_PET_ACTION);++calls;values=p.values;}};
struct Player:Unit {Pet* pet=nullptr;bool teleport=false;Session session;Pet* GetPet(){return pet;}
 bool IsBeingTeleported(){return teleport;}Session* GetSession(){return &session;}};
bool autocast=false;bool IsAutocastable(unsigned){return autocast;}
bool encounterPause=false;
namespace ai {bool ShouldAvoidEncounterOffense(Player*,Unit* caster,const SpellEntry* spell,Unit*){return caster&&spell&&encounterPause&&!spell->positive;}}
struct Spell {static unsigned checks,constructions,lastFlags;static SpellCastResult result;static Unit* checkedTarget;
 struct Targets{Unit* unit=nullptr;void setUnitTarget(Unit* u){unit=u;}}m_targets;
 Spell(Pet*,const SpellEntry*,unsigned flags){++constructions;lastFlags=flags;}
 SpellCastResult CheckCast(bool strict){assert(strict);++checks;checkedTarget=m_targets.unit;return result;}};
unsigned Spell::checks=0,Spell::constructions=0,Spell::lastFlags=0;Unit* Spell::checkedTarget=nullptr;
SpellCastResult Spell::result=SPELL_CAST_OK;
struct PlayerbotAI{Player* bot;bool CanCastPetSpell(unsigned,Unit*,SpellCastResult* =nullptr);bool CastPetSpell(unsigned,Unit*);};
__METHODS__
int main(){
 Player bot;Pet pet;Unit target;bot.pet=&pet;pet.guid=2;target.guid=3;PlayerbotAI ai{&bot};SpellCastResult result;
 assert(ai.CanCastPetSpell(1,&target,&result)&&result==SPELL_CAST_OK&&Spell::checkedTarget==&target);
 assert(Spell::lastFlags==(TRIGGERED_NORMAL_COMBAT_CAST|TRIGGERED_PET_CAST)&&bot.session.calls==0);
 auto rejected=[&](SpellCastResult expected){unsigned before=Spell::checks;assert(!ai.CanCastPetSpell(1,&target,&result)&&result==expected&&before==Spell::checks);assert(!ai.CastPetSpell(1,&target)&&bot.session.calls==0);};
 pet.ready=false;rejected(SPELL_FAILED_NOT_READY);pet.ready=true;
 pet.known=false;rejected(SPELL_FAILED_NOT_KNOWN);pet.known=true;
 entry.passive=true;rejected(SPELL_FAILED_NOT_KNOWN);entry.passive=false;
 pet.alive=false;rejected(SPELL_FAILED_CASTER_DEAD);pet.alive=true;
 bot.alive=false;rejected(SPELL_FAILED_CASTER_DEAD);bot.alive=true;
 bot.teleport=true;rejected(SPELL_FAILED_CASTER_DEAD);bot.teleport=false;
 pet.world=false;rejected(SPELL_FAILED_CASTER_DEAD);pet.world=true;
 pet.map=2;rejected(SPELL_FAILED_NOT_IN_CONTROL);pet.map=1;
 pet.master=99;rejected(SPELL_FAILED_NOT_IN_CONTROL);pet.master=1;
 pet.charm=false;rejected(SPELL_FAILED_NOT_IN_CONTROL);pet.charm=true;
 pet.disabled=true;rejected(SPELL_FAILED_NOT_IN_CONTROL);pet.disabled=false;
 pet.hasAI=false;rejected(SPELL_FAILED_NOT_IN_CONTROL);pet.hasAI=true;
 pet.nativeAI.scripted=true;rejected(SPELL_FAILED_NOT_IN_CONTROL);pet.nativeAI.scripted=false;
 pet.casting=true;rejected(SPELL_FAILED_SPELL_IN_PROGRESS);
 entry.allowConcurrent=true;assert(ai.CanCastPetSpell(1,&target));entry.allowConcurrent=false;pet.casting=false;
 sSpellRangeStore.exists=false;rejected(SPELL_FAILED_OUT_OF_RANGE);sSpellRangeStore.exists=true;
 for(unsigned bad:{3,4,5}){entry.EffectImplicitTargetA[2]=bad;rejected(SPELL_FAILED_BAD_TARGETS);}entry.EffectImplicitTargetA[2]=0;
 target.world=false;rejected(SPELL_FAILED_BAD_TARGETS);target.world=true;
 target.phase=2;rejected(SPELL_FAILED_BAD_TARGETS);target.phase=1;
 target.map=2;rejected(SPELL_FAILED_BAD_TARGETS);target.map=1;
 pet.attack=false;rejected(SPELL_FAILED_BAD_TARGETS);pet.attack=true;
 entry.positive=true;pet.assist=false;rejected(SPELL_FAILED_BAD_TARGETS);pet.assist=true;entry.positive=false;
 assert(!ai.CanCastPetSpell(1,nullptr));entry.need=false;assert(ai.CanCastPetSpell(1,nullptr)&&Spell::checkedTarget==nullptr);entry.need=true;
 for(auto failure:{SPELL_FAILED_NO_POWER,SPELL_FAILED_STUNNED,SPELL_FAILED_IMMUNE,SPELL_FAILED_NOT_READY}){
  Spell::result=failure;assert(!ai.CanCastPetSpell(1,&target,&result)&&result==failure);assert(!ai.CastPetSpell(1,&target)&&bot.session.calls==0);}
 // Keep the native hostile range/LOS opener; friendly spells must not chase an enemy instead.
 for(auto opener:{SPELL_FAILED_OUT_OF_RANGE,SPELL_FAILED_LINE_OF_SIGHT}){
  Spell::result=opener;assert(ai.CanCastPetSpell(1,&target,&result)&&result==opener);
  pet.attackNow=false;assert(!ai.CanCastPetSpell(1,&target));pet.attackNow=true;}
 Spell::result=SPELL_CAST_OK;pet.possessed=true;assert(ai.CanCastPetSpell(1,&target)&&Spell::lastFlags==TRIGGERED_NORMAL_COMBAT_CAST);pet.possessed=false;
 encounterPause=true;assert(!ai.CastPetSpell(1,&target)&&bot.session.calls==0);
 entry.positive=true;assert(ai.CastPetSpell(1,&target)&&bot.session.calls==1);entry.positive=false;
 bot.session.calls=0;encounterPause=false;
 assert(ai.CastPetSpell(1,&target)&&bot.session.calls==1&&bot.session.values[0]==2&&bot.session.values[2]==3);
 assert(bot.session.values[1]==((ACT_PASSIVE<<24)|1u));
 autocast=true;assert(ai.CastPetSpell(1,&target)&&bot.session.values[1]==((ACT_DISABLED<<24)|1u));
 pet.m_autospells={1};assert(ai.CastPetSpell(1,&target)&&bot.session.values[1]==((ACT_ENABLED<<24)|1u));
 assert(!ai.CanCastPetSpell(0,&target));bot.pet=nullptr;assert(!ai.CanCastPetSpell(1,&target));
 std::cout<<"PASS: actual pet admission/dispatch, native outcomes, ownership/lifecycle, opener preservation and target types\n";
}
'''.replace('__METHODS__', methods)

for era, realm in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk')):
    core = root.parent / f'mangos-{realm}-behavior/src/game'
    handler_source = (core/'Entities/PetHandler.cpp').read_text()
    handler = block(handler_source, 'void WorldSession::HandlePetAction(')
    if realm == 'wotlk':
        handler += block(handler_source, 'void WorldSession::HandlePetActionHelper(')
    for contract in ('GetMasterGuid()', 'HasActionsDisabled()', 'GetCombatScriptStatus()',
                     'IsPassiveSpell(spellInfo)', 'IsSpellRequireTarget(spellInfo)',
                     'CanAttackNow(unit_target)', 'CheckPathToTarget(petUnit, unit_target)',
                     'SetSpellOpener(spellid', 'TRIGGERED_NORMAL_COMBAT_CAST', 'TRIGGERED_PET_CAST'):
        assert contract in handler, (realm, contract)
    with tempfile.TemporaryDirectory(prefix='mantech-pet-cast-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
