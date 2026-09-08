"""Exercise native counter resets, repeated cast sequences and timer boundaries."""
from pathlib import Path
import subprocess,tempfile,re
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('classic','tbc','wotlk'):
    scripts=root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts'
    classes=[];checks=[]
    for name,filename,cls,enum,action,spell in (
        ('ouro','boss_ouro.cpp','boss_ouroAI','OuroActions','OURO_BOULDER','SPELL_BOULDER'),
        ('skeram','boss_skeram.cpp','boss_skeramAI','SkeramActions','SKERAM_EARTH_SHOCK','SPELL_EARTH_SHOCK')):
        source=next(scripts.rglob(filename)).read_text();boss=source[source.index('struct '+cls):]
        reset=block(boss,'    void Reset()').replace(' override','')
        action_code=block(boss,'            case '+action+':')
        classes.append('namespace '+name+'{'+block(source,'enum\n')+';'+block(source,'enum '+enum)+';struct Boss:Base{'+reset+'void ExecuteAction(unsigned action){switch(action){'+action_code+'}}};}')
        checks.append('''{
 N::Boss b;b.m_creature=&c;b.m_rangeCheckState=999;b.Reset();assert(b.m_rangeCheckState==-1);
 c.reachable=false;unsigned spell=N::S;b.ExecuteAction(N::A);b.ExecuteAction(N::A);assert(b.accepted[spell]==0);
 b.ExecuteAction(N::A);assert(b.accepted[spell]==1&&b.timers[N::A]==2500);
 c.reachable=true;b.ExecuteAction(N::A);assert(b.m_rangeCheckState==-1&&b.timers[N::A]==500);
 c.reachable=false;b.fail=spell;b.ExecuteAction(N::A);b.ExecuteAction(N::A);b.ExecuteAction(N::A);
 assert(b.accepted[spell]==1&&b.timers[N::A]==500);b.fail=0;b.ExecuteAction(N::A);assert(b.accepted[spell]==2);
 b.Reset();assert(b.m_rangeCheckState==-1);
}'''.replace('N::',name+'::').replace('::S','::'+spell).replace('::A','::'+action))
    if era!='classic':
        source=next(scripts.rglob('boss_gruul.cpp')).read_text()
        methods='\n'.join(block(source,s).replace(' override','') for s in ('    void Reset()', '    void SpellHitTarget('))
        action=block(source,'            case GRUUL_ACTION_GROUND_SLAM:')
        classes.append('namespace gruul{'+block(source,'enum\n')+';'+block(source,'enum GruulActions')+';struct Boss:Base{bool m_lookAround=true;'+methods+'void ExecuteAction(unsigned action){switch(action){'+action+'}}};}')
        checks.append('''{
 gruul::Boss b;b.m_creature=&c;b.Reset();assert(!b.m_lookAround);
 for(bool immediate:{true,false}){
  unsigned hits=0;c.castHook=[&](unsigned id){if(id==gruul::SPELL_LOOK_AROUND)++hits;if(immediate){SpellEntry spell{id};b.SpellHitTarget(&c,&spell);}};
  b.ExecuteAction(gruul::GRUUL_ACTION_GROUND_SLAM);if(!immediate){assert(b.m_lookAround);SpellEntry spell{gruul::SPELL_GROUND_SLAM};b.SpellHitTarget(&c,&spell);}
  assert(hits==1&&!b.m_lookAround);SpellEntry spell{gruul::SPELL_GROUND_SLAM};b.SpellHitTarget(&c,&spell);assert(hits==1);
 }
 c.castHook=nullptr;b.Reset();b.fail=gruul::SPELL_GROUND_SLAM_DUMMY;b.ExecuteAction(gruul::GRUUL_ACTION_GROUND_SLAM);assert(!b.m_lookAround);
}''')
        source=next(scripts.rglob('boss_kaelthas.cpp')).read_text()
        assert 'm_pyroblastCounter = 0;' in block(source,'    void Reset()')
        oncast=block(source,'    void OnSpellCast(')
        barrier=oncast[oncast.index('            case SPELL_SHOCK_BARRIER:'):oncast.index('            case SPELL_MIND_CONTROL:')]
        action=block(source,'            case KAEL_ACTION_PYROBLAST_SEQUENCE:')
        classes.append('namespace kael{'+block(source,'enum\n')+';'+block(source,'enum KaelThasActions')+';struct Boss:Base{unsigned m_uiPhase=PHASE_4_SOLO,m_pyroblastCounter=999;void Barrier(){switch(SPELL_SHOCK_BARRIER){'+barrier+'}}void ExecuteAction(unsigned action){switch(action){'+action+'}}};}')
        checks.append('''{
 kael::Boss b;b.m_creature=&c;
 for(unsigned wave=0;wave<100;++wave){b.disabled.clear();b.Barrier();assert(b.m_pyroblastCounter==0);auto before=b.accepted[kael::SPELL_PYROBLAST];
  for(unsigned cast=0;cast<3;++cast){b.fail=kael::SPELL_PYROBLAST;b.ExecuteAction(kael::KAEL_ACTION_PYROBLAST_SEQUENCE);
   assert(b.m_pyroblastCounter==cast&&b.disabled.empty());b.fail=0;b.ExecuteAction(kael::KAEL_ACTION_PYROBLAST_SEQUENCE);}
  assert(b.accepted[kael::SPELL_PYROBLAST]==before+3&&b.disabled.count(kael::KAEL_ACTION_PYROBLAST_SEQUENCE));
 }
 b.m_uiPhase=kael::PHASE_TRANSITION;auto before=b.accepted[kael::SPELL_PYROBLAST];b.ExecuteAction(kael::KAEL_ACTION_PYROBLAST_SEQUENCE);
 assert(b.accepted[kael::SPELL_PYROBLAST]==before);b.m_pyroblastCounter=2;b.Barrier();assert(b.m_pyroblastCounter==2);
}''')
    if era=='wotlk':
        source=next(scripts.rglob('boss_auriaya.cpp')).read_text();boss=source[source.index('struct boss_feral_defenderAI'):]
        initializer=re.search(r'm_maxFeralRush\((m_isRegularMode \? \d+ : \d+)\)',boss)[1]
        reset=block(boss,'    void Reset()').replace(' override','')
        action=block(boss,'    void ExecuteAction(').replace(' override','')
        classes.append('namespace feral{'+block(source,'enum\n')+';'+block(source,'enum FeralDefenderActions')+';struct Boss:Base{bool m_isRegularMode;unsigned m_feralRushCount=999,m_maxFeralRush,m_deathCount=999;Boss(bool normal):m_isRegularMode(normal),m_maxFeralRush('+initializer+'){}'+reset+action+'};}')
        checks.append('''{
 for(bool normal:{true,false}){feral::Boss b(normal);b.m_creature=&c;b.Reset();assert(b.m_feralRushCount==0&&b.m_maxFeralRush==(normal?6:10));
  for(unsigned wave=0;wave<100;++wave)for(unsigned n=0;n<b.m_maxFeralRush;++n){
   b.fail=normal?feral::SPELL_FERAL_RUSH:feral::SPELL_FERAL_RUSH_H;b.ExecuteAction(feral::FERAL_DEFENDER_FERAL_RUSH);assert(b.m_feralRushCount==n);
   b.fail=0;b.ExecuteAction(feral::FERAL_DEFENDER_FERAL_RUSH);assert(b.timers[feral::FERAL_DEFENDER_FERAL_RUSH]==(n+1<b.m_maxFeralRush?400:12000));
  }
  b.Reset();assert(b.m_feralRushCount==0&&b.m_deathCount==0);
 }
}''')
        source=next(scripts.rglob('boss_halion.cpp')).read_text();boss=source[source.index('struct boss_halion_realAI'):]
        reset=block(boss,'    void Reset()').replace(' override','')
        start=boss.index('                if (m_uiFlameBreathTimer < uiDiff)')
        end=boss.index('m_uiFlameBreathTimer -= uiDiff;',start)+len('m_uiFlameBreathTimer -= uiDiff;')
        classes.append('namespace halion{'+block(source,'enum\n')+';struct Boss:Base{unsigned m_uiPhase=0,m_uiTailLashTimer=0,m_uiCleaveTimer=0,m_uiFieryCombustionTimer=0,m_uiMeteorTimer=0,m_uiFlameBreathTimer=999;'+reset+'void Tick(unsigned uiDiff){'+boss[start:end]+'}};}')
        checks.append('''{
 halion::Boss b;b.m_creature=&c;b.Reset();assert(b.m_uiFlameBreathTimer==15000);b.Tick(14999);assert(b.accepted[halion::SPELL_FLAME_BREATH]==0);
 b.fail=halion::SPELL_FLAME_BREATH;b.Tick(2);assert(b.m_uiFlameBreathTimer==1);b.fail=0;b.Tick(2);assert(b.accepted[halion::SPELL_FLAME_BREATH]==1&&b.m_uiFlameBreathTimer==15000);
 b.Reset();assert(b.m_uiFlameBreathTimer==15000);
}''')
    code=r'''
#include <cassert>
#include <map>
#include <set>
#include <vector>
#include <chrono>
#include <iostream>
#include <functional>
using uint32=unsigned;using int32=int;using namespace std::chrono_literals;
enum{CAST_OK=0,CAST_FAIL=1,ATTACKING_TARGET_RANDOM=0,SELECT_FLAG_PLAYER=1,TRIGGERED_NONE=0};
struct SpellEntry{unsigned Id;};
struct Unit{};struct Creature:Unit{Unit*victim=nullptr;bool reachable=false;Unit*GetVictim(){return victim;}
 std::function<void(unsigned)>castHook;void CastSpell(Unit*,unsigned id,unsigned){if(castHook)castHook(id);}void SetTarget(Unit*){}
 bool CanReachWithMeleeAttack(Unit*){return reachable;}Unit*SelectAttackingTarget(unsigned,unsigned,unsigned,unsigned){return victim;}};
unsigned urand(unsigned a,unsigned){return a;}void DoBroadcastText(int,Creature*){}void DoScriptText(int,Creature*){}
struct CombatAI{void Reset(){}};
struct Base:CombatAI{Creature*m_creature;int32 m_rangeCheckState=999;unsigned m_burrowCounter=999,m_maxMeleeAllowed=0,m_teleportCounter=0,fail=0;
 float m_hpCheck=0;std::vector<unsigned>m_teleports;std::map<unsigned,unsigned>accepted,timers;std::set<unsigned>disabled;
 unsigned DoCastSpellIfCan(Unit*,unsigned id){if(id==fail)return CAST_FAIL;++accepted[id];return CAST_OK;}
 void SetCombatMovement(bool){}void SetMeleeEnabled(bool){}void DisableCombatAction(unsigned id){disabled.insert(id);}
 void SetActionReadyStatus(unsigned,bool){}
 void ResetCombatAction(unsigned id,unsigned delay){timers[id]=delay;}
 template<class R,class P>void ResetCombatAction(unsigned id,std::chrono::duration<R,P>d){timers[id]=std::chrono::duration_cast<std::chrono::milliseconds>(d).count();}
};
__CLASSES__
int main(){Creature c;Unit victim;c.victim=&victim;__CHECKS__
 std::cout<<"PASS: native encounter initialization, repeated sequence limits and rejected-cast retries\n";}
'''.replace('__CLASSES__','\n'.join(classes)).replace('__CHECKS__','\n'.join(checks))
    with tempfile.TemporaryDirectory(prefix='encounter-counters-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
