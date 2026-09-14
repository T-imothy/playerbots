"""Compile the actual altar action against a bounded native-interface fixture."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
actions=root/'playerbot/strategy/actions'
def clean(path):return '\n'.join(s for s in path.read_text().splitlines() if not s.startswith(('#include','#pragma')))
methods=clean(actions/'UldamanAltarAction.cpp')
header=clean(actions/'UldamanAltarAction.h')
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <ctime>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;
enum {GO_JUST_DEACTIVATED=3,GAMEOBJECT_TYPE_SUMMONING_RITUAL=18,CURRENT_CHANNELED_SPELL=1,SPELL_STATE_FINISHED=2,CMSG_GAMEOBJ_USE=22};
time_t now=1000;time_t testTime(void*){return now;}
#define time testTime
struct SpellEntry{unsigned Id=11206;};
struct Spell{SpellEntry* m_spellInfo=nullptr;int state=0;int getState()const{return state;}};
struct GameObjectInfo{struct {unsigned reqParticipants=3,animSpell=11206,spellId=11568;}summoningRitual;};
struct GameObject{bool world=true,spawned=true,same=true;unsigned guid=9,entry=130511,owner=0,users=1;int loot=0,type=18;float x=0;GameObjectInfo info;
 bool IsInWorld(){return world;}int GetLootState(){return loot;}unsigned GetOwnerGuid(){return owner;}
 int GetGoType(){return type;}GameObjectInfo* GetGOInfo(){return &info;}unsigned GetEntry(){return entry;}
 unsigned GetObjectGuid(){return guid;}unsigned GetUniqueUseCount(){return users;}float GetInteractionDistance(){return 5;}};
struct WorldPacket{unsigned guid=0;WorldPacket(int){}WorldPacket& operator<<(unsigned g){guid=g;return *this;}};
struct Session{unsigned uses=0,guid=0;void HandleGameObjectUseOpcode(WorldPacket& p){++uses;guid=p.guid;}};
struct Group;struct Player{unsigned guid=1,map=70,instance=1;bool valid=true,world=true,teleport=false,busy=false,los=true;float x=0;Group* group=nullptr;Spell* channel=nullptr;Session session;
 bool IsInWorld(){return world;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return map;}
 unsigned GetMap(){return map*1000+instance;}unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 unsigned GetObjectGuid(){return guid;}bool IsInMap(GameObject* o){return o->same;}
 float GetDistance(GameObject* o){return std::abs(x-o->x);}bool IsNonMeleeSpellCasted(bool){return busy||channel;}
 Spell* GetCurrentSpell(int){return channel;}bool IsWithinLOSInMap(GameObject*){return los;}Session* GetSession(){return &session;}};
struct GroupReference{Player* player;GroupReference* nextRef;Player* getSource(){return player;}GroupReference* next(){return nextRef;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai{struct UldamanAltarRequest{unsigned altar=0,requester=0,instance=0;time_t expires=0;};}
template<class T>struct Stored{T data{};T Get(){return data;}void Set(T t){data=t;}};
struct Context{Stored<ai::UldamanAltarRequest> request;template<class T>Stored<T>* GetValue(const char*){return &request;}};
struct PlayerbotAI{Player* bot;GameObject* altar;Context context;bool movable=true;unsigned moves=0,stops=0;
 Player* GetBot(){return bot;}GameObject* GetGameObject(unsigned g){return altar&&altar->guid==g?altar:nullptr;}
 Context* GetAiObjectContext(){return &context;}bool CanMove(){return movable;}void StopMoving(){++stops;}};
struct Facade{bool isSpawned(GameObject* g){return g->spawned;}}sServerFacade;
struct Config{float reactDistance=50;unsigned globalCoolDown=1500;}sPlayerbotAIConfig;
namespace ai{
bool CanParticipateInRitual(Player* p){return p&&p->valid&&p->world&&!p->teleport;}
struct Event{};
class MovementAction{protected:PlayerbotAI* ai;Player* bot;public:
 MovementAction(PlayerbotAI* a,const char*):ai(a),bot(a->bot){}virtual bool isUseful(){return true;}
 virtual bool isPossible(){return true;}virtual bool Execute(Event&){return true;}
 bool MoveNear(GameObject*,float){++ai->moves;return true;}void SetDuration(unsigned){} };
}
__HEADER__
__METHODS__
int main(){
 Player bot,master;GameObject altar;Group group,other;SpellEntry entry;Spell channel{&entry};GroupReference member{&master,nullptr};PlayerbotAI ai{&bot,&altar};ai::Event event;ai::AssistUldamanAltarAction action(&ai);
 auto reset=[&](){bot=Player{};master=Player{};master.guid=2;altar=GameObject{};bot.group=master.group=&group;group.first=&member;master.channel=&channel;ai.context.request.Set({});ai.moves=ai.stops=0;ai.movable=true;ai.altar=&altar;now=1000;entry.Id=11206;channel.state=0;};
 auto start=[&](){return ai::AssistUldamanAltarAction::Start(&ai,&master,altar.guid);};
 reset();assert(!action.isUseful());assert(start()&&action.isUseful());assert(action.Execute(event)&&bot.session.uses==1&&bot.session.guid==altar.guid);assert(altar.users==1); // Native handler owns participant changes.
 reset();altar.entry=133234;altar.info.summoningRitual.spellId=10340;assert(start()&&action.Execute(event));
 reset();altar.info.summoningRitual.reqParticipants=1;assert(!start());
 reset();altar.entry=36727;assert(!start());
 reset();altar.owner=2;assert(!start());
 reset();altar.info.summoningRitual.spellId=698;assert(!start());
 reset();master.group=&other;assert(!start());
 reset();master.instance=2;assert(!start());
 reset();bot.map=1;assert(!start());
 reset();master.x=6;assert(!start());
 reset();bot.x=51;assert(!start());
 reset();bot.valid=false;assert(!start());
 reset();assert(start());bot.x=20;assert(action.Execute(event)&&ai.moves==1&&!bot.session.uses);
 reset();assert(start());bot.x=20;ai.movable=false;assert(!action.isPossible()&&!action.Execute(event));
 reset();assert(start());bot.los=false;assert(!action.Execute(event)&&!bot.session.uses);
 reset();assert(start());master.channel=nullptr;assert(!action.Execute(event));
 reset();assert(start());channel.state=SPELL_STATE_FINISHED;assert(!action.Execute(event));
 reset();assert(start());entry.Id=698;assert(!action.Execute(event));
 reset();assert(start());altar.users=0;assert(!action.Execute(event));
 reset();assert(start());altar.users=3;assert(!action.Execute(event));
 reset();assert(start());altar.spawned=false;assert(!action.Execute(event));
 reset();assert(start());altar.same=false;assert(!action.Execute(event));
 reset();assert(start());ai.altar=nullptr;assert(!action.Execute(event));
 reset();assert(start());now+=31;assert(!action.Execute(event)&&!ai.context.request.data.expires);
 reset();assert(start());bot.instance=2;assert(!action.Execute(event)&&!ai.context.request.data.expires);
 reset();assert(start());master.group=nullptr;group.first=nullptr;assert(!action.Execute(event));
 reset();assert(start());master.group=&other;assert(!action.Execute(event)&&!ai.context.request.data.expires);
 reset();assert(start());bot.channel=&channel;assert(!action.Execute(event)&&!bot.session.uses);
 reset();assert(start());bot.teleport=true;assert(!action.Execute(event));
 std::cout<<"PASS: altar selection, invitation, movement, channel, completion and stale-request cases\n";
}
'''.replace('__HEADER__',header).replace('__METHODS__',methods)
default=(root/'playerbot/strategy/generic/WorldPacketHandlerStrategy.cpp').read_text()
assert 'new NextAction("assist uldaman altar"' in default
assert 'AssistUldamanAltarAction::Start' in (actions/'UseMeetingStoneAction.cpp').read_text()
assert 'player->GetMapId() == 70 && spell->m_spellInfo->Id == 11206' in (actions/'RitualSummonAction.cpp').read_text()
for forbidden in ('AddUniqueUse(', 'SetData(', 'TriggerSummoningRitual(', 'TeleportTo('):assert forbidden not in methods
with tempfile.TemporaryDirectory(prefix='uldaman-altar-') as tmp:
    p=Path(tmp);(p/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++20','/EHsc','/UNDEBUG',str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True)
    subprocess.run([str(p/'test.exe')],check=True)
