"""Exercise actual Turtle policies and tactical executor with controlled native admission."""
from pathlib import Path
from turtle_cpp_fixture import run
import re
p=Path(__file__).resolve().parents[1]/'playerbot'
body=re.sub(r'^#include.*$', '', (p/'TacticalCommands.cpp').read_text(), flags=re.M)
header=re.sub(r'^#(?:include|pragma).*$', '', (p/'TacticalCommands.h').read_text(), flags=re.M)
run(r'''
#include "BotProgress.h"
#include "BotIncidentStore.h"
#include "TacticalCommandPolicy.h"
#include <cassert>
#include <functional>
#include <limits>
#include <set>
#include <cstdio>
using uint32=uint32_t;
struct Unit {bool alive=true,world=true,casting=true; bool IsAlive(){return alive;} bool IsInWorld(){return world;}bool IsNonMeleeSpellCasted(bool){return casting;}};
struct Group;struct PlayerbotAI;
struct Player:Unit {uint32 id=0;bool real=false,teleport=false,taxi=false,charm=false,transport=false,hostile=true,authorized=true;float distance=1;int map=0;Group*group=nullptr;PlayerbotAI*ai=nullptr;
 Group*GetGroup(){return group;}bool IsBeingTeleported(){return teleport;}bool IsTaxiFlying(){return taxi;}bool HasCharmer(){return charm;}bool GetTransport(){return transport;}int GetMap(){return map;}bool IsValidAttackTarget(Unit*){return hostile;}float GetDistance(Unit*){return distance;}uint32 GetGUIDLow(){return id;}};
struct GroupReference {Player*p;GroupReference*n;Player*getSource(){return p;}GroupReference*next(){return n;}};
struct Group {GroupReference*first=nullptr;GroupReference*GetFirstMember(){return first;}};
template<class T>struct Value {T v{};int resets=0;T Get(){return v;}void Set(T x){v=x;}void Reset(){++resets;}};
struct Context {Value<uint32> spell{123};Value<std::string>mark;Value<Unit*>target;template<class T>Value<T>*GetValue(std::string const&,std::string const&="");};
template<>Value<uint32>*Context::GetValue<uint32>(std::string const&,std::string const&){return &spell;}
template<>Value<std::string>*Context::GetValue<std::string>(std::string const&,std::string const&){return &mark;}
template<>Value<Unit*>*Context::GetValue<Unit*>(std::string const&,std::string const&){return &target;}
struct PlayerbotAI {Player*p;Context ctx;std::set<std::string>ready;int casts=0;bool accept=true;Player*GetBot(){return p;}Context*GetAiObjectContext(){return &ctx;}bool CanCastSpell(std::string s,Unit*){return ready.count(s)>0;}bool CastSpell(std::string,Unit*){++casts;return accept;}};
PlayerbotAI*GetBotAI(Player*p){return p->ai;}bool IsRealPlayer(Player*p){return p->real;}
'''.replace('const&=""','const& unused=""')+header+body+r'''
int main(){using namespace ai;
 UnreachableTargetMemory m;assert(!m.Observe(1,0,0,0,20,true,15000,300000));
 assert(!m.Observe(1,14999,0,0,20,true,15000,300000));assert(m.Observe(1,15000,0,0,20,true,15000,300000));
 assert(m.Contains(1,314999));assert(!m.Contains(1,315000));
 m.Reset();m.Observe(1,0,0,0,20,true,15000,300000);assert(!m.Observe(1,14000,0,0,17,true,15000,300000));assert(!m.Observe(1,15000,0,0,17,true,15000,300000));
 assert(!m.Observe(1,28000,8,0,19,true,15000,300000));assert(m.Observe(1,43000,8,0,19,true,15000,300000));
 m.SetDomain(0,1);assert(!m.Contains(1,43000));
 m.Observe(2,0,0,0,20,true,15,100);assert(!m.Observe(2,15,0,0,20,false,15,100));assert(!m.Observe(2,16,0,0,20,true,15,100));assert(m.Observe(2,31,0,0,20,true,15,100));
 m.Reset();m.Observe(3,UINT32_MAX-10,0,0,20,true,15,100);assert(m.Observe(3,4,0,0,20,true,15,100));assert(m.Contains(3,103));assert(!m.Contains(3,104));
 m.Reset();for(unsigned i=1;i<=40;++i){m.Observe(i,i*2,0,0,20,true,1,10000);assert(m.Observe(i,i*2+1,0,0,20,true,1,10000));}assert(m.Size()==32);assert(!m.Contains(1,100));assert(m.Contains(40,100));
 assert(!m.Observe(90,100,0,0,20,true,0,10));assert(!m.Observe(90,200,0,0,std::numeric_limits<float>::quiet_NaN(),true,15,100));
 BotIncidentTracker tracker;int opens=0,closes=0;uint32 duration=0;auto emit=[&](BotIncidentKind,bool open,uint64_t,uint32 d){open?++opens:++closes;duration=d;};
 tracker.Observe(BotIncidentKind::Stuck,true,0,0,60000,emit);tracker.Observe(BotIncidentKind::Stuck,true,0,59999,60000,emit);assert(opens==0);tracker.Observe(BotIncidentKind::Stuck,true,0,60000,60000,emit);assert(opens==1&&duration==60000);
 tracker.Observe(BotIncidentKind::Stuck,true,0,89999,60000,emit);assert(opens==1);tracker.Observe(BotIncidentKind::Stuck,true,0,90000,60000,emit);assert(opens==2);tracker.Reset(90001,emit);assert(closes==1);
 tracker.Observe(BotIncidentKind::DeadLong,true,0,UINT32_MAX-10,120000,emit);tracker.Observe(BotIncidentKind::DeadLong,true,0,119989,120000,emit);assert(opens==3);tracker.Reset(119990,emit);
 tracker.Observe(BotIncidentKind::Unreachable,true,1,0,0,emit);tracker.Observe(BotIncidentKind::Unreachable,true,2,1,0,emit);assert(closes==3&&opens==5);
 BotIncidentStore store(2,2);BotIncident e;e.bot=1;e.open=true;e.updated=10;e.action="reach";store.Record(e);auto id=store.Snapshot()[0].id;e.updated=20;store.Record(e);assert(store.Active()==1&&store.Snapshot()[0].id==id);
 e.bot=2;store.Record(e);e.bot=3;store.Record(e);assert(store.Active()==2&&store.Overflow()==1);store.CloseBot(1);assert(store.Active()==1);store.Expire(90021);assert(!store.Active());assert(store.Snapshot().size()==2);
 e.bot=4;store.Record(e);e.open=false;e.action.clear();store.Record(e);auto rows=store.Snapshot();assert(rows.size()==2&&rows.back().action=="reach"&&!rows.back().open);
 TacticalCommand cmd;assert(cmd.Parse("action interrupt"));assert(cmd.Parse("action cc moon abc_1"));assert(cmd.markIndex==4);assert(!cmd.Parse("action cc bad"));assert(!cmd.Parse("action interrupt x y"));assert(!cmd.Parse("action interrupt <script>"));assert(!cmd.Parse("action cc moon "+std::string(33,'a')));
 Player owner,a,b;owner.casting=a.casting=b.casting=false;owner.real=true;a.id=2;b.id=1;a.distance=b.distance=5;PlayerbotAI aa{&a},bb{&b};a.ai=&aa;b.ai=&bb;aa.ready={"kick","polymorph"};bb.ready=aa.ready;
 GroupReference rb{&b,nullptr},ra{&a,&rb};Group group{&ra};owner.group=a.group=b.group=&group;Unit target;auto auth=[](Player*p){return p->authorized;};cmd.Parse("action interrupt test");
 auto r=TacticalCommands::Execute(&owner,&target,cmd,auth);assert(r.started&&r.executor==1&&aa.casts==0&&bb.casts==1);
 b.authorized=false;r=TacticalCommands::Execute(&owner,&target,cmd,auth);assert(r.executor==2&&aa.casts==1);b.authorized=true;
 for(int mode=0;mode<8;++mode){a.authorized=false;b.alive=mode!=0;b.world=mode!=1;b.teleport=mode==2;b.taxi=mode==3;b.charm=mode==4;b.transport=mode==5;b.map=mode==6?1:0;b.casting=mode==7;r=TacticalCommands::Execute(&owner,&target,cmd,auth);assert(!r.started&&r.reason=="no_ready_bot");}
 b.alive=b.world=true;b.teleport=b.taxi=b.charm=b.transport=b.casting=false;b.map=0;a.authorized=true;
 target.casting=false;r=TacticalCommands::Execute(&owner,&target,cmd,auth);assert(r.reason=="not_casting");target.casting=true;
 aa.ready.clear();bb.ready.clear();r=TacticalCommands::Execute(&owner,&target,cmd,auth);assert(r.reason=="no_ready_bot");aa.ready={"kick","polymorph"};bb.ready=aa.ready;
 int prior=aa.casts+bb.casts;bb.accept=false;r=TacticalCommands::Execute(&owner,&target,cmd,auth);assert(!r.started&&r.reason=="cast_rejected"&&aa.casts+bb.casts==prior+1);bb.accept=true;
 cmd.Parse("action cc moon");r=TacticalCommands::Execute(&owner,&target,cmd,auth);assert(r.started&&aa.ctx.mark.v=="moon"&&bb.ctx.mark.v=="moon"&&aa.ctx.target.resets==1);
 owner.group=nullptr;assert(TacticalCommands::Execute(&owner,&target,cmd,auth).reason=="no_party");
 puts("PASS Turtle progress, incident lifecycle/bounds, tactical syntax/admission/single-executor/CC policies");
}
''',includes=[p])
