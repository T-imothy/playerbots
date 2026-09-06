"""Compile real dispel predicates; one skipped aura must not veto other candidates."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/PlayerbotAI.cpp').read_text()
methods='\n'.join(block(source, marker) for marker in
                  ('bool PlayerbotAI::HasAuraToDispel(', 'bool PlayerbotAI::canDispel('))
code=r'''
#include <cassert>
#include <cstring>
#include <list>
#include <map>
#include <iostream>
#include <vector>
using uint32=unsigned;using int32=int;
#define strcmpi _stricmp
enum AuraType {SPELL_AURA_NONE=0,TOTAL_AURAS=4};
struct SpellEntry {unsigned Id=1,Dispel=2;const char* SpellName[1]={"curse"};bool positive=false,effectPositive=false;};
std::map<unsigned,SpellEntry*> spells;
bool IsPositiveSpell(unsigned id){return spells.at(id)->positive;}
bool IsPositiveAuraEffect(const SpellEntry* spell,unsigned){return spell->effectPositive;}
struct Aura {SpellEntry* info=nullptr;int duration=15000;const SpellEntry* GetSpellProto()const{return info;}
 unsigned GetEffIndex()const{return 0;}int GetAuraDuration()const{return duration;}};
struct Unit {using AuraList=std::list<Aura*>;AuraList lists[TOTAL_AURAS];bool friendly=true,world=true;unsigned map=1,phase=1;
 bool IsInWorld(){return world;}bool IsInMap(Unit* other){return world&&other->world&&map==other->map&&phase==other->phase;}
 const AuraList& GetAurasByType(AuraType type){return lists[type];}};
struct {uint32 dispelAuraDuration=2000;} sPlayerbotAIConfig;
struct {bool IsFriendlyTo(Unit*,Unit* target){return target->friendly;}} sServerFacade;
struct PlayerbotAI {Unit* bot;bool HasAuraToDispel(Unit*,uint32);bool canDispel(const SpellEntry*,uint32);};
__METHODS__
int main(){
 Unit bot,target;PlayerbotAI ai{&bot};SpellEntry shortInfo,longInfo;shortInfo.Id=1;longInfo.Id=2;
 spells={{1,&shortInfo},{2,&longInfo}};Aura shortAura{&shortInfo,1000},longAura{&longInfo,15000};
 target.lists[0]={&shortAura};target.lists[1]={&longAura};
 assert(ai.HasAuraToDispel(&target,2)); // old code returns false on the first short aura
 shortInfo.Dispel=0;assert(ai.HasAuraToDispel(&target,2)); // even an unrelated effect used to veto it
 target.lists[1].clear();assert(!ai.HasAuraToDispel(&target,2));shortInfo.Dispel=2;
 assert(!ai.HasAuraToDispel(&target,2)); // skip the only nearly-expired candidate
 shortAura.duration=2000;assert(ai.HasAuraToDispel(&target,2));
 shortAura.duration=-1;assert(ai.HasAuraToDispel(&target,2)); // native permanent duration is not "nearly expired"
 shortAura.duration=0;assert(ai.HasAuraToDispel(&target,2)); // preserve existing zero-duration handling
 shortAura.duration=1000;sPlayerbotAIConfig.dispelAuraDuration=0;assert(ai.HasAuraToDispel(&target,2));
 sPlayerbotAIConfig.dispelAuraDuration=2000;shortAura.duration=15000;
 shortInfo.positive=true;assert(!ai.HasAuraToDispel(&target,2)); // don't strip friendly buffs
 target.friendly=false;assert(ai.HasAuraToDispel(&target,2)); // enemy positive effect
 shortInfo.positive=false;assert(!ai.HasAuraToDispel(&target,2));target.friendly=true;
 shortInfo.effectPositive=true;assert(!ai.HasAuraToDispel(&target,2));shortInfo.effectPositive=false;
 shortInfo.SpellName[0]="chilled";assert(!ai.HasAuraToDispel(&target,2));shortInfo.SpellName[0]="curse";
 assert(!ai.HasAuraToDispel(nullptr,2));target.world=false;assert(!ai.HasAuraToDispel(&target,2));target.world=true;
 target.map=2;assert(!ai.HasAuraToDispel(&target,2));target.map=1;
 target.phase=2;assert(!ai.HasAuraToDispel(&target,2));target.phase=1;
 bot.world=false;assert(!ai.HasAuraToDispel(&target,2));
 std::cout<<"PASS: actual dispel scan skips only ineligible aura; duration, ownership and lifecycle guards\n";
}
'''.replace('__METHODS__',methods)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-dispel-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}',
                        'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
