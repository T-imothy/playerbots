"""Native skill auto-training rejects absent spells while retaining skill cleanup."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

work = Path(__file__).resolve().parents[2]
code = r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <vector>
using uint16=uint16_t;using uint32=uint32_t;
enum {SPELL_EFFECT_SKILL=118,SKILL_FISHING=356};
struct SkillLineAbilityEntry {uint32 skillId,spellId,racemask,classmask,req_skill_value,forward_spellid,learnOnGetSkill;};
struct SpellLearnSkillNode {uint32 skill,effect,step;};
struct SpellEntry {};
struct {std::set<uint32> valid;SpellEntry entry;
 template<class T>T const* LookupEntry(uint32 id){return valid.count(id)?&entry:nullptr;}}sSpellTemplate;
using AbilityMap=std::multimap<uint32,const SkillLineAbilityEntry*>;
using SkillLineAbilityMapBounds=std::pair<AbilityMap::const_iterator,AbilityMap::const_iterator>;
struct {AbilityMap abilities;std::map<uint32,SpellLearnSkillNode> training;
 SkillLineAbilityMapBounds GetSkillLineAbilityMapBoundsBySkillId(uint32 id){return abilities.equal_range(id);}
 const SpellLearnSkillNode* GetSpellLearnSkill(uint32 id){auto it=training.find(id);return it==training.end()?nullptr:&it->second;}}sSpellMgr;
struct Player {bool world=true;uint32 race=1,clazz=8;std::set<uint32> known;std::vector<uint32> granted,removed;
 uint32 getRaceMask(){return race;}uint32 getClassMask(){return clazz;}uint16 GetSkillStep(uint16){return 2;}
 bool IsInWorld(){return world;}bool HasSpell(uint32 id){return known.count(id);}
 void removeSpell(uint32 id,bool=false,bool=false,bool=false){removed.push_back(id);known.erase(id);}
 void addSpell(uint32 id,bool,bool,bool,bool){granted.push_back(id);known.insert(id);}
 void learnSpell(uint32 id,bool){granted.push_back(id);known.insert(id);}
 void UpdateSkillTrainedSpells(uint16,uint16);
};
__METHOD__
int main(){
 // Wrath SkillLineAbility.dbc row 21723: rogue auto-training for absent spell 75460.
 SkillLineAbilityEntry invalid{253,75460,1791,8,1,0,2},valid{253,100,1791,8,1,0,2};
 sSpellMgr.abilities={{253,&invalid},{253,&valid}};sSpellTemplate.valid={100};Player bot;
 bot.UpdateSkillTrainedSpells(253,1);assert(bot.granted==std::vector<uint32>{100});
 bot.granted.clear();bot.world=false;bot.UpdateSkillTrainedSpells(253,1);assert(bot.granted==std::vector<uint32>{100});
 bot.granted.clear();bot.clazz=1;bot.UpdateSkillTrainedSpells(253,1);assert(bot.granted.empty());
 bot.clazz=8;bot.race=2048;bot.UpdateSkillTrainedSpells(253,1);assert(bot.granted.empty());bot.race=1;
 valid.req_skill_value=10;bot.UpdateSkillTrainedSpells(253,1);assert(bot.granted.empty()&&bot.removed.back()==100);
 bot.removed.clear();bot.UpdateSkillTrainedSpells(253,0);assert((bot.removed==std::vector<uint32>{75460,100}));
 valid.learnOnGetSkill=0;sSpellMgr.training[100]={253,SPELL_EFFECT_SKILL,1};
 bot.known.clear();bot.granted.clear();bot.UpdateSkillTrainedSpells(253,1);assert(bot.granted==std::vector<uint32>{100});
 bot.granted.clear();bot.UpdateSkillTrainedSpells(253,1);assert(bot.granted.empty()); // Keep repair idempotent.
 std::cout<<"PASS: missing skill spells skipped; valid login/world training, race/class gates, rank removal and profession repair preserved\n";
}
'''
with tempfile.TemporaryDirectory(prefix='mantech-skill-training-') as folder:
    tmp = Path(folder)
    for era in ('classic', 'tbc', 'wotlk'):
        source = (work / ('mangos-' + era + '-behavior') / 'src/game/Entities/Player.cpp').read_text()
        method = block(source, 'void Player::UpdateSkillTrainedSpells(')
        (tmp / 'test.cpp').write_text(code.replace('__METHOD__', method))
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
