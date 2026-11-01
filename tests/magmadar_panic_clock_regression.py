"""Native-observable Panic preparation timing and the actual scoped collector."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
code=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include "playerbot/strategy/actions/MagmadarPanicPolicy.h"
using int32=int32_t;using uint32=uint32_t;
constexpr unsigned CLASS_WARRIOR=1;
struct Guid{uint64_t n=10;uint64_t GetRawValue(){return n;}};
struct Aura{int32 maximum=8000,remaining=8000;int32 GetAuraMaxDuration(){return maximum;}int32 GetAuraDuration(){return remaining;}};
struct Unit{unsigned entry=11982;bool world=true,alive=true,combat=true,charm=false;Guid guid;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}Guid GetObjectGuid(){return guid;}};
struct Group;
struct Player:Unit{unsigned map=409,instance=5,cls=1;bool transfer=false,same=true,ward=false,rage=false,ready=true;Group*group=nullptr;Aura*fear=nullptr;uint64_t caster=10;
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}unsigned getClass(){return cls;}
 bool IsBeingTeleported(){return transfer;}bool IsInMap(Unit*){return same;}Group*GetGroup(){return group;}
 bool HasAura(unsigned id){return id==6346?ward:rage;}bool IsSpellReady(unsigned id){assert(id==18499);return ready;}
 Aura*GetSpellAuraHolder(unsigned id,Guid boss){assert(id==19408);return caster==boss.n?fear:nullptr;}};
struct GroupReference{Player*p;GroupReference*following=nullptr;Player*getSource(){return p;}GroupReference*next(){return following;}};
struct Group{GroupReference ref;GroupReference*GetFirstMember(){return &ref;}};
namespace WorldTimer{uint32 now=1000;uint32 getMSTime(){return now;}}
namespace ai {
struct MagmadarControl{MagmadarPanicClock panic;};
template<class T>struct Cached{T value{};T Get(){return value;}void Set(T v){value=v;}};
struct Context{Cached<MagmadarControl> state;template<class T>Cached<T>*GetValue(const char*){return &state;}};
struct PlayerbotAI{Player*bot;Context context;bool tank=true,human=false,learned=true;int64_t start=42;
 Player*GetBot(){return bot;}bool IsTank(Player*){return tank;}bool IsRealPlayer(){return human;}bool HasSpell(const char*){return learned;}
 int64_t GetCombatStartTime(){return start;}Context*GetAiObjectContext(){return &context;}};
bool MoltenCoreMagmadarPanicDue(PlayerbotAI*,Unit*);
}
using namespace ai;
namespace ObservedClock{int64_t now=42;}
#define time(x) ObservedClock::now
__METHOD__
#undef time
int main(){
 MagmadarPanicClock clock;
 assert(!clock.Update(1000,10,5,42,-1));
 assert(!clock.Update(4999,10,5,42,-1));assert(clock.Update(5000,10,5,42,-1));
 assert(clock.Update(11000,10,5,42,-1));assert(!clock.Update(11001,10,5,42,-1));
 // Observe the real fear aura and keep its application time on repeated samples.
 assert(!clock.Update(12369,10,5,42,0));
 for(int age=100;age<8000;age+=100)assert(!clock.Update(12369+age,10,5,42,age));
 assert(!clock.Update(40368,10,5,42,-1));assert(clock.Update(40369,10,5,42,-1));
 assert(clock.Update(47369,10,5,42,-1));assert(!clock.Update(47370,10,5,42,-1));
 // New cast rebases the window; foreign encounter/reset cannot reuse it.
 assert(!clock.Update(48369,10,5,42,5000));assert(clock.Update(71369,10,5,42,-1));
 assert(!clock.Update(71369,11,5,42,-1));assert(!clock.Update(75369,11,6,42,-1));
 assert(!clock.Update(79369,11,6,43,-1));
 MagmadarPanicClock wrapped;assert(!wrapped.Update(UINT32_MAX-2000,1,1,1,-1));
 assert(wrapped.Update(1999,1,1,1,-1));
 Player bot,member;Group group{{&member}};bot.group=&group;member.group=&group;Unit boss;PlayerbotAI ai{&bot};
 assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));WorldTimer::now=5000;
#ifdef MANGOSBOT_ZERO
 assert(MoltenCoreMagmadarPanicDue(&ai,&boss));
 // Strategy registration can finish several seconds after observed combat.
 // First evaluation must not start another full first-Panic waiting window.
 PlayerbotAI late{&bot};WorldTimer::now=11000;ObservedClock::now=48;
 assert(MoltenCoreMagmadarPanicDue(&late,&boss));
 WorldTimer::now=14000;ObservedClock::now=51;assert(MoltenCoreMagmadarPanicDue(&late,&boss));
 WorldTimer::now=16001;ObservedClock::now=53;assert(!MoltenCoreMagmadarPanicDue(&late,&boss));
 PlayerbotAI stale{&bot};WorldTimer::now=100000;ObservedClock::now=142;
 assert(!MoltenCoreMagmadarPanicDue(&stale,&boss));
 PlayerbotAI future{&bot};ObservedClock::now=40;
 assert(!MoltenCoreMagmadarPanicDue(&future,&boss));
 ObservedClock::now=42;WorldTimer::now=5000;
 bot.ward=true;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));bot.ward=false;
 bot.rage=true;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));bot.rage=false;
 bot.ready=false;assert(MoltenCoreMagmadarPanicDue(&ai,&boss));bot.ready=true; // timing survives stance GCD
 ai.learned=false;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));ai.learned=true;
 Aura fear;member.fear=&fear;WorldTimer::now=12369;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));
 member.fear=nullptr;WorldTimer::now=40369;assert(MoltenCoreMagmadarPanicDue(&ai,&boss));
 for(unsigned map:{0u,249u,469u,489u,509u,531u,533u}){bot.map=map;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));}bot.map=409;
 boss.entry=12056;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));boss.entry=11982;
 ai.tank=false;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));ai.tank=true;
 ai.human=true;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));ai.human=false;
 bot.transfer=true;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));bot.transfer=false;
 bot.same=false;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));bot.same=true;
 boss.combat=false;assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));
#else
 assert(!MoltenCoreMagmadarPanicDue(&ai,&boss));
#endif
 std::cout<<"PASS observable Panic timing, repeated-aura stability, wrap/reset and native actor/role/era guards\n";
}
'''.replace('__METHOD__',block((root/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text(),'bool ai::MoltenCoreMagmadarPanicDue('))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='magmadar-panic-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/I{root}',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
