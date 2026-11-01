"""Execute the actual Classic C'Thun role module with bounded native fixtures."""
from pathlib import Path
import subprocess, tempfile
root = Path(__file__).resolve().parents[1]
source = (root/'playerbot/strategy/actions/CthunRoleActions.cpp').read_text()
source = '\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
declarations = (root/'playerbot/strategy/actions/CthunRoleActions.h').read_text().replace('#pragma once','')
stub = r'''
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <set>
#include <string>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;
enum{IN_PROGRESS=1,UNIT_CREATED_BY_SPELL=2,CMSG_AREATRIGGER=3};
struct SpellEntry{bool damage=true;};
struct SpellAuraHolder{unsigned stack=1;unsigned GetStackAmount()const{return stack;}};
struct Unit;struct Player;struct Creature;struct Group;
struct Threat{float value=1;float getThreat(Player*){return value;}};
struct Instance{virtual~Instance()=default;};
struct ScriptedInstance:Instance{unsigned state=1;Creature*body=nullptr;unsigned GetData(unsigned id){assert(id==8);return state;}
 Creature*GetSingleCreatureFromStorage(unsigned id,bool){assert(id==15727);return body;}};
struct Map{Instance*instance=nullptr;Instance*GetInstanceData(){return instance;}};
struct Unit{virtual~Unit()=default;bool world=true,alive=true,combat=true,charmed=false,player=false,valid=true,cc=false,ucc=false;
 unsigned entry=0,guid=0,spawner=0,created=0,mapid=531,instance=7;float x=0,y=0,z=100,hp=100;std::set<unsigned>auras;SpellAuraHolder acid;Unit*victim=nullptr;Threat threat;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool HasAura(unsigned id){return auras.count(id);}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}
 unsigned GetSpawnerGuid(){return spawner;}unsigned GetUInt32Value(unsigned){return created;}bool IsPlayer(){return player;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetHealthPercent(){return hp;}
 bool IsInMap(Unit*u){return u&&u->mapid==mapid&&u->instance==instance;}Unit*GetVictim(){return victim;}
 float GetDistance(Unit*u){return std::sqrt((x-u->x)*(x-u->x)+(y-u->y)*(y-u->y)+(z-u->z)*(z-u->z));}
 Threat&getThreatManager(){return threat;}const SpellAuraHolder*GetSpellAuraHolder(unsigned id){return HasAura(id)?&acid:nullptr;}};
struct WorldPacket{unsigned id=0;WorldPacket(unsigned){}WorldPacket&operator<<(unsigned n){id=n;return*this;}};
struct Session{unsigned calls=0;void HandleAreaTriggerOpcode(WorldPacket&p){assert(p.id==4033);++calls;}};
struct Player:Unit{Player(){player=true;}Group*group=nullptr;Map*map=nullptr;bool teleport=false;Session session;
 Group*GetGroup(){return group;}bool IsBeingTeleported(){return teleport;}Map*GetMap(){return map;}unsigned GetMapId(){return mapid;}
 unsigned GetInstanceId(){return instance;}Session*GetSession(){return &session;}};
struct Creature:Unit{};
struct GroupReference{Player*p=nullptr;GroupReference*n=nullptr;Player*getSource(){return p;}GroupReference*next(){return n;}};
struct Group{GroupReference first;GroupReference*GetFirstMember(){return &first;}};
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{Value<ObjectGuid>current;Value<std::list<ObjectGuid>>nearby;
 template<class T>Value<T>*GetValue(const char*,const char* =nullptr);};
template<>Value<ObjectGuid>*Context::GetValue<ObjectGuid>(const char*,const char*){return &current;}
template<>Value<std::list<ObjectGuid>>*Context::GetValue<std::list<ObjectGuid>>(const char*,const char*){return &nearby;}
struct PlayerbotAI{Player*bot=nullptr;Context context;bool real=false,heal=false,tank=false;std::map<unsigned,Unit*>units;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsHeal(Player*){return heal;}bool IsTank(Player*){return tank;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned g){return units.count(g)?units[g]:nullptr;}};
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*,float,bool){return u->valid;}
 static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->ucc;}};
struct{float sightDistance=100;}sPlayerbotAIConfig;
struct AreaTriggerEntry{unsigned mapid=531;float x=20,y=0,z=-98;};
struct{AreaTriggerEntry entry;bool exists=true;const AreaTriggerEntry*LookupEntry(unsigned id){assert(id==4033);return exists?&entry:nullptr;}}sAreaTriggerStore;
bool IsPointInAreaTriggerZone(const AreaTriggerEntry*e,unsigned m,float x,float y,float z,float){return e->mapid==m&&std::hypot(x-e->x,y-e->y)<1&&std::fabs(z-e->z)<1;}
namespace ai{struct EncounterPosition{bool active=false,exclusive=false;unsigned map=0,instance=0,boss=0,spell=0;struct Point{float x,y,z;}destination;};
 struct ClassicRaidPlan{unsigned boss=0,target=0;EncounterPosition position;bool holdDamage=false,emergency=false;};
 bool pathValid=true;bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&){return pathValid;}
 bool ClassicRaidDamageSpell(const SpellEntry*s){return s&&s->damage;}}
'''
tests = r'''
int main(){Player bot;Creature body,flesh,eye,claw;Group group;ScriptedInstance instance;Map map;PlayerbotAI ai;
 group.first.p=&bot;bot.group=&group;bot.map=&map;map.instance=&instance;instance.body=&body;ai.bot=&bot;
 body.guid=10;body.entry=15727;body.auras={26232,26156};body.victim=&bot;
 flesh.guid=11;flesh.entry=15802;flesh.spawner=10;flesh.z=-98;
 eye.guid=12;eye.entry=15334;eye.created=26768;eye.spawner=1;
 claw.guid=13;claw.entry=15728;claw.created=26216;claw.spawner=1;
 bot.guid=1;ai.units={{1,&bot},{10,&body},{11,&flesh},{12,&eye},{13,&claw}};
 ai.context.nearby.value={11};bot.z=-98;bot.auras={26476};ClassicRaidPlan p;
#ifdef MANGOSBOT_ZERO
 assert(CthunRolePlan(&ai,p)&&p.target==11&&!p.holdDamage&&!p.position.active);
 assert(CthunFleshTarget(&ai,&flesh)); // Passive, body-owned flesh needs no victim or initial attacker record.
 for(unsigned mapid:{0u,409u,469u,489u,533u}){bot.mapid=mapid;p={};assert(!CthunRolePlan(&ai,p));}bot.mapid=531;
 for(unsigned state:{0u,2u,3u}){instance.state=state;p={};assert(!CthunRolePlan(&ai,p));}instance.state=1;
 bot.teleport=true;assert(!CthunFleshTarget(&ai,&flesh));bot.teleport=false;
 bot.alive=false;assert(!CthunFleshTarget(&ai,&flesh));bot.alive=true;
 ai.real=true;assert(!CthunFleshTarget(&ai,&flesh));ai.real=false;
 body.threat.value=0;body.victim=nullptr;assert(!CthunFleshTarget(&ai,&flesh));body.threat.value=1;
 assert(CthunFleshTarget(&ai,&flesh)); // Native group threat survives victim handoff.
 flesh.spawner=99;assert(!CthunFleshTarget(&ai,&flesh));flesh.spawner=10;
 flesh.instance=8;assert(!CthunFleshTarget(&ai,&flesh));flesh.instance=7;
 flesh.cc=true;assert(!CthunFleshTarget(&ai,&flesh));flesh.cc=false;
 flesh.ucc=true;assert(!CthunFleshTarget(&ai,&flesh));flesh.ucc=false;
 flesh.valid=false;assert(!CthunFleshTarget(&ai,&flesh));flesh.valid=true;
 bot.acid.stack=5;p={};assert(CthunRolePlan(&ai,p)&&p.holdDamage&&p.emergency&&p.position.active&&p.position.spell==26221);
 assert(CthunPlanCurrent(&ai,p));p.position.instance=8;assert(!CthunPlanCurrent(&ai,p));
 assert(!CthunStomachExit(&ai,true)&&bot.session.calls==0);bot.x=20;
 assert(CthunStomachExit(&ai,false)&&bot.session.calls==0);assert(CthunStomachExit(&ai,true)&&bot.session.calls==1);
 ai::pathValid=false;p={};assert(CthunRolePlan(&ai,p)&&p.holdDamage&&!p.position.active);assert(!CthunStomachExit(&ai,true));ai::pathValid=true;
 bot.acid.stack=1;body.auras.insert(26235);p={};assert(CthunRolePlan(&ai,p)&&p.position.active);body.auras.erase(26235);
 bot.hp=34;p={};assert(CthunRolePlan(&ai,p)&&p.position.active);bot.hp=100;
 flesh.alive=false;p={};assert(CthunRolePlan(&ai,p)&&p.position.active);flesh.alive=true;
 assert(!CthunApproachAllowed(&ai,&body));SpellEntry damage,heal;heal.damage=false;
 assert(!CthunOffenseAllowed(&ai,&damage,&body));assert(CthunOffenseAllowed(&ai,&heal,&body));
 bot.auras.clear();bot.z=100;ai.context.nearby.value={12,13};p={};
 assert(CthunRolePlan(&ai,p)&&p.target==12);ai.tank=true;p={};assert(CthunRolePlan(&ai,p)&&p.target==13);ai.tank=false;
 eye.spawner=99;p={};assert(CthunRolePlan(&ai,p)&&p.target==13);eye.spawner=1;
 eye.created=999;p={};assert(CthunRolePlan(&ai,p)&&p.target==13);eye.created=26768;
 ai.context.nearby.value={};p={};assert(CthunRolePlan(&ai,p)&&p.holdDamage&&!p.target);
 body.auras.insert(26235);p={};assert(CthunRolePlan(&ai,p)&&p.target==10&&!p.holdDamage);
 assert(CthunOffenseAllowed(&ai,&damage,&body));assert(CthunApproachAllowed(&ai,&body));
 ai.heal=true;p={};assert(CthunRolePlan(&ai,p)&&!p.target&&!p.holdDamage);
 body.auras.erase(26232);p={};assert(!CthunRolePlan(&ai,p));
#else
 assert(!CthunRolePlan(&ai,p)&&!CthunFleshTarget(&ai,&flesh)&&!CthunStomachExit(&ai,true));
 assert(CthunOffenseAllowed(&ai,nullptr,&body)&&CthunApproachAllowed(&ai,&body));
#endif
 std::cout<<"PASS native CThun stomach, exit, target ownership, phase, instance and era isolation\n";
}
'''
with tempfile.TemporaryDirectory(prefix='cthun-stomach-') as directory:
    p=Path(directory);(p/'test.cpp').write_text(stub+declarations+source+tests)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
