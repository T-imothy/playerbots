"""Run native packet wake, owning-map imp recovery and cached plan admission."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
source=(r/'playerbot/PlayerbotAI.cpp').read_text()
actions=(r/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
wake=block(source,'void PlayerbotAI::PrepareForUrgentCombat(')
publish=block(source,'if (((packet.GetOpcode()==SMSG_ATTACKSTART')
getplan=block(actions,'bool MoltenCorePositionAction::GetPlan(')
execute=block(actions,'bool MoltenCorePositionAction::Execute(')
assert 'plan.spell == 19364' in execute and 'plan.spell == 20602' in execute
assert execute.index('PlanMoltenCoreTrash(ai, current)')<execute.index('return MoveTo(')
assert block(source,'void PlayerbotAI::UpdateAI(').index('PrepareForUrgentCombat()')<block(source,'void PlayerbotAI::UpdateAI(').index('if (!delayAlreadyAdvanced)')
urgent=block((r/'playerbot/PlayerbotAI.h').read_text(),'bool HasUrgentCommand()').replace(' override','')
code=r'''
#include <cassert>
#include <any>
#include <list>
#include <atomic>
#include <map>
#include <set>
#include <vector>
#include <string>
#include <iostream>
using uint32=unsigned;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}bool IsEmpty(){return !id;}void Clear(){id=0;}operator unsigned()const{return id;}};
constexpr unsigned SMSG_ATTACKSTART=1,SMSG_ATTACKSTOP=2,UNIT_STAND_STATE_STAND=0;
struct Group{};struct Unit{virtual ~Unit()=default;unsigned entry=11669,map=409,instance=1;float x=0,y=0,o=0;float GetPositionX(){return x;}float GetPositionY(){return y;}float GetOrientation(){return o;}bool world=true,alive=true,combat=true,charm=false;Unit*victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}unsigned GetEntry(){return entry;}
 ObjectGuid GetObjectGuid(){return 3;}
 std::set<unsigned>auras;bool HasAura(unsigned id){return auras.count(id);}Unit*GetVictim(){return victim;}virtual bool IsPlayer(){return false;}};
struct Player:Unit{bool transfer=false,tank=false,sit=true;unsigned guid=2,interrupts=0,stands=0;Group*group=nullptr;std::vector<Unit*>attackers;
 bool IsPlayer()override{return true;}bool IsBeingTeleported(){return transfer;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}
 bool IsInMap(Unit*u){return u&&u->world&&map==u->map&&instance==u->instance;}Group*GetGroup(){return group;}
 ObjectGuid GetObjectGuid(){return guid;}bool HasAura(unsigned){return false;}bool IsSitState(){return sit;}
 void SetStandState(unsigned){sit=false;++stands;}void InterruptNonMeleeSpells(bool f){assert(!f);++interrupts;}
 auto const&getAttackers(){return attackers;}};
namespace encounter{struct Circle{};}
struct EncounterPosition{bool active=true;unsigned map=409,instance=1,spell=20602;ObjectGuid boss=3,source;struct Point{float x=-20,y=0,z=0;}destination;};
template<class T>struct Cached{T value;unsigned resets=0;T Get(){return value;}void Reset(){++resets;}};
struct Context{Cached<EncounterPosition>plan;std::map<std::string,std::any>cells;template<class T,class Q=int>Cached<T>*GetValue(const char*n,Q={}){if constexpr(std::is_same_v<T,EncounterPosition>)return &plan;else{auto[it,b]=cells.emplace(n,Cached<T>{});return std::any_cast<Cached<T>>(&it->second);}}};
struct WorldPacket{unsigned opcode=1,bytes=16,index=0;unsigned ids[2]={3,2};unsigned GetOpcode()const{return opcode;}unsigned size()const{return bytes;}
 void rpos(unsigned n){index=n;}WorldPacket&operator>>(ObjectGuid&g){g=ids[index++];return *this;}};
struct ReactionEngine{unsigned notifications=0;void NotifyPartyCombat(){++notifications;}};
struct PlayerbotAI{Player*bot;bool real=false,isWaiting=true;unsigned aiInternalUpdateDelay=8000;Context context;Context*aiObjectContext=&context;
 ReactionEngine reactions;ReactionEngine*reactionEngine=&reactions;Unit*loose=nullptr;std::map<unsigned,Unit*>units;std::atomic<bool>urgentAttackPending{false},urgentCombatPending{false};
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}static bool IsTank(Player*p){return p->tank;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(ObjectGuid g){return units.count(g)?units[g]:nullptr;}
 bool HasRealPlayerMaster(){return true;}void ResetAIInternalUpdateDelay(){aiInternalUpdateDelay=0;}ObjectGuid urgentRecoveryTarget;
 void PrepareForUrgentCombat();void Publish(const WorldPacket&packet){__PUBLISH__}
 __URGENT__
};
bool MoltenCoreRecoveryTrash(unsigned e){return e!=11502;}
Unit*MoltenCoreTrashAggroTarget(PlayerbotAI*a){for(auto*u:a->bot->attackers)if(u->world&&u->alive&&!u->charm&&a->bot->IsInMap(u)&&u->victim==a->bot&&!u->HasAura(19951)&&MoltenCoreRecoveryTrash(u->entry))return u;return nullptr;}
bool PlanMoltenCoreGiants(PlayerbotAI*,EncounterPosition&){return false;}
bool MoltenCoreThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&){return false;}
Unit*MoltenCorePackTankTarget(PlayerbotAI*a){return a->loose;}Unit*MoltenCoreAssignedTankTarget(PlayerbotAI*a){return a->loose;}
unsigned replans=0;bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&p){++replans;p.destination.x=-20;return true;}
Unit*LavaTrashBanishTarget(PlayerbotAI*){return nullptr;}bool PlanLavaTrashCarrier(PlayerbotAI*,EncounterPosition&){return false;}
struct MoltenCorePositionAction{static bool GetPlan(PlayerbotAI*,EncounterPosition&);};
__WAKE__
__GETPLAN__
int main(){Group group;Player bot,tank;bot.group=tank.group=&group;Unit imp;imp.victim=&bot;bot.attackers={&imp};PlayerbotAI ai{&bot};ai.units={{3,&imp}};WorldPacket packet;
 ai.Publish(packet);assert(ai.HasUrgentCommand());ai.PrepareForUrgentCombat();
 assert(bot.interrupts==1&&!bot.sit&&bot.stands==1&&!ai.isWaiting&&ai.aiInternalUpdateDelay==0&&ai.context.plan.resets==1&&!ai.HasUrgentCommand());
 EncounterPosition plan;assert(MoltenCorePositionAction::GetPlan(&ai,plan));
 imp.victim=&tank;assert(!MoltenCorePositionAction::GetPlan(&ai,plan));imp.victim=&bot;
 // Native five-pack carrier wakes immediately, but collapse and patrol do not.
 imp.entry=11671;ai.context.plan.value.spell=19771;ai.context.plan.value.source=bot.GetObjectGuid();
 ai.urgentCombatPending=true;ai.aiInternalUpdateDelay=9000;ai.PrepareForUrgentCombat();
 assert(ai.aiInternalUpdateDelay==0&&bot.interrupts==2&&ai.reactions.notifications==2);
 assert(MoltenCorePositionAction::GetPlan(&ai,plan));imp.auras.insert(19951);
 ai.urgentCombatPending=true;ai.PrepareForUrgentCombat();assert(bot.interrupts==2);
 assert(!MoltenCorePositionAction::GetPlan(&ai,plan));imp.auras.clear();
 imp.victim=&tank;assert(!MoltenCorePositionAction::GetPlan(&ai,plan));
 // A cached off-tank gathering station cannot hide a newly loose assigned hound.
 bot.tank=true;ai.context.plan.value.source=0;ai.loose=&imp;
 assert(!MoltenCorePositionAction::GetPlan(&ai,plan));imp.victim=&bot;
 assert(MoltenCorePositionAction::GetPlan(&ai,plan));bot.tank=false;ai.loose=nullptr;
 ai.context.plan.value.source=0;
 ai.context.plan.value.spell=19364;imp.entry=11673;assert(MoltenCorePositionAction::GetPlan(&ai,plan));
 imp.victim=&tank;imp.o=3.14159265f;assert(MoltenCorePositionAction::GetPlan(&ai,plan)&&replans==1);imp.o=0;
 imp.alive=false;assert(!MoltenCorePositionAction::GetPlan(&ai,plan));imp.alive=true;imp.instance=2;assert(!MoltenCorePositionAction::GetPlan(&ai,plan));imp.instance=1;
 packet.bytes=15;ai.Publish(packet);assert(!ai.HasUrgentCommand());packet.bytes=16;
 packet.ids[1]=9;ai.Publish(packet);assert(ai.HasUrgentCommand());ai.urgentCombatPending=false;packet.ids[1]=2;
 for(unsigned fault=0;fault<7;++fault){bot.world=bot.alive=true;bot.transfer=bot.charm=bot.tank=false;bot.map=409;ai.real=false;imp.entry=11669;imp.victim=&bot;
  if(fault==0)bot.world=false;if(fault==1)bot.alive=false;if(fault==2)bot.transfer=true;if(fault==3)bot.charm=true;if(fault==4)bot.tank=true;if(fault==5)ai.real=true;if(fault==6)imp.entry=11502;
  unsigned before=bot.interrupts;ai.urgentCombatPending=true;ai.PrepareForUrgentCombat();assert(bot.interrupts==before&&!ai.HasUrgentCommand());
 }
 bot.map=0;packet.bytes=16;ai.Publish(packet);assert(ai.HasUrgentCommand());
 unsigned outsideInterrupts=bot.interrupts;ai.aiInternalUpdateDelay=9000;ai.PrepareForUrgentCombat();
 assert(!ai.HasUrgentCommand()&&ai.aiInternalUpdateDelay==0&&bot.interrupts==outsideInterrupts);
 packet.opcode=SMSG_ATTACKSTOP;packet.bytes=6;ai.Publish(packet);assert(ai.HasUrgentCommand());
 ai.PrepareForUrgentCombat();assert(!ai.HasUrgentCommand()&&bot.interrupts==outsideInterrupts);
 std::cout<<"PASS native imp wake/cast interruption, owner-map guards, Core Hound plan admission and stale aggro rejection\n";
}
'''.replace('__PUBLISH__',publish).replace('__URGENT__',urgent).replace('__WAKE__',wake).replace('__GETPLAN__',getplan)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-engage-') as tmp:
  d=Path(tmp);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
