"""Native Wrath10 crystal opening under the real pending-request control flow.

Execute the production helper with deterministic native-session responses.
No simulated acceptance is confused with proving a live encounter/path.
"""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/RazuviousPullActions.cpp').read_text()
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
code=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <vector>
using uint32=unsigned;using int32=int;using uint8=unsigned char;using time_t=long long;
time_t clockNow=100;time_t fakeTime(void*){return clockNow;}
#define time fakeTime
constexpr unsigned UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=1;
constexpr unsigned CMSG_SPELLCLICK=1,CMSG_PET_CAST_SPELL=2,CMSG_PET_ACTION=3,CMSG_PET_SPELL_AUTOCAST=4,ACT_COMMAND=7,COMMAND_ATTACK=2;
bool IsAutocastable(unsigned id){return id==29061||id==29060;}
constexpr float INTERACTION_DISTANCE=5;
struct ObjectGuid{unsigned id=0;bool operator==(ObjectGuid o)const{return id==o.id;}
 bool operator<(ObjectGuid o)const{return id<o.id;}bool operator!=(ObjectGuid o)const{return id!=o.id;}};
struct Unit;struct Player;struct PlayerbotAI;struct Group;struct PullStrategy;
namespace ai{class Action;}
struct SpellEntry{unsigned Id;};
struct Unit{ObjectGuid guid{},owner{};unsigned entry=0;bool world=true,alive=true,compatible=true,combat=false,casting=false,los=true,ready=true,player=false;
 float distance=10;Unit*victim=nullptr;std::set<unsigned>spells{29060,29061},auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsNonMeleeSpellCasted(bool){return casting;}bool IsPlayer(){return player;}
 bool HasCharmer(){return owner.id!=0;}bool HasCharmer(ObjectGuid g){return owner==g;}
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}
 bool HasSpell(unsigned id){return spells.count(id);}bool HasAura(unsigned id){return auras.count(id);}
 bool IsSpellReady(const SpellEntry&){return ready;}float GetDistance(Unit*){return distance;}
 Unit*GetVictim(){return victim;}};
struct SpellCastTargets{Unit*target=nullptr;void setUnitTarget(Unit*u){target=u;}};
struct WorldPacket{unsigned kind;std::vector<unsigned>data;Unit*target=nullptr;WorldPacket(unsigned k):kind(k){}
 WorldPacket&operator<<(ObjectGuid g){data.push_back(g.id);return *this;}
 WorldPacket&operator<<(unsigned v){data.push_back(v);return *this;}
 WorldPacket&operator<<(uint8 v){data.push_back(v);return *this;}
 WorldPacket&operator<<(SpellCastTargets t){target=t.target;return *this;}};
struct Session{Player*owner=nullptr;Unit*grant=nullptr;bool clickAccepted=false,wallAccepted=false,attackAccepted=false;
 unsigned clicks=0,walls=0,attacks=0;std::vector<unsigned>disabled;
 void HandleSpellClick(WorldPacket&);void HandlePetCastSpellOpcode(WorldPacket&);void HandlePetAction(WorldPacket&);void HandlePetSpellAutocastOpcode(WorldPacket&);};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Player:Unit{PlayerbotAI*brain=nullptr;Group*group=nullptr;Map map;Session session;Unit*charm=nullptr;
 bool transfer=false,tank=false,locked=false;unsigned mapId=533;
 Player(){player=true;session.owner=this;}bool IsBeingTeleported(){return transfer;}Map*GetMap(){return &map;}
 unsigned GetMapId(){return mapId;}Group*GetGroup(){return group;}bool IsInMap(Unit*u){return u&&u->compatible;}
 Unit*GetCharm(){return charm;}PlayerbotAI*GetPlayerbotAI(){return brain;}Session*GetSession(){return &session;}
 bool hasUnitState(unsigned){return locked;}bool IsWithinDistInMap(Unit*u,float limit){return u->distance<=limit;}
 bool IsWithinLOSInMap(Unit*u){return u->los;}};
struct GroupReference{Player*source;GroupReference*following=nullptr;Player*getSource(){return source;}GroupReference*next(){return following;}};
struct Group{std::vector<GroupReference>refs;void set(std::initializer_list<Player*>players){refs.clear();for(auto*p:players){refs.push_back({p});p->group=this;}
 for(size_t i=1;i<refs.size();++i)refs[i-1].following=&refs[i];}GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs[0];}};
struct Context{std::list<ObjectGuid>nearby;ai::Action*action=nullptr;
 template<class T>struct Value{T value;T Get(){return value;}};
 template<class T>Value<T>*GetValue(const char*,const char*){static Value<T>v;v.value=nearby;return &v;}
 ai::Action*GetAction(const char*){return action;}};
struct PlayerbotAI{Player bot;Context context;PullStrategy*pull=nullptr;std::map<unsigned,Unit*>units;
 bool real=false,canMove=true,authorized=true;PlayerbotAI(){bot.brain=this;}
 Player*GetBot(){return &bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}
 bool CanMove(){return canMove;}Unit*GetUnit(ObjectGuid g){auto i=units.find(g.id);return i==units.end()?nullptr:i->second;}
 Context*GetAiObjectContext(){return &context;}void see(Unit&u){units[u.guid.id]=&u;context.nearby.push_back(u.guid);}};
