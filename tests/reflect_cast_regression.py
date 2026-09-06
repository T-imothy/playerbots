"""Exercise actual cast usefulness against native-reflectability interface fixtures."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
method = block((root / 'playerbot/strategy/actions/GenericSpellActions.cpp').read_text(),
               'bool CastSpellAction::isUseful(')
code = r'''
#include <cassert>
#include <set>
#include <list>
#include <iostream>
#include <string>
using uint32=unsigned;
constexpr int ATTACK_DISTANCE=5,SPELL_AURA_DAMAGE_SHIELD=1;
struct SpellEntry {bool passive=false,reflectable=true;unsigned school=4;};
bool IsPassiveSpell(const SpellEntry* s){return s->passive;}
bool IsReflectableSpell(const SpellEntry* s){return s->reflectable;}
unsigned GetSpellSchoolMask(const SpellEntry* s){return s->school;}
struct Aura {struct Modifier {int m_amount=100;}modifier;Modifier* GetModifier(){return &modifier;}};
struct Unit {using AuraList=std::list<Aura*>;AuraList shields;bool world=true;unsigned phase=1;int map=1;
 float reflect=0;unsigned reflectedSchool=4,queriedSchool=0;
 bool IsInWorld(){return world;}int GetMap(){return map;}
 const AuraList& GetAurasByType(int){return shields;}
 float GetReflectChance(unsigned school){queriedSchool=school;return school==reflectedSchool?reflect:0;}};
struct Player:Unit {bool teleport=false;unsigned stops=0;
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit* u){return map==u->map&&phase==u->phase;}
 unsigned GetMaxHealth(){return 1000;}void AttackStop(){++stops;}};
struct PlayerbotAI {bool learned=true;bool HasSpell(unsigned){return learned;}
 bool IsInVehicle(bool=false,bool=false,bool=false){return false;}};
struct Facade {SpellEntry spell;bool found=true;const SpellEntry* LookupSpellInfo(unsigned id){return id&&found?&spell:nullptr;}}sServerFacade;
struct CastSpellAction {Player* bot;PlayerbotAI* ai;Unit* target;unsigned spellId=1;float range=30;
 std::string spellName="spell";bool useful=true;void RefreshSpellId(){}Unit* GetTarget(){return target;}bool isUseful();};
#define AI_VALUE2(type,key,value) useful
__METHOD__
int main(){
 Player bot;Unit target;PlayerbotAI ai;CastSpellAction action{&bot,&ai,&target};
 assert(action.isUseful());target.reflect=49;assert(action.isUseful());
 target.reflect=50;assert(!action.isUseful());target.reflect=100;assert(!action.isUseful());
 // Native non-reflectable healing/ability/AoE flags remain authoritative.
 sServerFacade.spell.reflectable=false;assert(action.isUseful());sServerFacade.spell.reflectable=true;
 sServerFacade.spell.school=8;assert(action.isUseful()&&target.queriedSchool==8);sServerFacade.spell.school=4;
 target.reflect=0;target.phase=2;assert(!action.isUseful());target.phase=1;
 target.map=2;assert(!action.isUseful());target.map=1;
 target.world=false;assert(!action.isUseful());target.world=true;
 bot.teleport=true;assert(!action.isUseful());bot.teleport=false;
 bot.world=false;assert(!action.isUseful());bot.world=true;
 action.target=nullptr;assert(!action.isUseful());action.target=&target;
 ai.learned=false;assert(!action.isUseful());ai.learned=true;
 sServerFacade.spell.passive=true;assert(!action.isUseful());sServerFacade.spell.passive=false;
 action.spellId=0;assert(!action.isUseful());action.spellId=1;
 Aura shield;target.shields={&shield};action.range=ATTACK_DISTANCE;
 assert(!action.isUseful()&&bot.stops==1);shield.modifier.m_amount=99;assert(action.isUseful());
 std::cout<<"PASS: actual cast usefulness: 50% native school reflect, non-reflectable spells, lifecycle, unchanged shield threshold\n";
}
'''.replace('__METHOD__', method)
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-reflect-cast-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{era}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
