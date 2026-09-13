#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <memory>
#include <new>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>
#include <thread>
using int32=std::int32_t;using uint32=std::uint32_t;using uint8=std::uint8_t;
using int8=std::int8_t;
class PlayerbotAI;
#ifndef LOOKUP_HEADER
#define LOOKUP_HEADER "NamedObjectContext.h"
#endif
#include LOOKUP_HEADER
static bool tracking=false;
static std::uint64_t allocations=0;
void* operator new(std::size_t n) { if(tracking)++allocations; if(auto p=std::malloc(n?n:1))return p;throw std::bad_alloc(); }
void operator delete(void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
struct Value:ai::Qualified { static inline unsigned live=0;Value(){++live;}~Value(){--live;}void Update(){}void Reset(){} };
struct Context:ai::NamedObjectContext<Value> {
    Context(){creators["health"]=[](PlayerbotAI*){return new Value;};creators["party member to heal"]=[](PlayerbotAI*){return new Value;};}
};
static void require(bool ok){if(!ok)std::abort();}
int main(){
    Context context;
    std::vector<std::string> keys={"health","health::","health::1234567890123456789","party member to heal::target-guid-123456789"};
    std::vector<Value*> values;
    for(auto& key:keys)values.push_back(context.Create(key,nullptr));
    require(Value::live==keys.size());
    require(values[2]->getQualifier()=="1234567890123456789");
    for(unsigned i=0;i<1000;++i) require(!context.Create("unsupported::"+std::to_string(i),nullptr));
    require(context.GetCreatedCount()==keys.size());
    auto begin=std::chrono::steady_clock::now();
    tracking=true;
    for(unsigned i=0;i<400000;++i) require(context.Create(keys[i%keys.size()],nullptr)==values[i%keys.size()]);
    tracking=false;
    require(allocations==0);
    auto elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
    std::cout<<"cached lookups=400000 allocations="<<allocations<<" elapsed_ms="<<elapsed<<'\n';
    std::vector<Value*> concurrent(8);
    std::vector<std::thread> readers;
    for(unsigned i=0;i<8;++i) readers.emplace_back([&,i]{
        for(unsigned j=0;j<10000;++j) require(context.Create(keys[j%keys.size()],nullptr)==values[j%keys.size()]);
        concurrent[i]=context.Create("health::concurrent-long-qualifier",nullptr);
    });
    for(auto& reader:readers) reader.join();
    for(auto value:concurrent) require(value==concurrent[0]);
    require(Value::live==keys.size()+1);
    context.Erase("health::concurrent-long-qualifier");
    context.Erase(keys[0]);require(Value::live==keys.size()-1);
    context.Clear();require(Value::live==0 && context.GetCreatedCount()==0);
    require(context.Create(keys[3],nullptr)->getQualifier()=="target-guid-123456789");
    context.Clear();require(Value::live==0);
    std::cout<<"Qualification, cache identity, unsupported probes, erase, clear and recreation passed\n";
}
