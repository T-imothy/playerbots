"""Execute hazard admission after despawn, death, map and phase changes."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/triggers/DungeonTriggers.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('bool CloseToHazardTrigger::IsHazardValid(', 'bool CloseToCreatureHazardTrigger::IsHazardValid('))
code=r'''
#include <cassert>
#include <iostream>
struct ObjectGuid{unsigned id;bool IsGameObject()const{return id==1;}bool IsCreature()const{return id==2;}bool operator!=(ObjectGuid other)const{return id!=other.id;}};
struct WorldObject{bool world=true;unsigned map=1,phase=1;};
struct Unit:WorldObject{ObjectGuid guid{3};bool alive=true;Unit*victim=nullptr;bool IsAlive(){return alive;}Unit*GetVictim(){return victim;}ObjectGuid GetObjectGuid(){return guid;}};
struct Creature:Unit{};
struct GameObject:WorldObject{bool spawned=true;bool IsSpawned(){return spawned;}};
struct Player:Unit{bool IsInMap(WorldObject* object){return world&&object&&object->world&&map==object->map
#ifndef MANGOSBOT_ZERO
 && (phase&object->phase)!=0
#endif
 ;}};
struct PlayerbotAI{Creature*creature=nullptr;GameObject*gameobject=nullptr;
 Creature*GetCreature(ObjectGuid){return creature;}GameObject*GetGameObject(ObjectGuid){return gameobject;}};
struct CloseToHazardTrigger{PlayerbotAI*ai;Player*bot;bool IsHazardValid(const ObjectGuid&);};
struct CloseToCreatureHazardTrigger:CloseToHazardTrigger{bool IsHazardValid(const ObjectGuid&);};
__METHODS__
int main(){Player bot,other;other.guid.id=4;PlayerbotAI ai;CloseToHazardTrigger base{&ai,&bot};CloseToCreatureHazardTrigger creatureTrigger;creatureTrigger.ai=&ai;creatureTrigger.bot=&bot;
 ObjectGuid goGuid{1},creatureGuid{2};GameObject go;Creature creature;
 assert(!base.IsHazardValid(goGuid));assert(!base.IsHazardValid(creatureGuid));assert(!creatureTrigger.IsHazardValid(creatureGuid));
 ai.gameobject=&go;ai.creature=&creature;
 auto valid=[&]{assert(base.IsHazardValid(goGuid));assert(base.IsHazardValid(creatureGuid));assert(creatureTrigger.IsHazardValid(creatureGuid));};
 auto invalid=[&]{assert(!base.IsHazardValid(goGuid));assert(!base.IsHazardValid(creatureGuid));assert(!creatureTrigger.IsHazardValid(creatureGuid));};
 valid();go.world=creature.world=false;invalid();go.world=creature.world=true;
 go.map=creature.map=2;invalid();go.map=creature.map=1;
 bot.world=false;invalid();bot.world=true;valid();
#ifndef MANGOSBOT_ZERO
 go.phase=creature.phase=2;invalid();go.phase=creature.phase=3;valid();go.phase=creature.phase=1;
#endif
 go.spawned=false;creature.alive=false;invalid();go.spawned=true;creature.alive=true;valid();
 creature.victim=&bot;assert(base.IsHazardValid(creatureGuid));assert(!creatureTrigger.IsHazardValid(creatureGuid));
 creature.victim=&other;valid();creature.victim=nullptr;valid();assert(!base.IsHazardValid({99}));
 std::cout<<"PASS: native hazard trigger admission excludes missing/despawned/dead/wrong-map/phase sources and preserves victim exception\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='hazard-trigger-lifecycle-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
