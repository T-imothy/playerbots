"""Actual AI allegiance gate with each core's native neutral-target classifier."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/PlayerbotAI.cpp').read_text()
method = block(source, 'bool PlayerbotAI::CanCastSpell(uint32 spellid, Unit* target,')
gate = block(method, 'if(!neutralSpell)')
code = r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;
constexpr unsigned MAX_SPELL_TARGETS=2,TARGET_TYPE_UNIT=1,TYPEID_PLAYER=4,TYPEID_UNIT=3;
struct TargetInfo{unsigned type=TARGET_TYPE_UNIT;}SpellTargetInfoTable[MAX_SPELL_TARGETS];
struct Unit;
struct WorldObject{virtual ~WorldObject()=default;bool hostile=false;unsigned type=TYPEID_UNIT;
 unsigned GetTypeId()const{return type;}bool CanAttackSpell(const Unit*)const;};
struct Unit:WorldObject{};
bool WorldObject::CanAttackSpell(const Unit* target)const{return target->hostile;}
__NATIVE__
struct SpellEntry{enum Mode{Neutral,Friendly,Enemy}mode=Neutral;};
bool IsPositiveSpell(const SpellEntry* s,const WorldObject* caster=nullptr,const WorldObject* target=nullptr){
 if(s->mode==SpellEntry::Friendly)return true;if(s->mode==SpellEntry::Enemy)return false;
 return IsNeutralEffectTargetPositive(1,caster,target);}
enum SpellCastResult{SPELL_CAST_OK,SPELL_FAILED_TARGET_ENEMY,SPELL_FAILED_TARGET_FRIENDLY};
struct Facade{bool IsHostileTo(Unit*,Unit* target){return target->hostile;}
 bool IsFriendlyTo(Unit*,Unit* target){return !target->hostile;}}sServerFacade;
bool eligible(Unit* bot,Unit* target,const SpellEntry* spellInfo,bool neutralSpell,SpellCastResult* checkResult){
 __GATE__
 return true;
}
int main(){Unit bot,target;bot.type=TYPEID_PLAYER;SpellEntry spell;SpellCastResult result=SPELL_CAST_OK;
 assert(eligible(&bot,&target,&spell,false,&result));
 target.hostile=true;assert(IsPositiveSpell(&spell)); // Reproduce the old missing-context classification.
 assert(!IsPositiveSpell(&spell,&bot,&target)&&eligible(&bot,&target,&spell,false,&result));
 spell.mode=SpellEntry::Friendly;assert(!eligible(&bot,&target,&spell,false,&result)&&result==SPELL_FAILED_TARGET_ENEMY);
 target.hostile=false;spell.mode=SpellEntry::Enemy;
 assert(!eligible(&bot,&target,&spell,false,&result)&&result==SPELL_FAILED_TARGET_FRIENDLY);
 assert(eligible(&bot,&target,&spell,true,nullptr)); // Existing explicitly neutral exception behavior unchanged.
 spell.mode=SpellEntry::Neutral;assert(eligible(&bot,&bot,&spell,false,nullptr));
 std::cout<<"PASS: actual spell gate uses native caster/target context, keeps strict friendly/enemy and neutral-exception rules\n";
}
'''.replace('__GATE__', gate)
for era, realm in (('ZERO', 'classic'), ('ONE', 'tbc'), ('TWO', 'wotlk')):
    native = (root.parent / f'mangos-{realm}-behavior/src/game/Spells/SpellMgr.h').read_text()
    helper = block(native, 'inline bool IsNeutralEffectTargetPositive(')
    with tempfile.TemporaryDirectory(prefix='mantech-spell-target-context-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code.replace('__NATIVE__', helper))
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{era}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
