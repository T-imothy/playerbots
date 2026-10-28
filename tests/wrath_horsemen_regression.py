"""Run the real Wrath Horsemen planner/relief helper against native ownership and paths."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root/'playerbot/strategy/actions/WrathHorsemenActions.cpp').read_text()
source = '\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
geometry = (root/'playerbot/strategy/EncounterGeometry.h').read_text().replace('#pragma once','')
policy = (root/'playerbot/strategy/ClassicRaidPolicy.h').read_text().replace('#pragma once','')
code = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <vector>
using uint32=unsigned;
struct ObjectGuid{unsigned v=0;ObjectGuid(unsigned x=0):v(x){} void Clear(){v=0;}bool IsEmpty()const{return !v;}
 bool operator==(ObjectGuid b)const{return v==b.v;}bool operator!=(ObjectGuid b)const{return v!=b.v;}bool operator<(ObjectGuid b)const{return v<b.v;}};
struct SpellAuraHolder{unsigned stacks=0;unsigned GetStackAmount()const{return stacks;}};
struct SpellEntry{unsigned rangeIndex=170;};struct SpellRangeEntry{float maxRange=45;};
struct SpellStore{SpellEntry spell;const SpellEntry* LookupSpellInfo(unsigned){return &spell;}}sServerFacade;
struct RangeStore{SpellRangeEntry range;const SpellRangeEntry* LookupEntry(unsigned){return &range;}}sSpellRangeStore;
float GetSpellMaxRange(const SpellRangeEntry* range){return range->maxRange;}
struct SpellTargetMgr{static float GetJumpRadius(unsigned){return 10;}};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Group;struct PlayerbotAI;
struct Unit{virtual~Unit()=default;unsigned entry=0,map=533,instance=1;ObjectGuid guid;Group* group=nullptr;
 bool world=true,alive=true,combat=true,charm=false,teleport=false,los=true;float x=0,y=0,z=241.35f,reach=2;
 Unit* victim=nullptr;std::map<unsigned,SpellAuraHolder> auras;
 virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charm;}
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit* u){return u&&u->world&&world&&map==u->map&&instance==u->instance;}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetCombatReach(){return reach;}
 float GetDistance(Unit* u){return std::hypot(x-u->x,y-u->y);}Unit* GetVictim(){return victim;}
 bool IsWithinLOS(float,float,float,bool){return los;}float GetCollisionHeight(){return 2;}
 const SpellAuraHolder* GetSpellAuraHolder(unsigned id){auto i=auras.find(id);return i==auras.end()?nullptr:&i->second;}};
struct Player:Unit{PlayerbotAI* ai=nullptr;bool tank=false,healer=false,ranged=false;Map mapObject;
 bool IsPlayer()override{return true;}Group* GetGroup(){return group;}PlayerbotAI* GetPlayerbotAI(){return ai;}Map* GetMap(){return &mapObject;}};
struct GroupReference{Player* player=nullptr;GroupReference* following=nullptr;Player* getSource(){return player;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
template<class T>struct Value{T value;T Get(){return value;}};
struct Context{Value<std::list<ObjectGuid>> nearby;template<class T>Value<T>* GetValue(const char*,const char*){return &nearby;}};
struct PlayerbotAI{Player* bot=nullptr;bool human=false;Context context;std::map<ObjectGuid,Unit*> units;
 Player* GetBot(){return bot;}bool IsRealPlayer(){return human;}bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->healer;}
 bool IsRanged(Player*p){return p->ranged;}Context* GetAiObjectContext(){return &context;}Unit* GetUnit(ObjectGuid g){return units[g];}};
__GEOMETRY__
__POLICY__
namespace ai{
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss;encounter::Point destination;};
struct ClassicRaidPlan{ObjectGuid boss,target;EncounterPosition position;bool emergency=false,holdDamage=false;};
bool BuildWrathHorsemenPlan(PlayerbotAI*,const std::vector<Unit*>&,ObjectGuid&,ClassicRaidPlan&);
Unit* WrathHorsemanReliefTarget(PlayerbotAI*);
bool pathAllowed=true;float blockedX=-100000;
bool ValidateEncounterDestination(PlayerbotAI* a,EncounterPosition&p){return pathAllowed&&p.destination.x!=blockedX&&
 encounter::Distance2d({a->bot->x,a->bot->y,a->bot->z},p.destination)<=60&&std::isfinite(p.destination.x)&&std::isfinite(p.destination.y);}
bool NaxxramasEncounterEngaged(Player*p,Unit*u){return u&&p->IsInMap(u)&&u->alive&&u->combat&&!u->charm&&u->group==p->group;}
float NativeEncounterSpellRadius(unsigned id){return id==28884||id==57467?8:45;}
}
__SOURCE__
struct Fixture{
 Group group;Player p[8];PlayerbotAI a[8];GroupReference refs[8];Unit k,r,z,b;std::vector<Unit*> bosses;
 Fixture(){
  k.entry=16064;k.guid=101;k.x=2542.9f;k.y=-3015;
  r.entry=30549;r.guid=102;r.x=2583.9f;r.y=-2971.67f;
  z.entry=16063;z.guid=103;z.x=2517.8f;z.y=-2896.6f;
  b.entry=16065;b.guid=104;b.x=2469.4f;b.y=-2947.6f;
  bosses={&k,&r,&z,&b};group.first=&refs[0];
  for(unsigned i=0;i<8;++i){p[i].guid=i+1;p[i].group=&group;p[i].ai=&a[i];a[i].bot=&p[i];
   refs[i].player=&p[i];if(i<7)refs[i].following=&refs[i+1];p[i].x=2575;p[i].y=-3010;
   for(Unit* boss:bosses){boss->group=&group;a[i].units[boss->guid]=boss;a[i].context.nearby.value.push_back(boss->guid);}}
  p[0].tank=p[1].tank=true;p[2].ranged=p[3].ranged=true;p[4].healer=p[5].healer=true;
  p[0].x=k.x;p[0].y=k.y;p[1].x=r.x;p[1].y=r.y;
  p[2].x=b.x+10;p[2].y=b.y;p[3].x=z.x+10;p[3].y=z.y;
  k.victim=&p[0];r.victim=&p[1];b.victim=&p[2];z.victim=&p[3];
 }
 ai::ClassicRaidPlan plan(unsigned i,ObjectGuid& prev){ai::ClassicRaidPlan out;assert(ai::BuildWrathHorsemenPlan(&a[i],bosses,prev,out));return out;}
};
int main(){
 Fixture f;ObjectGuid previous;
#ifndef MANGOSBOT_TWO
 ai::ClassicRaidPlan noOp;assert(!ai::BuildWrathHorsemenPlan(&f.a[0],f.bosses,previous,noOp));assert(!ai::WrathHorsemanReliefTarget(&f.a[0]));
#else
 // Native two-tank ownership remains unchanged until a successful taunt.
 f.p[0].auras[28832].stacks=3;
 auto left=f.plan(0,previous);assert(left.boss==f.k.guid&&left.target==f.r.guid&&left.position.active&&left.emergency);
 auto right=f.plan(1,previous);assert(right.boss==f.r.guid&&right.target==f.k.guid&&right.position.active);
 assert(std::fabs(left.position.destination.x-right.position.destination.x)<.01f);
 f.p[0].victim=&f.r;assert(ai::WrathHorsemanReliefTarget(&f.a[0])==&f.r);
 auto miss=f.plan(0,previous);assert(miss.target==left.target&&miss.position.destination.x==left.position.destination.x);
 assert(f.k.victim==&f.p[0]&&f.r.victim==&f.p[1]); // planner never mutates threat/ownership.
 f.p[0].x=f.p[1].x=left.position.destination.x;f.p[0].y=f.p[1].y=left.position.destination.y;
 f.r.victim=&f.p[0];auto waiting=f.plan(0,previous);assert(waiting.target==f.r.guid);
 auto pickup=f.plan(1,previous);assert(pickup.target==f.k.guid);
 f.k.victim=&f.p[1];auto returned=f.plan(0,previous);assert(returned.boss==f.r.guid&&previous==f.r.guid);
 assert(std::fabs(returned.position.destination.x-f.r.x)<.01f);
 // A third clean tank prevents bridge dragging and owns a unique real relief.
 Fixture three;three.p[6].tank=true;three.p[0].auras[28832].stacks=3;
 auto hold=three.plan(0,previous);assert(hold.target==three.k.guid&&hold.position.destination.x==three.k.x);
 auto spare=three.plan(6,previous);assert(spare.target==three.k.guid);three.p[6].victim=&three.k;
 assert(ai::WrathHorsemanReliefTarget(&three.a[6])==&three.k);
 three.p[6].auras[28832].stacks=1;assert(!ai::WrathHorsemanReliefTarget(&three.a[6]));
 // Initial loose bosses elect distinct available tanks; rear casters are never taunted.
 Fixture pull;pull.k.victim=&pull.p[4];pull.r.victim=&pull.p[5];
 auto first=pull.plan(0,previous),second=pull.plan(1,previous);assert(first.target!=second.target);
 pull.p[0].victim=&pull.b;assert(!ai::WrathHorsemanReliefTarget(&pull.a[0]));
 // Back casters retain separate holders and exchange at three real marks.
 Fixture back;back.p[4].x=back.p[5].x=3000;
 auto blue=back.plan(2,previous),holy=back.plan(3,previous);
 assert(blue.target==back.b.guid&&holy.target==back.z.guid);
 back.p[2].auras[28833].stacks=2;back.p[3].auras[28835].stacks=2;
 assert(back.plan(2,previous).target==back.b.guid);
 back.p[2].auras[28833].stacks=3;back.p[3].auras[28835].stacks=3;
 assert(back.plan(2,previous).target==back.z.guid&&back.plan(3,previous).target==back.b.guid);
 assert(back.b.victim==&back.p[2]);
 back.p[3].alive=false;auto understaffed=back.plan(2,previous);assert(understaffed.target==back.b.guid);
 // A fresh rear relief walks closer; the retiring holder does not tie its radius.
 Fixture relief;relief.p[2].auras[28833].stacks=3;relief.p[4].x=relief.b.x+30;relief.p[4].y=relief.b.y;relief.p[5].x=3000;
 auto retiring=relief.plan(2,previous),incoming=relief.plan(4,previous);
 assert(retiring.boss==relief.b.guid&&incoming.boss==relief.b.guid&&incoming.target.IsEmpty());
 const auto origin=ai::encounter::Point{relief.b.x,relief.b.y,relief.b.z};
 assert(ai::encounter::Distance2d(retiring.position.destination,origin)>ai::encounter::Distance2d(incoming.position.destination,origin)+3);
 assert(!incoming.emergency); // Normal healing casts are preserved by the common movement dispatcher.
 // Meteor soak follows its actual tank, including during native movement.
 Fixture damage;auto meteor=damage.plan(6,previous);assert(meteor.target==damage.k.guid);
 assert(meteor.position.destination.x==damage.p[0].x&&meteor.position.destination.y==damage.p[0].y);
 damage.p[6].ranged=true;damage.p[6].auras[28832].stacks=3;
 auto rotated=damage.plan(6,previous);assert(rotated.target==damage.r.guid);
 assert(ai::encounter::Distance2d(rotated.position.destination,{damage.k.x,damage.k.y,damage.k.z})>=47);
 damage.p[6].auras.clear();damage.p[6].ranged=false;
 // Path rejection never invents a teleport or releases native ownership.
 ai::pathAllowed=false;auto blocked=damage.plan(6,previous);assert(blocked.holdDamage&&blocked.position.active);
 assert(blocked.position.destination.x==damage.p[6].x);ai::pathAllowed=true;
 // Dead front bosses release melee tanks to rear bolt duty; late joiners cannot pull idle bosses.
 Fixture rearOnly;rearOnly.k.alive=rearOnly.r.alive=false;
 auto tankRear=rearOnly.plan(0,previous);assert(tankRear.target==rearOnly.b.guid||tankRear.target==rearOnly.z.guid);
 rearOnly.p[6].ranged=true;auto spread=rearOnly.plan(6,previous);assert(spread.target==rearOnly.z.guid);
 assert(ai::encounter::Distance2d(spread.position.destination,{rearOnly.z.x,rearOnly.z.y,rearOnly.z.z})>=18);
 ai::blockedX=spread.position.destination.x;auto voidAvoided=rearOnly.plan(6,previous);
 assert(voidAvoided.position.active&&voidAvoided.position.destination.x!=ai::blockedX);ai::blockedX=-100000;
 Fixture reset;for(Unit* boss:reset.bosses)boss->combat=false;
 ai::ClassicRaidPlan empty;previous=99;assert(!ai::BuildWrathHorsemenPlan(&reset.a[0],reset.bosses,previous,empty)&&previous.IsEmpty());
 for(Unit* boss:reset.bosses){boss->combat=true;boss->instance=2;}
 assert(!ai::BuildWrathHorsemenPlan(&reset.a[0],reset.bosses,previous,empty));
 for(Unit* boss:reset.bosses){boss->instance=1;boss->group=nullptr;}
 assert(!ai::BuildWrathHorsemenPlan(&reset.a[0],reset.bosses,previous,empty));
 reset.p[0].teleport=true;assert(!ai::BuildWrathHorsemenPlan(&reset.a[0],reset.bosses,previous,empty));
#endif
 std::cout<<"PASS: actual Wrath Horsemen helper, native ownership/relief, distinct holders, paths, lifecycle and era gates\n";
}
'''.replace('__GEOMETRY__',geometry).replace('__POLICY__',policy).replace('__SOURCE__',source)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-wrath-horsemen-') as folder:
        temp=Path(folder);(temp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=temp,check=True)
        subprocess.run([str(temp/'test.exe')],cwd=temp,check=True)
native=(root.parent/'wotlk/src/game/AI/ScriptDevAI/scripts/northrend/naxxramas/boss_four_horsemen.cpp').read_text()
for value in ('2469.4f','-2947.6f','2583.9f','-2971.67f','2542.9f','-3015.0f','2517.8f','-2896.6f','57374','57376','AttackClosestEnemy()'):
    assert value in native,value
print('PASS: native corner/bolt/closest-victim source contract')
