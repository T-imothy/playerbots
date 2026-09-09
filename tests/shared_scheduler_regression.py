"""Source checks by default; --compile additionally exercises actual Queue methods.

The optional native harness uses controlled interfaces, not a running realm.
Run --compile from an MSVC developer shell after the build hold is lifted.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

def block(text, marker):
    start=text.index(marker); opening=text.index('{',start); depth=0
    for i in range(opening,len(text)):
        depth += (text[i]=='{')-(text[i]=='}')
        if depth==0:return text[start:i+1]
    raise ValueError(marker)

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--compile',action='store_true')
args=parser.parse_args()
root=args.root/'playerbot/strategy'
def source(name):return (root/name).read_text(encoding='utf-8')

queue=source('Queue.cpp'); header=source('Queue.h')
assert 'std::greater<float>' in header
assert 'actions.begin()' in block(queue,'ActionBasket* Queue::Peek')
assert 'selectionIterator = actions.begin()' in block(queue,'ActionNode* Queue::Pop')
assert 'std::prev(actions.end())' not in queue
engine=source('Engine.cpp'); reaction=source('ReactionEngine.cpp')
tick=block(engine,'bool Engine::DoNextAction')
assert tick.index('queue.RemoveExpired()') < tick.index('ProcessTriggers(minimal)')
veto=tick.index('// A strategy veto')
assert veto < tick.index('ActionBasket* peekAction') < tick.index('if (!skipPrerequisites)')
assert 'delete actionNode;' in block(tick[veto:],'if (!relevance)')
assert 'continue;' in block(tick[veto:],'if (!relevance)')
assert 'PushAgain(actionNode, relevance, event, skipPrerequisites)' in tick
assert 'skipPrerequisites = true' in source('Engine.h')
assert 'MultiplyAndPush(nextAction, relevance, skipPrerequisites' in block(engine,'void Engine::PushAgain')
direct=block(engine,'ActionResult Engine::ExecuteAction')
assert 'if (executionResult)\n                        MultiplyAndPush(action->getContinuers()' in direct
find=block(reaction,'bool ReactionEngine::FindReaction')
assert find.index('queue.RemoveExpired()') < find.index('ProcessTriggers(false)')
veto=find.index('// A blocked reaction')
assert veto < find.index('// Process prerequisites')
assert 'continue;' in block(find[veto:],'if (reactionRelevance <= 0.0f)')
reach=block(source('actions/ReachTargetActions.h'),'class ReachTargetAction')
wait=block(reach,'if (!isFriend && MoveStyleValue::WaitForEnemy(ai)')
assert 'SetDuration(sPlayerbotAIConfig.reactDelay)' in wait
assert wait.index('SetDuration') < wait.index('return true;')
assert 'IsExplicitPlayerCommand(action, event)' in block(engine,'bool Engine::IsFailureBackedOff')
print('PASS: scheduler source contracts (shared across Classic/TBC/Wrath).')

if not args.compile:
    print('NOT RUN: C++ harness, complete core builds and gameplay tests.')
    raise SystemExit(0)

common=r'''
#include <cassert>
#include <map>
#include <functional>
#include <unordered_map>
#include <string>
namespace ai {
struct Event {int id=0;};
struct ActionNode {
    static int live;std::string name;
    ActionNode(std::string n):name(n){++live;}
    ~ActionNode(){--live;}
    std::string getName(){return name;}
};int ActionNode::live=0;
struct ActionBasket {
    ActionNode* node;float relevance;Event event;bool expired=false;
    ActionBasket(ActionNode* n,float r,bool,Event e):node(n),relevance(r),event(e){}
    ActionNode* getAction(){return node;}float getRelevance(){return relevance;}
    void setRelevance(float r){relevance=r;}Event getEvent(){return event;}
    void setEvent(Event e){event=e;}bool isExpired(int){return expired;}
};
}
struct Config {int expireActionTime=5000;} sPlayerbotAIConfig;
struct Log {void outDebug(const char*,const char*){}} sLog;
'''
queue_header='\n'.join(line for line in header.splitlines() if not line.startswith('#include "'))
queue_body='\n'.join(line for line in queue.splitlines() if not line.startswith('#include'))
main=r'''
int main(){
    Queue q;
    auto push=[&](const char* n,float r,int event=0){q.Push(new ActionBasket(new ActionNode(n),r,false,Event{event}));};
    auto take=[&](){assert(q.Peek());std::string n=q.Peek()->getAction()->getName();auto a=q.Pop();assert(a->getName()==n);delete a;return n;};
    // Repeated eligible work cannot starve an older action of equal priority.
    push("heal A",90);push("heal B",90);assert(take()=="heal A");
    push("heal A",90);assert(take()=="heal B");assert(take()=="heal A");
    // Prerequisite/parent offsets and default negative priorities retain order.
    push("default",-190);push("parent",10.01f);push("prerequisite",10.02f);
    push("emergency",90);assert(take()=="emergency");assert(take()=="prerequisite");
    assert(take()=="parent");assert(take()=="default");
    // Promotion updates event, preserves deduplication and index integrity.
    push("a",10,1);push("b",20);push("a",30,2);assert(q.Size()==2);
    assert(q.Peek()->getEvent().id==2);assert(take()=="a");assert(take()=="b");
    // Explicit basket pop, equal-priority dedup, expiration and no node leaks.
    push("a",10);auto selected=q.Peek();push("b",20);delete q.Pop(selected);
    assert(q.Size()==1&&take()=="b");
    push("old",30);q.Peek()->expired=true;push("live",20);q.RemoveExpired();
    assert(q.Size()==1&&take()=="live");
    push("a",20);push("b",20);push("a",20);assert(q.Size()==2);
    assert(take()=="a"&&take()=="b");assert(!q.Peek()&&!q.Pop());
    assert(ActionNode::live==0);
}
'''
with tempfile.TemporaryDirectory(prefix='scheduler-regression-') as td:
    p=Path(td);(p/'test.cpp').write_text(common+queue_header+queue_body+main,encoding='utf-8')
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True,timeout=20)
print('PASS: actual Queue methods against controlled interfaces; no realm test.')
