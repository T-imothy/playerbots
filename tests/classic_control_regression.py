"""Actual Classic possession controller and packet submission, including refusals."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
src=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
parts='\n'.join(block(src,marker) for marker in ('    bool Ready(','    bool NaxxRegular(','    bool SubmitControlledSpell(','    Unit* ControlledRelief(','bool ClassicRaidControlAction::UpdateControl('))
code=r'''
#include <cassert>
#include <iostream>
#include <set>
#include <vector>
#include <cstdint>
#include "__POLICY__"
#include "__NATIVE__"
using namespace ai;
using uint32=unsigned;using int32=int;using uint8=unsigned char;
constexpr unsigned CLASS_PRIEST=5,CMSG_PET_CAST_SPELL=1,CMSG_PET_ACTION=2,CMSG_PET_SPELL_AUTOCAST=3,ACT_COMMAND=7,COMMAND_ATTACK=2;
struct Guid{unsigned id=0;void Clear(){id=0;}bool operator==(Guid b)const{return id==b.id;}bool operator!=(Guid b)const{return id!=b.id;}bool operator<(Guid b)const{return id<b.id;}};
struct Unit;
struct PlayerbotAI;
struct SpellEntry{unsigned Id;};
bool IsSpellRequireTarget(const SpellEntry*s){return s->Id==29060;}
bool IsAutocastable(unsigned){return true;}
struct Facade{SpellEntry a{29061},b{29060},c{28732},d{54097};const SpellEntry*LookupSpellInfo(unsigned id){return id==29061?&a:id==29060?&b:id==28732?&c:id==54097?&d:nullptr;}}sServerFacade;
struct SpellCastTargets{Unit*target=nullptr;void setUnitTarget(Unit*u){target=u;}};
struct WorldPacket{unsigned kind;std::vector<unsigned>data;Unit*target=nullptr;WorldPacket(unsigned k):kind(k){}
 WorldPacket&operator<<(Guid g){data.push_back(g.id);return *this;}WorldPacket&operator<<(unsigned v){data.push_back(v);return *this;}
 WorldPacket&operator<<(uint8 v){data.push_back(v);return *this;}WorldPacket&operator<<(SpellCastTargets t){target=t.target;return *this;}};
struct Unit{unsigned entry=16803;Guid guid{2},owner{1};bool world=true,alive=true,sameMap=true,casting=false,ready=true,tauntReady=true;
 bool melee=true,los=true;Unit*victim=nullptr;std::set<unsigned>spells{29061,29060,28732,54097},auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(Guid g){return owner==g;}
 unsigned GetEntry(){return entry;}Guid GetObjectGuid(){return guid;}bool HasSpell(unsigned id){return spells.count(id);}
 bool IsSpellReady(const SpellEntry&s){return s.Id==29060?tauntReady:ready;}bool IsNonMeleeSpellCasted(bool){return casting;}
 bool HasAura(unsigned id){return auras.count(id);}Unit*GetVictim(){return victim;}
 bool CanReachWithMeleeAttack(Unit*){return melee;}bool IsWithinLOSInMap(Unit*){return los;}};
struct Session{unsigned casts=0,attacks=0,effects=0,lastSpell=0;bool nativeAccepted=true;
 unsigned disabled=0;void HandlePetSpellAutocastOpcode(WorldPacket&){++disabled;}
 void HandlePetCastSpellOpcode(WorldPacket&p){++casts;
#ifdef MANGOSBOT_TWO
 assert(p.data[1]==0);lastSpell=p.data[2];
#else
 lastSpell=p.data[1];
#endif
 if(nativeAccepted)++effects;}
 void HandlePetAction(WorldPacket&){++attacks;}};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Player:Unit{PlayerbotAI*brain=nullptr;unsigned map=533,cls=CLASS_PRIEST;bool combat=true,transfer=false,charmed=false;Unit*charm=nullptr;Session session;Map native;Map*GetMap(){return &native;}
 Player(){guid={1};}bool IsInCombat(){return combat;}bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charmed;}
 unsigned GetMapId(){return map;}void*GetGroup(){return this;}unsigned getClass(){return cls;}Unit*GetCharm(){return charm;}
 bool IsInMap(Unit*u){return u&&u->sameMap;}Session*GetSession(){return &session;}PlayerbotAI*GetPlayerbotAI(){return brain;}};
struct PlayerbotAI{Player bot;Unit boss;std::vector<Player*>roster;bool real=false,engaged=true;PlayerbotAI(){boss.entry=16061;boss.guid={3};bot.brain=this;roster={&bot};}
 Player*GetBot(){return &bot;}bool IsRealPlayer(){return real;}};
struct WorldTimer{static unsigned now;static unsigned getMSTime(){return now;}};unsigned WorldTimer::now=1000;
Unit*FindBoss(PlayerbotAI*a,unsigned entry){return a->engaged&&a->boss.entry==entry?&a->boss:nullptr;}
std::vector<Player*>Members(PlayerbotAI*a){return a->roster;}
bool ControlledInRadius(PlayerbotAI*,Unit*,Unit*,float){return true;}
float NativeEncounterSpellRadius(unsigned){return 15;}
struct ClassicRaidControlAction{PlayerbotAI*ai;Player*bot;unsigned nextControl=0;Guid configuredCharm{};bool UpdateControl();};
__PARTS__
int main(){PlayerbotAI brain;Unit student;brain.bot.charm=&student;ClassicRaidControlAction action{&brain,&brain.bot};
 assert(action.UpdateControl()&&brain.bot.session.lastSpell==29061&&brain.bot.session.casts==1);
 assert(brain.bot.session.disabled==3); // once per native owned charm, prevent PetAI timing races
 assert(action.UpdateControl()&&brain.bot.session.casts==1); // bounded 300ms attempts
 WorldTimer::now+=300;student.auras.insert(29061);assert(action.UpdateControl());assert(brain.bot.session.lastSpell==29060);
 brain.boss.victim=&student;student.victim=&brain.boss;WorldTimer::now+=300;assert(action.UpdateControl());assert(brain.bot.session.casts==2);
 Unit other;other.auras.insert(29061);brain.boss.victim=&other;WorldTimer::now+=300;assert(action.UpdateControl());assert(brain.bot.session.casts==2); // healthy holder kept
 other.auras.clear();student.ready=false;student.tauntReady=false;WorldTimer::now+=300;assert(action.UpdateControl());assert(brain.bot.session.casts==2);
 student.ready=true;student.tauntReady=true;student.auras.clear();brain.bot.session.nativeAccepted=false;WorldTimer::now+=300;
 const auto effects=brain.bot.session.effects;assert(action.UpdateControl());assert(brain.bot.session.effects==effects&&!student.HasAura(29061)); // rejected packet grants no fabricated aura
 student.owner={99};assert(!action.UpdateControl());student.owner={1};student.sameMap=false;assert(!action.UpdateControl());student.sameMap=true;
 brain.engaged=false;assert(!action.UpdateControl());brain.engaged=true;brain.bot.map=409;assert(!action.UpdateControl());brain.bot.map=533;
 brain.bot.transfer=true;assert(!action.UpdateControl());brain.bot.transfer=false;brain.real=true;assert(!action.UpdateControl());brain.real=false;
 student.entry=16506;brain.boss.entry=15953;brain.bot.native.regular=false;
 brain.boss.auras.insert(naxxnative::FaerlinaFrenzy(false));brain.bot.casting=true;WorldTimer::now+=300;
 assert(action.UpdateControl()&&brain.bot.session.lastSpell==naxxnative::FaerlinaEmbrace(false)&&brain.bot.casting); // owner's MC channel not interrupted
 brain.boss.auras.clear();WorldTimer::now+=300;const auto count=brain.bot.session.casts;assert(action.UpdateControl()&&brain.bot.session.casts==count);
 PlayerbotAI first,second;Unit a,b;b.guid={4};second.bot.guid={5};b.owner={5};first.bot.charm=&a;second.bot.charm=&b;
 first.roster=second.roster={&first.bot,&second.bot};ClassicRaidControlAction ca{&first,&first.bot},cb{&second,&second.bot};
 WorldTimer::now+=300;assert(ca.UpdateControl()&&first.bot.session.casts==1);a.auras.insert(29061);a.ready=false;
 assert(cb.UpdateControl()&&second.bot.session.casts==0); // both cannot spend their shield on the same frame
 a.auras.clear();WorldTimer::now+=300;assert(ca.UpdateControl()&&first.bot.session.casts==1);
 assert(cb.UpdateControl()&&second.bot.session.casts==1); // actual ready relief elected after shield expiry
 b.auras.clear();b.melee=false;WorldTimer::now+=300;const auto previous=second.bot.session.casts;
 assert(cb.UpdateControl()&&second.bot.session.casts==previous); // approach before spending wall/taunt out of range
 a.ready=true;a.melee=false;b.melee=true;WorldTimer::now+=300;
 assert(ControlledRelief(&first,&first.boss)==&b); // an unreachable earlier GUID cannot monopolize relief
 const auto disabled=first.bot.session.disabled;first.bot.charm=nullptr;assert(!ca.UpdateControl());
 first.bot.charm=&a;a.melee=true;WorldTimer::now+=300;assert(ca.UpdateControl());
 assert(first.bot.session.disabled==disabled+3); // same native actor re-acquired after charm reinitialization
 std::cout<<"PASS actual owned Classic student/worshipper control, bounded native packet submission, no fabricated success/channel cancellation\n";
}
'''.replace('__POLICY__',(root/'playerbot/strategy/ClassicRaidPolicy.h').as_posix()).replace('__NATIVE__',(root/'playerbot/strategy/NaxxramasNativePolicy.h').as_posix()).replace('__PARTS__',parts)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='classic-control-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
