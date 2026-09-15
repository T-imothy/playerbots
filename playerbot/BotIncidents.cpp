#include "playerbot/playerbot.h"
#include "PlayerbotDiagnostics.h"
#include <chrono>
#include <cstdio>
#include <cerrno>
#include <sstream>

using namespace ai;
namespace {
uint64 IncidentNow() { return std::chrono::duration_cast<std::chrono::milliseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count(); }
std::string IncidentText(std::string value) {
    if(value.size()>96) value.resize(96);
    for(char& c:value) if(static_cast<unsigned char>(c)<32 || c=='"' || c=='\\') c='_';
    return value;
}
}
bool PlayerbotDiagnostics::IncidentsEnabled() const {
    return IsEnabled() && IsDeepEnabled() && sPlayerbotAIConfig.diagnosticIncidents;
}
void PlayerbotDiagnostics::RecordBotIncident(uint32 bot, BotIncidentKind kind, bool open,
    uint64 target,uint32 duration,uint32 map,uint32 zone,std::string const& action)
{
    if(!IncidentsEnabled()) return;
    BotIncident entry;
    entry.bot=bot;entry.kind=kind;entry.open=open;entry.target=target;entry.duration=duration;
    entry.map=map;entry.zone=zone;entry.action=action;entry.updated=IncidentNow();
    std::lock_guard<std::mutex> guard(incidentMutex);
    incidentStore.Record(std::move(entry));
}
void PlayerbotDiagnostics::CloseBotIncidents(uint32 bot) {
    std::lock_guard<std::mutex> guard(incidentMutex);
    incidentStore.CloseBot(bot);
}
void PlayerbotDiagnostics::FlushIncidents() {
    if(!IncidentsEnabled()) return;
    std::vector<BotIncident> rows;uint64 overflow;size_t active;
    {
        std::lock_guard<std::mutex> guard(incidentMutex);
        incidentStore.Expire(IncidentNow());rows=incidentStore.Snapshot();
        active=incidentStore.Active();overflow=incidentStore.Overflow();
    }
    const std::string stamp=sPlayerbotAIConfig.GetTimestampStr();
    const uint64 seq=++incidentSequence;
    std::ostringstream out;
    out<<stamp<<" PB_INCIDENTS_BEGIN seq="<<seq<<" active="<<active<<" rows="<<rows.size()
       <<" overflow="<<overflow<<" capacity=1024 history=200\n";
    for(auto const& e:rows) out<<stamp<<" PB_INCIDENT id="<<e.id<<" bot="<<e.bot<<" type="
        <<BotIncidentName(e.kind)<<" state="<<(e.open?"active":"resolved")<<" target="<<e.target
        <<" duration_ms="<<e.duration<<" map="<<e.map<<" zone="<<e.zone
        <<" action=\""<<IncidentText(e.action)<<"\" reason=\""<<IncidentText(e.reason)<<"\"\n";
    out<<stamp<<" PB_INCIDENTS_END seq="<<seq<<" rows="<<rows.size()<<"\n";
    std::string directory=sConfig.GetStringDefault("LogsDir");
    if(!directory.empty() && directory.back()!='/' && directory.back()!='\\') directory+='/';
    const std::string path=directory+"PlayerbotIncidents.log",previous=path+".1",block=out.str();
    FILE* file=fopen(path.c_str(),"ab+");
    if(!file) return;
    if(fseek(file,0,SEEK_END)!=0) {fclose(file);return;}
    long size=ftell(file);
    if(size<0) {fclose(file);return;}
    // Rotate before the whole snapshot; a reader never needs to join files.
    if(uint64(size)+block.size()>8*1024*1024) {
        fclose(file);
        if(std::remove(previous.c_str())!=0 && errno!=ENOENT) return;
        if(std::rename(path.c_str(),previous.c_str())!=0) return;
        file=fopen(path.c_str(),"ab+");if(!file)return;
    }
    fwrite(block.data(),1,block.size(),file);fclose(file);
}
