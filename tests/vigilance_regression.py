"""Actual Vigilance selection: threat direction, ownership, stable eligible DPS."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

base = Path(__file__).resolve().parents[1] / 'playerbot/strategy/warrior'
text = (base / 'WarriorActions.cpp').read_text()
methods = '\n'.join(block(text, x) for x in ('Unit* CastVigilanceAction::GetTarget(', 'bool CastVigilanceAction::isUseful('))
code = r'''
#include <cassert>
#include <iostream>
struct Map{};struct Group;
struct Unit{};
struct Player:Unit {unsigned guid=1;Group* group=nullptr;Map* map=nullptr;
 bool alive=true,world=true,charmed=false,teleport=false,combat=false,tank=false,heal=false,knows=true,own=false,aura=false,castable=true;
 Group* GetGroup(){return group;}Map* GetMap(){return map;}unsigned GetObjectGuid(){return guid;}
 bool IsAlive(){return alive;}bool IsInWorld(){return world;}bool HasCharmer(){return charmed;}
 bool IsBeingTeleported(){return teleport;}bool IsInCombat(){return combat;}bool HasSpell(unsigned){return knows;}};
struct GroupReference {Player* player;GroupReference* following;
 Player* getSource(){return player;}GroupReference* next(){return following;}};
struct Group {GroupReference* first;GroupReference* GetFirstMember(){return first;}};
struct AI {Player* bot;bool base=true;bool IsTank(Player* p){return p->tank;}bool IsHeal(Player* p){return p->heal;}
 bool HasAura(const char*,Player* p,bool=false,bool owner=false){return owner?p->own:p->aura;}
 bool CanCastSpell(unsigned,Player* p,unsigned char){return p->castable;}};
struct CastBuffSpellAction {AI* ai;Player* bot;bool isUseful(){return ai->base;}};
struct CastVigilanceAction:CastBuffSpellAction {Unit* GetTarget();bool isUseful();};
__METHODS__
int main(){Map map,other;Player tank,dps1,dps2;GroupReference r1{&dps1,nullptr},r2{&dps2,&r1};Group group{&r2};
 AI ai{&tank};CastVigilanceAction action{{&ai,&tank}};
 auto reset=[&](){tank=Player{};dps1=Player{};dps2=Player{};tank.tank=true;
 tank.group=dps1.group=dps2.group=&group;tank.map=dps1.map=dps2.map=&map;
 dps1.guid=2;dps2.guid=3;ai.base=true;};
 reset();assert(action.GetTarget()==&dps1&&action.isUseful()); // stable even reverse iteration
 dps1.aura=true;assert(action.GetTarget()==&dps2); // don't overwrite another warrior
 reset();dps2.own=true;dps2.map=&other;assert(!action.isUseful()); // preserve own assignment
 reset();dps1.heal=true;dps2.tank=true;assert(!action.isUseful());
 reset();dps1.castable=false;assert(action.GetTarget()==&dps2);
 reset();dps1.alive=false;assert(action.GetTarget()==&dps2);
 reset();dps1.charmed=true;assert(action.GetTarget()==&dps2);
 reset();dps1.teleport=true;assert(action.GetTarget()==&dps2);
 reset();dps1.world=false;assert(action.GetTarget()==&dps2);
 reset();dps1.map=&other;assert(action.GetTarget()==&dps2);
 reset();tank.knows=false;assert(!action.isUseful());
 reset();tank.combat=true;assert(!action.isUseful());
 reset();tank.tank=false;assert(!action.isUseful());
 reset();tank.group=nullptr;assert(!action.isUseful());
 reset();tank.charmed=true;assert(!action.isUseful());
 reset();ai.base=false;assert(!action.isUseful());
 std::cout<<"PASS: native Vigilance maintenance targeting/ownership and eligibility\n";
}
'''.replace('__METHODS__', methods)
with tempfile.TemporaryDirectory(prefix='mantech-vigilance-') as folder:
    tmp=Path(folder)
    (tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/W3','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(base/'WarriorStrategy.cpp').read_text()
old,wrath=strategy.split('#ifdef MANGOSBOT_TWO // WOTLK',1)
assert 'new NextAction("vigilance"' not in old
assert 'new NextAction("vigilance"' in wrath
assert '#ifdef MANGOSBOT_TWO' in text.split('Unit* CastVigilanceAction::GetTarget',1)[0]
print('PASS: Vigilance action/scheduling are Wrath-only')
