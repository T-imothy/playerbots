"""Execute Volazj's real population and victim-independent phase update methods."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]/'mangos-wotlk-behavior'
s=(root/'src/game/AI/ScriptDevAI/scripts/northrend/azjol-nerub/ahnkahet/boss_volazj.cpp').read_text()
boss=block(s,'struct boss_volazjAI')
methods='\n'.join(block(boss,k).replace(' override','') for k in ('    void JustSummoned(', '    void BuildInsanityVisages()', '    void UpdateAI(', '    void DamageTaken('))
code=r'''
#include <cassert>
#include <array>
#include <map>
#include <set>
#include <vector>
#include <iostream>
using uint32=unsigned;using uint8=unsigned char;using ObjectGuid=unsigned;using DamageEffectType=unsigned;
struct SpellEntry{};
enum{MAX_INSANITY_SPELLS=5,NPC_TWISTED_VISAGE_1=30621,NPC_TWISTED_VISAGE_5=30625,SPELL_TWISTED_VISAGE_EFFECT=57507,SPELL_TWISTED_VISAGE_PASSIVE=57551,TYPE_VOLAZJ=0,SPECIAL=3,IN_PROGRESS=1,FAIL=2,TRIGGERED_OLD_TRIGGERED=0,SPELL_INSANITY_VISUAL=57561,SPELL_INSANITY=57496,SPELL_MIND_FLAY=57941,SPELL_MIND_FLAY_H=59974,SPELL_SHADOW_BOLT=57942,SPELL_SHADOW_BOLT_H=59975,SPELL_SHIVER=57949,SPELL_SHIVER_H=59978,CAST_OK=0,UNIT_FIELD_FLAGS=0,UNIT_FLAG_UNINTERACTIBLE=1,ATTACKING_TARGET_RANDOM=0};
unsigned aInsanityPhaseSpells[]={57508,57509,57510,57511,57512},aSpawnVisageSpells[]={57500,57501,57502,57503,57504};unsigned urand(unsigned lo,unsigned){return lo;}
struct boss_volazjAI;boss_volazjAI*active;unsigned failAt=999;
struct Unit{virtual ~Unit()=default;};struct Creature;struct Player;struct NpcAI{virtual ~NpcAI()=default;};struct npc_volazj_visageAI:NpcAI{Player*model=nullptr;Unit*target=nullptr;void Configure(Player*p){model=p;}void AttackStart(Unit*p){target=p;}};
struct Player:Unit{unsigned guid;bool alive=true,teleport=false;std::set<unsigned>auras;bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}bool HasAura(unsigned s){return auras.count(s);}void CastSpell(Player*,unsigned,unsigned,void*,void*,unsigned);void CastSpell(Creature*,unsigned,unsigned){}};
struct Map{std::map<unsigned,Player*>players;Player*GetPlayer(unsigned guid){auto i=players.find(guid);return i==players.end()?nullptr:i->second;}};
struct Creature:Unit{unsigned entry=0,spawner=0,despawns=0;NpcAI*ai=nullptr;bool immune=true;unsigned GetEntry(){return entry;}unsigned GetSpawnerGuid(){return spawner;}NpcAI*AI(){return ai;}void ForcedDespawn(){++despawns;}void CastSpell(Creature*,unsigned,unsigned){}void SetImmuneToPlayer(bool b){immune=b;}Map*map;bool visual=true;Unit*victim=nullptr;float hp=65;unsigned flags=1;Map*GetMap(){return map;}unsigned GetObjectGuid(){return 29311;}bool HasAura(unsigned){return visual;}void RemoveAurasDueToSpell(unsigned){visual=false;}void RemoveFlag(unsigned,unsigned){flags=0;}bool SelectHostileTarget(){return victim!=nullptr;}Unit*GetVictim(){return victim;}float GetHealthPercent(){return hp;}Unit*SelectAttackingTarget(unsigned,unsigned){return victim;}};
struct instance_ahnkahet{unsigned state=SPECIAL,reconciles=0;unsigned GetData(unsigned){return state;}void SetData(unsigned,unsigned s){state=s;}void UpdateInsanityPhases(){++reconciles;}};
struct ScriptedAI{unsigned evades=0,casts=0,melee=0;bool movement=true;void EnterEvadeMode(){++evades;}void SetCombatMovement(bool b){movement=b;}int DoCastSpellIfCan(Unit*,unsigned){++casts;return CAST_OK;}void DoMeleeAttackIfReady(){++melee;}};
struct boss_volazjAI:ScriptedAI{
 Creature*m_creature;instance_ahnkahet*m_pInstance;bool m_insanityBuilt=false,m_bIsInsanityInProgress=true,m_bIsRegularMode=true;unsigned m_spawnedVisages=0,m_uiInsanityIndex=0,m_insanityCheckTimer=0,m_uiCombatPhase=1,m_uiMindFlayTimer=10000,m_uiShadowBoltTimer=5000,m_uiShiverTimer=18000;std::array<unsigned,5>m_insanityPlayers{};
 __METHODS__
};
struct Spawn{unsigned donor,phase;};std::vector<Spawn>spawns;
void Player::CastSpell(Player*,unsigned spell,unsigned,void*,void*,unsigned){assert(spell>=57500&&spell<=57504);if(spawns.size()==failAt)return;Creature summon;summon.entry=30621+spell-57500;summon.spawner=guid;npc_volazj_visageAI ai;summon.ai=&ai;active->JustSummoned(&summon);assert(ai.model==this&&ai.target==active->m_creature->GetMap()->GetPlayer(active->m_insanityPlayers[spell-57500]));assert(!summon.immune&&!summon.flags&&!summon.despawns);spawns.push_back({guid,spell-57500});}
int main(){
 Map map;Creature creature;creature.map=&map;instance_ahnkahet instance;boss_volazjAI ai;ai.m_creature=&creature;ai.m_pInstance=&instance;active=&ai;
 Player players[5];for(unsigned i=0;i<5;++i){players[i].guid=10+i;players[i].auras={57508+i};map.players[10+i]=&players[i];ai.m_insanityPlayers[i]=10+i;}ai.m_uiInsanityIndex=5;
 ai.BuildInsanityVisages();assert(spawns.size()==20&&ai.m_spawnedVisages==20&&instance.reconciles==1);for(auto spawn:spawns)assert(spawn.donor!=ai.m_insanityPlayers[spawn.phase]);ai.BuildInsanityVisages();assert(spawns.size()==20);
 Creature invalid;invalid.entry=30621;invalid.spawner=999;ai.JustSummoned(&invalid);assert(invalid.despawns==1&&ai.m_spawnedVisages==20);
 // No ordinary spells, melee or timers while phased, even without a victim.
 ai.UpdateAI(1000);assert(ai.casts==0&&ai.melee==0&&ai.m_uiMindFlayTimer==10000&&instance.reconciles==2);
 unsigned damage=123;ai.DamageTaken(nullptr,damage,0,nullptr);assert(damage==0);
 for(auto&p:players)p.alive=false;ai.UpdateAI(1000);assert(ai.evades==1&&instance.state==FAIL);
 // Incomplete creation fails the encounter instead of leaving missing clone groups.
 for(auto&p:players)p.alive=true;instance.state=SPECIAL;ai.m_insanityBuilt=false;ai.m_spawnedVisages=0;spawns.clear();failAt=3;ai.BuildInsanityVisages();assert(ai.evades==2&&instance.state==FAIL&&spawns.size()==3);
 // Solo entry has no other party members to copy and completes without trapping.
 failAt=999;spawns.clear();instance.state=SPECIAL;ai.m_insanityBuilt=false;ai.m_spawnedVisages=0;ai.m_uiInsanityIndex=1;creature.visual=true;ai.BuildInsanityVisages();assert(spawns.empty()&&instance.state==IN_PROGRESS&&!creature.visual);
 ai.UpdateAI(1);assert(!ai.m_bIsInsanityInProgress&&creature.flags==0&&ai.movement);
 damage=123;ai.DamageTaken(nullptr,damage,0,nullptr);assert(damage==123);
 // The accepted Insanity cast ends this update, preventing an ordinary cast
 // from immediately following it and disturbing the transition.
 creature.victim=&players[0];ai.m_uiMindFlayTimer=0;ai.m_uiShadowBoltTimer=0;ai.UpdateAI(1);assert(ai.casts==1&&ai.m_uiCombatPhase==2);
 std::cout<<"PASS: 20 non-self clones across five phases, native summon setup/activation and duplicate finish guard, missing-victim phase progress, DoT protection, wipe/failure cleanup, solo completion and transition cast ordering\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='volazj-population-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True,timeout=60)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True,timeout=20)
