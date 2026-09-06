"""Run real threat calculations against native-shaped lifecycle/threat interfaces."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/values/ThreatValues.cpp').read_text()
header = (root / 'playerbot/strategy/values/ThreatValues.h').read_text()
values = (root / 'playerbot/strategy/Value.h').read_text()
templates = '\n'.join(block(values, marker) + ';' for marker in (
    'template<class T>\n    class CalculatedValue',
    'template<class T> class MemoryCalculatedValue',
    'template<class T> class LogCalculatedValue'))
classes = '\n'.join(block(header, 'class ' + name) + ';' for name in
                    ('MyThreatValue', 'TankThreatValue', 'ThreatValue'))
methods = source[source.index('float MyThreatValue::Calculate()'):]
helper = block(source, 'Unit* ResolveThreatTarget(') if 'Unit* ResolveThreatTarget(' in source else ''
code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <ctime>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <type_traits>
#include <utility>
using uint32=unsigned;using uint8=unsigned char;
constexpr int FLEEING_MOTION_TYPE=1,TIMED_FLEEING_MOTION_TYPE=2,TYPEID_PLAYER=4,TYPEID_UNIT=3,PERF_MON_VALUE=0;
time_t clockNow=100;time_t fakeTime(time_t*){return clockNow;}
#define time fakeTime
struct ObjectGuid {
 unsigned id=0;bool player=false;
 bool IsPlayer()const{return player;}bool operator!=(ObjectGuid b)const{return id!=b.id||player!=b.player;}
 bool operator==(ObjectGuid b)const{return !(*this!=b);}
};
struct Player;
struct Motion {int kind=0;int GetCurrentMovementGeneratorType(){return kind;}};
struct ThreatManager {std::map<Player*,float> values;float getThreat(Player* p){return values[p];}};
struct Unit {
 virtual ~Unit()=default;ObjectGuid guid{1,false};bool world=true,alive=true,friendly=false,combat=true;
 unsigned map=409,instance=1,phase=1;Unit* target=nullptr;Motion motion;ThreatManager threat;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}unsigned GetMapId(){return map;}
 bool IsInMap(Unit* u){return world&&u->world&&map==u->map&&instance==u->instance
#ifndef MANGOSBOT_ZERO
  &&phase==u->phase
#endif
  ;}
 bool IsFriend(Unit*){return friendly;}Unit* GetTarget(){return target;}ObjectGuid GetObjectGuid(){return guid;}
 int GetTypeId(){return guid.player?TYPEID_PLAYER:TYPEID_UNIT;}
 Motion* GetMotionMaster(){return &motion;}bool IsInCombat(){return combat;}
};
struct GroupReference {Player* source;GroupReference* following=nullptr;Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct Player:Unit {Group* group=nullptr;bool teleport=false,tank=false;Player(){guid.player=true;}
 Group* GetGroup(){return group;}bool IsBeingTeleported(){return teleport;}};
template<class T>struct Proxy {T value{};T Get(){return value;}};
struct Context {template<class T>Proxy<T>* GetValue(std::string){static Proxy<T> p;return &p;}};
struct PlayerbotAI {
 Player* bot;Unit* selected=nullptr;Context context;
 Player* GetBot(){return bot;}bool IsSafe(Player* p){return bot->map==p->map&&bot->instance==p->instance;}
 bool IsTank(Player* p){return p->tank;}Unit* GetUnit(ObjectGuid){return nullptr;}
 template<class T>T Read(std::string name,std::string qualifier=""){
  if constexpr(std::is_same_v<T,Unit*>)return selected;
  else return T{};
 }
};
struct AiNamedObject {std::string getName(){return "fixture";}};
struct UntypedValue:AiNamedObject {
 PlayerbotAI* ai;Player* bot;Context* context;
 UntypedValue(PlayerbotAI* a,std::string):ai(a),bot(a->bot),context(&a->context){}
 virtual void Reset(){}virtual bool Expired(){return false;}virtual bool Expired(uint32){return false;}
 virtual bool Protected(){return false;}virtual uint32 LastChangeDelay(){return 0;}
};
template<class T>struct Value {virtual T Get()=0;virtual T LazyGet()=0;virtual void Set(T)=0;};
struct {int start(int,std::string,PlayerbotAI*){return 0;}} sPerformanceMonitor;
struct {bool IsAlive(Unit* u){return u->alive;}ThreatManager& GetThreatManager(Unit* u){
 assert(u&&u->world&&u->alive&&!u->guid.player);return u->threat;}} sServerFacade;
#define AI_VALUE(type,name) ai->Read<type>(name)
#define AI_VALUE2(type,name,qualifier) ai->Read<type>(name,qualifier)
__TEMPLATES__
struct FloatCalculatedValue:CalculatedValue<float>{using CalculatedValue<float>::CalculatedValue;};
struct Uint8CalculatedValue:CalculatedValue<uint8>{using CalculatedValue<uint8>::CalculatedValue;};
struct Qualified {std::string qualifier="current target";};
__CLASSES__
__HELPER__
__METHODS__
struct Relative:ThreatValue {using ThreatValue::ThreatValue;using ThreatValue::Calculate;};
int main(){
 Player bot,tank;bot.guid.id=10;tank.guid.id=11;tank.tank=true;PlayerbotAI ai{&bot};
 GroupReference botRef{&bot},tankRef{&tank};botRef.following=&tankRef;Group group{&botRef};bot.group=&group;
 Unit enemy,other;other.guid.id=2;enemy.threat.values={{&bot,300.0f},{&tank,100.0f}};
 Relative relative(&ai);relative.qualifier="aoe";
 assert(relative.Calculate(&enemy)==255); // BEFORE FIX: uint8 overflow hides extreme threat
 enemy.threat.values[&bot]=79;assert(relative.Calculate(&enemy)==79);
 enemy.threat.values[&tank]=0;assert(relative.Calculate(&enemy)==100);
 enemy.combat=false;assert(relative.Calculate(&enemy)==0);enemy.combat=true;
 enemy.motion.kind=FLEEING_MOTION_TYPE;assert(relative.Calculate(&enemy)==0);
 enemy.threat.values[&tank]=100;assert(relative.Calculate(&enemy)==0);enemy.motion.kind=0;
 tank.tank=false;assert(ThreatValue::GetTankThreat(&ai,&enemy)==-1&&relative.Calculate(&enemy)==0);tank.tank=true;
 assert(ThreatValue::GetThreat(nullptr,&enemy)==0&&ThreatValue::GetThreat(&bot,nullptr)==0);
 assert(ThreatValue::GetTankThreat(nullptr,&enemy)==0&&ThreatValue::GetTankThreat(&ai,nullptr)==0);
 Unit friendly;friendly.friendly=true;
 assert(ThreatValue::GetThreat(&bot,&friendly)==0&&ThreatValue::GetTankThreat(&ai,&friendly)==0);
 friendly.target=&enemy;assert(ThreatValue::GetThreat(&bot,&friendly)==79);
 friendly.target=&tank;assert(ThreatValue::GetThreat(&bot,&friendly)==0);friendly.target=&enemy;
#ifndef MANGOSBOT_ZERO
 enemy.phase=2;assert(ThreatValue::GetThreat(&bot,&friendly)==0&&relative.Calculate(&enemy)==0);enemy.phase=1;
#endif
 enemy.instance=2;assert(ThreatValue::GetTankThreat(&ai,&enemy)==0);enemy.instance=1;
 enemy.map=1;assert(relative.Calculate(&enemy)==0);enemy.map=409;
 enemy.world=false;assert(ThreatValue::GetThreat(&bot,&enemy)==0);enemy.world=true;
 enemy.alive=false;assert(ThreatValue::GetTankThreat(&ai,&enemy)==0);enemy.alive=true;
#ifndef MANGOSBOT_ZERO
 tank.phase=2;assert(ThreatValue::GetTankThreat(&ai,&enemy)==-1);tank.phase=1;
#endif
 tank.world=false;assert(ThreatValue::GetTankThreat(&ai,&enemy)==-1);tank.world=true;
 tank.teleport=true;assert(ThreatValue::GetTankThreat(&ai,&enemy)==-1);tank.teleport=false;
 bot.teleport=true;assert(ThreatValue::GetThreat(&bot,&enemy)==0);bot.teleport=false;
 MyThreatValue history(&ai);
 assert(history.GetDelta(5)==0); // no selected target, including debug before any sample
 ai.selected=&friendly;assert(history.Get()==79&&history.lastTarget==enemy.guid);
 clockNow+=2;enemy.threat.values[&bot]=83;assert(history.GetDelta(5)==2);
 clockNow+=2;other.threat.values[&bot]=1000;friendly.target=&other;
 assert(history.GetDelta(5)==0&&history.ValueLog().size()==1&&history.lastTarget==other.guid);
 ai.selected=nullptr;assert(history.GetDelta(5)==0&&history.lastTarget==ObjectGuid());
 ai.selected=&enemy;enemy.world=false;assert(history.Get()==0);enemy.world=true;
 std::cout<<"PASS: actual native threat reads, target/proxy lifecycle, phase/instance, history and safe percentage\n";
}
'''.replace('__TEMPLATES__', templates).replace('__CLASSES__', classes).replace('__HELPER__', helper).replace('__METHODS__', methods)
for expansion in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-threat-target-') as folder:
        tmp=Path(folder)
        (tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}',
                        'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
