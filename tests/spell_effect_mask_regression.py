"""Actual AI mask forwarding/filter with each core's native target-mask helpers."""
from pathlib import Path
import re
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/PlayerbotAI.cpp').read_text()
wrapper = block(source, 'bool PlayerbotAI::CanCastSpell(std::string name,')
method = block(source, 'bool PlayerbotAI::CanCastSpell(uint32 spellid, Unit* target,')
start = method.index('uint8 checkedEffectMask')
end = method.index('if (!ignoreRange', start)
immunity = method[start:end]
for name in ('actions/PullActions.cpp', 'actions/ReachTargetActions.h', 'triggers/GenericTriggers.cpp'):
    text = (root / 'playerbot/strategy' / name).read_text()
    assert not re.search(r'CanCastSpell\(\w+, target, true', text)

code = r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
using uint8=uint8_t;using uint32=unsigned;using int32=int;
enum SpellEffectIndex{EFFECT_INDEX_0,EFFECT_INDEX_1,EFFECT_INDEX_2,MAX_EFFECT_INDEX};
enum{TARGET_UNIT_CASTER=1,TARGET_UNIT_ENEMY=2,TARGET_AREA_ENEMY=3,
 SPELL_EFFECT_SCHOOL_DAMAGE=2,SPELL_EFFECT_APPLY_AURA=6,SPELL_AURA_PERIODIC_DAMAGE=3};
enum SpellCastResult{SPELL_CAST_OK,SPELL_FAILED_IMMUNE};
struct WorldObject{};
struct SpellEntry{unsigned Effect[3]{6,6,0},EffectApplyAuraName[3]{},EffectImplicitTargetA[3]{2,1,0},
 EffectImplicitTargetB[3]{};int EffectBasePoints[3]{};bool positive[3]{false,true,true};};
bool IsCheckCastTarget(unsigned target){return target==TARGET_UNIT_ENEMY;}
bool IsPositiveEffect(const SpellEntry* s,SpellEffectIndex i,const WorldObject*,const WorldObject*){return s->positive[i];}
unsigned GetSpellSchoolMask(const SpellEntry*){return 1;}
__NATIVE__
struct Unit:WorldObject{unsigned receivedMask=0,checks[3]{},schoolChecks=0;bool immuneEffect[3]{},school=false;
 bool IsImmuneToSpell(const SpellEntry* s,bool,unsigned mask,Unit*){receivedMask=mask;return school&&!IsPositiveEffectMask(s,mask);}
 bool IsImmuneToSpellEffect(const SpellEntry*,SpellEffectIndex i,bool){++checks[i];return immuneEffect[i];}
 bool IsImmuneToDamage(unsigned){++schoolChecks;return school;}};
bool eligible(Unit* bot,Unit* target,const SpellEntry* spellInfo,uint8 effectMask,SpellCastResult* checkResult){
 __FILTER__
 return true;
}
struct Item{};
struct IdValue{uint32 Get(){return 123;}};
struct Context{IdValue value;template<class T>IdValue* GetValue(const char*,std::string){return &value;}};
struct PlayerbotAI{Context* aiObjectContext;uint8 mask=0;bool known=false,range=false,combat=false,mount=false;Item* item=nullptr;
 bool CanCastSpell(std::string,Unit*,uint8,Item*,bool,bool,bool,SpellCastResult*);
 bool CanCastSpell(uint32 id,Unit*,uint8 m,bool k,Item* i,bool r,bool c,bool mo,SpellCastResult* result){
  assert(id==123);mask=m;known=k;item=i;range=r;combat=c;mount=mo;if(result)*result=SPELL_CAST_OK;return true;}};
__WRAPPER__
int main(){
 Unit bot,target;SpellEntry spell;SpellCastResult result=SPELL_CAST_OK;
 assert(eligible(&bot,&target,&spell,0,&result)&&target.receivedMask==1&&target.checks[1]==0);
 target.school=true;assert(!eligible(&bot,&target,&spell,0,&result)&&result==SPELL_FAILED_IMMUNE);
 // The old empty mask misclassified the negative effect as positive.
 assert(IsPositiveEffectMask(&spell,0)&&!IsPositiveEffectMask(&spell,1));target.school=false;
 target.immuneEffect[0]=true;
 assert(!eligible(&bot,&target,&spell,0,nullptr)); // A usable self effect cannot rescue the immune target effect.
 assert(eligible(&bot,&target,&spell,2,nullptr)&&target.receivedMask==2); // Explicit subset is forwarded and honored.
 target.immuneEffect[1]=true;assert(!eligible(&bot,&target,&spell,2,nullptr));
 target.immuneEffect[1]=false;assert(eligible(&bot,&target,&spell,3,nullptr));
 bot.immuneEffect[0]=true;assert(eligible(&bot,&bot,&spell,0,nullptr)&&bot.receivedMask==3);
 spell.Effect[0]=SPELL_EFFECT_SCHOOL_DAMAGE;target.school=true;target.schoolChecks=0;
 assert(eligible(&bot,&target,&spell,2,nullptr)&&target.schoolChecks==0); // Unselected damage must not veto selected buff.
 spell.EffectImplicitTargetA[0]=TARGET_AREA_ENEMY;spell.EffectImplicitTargetA[1]=0;
 target.receivedMask=0;target.schoolChecks=0;
 assert(eligible(&bot,&target,&spell,0,nullptr)&&target.receivedMask==0&&target.schoolChecks==0);
 // AoE-center eligibility is left to native CheckCast/recipient targeting.
 spell.EffectImplicitTargetA[0]=0;spell.EffectImplicitTargetB[2]=TARGET_UNIT_ENEMY;spell.Effect[2]=6;
 target.school=false;target.immuneEffect[2]=true;assert(!eligible(&bot,&target,&spell,0,nullptr)&&target.receivedMask==4);
 Context context;PlayerbotAI ai{&context};Item item;
 for(unsigned mask=0;mask<8;++mask){result=SPELL_FAILED_IMMUNE;
  assert(ai.CanCastSpell(std::string("spell"),&target,uint8(mask),&item,true,true,true,&result));
  assert(ai.mask==mask&&ai.known&&ai.item==&item&&ai.range&&ai.combat&&ai.mount&&result==SPELL_CAST_OK);}
 std::cout<<"PASS: actual named-mask forwarding, native target/self masks, selected effects, AoE-center and caller compatibility\n";
}
'''.replace('__FILTER__', immunity).replace('__WRAPPER__', wrapper)
for era, realm in (('ZERO', 'classic'), ('ONE', 'tbc'), ('TWO', 'wotlk')):
    native = (root.parent / f'mangos-{realm}-behavior/src/game/Spells/SpellMgr.h').read_text()
    helpers = '\n'.join(block(native, marker) for marker in
                        ('inline uint32 GetCheckCastEffectMask(', 'inline uint32 GetCheckCastSelfEffectMask(',
                         'inline bool IsPositiveEffectMask('))
    with tempfile.TemporaryDirectory(prefix='mantech-spell-effect-mask-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code.replace('__NATIVE__', helpers))
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{era}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
