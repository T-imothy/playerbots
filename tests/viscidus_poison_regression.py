"""Run actual Viscidus poison selector/dispatch with native-admission boundaries."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ViscidusFrostAction.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('uint32 ViscidusPoisonAction::SelectPoisonRemoval(',
    'bool ViscidusPoisonAction::isUseful(', 'bool ViscidusPoisonAction::Execute('))
code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <vector>
#include <string>
using uint32=unsigned;using ObjectGuid=unsigned;
struct Group;
struct Unit {unsigned entry=0,guid=1,instance=1;bool world=true,alive=true,combat=true,charm=false;
 std::set<std::pair<unsigned,unsigned>>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool HasCharmer(){return charm;}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}
 bool GetSpellAuraHolder(unsigned id,unsigned caster){return auras.count({id,caster});}
 bool HasAura(unsigned id){for(auto a:auras)if(a.first==id)return true;return false;}};
struct Player:Unit {unsigned map=531;float health=50;bool teleport=false,casting=false;Group*group=nullptr;std::set<unsigned>known;
 unsigned GetMapId(){return map;}Group*GetGroup(){return group;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit*u){return u&&instance==u->instance;}bool HasSpell(unsigned id){return known.count(id);}
 float GetHealthPercent(){return health;}bool IsNonMeleeSpellCasted(bool){return casting;}};
struct GroupReference {Player*player;GroupReference*link=nullptr;Player*getSource(){return player;}GroupReference*next(){return link;}};
struct Group {GroupReference*first;GroupReference*GetFirstMember(){return first;}};
struct PlayerbotAI {bool real=false,castResult=true;unsigned casts=0,last=0;Unit*lastTarget=nullptr;
 std::map<unsigned,Unit*>units;std::set<Unit*>blocked;
 bool IsRealPlayer(){return real;}Unit*GetUnit(unsigned g){return units.count(g)?units[g]:nullptr;}
 template<class T>T value(std::string key,std::string qualifier){assert(key=="possible targets"&&qualifier=="100:1");T r;for(auto a:units)r.push_back(a.first);return r;}
 bool CanCastSpell(unsigned,Unit*u,unsigned mask,bool learned){assert(mask==0&&learned);return !blocked.count(u);}
 bool CastSpell(unsigned s,Unit*u,void*,bool wait,unsigned*d){assert(!wait);++casts;last=s;lastTarget=u;*d=1500;return castResult;}};
struct Event{};
struct ViscidusPoisonAction {PlayerbotAI*ai;Player*bot;unsigned duration=0;void SetDuration(unsigned d){duration=d;}
 unsigned SelectPoisonRemoval(Unit*&);bool isUseful();bool Execute(Event&);};
#define AI_VALUE2(type,key,q) ai->value<type>(key,q)
__METHODS__
int main(){Player bot,a,b;bot.guid=2;a.guid=3;b.guid=4;a.health=20;b.health=40;
 GroupReference rb{&b},ra{&a,&rb},rbot{&bot,&ra};Group group{&rbot};bot.group=a.group=b.group=&group;
 Unit boss;boss.entry=15299;boss.guid=100;boss.auras={{25926,100}};a.auras=b.auras={{25991,100}};
 PlayerbotAI brain;brain.units[100]=&boss;bot.known={2893};ViscidusPoisonAction action{&brain,&bot};Event e;Unit*target=nullptr;
#ifdef MANGOSBOT_ZERO
 assert(action.SelectPoisonRemoval(target)==2893&&target==&a);
 assert(action.Execute(e)&&brain.casts==1&&brain.lastTarget==&a&&action.duration==1500);
 a.auras.insert({2893,2});assert(action.SelectPoisonRemoval(target)==2893&&target==&b);
 b.auras.insert({2893,99});assert(!action.isUseful());b.auras.erase({2893,99});
 brain.blocked.insert(&b);assert(!action.isUseful());brain.blocked.clear();
 bot.known={4987};assert(action.SelectPoisonRemoval(target)==4987&&target==&b);
 for(unsigned id:{8946u,526u,1152u}){bot.known={id};assert(action.SelectPoisonRemoval(target)==id);}
 bot.known.clear();assert(!action.isUseful());bot.known={4987};
 b.auras={{25991,101}};assert(!action.isUseful());b.auras={{25991,100}};
 b.instance=2;assert(!action.isUseful());b.instance=1;b.world=false;assert(!action.isUseful());b.world=true;
 b.alive=false;assert(!action.isUseful());b.alive=true;b.teleport=true;assert(!action.isUseful());b.teleport=false;
 b.group=nullptr;assert(!action.isUseful());b.group=&group;b.charm=true;assert(!action.isUseful());b.charm=false;
 boss.instance=2;assert(!action.isUseful());boss.instance=1;boss.entry=1;assert(!action.isUseful());boss.entry=15299;
 boss.auras={{25926,99}};assert(!action.isUseful());boss.auras={{25926,100}};
 boss.alive=false;assert(!action.isUseful());boss.alive=true;boss.combat=false;assert(!action.isUseful());boss.combat=true;
 bot.map=409;assert(!action.isUseful());bot.map=531;bot.world=false;assert(!action.isUseful());bot.world=true;
 bot.alive=false;assert(!action.isUseful());bot.alive=true;bot.teleport=true;assert(!action.isUseful());bot.teleport=false;
 bot.charm=true;assert(!action.isUseful());bot.charm=false;brain.real=true;assert(!action.isUseful());brain.real=false;
 bot.casting=true;assert(!action.Execute(e)&&brain.casts==1);bot.casting=false;
 assert(action.isUseful());b.auras.clear();assert(!action.Execute(e)&&brain.casts==1);b.auras={{25991,100}};
 brain.castResult=false;assert(!action.Execute(e)&&brain.casts==2);brain.castResult=true;
 assert(action.Execute(e)&&brain.casts==3);
#else
 assert(!action.isUseful()&&!action.Execute(e)&&brain.casts==0);
#endif
 std::cout<<"PASS poison ownership, world/instance, membership, learned/native admission, active abolish, dispatch race and cast preservation\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='raid-viscidus-poison-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
