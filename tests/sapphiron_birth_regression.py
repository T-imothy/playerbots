"""Replay player arrivals during the native Sapphiron birth timer (Classic)."""
from pathlib import Path
import argparse, subprocess, tempfile
from behavior_regression import block

parser=argparse.ArgumentParser();parser.add_argument('--core',type=Path,required=True);args=parser.parse_args()
source=(args.core/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/naxxramas/naxxramas.cpp').read_text()
enter=block(source,'void instance_naxxramas::OnPlayerEnter(')
timer=block(source,'    if (m_sapphironSpawnTimer)')
code=r'''
#include <cassert>
#include <iostream>
constexpr unsigned TYPE_SAPPHIRON=13,NPC_SAPPHIRON=15989,NOT_STARTED=0,IN_PROGRESS=1,DONE=3,SPECIAL=4,TEMPSPAWN_DEAD_DESPAWN=0;
float sapphironPositions[4]={0,0,0,0};
struct instance_naxxramas;
struct Player {instance_naxxramas* owner;void SummonCreature(unsigned,float,float,float,float,unsigned,unsigned);};
struct instance_naxxramas {
 unsigned state=NOT_STARTED,m_sapphironSpawnTimer=0,summons=0;bool present=false;
 Player player{this};bool playerPresent=true;
 unsigned GetData(unsigned id){assert(id==TYPE_SAPPHIRON);return state;}
 Player*GetPlayerInMap(){return playerPresent?&player:nullptr;}
 bool GetSingleCreatureFromStorage(unsigned id,bool){assert(id==NPC_SAPPHIRON);return present;}
 void OnPlayerEnter(Player*);
 void UpdateBirth(unsigned diff){__TIMER__}
};
void Player::SummonCreature(unsigned id,float,float,float,float,unsigned,unsigned){assert(id==NPC_SAPPHIRON);++owner->summons;owner->present=true;}
__ENTER__
int main(){
 instance_naxxramas raid;raid.state=SPECIAL;raid.m_sapphironSpawnTimer=22000;
 // Players entering during the real animation cannot bypass the summon timer.
 for(int n=0;n<40;++n)raid.OnPlayerEnter(&raid.player);
 assert(raid.summons==0);
 raid.UpdateBirth(21000);assert(raid.summons==0);
 raid.OnPlayerEnter(&raid.player);assert(raid.summons==0);
 raid.UpdateBirth(1000);assert(raid.summons==1&&raid.m_sapphironSpawnTimer==0);
 for(int n=0;n<40;++n)raid.OnPlayerEnter(&raid.player);
 raid.UpdateBirth(30000);assert(raid.summons==1);
 // Persisted SPECIAL after reload restores exactly one boss, as before.
 raid.present=false;raid.OnPlayerEnter(&raid.player);assert(raid.summons==2);
 raid.OnPlayerEnter(&raid.player);assert(raid.summons==2);
 // A pending timer cannot duplicate a boss already registered in this map.
 raid.m_sapphironSpawnTimer=1;raid.UpdateBirth(1);assert(raid.summons==2);
 raid.present=false;raid.state=DONE;raid.m_sapphironSpawnTimer=1;
 raid.UpdateBirth(1);raid.OnPlayerEnter(&raid.player);assert(raid.summons==2);
 raid.state=NOT_STARTED;raid.OnPlayerEnter(&raid.player);assert(raid.summons==2);
 raid.state=SPECIAL;raid.playerPresent=false;raid.m_sapphironSpawnTimer=1;
 raid.UpdateBirth(1);assert(raid.summons==2);
 raid.playerPresent=true;raid.OnPlayerEnter(&raid.player);assert(raid.summons==3);
 std::cout<<"PASS native Sapphiron summon delay, arriving raid, reload recovery and duplicate guards\n";
}
'''.replace('__TIMER__',timer).replace('__ENTER__',enter)
with tempfile.TemporaryDirectory(prefix='sapphiron-birth-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
