"""Execute native allowed-height adjustment against different source/destination maps."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
for era in ('classic','tbc','wotlk'):
    native=root.parent/f'mangos-{era}-behavior/src/game/Entities/Unit.cpp'
    method=block(native.read_text(),'void Unit::UpdateAllowedPositionZ(')
    code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
constexpr float INVALID_HEIGHT=-100000;
constexpr int SPELL_AURA_WATER_WALK=1;
struct Terrain {
 float water=120,seenGround=0;unsigned calls=0;bool swim=false;
 float GetWaterOrGroundLevel(float x,float y,float z,float& ground,bool swimming,float collision){
  assert(x==10&&y==20&&collision==2);++calls;seenGround=ground;swim=swimming;
  return ground<=INVALID_HEIGHT?ground:std::max(ground,water-(swimming?collision:0));
 }
};
struct Map {
 float floor;unsigned calls=0;bool lastVmaps=false;unsigned phase=0;Terrain terrain;
 explicit Map(float height):floor(height){}
 float GetHeight(float x,float y,float,bool vmaps=true){assert(x==10&&y==20);++calls;lastVmaps=vmaps;return floor;}
 float GetHeight(unsigned mask,float x,float y,float z,bool vmaps=true){phase=mask;return GetHeight(x,y,z,vmaps);}
 Terrain*GetTerrain(){return &terrain;}
};
struct Unit {
 Map*current;bool flying=false,swimming=false,waterWalk=false;float hover=0;
 Map*GetMap()const{return current;}bool CanFly()const{return flying;}bool CanSwim()const{return swimming;}
 bool HasAuraType(int spell)const{assert(spell==SPELL_AURA_WATER_WALK);return waterWalk;}
 float GetCollisionHeight()const{return 2;}unsigned GetPhaseMask()const{return 7;}float GetHoverOffset()const{return hover;}
 void UpdateAllowedPositionZ(float x,float y,float& z,Map*atMap=nullptr)const;
};
__METHOD__
int main(){
 Map current(40),destination(100);Unit unit{&current};float z=45;
 unit.UpdateAllowedPositionZ(10,20,z,&destination);
 assert(z==100&&current.calls==0&&destination.calls==1&&!destination.lastVmaps);
 // Default-map calls retain the existing ground clamp.
 z=80;unit.UpdateAllowedPositionZ(10,20,z);assert(z==40&&current.calls==1);
 // A swimmer must combine ground and water from the same requested map.
 current.calls=0;unit.swimming=true;z=90;unit.UpdateAllowedPositionZ(10,20,z,&destination);
 assert(z==100&&current.calls==0&&destination.lastVmaps&&destination.terrain.seenGround==100);
 z=130;unit.UpdateAllowedPositionZ(10,20,z,&destination);assert(z==118&&destination.terrain.swim);
 z=110;unit.UpdateAllowedPositionZ(10,20,z,&destination);assert(z==110);
 unit.waterWalk=true;z=130;unit.UpdateAllowedPositionZ(10,20,z,&destination);assert(z==120&&!destination.terrain.swim);
 // Flying uses destination ground but does not pull a flying unit down to it.
 unit.flying=true;z=90;unit.UpdateAllowedPositionZ(10,20,z,&destination);assert(z==100);
 z=130;unit.UpdateAllowedPositionZ(10,20,z,&destination);assert(z==130);
 // Preserve invalid-height handling and Wrath's existing hover offset.
 unit.flying=false;unit.swimming=false;destination.floor=INVALID_HEIGHT;z=90;
 unit.UpdateAllowedPositionZ(10,20,z,&destination);assert(z==90);
#ifdef WRATH
 destination.floor=100;unit.hover=0.75f;z=90;unit.UpdateAllowedPositionZ(10,20,z,&destination);
 assert(z==100.75f&&destination.phase==7);
#endif
 std::cout<<"PASS: native destination-map ground, water, flying, default-map and hover behavior\n";
}
'''.replace('__METHOD__',method)
    with tempfile.TemporaryDirectory(prefix=f'mantech-height-context-{era}-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        flags=['/DWRATH'] if era=='wotlk' else []
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',*flags,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
