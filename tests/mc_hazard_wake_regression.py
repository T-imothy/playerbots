"""Execute the actual urgent-fire wake repeatedly without admitting movement."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
method = block((root/'playerbot/PlayerbotAI.cpp').read_text(), 'void PlayerbotAI::PrepareForUrgentHazard(')
code = r'''
#include <cassert>
#include <string>
#include <iostream>
enum class BotState { BOT_STATE_COMBAT };
struct Player {
 bool world=true,alive=true,teleport=false,charmed=false,casting=true;unsigned map=409,interrupts=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}
 unsigned GetMapId(){return map;}void InterruptNonMeleeSpells(bool){++interrupts;casting=false;}
};
struct ReactionEngine {unsigned wakes=0;void NotifyHazard(){++wakes;}};
struct PlayerbotAI {
 Player*bot;ReactionEngine*reactionEngine;bool human=false,magmadar=false,isWaiting=true;unsigned resets=0;
 bool IsRealPlayer(){return human;}bool HasStrategy(const char*name,BotState){return magmadar&&std::string(name)=="magmadar";}
 void ResetAIInternalUpdateDelay(){++resets;}void PrepareForUrgentHazard();
};
__METHOD__
int main(){
 Player bot;ReactionEngine reaction;PlayerbotAI ai{&bot,&reaction};
 // Gehennas: repeated fire polls with rejected escape paths must not repeatedly cancel a heal.
 for(unsigned n=0;n<100;++n)ai.PrepareForUrgentHazard();
#ifdef MANGOSBOT_ZERO
 assert(bot.casting&&bot.interrupts==0);
#else
 assert(!bot.casting&&bot.interrupts==100); // no expansion behavior change
#endif
 assert(reaction.wakes==100&&ai.resets==100&&!ai.isWaiting);
 // Existing Magmadar protection remains in every era.
 bot.casting=true;ai.magmadar=true;auto before=bot.interrupts;
 ai.PrepareForUrgentHazard();assert(bot.casting&&bot.interrupts==before);
 ai.magmadar=false;
 // Other maps retain their previous behavior; calling a wake does not teleport or move.
 for(unsigned map:{0,1,229,230,489,529,30,531,533,309,509,249,469}){
  bot.map=map;bot.casting=true;before=bot.interrupts;
  ai.PrepareForUrgentHazard();assert(!bot.casting&&bot.interrupts==before+1);
 }
 bot.map=409;
 for(unsigned condition=0;condition<5;++condition){
  bot.world=condition!=0;bot.alive=condition!=1;bot.teleport=condition==2;
  bot.charmed=condition==3;ai.human=condition==4;bot.casting=true;
  before=reaction.wakes;auto resets=ai.resets;
  ai.PrepareForUrgentHazard();assert(bot.casting&&reaction.wakes==before&&ai.resets==resets);
 }
 std::cout<<"PASS: Classic MC fire wakes preserve casts until escape admission; other maps/eras/lifecycle unchanged\n";
}
'''.replace('__METHOD__', method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-hazard-wake-') as directory:
  path=Path(directory);(path/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=path,check=True)
  subprocess.run([str(path/'test.exe')],cwd=path,check=True)