void Session::HandleSpellClick(WorldPacket&p){++clicks;if(clickAccepted&&grant&&!grant->HasCharmer()){
 owner->charm=grant;grant->owner=owner->guid;}}
void Session::HandlePetCastSpellOpcode(WorldPacket&p){++walls;assert(p.data[1]==0&&p.data[2]==29061&&p.data[3]==0);
 if(wallAccepted&&owner->charm&&owner->charm->HasCharmer(owner->guid)&&p.data[0]==owner->charm->guid.id)owner->charm->auras.insert(29061);}
void Session::HandlePetAction(WorldPacket&p){++attacks;assert(p.data[1]==((ACT_COMMAND<<24)|COMMAND_ATTACK));
 if(attackAccepted&&owner->charm&&owner->charm->HasCharmer(owner->guid))owner->charm->victim=owner->brain->GetUnit({p.data[2]});}
void Session::HandlePetSpellAutocastOpcode(WorldPacket&p){assert(p.kind==CMSG_PET_SPELL_AUTOCAST&&p.data.size()==3&&p.data[2]==0);
 assert(owner->charm&&owner->charm->HasCharmer(owner->guid)&&p.data[0]==owner->charm->guid.id);
 disabled.push_back(p.data[1]);}
struct PullStrategy{PlayerbotAI*brain;Unit*target=nullptr;ObjectGuid requester{};time_t start=100;
 bool allowed=true,started=true,pending=true,issued=false;
 PullStrategy(PlayerbotAI*a):brain(a){a->pull=this;}static PullStrategy*Get(PlayerbotAI*a){return a?a->pull:nullptr;}
 bool IsEncounterPreparationAllowed(){return allowed;}bool HasPullStarted(){return started;}bool HasPullActionIssued(){return issued;}
 time_t GetPullStartTime(){return start;}unsigned GetMaxPullTime(){return 15;}Unit*GetTarget(){return target;}
 ObjectGuid GetRequester(){return requester;}bool IsPullPendingToStart(){return pending;}
 void OnPullActionIssued(){issued=true;pending=false;}};
