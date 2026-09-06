"""Exercise the actual new dose/owned-HoT predicates with controlled core interfaces."""
import subprocess
import tempfile
from pathlib import Path
from behavior_regression import block

root = Path(__file__).resolve().parents[1] / 'playerbot/strategy'
rogue = block((root / 'rogue/RogueActions.h').read_text(), 'class CastEnvenomAction') + ';'
nourish = 'template<class Base>\n' + block((root / 'druid/DruidActions.h').read_text(), 'class CastNourishWithHotAction') + ';'
lava = block((root / 'shaman/ShamanTriggers.h').read_text(), 'class LavaBurstTrigger') + ';'
code = r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
#include <iostream>
using uint64=uint64_t;
enum {SPELLFAMILY_ROGUE=8,SPELLFAMILY_DRUID=7,SPELL_AURA_PERIODIC_DAMAGE=1,SPELL_AURA_PERIODIC_HEAL=2};
struct Proto {int SpellFamilyName=SPELLFAMILY_ROGUE;uint64 SpellFamilyFlags=0x10000;};
struct Aura {Proto proto;int owner=1,stacks=4;Proto* GetSpellProto(){return &proto;}int GetCasterGuid(){return owner;}int GetStackAmount(){return stacks;}};
struct Unit {std::vector<Aura*> auras;bool ownFlame=false;const std::vector<Aura*>& GetAurasByType(int){return auras;}};
struct Player:Unit {int combo=4;int GetObjectGuid(){return 1;}int GetComboPoints(){return combo;}};
struct PlayerbotAI {Player bot;Unit* target=nullptr;bool eligible=true,castable=true;bool HasAura(std::string,Unit* t,bool,bool own){return own && t->ownFlame;}};
struct BaseSpell {
 PlayerbotAI* ai;Player* bot;
 BaseSpell(PlayerbotAI* a,std::string):ai(a),bot(&a->bot){}
 virtual bool isUseful(){return ai->eligible;}Unit* GetTarget(){return ai->target;}
};
using CastMeleeSpellAction=BaseSpell;
using CastHealingSpellAction=BaseSpell;
using HealPartyMemberAction=BaseSpell;
struct SpellCanBeCastedTrigger:BaseSpell {
 using BaseSpell::BaseSpell;virtual bool IsActive(){return ai->castable;}
};
__ROGUE__
__NOURISH__
__LAVA__
int main(){
 PlayerbotAI ai;Unit target;Aura aura;ai.target=&target;
 CastEnvenomAction envenom(&ai);
 assert(!envenom.isUseful());target.auras={&aura};assert(envenom.isUseful());
 aura.owner=2;assert(!envenom.isUseful());aura.owner=1;
 aura.stacks=1;assert(!envenom.isUseful());aura.stacks=4;
 aura.proto.SpellFamilyName=3;assert(!envenom.isUseful());aura.proto.SpellFamilyName=SPELLFAMILY_ROGUE;
 aura.proto.SpellFamilyFlags=0;assert(!envenom.isUseful());aura.proto.SpellFamilyFlags=0x10000;
 ai.bot.combo=0;assert(!envenom.isUseful());ai.bot.combo=4;
 ai.eligible=false;assert(!envenom.isUseful());ai.eligible=true;
 CastNourishWithHotAction<HealPartyMemberAction> nourish(&ai);
 assert(!nourish.isUseful());aura.proto.SpellFamilyName=SPELLFAMILY_DRUID;assert(nourish.isUseful());
 aura.owner=2;assert(!nourish.isUseful());aura.owner=1;
 ai.eligible=false;assert(!nourish.isUseful());ai.eligible=true;
 ai.target=nullptr;assert(!nourish.isUseful() && !envenom.isUseful());ai.target=&target;
 LavaBurstTrigger lava(&ai);assert(!lava.IsActive());target.ownFlame=true;assert(lava.IsActive());
 ai.castable=false;assert(!lava.IsActive());ai.target=nullptr;assert(!lava.IsActive());
 std::cout<<"PASS: actual Envenom dose/ownership, Nourish owned HoT, Lava Burst owned Flame Shock/core castability\n";
}
'''.replace('__ROGUE__', rogue).replace('__NOURISH__', nourish).replace('__LAVA__', lava)
with tempfile.TemporaryDirectory(prefix='mantech-combat-rework-') as tmp:
    tmp = Path(tmp)
    (tmp / 'test.cpp').write_text(code)
    subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/W3', 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
    subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)

# The new dispatcher names must resolve, and cleanup must use the exact key.
dispatcher = (root / 'generic/DungeonStrategy.cpp').read_text()
assert dispatcher.count('"enter naxxramas"') == 2
assert '"leave naxxramas"' in dispatcher
horsemen = (root / 'generic/NaxxramasDungeonStrategies.cpp').read_text()
assert '"end horseman fight"' not in horsemen
assert horsemen.count('"end four horseman fight"') == 2
assert '"end four horseman fight"' in (root / 'triggers/TriggerContext.h').read_text()
print('PASS: Naxxramas dispatcher/cleanup registration contracts (not an encounter-play test)')

demo = (root / 'warlock/DemonologyWarlockStrategy.cpp').read_text()
wrath_demo = demo.split('#ifdef MANGOSBOT_TWO // WOTLK', 1)[1]
assert '"demonic sacrifice raid"' not in wrath_demo
assert '"demonic sacrifice raid"' in demo.split('#ifdef MANGOSBOT_TWO // WOTLK', 1)[0]
raid_pet = block(wrath_demo, 'void DemonologyWarlockPetRaidStrategy::InitNonCombatTriggers(')
assert '/*' not in raid_pet and '"summon felguard"' in raid_pet
print('PASS: Wrath no longer inherits the old sacrifice/no-pet raid policy; older policy retained')
