"""Run actual TravelPath clipping on dense and core-optimized corridors."""
from pathlib import Path
import subprocess
import sys
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/TravelNode.cpp').read_text()
header = (root / 'playerbot/TravelNode.h').read_text()
if '--before-fix' in sys.argv:
    source = source.replace('> 125.0f * 125.0f', '> 125')
classes = header[header.index('    enum class PathNodeType'):header.index('    //An stored A*')]
methods = '\n'.join(block(source, marker) for marker in (
    'bool TravelPath::cutTo', 'bool TravelPath::shouldMoveToNextPoint',
    'std::vector<PathNodePoint>::iterator TravelPath::getNextPoint', 'void TravelPath::ClipPath'))
code = r'''
#include <algorithm>
#include <cassert>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <list>
#include <map>
#include <sstream>
#include <vector>
using uint32=uint32_t;using uint8=uint8_t;
#define MANGOS_ASSERT(x) assert(x)
struct Unit {float x=0,y=0,z=0;unsigned map=489;bool dead=false;
 bool IsDead(){return dead;}unsigned GetLevel(){return 60;}float GetAttackDistance(Unit*){return 4;}
 bool CanAttackOnSight(Unit*){return true;}bool IsWithinLOSInMap(Unit*){return true;}};
struct WorldPosition {float x=0,y=0,z=0;unsigned map=489;
 WorldPosition()=default;WorldPosition(float x,float y=0,float z=0):x(x),y(y),z(z){}
 WorldPosition(Unit*u):x(u->x),y(u->y),z(u->z),map(u->map){}
 unsigned getMapId()const{return map;}
 float sqDistance(WorldPosition p)const{return (x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z);}
 float distance(WorldPosition p)const{return std::sqrt(sqDistance(p));}
 bool operator==(WorldPosition p)const{return x==p.x&&y==p.y&&z==p.z&&map==p.map;}
 float projectOnSegment(WorldPosition a,WorldPosition b)const{float d=a.sqDistance(b);return d?((x-a.x)*(b.x-a.x)+(y-a.y)*(b.y-a.y)+(z-a.z)*(b.z-a.z))/d:0;}
};
struct PlayerbotAI;
__CLASSES__
struct ObjectGuid {bool creature=true;bool IsCreature(){return creature;}};
using HazardPosition=std::pair<WorldPosition,float>;
struct AiObjectContext{};
enum class BotState{BOT_STATE_COMBAT};
struct PlayerbotAI {Unit* bot;Unit enemy;bool combat=false;AiObjectContext context;
 std::list<ObjectGuid> targets;std::list<HazardPosition> hazards;
 AiObjectContext* GetAiObjectContext(){return &context;}Unit*GetBot(){return bot;}
 Unit*GetUnit(ObjectGuid){return &enemy;}bool IsStateActive(BotState){return combat;}};
struct {float reactDistance=150;} sPlayerbotAIConfig;
#define AI_VALUE_LAZY(type,name) ai->targets
#define AI_VALUE(type,name) ai->hazards
__METHODS__
int main(){
 Unit bot;PlayerbotAI ai{&bot};
 for(unsigned map:{0u,489u,529u,30u,469u}){
  bot.map=map;
  for(float spacing:{4.f,12.f,20.f,28.f}){
   TravelPath path;std::vector<WorldPosition> points;
   for(float x=0;x<=112;x+=spacing){WorldPosition p(x);p.map=map;points.push_back(p);}
   path.addPath(points);path.ClipPath(&ai,&bot,false);
   if(path.getBack().x<84){std::cerr<<"FAIL: optimized corridor truncated at "<<path.getBack().x<<" spacing="<<spacing<<" map="<<map<<"\n";return 1;}
  }
 }
 bot.map=489;
 TravelPath edge;edge.addPath({WorldPosition(0.0f),WorldPosition(4),WorldPosition(129)});edge.ClipPath(&ai,&bot,false);assert(edge.getBack().x==129);
 TravelPath gap;gap.addPath({WorldPosition(0.0f),WorldPosition(4),WorldPosition(130)});gap.ClipPath(&ai,&bot,false);assert(gap.getBack().x==4);
 TravelPath bounded;bounded.addPath({WorldPosition(0.0f),WorldPosition(4),WorldPosition(100),WorldPosition(160),WorldPosition(200)});bounded.ClipPath(&ai,&bot,false);assert(bounded.getBack().x==160);
 ai.hazards={{{56},4}};TravelPath hazard;hazard.addPath({WorldPosition(0.0f),WorldPosition(28),WorldPosition(56),WorldPosition(84)});hazard.ClipPath(&ai,&bot,false);assert(hazard.getBack().x==56);
 ai.hazards.clear();ai.targets={{true}};ai.enemy.x=28;
 TravelPath enemy;enemy.addPath({WorldPosition(0.0f),WorldPosition(28),WorldPosition(56)});auto ignored=enemy;
 enemy.ClipPath(&ai,&bot,false);assert(enemy.getBack().x==28);
 ignored.ClipPath(&ai,&bot,true);assert(ignored.getBack().x==56);
 std::cout<<"PASS: optimized/dense paths advance; 125-yard discontinuity, reaction distance, hazards and hostile avoidance preserved\n";
}
'''.replace('__CLASSES__', classes).replace('__METHODS__', methods)
with tempfile.TemporaryDirectory(prefix='mantech-path-clip-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
    subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
