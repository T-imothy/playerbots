"""Execute native Web Wrap selection with depleted raids and the Wrath release hook."""
from pathlib import Path
import subprocess, tempfile, sys
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
mode=sys.argv[1] if len(sys.argv)>1 else 'all'
assert mode in ('all','selection','release')
for era in ('classic','tbc','wotlk'):
    region='northrend' if era=='wotlk' else 'eastern_kingdoms'
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/{region}/naxxramas/boss_maexxna.cpp').read_text()
    selection=block(source,'struct WebWrapMaexxna')+';'
    release=block(block(source,'struct npc_web_wrapAI'),'void JustDied(') if era=='wotlk' else 'void JustDied(Unit*) override {}'
    code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <random>
#include <set>
#include <vector>
#include <stdexcept>
using uint32=unsigned;using SpellEffectIndex=unsigned;using ObjectGuid=unsigned;
enum { SPELL_WEBWRAP=28673,SPELL_WEBWRAP_H=54127,SPELL_WEBWRAP_STUN=28622,
 SPELL_WEB_WRAP_SUMMON=28627,TRIGGERED_OLD_TRIGGERED=1,ATTACKING_TARGET_ALL_SUITABLE=2,
 SELECT_FLAG_PLAYER=4,SELECT_FLAG_SKIP_TANK=8,MAX_PLAYERS_WEB_WRAP=__COUNT__,MAX_PLAYERS_WEB_WRAP_H=2 };
std::mt19937*GetRandomGenerator(){static std::mt19937 generator(42);return &generator;}
unsigned urand(unsigned a,unsigned b){assert(a<=b);return a;}
struct Unit {std::vector<Unit*> candidates;std::vector<unsigned> casts;
 void SelectAttackingTargets(std::vector<Unit*>&out,unsigned,unsigned offset,void*,unsigned flags){
  assert(offset==1&&flags==(SELECT_FLAG_PLAYER|SELECT_FLAG_SKIP_TANK));out=candidates;}
 void CastSpell(void*,unsigned id,unsigned){if(!this)throw std::runtime_error("Web Wrap selected a null player");casts.push_back(id);}
};
struct Player:Unit {bool alive=true;unsigned restores=0;std::set<unsigned> auras;
 bool IsAlive(){return alive;}void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}
 void RestoreDisplayId(){++restores;}
};
struct Map {Player*victim=nullptr;Player*GetPlayer(unsigned id){assert(id==10);return victim;}};
struct Creature:Unit {Map map;Map*GetMap(){return &map;}};
struct Entry {unsigned Id;};
struct Spell {Unit* caster;Entry*m_spellInfo;Unit*GetCaster(){return caster;}};
struct SpellScript {virtual void OnEffectExecute(Spell*,SpellEffectIndex) const{}};
__SELECT__
struct Base {virtual void JustDied(Unit*){}};
struct Wrap:Base {Creature*m_creature;ObjectGuid m_victimGuid=10;__RELEASE__};
int main(){try{
#ifndef RELEASE_ONLY
 for(unsigned spellId:{unsigned(SPELL_WEBWRAP),unsigned(SPELL_WEBWRAP_H)}){
  unsigned cap=__CAP__;
  for(unsigned count=0;count<=8;++count){
   Unit boss;std::vector<Unit> players(count);
   for(auto&player:players)boss.candidates.push_back(&player);
   Entry entry{spellId};Spell spell{&boss,&entry};WebWrapMaexxna action;action.OnEffectExecute(&spell,0);
   unsigned total=0;std::set<unsigned> destinations;
   for(auto&player:players){assert(player.casts.size()<=1);for(unsigned id:player.casts){++total;destinations.insert(id);}}
   assert(total==std::min(count,cap)&&destinations.size()==total);
  }
 }
#endif
#ifdef WRATH
#ifndef SELECTION_ONLY
 Creature creature;Player victim;creature.map.victim=&victim;Wrap wrap;wrap.m_creature=&creature;
 victim.auras={28622,28627,12345};wrap.JustDied(nullptr);
 assert(victim.auras==std::set<unsigned>{12345}&&victim.restores==1);
 creature.map.victim=nullptr;wrap.JustDied(nullptr);
 wrap.m_victimGuid=0;wrap.JustDied(nullptr);
#endif
#endif
 std::cout<<"PASS: native Maexxna depleted raid selection and Web Wrap release\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''.replace('__COUNT__','1' if era=='wotlk' else '3').replace('__CAP__','spellId==SPELL_WEBWRAP?1:2' if era=='wotlk' else '3').replace('__SELECT__',selection).replace('__RELEASE__',release)
    with tempfile.TemporaryDirectory(prefix=f'mantech-maexxna-{era}-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        flags=(['/DWRATH'] if era=='wotlk' else [])+([] if mode=='all' else ['/D'+mode.upper()+'_ONLY'])
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',*flags,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
