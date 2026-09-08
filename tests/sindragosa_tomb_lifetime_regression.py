"""Execute native Sindragosa tomb, aura and marker lifecycles without a realm."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/icecrown_citadel/icecrown_citadel/boss_sindragosa.cpp').read_text(encoding='utf-8')
names=('npc_sindragosa_ice_tombAI','spell_sindragosa_ice_tomb_selector','spell_sindragosa_frost_beacon','spell_sindragosa_ice_tomb_trap','spell_sindragosa_ice_block_los','mob_frost_bombAI')
code=r'''
#include <cassert>
#include <map>
#include <set>
#include <iostream>
using uint32=unsigned;using SpellEffectIndex=unsigned;using Difficulty=unsigned;
enum {EFFECT_INDEX_0=0,EFFECT_INDEX_2=2,RAID_DIFFICULTY_25MAN_NORMAL=1,RAID_DIFFICULTY_25MAN_HEROIC=3,
 HIGHGUID_GAMEOBJECT=1,TEMPSPAWN_DEAD_DESPAWN=1,TRIGGERED_OLD_TRIGGERED=1,CAST_TRIGGERED=1,
 SPELL_CAST_OK=0,TYPE_SINDRAGOSA=0,IN_PROGRESS=1,NPC_SINDRAGOSA=36853,SINDRAGOSA_PHASE_GROUND=2,
 SPELL_ICE_TOMB=69712,SPELL_ICE_TOMB_PROTECTION=69700,SPELL_FROST_BOMB_DMG=69845,SPELL_FROST_BOMB_VISUAL=70022};
struct ObjectGuid{unsigned id=0;void Clear(){id=0;}bool operator<(ObjectGuid o)const{return id<o.id;}};
struct Unit;struct Creature;struct Player;struct GameObject;struct UnitAI;struct Instance;
struct Map{unsigned difficulty=0,next=10;std::map<ObjectGuid,Player*>players;std::map<ObjectGuid,GameObject*>objects;
 unsigned GetDifficulty(){return difficulty;}unsigned GenerateLocalLowGuid(unsigned){return next++;}
 Player*GetPlayer(ObjectGuid id){return players.count(id)?players[id]:nullptr;}
 GameObject*GetGameObject(ObjectGuid id){return objects.count(id)?objects[id]:nullptr;}void Add(GameObject*);
};
struct Instance{virtual ~Instance(){};unsigned state=IN_PROGRESS;Creature*boss=nullptr;
 unsigned GetData(unsigned){return state;}Creature*GetSingleCreatureFromStorage(unsigned){return boss;}};
using instance_icecrown_citadel=Instance;
struct Unit{virtual ~Unit(){};bool alive=true,player=false,los=true;ObjectGuid guid;Map*map=nullptr;Instance*instance=nullptr;
 std::set<unsigned>auras;Unit*victim=nullptr;unsigned casts=0,lastSpell=0,failSpell=0,origin=0;Unit*lastTarget=nullptr;
 bool IsAlive(){return alive;}bool IsPlayer(){return player;}bool HasAura(unsigned id){return auras.count(id);}
 void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}ObjectGuid GetObjectGuid(){return guid;}Map*GetMap(){return map;}
 Instance*GetInstanceData(){return instance;}unsigned GetPhaseMask(){return 1;}
 float GetPositionX(){return 0;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}float GetOrientation(){return 0;}
 Unit*GetVictim(){return victim;}bool IsWithinLOSInMap(Unit*,bool ignore){assert(!ignore);return los;}
 unsigned CastSpell(Unit*t,unsigned id,unsigned,void* =nullptr,void* =nullptr,ObjectGuid owner={}){
  ++casts;lastSpell=id;lastTarget=t;origin=owner.id;if(failSpell==id)return 1;if(t)t->auras.insert(id);return 0;}
};
struct Player:Unit{Player(){player=true;}};
struct UnitAI{virtual ~UnitAI(){};virtual void Reset(){}virtual void AttackStart(Unit*){}virtual void JustDied(Unit*){}
 virtual void SummonedCreatureDespawn(Creature*){}virtual void UpdateAI(unsigned){};};
struct Creature:Unit{UnitAI*ai=nullptr;Creature*summon=nullptr;unsigned despawns=0,delay=0,summons=0;
 UnitAI*AI(){return ai;}void ForcedDespawn(unsigned n=0){++despawns;delay=n;}
 Creature*SummonCreature(unsigned,float,float,float,float,unsigned,unsigned){++summons;return summon;}};
struct GameObject{static bool fail;ObjectGuid guid;unsigned deletes=0;Map*map=nullptr;
 bool Create(unsigned db,unsigned id,unsigned entry,Map*m,unsigned,float,float,float,float){assert(db==0&&entry==201722);guid.id=id;map=m;return !fail;}
 void AIM_Initialize(){}ObjectGuid GetObjectGuid(){return guid;}void Delete(){++deletes;}};bool GameObject::fail=false;
void Map::Add(GameObject*g){objects[g->guid]=g;}
struct ScriptedAI:UnitAI{Creature*m_creature;ScriptedAI(Creature*c):m_creature(c){}void SetCombatMovement(bool){}
 unsigned DoCastSpellIfCan(Unit*t,unsigned id,unsigned f){return m_creature->CastSpell(t,id,f);}};
using Scripted_NoMovementAI=ScriptedAI;
struct boss_sindragosaAI:UnitAI{unsigned m_uiPhase=4;};
struct SpellEntry{unsigned Id;};struct Store{SpellEntry value{70157};template<class T>T const*LookupEntry(unsigned id){assert(id==70157);return &value;}}sSpellTemplate;
struct Spell{Unit*caster=nullptr,*target=nullptr;SpellEntry*m_spellInfo;unsigned maximum=0;
 Unit*GetCaster()const{return caster;}Unit*GetUnitTarget(){return target;}void SetMaxAffectedTargets(unsigned n){maximum=n;}};
struct Aura{Unit*caster=nullptr,*target=nullptr;unsigned ticks=1,effect=2;Unit*GetCaster(){return caster;}Unit*GetTarget(){return target;}
 unsigned GetAuraTicks(){return ticks;}unsigned GetEffIndex(){return effect;}};
struct PeriodicTriggerData{Unit*trueCaster=nullptr,*caster=nullptr,*target=nullptr,*targetObject=nullptr;SpellEntry const*spellInfo=nullptr;};
struct SpellScript{virtual void OnInit(Spell*)const{}virtual bool OnCheckTarget(Spell const*,Unit*,unsigned)const{return true;}
 virtual void OnEffectExecute(Spell*,unsigned)const{}};
struct AuraScript{virtual void OnPeriodicTrigger(Aura*,PeriodicTriggerData&)const{}virtual void OnApply(Aura*,bool)const{}};
__SCRIPTS__
int main(){
 Map map;Instance instance;Creature boss,tomb;boss.guid.id=1;boss.map=tomb.map=&map;boss.instance=tomb.instance=&instance;
 instance.boss=&boss;boss.summon=&tomb;boss_sindragosaAI bossAI;boss.ai=&bossAI;
 Player p,tank;p.guid.id=2;p.map=&map;map.players[p.guid]=&p;boss.victim=&tank;
 npc_sindragosa_ice_tombAI tombAI(&tomb);tomb.ai=&tombAI;
 SpellEntry entry{SPELL_ICE_TOMB};Spell spell{&boss,&p,&entry};spell_sindragosa_ice_tomb_selector selector;
 for(unsigned difficulty=0;difficulty<4;++difficulty){map.difficulty=difficulty;selector.OnInit(&spell);assert(spell.maximum==(difficulty==1?5:difficulty==3?6:2));}
 assert(selector.OnCheckTarget(&spell,&p,0)&&!selector.OnCheckTarget(&spell,&tank,0));p.auras.insert(70157);assert(!selector.OnCheckTarget(&spell,&p,0));p.auras.clear();
 selector.OnEffectExecute(&spell,0);assert(p.HasAura(70126));
 Aura aura{&boss,&p};PeriodicTriggerData data;spell_sindragosa_frost_beacon beacon;
 beacon.OnPeriodicTrigger(&aura,data);assert(data.trueCaster==&boss&&data.target==&p&&data.spellInfo->Id==70157);
 instance.state=0;beacon.OnPeriodicTrigger(&aura,data);assert(!data.spellInfo);instance.state=1;
 spell_sindragosa_ice_tomb_trap trap;assert(trap.OnCheckTarget(&spell,&p,0));
 p.auras.insert(70157);assert(!trap.OnCheckTarget(&spell,&p,0));trap.OnPeriodicTrigger(&aura,data);
 assert(boss.summons==1&&p.HasAura(69700)&&map.objects.size()==1);auto go=map.objects.begin()->second;
 aura.ticks=2;trap.OnPeriodicTrigger(&aura,data);assert(boss.summons==1);
 // Prison persists while flying, releases once, and removes its physical cover.
 tombAI.UpdateAI(1000);assert(!p.HasAura(71665));bossAI.m_uiPhase=SINDRAGOSA_PHASE_GROUND;tombAI.UpdateAI(1000);assert(p.HasAura(71665));
 tombAI.JustDied(nullptr);assert(!p.HasAura(70157)&&!p.HasAura(69700)&&!p.HasAura(71665)&&go->deletes==1);
 tombAI.SummonedCreatureDespawn(&tomb);assert(go->deletes==1);
 // Missing creature/GO or AI cannot leave a permanent stun.
 aura.ticks=1;boss.summon=nullptr;p.auras.insert(70157);trap.OnPeriodicTrigger(&aura,data);assert(!p.HasAura(70157));
 boss.summon=&tomb;GameObject::fail=true;p.auras.insert(70157);trap.OnPeriodicTrigger(&aura,data);assert(!p.HasAura(70157)&&tomb.despawns==1);GameObject::fail=false;
 // A later aura tick detects a wipe or map transfer, even after creation.
 p.auras.insert(70157);trap.OnPeriodicTrigger(&aura,data);aura.ticks=4;Map other;p.map=&other;trap.OnPeriodicTrigger(&aura,data);assert(!p.HasAura(70157));p.map=&map;
 tombAI.UpdateAI(1000);assert(tomb.despawns==2);
 p.auras.insert(70157);aura.ticks=1;trap.OnPeriodicTrigger(&aura,data);map.players.clear();tombAI.UpdateAI(1000);assert(tomb.despawns==3);
 p.auras.insert(69700);p.auras.insert(71665);trap.OnApply(&aura,false);assert(!p.HasAura(69700)&&!p.HasAura(71665));
 // The explosion originates at the marker; boss GUID supplies attribution only.
 Creature marker;marker.map=&map;marker.instance=&instance;mob_frost_bombAI bomb(&marker);
 marker.failSpell=SPELL_FROST_BOMB_DMG;bomb.UpdateAI(6000);assert(marker.despawns==0&&bomb.m_uiFrostBombTimer==6000);
 marker.failSpell=0;bomb.UpdateAI(6000);assert(marker.lastTarget==&marker&&marker.origin==1&&marker.delay==2000&&!bomb.m_uiFrostBombTimer);
 bomb.Reset();instance.state=0;bomb.UpdateAI(6000);assert(!bomb.m_uiFrostBombTimer&&marker.delay==0);
 spell_sindragosa_ice_block_los cover;boss.los=false;assert(!cover.OnCheckTarget(&spell,&p,0));boss.los=true;assert(cover.OnCheckTarget(&spell,&p,0));
 for(auto item:map.objects)delete item.second;
 std::cout<<"PASS native tomb selection, delayed trigger, creation failures, release/reset/transfer/despawn, model LOS and bomb attribution/retry\n";
}
'''.replace('__SCRIPTS__','\n'.join(block(source,'struct '+name)+';' for name in names))
with tempfile.TemporaryDirectory(prefix='sindragosa-lifetime-') as td:
 p=Path(td);(p/'test.cpp').write_text(code,encoding='utf-8')
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True,timeout=20)
