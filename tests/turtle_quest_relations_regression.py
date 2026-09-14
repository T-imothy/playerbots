from pathlib import Path
from turtle_cpp_fixture import run
r=Path(__file__).resolve().parents[1]/'playerbot'
s=(r/'strategy/values/QuestValues.cpp').read_text(encoding='utf-8')
s=s[s.index('EntryQuestRelationMap EntryQuestRelationMapValue::Calculate()'):s.index('\t//Quest objectives')]+"return rMap; }"
run(r'''#include <map>
#include <unordered_map>
#include <cstdint>
#include <cassert>
#include <cstdio>
using uint32=uint32_t;using uint8=uint8_t;using int32=int32_t;
using QuestRelationsMap=std::multimap<uint32,uint32>;
using QuestRelationsMapBounds=std::pair<QuestRelationsMap::const_iterator,QuestRelationsMap::const_iterator>;
using EntryQuestRelationMap=std::unordered_map<int32,std::unordered_map<uint32,uint32>>;
enum class TravelDestinationPurpose:uint8{QuestGiver=1,QuestTaker=64};
struct ObjectMgr{std::map<uint32,int>creatures{{5,0},{6,0}},objects{{5,0},{7,0}};
 QuestRelationsMap cg{{5,10},{5,11}},ct{{5,10},{6,12}},gg{{5,20},{7,21}},gt{{5,20}};
 auto const&GetCreatureInfoMap(){return creatures;}auto const&GetGameObjectInfoMap(){return objects;}
 auto GetCreatureQuestRelationsMapBounds(uint32 e)const{return cg.equal_range(e);}auto GetCreatureQuestInvolvedRelationsMapBounds(uint32 e)const{return ct.equal_range(e);}
 auto GetGOQuestRelationsMapBounds(uint32 e)const{return gg.equal_range(e);}auto GetGOQuestInvolvedRelationsMapBounds(uint32 e)const{return gt.equal_range(e);}
}sObjectMgr;
struct EntryQuestRelationMapValue{EntryQuestRelationMap Calculate();};
'''+s+r'''
int main(){EntryQuestRelationMapValue v;auto m=v.Calculate();assert(m.size()==4);assert(m[5][10]==65&&m[5][11]==1&&m[6][12]==64);assert(m[-5][20]==65&&m[-7][21]==1);assert(!m[5].count(20)&&!m[-5].count(10));puts("PASS native creature/gameobject quest giver+taker union and separate signed entry namespaces");}
''')
