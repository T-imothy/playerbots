"""Compile the actual observer/buffer/writer with controlled core interfaces."""
import re
import subprocess
import tempfile
from pathlib import Path
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
header = (root / 'playerbot/CombatDiagnostics.h').read_text().replace('#pragma once', '')
impl = (root / 'playerbot/CombatDiagnostics.cpp').read_text()
strip = lambda s: re.sub(r'^#include "[^\n]+\n', '', s, flags=re.M)
probe = block((root / 'playerbot/PlayerbotAI.cpp').read_text(), 'class CombatSpellCheck') + ';'
mock = r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <filesystem>
#include <fstream>
using uint32=uint32_t;using uint64=uint64_t;using int32=int32_t;
enum SpellCastResult {SPELL_CAST_OK=255,SPELL_FAILED_NOT_READY=42};
const char* GetSpellCastResultString(SpellCastResult){return "core_reason";}
struct Guid{uint64 GetRawValue(){return 123;}};
class Unit{public:virtual ~Unit(){} Guid GetObjectGuid(){return {};}int* GetMap(){static int x;return &x;}int GetReactionTo(Unit*){return 4;}};
class Player:public Unit{public:uint32 guid=42,klass=1;bool world=true;bool IsInWorld(){return world;}uint32 GetGUIDLow(){return guid;}uint32 getClass(){return klass;}uint32 GetLevel(){return 60;}bool IsInCombat(){return true;}uint32 GetMapId(){return 0;}uint32 GetInstanceId(){return 1;}Unit* GetPet(){return nullptr;}bool IsFriendlyTo(Unit*){return false;}float GetDistance(Unit*){return 3;}};
class PlayerbotAI{public:Player bot;bool human=false;Player* GetBot(){return &bot;}bool IsRealPlayer(){return human;}static bool IsTank(Player*){return false;}static bool IsHeal(Player*){return false;}bool IsRanged(Player*){return false;}};
struct Config{bool combatDiagnosticsEnabled=false,diagnosticsEnabled=true;uint32 combatDiagnosticsSampleRate=2,combatDiagnosticsClassMask=4094,combatDiagnosticsTraceBot=0,combatDiagnosticsMaxKeys=4,combatDiagnosticsMaxTraces=2,combatDiagnosticsMaxFileMB=1;std::string GetTimestampStr(){return "TEST";}}sPlayerbotAIConfig;
struct CoreConfig{std::string GetStringDefault(const char*){return "";}}sConfig;
'''
test = r'''
int main(){PlayerbotAI ai;
 for(int i=0;i<100;++i)assert(!ai::CombatDiagnostics::Select(&ai));
 ai::CombatDiagnostics::Flush();assert(!std::filesystem::exists("PlayerbotCombat.log"));
 sPlayerbotAIConfig.combatDiagnosticsEnabled=true;int selected=0;
 for(int i=0;i<100;++i) selected+=ai::CombatDiagnostics::Select(&ai);assert(selected==50);
 ai.human=true;assert(!ai::CombatDiagnostics::Select(&ai));ai.human=false;
 sPlayerbotAIConfig.combatDiagnosticsClassMask=1<<9;assert(!ai::CombatDiagnostics::Select(&ai));
 sPlayerbotAIConfig.combatDiagnosticsClassMask=4094;sPlayerbotAIConfig.combatDiagnosticsTraceBot=42;
 assert(ai::CombatDiagnostics::Select(&ai));
 assert(ai::CombatActionContext::Current()=="outside_engine_action");
 std::string first="first",second="second";
 {ai::CombatActionContext x(first);assert(ai::CombatActionContext::Current()==first);{ai::CombatActionContext y(second);assert(ai::CombatActionContext::Current()==second);}assert(ai::CombatActionContext::Current()==first);}
 assert(ai::CombatActionContext::Current()=="outside_engine_action");
 SpellCastResult original=SPELL_CAST_OK;SpellCastResult* output=&original;
 {CombatSpellCheck check(&ai,123,&ai.bot,output);*output=SPELL_FAILED_NOT_READY;}
 assert(original==SPELL_FAILED_NOT_READY);
 original=SPELL_CAST_OK;output=&original;{CombatSpellCheck check(&ai,123,nullptr,output);}assert(original==SPELL_CAST_OK);
 sPlayerbotAIConfig.combatDiagnosticsEnabled=false;output=&original;
 {CombatSpellCheck check(&ai,123,nullptr,output);assert(output==&original);}
 sPlayerbotAIConfig.combatDiagnosticsEnabled=true;
 for(int i=0;i<20;++i)ai::CombatDiagnostics::Record(&ai,"a"+std::to_string(i),"test","action_execute",1);
 assert(buckets.size()<=4&&traces.size()<=2&&droppedKeys>0&&droppedTraces>0);
 ai::CombatDiagnostics::Flush();assert(buckets.empty()&&traces.empty());
 sPlayerbotAIConfig.combatDiagnosticsMaxKeys=2048;
 for(int pass=0;pass<8;++pass){for(int i=0;i<2048;++i)ai::CombatDiagnostics::Record(&ai,std::to_string(i)+std::string(200,'x'),std::string(200,'y'),"action_execute",1);ai::CombatDiagnostics::Flush();}
 assert(std::filesystem::file_size("PlayerbotCombat.log")<=1024*1024);
 assert(std::filesystem::file_size("PlayerbotCombat.log.1")<=1024*1024);
}
'''
for expansion in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-combat-') as tmp:
        path = Path(tmp)
        (path/'test.cpp').write_text(mock + strip(header) + strip(impl) + probe + test)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{expansion}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(path/'test.exe')],cwd=tmp,check=True)
        print('PASS:', expansion, 'disabled/filter/sample/context/result/caps/flush/rotation', flush=True)
