"""Actual Bronze-affliction item action retains native inventory and use admission."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
methods=block(source,'bool HourglassSandAction::isUseful(')+'\n'+block(source,'bool HourglassSandAction::Execute(')
code=r'''
#include <cassert>
#include <iostream>
struct Player{bool world=true,alive=true,charmed=false,teleport=false,bronze=true;unsigned map=469,items=1;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}unsigned GetMapId(){return map;}
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}
 bool HasAura(unsigned id){assert(id==23170);return bronze;}bool HasItemCount(unsigned id,unsigned count){assert(id==19183&&count==1);return items>=count;}
};
struct PlayerbotAI{bool real=false;bool IsRealPlayer(){return real;}};struct Event{};
struct UseItemIdAction{Player*bot;PlayerbotAI*ai;bool nativeUseful=true,nativeSuccess=true;unsigned uses=0;
 bool isUseful(){return nativeUseful;}bool Execute(Event&){++uses;return nativeSuccess;}
};
struct HourglassSandAction:UseItemIdAction{bool isUseful();bool Execute(Event&);};
__METHODS__
int main(){Player bot;PlayerbotAI ai;HourglassSandAction action;action.bot=&bot;action.ai=&ai;Event event;
 assert(action.isUseful()&&action.Execute(event)&&action.uses==1);
 bot.bronze=false;assert(!action.Execute(event)&&action.uses==1);bot.bronze=true;
 bot.items=0;assert(!action.Execute(event)&&action.uses==1);bot.items=1;
 bot.map=0;assert(!action.isUseful());bot.map=469;
 bot.teleport=true;assert(!action.isUseful());bot.teleport=false;
 bot.charmed=true;assert(!action.isUseful());bot.charmed=false;
 bot.alive=false;assert(!action.isUseful());bot.alive=true;
 bot.world=false;assert(!action.isUseful());bot.world=true;
 ai.real=true;assert(!action.isUseful());ai.real=false;
 action.nativeUseful=false;assert(!action.Execute(event));action.nativeUseful=true;
 action.nativeSuccess=false;assert(!action.Execute(event)); // core cooldown/cast failures are not reported as success
 std::cout<<"PASS: actual Bronze item guard, inventory requirement, stale-aura and native failure handling\n";
}
'''.replace('__METHODS__',methods)
for era in ('classic','tbc','wotlk'):
 native=(root.parent/f'mangos-{era}-behavior/src/game/Spells/SpellEffects.cpp').read_text()
 sand=block(native,'case 23645:');assert 'RemoveAurasDueToSpell(23170)' in sand
 with tempfile.TemporaryDirectory(prefix='mantech-hourglass-') as directory:
  tmp=Path(directory);(tmp/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
