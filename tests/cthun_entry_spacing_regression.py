"""Execute native CThun spacing scope and recorded waiting-point geometry."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
f=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <limits>
#include <iostream>
#include <vector>
#include <algorithm>
struct Unit{unsigned entry=15589;unsigned GetEntry(){return entry;}};
struct Player{unsigned map=531;unsigned GetMapId(){return map;}float GetCollisionHeight(){return 2;}};
struct PlayerbotAI{Player bot;bool ready=true;Player*GetBot(){return &bot;}};
bool Ready(PlayerbotAI* a){return a->ready;}bool engaged=true;bool Engaged(Player*,Unit*){return engaged;}
struct SpellTargetMgr{static float radius;static float GetJumpRadius(unsigned id){assert(id==26134||id==32950);return radius;}};float SpellTargetMgr::radius=10;
struct WorldPosition{unsigned map;float x,y,z;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 float distance(const WorldPosition&p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}};
struct Creature:Unit{unsigned map=531;float sight=60;unsigned GetMapId(){return map;}
 float GetPositionX(){return 0;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}
 bool IsWithinLOS(float x,float y,float,bool){return x<=sight&&std::fabs(y)<.01f;}};
__SPACING__
__ENTRY__
__ROUTE__
int main(){PlayerbotAI ai;Unit boss;
 assert(CthunEyeBeamSpacing(&ai,&boss)==11);engaged=false;assert(!CthunEyeBeamSpacing(&ai,&boss));engaged=true;
 boss.entry=15727;assert(!CthunEyeBeamSpacing(&ai,&boss));boss.entry=15589;
 for(unsigned map:{0u,409u,469u,489u,533u}){ai.bot.map=map;assert(!CthunEyeBeamSpacing(&ai,&boss));}ai.bot.map=531;
 ai.ready=false;assert(!CthunEyeBeamSpacing(&ai,&boss));ai.ready=true;
 for(float invalid:{0.f,-1.f,21.f,std::numeric_limits<float>::quiet_NaN()}){SpellTargetMgr::radius=invalid;assert(!CthunEyeBeamSpacing(&ai,&boss));}
 assert(!RaidLabEyeEntrySeparated(66.f,80.f,60.f,6.f,10.f)); // Recorded raid behind cover was nearer than entrant.
 assert(!RaidLabEyeEntrySeparated(90.f,79.f,12.f,6.f,10.f)); // Still within the chain envelope.
 assert(RaidLabEyeEntrySeparated(90.f,79.f,21.f,6.f,10.f));
 assert(!RaidLabEyeEntrySeparated(90.f,83.f,21.f,6.f,10.f)); // Formation edge can steal closest target.
 assert(!RaidLabEyeEntrySeparated(90.f,79.f,21.f,6.f,0.f));
 SpellTargetMgr::radius=10;Creature eye;std::vector<WorldPosition> route{{531,0,0,0},{531,90,0,0}};
 assert(RaidLabEyeEntryRoute(&eye,&ai.bot,route,6)); // First visible point60: isolated and closer than waiting formation.
 eye.sight=80;assert(!RaidLabEyeEntryRoute(&eye,&ai.bot,route,6)); // First visible point80 is still too near waiting team.
 route={{531,0,0,0},{531,80,0,0},{531,66,40,0}};
 assert(!RaidLabEyeEntryRoute(&eye,&ai.bot,route,6)); // Recorded topology: path goes farther around cover before LOS.
 eye.map=469;assert(!RaidLabEyeEntryRoute(&eye,&ai.bot,route,6));eye.map=531;
 assert(!RaidLabEyeEntryRoute(nullptr,&ai.bot,route,6));assert(!RaidLabEyeEntryRoute(&eye,nullptr,route,6));
 route={{531,0,0,0},{531,2000,0,0}};assert(!RaidLabEyeEntryRoute(&eye,&ai.bot,route,6));
 std::cout<<"PASS CThun native jump spacing, all-role scope, protected entry geometry and invalid metadata guards\n";
}
'''.replace('__SPACING__',block(s,'    float CthunEyeBeamSpacing(')).replace('__ENTRY__',block(f,'bool RaidLabEyeEntrySeparated(')).replace('__ROUTE__',block(f,'bool RaidLabEyeEntryRoute('))
plan=block(s,'ClassicRaidPlan ClassicRaidPlanValue::Calculate(')
assert 'if (eyeSpacing > 0) spacing = eyeSpacing;' in plan and '&& eyeSpacing <= 0' in plan
assert 'if (eyeSpacing > 0) p.spell = 26134;' in plan
assert 'CthunEyeBeamSpacing(ai, ai->GetUnit(eye.boss))' in block(s,'float PreserveClassicRaidPlan::GetValue(')
landing=block(f,'TestResult CommandRaidLabLanding::Execute(')
assert 'coveredEyePull && !RaidLabEyeEntryRoute' in landing
assert landing.index('!destination.isPathTo(route,1.0f,2.0f)') < landing.index('coveredEyePull && !RaidLabEyeEntryRoute')
with tempfile.TemporaryDirectory(prefix='cthun-spacing-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
