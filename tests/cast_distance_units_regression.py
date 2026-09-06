"""Actual coordinate-cast sight check against each core's real distance implementation."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/PlayerbotAI.cpp').read_text()
method=block(source,'bool PlayerbotAI::CanCastSpell(uint32 spellid, float')
check=block(method,'if (!itemTarget)')
for era,realm in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk')):
    core=root.parent/f'mangos-{realm}-behavior/src/game/Entities'
    assert 'distcalc = DIST_CALC_BOUNDING_RADIUS' in (core/'Object.h').read_text()
    distance=block((core/'Object.cpp').read_text(),'float WorldObject::GetDistance(float x, float y, float z,')
    code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
enum DistanceCalculation{DIST_CALC_NONE,DIST_CALC_BOUNDING_RADIUS,DIST_CALC_COMBAT_REACH,DIST_CALC_COMBAT_REACH_WITH_MELEE};
struct Position{float x=0,y=0,z=0;};
struct WorldObject{
 Position GetPosition(void*)const{return {};}
 void* GetTransport()const{return nullptr;}float GetObjectBoundingRadius()const{return 1;}
 float GetCombinedCombatReach(bool)const{return 2;}
 float GetDistance(float,float,float,DistanceCalculation=DIST_CALC_BOUNDING_RADIUS,bool=false)const;
};
__DISTANCE__
enum SpellCastResult{SPELL_CAST_OK,SPELL_FAILED_OUT_OF_RANGE};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
bool allowed(WorldObject* bot,float x,float y,float z,void* itemTarget,SpellCastResult* checkResult){
 __CHECK__
 return true;
}
int main(){
 WorldObject bot;SpellCastResult result=SPELL_CAST_OK;
 assert(allowed(&bot,3,4,0,nullptr,&result));
 assert(allowed(&bot,61,0,0,nullptr,&result));
 assert(!allowed(&bot,62,0,0,nullptr,&result)&&result==SPELL_FAILED_OUT_OF_RANGE);
 assert(!allowed(&bot,400,0,0,nullptr,nullptr)); // Old sqrt incorrectly accepted this.
 assert(allowed(&bot,400,0,0,&bot,nullptr)); // Existing item-target policy remains.
 assert(bot.GetDistance(3,4,0)==4); // Bounding radius returns linear distance.
 assert(bot.GetDistance(3,4,0,DIST_CALC_NONE)==25); // BG sqrt(NONE) is correct; do not change it.
 std::cout<<"PASS: native distance units, coordinate sight boundary, item policy and squared-distance distinction\n";
}
'''.replace('__DISTANCE__',distance).replace('__CHECK__',check)
    with tempfile.TemporaryDirectory(prefix='mantech-cast-distance-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
