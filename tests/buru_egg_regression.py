"""Actual Classic Buru egg selection, damage admission and native-route refusal."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
methods='\n'.join(block(source,name) for name in ('bool BuruEggPhase(', 'bool BuruEgg(', 'Unit* BuruNextEgg(', 'bool BuruEggInBlast(', 'bool BuruKitePosition(', 'bool BuruOffenseAllowed('))
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <vector>
using ObjectGuid=unsigned;
namespace encounter{struct Point{float x=0,y=0,z=0;};struct Circle{Point center;float radius;};}
struct Spline{bool done=false;encounter::Point end;bool Finalized(){return done;}auto FinalDestination(){return end;}};
struct Unit{unsigned entry=0,guid=0,map=509,instance=1;float x=0,y=0,z=0,hp=100;bool alive=true,world=true,charm=false,combat=true,thorns=true,cc=false,hardCC=false,friendly=false,attackable=true;Unit*victim=nullptr;Spline*movespline=nullptr;
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}float GetHealthPercent(){return hp;}
 bool HasAura(unsigned id){assert(id==25640);return thorns;}Unit*GetVictim(){return victim;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}
 float GetDistance(Unit*u){return std::hypot(std::hypot(x-u->x,y-u->y),z-u->z);}
};using Player=Unit;
struct Values{std::list<ObjectGuid> list;auto Get(){return list;}};
struct Context{Values values;template<class T>Values*GetValue(const char*,const char*){return &values;}};
struct PlayerbotAI{Player bot;Context ctx;std::map<unsigned,Unit*> units;bool move=true;Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &ctx;}Unit*GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}bool CanMove(){return move;}};
bool Live(Player*p,Unit*u){return u&&u->alive&&u->world&&!u->charm&&p->map==u->map&&p->instance==u->instance;}
bool Engaged(Player*p,Unit*u){return Live(p,u)&&u->combat&&!u->friendly;}
struct Facade{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*p,float distance,bool){return u->attackable&&p->GetDistance(u)<=distance;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0,boss=0,source=0;encounter::Point destination;};
float nativeRadius=25;float NativeEncounterSpellRadius(unsigned id){assert(id==19593);return nativeRadius;}
bool nativePath=true;unsigned pathCalls=0;
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&p){++pathCalls;return nativePath&&std::hypot(p.destination.x-a->bot.x,p.destination.y-a->bot.y)<=60&&std::isfinite(p.destination.z);}
bool circleSafe=true;bool LocalCircleRoute(PlayerbotAI*,const EncounterPosition&,const std::vector<encounter::Circle>&c){assert(c.size()==1&&c[0].radius==8);return circleSafe;}
constexpr unsigned MAX_EFFECT_INDEX=3,SPELL_AURA_PERIODIC_DAMAGE=3,SPELL_AURA_PERIODIC_LEECH=53;
struct SpellEntry{unsigned Id=1,MaxAffectedTargets=1,EffectApplyAuraName[3]={};bool damage=true,area=false;};
bool RaidDamageSpell(const SpellEntry*s){return s->damage;}bool IsAreaOfEffectSpell(const SpellEntry*s){return s->area;}
Unit* FindBoss(PlayerbotAI*a,unsigned entry){for(auto pair:a->units)if(pair.second->entry==entry&&Engaged(&a->bot,pair.second))return pair.second;return nullptr;}
__METHODS__
int main(){
 PlayerbotAI ai;Unit boss,egg,other,add;boss.entry=15370;boss.guid=1;egg.entry=other.entry=15514;egg.guid=2;other.guid=3;egg.x=20;other.x=40;add.entry=15521;add.guid=4;
 ai.units={{1,&boss},{2,&egg},{3,&other},{4,&add}};ai.ctx.values.list={1,3,2,4};
 assert(BuruNextEgg(&ai,&boss)==&egg);other.hp=90;assert(BuruNextEgg(&ai,&boss)==&other);other.hp=100;
 other.x=20;assert(BuruNextEgg(&ai,&boss)==&egg);other.x=40;
 assert(BuruEggInBlast(&boss,&egg));egg.x=23;assert(!BuruEggInBlast(&boss,&egg));egg.x=20;egg.z=20;assert(!BuruEggInBlast(&boss,&egg));egg.z=0;
 for(float bad:{0.f,3.f,41.f,NAN}){nativeRadius=bad;assert(!BuruEggInBlast(&boss,&egg));}nativeRadius=25;
 SpellEntry spell;assert(!BuruOffenseAllowed(&ai,&spell,&boss));assert(BuruOffenseAllowed(&ai,&spell,&egg));assert(BuruOffenseAllowed(&ai,nullptr,&egg));
 assert(!BuruOffenseAllowed(&ai,&spell,&other));egg.x=23;assert(!BuruOffenseAllowed(&ai,&spell,&egg));egg.x=20;
 spell.area=true;assert(!BuruOffenseAllowed(&ai,&spell,&add));spell.area=false;
 spell.EffectApplyAuraName[0]=SPELL_AURA_PERIODIC_DAMAGE;assert(!BuruOffenseAllowed(&ai,&spell,&egg));assert(BuruOffenseAllowed(&ai,&spell,&add));spell.EffectApplyAuraName[0]=0;
 spell.damage=false;assert(BuruOffenseAllowed(&ai,&spell,&boss));spell.Id=13877;assert(!BuruOffenseAllowed(&ai,&spell,&boss));spell.Id=1;spell.damage=true;
 boss.hp=19;assert(!BuruNextEgg(&ai,&boss)&&BuruOffenseAllowed(&ai,&spell,&boss));boss.hp=100;
 boss.thorns=false;assert(!BuruNextEgg(&ai,&boss));boss.thorns=true;boss.combat=false;assert(!BuruNextEgg(&ai,&boss));boss.combat=true;
 egg.alive=false;assert(!BuruEgg(&ai,&egg));egg.alive=true;egg.cc=true;assert(!BuruEgg(&ai,&egg));egg.cc=false;egg.instance=2;assert(!BuruEgg(&ai,&egg));egg.instance=1;
 ai.bot.map=409;assert(!BuruEggPhase(&ai,&boss)&&!BuruEgg(&ai,&egg));ai.bot.map=509;
 EncounterPosition p;assert(!BuruKitePosition(&ai,&boss,&egg,p));boss.victim=&ai.bot;
 assert(BuruKitePosition(&ai,&boss,&egg,p)&&p.active&&p.spell==19593&&p.source==2);assert(p.destination.x==35&&p.destination.y==0);
 Spline travel;travel.end={34,2,0};ai.bot.movespline=&travel;pathCalls=0;assert(BuruKitePosition(&ai,&boss,&egg,p)&&p.destination.x==34&&p.destination.y==2&&pathCalls==1);
 travel.end={5,0,0};assert(BuruKitePosition(&ai,&boss,&egg,p)&&p.destination.x==35);
 ai.bot.movespline=nullptr;nativePath=false;pathCalls=0;assert(!BuruKitePosition(&ai,&boss,&egg,p)&&!p.active&&pathCalls==9);nativePath=true;
 circleSafe=false;assert(!BuruKitePosition(&ai,&boss,&egg,p));circleSafe=true;
 ai.move=false;assert(!BuruKitePosition(&ai,&boss,&egg,p));ai.move=true;boss.hp=19;assert(!BuruKitePosition(&ai,&boss,&egg,p));
 std::cout<<"PASS native Buru phase/egg guards, stable selection, blast admission, damage/DoT/splash holds, healing, kite retention and path refusal\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='buru-eggs-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(p/'test.exe')],cwd=p,check=True)
