"""Run the actual Majordomo outro through rejected casts and missing summons."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('classic','tbc','wotlk'):
    source=next((root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts').rglob('boss_majordomo_executus.cpp')).read_text()
    code=r'''
#include <cassert>
#include <map>
#include <iostream>
using uint32=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,SPELL_CAST_OK=255,TRIGGERED_NONE=0,HOUR=3600,IN_MILLISECONDS=1000,
 TEMPSPAWN_TIMED_OOC_OR_DEAD_DESPAWN=0,NPC_RAGNAROS=11502,GO_LAVA_SPLASH=1,GO_LAVA_STEAM=2,EMOTE_ONESHOT_ROAR=1};
__ENUMS__
struct GameObject{void SetRespawnTime(unsigned){}void Refresh(){}};
struct Motion{void MovePoint(unsigned,float,float,float){}};
struct Creature;struct Map{Creature*rag=nullptr;Creature*GetCreature(unsigned){return rag;}};
struct Creature{Map map;Motion motion;bool summonFail=false,castFail=false;unsigned summons=0,kills=0;
 Map*GetMap(){return &map;}Motion*GetMotionMaster(){return &motion;}void SetFacingToObject(GameObject*){}void HandleEmote(unsigned){}
 Creature*SummonCreature(unsigned,float,float,float,float,unsigned,unsigned){++summons;if(summonFail)return nullptr;map.rag=this;return this;}
 unsigned CastSpell(Creature*,unsigned,unsigned){if(castFail)return 1;++kills;return SPELL_CAST_OK;}
};
void DoScriptText(int,Creature*){}
struct Instance{GameObject go;bool missing=false;GameObject*GetSingleGameObjectFromStorage(unsigned){return missing?nullptr:&go;}};
struct Boss{Creature*m_creature;Instance*m_instance=nullptr;unsigned m_speechStage=0,m_ragnarosGuid=1,fail=0,unsummons=0;
 std::map<unsigned,unsigned>timers;
 unsigned DoCastSpellIfCan(Creature*,unsigned id){return id==fail?CAST_FAIL:CAST_OK;}
 void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}void UnsummonMajordomoAdds(){++unsummons;}
 __METHOD__
};
int main(){Creature c;Instance instance;Boss b;b.m_creature=&c;b.m_instance=&instance;
 b.m_speechStage=4;b.fail=SPELL_TELEPORT_SELF;for(unsigned n=0;n<100;++n){b.HandleOutro();assert(b.m_speechStage==4&&b.timers[MAJORDOMO_OUTRO]==500&&b.unsummons==0);}
 b.fail=0;b.HandleOutro();assert(b.m_speechStage==5&&b.timers[MAJORDOMO_OUTRO]==900);b.HandleOutro();assert(b.unsummons==1&&b.m_speechStage==0);
 b.m_speechStage=13;b.m_instance=nullptr;b.HandleOutro();assert(c.summons==0&&b.m_speechStage==13);
 b.m_instance=&instance;instance.missing=true;b.HandleOutro();assert(c.summons==0&&b.m_speechStage==13);
 instance.missing=false;c.summonFail=true;b.HandleOutro();assert(c.summons==1&&b.m_speechStage==13);
 c.summonFail=false;b.HandleOutro();assert(c.summons==2&&b.m_speechStage==14&&b.timers[MAJORDOMO_OUTRO]==8700);
 b.m_speechStage=13;b.HandleOutro();assert(c.summons==2&&b.m_speechStage==14);
 b.m_speechStage=17;c.castFail=true;b.HandleOutro();assert(b.m_speechStage==17&&c.kills==0);
 c.map.rag=nullptr;b.HandleOutro();assert(b.m_speechStage==17);
 c.map.rag=&c;c.castFail=false;b.HandleOutro();assert(b.m_speechStage==0&&c.kills==1);
 std::cout<<"PASS: Majordomo failed teleport, missing object/boss, rejected summon/kill cast and duplicate summon guard\n";
}
'''.replace('__ENUMS__',block(source,'enum\n')+';\n'+block(source,'enum MajordomoActions')+';').replace('__METHOD__',block(source,'    void HandleOutro()'))
    with tempfile.TemporaryDirectory(prefix='majordomo-event-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
