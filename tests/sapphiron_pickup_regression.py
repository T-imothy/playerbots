"""Execute Sapphiron's tank election; pickup precedes optional flank formation."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <vector>
#include <iostream>
constexpr unsigned UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=1;
struct Player;struct PlayerbotAI;
struct Unit{unsigned entry=15989,guid=1;bool player=false,air=false,engaged=true;Unit*victim=nullptr;
 unsigned GetEntry(){return entry;}bool HasAura(unsigned id){return air&&id==18430;}Unit*GetVictim(){return victim;}
 bool IsPlayer(){return player;}float GetDistance(Player*);bool IsWithinLOSInMap(Player*);};
struct Player:Unit{unsigned map=533;bool member=true,tank=true,stunned=false,los=true;float distance=20;PlayerbotAI*brain=nullptr;
 unsigned GetMapId(){return map;}unsigned GetObjectGuid(){return guid;}PlayerbotAI*GetPlayerbotAI(){return brain;}
 bool hasUnitState(unsigned){return stunned;}};
float Unit::GetDistance(Player*p){return p->distance;}bool Unit::IsWithinLOSInMap(Player*p){return p->los;}
struct PlayerbotAI{Player*bot;bool real=false,movable=true;std::vector<Player*>roster;
 Player*GetBot(){return bot;}bool IsTank(Player*p){return p->tank;}bool IsRealPlayer(){return real;}bool CanMove(){return movable;}};
bool Engaged(Player*,Unit*u){return u&&u->engaged;}
bool Member(Player*,Player*p){return p&&p->member;}
std::vector<Player*> Members(PlayerbotAI*a,bool){std::vector<Player*> out;for(auto p:a->roster)if(p->member&&p->tank)out.push_back(p);return out;}
'''+block(source,'    Player* SapphironPickupTank(')+r'''
int main(){Player self,a,b,healer;self.player=a.player=b.player=healer.player=true;healer.tank=false;
 a.guid=11;b.guid=12;a.distance=26.51f;b.distance=25.93f;PlayerbotAI brain{&self},aa{&a},bb{&b};a.brain=&aa;b.brain=&bb;
 brain.roster={&a,&b};Unit boss;boss.victim=&healer;
#ifdef MANGOSBOT_ZERO
 assert(SapphironPickupTank(&brain,&boss)==&b); // Recorded healer-victim opening, closest available tank.
 boss.victim=&a;assert(!SapphironPickupTank(&brain,&boss)); // Do not steal an established tank hold.
 boss.victim=&healer;b.stunned=true;assert(SapphironPickupTank(&brain,&boss)==&a);b.stunned=false;
 b.los=false;assert(SapphironPickupTank(&brain,&boss)==&a);b.los=true;
 bb.real=true;assert(SapphironPickupTank(&brain,&boss)==&a);bb.real=false;
 bb.movable=false;assert(SapphironPickupTank(&brain,&boss)==&a);bb.movable=true;
 b.member=false;assert(SapphironPickupTank(&brain,&boss)==&a);b.member=true;
 b.distance=a.distance;brain.roster={&b,&a};assert(SapphironPickupTank(&brain,&boss)==&a);
 for(unsigned fault=0;fault<5;++fault){Unit copy=boss;self.map=533;
  if(fault==0)self.map=469;if(fault==1)copy.entry=11982;if(fault==2)copy.air=true;if(fault==3)copy.engaged=false;if(fault==4)copy.victim=nullptr;
  assert(!SapphironPickupTank(&brain,&copy));
 }
#else
 assert(!SapphironPickupTank(&brain,&boss));
#endif
 std::cout<<"PASS Sapphiron pickup tank ownership, unavailable/foreign roles, air/reset and era isolation\n";
}
'''
calculate=block(source,'ClassicRaidPlan ClassicRaidPlanValue::Calculate(')
assert calculate.index('if (SapphironPickupTank(ai,boss)==bot)')<calculate.index('if (KeepFormationRoute(')
assert 'SapphironPickupTank(ai,boss)==ai->GetBot()' in block(source,'bool ClassicRaidPositionAction::GetPlan(')
owned=block(source,'bool ClassicRaidPlanValue::OwnedSapphironTankStop(')
for guard in ('GetId()!=sapphironFormationSpline','CanReachWithMeleeAttack(boss)','ValidateEncounterDestination','SapphironPickupTank(ai,boss)!=bot'):
 assert guard in owned
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='sapphiron-pickup-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
