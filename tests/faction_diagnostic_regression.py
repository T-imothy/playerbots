"""Compile actual faction-reaction methods with missing diagnostic metadata."""
from pathlib import Path
import subprocess, tempfile, sys
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'tests'))
from behavior_regression import block
before='--upstream' in sys.argv
git='C:/Program Files/Git/cmd/git.exe'
def read(name):
    if before:return subprocess.check_output([git,'-c','safe.directory='+root.as_posix(),'-C',str(root),'show','upstream/master:'+name],text=True)
    return (root/name).read_text()
methods=block(read('playerbot/GuidPosition.cpp'),'const ReputationRank GuidPosition::GetReactionTo(')+'\n'+block(read('playerbot/PlayerbotAI.cpp'),'ReputationRank PlayerbotAI::GetFactionReaction(')
code=r'''
#include <cassert>
#include <stdexcept>
#include <iostream>
using uint32=unsigned;
enum ReputationRank {REP_HOSTILE,REP_NEUTRAL,REP_FRIENDLY};
enum {UNIT_FIELD_FLAGS,UNIT_FLAG_PLAYER_CONTROLLED,PLAYER_FLAGS,PLAYER_FLAGS_CONTESTED_PVP,UNIT_FIELD_FLAGS_2,UNIT_FLAG2_IGNORE_REPUTATION};
#define MANGOS_ASSERT(x) if(!(x))throw std::runtime_error("missing faction reaches core assertion");
struct FactionTemplateEntry {unsigned faction=1,factionGroupMask=0,enemyGroupMask=0,friendGroupMask=0,enemyFaction[4]{},friendFaction[4]{};bool guard=false;bool IsContestedGuardFaction()const{return guard;}};
struct FactionEntry {bool HasReputation()const{return true;}};
struct Store {bool present=true;FactionEntry entry;const FactionEntry* LookupEntry(unsigned){return present?&entry:nullptr;}template<class T>const T* LookupEntry(unsigned){return present?&entry:nullptr;}}sFactionStore;
struct ReputationMgr {bool war=false,forced=false;ReputationRank rank=REP_FRIENDLY;
 const ReputationRank* GetForcedRankIfAny(const FactionTemplateEntry*)const{return forced?&rank:nullptr;}
 bool IsAtWar(const FactionEntry*)const{return war;}ReputationRank GetRank(const FactionEntry*)const{return rank;}};
struct Player {bool contested=false;ReputationMgr rep;bool HasFlag(int,int)const{return contested;}const ReputationMgr& GetReputationMgr()const{return rep;}};
struct Unit {Player* player=nullptr;bool ignore=false;bool HasFlag(int field,int)const{return field==UNIT_FIELD_FLAGS?player!=nullptr:ignore;}const Player* GetControllingPlayer()const{return player;}};
struct GuidPosition {const FactionTemplateEntry* faction=nullptr;Unit* unit=nullptr;const FactionTemplateEntry* GetFactionTemplateEntry()const{return faction;}bool IsUnit()const{return unit!=nullptr;}Unit* GetUnit(unsigned)const{return unit;}
 const ReputationRank GetReactionTo(const GuidPosition&,uint32)const;};
struct PlayerbotAI {static ReputationRank GetFactionReaction(const FactionTemplateEntry*,const FactionTemplateEntry*);};
__METHODS__
int main(){try{
 FactionTemplateEntry a,b;GuidPosition source{&a},other{&b};
 assert(source.GetReactionTo(other,0)==REP_NEUTRAL);
 source.faction=nullptr;assert(source.GetReactionTo(other,0)==REP_NEUTRAL);
 source.faction=&a;other.faction=nullptr;assert(source.GetReactionTo(other,0)==REP_NEUTRAL);
 Player player;Unit unit{&player};other.unit=&unit;player.contested=true;
 source.faction=nullptr;assert(source.GetReactionTo(other,0)==REP_NEUTRAL);
 source.faction=&a;other.faction=&b;a.guard=true;assert(source.GetReactionTo(other,0)==REP_HOSTILE);
 player.contested=false;player.rep.forced=true;assert(source.GetReactionTo(other,0)==REP_FRIENDLY);
 player.rep.forced=false;sFactionStore.present=false;a.guard=false;assert(source.GetReactionTo(other,0)==REP_NEUTRAL);
 sFactionStore.present=true;
#ifdef MANGOSBOT_ZERO
 player.rep.war=true;assert(source.GetReactionTo(other,0)==REP_HOSTILE);
#else
 player.rep.rank=REP_HOSTILE;assert(source.GetReactionTo(other,0)==REP_HOSTILE);
#endif
 std::cout<<"PASS: missing faction, contested guard, forced reaction, missing faction record and normal reputation\n";
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 90;}}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='faction-diagnostic-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        rc=subprocess.run([str(tmp/'test.exe')],cwd=tmp).returncode
        assert rc==(90 if before else 0),(era,rc)
        if before:print(era,'upstream missing-faction assertion reproduced')
