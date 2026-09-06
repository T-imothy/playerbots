"""Run the actual Wrath proc/resource predicates; verify old-era exclusion."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1] / 'playerbot/strategy'
dk = (root / 'deathknight/DKTriggers.h').read_text()
mage = block((root / 'mage/MageTriggers.h').read_text(), 'class ArcaneBlastTrigger') + ';'
runes = '#ifdef MANGOSBOT_TWO\n' + block(dk, 'class EmpowerRuneWeaponTrigger') + ';\n#endif'
spread = block((root / 'deathknight/DKActions.cpp').read_text(), 'bool CastPestilenceAction::isUseful(')
code = r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <list>
#include <map>
#include <iostream>
using uint8=uint8_t; using uint32=uint32_t; using ObjectGuid=int;
enum {POWER_RUNIC_POWER=1};
struct Map {};
struct Aura {int stacks=0,duration=10000;Aura* GetHolder(){return this;}
 int GetAuraDuration(){return duration;}int GetStackAmount(){return stacks;}};
struct Unit {Map* map=nullptr;bool world=true,alive=true;float distance=0;
 Aura* plague=nullptr;Aura* fever=nullptr;bool owned=true;
 bool IsInWorld(){return world;} bool IsAlive(){return alive;} Map* GetMap(){return map;}
 float GetDistance(Unit* other){return other->distance;}};
struct Player:Unit {bool combat=true,glyph=false;unsigned runic=0;int cooldown[6]={};
 bool IsInCombat(){return combat;}unsigned GetPower(int){return runic;}
 int GetRuneCooldown(uint8 i){return cooldown[i];}bool HasAura(int){return glyph;}};
struct PlayerbotAI {Player bot;Unit* target=nullptr;bool eligible=true,known=true,castable=true;
 uint8 mana=100;Aura* blast=nullptr;std::map<int,Unit*> units;std::list<int> targets;
 bool HasSpell(std::string){return known;}bool CanCastSpell(std::string,Player*,uint8){return castable;}
 Aura* GetAura(int id,Unit* unit,bool own=false){if(id==36032)return blast;
 if(!unit || (own && !unit->owned))return nullptr;return id==55078?unit->plague:unit->fever;}
 Unit* GetUnit(int guid){return units.count(guid)?units[guid]:nullptr;}
};
#define AI_VALUE(type,name) (ai->targets)
#define AI_VALUE2(type,name,qualifier) (ai->mana)
struct Config{uint8 lowMana=20;}sPlayerbotAIConfig;
struct Trigger {PlayerbotAI* ai;Player* bot;Trigger(PlayerbotAI* a,std::string,int=1):ai(a),bot(&a->bot){}
 virtual bool IsActive(){return true;}};
using BuffTrigger=Trigger;
struct CastSpellAction {PlayerbotAI* ai;Player* bot;CastSpellAction(PlayerbotAI* a):ai(a),bot(&a->bot){}
 virtual bool isUseful(){return ai->eligible;}Unit* GetTarget(){return ai->target;}};
struct CastPestilenceAction:CastSpellAction {using CastSpellAction::CastSpellAction;bool isUseful()override;};
__RUNES__
__MAGE__
__SPREAD__
int main(){
 PlayerbotAI ai;Map first,other;ai.bot.map=&first;Unit source,target;
 source.map=target.map=&first;ai.target=&source;ai.units[1]=&source;ai.units[2]=&target;ai.targets={1,2};
 CastPestilenceAction pestilence(&ai);ArcaneBlastTrigger blast(&ai);
#ifdef MANGOSBOT_TWO
 EmpowerRuneWeaponTrigger empower(&ai);assert(!empower.IsActive());
 for(int i=0;i<4;++i)ai.bot.cooldown[i]=5000;assert(empower.IsActive());
 ai.bot.runic=601;assert(!empower.IsActive());ai.bot.runic=600;assert(empower.IsActive());
 ai.bot.cooldown[0]=2999;assert(!empower.IsActive());ai.bot.cooldown[0]=3000;
 ai.bot.combat=false;assert(!empower.IsActive());ai.bot.combat=true;
 ai.known=false;assert(!empower.IsActive());ai.known=true;
 ai.castable=false;assert(!empower.IsActive());ai.castable=true;
 assert(blast.IsActive());Aura stack;ai.blast=&stack;stack.stacks=3;assert(blast.IsActive());
 stack.stacks=4;assert(!blast.IsActive());stack.stacks=0;
 ai.mana=20;assert(!blast.IsActive());ai.mana=21;assert(blast.IsActive());
 ai.known=false;assert(!blast.IsActive());ai.known=true;
 assert(!pestilence.isUseful());Aura disease;source.plague=&disease;assert(pestilence.isUseful());
 source.owned=false;assert(!pestilence.isUseful());source.owned=true;
 target.plague=&disease;assert(!pestilence.isUseful());target.owned=false;assert(pestilence.isUseful());target.owned=true;
 target.plague=nullptr;target.map=&other;assert(!pestilence.isUseful());target.map=&first;
 target.alive=false;assert(!pestilence.isUseful());target.alive=true;
 target.world=false;assert(!pestilence.isUseful());target.world=true;
 target.distance=11;assert(!pestilence.isUseful());target.distance=10;assert(pestilence.isUseful());
 ai.targets.clear();assert(!pestilence.isUseful());ai.bot.glyph=true;disease.duration=2999;assert(pestilence.isUseful());
 disease.duration=3000;assert(!pestilence.isUseful());disease.duration=2999;
 ai.eligible=false;assert(!pestilence.isUseful());ai.eligible=true;
 ai.bot.glyph=false;assert(!pestilence.isUseful());
#else
 assert(!pestilence.isUseful()); // No Wrath disease/rune behavior in the older builds.
 ai.known=false;ai.mana=0;assert(blast.IsActive()); // Original BuffTrigger behavior retained.
#endif
 std::cout<<"PASS: actual expansion-gated rune/mana/disease ownership and spread predicates\n";
}
'''.replace('__RUNES__',runes).replace('__MAGE__',mage).replace('__SPREAD__',spread)
with tempfile.TemporaryDirectory(prefix='mantech-combat-policy-') as tmp:
    tmp=Path(tmp)
    (tmp/'test.cpp').write_text(code)
    for expansion in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/W3','/D'+expansion,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)

spells=(root/'actions/GenericSpellActions.cpp').read_text()
for function in ('bool CastSpellAction::Execute(', 'bool CastSpellAction::isUseful(', 'bool CastSpellAction::isPossible('):
    assert 'IsPassiveSpell(' in block(spells,function)
print('PASS: passive-spell rejection present at scheduling, feasibility and execution boundaries')
