"""Compile every encounter arrival predicate against retained native movement state.

This exercises actual action bodies, not simulated boss encounter success.
"""
from pathlib import Path
import subprocess,sys,tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
base=root/'playerbot/strategy'
specs=[('DungeonActions.cpp','GruulSpreadAction',1.5),('DungeonActions.cpp','BossCastPositionAction',1.5),
 ('BlackwingLairDungeonActions.cpp','BlackwingLairPositionAction',1.5),('NaxxramasDungeonActions.cpp','NaxxramasPositionAction',1.5),
 ('MechanarDungeonActions.cpp','MechanarPositionAction',1.5),('KarazhanDungeonActions.cpp','NetherspitePositionAction',1),
 ('TempestKeepActions.cpp','SolarianPositionAction',1.5),('BossCoverAction.cpp','BossCoverAction',1.5),
 ('RotatingBeamAction.cpp','RotatingBeamAction',1),('HeiganDanceAction.cpp','HeiganDanceAction',1),
 ('LinkedBurstAction.cpp','LinkedBurstAction',1),('AkilzonStormAction.cpp','AkilzonStormAction',1),
 ('HakkarPoisonAction.cpp','HakkarPoisonAction',1),('OssirianCrystalAction.cpp','OssirianCrystalAction',1),
 ('OnyxiasLairDungeonActions.cpp','OnyxiaPositionAction',1.5),('MoltenCoreDungeonActions.cpp','MoltenCorePositionAction',1.5)]
declarations=[];methods=[];cases=[]
helper=block((base/'values/EncounterPositionValue.cpp').read_text(),'bool ai::EncounterMovementRequired(')
for file,cls,tolerance in specs:
    source=(base/'actions'/file).read_text()
    if '--before' in sys.argv:
        source=subprocess.check_output(['git','-C',str(root),'show','HEAD:playerbot/strategy/actions/'+file],text=True)
    methods.append(block(source,'bool '+cls+'::isUseful('))
    declarations.append('struct '+cls+''' {PlayerbotAI* ai;Player* bot;
 static bool GetPlan(PlayerbotAI*a,EncounterPosition&p){p=a->plan;return a->active;}
 static bool GetPlan(PlayerbotAI*a,EncounterPosition&p,encounter::RotatingBeam&){return GetPlan(a,p);}
 bool ShouldReactionInterruptCast(){return ai->urgent;}bool isUseful();};''')
    cases.append('''{
 '''+cls+''' action{&brain,&bot};brain.active=true;brain.plan={};bot.x=bot.y=bot.z=0;bot.casting=false;
 bot.stopped=false;bot.motion.kind=1;bot.spline.done=true;
 assert(!action.isUseful()); // retained flags/generator do not consume combat frames
 bot.movespline=nullptr;assert(!action.isUseful());bot.movespline=&bot.spline;
 bot.spline.done=false;bot.spline.end={0,0,0};assert(!action.isUseful()); // in-place facing spline
 bot.spline.end={10,0,0};assert(action.isUseful()); // stop a route carrying us beyond the station
 bot.spline.done=true;bot.x=10;assert(action.isUseful()); // actual correction remains eligible
 brain.active=false;assert(!action.isUseful());brain.active=true;bot.x=0;
}''')
code=r'''
#include <cassert>
#include <iostream>
#include <limits>
#include "__GEOMETRY__"
namespace ai::encounter{struct RotatingBeam{};}
struct Motion{int kind=1;int GetCurrentMovementGeneratorType(){return kind;}};
struct Spline{bool done=true;struct End{float x=0,y=0,z=0;};End end;
 bool Finalized(){return done;}End FinalDestination(){return end;}};
struct Player;
struct Unit{Player* victim=nullptr;Player* GetVictim(){return victim;}};
struct Player{float x=0,y=0,z=0;bool stopped=false,casting=false;Motion motion;Spline spline;Spline*movespline=&spline;
 bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}
 bool IsNonMeleeSpellCasted(bool,bool=false,bool=false){return casting;}unsigned GetObjectGuid(){return 7;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}};
constexpr int IDLE_MOTION_TYPE=0;
namespace ai{struct EncounterPosition{bool exclusive=true;unsigned spell=0,boss=1,source=0;encounter::Point destination;};
 bool EncounterMovementRequired(Player*,const encounter::Point&,float=1.5f);}
struct PlayerbotAI{bool active=true,urgent=false;ai::EncounterPosition plan;Unit boss;Unit*GetUnit(unsigned){return &boss;}};
bool OssirianNeedsCrystal(Unit*){return false;}
using namespace ai;
__DECLARATIONS__
__HELPER__
__METHODS__
int main(){Player bot;PlayerbotAI brain;
__CASES__
 assert(!EncounterMovementRequired(nullptr,{0,0,0}));
 assert(!EncounterMovementRequired(&bot,{std::numeric_limits<float>::quiet_NaN(),0,0}));
 assert(!EncounterMovementRequired(&bot,{0,0,0},-1));
 // Arrival must not cancel a valid channel while recovering Loken's close phase.
 BossCastPositionAction loken{&brain,&bot};brain.plan.spell=59414;bot.x=10;bot.casting=true;assert(!loken.isUseful());
#ifdef MANGOSBOT_ZERO
 OnyxiaPositionAction onyxia{&brain,&bot};brain.plan.spell=18392;brain.plan.source=0;
 assert(!onyxia.isUseful()); // routine air spacing waits for a valid cast
 brain.plan.source=bot.GetObjectGuid();assert(onyxia.isUseful()); // targeted Fireball may interrupt
 brain.plan.spell=17086;brain.plan.source=0;assert(onyxia.isUseful()); // Deep Breath takes priority
#endif
 std::cout<<"PASS actual arrival predicates for 16 raid/dungeon movement actions, native spline/facing, expiry and Loken casting\n";
}
'''.replace('__GEOMETRY__',(base/'EncounterGeometry.h').as_posix()).replace('__DECLARATIONS__','\n'.join(declarations))
code=code.replace('__HELPER__',helper).replace('__METHODS__','\n'.join(methods)).replace('__CASES__','\n'.join(cases))
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='encounter-arrival-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
# Every currently registered encounter arrival check must use this predicate.
for source in (base/'actions').glob('*Action*.cpp'):
    text=source.read_text()
    for match in __import__('re').finditer(r'bool (\w+)::isUseful\(',text):
        cls=match.group(1)
        if any(cls==item[1] for item in specs):
            assert 'EncounterMovementRequired' in block(text,match.group(0)),cls
