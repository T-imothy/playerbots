"""Execute native raid-control selection/admission in all three era builds.

Native contract: Wrath boss_razuvious.cpp and npc_spellclick_spells 29912/55479;
spell_template 605,28732,54097 and Faerlina difficulty script. Classic/TBC retain
Mind Control rank 10912 and controlled Worshipper Embrace. This fixture mocks
world/session admission, not native spell outcomes or a successful live raid.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
src = (root / 'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
parts = '\n'.join(block(src, marker) for marker in (
    '    bool Ready(', '    bool NaxxRegular(', '    Unit* FaerlinaSacrifice(',
    'Unit* ClassicRaidControlAction::SelectUnderstudy(',
    'bool ClassicRaidControlAction::Execute('))
code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <vector>
#include "__POLICY__"
#include "__NATIVE__"
using namespace ai;
using uint32=unsigned;using int32=int;
constexpr unsigned CLASS_PRIEST=5,CLASS_WARRIOR=1,POWER_MANA=0;
constexpr unsigned CURRENT_GENERIC_SPELL=0,CURRENT_CHANNELED_SPELL=1;
constexpr unsigned SPELL_STATE_FINISHED=2,UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=1;
constexpr unsigned CMSG_SPELLCLICK=1;constexpr float INTERACTION_DISTANCE=5;
struct ObjectGuid{unsigned id=0;bool operator==(ObjectGuid b)const{return id==b.id;}
 bool operator!=(ObjectGuid b)const{return id!=b.id;}bool operator<(ObjectGuid b)const{return id<b.id;}};
struct Unit;struct Player;struct PlayerbotAI;
struct SpellEntry{unsigned Id;};
struct SpellTargets{Unit*target=nullptr;Unit*getUnitTarget()const{return target;}};
struct Spell{const SpellEntry*m_spellInfo=nullptr;SpellTargets m_targets;unsigned state=0;
 unsigned getState()const{return state;}static unsigned CalculatePowerCost(const SpellEntry*,Player*){return 100;}};
struct Unit{ObjectGuid guid{},owner{};unsigned entry=0;bool world=true,alive=true,sameMap=true,combat=true;
 bool casting=false,los=true,cc=false;float distance=10;Unit*victim=nullptr;std::set<unsigned>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return owner.id!=0;}
 bool HasCharmer(ObjectGuid g){return owner==g;}bool IsInCombat(){return combat;}
 bool IsNonMeleeSpellCasted(bool){return casting;}bool HasAura(unsigned id){return auras.count(id);}
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}float GetDistance(Unit*){return distance;}
 bool IsWithinLOSInMap(Unit*u){return u->los;}bool IsWithinDistInMap(Unit*u,float limit){return u->distance<=limit;}};
struct WorldPacket{unsigned kind;ObjectGuid guid;WorldPacket(unsigned k):kind(k){}
 WorldPacket&operator<<(ObjectGuid g){guid=g;return *this;}};
struct Session{Player*owner=nullptr;Unit*granted=nullptr;unsigned clicks=0;bool accepted=false;ObjectGuid last{};
 void HandleSpellClick(WorldPacket&);};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Player:Unit{PlayerbotAI*brain=nullptr;unsigned map=533,cls=CLASS_PRIEST,mana=500;
 bool transfer=false,ready=true,tank=false,locked=false;Unit*charm=nullptr;Map native;Session session;
 std::set<unsigned>spells{605,10912};Spell*casts[2]={nullptr,nullptr};
 Player(){session.owner=this;}Map*GetMap(){return &native;}unsigned GetMapId(){return map;}
 bool IsBeingTeleported(){return transfer;}bool IsInMap(Unit*u){return u&&u->sameMap;}
 void*GetGroup(){return this;}unsigned getClass(){return cls;}Unit*GetCharm(){return charm;}
 bool HasSpell(unsigned id){return spells.count(id);}bool IsSpellReady(const SpellEntry&){return ready;}
 unsigned GetPower(unsigned){return mana;}bool hasUnitState(unsigned){return locked;}
 Spell*GetCurrentSpell(unsigned slot){return casts[slot];}PlayerbotAI*GetPlayerbotAI(){return brain;}
 Session*GetSession(){return &session;}};
void Session::HandleSpellClick(WorldPacket&p){++clicks;last=p.guid;
 if(accepted&&granted&&!granted->HasCharmer()){owner->charm=granted;granted->owner=owner->guid;}}
struct Context{std::list<ObjectGuid>nearby;
 template<class T>struct Value{T v;T Get(){return v;}};
 template<class T>Value<T>*GetValue(const char*,const char*){static Value<T>v;v.v=nearby;return &v;}};
struct PlayerbotAI{Player bot;Unit boss;Context context;std::map<unsigned,Unit*>units;std::vector<Player*>roster;
 bool real=false,engaged=true,castAllowed=true,castAccepted=true;unsigned casts=0;Unit*castTarget=nullptr;
 PlayerbotAI(){bot.guid={1};bot.brain=this;boss.entry=16061;boss.guid={100};roster={&bot};}
 Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &context;}
 bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}
 Unit*GetUnit(ObjectGuid g){auto i=units.find(g.id);return i==units.end()?nullptr:i->second;}
 bool CanCastSpell(const char*,Unit*,unsigned){return castAllowed;}
 bool CastSpell(const char*,Unit*u,void*,bool,unsigned*){++casts;castTarget=u;return castAccepted;}
 void add(Unit&u,unsigned id,unsigned entry){u.guid={id};u.entry=entry;units[id]=&u;context.nearby.push_back(u.guid);}};
struct Facade{SpellEntry classic{10912},wrath{605};bool present=true;
 const SpellEntry*LookupSpellInfo(unsigned id){return !present?nullptr:id==10912?&classic:id==605?&wrath:nullptr;}}sServerFacade;
struct Config{unsigned globalCoolDown=1500;}sPlayerbotAIConfig;
struct WorldTimer{static unsigned now;static unsigned getMSTime(){return now;}};unsigned WorldTimer::now=1000;
namespace PossibleAttackTargetsValue{bool HasBreakableCC(Unit*u,Player*){return u->cc;}}
float nativeRadius=15;float NativeEncounterSpellRadius(unsigned){return nativeRadius;}
bool Live(Player*b,Unit*u){return u&&u->IsInWorld()&&u->IsAlive()&&b->IsInMap(u)&&!u->HasCharmer();}
bool Engaged(Player*b,Unit*u){return Live(b,u)&&u->combat;}
Unit*FindBoss(PlayerbotAI*a,unsigned entry){return a->engaged&&a->boss.entry==entry?&a->boss:nullptr;}
std::vector<Player*>Members(PlayerbotAI*a){std::vector<Player*>r;
 for(auto*p:a->roster)if(Live(&a->bot,p)&&!p->transfer)r.push_back(p);
 std::sort(r.begin(),r.end(),[](Player*a,Player*b){return a->guid<b->guid;});return r;}
struct Event{};
bool controlAllowed=true;
bool NaxxramasControlAllowed(PlayerbotAI*){return controlAllowed;}
struct ClassicRaidControlAction{PlayerbotAI*ai;Player*bot;unsigned nextControl=0,moves=0,duration=0;
 Unit*moveTarget=nullptr;Unit*SelectUnderstudy();bool Execute(Event&);
 bool MoveNear(Unit*u,float){++moves;moveTarget=u;return true;}void SetDuration(unsigned d){duration=d;}};
#define AI_VALUE2(T,N,Q) (ai->GetAiObjectContext()->GetValue<T>(N,Q)->Get())
__PARTS__
int main(){
 PlayerbotAI a;Unit s1,s2,c1,c2;a.add(s1,10,16803);a.add(s2,11,16803);
 a.add(c1,20,29912);a.add(c2,21,29912);c1.combat=c2.combat=false;
 ClassicRaidControlAction action{&a,&a.bot};Event event;
 controlAllowed=false;assert(!action.SelectUnderstudy());controlAllowed=true;
#ifdef MANGOSBOT_TWO
 assert(naxxnative::MindControl()==605&&naxxnative::ObedienceCrystal(true));
 assert(naxxnative::FaerlinaEmbrace(false)==54097);
 assert(!action.SelectUnderstudy()); // Wrath10 elects tanks, never arbitrary priests.
 a.bot.cls=CLASS_WARRIOR;a.bot.tank=true;a.bot.spells.clear();assert(action.SelectUnderstudy()==&c1);
 c1.distance=10;assert(action.Execute(event)&&action.moves==1&&a.bot.session.clicks==0);
 c1.distance=2;c1.los=false;assert(action.Execute(event)&&action.moves==2&&a.bot.session.clicks==0);
 c1.los=true;assert(!action.Execute(event)&&a.bot.session.clicks==1&&!a.bot.charm);
 assert(!action.Execute(event)&&a.bot.session.clicks==1); // Native refusal is bounded, not fabricated ownership.
 WorldTimer::now+=1000;a.bot.session.accepted=true;a.bot.session.granted=&s1;
 assert(action.Execute(event)&&a.bot.charm==&s1&&s1.owner==a.bot.guid);
 assert(!action.SelectUnderstudy());a.bot.charm=nullptr;s1.owner={};
 c1.casting=true;assert(action.SelectUnderstudy()==&c2);c1.casting=false;
 c1.owner={999};assert(action.SelectUnderstudy()==&c2);c1.owner={};
 a.bot.native.regular=false;assert(!action.SelectUnderstudy()); // 25-player never admits warrior crystal control.
 a.bot.cls=CLASS_PRIEST;a.bot.tank=false;a.bot.spells={605};
#else
 assert(naxxnative::MindControl()==10912&&!naxxnative::ObedienceCrystal(true));
 assert(naxxnative::FaerlinaEmbrace(false)==28732);
 a.bot.spells={10912};
#endif
 assert(action.SelectUnderstudy()==&s1);
 a.bot.spells.clear();assert(!action.SelectUnderstudy());a.bot.spells={naxxnative::MindControl()};
 a.bot.ready=false;assert(!action.SelectUnderstudy());a.bot.ready=true;
 a.bot.mana=99;assert(!action.SelectUnderstudy());a.bot.mana=100;
 a.bot.transfer=true;assert(!action.SelectUnderstudy());a.bot.transfer=false;
 a.bot.alive=false;assert(!action.SelectUnderstudy());a.bot.alive=true;
 a.bot.locked=true;assert(!action.SelectUnderstudy());a.bot.locked=false;
 a.real=true;assert(!action.SelectUnderstudy());a.real=false;
 a.bot.map=409;assert(!action.SelectUnderstudy());a.bot.map=533;
 s1.owner={99};assert(action.SelectUnderstudy()==&s2);s1.owner={};
 s1.cc=true;assert(action.SelectUnderstudy()==&s2);s1.cc=false;
 s1.alive=false;assert(action.SelectUnderstudy()==&s2);s1.alive=true;
 s1.sameMap=false;assert(action.SelectUnderstudy()==&s2);s1.sameMap=true;
 a.castAllowed=false;const auto n=a.casts;assert(action.Execute(event)&&a.casts==n&&action.moveTarget==&s1);
 a.castAllowed=true;a.castAccepted=false;assert(!action.Execute(event)&&a.casts==n+1&&!a.bot.charm);
 a.castAccepted=true;assert(action.Execute(event)&&a.castTarget==&s1&&action.duration==1500);
 // An actual in-flight native MC cast reserves exactly one actor/controller slot.
 PlayerbotAI p2,p3;p2.bot.guid={2};p3.bot.guid={3};a.roster={&a.bot,&p2.bot,&p3.bot};
 SpellEntry native{naxxnative::MindControl()};Spell claiming{&native,{&s1},0};
 p2.bot.casts[CURRENT_GENERIC_SPELL]=&claiming;p2.bot.casting=true;
 assert(action.SelectUnderstudy()==&s2);
 p2.real=true;assert(action.SelectUnderstudy()==&s2); // Human MC in flight still reserves its exact actor.
 p2.bot.brain=nullptr;assert(action.SelectUnderstudy()==&s2); // Ordinary human session has no bot AI.
 Spell humanSecond{&native,{&s2},0};p3.bot.casts[CURRENT_CHANNELED_SPELL]=&humanSecond;p3.real=true;
 assert(!action.SelectUnderstudy()); // Both human claims are preserved; do not nominate another controller.
 p3.bot.casts[CURRENT_CHANNELED_SPELL]=nullptr;p3.real=false;p2.bot.brain=&p2;p2.real=false;
 p3.bot.charm=&s2;s2.owner=p3.bot.guid;assert(!action.SelectUnderstudy());
 p3.bot.charm=nullptr;s2.owner={};p2.bot.casts[0]=nullptr;p2.bot.casting=false;
 // Dead, transferring, channeling, foreign-controlled and non-bot peers cannot steal selection slots.
 a.bot.guid={4};p2.bot.alive=false;p3.bot.transfer=true;assert(action.SelectUnderstudy()==&s1);
 p2.bot.alive=true;p2.bot.owner={99};p3.bot.transfer=false;p3.real=true;assert(action.SelectUnderstudy()==&s1);
 p2.bot.owner={};p2.bot.casting=true;assert(action.SelectUnderstudy()==&s1);
 a.roster={&a.bot};a.bot.guid={1};
 // Sacrifice uses actual native frenzy and radius, and is Wrath10 only.
 Unit w1,w2;a.add(w1,30,16506);a.add(w2,31,16506);a.boss.entry=15953;
 a.bot.native.regular=true;a.boss.auras.clear();assert(!FaerlinaSacrifice(&a,&a.boss));
 a.boss.auras.insert(naxxnative::FaerlinaFrenzy(true));
#ifdef MANGOSBOT_TWO
 assert(FaerlinaSacrifice(&a,&a.boss)==&w1);assert(!action.SelectUnderstudy());
 w1.distance=14;assert(FaerlinaSacrifice(&a,&a.boss)==&w2);w1.distance=10;
 w1.cc=true;assert(FaerlinaSacrifice(&a,&a.boss)==&w2);w1.cc=false;
 w1.owner={99};assert(FaerlinaSacrifice(&a,&a.boss)==&w2);w1.owner={};
 w1.combat=false;assert(FaerlinaSacrifice(&a,&a.boss)==&w2);w1.combat=true;
 nativeRadius=0;assert(!FaerlinaSacrifice(&a,&a.boss));nativeRadius=NAN;assert(!FaerlinaSacrifice(&a,&a.boss));nativeRadius=15;
 a.bot.native.regular=false;a.boss.auras={54100};assert(!FaerlinaSacrifice(&a,&a.boss));
 assert(action.SelectUnderstudy()==&w1);a.boss.auras={28798};assert(!action.SelectUnderstudy());
#else
 assert(!FaerlinaSacrifice(&a,&a.boss));assert(action.SelectUnderstudy()==&w1);
#endif
 a.boss.auras.clear();assert(!action.SelectUnderstudy());
 std::cout<<"PASS actual raid control selection: era/rank/role, native admission, reservations, refusal and sacrifice\n";
}
'''.replace('__POLICY__', (root/'playerbot/strategy/ClassicRaidPolicy.h').as_posix()).replace(
    '__NATIVE__', (root/'playerbot/strategy/NaxxramasNativePolicy.h').as_posix()).replace('__PARTS__', parts)
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='naxx-control-selection-') as folder:
        p = Path(folder)
        (p/'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', '/DMANGOSBOT_'+era,
                        'test.cpp', '/Fe:test.exe'], cwd=p, check=True)
        subprocess.run([str(p/'test.exe')], cwd=p, check=True)