bool CanManageBotCommands(PlayerbotAI*a,Player*){return a->authorized;}
struct Facade{SpellEntry wall{29061};const SpellEntry*LookupSpellInfo(unsigned id){return id==29061?&wall:nullptr;}}sServerFacade;
struct WorldTimer{static unsigned now;static unsigned getMSTime(){return now;}};unsigned WorldTimer::now=1000;
namespace ai{
struct Event{Event(const char* name=""){};};
class Action{public:PlayerbotAI*ai;Player*bot;std::string name;Action(PlayerbotAI*a,std::string n):ai(a),bot(a->GetBot()),name(n){}
 virtual~Action()=default;virtual bool isUseful(){return true;}virtual bool Execute(Event&){return true;}
 std::string getName(){return name;}void SetDuration(unsigned){};};
class ChatCommandAction:public Action{public:using Action::Action;};
class MovementAction:public Action{public:using Action::Action;unsigned moves=0;
 bool MoveNear(Unit*,float){++moves;return true;}};
bool IsRazuviousCrystalPull(PlayerbotAI*,Unit*);bool RazuviousCrystalPullReady(PlayerbotAI*);
bool ExecuteRazuviousCrystalPull(PlayerbotAI*);float RazuviousPreparationMultiplier(PlayerbotAI*,Action*);
class RazuviousPreparationAction:public MovementAction{public:RazuviousPreparationAction(PlayerbotAI*a):MovementAction(a,"razuvious preparation"){}
 bool isUseful()override;bool Execute(Event&)override;private:unsigned nextAttempt=0;};
}
__SOURCE__
int main(){using namespace ai;PlayerbotAI a,b;Player human;Group group;
 a.bot.guid={1};b.bot.guid={2};human.guid={3};a.bot.tank=b.bot.tank=true;group.set({&a.bot,&b.bot,&human});
 Unit boss,c1,c2,s1,s2;boss.guid={100};boss.entry=16061;c1.guid={20};c2.guid={21};c1.entry=c2.entry=29912;
 s1.guid={10};s2.guid={11};s1.entry=s2.entry=16803;
 for(auto*brain:{&a,&b})for(auto*u:{&boss,&c1,&c2,&s1,&s2,static_cast<Unit*>(&human)})brain->see(*u);
 PullStrategy request(&a);request.target=&boss;request.requester=human.guid;
 RazuviousPreparationAction aa(&a),ab(&b);a.context.action=&aa;b.context.action=&ab;Event event;
 Action follow(&a,"follow"),shot(&a,"pull action");ChatCommandAction cancel(&a,"follow command");
#ifndef MANGOSBOT_TWO
 assert(!IsRazuviousCrystalPull(&a,&boss)&&RazuviousCrystalPullReady(&a)&&!aa.isUseful());
 assert(!aa.Execute(event)&&!ExecuteRazuviousCrystalPull(&a)&&RazuviousPreparationMultiplier(&a,&follow)==1);
#else
 assert(IsRazuviousCrystalPull(&a,&boss)&&!RazuviousCrystalPullReady(&a)&&aa.isUseful()&&ab.isUseful());
 assert(RazuviousPreparationMultiplier(&a,&follow)==0&&RazuviousPreparationMultiplier(&a,&cancel)==1&&RazuviousPreparationMultiplier(&a,&shot)==1);
 request.allowed=false;assert(!aa.isUseful()&&!ab.isUseful());request.allowed=true;
 a.authorized=false;assert(!aa.isUseful()&&!ab.isUseful());a.authorized=true;
 request.target=&s1;assert(!aa.isUseful());request.target=&boss;
 request.started=false;assert(!aa.isUseful());request.started=true;
 clockNow=115;assert(!aa.isUseful());clockNow=100;
 a.bot.map.regular=false;assert(!aa.isUseful());a.bot.map.regular=true;
 human.transfer=true;assert(!aa.isUseful());human.transfer=false;
 a.bot.transfer=true;assert(!aa.isUseful());a.bot.transfer=false;
 a.bot.alive=false;assert(!aa.isUseful());a.bot.alive=true;
 boss.combat=true;assert(!aa.isUseful()&&RazuviousCrystalPullReady(&a));boss.combat=false;
 // No click through range/LOS; native refusal leaves ownership/readiness false.
 assert(aa.Execute(event)&&aa.moves==1&&!a.bot.session.clicks);
 c1.distance=2;c1.los=false;assert(aa.Execute(event)&&aa.moves==2&&!a.bot.session.clicks);
 c1.los=true;assert(!aa.Execute(event)&&a.bot.session.clicks==1&&!a.bot.charm&&a.bot.session.disabled.empty());
 assert(!aa.Execute(event)&&a.bot.session.clicks==1);
 WorldTimer::now+=1000;a.bot.session.grant=&s1;a.bot.session.clickAccepted=true;
 assert(aa.Execute(event)&&a.bot.charm==&s1&&!RazuviousCrystalPullReady(&a));
 assert(a.bot.session.disabled==std::vector<unsigned>({29061,29060})&&!a.bot.session.walls&&!a.bot.session.attacks);
 assert(!aa.isUseful()&&ab.isUseful()); // One native owner holds, second tank still prepares.
 assert(RazuviousPreparationMultiplier(&a,&follow)==0);
 c1.casting=true;c2.distance=2;b.bot.session.grant=&s2;b.bot.session.clickAccepted=true;
 assert(ab.Execute(event)&&b.bot.charm==&s2&&aa.isUseful()&&!ab.isUseful());
 assert(b.bot.session.disabled==std::vector<unsigned>({29061,29060})&&a.bot.session.disabled.size()==2);
 WorldTimer::now+=1000;a.bot.casting=true; // Preserve actual owner channel while commanding owned student.
 assert(!aa.Execute(event)&&a.bot.session.walls==1&&!RazuviousCrystalPullReady(&a));
 WorldTimer::now+=300;a.bot.session.wallAccepted=true;assert(aa.Execute(event)&&RazuviousCrystalPullReady(&a));
 assert(!aa.isUseful()&&!a.bot.session.attacks&&!request.issued); // PullStart still pending: no attack yet.
 request.pending=false;WorldTimer::now+=300;assert(!ExecuteRazuviousCrystalPull(&a)&&a.bot.session.attacks==1&&!request.issued);
 WorldTimer::now+=300;a.bot.session.attackAccepted=true;assert(ExecuteRazuviousCrystalPull(&a)&&request.issued&&s1.victim==&boss);
 assert(!aa.isUseful()&&!ab.isUseful()); // Original request completed, no repeat activation.
 request.issued=false;request.pending=true;s1.victim=nullptr;s1.auras.clear();a.bot.casting=false;
 request.target=nullptr;WorldTimer::now+=1000;const auto n=a.bot.session.clicks+a.bot.session.walls+a.bot.session.attacks;
 assert(!aa.Execute(event)&&a.bot.session.clicks+a.bot.session.walls+a.bot.session.attacks==n);request.target=&boss;
 s1.owner={99};assert(!aa.Execute(event)); // Foreign charm cannot be used or silently replaced.
 s1.owner=a.bot.guid;s1.alive=false;assert(!aa.Execute(event));s1.alive=true;
 a.bot.tank=false;b.bot.tank=false;a.bot.charm=b.bot.charm=nullptr;s1.owner={};s2.owner={};
 assert(!aa.isUseful()&&!ab.isUseful()&&!RazuviousCrystalPullReady(&a)); // No controller: deadline, never ranged fallback.
#endif
 std::cout<<"PASS Razuvious native explicit pull preparation, actual ownership/barrier, bounded refusal/cancel and era isolation\n";
}
'''.replace('__SOURCE__',source)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='razuvious-pull-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
