"""Execute Hurtful Strike against disappearing/reordered targets and tank fallback."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
parts=[block((root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland/gruuls_lair/boss_gruul.cpp').read_text(),'struct HurtfulStrikePrimer') for era in ('tbc','wotlk')];assert parts[0]==parts[1]
code=r"""
#include <cassert>
#include <map>
#include <vector>
#include <iostream>
using SpellEffectIndex=unsigned;
enum{EFFECT_INDEX_0=0,TRIGGERED_IGNORE_GCD=1,TRIGGERED_IGNORE_CURRENT_CASTED_SPELL=2,TRIGGERED_NORMAL_COMBAT_CAST=4};
struct Unit;struct Player;struct Map{std::map<unsigned,Player*>players;Player*GetPlayer(unsigned id){auto it=players.find(id);return it==players.end()?nullptr:it->second;}};
struct Threat{std::map<Unit*,float>values;float getThreat(Unit*u){assert(u);return values[u];}};
struct Unit{bool alive=true,player=false,near=true;unsigned phase=1,calls=0;Unit*victim=nullptr,*chosen=nullptr;Map*map=nullptr;Threat threat;
 bool IsPlayer(){return player;}bool IsAlive(){return alive;}bool IsInMap(Unit*u){return u&&map==u->map&&phase==u->phase;}bool CanReachWithMeleeAttack(Unit*u){return u->near;}Unit*GetVictim(){return victim;}Map*GetMap(){return map;}Threat&getThreatManager(){return threat;}
 void CastSpell(Unit*u,unsigned id,unsigned flags){assert(id==33813&&flags==7);chosen=u;++calls;}
};struct Player:Unit{Player(){player=true;}};
struct TargetInfo{unsigned targetGUID;};struct Spell{Unit*caster;unsigned value=99;std::vector<TargetInfo>targets;Unit*GetCaster()const{return caster;}unsigned GetScriptValue(){return value;}void SetScriptValue(unsigned v){value=v;}auto&GetTargetList(){return targets;}};struct SpellScript{};
__HANDLER__;
int main(){
 Map map;Unit boss;Player tank,offtank,dps;boss.map=tank.map=offtank.map=dps.map=&map;boss.victim=&tank;map.players={{1,&tank},{2,&offtank},{3,&dps}};boss.threat.values={{&tank,1000},{&offtank,800},{&dps,300}};
 HurtfulStrikePrimer handler;Spell spell{&boss};spell.targets={{1},{2},{3},{99}};handler.OnInit(&spell);
 handler.OnEffectExecute(&spell,1);assert(boss.calls==0);handler.OnEffectExecute(&spell,0);assert(boss.calls==1&&boss.chosen==&offtank);
 for(unsigned i=0;i<5;++i)handler.OnEffectExecute(&spell,0);assert(boss.calls==1);
 // Deleted last target cannot cancel the whole strike; missing high-threat player is skipped.
 map.players.erase(2);handler.OnInit(&spell);handler.OnEffectExecute(&spell,0);assert(boss.chosen==&dps&&boss.calls==2);map.players[2]=&offtank;
 offtank.alive=false;handler.OnInit(&spell);handler.OnEffectExecute(&spell,0);assert(boss.chosen==&dps);offtank.alive=true;
 offtank.near=dps.near=false;handler.OnInit(&spell);handler.OnEffectExecute(&spell,0);assert(boss.chosen==&tank);
 tank.near=false;auto calls=boss.calls;handler.OnInit(&spell);handler.OnEffectExecute(&spell,0);assert(boss.calls==calls);tank.near=offtank.near=dps.near=true;
 offtank.phase=2;handler.OnInit(&spell);handler.OnEffectExecute(&spell,0);assert(boss.chosen==&dps);offtank.phase=1;
 spell.targets.clear();calls=boss.calls;handler.OnInit(&spell);handler.OnEffectExecute(&spell,0);assert(boss.calls==calls);
 assert(!handler.OnCheckTarget(&spell,nullptr,0));assert(!handler.OnCheckTarget(&spell,&boss,0));
 spell.caster=nullptr;assert(!handler.OnCheckTarget(&spell,&tank,0));handler.OnEffectExecute(&spell,0);assert(boss.calls==calls);
 std::cout<<"PASS: one native Hurtful Strike, highest-threat secondary player, tank fallback, missing/dead/out-of-range/out-of-phase targets and empty target list; TBC/Wrath match\n";
}
""".replace('__HANDLER__',parts[0].replace(' override',''))
with tempfile.TemporaryDirectory(prefix='gruul-hurtful-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
