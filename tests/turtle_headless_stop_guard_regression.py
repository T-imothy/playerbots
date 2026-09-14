from pathlib import Path
from turtle_cpp_fixture import run
r=Path(__file__).resolve().parents[3]
s=(r/'src/game/HeadlessSessionMgr.cpp').read_text(encoding='utf-8')
s=s[s.index('void HeadlessSessionMgr::EndStopDeferral()'):s.index('void HeadlessSessionMgr::StopForAccount(')]
run(r'''#include <map>
#include <vector>
#include <cassert>
#include <cstdint>
#include <cstdio>
using uint64=uint64_t;using uint32=uint32_t;using ObjectGuid=int;
#define MANGOS_ASSERT assert
struct HeadlessSessionMgr {
 struct SessionEntry{uint64 requestToken;};struct DeferredStop{uint64 token;bool save;};
 std::map<int,SessionEntry>m_sessions,m_pendingSessions;std::map<int,DeferredStop>m_deferredStops;
 uint32 m_stopDeferralDepth=0;std::vector<std::pair<uint64,bool>>destroyed;
 void BeginStopDeferral(){++m_stopDeferralDepth;}void EndStopDeferral();bool Stop(int,bool=true);
 void DestroySession(SessionEntry&e,bool save,bool){destroyed.emplace_back(e.requestToken,save);}
};
'''+s+r'''
int main(){
 HeadlessSessionMgr m;m.m_sessions[1]={10};
 m.BeginStopDeferral();m.BeginStopDeferral();assert(m.Stop(1));assert(m.m_sessions.size()==1&&m.destroyed.empty());
 m.EndStopDeferral();assert(m.destroyed.empty());m.EndStopDeferral();assert(m.m_sessions.empty()&&m.destroyed.size()==1&&m.destroyed[0].second);
 m.m_sessions[1]={11};m.BeginStopDeferral();m.Stop(1,false);m.Stop(1,true);m.EndStopDeferral();assert(!m.destroyed.back().second);
 m.m_sessions[1]={12};m.BeginStopDeferral();m.Stop(1);m.m_sessions[1]={13};m.EndStopDeferral();assert(m.m_sessions[1].requestToken==13&&m.destroyed.size()==2);
 m.m_pendingSessions[2]={14};m.BeginStopDeferral();m.Stop(2);m.EndStopDeferral();assert(m.m_pendingSessions.empty()&&!m.destroyed.back().second);
 assert(!m.Stop(99));m.Stop(1);assert(m.destroyed.back().first==13);
 puts("PASS headless callback lifetime, nested deferral, deletion precedence, stale replacement token, pending and direct stops");
}
''')
