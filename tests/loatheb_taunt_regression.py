"""Prevent observed healthy tank ping-pong without disabling emergency pickup."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
s=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
signature='    bool UnnecessaryLoathebTaunt('
method=block(s,signature) if signature in s else 'bool UnnecessaryLoathebTaunt(PlayerbotAI*,const SpellEntry*,Unit*){return false;}'
code=r'''
#include <cassert>
#include <iostream>
enum{MAX_EFFECT_INDEX=3,SPELL_EFFECT_ATTACK_ME=114,SPELL_AURA_MOD_TAUNT=11};
struct SpellEntry{unsigned Effect[3]={},EffectApplyAuraName[3]={};};
struct Unit{unsigned entry=16011;bool player=false;Unit*victim=nullptr;float hp=80;
 unsigned GetEntry(){return entry;}bool IsPlayer(){return player;}Unit*GetVictim(){return victim;}float GetHealthPercent(){return hp;}};
struct Player:Unit{unsigned map=533;bool tank=true,member=true;Player(){player=true;}unsigned GetMapId(){return map;}};
struct PlayerbotAI{Player bot;bool ready=true;Player*GetBot(){return &bot;}bool IsTank(Player*p){return p->tank;}};
struct Config{unsigned criticalHealth=20;}sPlayerbotAIConfig;
bool engaged=true;bool Ready(PlayerbotAI*ai){return ai->ready;}bool Engaged(Player*,Unit*u){return engaged&&u;}
bool Member(Player*,Player*p){return p&&p->member;}
__METHOD__
int main(){PlayerbotAI ai;Player holder;Unit boss;boss.victim=&holder;SpellEntry taunt,challenging,damage;
 taunt.Effect[0]=114;challenging.EffectApplyAuraName[0]=11;damage.Effect[0]=2;
#ifdef MANGOSBOT_ZERO
 assert(UnnecessaryLoathebTaunt(&ai,&taunt,&boss));assert(UnnecessaryLoathebTaunt(&ai,&challenging,&boss));
 holder.hp=20;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));holder.hp=80;
 holder.tank=false;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));holder.tank=true;
 holder.member=false;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));holder.member=true;
 boss.victim=nullptr;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));boss.victim=&holder;
 ai.bot.tank=false;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));ai.bot.tank=true;
 engaged=false;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));engaged=true;
 ai.ready=false;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));ai.ready=true;
#else
 assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));
#endif
 assert(!UnnecessaryLoathebTaunt(&ai,&damage,&boss));assert(!UnnecessaryLoathebTaunt(&ai,nullptr,&boss));
 for(unsigned entry:{16028u,15990u,16060u}){boss.entry=entry;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));}boss.entry=16011;
 for(unsigned map:{0u,409u,469u,489u}){ai.bot.map=map;assert(!UnnecessaryLoathebTaunt(&ai,&taunt,&boss));}
 std::cout<<"PASS Loatheb stable healthy tank, critical/non-tank pickup, native taunt effects and era/map scope\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='loatheb-taunt-') as directory:
  p=Path(directory);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
