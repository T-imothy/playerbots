"""Actual Tears action timing, inventory/lifecycle gates and native delegation."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ArchimondeTearsAction.cpp').read_text()
methods='\n'.join(block(source,'bool ArchimondeTearsAction::'+s+'(') for s in ('isUseful','Execute'))
code=r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <list>
using uint32=uint32_t;using int32=int32_t;using ObjectGuid=unsigned;
enum{SPELL_AURA_FEATHER_FALL=1,MOVEFLAG_FALLING=2};
struct World{uint32 now=10000;uint32 GetCurrentMSTime(){return now;}}sWorld;
struct Unit{unsigned entry=17968,map=534,phase=1;bool world=true,alive=true,combat=true,charmed=false;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}unsigned GetEntry(){return entry;}};
struct Player:Unit{bool teleport=false,group=true,item=true,slow=false,fall=true;
 bool IsBeingTeleported(){return teleport;}bool GetGroup(){return group;}unsigned GetMapId(){return map;}
 bool HasItemCount(unsigned id,unsigned count){assert(id==24494&&count==1);return item;}
 bool HasAuraType(unsigned){return slow;}bool HasMovementFlag(unsigned){return fall;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}float GetDistance(Unit*){return 30;}};
template<class T>struct Value{T data;T Get(){return data;}};
struct Context{Value<std::list<ObjectGuid>>attackers;template<class T>Value<T>*GetValue(const char*){return &attackers;}};
struct PlayerbotAI{Player*bot;Unit*boss;Context context;bool real=false;uint32 jump=11200;unsigned uses=0;bool cooldown=false;
 bool IsRealPlayer(){return real;}bool IsJumping(){return jump;}uint32 GetJumpTime(){return jump;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned){return boss;}};
struct Event{};struct UseItemIdAction{PlayerbotAI*ai;Player*bot;bool isUseful(){return true;}bool Execute(Event&){if(ai->cooldown)return false;++ai->uses;return true;}};
struct ArchimondeTearsAction:UseItemIdAction{bool isUseful();bool Execute(Event&);};
__METHODS__
int main(){Player bot;Unit boss;PlayerbotAI ai{&bot,&boss};ai.context.attackers.data={1};ArchimondeTearsAction action;action.ai=&ai;action.bot=&bot;Event event;
#ifndef MANGOSBOT_ZERO
 assert(action.isUseful()&&action.Execute(event)&&ai.uses==1);
 ai.jump=13000;assert(!action.isUseful());ai.jump=10000;assert(!action.isUseful());ai.jump=9999;assert(!action.isUseful());
 sWorld.now=0xffffff00;ai.jump=0x100;assert(action.isUseful());sWorld.now=10000;ai.jump=11200;
 bot.item=false;assert(!action.Execute(event));bot.item=true;
 bot.slow=true;assert(!action.Execute(event));bot.slow=false;
 bot.fall=false;assert(!action.isUseful());bot.fall=true;
 ai.jump=0;assert(!action.isUseful());ai.jump=11200;
 ai.cooldown=true;assert(!action.Execute(event)&&ai.uses==1);ai.cooldown=false;
 boss.combat=false;assert(!action.isUseful());boss.combat=true;
 boss.phase=2;assert(!action.isUseful());boss.phase=1;
 bot.teleport=true;assert(!action.isUseful());bot.teleport=false;
 bot.charmed=true;assert(!action.isUseful());bot.charmed=false;
 ai.real=true;assert(!action.isUseful());ai.real=false;
 bot.map=1;assert(!action.isUseful());
#else
 assert(!action.isUseful()&&!action.Execute(event));
#endif
 std::cout<<"PASS: landing window/wraparound, actual inventory, native item cooldown and encounter lifecycle\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-tears-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
native=(root/'playerbot/PlayerbotAI.cpp').read_text()
assert 'bot->Relocate(highestPoint.getX(), highestPoint.getY(), highestPoint.getZ())' in native
assert 'jumpTime = curTime + sWorld.GetAverageDiff()' in native
assert 'WorldPacket land(MSG_MOVE_FALL_LAND)' in native
