"""Execute grip-release scripts with reentrant aura-removal callbacks."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]/'mangos-wotlk-behavior'
s=(root/'src/game/AI/ScriptDevAI/scripts/northrend/ulduar/ulduar/boss_kologarn.cpp').read_text()
parts='\n'.join(block(s,key).replace(' override','')+(';' if key.startswith('struct') else '') for key in ['static void ClearKologarnPlayerGrip(', 'static void ReleaseKologarnArm(', 'struct CancelKologarnStoneGrip', 'struct KologarnStoneGripAbsorb', 'struct KologarnStoneGrip :'])
code=r'''
#include <cassert>
#include <map>
#include <set>
#include <vector>
#include <iostream>
using uint32=unsigned;using SpellEffectIndex=unsigned;
enum{TYPEID_PLAYER=1,TYPEID_UNIT=2,NPC_RIGHT_ARM=32934,EFFECT_INDEX_0=0,EFFECT_INDEX_2=2,AURA_REMOVE_BY_SHIELD_BREAK=9};
struct Unit;struct Creature;struct Player;struct Aura;struct Instance{virtual ~Instance()=default;};
struct instance_ulduar:Instance{Creature*arm;Creature*GetSingleCreatureFromStorage(unsigned){return arm;}};
std::map<unsigned,Unit*>world;
struct Unit{unsigned guid=0,entry=0,type=TYPEID_UNIT,unboards=0;Instance*instance=nullptr;std::map<unsigned,std::set<unsigned>>auras;virtual ~Unit()=default;unsigned GetTypeId(){return type;}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}Instance*GetInstanceData(){return instance;}void RemoveAurasDueToSpell(unsigned);void RemoveAurasByCasterSpell(unsigned,unsigned);};
struct Player:Unit{Player(){type=TYPEID_PLAYER;}};
struct Ref{Player*p;Player*getSource()const{return p;}};
struct Map{std::vector<Ref>players;const std::vector<Ref>&GetPlayers(){return players;}};
struct Creature:Unit{Map*map=nullptr;Map*GetMap(){return map;}};
struct Aura{Unit*target,*caster;unsigned id,index,mode=0;Unit*GetTarget(){return target;}Unit*GetCaster(){return caster;}unsigned GetId(){return id;}unsigned GetEffIndex(){return index;}unsigned GetRemoveMode(){return mode;}};
struct AuraScript{};struct SpellScript{};struct Spell{Unit*target;Unit*GetUnitTarget(){return target;}};
__PARTS__
void Unit::RemoveAurasByCasterSpell(unsigned id,unsigned caster){
 auto it=auras.find(id);if(it==auras.end()||!it->second.erase(caster))return;
 if(it->second.empty())auras.erase(it);
 // Native aura holders detach before running removal callbacks. Model that
 // ordering so reciprocal player/vehicle cleanup must remain idempotent.
 if(id==62056||id==63985){if(type==TYPEID_UNIT)++unboards;Aura aura{this,world[caster],id,type==TYPEID_PLAYER?2u:0u};KologarnStoneGrip().OnApply(&aura,false);}
}
void Unit::RemoveAurasDueToSpell(unsigned id){auto it=auras.find(id);if(it==auras.end())return;auto owners=it->second;for(auto guid:owners)RemoveAurasByCasterSpell(id,guid);}
struct AI{Creature*m_creature;instance_ulduar*m_pInstance;__CLEAR_ALL__};
int main(){
 Creature arm,left,boss;arm.guid=1;arm.entry=NPC_RIGHT_ARM;left.guid=2;left.entry=32933;Player first,second,third;first.guid=11;second.guid=12;third.guid=13;instance_ulduar instance;instance.arm=&arm;Map map{{{&first},{&second},{nullptr},{&third}}};boss.map=&map;AI ai{&boss,&instance};
 for(Unit*u:std::initializer_list<Unit*>{&arm,&left,&first,&second,&third}){world[u->guid]=u;u->instance=&instance;}
 auto grant=[&](unsigned grip){unsigned damage=grip==62056?64290:64292;for(Player*p:{&first,&second,&third}){p->auras[grip].insert(p->guid);p->auras[damage].insert(p->guid);p->auras[64708].insert(p->guid);p->auras[777].insert(p->guid);arm.auras[grip].insert(p->guid);}};
 auto clean=[&](){assert(!arm.auras.count(62056)&&!arm.auras.count(63985));for(Player*p:{&first,&second,&third})assert(p->auras.size()==1&&p->auras.count(777));};
 for(unsigned grip:{62056u,63985u}){
  grant(grip);Spell spell{&left};CancelKologarnStoneGrip().OnEffectExecute(&spell,0);assert(arm.auras[grip].size()==3);
  Aura shield{&arm,&first,grip==62056?64224u:64225u,0,0};KologarnStoneGripAbsorb absorb;absorb.OnApply(&shield,false);assert(arm.auras[grip].size()==3);shield.mode=AURA_REMOVE_BY_SHIELD_BREAK;absorb.OnApply(&shield,true);assert(arm.auras[grip].size()==3);absorb.OnApply(&shield,false);clean();unsigned exits=arm.unboards;absorb.OnApply(&shield,false);assert(arm.unboards==exits);
  grant(grip);first.RemoveAurasDueToSpell(grip);assert(first.auras.size()==1&&arm.auras[grip].size()==2&&second.auras.count(grip));
  spell.target=&arm;CancelKologarnStoneGrip().OnEffectExecute(&spell,0);clean();
  grant(grip);ai.ClearAllGrips();clean();ai.ClearAllGrips();
 }
 Spell none{nullptr};CancelKologarnStoneGrip().OnEffectExecute(&none,0);ClearKologarnPlayerGrip(nullptr);ReleaseKologarnArm(nullptr);
 std::cout<<"PASS: both grip variants, shared shield break, left-arm isolation, individual death/stun release, repeated reciprocal cleanup and lifecycle cleanup\n";
}
'''.replace('__PARTS__',parts).replace('__CLEAR_ALL__',block(s,'void ClearAllGrips()'))
with tempfile.TemporaryDirectory(prefix='kologarn-grip-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
