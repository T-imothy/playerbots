"""Execute native felfire setup with failed, stale and successful charge markers."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('tbc','wotlk'):
    source=next((root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts').rglob('boss_soccothrates.cpp')).read_text()
    methods='\n'.join(block(source,s).replace(' override','') for s in ('    void Reset()', '    void JustSummoned(', '    void SpellHitTarget(', '    void HandleFelfireLineup()', '    void OnSpellCast('))
    code=r'''
#include <cassert>
#include <cmath>
#include <map>
#include <iostream>
using uint32=unsigned;using uint8=unsigned char;
enum{CAST_OK=0,CAST_FAIL=1,SPELL_CAST_OK=255,TRIGGERED_OLD_TRIGGERED=1,ATTACKING_TARGET_RANDOM=0,SELECT_FLAG_PLAYER=1,NPC_WRATH_SCRYER_FELFIRE=20978};
__ENUMS__
struct ObjectGuid{unsigned id=0;void Clear(){id=0;}};struct SpellEntry{unsigned Id;};
struct Unit{unsigned entry=0;float x=0,y=0,z=100;unsigned moves=0;unsigned GetEntry(){return entry;}
 void NearTeleportTo(float a,float b,float c,float){x=a;y=b;z=c;++moves;}};
struct Creature;struct Map{std::map<unsigned,Creature*>actors;Creature*GetCreature(ObjectGuid g){return actors.count(g.id)?actors[g.id]:nullptr;}};
struct Creature:Unit{ObjectGuid guid;Map map;Unit*target=nullptr;bool alive=true,combat=true,lineFail=false;unsigned lineCasts=0;
 Map*GetMap(){return &map;}ObjectGuid GetObjectGuid(){return guid;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return 0;}
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}Unit*SelectAttackingTarget(unsigned,unsigned,std::nullptr_t,unsigned){return target;}
 unsigned CastSpell(Unit*,unsigned id,unsigned){assert(id==SPELL_FELFIRE_LINE_UP);++lineCasts;return lineFail?1:SPELL_CAST_OK;}
};
unsigned urand(unsigned a,unsigned){return a;}unsigned yells=0;void DoBroadcastText(int,Creature*,Unit*){++yells;}
struct CombatAI{void Reset(){}};
struct Boss:CombatAI{Creature*m_creature;Creature marker;ObjectGuid m_chargeTarget;uint8 m_lineUpCounter=0;bool m_isRegularMode=true,allocationFail=false;unsigned fail=0,summons=0;
 std::map<unsigned,unsigned>timers;
 void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}void SetCombatMovement(bool){}
 unsigned DoCastSpellIfCan(Unit*,unsigned id){if(id==fail)return CAST_FAIL;if(id==SPELL_CHARGE_TARGETING){++summons;if(!allocationFail){marker.entry=NPC_WRATH_SCRYER_CHARGE_TARGET;marker.guid.id=100+summons;marker.x=70;marker.y=140;m_creature->map.actors[marker.guid.id]=&marker;JustSummoned(&marker);}}return CAST_OK;}
 __METHODS__
};
int main(){Creature c;Unit player;player.entry=1;c.target=&player;Boss b;b.m_creature=&c;b.Reset();
 Unit fire;fire.entry=NPC_WRATH_SCRYER_FELFIRE;SpellEntry lineup{SPELL_FELFIRE_LINE_UP},knock{SPELL_KNOCK_AWAY},charge{SPELL_CHARGE};
 b.SpellHitTarget(&fire,&lineup);assert(fire.moves==0);
 c.target=nullptr;b.HandleFelfireLineup();assert(b.summons==0&&b.timers[SOCCOTHRATES_FELFIRE_LINEUP]==500);c.target=&player;
 b.fail=SPELL_CHARGE_TARGETING;b.HandleFelfireLineup();assert(b.summons==0&&c.lineCasts==0);b.fail=0;
 b.allocationFail=true;for(unsigned n=0;n<100;++n){b.HandleFelfireLineup();b.SpellHitTarget(&fire,&lineup);assert(c.lineCasts==0&&fire.moves==0&&b.m_chargeTarget.id==0);}
 b.allocationFail=false;c.lineFail=true;b.HandleFelfireLineup();auto summons=b.summons;assert(c.lineCasts==1&&yells==1);
 b.HandleFelfireLineup();assert(b.summons==summons&&c.lineCasts==2&&yells==1);
 c.lineFail=false;b.HandleFelfireLineup();assert(b.summons==summons&&c.lineCasts==3);
 for(unsigned n=1;n<=7;++n){b.SpellHitTarget(&fire,&lineup);assert(std::abs(fire.x-10*n)<0.001&&std::abs(fire.y-20*n)<0.001&&fire.z==100);}
 auto moves=fire.moves;b.SpellHitTarget(&fire,&lineup);assert(fire.moves==moves);
 b.HandleFelfireLineup();Unit other;other.entry=999;b.SpellHitTarget(&other,&lineup);assert(other.moves==0);
 b.SpellHitTarget(nullptr,&lineup);b.SpellHitTarget(nullptr,&charge);
 // Next knock-away must not reuse the previous marker while its actor still exists.
 b.OnSpellCast(&knock,nullptr);assert(!b.m_chargeTarget.id&&b.m_lineUpCounter==0&&b.timers[SOCCOTHRATES_FELFIRE_LINEUP]==2000);
 b.allocationFail=true;b.HandleFelfireLineup();b.SpellHitTarget(&fire,&lineup);assert(fire.moves==moves);
 b.allocationFail=false;b.HandleFelfireLineup();b.Reset();b.SpellHitTarget(&fire,&lineup);assert(fire.moves==moves);
 c.combat=false;summons=b.summons;b.HandleFelfireLineup();assert(b.summons==summons);
 c.combat=true;c.alive=false;b.HandleFelfireLineup();assert(b.summons==summons);
 std::cout<<"PASS: current-marker felfire positioning, failed allocation/casts, no duplicate retry summons, bounded line and reset guards\n";
}
'''.replace('__ENUMS__',block(source,'enum\n')+';\n'+block(source,'enum SoccothratesActions')+';').replace('__METHODS__',methods)
    with tempfile.TemporaryDirectory(prefix='soccothrates-marker-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
