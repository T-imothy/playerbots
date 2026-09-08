"""Run native shield-orb allocation and death callbacks with partial waves."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('tbc','wotlk'):
    source=next((root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts').rglob('boss_kiljaeden.cpp')).read_text()
    boss=source[source.index('struct boss_kiljaedenAI'):]
    reset=block(boss,'    void Reset()')
    assert 'm_uiShieldOrbCount = 0;' in reset and 'DespawnGuids(m_freeShieldOrbs);' in reset and 'm_freeShieldOrbs.resize(3);' in reset
    methods='\n'.join(block(boss,s).replace(' override','') for s in ('    void JustSummoned(', '    void SummonedCreatureJustDied(', '    uint32 GetFirstFreeShieldOrbIndex()'))
    action=boss[boss.index('            case KILJAEDEN_SHIELD_ORB:'):boss.index('            case KILJAEDEN_SOUL_FLAY:')]
    code=r'''
#include <cassert>
#include <functional>
#include <map>
#include <vector>
#include <memory>
#include <iostream>
using uint32=unsigned;
enum{NPC_KALECGOS=1,TRIGGERED_OLD_TRIGGERED=1,PATH_NO_PATH=0,FORCED_MOVEMENT_NONE=0,REACT_PASSIVE=0,TEMPSPAWN_CORPSE_DESPAWN=0};
__ENUMS__
struct ObjectGuid{unsigned id=0;ObjectGuid()=default;ObjectGuid(unsigned v):id(v){}bool IsEmpty()const{return !id;}bool operator==(const ObjectGuid&o)const{return id==o.id;}};
struct Position{float x,y,z,o;};
struct Motion{unsigned path=0;void Clear(bool,bool){}void MovePath(unsigned p,unsigned,unsigned,bool,float,bool){assert(p>=1&&p<=3);path=p;}};
struct AI{void SetReactState(unsigned){}void SetCombatMovement(bool){}};
struct Creature{unsigned entry=0,id=0,nextId=1,spawns=0;int failAt=-1;bool despawned=false;Motion motion;struct AI ai;
 std::function<void(Creature*)>callback;std::vector<std::unique_ptr<Creature>>children;
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return ObjectGuid(id);}void CastSpell(Creature*,unsigned,unsigned){}
 struct AI*AI(){return &ai;}Motion*GetMotionMaster(){return &motion;}void SetInCombatWithZone(){}void ForcedDespawn(){despawned=true;}
 Creature*SummonCreature(unsigned e,float,float,float,float,unsigned,unsigned){if(int(spawns)==failAt)return nullptr;
  auto c=std::make_unique<Creature>();c->entry=e;c->id=nextId++;Creature*raw=c.get();children.push_back(std::move(c));++spawns;callback(raw);return raw;}
};
struct Boss{Creature*m_creature;unsigned m_uiMaxShieldOrbs=3,m_uiShieldOrbCount=0;std::vector<ObjectGuid>m_freeShieldOrbs=std::vector<ObjectGuid>(3);
 bool canAct=true;std::map<unsigned,unsigned>timers;void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}
 void ResetCombatAction(unsigned id,unsigned delay){timers[id]=delay;}bool CanExecuteCombatAction(){return canAct;}
 __METHODS__
 void ExecuteAction(unsigned action){switch(action){__ACTION__}}
};
int main(){Creature c;Boss b;b.m_creature=&c;c.callback=[&](Creature*p){b.JustSummoned(p);};
 c.failAt=1;b.ExecuteAction(KILJAEDEN_SHIELD_ORB);assert(c.spawns==1&&b.m_uiShieldOrbCount==1&&b.timers[KILJAEDEN_SHIELD_ORB]==500);
 for(unsigned n=0;n<100;++n)b.ExecuteAction(KILJAEDEN_SHIELD_ORB);assert(c.spawns==1&&b.m_uiShieldOrbCount==1);
 c.failAt=-1;b.ExecuteAction(KILJAEDEN_SHIELD_ORB);assert(c.spawns==3&&b.m_uiShieldOrbCount==3&&b.timers[KILJAEDEN_SHIELD_ORB]==45000);
 Creature unknown;unknown.entry=NPC_SHIELD_ORB;unknown.id=999;b.SummonedCreatureJustDied(&unknown);assert(b.m_uiShieldOrbCount==3);
 Creature*first=c.children[0].get();b.SummonedCreatureJustDied(first);b.SummonedCreatureJustDied(first);assert(b.m_uiShieldOrbCount==2);
 b.ExecuteAction(KILJAEDEN_SHIELD_ORB);assert(c.spawns==4&&b.m_uiShieldOrbCount==3&&c.children.back()->motion.path==1);
 b.SummonedCreatureJustDied(first);assert(b.m_uiShieldOrbCount==3);
 // A corrupt requested count cannot index beyond the three native positions.
 b.m_uiMaxShieldOrbs=5;b.ExecuteAction(KILJAEDEN_SHIELD_ORB);assert(c.spawns==4&&b.m_uiShieldOrbCount==3);
 b.JustSummoned(&unknown);assert(unknown.despawned&&b.m_uiShieldOrbCount==3);
 for(auto&child:c.children)b.SummonedCreatureJustDied(child.get());assert(b.m_uiShieldOrbCount==0);
 b.SummonedCreatureJustDied(first);assert(b.m_uiShieldOrbCount==0);
 b.canAct=false;b.ExecuteAction(KILJAEDEN_SHIELD_ORB);assert(c.spawns==4);
 std::cout<<"PASS: shield orb partial allocation, matched deaths, duplicate/old callbacks, slot reuse and capacity bounds\n";
}
'''.replace('__ENUMS__',block(source,'enum\n')+';\n'+block(source,'enum KiljaedenActions')+';').replace('__METHODS__',methods).replace('__ACTION__',action)
    with tempfile.TemporaryDirectory(prefix='kiljaeden-orbs-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
