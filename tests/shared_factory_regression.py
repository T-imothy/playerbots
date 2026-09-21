"""Test production factory sharing, private values, concurrency and allocation reduction."""
from pathlib import Path
import subprocess,tempfile
def block(text, marker):
 start=text.index(marker); opening=text.index('{',start);depth=0
 for i in range(opening,len(text)):
  depth+=(text[i]=='{')-(text[i]=='}')
  if depth==0:return text[start:i+1]
 raise ValueError(marker)

root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/NamedObjectContext.h').read_text()
factory=block(s,'template <class T>\n    class NamedObjectFactory')+';'
context=block(s,'template <class T>\n    class NamedObjectContext :')+';'
code=r'''
#include <atomic>
#include <cassert>
#include <cstdlib>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <new>
#include <set>
#include <string>
#include <string_view>
#include <thread>
#include <vector>
#include <iostream>
static std::atomic<size_t> bytes{0};
void* operator new(size_t n){if(void* p=std::malloc(n)){bytes+=n;return p;}throw std::bad_alloc();}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete(void* p,size_t) noexcept {std::free(p);}
struct PlayerbotAI{int id;};
struct Qualified{std::string q;virtual ~Qualified()=default;void Qualify(std::string x){q=std::move(x);}};
struct Object:Qualified{PlayerbotAI* owner;int state=0;Object(PlayerbotAI* a):owner(a){}void Update(){++state;}void Reset(){state=0;}};
__FACTORY__
__CONTEXT__
static std::atomic<unsigned> initializations{0};
class Shared:public NamedObjectContext<Object>{public:Shared(){ShareCreators<Shared>([this]{++initializations;for(int i=0;i<1500;++i)creators["registration "+std::to_string(i)]=[](PlayerbotAI* a){return new Object(a);};});}};
class Local:public NamedObjectContext<Object>{public:Local(){for(int i=0;i<1500;++i)creators["registration "+std::to_string(i)]=[](PlayerbotAI* a){return new Object(a);};}};
class Overlay:public Shared{public:Overlay(){creators["registration 1"]=[](PlayerbotAI* a){auto o=new Object(a);o->state=99;return o;};}};
class Other:public NamedObjectContext<Object>{public:Other(){ShareCreators<Other>([this]{creators["other"]=[](PlayerbotAI* a){return new Object(a);};});}};
class Retry:public NamedObjectContext<Object>{public:static int attempts;Retry(){ShareCreators<Retry>([this]{if(++attempts==1)throw 7;creators["retry"]=[](PlayerbotAI* a){return new Object(a);};});}};int Retry::attempts=0;
namespace paladin { class StrategyFactoryInternal:public NamedObjectContext<Object>{public:StrategyFactoryInternal():NamedObjectContext<Object>(false,true){ShareCreators<StrategyFactoryInternal>([this]{creators["class spell"]=[](PlayerbotAI* a){auto o=new Object(a);o->state=1;return o;};});}};}
namespace mage { class StrategyFactoryInternal:public NamedObjectContext<Object>{public:StrategyFactoryInternal():NamedObjectContext<Object>(false,true){ShareCreators<StrategyFactoryInternal>([this]{creators["class spell"]=[](PlayerbotAI* a){auto o=new Object(a);o->state=2;return o;};});}};}
int main(){
 std::vector<std::thread> threads;for(int i=0;i<16;++i)threads.emplace_back([]{Shared x;std::set<std::string> keys;x.GetSupportedKeys(keys);assert(keys.size()==1500);});for(auto& t:threads)t.join();assert(initializations==1);
 PlayerbotAI a{1},b{2};Shared one,two;auto x=one.Create("registration 1::spell",&a);auto y=two.Create("registration 1::spell",&b);
 assert(x!=y&&x->owner==&a&&y->owner==&b&&x->q=="spell");x->state=25;assert(y->state==0);assert(one.Create("registration 1::spell",&a)==x);
 assert(!one.Create("unknown",&a)&&one.GetCreatedCount()==1);one.Reset();assert(x->state==0);one.Erase("registration 1::spell");assert(one.GetCreatedCount()==0&&two.GetCreatedCount()==1);
 paladin::StrategyFactoryInternal p1,p2;mage::StrategyFactoryInternal m1;
 auto pspell=p1.Create("class spell",&a);auto pother=p2.Create("class spell",&b);auto mspell=m1.Create("class spell",&a);
 assert(pspell->state==1&&pother->state==1&&mspell->state==2&&pspell!=pother&&pother->owner==&b);
 pspell->state=99;assert(pother->state==1&&mspell->state==2);
 Overlay overlay;auto special=overlay.Create("registration 1",&a);assert(special->state==99);std::set<std::string> keys;overlay.GetSupportedKeys(keys);assert(keys.size()==1500);
 Other other;assert(!other.Create("registration 1",&a)&&other.Create("other",&a));
 try{Retry first;assert(false);}catch(int){} Retry retry;assert(retry.Create("retry",&a)&&Retry::attempts==2);
 size_t start=bytes;for(int i=0;i<200;++i){Local local;}size_t duplicated=bytes-start;
 start=bytes;for(int i=0;i<200;++i){Shared shared;}size_t shared=bytes-start;
 assert(shared*100<duplicated);assert(initializations==1);
 std::cout<<"PASS: concurrent one-time publication, private actor state, qualifiers/misses/reset, overrides, separate types and exception retry\n";
 std::cout<<"Registry fixture allocated bytes (200 contexts x 1500 entries): duplicated="<<duplicated<<" shared="<<shared<<"\n";
}
'''.replace('__FACTORY__',factory).replace('__CONTEXT__',context)
with tempfile.TemporaryDirectory(prefix='cmangos-shared-factory-') as d:
 p=Path(d);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/O2','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
