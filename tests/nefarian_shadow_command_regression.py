"""Execute native-identity and in-flight CC admission for Shadow Command."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
s=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <iostream>
using SpellEffectIndex=unsigned;
constexpr unsigned CURRENT_GENERIC_SPELL=0,SPELL_STATE_CASTING=1,MAX_EFFECT_INDEX=3,SPELL_AURA_MOD_CONFUSE=5,SPELL_AURA_MOD_STUN=12;
struct Unit;struct Player;struct Group;
struct SpellAuraHolder{Unit*caster=nullptr;Unit*GetCaster()const{return caster;}};
struct SpellEntry{unsigned EffectApplyAuraName[3]={};bool aura=true;};
bool IsAuraApplyEffect(const SpellEntry*s,unsigned){return s->aura;}
struct Targets{Unit*target=nullptr;Unit*getUnitTarget(){return target;}};
struct Spell{SpellEntry*m_spellInfo=nullptr;Targets m_targets;unsigned state=1;unsigned getState(){return state;}};
struct Unit{bool world=true,alive=true,combat=true,player=false,poly=false;unsigned map=469,instance=1,entry=0,cc=0;
 Unit*charmer=nullptr;SpellAuraHolder*command=nullptr;
 bool IsPlayer(){return player;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 unsigned GetMapId(){return map;}unsigned GetEntry(){return entry;}bool IsInMap(Unit*u){return u&&map==u->map&&instance==u->instance;}
 const SpellAuraHolder*GetSpellAuraHolder(unsigned id){assert(id==22667);return command;}Unit*GetCharmer(){return charmer;}
 bool IsPolymorphed(){return poly;}bool HasAuraType(unsigned type){return cc==type;}};
struct Player:Unit{Group*group=nullptr;Spell*cast=nullptr;Player(){player=true;}
 Group*GetGroup(){return group;}Spell*GetCurrentSpell(unsigned type){assert(type==0);return cast;}};
struct Ref{Player*p;Ref*n=nullptr;Player*getSource(){return p;}Ref*next(){return n;}};
struct Group{Ref*head=nullptr;Ref*GetFirstMember(){return head;}};
struct PlayerbotAI{Player*bot;Player*GetBot(){return bot;}};
bool Member(Player*b,Player*p){return p&&p->world&&p->alive&&!p->charmer&&b->IsInMap(p)&&b->group==p->group;}
__METHODS__
int main(){
 Player bot,victim,mage;Group group;Ref a{&victim},b{&mage};a.n=&b;group.head=&a;bot.group=victim.group=mage.group=&group;
 Unit boss;boss.entry=10162;SpellAuraHolder command{&boss};victim.command=&command;victim.charmer=&boss;PlayerbotAI ai{&bot};
 assert(NefariusControlledMember(&bot,&victim));assert(NefariusCrowdControlTarget(&ai)==&victim);
 victim.command=nullptr;assert(!NefariusControlledMember(&bot,&victim));victim.command=&command;
 victim.charmer=nullptr;assert(!NefariusControlledMember(&bot,&victim));victim.charmer=&boss;
 boss.entry=11583;assert(!NefariusControlledMember(&bot,&victim));boss.entry=10162;
 boss.instance=2;assert(!NefariusControlledMember(&bot,&victim));boss.instance=1;
 boss.alive=false;assert(!NefariusControlledMember(&bot,&victim));boss.alive=true;
 boss.combat=false;assert(!NefariusControlledMember(&bot,&victim));boss.combat=true;
 victim.group=nullptr;assert(!NefariusControlledMember(&bot,&victim));victim.group=&group;
 victim.alive=false;assert(!NefariusControlledMember(&bot,&victim));victim.alive=true;
 victim.world=false;assert(!NefariusControlledMember(&bot,&victim));victim.world=true;
 victim.instance=2;assert(!NefariusControlledMember(&bot,&victim));victim.instance=1;
 for(unsigned map:{0u,409u,489u,533u}){bot.map=map;assert(!NefariusCrowdControlTarget(&ai));}bot.map=469;
 for(unsigned cc:{5u,12u}){victim.cc=cc;assert(!NefariusCrowdControlTarget(&ai));}victim.cc=0;
 victim.poly=true;assert(!NefariusCrowdControlTarget(&ai));victim.poly=false;
 SpellEntry sheep;sheep.EffectApplyAuraName[0]=5;Spell cast{&sheep,{&victim}};mage.cast=&cast;
 assert(!NefariusCrowdControlTarget(&ai));
 cast.state=2;assert(NefariusCrowdControlTarget(&ai)==&victim);cast.state=1;
 cast.m_targets.target=&boss;assert(NefariusCrowdControlTarget(&ai)==&victim);cast.m_targets.target=&victim;
 sheep.EffectApplyAuraName[0]=0;assert(NefariusCrowdControlTarget(&ai)==&victim);
 std::cout<<"PASS Shadow Command identity, group/map/lifecycle guards, existing and in-flight native CC, release recovery\n";
}
'''.replace('__METHODS__',block(s,'    bool NefariusControlledMember(')+'\n'+block(s,'    Unit* NefariusCrowdControlTarget('))
with tempfile.TemporaryDirectory(prefix='nef-shadow-command-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
