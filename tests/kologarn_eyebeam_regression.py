"""Execute player-owned marker handoff and native marker lifetime gates."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]/'mangos-wotlk-behavior'
s=(root/'src/game/AI/ScriptDevAI/scripts/northrend/ulduar/ulduar/boss_kologarn.cpp').read_text()
handler=block(s,'struct KologarnEyebeamSummon').replace(' override','')
update=block(s[s.index('struct npc_focused_eyebeamAI'):],'void UpdateAI(').replace(' override','')
code=r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;enum{TYPEID_PLAYER=1,NPC_FOCUSED_EYEBEAM_LEFT=33632,NPC_FOCUSED_EYEBEAM_RIGHT=33802,NPC_KOLOGARN=32930,TYPE_KOLOGARN=1,IN_PROGRESS=1};
struct Creature;struct Instance{virtual ~Instance()=default;};
struct Unit{unsigned type=1,guid=11;bool alive=true,same=true;virtual ~Unit()=default;unsigned GetTypeId(){return type;}unsigned GetObjectGuid(){return guid;}bool IsAlive(){return alive;}bool IsInMap(Unit*u){return u&&u->same;}};
struct AI{unsigned calls=0;Creature*last=nullptr;void JustSummoned(Creature*c){++calls;last=c;}};
struct Creature:Unit{unsigned entry=33632,owner=11,despawns=0;::AI*ai=nullptr;Instance*instance;unsigned GetEntry(){return entry;}unsigned GetSpawnerGuid(){return owner;}Instance*GetInstanceData(){return instance;}::AI*AI(){return ai;}void ForcedDespawn(){++despawns;}};
struct instance_ulduar:Instance{Creature*boss=nullptr;unsigned state=IN_PROGRESS;Creature*GetSingleCreatureFromStorage(unsigned){return boss;}unsigned GetData(unsigned){return state;}};
struct Spell{Unit*caster,*original;Unit*GetCaster(){return caster;}Unit*GetAffectiveCaster(){return original?original:caster;}};
struct SpellScript{};
__HANDLER__;
struct MarkerAI{instance_ulduar*m_pInstance;Creature*m_creature;__UPDATE__};
int main(){
 Unit player;AI ai;Creature boss,marker;boss.type=2;boss.entry=NPC_KOLOGARN;boss.ai=&ai;instance_ulduar instance;instance.boss=&boss;marker.instance=&instance;Spell spell{&player,nullptr};KologarnEyebeamSummon handler;
 for(unsigned entry:{33632u,33802u}){marker.entry=entry;handler.OnSummon(&spell,&marker);assert(ai.last==&marker);}assert(ai.calls==2);
 spell.original=&boss;handler.OnSummon(&spell,&marker);assert(ai.calls==2);spell.original=nullptr; // native original-caster callback already handled it
 marker.owner=99;handler.OnSummon(&spell,&marker);assert(ai.calls==2);marker.owner=11;marker.entry=123;handler.OnSummon(&spell,&marker);assert(ai.calls==2);marker.entry=33632;
 player.alive=false;handler.OnSummon(&spell,&marker);assert(ai.calls==2);player.alive=true;
 instance.state=0;handler.OnSummon(&spell,&marker);assert(marker.despawns==1);instance.state=IN_PROGRESS;boss.ai=nullptr;handler.OnSummon(&spell,&marker);assert(marker.despawns==2);boss.ai=&ai;
 MarkerAI markerAI{&instance,&marker};markerAI.UpdateAI(1);assert(marker.despawns==2);boss.alive=false;markerAI.UpdateAI(1);assert(marker.despawns==3);boss.alive=true;instance.state=0;markerAI.UpdateAI(1);assert(marker.despawns==4);markerAI.m_pInstance=nullptr;markerAI.UpdateAI(1);assert(marker.despawns==5);
 handler.OnSummon(&spell,nullptr);spell.caster=nullptr;handler.OnSummon(&spell,&marker);
 std::cout<<"PASS: both player-owned marker entries, exactly one boss initialization path, source validation and reset/death/missing-instance cleanup\n";
}
'''.replace('__HANDLER__',handler).replace('__UPDATE__',update)
with tempfile.TemporaryDirectory(prefix='kologarn-eyebeam-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
