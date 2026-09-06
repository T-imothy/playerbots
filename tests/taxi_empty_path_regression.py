"""The native taxi generator starts empty; real empty fixed paths still warn."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

work=Path(__file__).resolve().parents[2]
code=r'''
#include <atomic>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
using uint32=uint32_t;enum{TAXI_MOTION_TYPE,FIXED_PATH_MOTION_TYPE,UNIT_STAT_ROAMING_MOVE};
namespace WorldTimer{uint32 now=100;uint32 getMSTime(){return now;}uint32 getMSTimeDiff(uint32 a,uint32 b){return b-a;}}
struct {int warnings=0;template<class... T>void outError(const char*,T...){++warnings;}}sLog;
struct Unit {int stops=0,clears=0;const char* GetName(){return "taxi bot";}unsigned GetEntry(){return 0;}unsigned GetDbGuid(){return 12;}
 void clearUnitState(int){++clears;}void StopMoving(bool){++stops;}};
struct Generator {std::vector<int> m_path,m_spline;int type=TAXI_MOTION_TYPE;
 int GetMovementGeneratorType(){return type;}void initializeEmpty(Unit& unit)__BLOCK__};
int main(){Unit bot;Generator generator;generator.initializeEmpty(bot);
 assert(sLog.warnings==0);assert(bot.stops==1&&bot.clears==1); // Preserve native setup/cleanup without a false alarm.
 generator.type=FIXED_PATH_MOTION_TYPE;generator.initializeEmpty(bot);assert(sLog.warnings==1);
 generator.initializeEmpty(bot);assert(sLog.warnings==1); // Retain the existing rate limit.
 WorldTimer::now+=60001;generator.initializeEmpty(bot);assert(sLog.warnings==2);
 std::cout<<"PASS: expected empty taxi initialization stays quiet; broken fixed paths still warn and stop\n";}
'''
with tempfile.TemporaryDirectory(prefix='mantech-taxi-empty-') as folder:
    tmp=Path(folder)
    for era in ('classic','tbc','wotlk'):
        core=work/('mangos-'+era+'-behavior')/'src/game/MotionGenerators'
        header=(core/'PathMovementGenerator.h').read_text()
        assert 'AbstractPathMovementGenerator(Movement::PointsArray(), std::nullopt)' in header
        method=block((core/'PathMovementGenerator.cpp').read_text(),'void AbstractPathMovementGenerator::Initialize(')
        guard=block(method,'if (m_path.empty())')
        (tmp/'test.cpp').write_text(code.replace('__BLOCK__','{'+guard+'}'))
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
