"""Actual summon actions under three native-interface fixtures, not a raid/client test."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
base = root / "playerbot/strategy"
source = (base / "actions/RitualSummonAction.cpp").read_text()
methods = "\n".join(line for line in source.splitlines() if not line.startswith("#include"))
header = (base / "actions/RitualSummonAction.h").read_text()
header = "\n".join(line for line in header.splitlines() if not line.startswith(("#include", "#pragma")))
value = block((base / "values/RitualSummonValue.h").read_text(), "struct RitualSummonRequest") + ";"
code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <map>
#include <string>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
enum CurrentSpellTypes {CURRENT_GENERIC_SPELL,CURRENT_CHANNELED_SPELL};
enum SpellCastResult {SPELL_CAST_OK=255,SPELL_FAILED_REAGENTS=100};
enum {CLASS_WARLOCK=9,SPELL_STATE_FINISHED=2,GO_JUST_DEACTIVATED=3,
 GAMEOBJECT_TYPE_SUMMONING_RITUAL=18,CMSG_GAMEOBJ_USE=22,TRIGGERED_NONE=0};
time_t clockNow=1000;time_t clockTime(void*){return clockNow;}
#define time clockTime
struct SpellEntry {unsigned Id=698;};
struct Spell {const SpellEntry* m_spellInfo=nullptr;int state=0;int getState()const{return state;}};
int GetSpellDuration(const SpellEntry*){return 120000;}
struct WorldPacket {unsigned guid=0;WorldPacket(int){}WorldPacket& operator<<(unsigned g){guid=g;return *this;}};
struct Session {bool logout=false;unsigned uses=0,lastGuid=0;bool isLogingOut(){return logout;}
 void HandleGameObjectUseOpcode(WorldPacket& packet){++uses;lastGuid=packet.guid;}};
struct Map {};
struct GameObjectInfo {int type=18;struct {unsigned reqParticipants=3;}summoningRitual;};
struct GameObject {unsigned guid=20,entry=36727,spell=698,owner=1,users=1;int loot=0,type=18;
 bool world=true,spawned=true,info=true;float x=0,interaction=5;Map* map=nullptr;GameObjectInfo data;
 bool IsInWorld(){return world;}Map* GetMap(){return map;}unsigned GetEntry(){return entry;}
 unsigned GetObjectGuid(){return guid;}unsigned GetOwnerGuid(){return owner;}unsigned GetSpellId(){return spell;}
 int GetLootState(){return loot;}int GetGoType(){return type;}GameObjectInfo* GetGOInfo(){return info?&data:nullptr;}
 unsigned GetUniqueUseCount(){return users;}float GetInteractionDistance(){return interaction;}};
struct Player;
struct GroupReference {Player* player=nullptr;GroupReference* following=nullptr;
 Player* getSource(){return player;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct Player {unsigned guid=1,mapId=0,instance=0,selection=0;int playerClass=CLASS_WARLOCK;
 bool world=true,alive=true,charmed=false,combat=false,teleport=false,taxi=false,transport=false,knows=true,busy=false,los=true,sessionExists=true;
 float x=0;Map* map=nullptr;Group* group=nullptr;Session session;Spell* generic=nullptr;Spell* channel=nullptr;
 std::map<unsigned,GameObject*> owned;
 SpellCastResult castResult=SPELL_CAST_OK;unsigned casts=0,castId=0,castSelection=0;int castFlags=-1;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}
 bool IsInCombat(){return combat;}bool IsBeingTeleported(){return teleport;}bool IsTaxiFlying(){return taxi;}
 bool GetTransport(){return transport;}Session* GetSession(){return sessionExists?&session:nullptr;}
 Group* GetGroup(){return group;}Map* GetMap(){return map;}unsigned GetObjectGuid(){return guid;}
 unsigned GetMapId(){return mapId;}unsigned GetInstanceId(){return instance;}
 unsigned GetPhaseMask()const{return 1;}
 int getClass(){return playerClass;}bool HasSpell(unsigned id){return knows && id==698;}
 bool IsNonMeleeSpellCasted(bool){return busy || (generic && generic->state!=SPELL_STATE_FINISHED) || (channel && channel->state!=SPELL_STATE_FINISHED);}
 Spell* GetCurrentSpell(CurrentSpellTypes t){return t==CURRENT_GENERIC_SPELL?generic:channel;}
 unsigned GetSelectionGuid(){return selection;}void SetSelectionGuid(unsigned g){selection=g;}
 GameObject* GetGameObject(unsigned id){auto it=owned.find(id);return it==owned.end()?nullptr:it->second;}
 float GetDistance(GameObject* g){return std::abs(x-g->x);}bool IsWithinLOSInMap(GameObject*){return los;}
 SpellCastResult CastSpell(Player* target,unsigned id,int flags){assert(target==this);++casts;castId=id;castFlags=flags;castSelection=selection;return castResult;}
};
namespace ai {__VALUE__}
template<class T>struct Stored {T data{};T Get(){return data;}void Set(T v){data=v;}};
struct Context {Stored<ai::RitualSummonRequest> request;
 template<class T>Stored<T>* GetValue(const char*){return &request;}};
struct PlayerbotAI {Player* bot;Context context;bool movable=true;unsigned moves=0,stops=0,tells=0;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}bool CanMove(){return movable;}
 void StopMoving(){++stops;}void TellPlayerNoFacing(Player*,const char*){++tells;}};
struct Event {};
struct Action {PlayerbotAI* ai;Player* bot;unsigned duration=0;
 Action(PlayerbotAI* a,const char*):ai(a),bot(a->GetBot()){}virtual bool isUseful(){return true;}
 virtual bool isPossible(){return true;}virtual bool Execute(Event&){return false;}void SetDuration(unsigned d){duration=d;}};
struct MovementAction:Action {using Action::Action;bool MoveNear(GameObject*,float){++ai->moves;return ai->movable;}};
struct Facade {SpellEntry info;bool available=true;const SpellEntry* LookupSpellInfo(unsigned){return available?&info:nullptr;}
 bool isSpawned(GameObject* g){return g->spawned;}}sServerFacade;
struct Config {float reactDistance=50;unsigned globalCoolDown=1000;}sPlayerbotAIConfig;
struct ObjectMgr {std::map<unsigned,Player*> players;
 std::map<unsigned,GameObjectInfo> templates;
 const GameObjectInfo* GetGameObjectInfo(unsigned entry){auto it=templates.find(entry);return it==templates.end()?nullptr:&it->second;}
 Player* GetPlayer(unsigned guid){auto it=players.find(guid);return it==players.end()?nullptr:it->second;}}sObjectMgr;
std::vector<GameObject*> grid;
namespace MaNGOS {template<class Check>struct GameObjectSearcher {GameObject*& result;Check& check;
 GameObjectSearcher(GameObject*& r,Check& c):result(r),check(c){assert(c.GetFocusObject().GetPhaseMask()==1);}void Visit(GameObject* g){if(!result && check(g))result=g;}};}
namespace Cell {template<class Search>void VisitGridObjects(Player*,Search& search,float){for(auto* g:grid)search.Visit(g);}}
__HEADER__
__METHODS__
int main(){using namespace ai;
 Map map,other;Group group;Player warlock,target,helper;GroupReference wref,tref,href;
 PlayerbotAI ownerAI{&warlock},helperAI{&helper};GameObject ritual,portal;
 SpellEntry ritualInfo{698};Spell active{&ritualInfo};Event event;
 auto reset=[&](){
  warlock=Player{};target=Player{};helper=Player{};ritual=GameObject{};portal=GameObject{};
  warlock.guid=1;target.guid=2;helper.guid=3;warlock.selection=2;
  warlock.map=target.map=helper.map=&map;warlock.group=target.group=helper.group=&group;
  ritual.map=portal.map=&map;portal.entry=194097;portal.spell=61993;portal.guid=30;portal.type=23;
  wref={&warlock,&tref};tref={&target,&href};href={&helper,nullptr};group.first=&wref;
  ownerAI.context.request.Set({});ownerAI.stops=ownerAI.moves=ownerAI.tells=0;
  helperAI.context.request.Set({});helperAI.moves=0;helperAI.movable=ownerAI.movable=true;
  ritualInfo.Id=698;active.state=0;warlock.channel=&active;warlock.owned={{698,&ritual}};
  grid.clear();sServerFacade.available=true;sObjectMgr.players={{1,&warlock},{2,&target},{3,&helper}};
  sObjectMgr.templates={{36727,GameObjectInfo{}},{194108,GameObjectInfo{}},{179944,GameObjectInfo{}}};
  sObjectMgr.templates[179944].summoningRitual.reqParticipants=2;
 };
 auto start=[&](){warlock.channel=nullptr;return ContinueRitualSummonAction::Start(&ownerAI,&helper,&target);};
 reset();assert(IsNativeSummoningRitual(698)&&IsNativeSummoningRitual(23598)&&!IsNativeSummoningRitual(18540));
 assert(ContinueRitualSummonAction::RequiredHelpers(&warlock)==2);
 sObjectMgr.templates.clear();assert(ContinueRitualSummonAction::RequiredHelpers(&warlock)==0);reset();
#ifdef MANGOSBOT_ZERO
 assert(!IsNativeSummoningRitual(46546)&&!IsNativeSummoningRitual(61994));
#else
 assert(IsNativeSummoningRitual(46546));
#endif
#ifdef MANGOSBOT_TWO
 assert(IsNativeSummoningRitual(61994)&&IsNativeSummoningRitual(59782));
#endif
 AssistSummoningRitualAction assist(&helperAI);ContinueRitualSummonAction continuation(&ownerAI);HoldSummoningRitualAction hold(&ownerAI);
 assert(assist.GetRitual()==&ritual && assist.isPossible());assert(assist.Execute(event));assert(helper.session.uses==1);
 assert(hold.Execute(event)&&hold.duration==500);active.state=SPELL_STATE_FINISHED;assert(!hold.isUseful());
 reset();warlock.channel=nullptr;warlock.generic=&active;assert(HasActiveSummoningRitual(&warlock));assert(!assist.isUseful());
 reset();ritualInfo.Id=18540;assert(!hold.isUseful()&&!assist.isUseful());
 reset();helper.combat=true;assert(!assist.isUseful());
 reset();helper.charmed=true;assert(!assist.isUseful());
 reset();helper.busy=true;assert(!assist.isUseful());
 reset();helper.sessionExists=false;assert(!assist.isUseful());
 reset();helper.map=&other;assert(!assist.isUseful());
 reset();warlock.selection=3;assert(!assist.isUseful());
 reset();warlock.channel=nullptr;assert(!assist.isUseful());
 reset();ritual.users=3;assert(!assist.isUseful());
 reset();ritual.owner=9;assert(!assist.isUseful());
 reset();ritual.loot=GO_JUST_DEACTIVATED;assert(!assist.isUseful());
 reset();ritual.spawned=false;assert(!assist.isUseful());
 reset();helper.x=51;assert(!assist.isUseful());
 reset();helper.x=20;assert(assist.Execute(event)&&helperAI.moves==1&&helper.session.uses==0);
 reset();helper.los=false;assert(!assist.Execute(event));
 reset();helper.x=20;helperAI.movable=false;assert(!assist.isPossible()&&!assist.Execute(event));
 reset();assert(!assist.UseRitual(&portal)); // stale/unrelated object
 reset();assert(start());assert(warlock.casts==1&&warlock.castId==698&&warlock.castFlags==TRIGGERED_NONE&&warlock.castSelection==2);
 reset();warlock.selection=99;warlock.castResult=SPELL_FAILED_REAGENTS;assert(!start());assert(warlock.selection==99&&!ownerAI.context.request.Get().expires);
 reset();warlock.knows=false;assert(!start()&&!warlock.casts);
 reset();warlock.busy=true;assert(!start());
 reset();warlock.charmed=true;assert(!start());
 reset();target.transport=true;assert(!start());
 reset();target.alive=false;assert(!start());
 reset();target.group=nullptr;assert(!start());
 reset();helper.group=nullptr;assert(!start());
 reset();sServerFacade.available=false;assert(!start());
#ifndef MANGOSBOT_TWO
 reset();assert(start());assert(!ownerAI.context.request.Get().expires&&!continuation.isUseful()&&!continuation.Execute(event));
 grid={&portal};assert(!FindOwnedSummoningPortal(&warlock));
#else
 reset();grid={&portal};assert(ContinueRitualSummonAction::RequiredHelpers(&warlock)==1);
 assert(start()&&warlock.casts==0);assert(ownerAI.context.request.Get().expires==clockNow+30);
 assert(continuation.Execute(event));assert(warlock.session.uses==1&&warlock.session.lastGuid==30&&warlock.selection==2);
 assert(!continuation.Execute(event)&&warlock.session.uses==1); // no repeated clicks
 reset();grid={&portal};portal.owner=7;assert(!FindOwnedSummoningPortal(&warlock));assert(start()&&warlock.casts==1);
 reset();grid={&portal};portal.map=&other;assert(!FindOwnedSummoningPortal(&warlock));
 reset();grid={&portal};portal.spell=698;assert(!FindOwnedSummoningPortal(&warlock));
 reset();grid={&portal};portal.spawned=false;assert(!FindOwnedSummoningPortal(&warlock));
 reset();grid={&portal};portal.loot=GO_JUST_DEACTIVATED;assert(!FindOwnedSummoningPortal(&warlock));
 reset();grid={&portal};portal.x=51;assert(!FindOwnedSummoningPortal(&warlock));
 reset();assert(start());warlock.channel=&active;assert(!continuation.isUseful());warlock.channel=nullptr;grid={&portal};assert(continuation.Execute(event));
 reset();assert(start());assert(!start());assert(warlock.casts==1); // one outstanding request
 reset();assert(start());ownerAI.context.request.data.expires=clockNow;assert(!continuation.isUseful()&&!ownerAI.context.request.Get().expires);
 reset();assert(start());warlock.instance=2;assert(!continuation.isUseful()&&!ownerAI.context.request.Get().expires);
 reset();assert(start());target.group=nullptr;assert(!continuation.Execute(event)&&!ownerAI.context.request.Get().expires);
 reset();assert(start());assert(!continuation.Execute(event)&&ownerAI.tells==1&&!ownerAI.context.request.Get().expires);
 reset();grid={&portal};assert(start());portal.x=20;assert(continuation.Execute(event)&&ownerAI.moves==1&&warlock.session.uses==0);
#endif
 std::cout<<"PASS: native ritual start/assist/hold/portal lifecycle and expansion guards\n";
}
'''.replace('__VALUE__', value).replace('__HEADER__', header).replace('__METHODS__', methods)

# No player transport or fake completion in either explicit-ritual path.
command = block((base / "actions/CastCustomSpellAction.cpp").read_text(), 'bool CastCustomSpellAction::CastSummonPlayer(')
for forbidden in ('TeleportTo(', 'SetSummonPoint(', 'SMSG_SUMMON_REQUEST', 'AddCooldown(', 'RemoveCooldown('):
    assert forbidden not in source + command, forbidden
default = (base / 'generic/WorldPacketHandlerStrategy.cpp').read_text()
assert 'new NextAction("assist summoning ritual"' in default
assert 'new NextAction("hold summoning ritual"' in default
assert 'creators["default"]' in (base / 'StrategyContext.h').read_text()

with tempfile.TemporaryDirectory(prefix="mantech-native-ritual-") as folder:
    tmp = Path(folder)
    (tmp / 'test.cpp').write_text(code)
    for expansion in ('ZERO', 'ONE', 'TWO'):
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/W3', f'/DMANGOSBOT_{expansion}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
print('PASS: no direct teleport/packet shortcut; shared default-strategy registration')
