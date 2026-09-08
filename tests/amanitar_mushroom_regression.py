"""Execute the native mushroom hit and encounter cleanup callbacks."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/azjol-nerub/ahnkahet/boss_amanitar.cpp').read_text()
boss=block(source,'struct boss_amanitarAI')
methods='\n'.join(block(boss,s).replace(' override','') for s in (
 '    void DespawnMushrooms(', '    void RemoveMushroomAuras(', '    void Reset(',
 '    void JustDied(', '    void EnterEvadeMode(', '    void JustSummoned(', '    void SummonedCreatureDespawn('))
code=r'''
#include <cassert>
#include <functional>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;using GuidList=std::list<ObjectGuid>;
enum {EFFECT_INDEX_0, SPELL_MISS_NONE=0, SPELL_MISS_IMMUNE=1, TYPE_AMANITAR=4, DONE=3,
 CAST_TRIGGERED=1, TRIGGERED_OLD_TRIGGERED=1};
using SpellMissInfo=int;
__ENUM__
struct Unit {
 std::set<unsigned> auras, effectZero;
 bool HasAura(unsigned id){return auras.count(id);}
 bool HasAura(unsigned id,unsigned){return auras.count(id)&&effectZero.count(id);}
 void RemoveAurasDueToSpell(unsigned id){auras.erase(id);effectZero.erase(id);}
};using Player=Unit;
struct Ref{Player*p;Player*getSource()const{return p;}};
struct Creature;
struct Map{std::map<unsigned,Creature*> creatures;std::vector<Ref>players;
 Creature*GetCreature(unsigned g){return creatures[g];}const std::vector<Ref>&GetPlayers(){return players;}};
struct Creature:Unit {unsigned entry=0,guid=0,despawns=0,casts=0;Map*map=nullptr;std::function<void(Creature*)> callback;
 Map*GetMap(){return map;}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}
 void ForcedDespawn(){++despawns;if(callback)callback(this);}
 void CastSpell(Creature*,unsigned,unsigned){++casts;}
};
struct Instance{unsigned state=0;void SetData(unsigned id,unsigned s){assert(id==TYPE_AMANITAR);state=s;}};
struct ScriptedAI{unsigned evades=0;virtual void Reset()=0;void EnterEvadeMode(){++evades;Reset();}};
unsigned urand(unsigned a,unsigned){return a;}
struct Boss:ScriptedAI {
 Creature*m_creature;Instance*m_pInstance;GuidList m_mushroomGuids;
 unsigned m_uiBashTimer,m_uiVenomBoltTimer,m_uiRootsTimer,m_uiMiniTimer,m_uiMushroomTimer;
 unsigned DoCastSpellIfCan(Creature*,unsigned,unsigned){return 1;} // Cleanup cast fails.
 __METHODS__
};
struct Spell{Unit*target;Unit*GetUnitTarget(){return target;}};
struct SpellScript{};
__FUNGUS__
int main(){
 spell_amanitar_potent_fungus fungus;Unit player;Spell spell{&player};
 auto buff=[&](){player.auras.insert(SPELL_POTENT_FUNGUS);player.effectZero.insert(SPELL_POTENT_FUNGUS);};
 buff();fungus.OnHit(&spell,SPELL_MISS_NONE);assert(player.HasAura(SPELL_POTENT_FUNGUS));
 player.auras.insert(SPELL_MINI);fungus.OnHit(&spell,SPELL_MISS_IMMUNE);
 assert(player.HasAura(SPELL_MINI)&&player.HasAura(SPELL_POTENT_FUNGUS));
 fungus.OnHit(&spell,SPELL_MISS_NONE);assert(player.auras.empty());
 player.auras.insert(SPELL_MINI);fungus.OnHit(&spell,SPELL_MISS_NONE);assert(player.HasAura(SPELL_MINI));
 // A hit outside the scale effect's radius cannot consume Mini via damage-buff-only effect.
 player.auras.insert(SPELL_POTENT_FUNGUS);fungus.OnHit(&spell,SPELL_MISS_NONE);assert(player.HasAura(SPELL_MINI));
 buff();player.auras.insert(1234);fungus.OnHit(&spell,SPELL_MISS_NONE);assert(player.auras==std::set<unsigned>{1234});
 spell.target=nullptr;fungus.OnHit(&spell,SPELL_MISS_NONE);
 Map map;Creature owner,a,b,unrelated;owner.map=&map;a.entry=NPC_HEALTHY_MUSHROOM;b.entry=NPC_POISONOUS_MUSHROOM;
 a.guid=1;b.guid=2;unrelated.guid=3;unrelated.entry=9;map.creatures={{1,&a},{2,&b},{3,&unrelated}};
 Instance instance;Boss ai;ai.m_creature=&owner;ai.m_pInstance=&instance;
 ai.JustSummoned(&a);ai.JustSummoned(&b);ai.JustSummoned(&unrelated);
 assert(ai.m_mushroomGuids.size()==2&&a.casts==2&&b.casts==2&&unrelated.casts==0);
 ai.m_mushroomGuids.push_back(99); // Missing actor is safe.
 for(Creature*c:{&a,&b})c->callback=[&](Creature*c){assert(ai.m_mushroomGuids.empty());ai.SummonedCreatureDespawn(c);};
 Player alive,dead,distant;for(Player*p:{&alive,&dead,&distant}){p->auras={SPELL_MINI,SPELL_POTENT_FUNGUS,1234};map.players.push_back({p});}
 map.players.push_back({nullptr});ai.EnterEvadeMode();
 assert(ai.evades==1&&ai.m_mushroomGuids.empty()&&a.despawns==1&&b.despawns==1&&unrelated.despawns==0);
 for(Player*p:{&alive,&dead,&distant})assert(p->auras==std::set<unsigned>{1234});
 ai.Reset();assert(a.despawns==1&&b.despawns==1);
 ai.JustSummoned(&a);ai.SummonedCreatureDespawn(&a);assert(ai.m_mushroomGuids.empty());
 ai.JustSummoned(&b);alive.auras.insert(SPELL_MINI);ai.JustDied(nullptr);
 assert(instance.state==DONE&&b.despawns==2&&!alive.HasAura(SPELL_MINI));
 std::cout<<"PASS: native Mini/Fungus hit, immunity/partial hit, callback-safe mushroom cleanup, wipe/death and repeated reset\n";
}
'''.replace('__ENUM__',block(source,'enum\n')+';').replace('__METHODS__',methods).replace('__FUNGUS__',block(source,'struct spell_amanitar_potent_fungus').replace(' override','')+';')
sql=(root/'wotlk-db-behavior/Updates/5880_amanitar_potent_fungus.sql').read_text()
assert "(56648, 'spell_amanitar_potent_fungus')" in sql
assert 'RegisterSpellScript<spell_amanitar_potent_fungus>("spell_amanitar_potent_fungus")' in source
with tempfile.TemporaryDirectory(prefix='amanitar-mushroom-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
