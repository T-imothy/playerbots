"""Run native eligibility and actual bot policy/persistence code in every era."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/LootRollAction.cpp').read_text()
header=(root/'playerbot/strategy/values/RollPolicyValue.h').read_text()
access=(root/'playerbot/strategy/actions/BotCommandAccess.h').read_text()
code=r'''
#include <cassert>
#include <cstdarg>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
enum RollVote{ROLL_PASS,ROLL_NEED,ROLL_GREED,ROLL_DISENCHANT,ROLL_NOT_EMITED_YET,ROLL_NOT_VALID};
enum RollVoteMask{ROLL_VOTE_MASK_PASS=1,ROLL_VOTE_MASK_NEED=2,ROLL_VOTE_MASK_GREED=4,ROLL_VOTE_MASK_DISENCHANT=8};
enum{NEED_BEFORE_GREED=2,EQUIP_ERR_OK=0,SEC_PLAYER=0};
enum class PlayerbotSecurityLevel{PLAYERBOT_SECURITY_ALLOW_ALL};
long long auditTime(void*){return 100;}
#define time auditTime
struct Guid{unsigned long long GetRawValue(){return 42;}};
struct Session{unsigned level=0;unsigned GetSecurity(){return level;}};
struct Player{bool real=true;int usable=0;Session session;bool isRealPlayer(){return real;}
 Session*GetSession(){return &session;}ObjectGuid GetObjectGuid(){return 42;}int CanUseItem(void*){return usable;}};
struct Bot:Player{Guid GetObjectGuid(){return {};}};
struct Security{bool allowed=true;bool CheckLevelFor(PlayerbotSecurityLevel,bool,Player*){return allowed;}};
struct PlayerbotAI{Bot*bot;Player*master=nullptr;Security security;bool realMaster=true;
 Bot*GetBot(){return bot;}Player*GetMaster(){return master;}bool HasRealPlayerMaster(){return realMaster;}Security*GetSecurity(){return &security;}};
namespace ai { __ACCESS__ }
struct Loot{int m_lootMethod=0;};
struct LootItem{bool allowed=true;void*itemProto=nullptr;bool IsAllowed(Player*,Loot*){return allowed;}};
struct GroupLootRoll{struct Vote{RollVote vote=ROLL_NOT_EMITED_YET;};std::map<unsigned,Vote>m_rollVoteMap;
 bool m_isStarted=true;Loot*m_loot;LootItem*m_lootItem;long long m_endTime=200;RollVoteMask m_voteMask=RollVoteMask(7);
 RollVoteMask GetVoteMaskFor(Player*)const;};
__NATIVE__
struct Field{std::string s;std::string GetString(){return s;}};
struct Rows{Field field;Field*Fetch(){return &field;}};
struct Database{
 std::string saved;unsigned reads=0,writes=0,begins=0,commits=0;
 std::unique_ptr<Rows>PQuery(const char*sql,unsigned long long id){assert(id==42);assert(std::string(sql).find("'__roll_policy'")!=std::string::npos);++reads;
  if(saved.empty())return {};return std::make_unique<Rows>(Rows{Field{saved}});}
 void BeginTransaction(){++begins;}void CommitTransaction(){++commits;}
 void PExecute(const char*sql,unsigned long long id,...){assert(id==42);std::string q=sql;assert(q.find("'__roll_policy'")!=std::string::npos);++writes;
  if(q.find("INSERT")==0){va_list args;va_start(args,id);saved=va_arg(args,const char*);va_end(args);}else saved.clear();}
}CharacterDatabase;
namespace ai {
 struct RollPolicyValue{PlayerbotAI*ai;bool loaded=false;std::string value="auto";
  __VALID__
  std::string Get();bool Persist(const std::string&);};
}
using namespace ai;
__GET__
__PERSIST__
struct ItemQualifier{};
bool lootAllowed=true;std::string policy="auto";unsigned autoCalls=0;
struct StoreLootAction{static bool IsLootAllowed(ItemQualifier&,PlayerbotAI*){return lootAllowed;}};
#define AI_VALUE(type,name) ::policy
struct RollAction{PlayerbotAI*ai;RollVote CalculateAutomaticRollVote(ItemQualifier&);
 RollVote CalculateRollVote(ItemQualifier&){++autoCalls;return ROLL_DISENCHANT;}};
__AUTO__
// Extract the actual fallback block from the submission route below.
bool Submit(RollVote& vote,GroupLootRoll*lootRoll,Player*bot,bool automatic){
 __FALLBACK__
 return true;
}
int main(){
 Bot bot;Player owner,stranger;PlayerbotAI ai{&bot,&owner};
 assert(CanManageBotCommands(&ai,&owner));assert(!CanManageBotCommands(&ai,&stranger));assert(!CanManageBotCommands(&ai,nullptr));
 owner.real=false;assert(!CanManageBotCommands(&ai,&owner));owner.real=true;ai.security.allowed=false;assert(!CanManageBotCommands(&ai,&owner));ai.security.allowed=true;
 stranger.session.level=1;assert(CanManageBotCommands(&ai,&stranger));
 RollPolicyValue value{&ai};assert(value.Get()=="auto"&&CharacterDatabase.reads==1);assert(value.Get()=="auto"&&CharacterDatabase.reads==1);
 for(const std::string&mode:{"pass","greed","need","auto"}){
  assert(value.Persist(mode));RollPolicyValue afterRestart{&ai};assert(afterRestart.Get()==mode);
 }
 assert(CharacterDatabase.begins==4&&CharacterDatabase.commits==4&&CharacterDatabase.writes==8);
 assert(!value.Persist("need'; DELETE")&&CharacterDatabase.writes==8&&value.Get()=="auto");
 CharacterDatabase.saved="bad";RollPolicyValue corrupt{&ai};assert(corrupt.Get()=="auto");
 ItemQualifier item;RollAction action{&ai};assert(action.CalculateAutomaticRollVote(item)==ROLL_DISENCHANT&&autoCalls==1);
 for(const auto&mode:{"pass","greed","need"}){policy=mode;auto vote=action.CalculateAutomaticRollVote(item);assert(vote==(policy=="pass"?ROLL_PASS:policy=="need"?ROLL_NEED:ROLL_GREED));}
 lootAllowed=false;assert(action.CalculateAutomaticRollVote(item)==ROLL_PASS);lootAllowed=true;assert(autoCalls==1);
 Loot loot;LootItem lootItem;GroupLootRoll roll;roll.m_loot=&loot;roll.m_lootItem=&lootItem;roll.m_rollVoteMap[42]={};
 assert(roll.GetVoteMaskFor(&bot)==7);loot.m_lootMethod=NEED_BEFORE_GREED;bot.usable=1;assert(roll.GetVoteMaskFor(&bot)==5);
 policy="need";RollVote vote=ROLL_NEED;assert(Submit(vote,&roll,&bot,true)&&vote==ROLL_GREED);
 roll.m_voteMask=ROLL_VOTE_MASK_PASS;vote=ROLL_NEED;assert(Submit(vote,&roll,&bot,true)&&vote==ROLL_PASS);
 roll.m_voteMask=RollVoteMask(0);vote=ROLL_NEED;assert(!Submit(vote,&roll,&bot,true));
 roll.m_voteMask=RollVoteMask(7);lootItem.allowed=false;assert(roll.GetVoteMaskFor(&bot)==0);lootItem.allowed=true;
 roll.m_rollVoteMap[42].vote=ROLL_NOT_VALID;assert(roll.GetVoteMaskFor(&bot)==0);
 roll.m_rollVoteMap[42].vote=ROLL_GREED;assert(roll.GetVoteMaskFor(&bot)==0);
 roll.m_rollVoteMap[42].vote=ROLL_NOT_EMITED_YET;roll.m_endTime=100;assert(roll.GetVoteMaskFor(&bot)==0);roll.m_endTime=200;
 roll.m_isStarted=false;assert(roll.GetVoteMaskFor(&bot)==0);roll.m_isStarted=true;assert(!roll.GetVoteMaskFor(nullptr));
 vote=ROLL_NEED;policy="auto";assert(Submit(vote,&roll,&bot,true)&&vote==ROLL_NEED);policy="need";assert(Submit(vote,&roll,&bot,false)&&vote==ROLL_NEED);
 std::cout<<"PASS: policy persistence, invalid/auth/default cases, native eligibility, restricted-Need fallback and legacy auto/manual isolation\n";
}
'''
code=code.replace('__ACCESS__',block(access,'    inline bool CanManageBotCommands(')).replace('__VALID__',block(header,'        static bool IsValid('))
for key,signature in [('__GET__','std::string RollPolicyValue::Get('),('__PERSIST__','bool RollPolicyValue::Persist('),('__AUTO__','RollVote RollAction::CalculateAutomaticRollVote(')]:
 code=code.replace(key,block(source,signature))
code=code.replace('__FALLBACK__',block(source,'    if (automatic && AI_VALUE'))
for era,macro in [('classic','ZERO'),('tbc','ONE'),('wotlk','TWO')]:
 native=(root.parent/f'mangos-{era}-behavior/src/game/Loot/LootMgr.cpp').read_text()
 with tempfile.TemporaryDirectory(prefix='roll-policy-') as d:
  p=Path(d);(p/'test.cpp').write_text(code.replace('__NATIVE__',block(native,'RollVoteMask GroupLootRoll::GetVoteMaskFor(')))
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{macro}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
# Both automatic dispatch paths use the policy; explicit votes still use legacy decisions.
for name in ('LootRollAction','AutoLootRollAction'):
 body=block(source,f'bool {name}::Execute(')
 assert 'CalculateAutomaticRollVote' in body and ', true)' in body
assert 'CalculateRollVote(itemQualifier)' in block(source,'bool RollAction::Execute(')
assert 'CanManageBotCommands(ai, requester)' in block(source,'bool RollAction::Execute(')
assert '"pass"' in block(source,'bool AutoLootRollAction::isPossible(')
