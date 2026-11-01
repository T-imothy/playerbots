"""Execute the production pull-start method against failed/already-ready form cases."""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[1]
source = (root/'playerbot/strategy/actions/PullActions.cpp').read_text()
start = source.index('bool PullStartAction::Execute(')
end = source.index('\nPullAction::PullAction(', start)
method = source[start:end]
stub = r'''
#include <cassert>
#include <string>
constexpr int CLASS_DRUID=11,FORM_BEAR=5,FORM_DIREBEAR=8,REACT_PASSIVE=0;
struct Event {};
struct Unit {};
struct UnitAI { int react=2; int GetReactState(){return react;} void SetReactState(int v){react=v;} };
struct Creature { UnitAI controller; UnitAI* AI(){return &controller;} }; using Pet=Creature;
struct Player { int klass=11,form=0; Pet* pet=nullptr; int getClass(){return klass;} int GetShapeshiftForm(){return form;} Pet* GetPet(){return pet;} };
struct PlayerbotAI { bool cast=false,learnedDire=true; int calls=0; std::string last;
 bool HasSpell(const char*){return learnedDire;}
 bool DoSpecificAction(const std::string& n,Event&,bool){++calls;last=n;return cast;}
};
struct PullStrategy { static PullStrategy* active; Unit* target=nullptr; std::string pre="dire bear form";
 bool pending=true,saved=false,encounter=false; int startCount=0,deadline=115;
 static PullStrategy* Get(PlayerbotAI*){return active;}
 bool IsEncounterPreparationAllowed(){return encounter;}
 Unit* GetTarget(){return target;} std::string GetPreActionName(){return pre;}
 bool HasSavedPetReactState(){return saved;} void SetPetReactState(int){saved=true;}
 void OnPullStarted(){pending=false;++startCount;}
}; PullStrategy* PullStrategy::active=nullptr;
bool NaxxramasGothikPullReady(PlayerbotAI*){return true;}
bool NaxxramasThaddiusPullReady(PlayerbotAI*){return true;}
bool RazuviousCrystalPullReady(PlayerbotAI*){return true;}
bool IsRazuviousCrystalPull(PlayerbotAI*,Unit*){return false;}
struct PullStartAction { PlayerbotAI* ai; Player* bot; int duration=0;
 void SetDuration(int v){duration=v;} bool Execute(Event&);
};
'''
tests = r'''
int main(){
 Player p; Pet pet;p.pet=&pet; PlayerbotAI ai; Unit target; Event e;
 PullStrategy strategy; strategy.target=&target;PullStrategy::active=&strategy;
 PullStartAction action{&ai,&p};
 // Failed GCD/resource/form cast keeps preparation pending without pet mutation.
 assert(!action.Execute(e));assert(strategy.pending&&strategy.startCount==0&&!strategy.saved);
 assert(pet.controller.react==2&&strategy.deadline==115&&ai.last=="dire bear form");
 ai.cast=true;assert(action.Execute(e));assert(!strategy.pending&&strategy.startCount==1);
 assert(strategy.deadline==115&&strategy.saved&&pet.controller.react==0);
 // Already-correct form must not recast/toggle it or fail as useless.
 for(int form:{FORM_BEAR,FORM_DIREBEAR}){
  strategy.pending=true;p.form=form;ai.cast=false;int calls=ai.calls;
  assert(action.Execute(e));assert(ai.calls==calls&&!strategy.pending);
 }
 p.form=0;ai.learnedDire=false;ai.cast=true;strategy.pending=true;
 assert(action.Execute(e));assert(ai.last=="bear form");
 // Optional preparation retains existing behavior; no-prep pull still succeeds.
 p.klass=3;strategy.pre="misdirection on party tank";ai.cast=false;strategy.pending=true;
 assert(!action.Execute(e));assert(!strategy.pending);
 strategy.pre="";strategy.pending=true;assert(action.Execute(e));assert(!strategy.pending);
 strategy.target=nullptr;strategy.pending=true;assert(!action.Execute(e));assert(strategy.pending);
 PullStrategy::active=nullptr;assert(!action.Execute(e));
}
'''
with tempfile.TemporaryDirectory(prefix='druid-pull-preparation-') as tmp:
    p=Path(tmp);(p/'test.cpp').write_text(stub+method+tests)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS: failed bear-form preparation, retry, existing form, low-level fallback, deadline/pet preservation, optional/no preparation, missing target/strategy')
