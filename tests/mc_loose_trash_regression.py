"""Replay real MC tank allocation for four tanks/two mobs and native victim changes."""
from pathlib import Path
import ast,subprocess,tempfile
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
tree=ast.parse((R/'tests/molten_core_support_regression.py').read_text())
node=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
while isinstance(node,ast.Call):node=node.func.value
code=ast.literal_eval(node);code=code[:code.index('__METHODS__')]+'__METHODS__'
names=next(n.value.args[0].generators[0].iter for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='methods' for t in n.targets))
source=(R/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
code=code.replace('__METHODS__','\n'.join(block(source,n) for n in ast.literal_eval(names)))
code+=r'''
int main(){
 Player tanks[4],ranged;PlayerbotAI*brain[4];Group group;ranged.guid=50;ranged.ranged=true;ranged.x=40;group.Add(&ranged);
 for(unsigned i=0;i<4;++i){tanks[i].guid=10+i;tanks[i].tank=true;group.Add(&tanks[i]);brain[i]=new PlayerbotAI(&tanks[i]);}
 Unit first,loose;first.entry=11658;first.guid=100;first.victim=&tanks[0];loose.entry=11659;loose.guid=101;loose.x=60;loose.victim=&ranged;
 units={&first,&loose,&ranged};for(auto&t:tanks)units.push_back(&t);
 // Empty per-bot target caches still see actual native raid attackers.
 tanks[0].attackers={&first};ranged.attackers={&loose};
 for(auto*b:brain)b->context.attack.value=100; // Attack/skull focus does not disable tank ownership.
 assert(MoltenCoreAssignedTankTarget(brain[0])==&first);
 assert(MoltenCoreAssignedTankTarget(brain[1])==&loose);
 assert(!MoltenCoreAssignedTankTarget(brain[2])&&!MoltenCoreAssignedTankTarget(brain[3]));
 // The spare tank rescues immediately when the nominal owner is knocked down.
 tanks[1].mobile=false;assert(MoltenCoreAssignedTankTarget(brain[2])==&loose);assert(!MoltenCoreAssignedTankTarget(brain[1]));
 tanks[2].mobile=false;assert(MoltenCoreAssignedTankTarget(brain[3])==&loose);
 loose.victim=&tanks[3];ranged.attackers.clear();tanks[3].attackers={&loose};
 assert(MoltenCoreAssignedTankTarget(brain[3])==&loose);assert(!MoltenCoreAssignedTankTarget(brain[1]));
 tanks[1].mobile=tanks[2].mobile=true;assert(!MoltenCoreAssignedTankTarget(brain[1])&&!MoltenCoreAssignedTankTarget(brain[2])); // no healthy tank stealing
 EncounterPosition p;assert(PlanMoltenCoreGiants(brain[3],p)&&p.spell==18945&&p.source==tanks[0].guid);
 brain[3]->path=false;assert(!PlanMoltenCoreGiants(brain[3],p));brain[3]->path=true;
 loose.x=4;assert(!PlanMoltenCoreGiants(brain[3],p)); // already cleavable, don't keep moving
 loose.x=60;loose.victim=&ranged;ranged.attackers={&loose};tanks[3].attackers.clear();
 loose.cc=true;assert(!MoltenCoreAssignedTankTarget(brain[1]));loose.cc=false;
 loose.combat=false;assert(!MoltenCoreAssignedTankTarget(brain[1]));loose.combat=true;
 Player foreign;loose.victim=&foreign;assert(!MoltenCoreAssignedTankTarget(brain[1]));loose.victim=&ranged;
 loose.instance=2;assert(!MoltenCoreAssignedTankTarget(brain[1]));loose.instance=1;
 loose.alive=false;first.alive=false;for(auto*b:brain)assert(!MoltenCoreAssignedTankTarget(b));
 // Geddon's preferred pads are range-limited, not forced out-of-range casts.
 Unit geddon;geddon.entry=12056;geddon.guid=200;geddon.x=644;geddon.y=-761;geddon.z=-208.74f;geddon.victim=&tanks[0];
 tanks[0].x=644;tanks[0].y=-761;tanks[0].z=-208.74f;ranged.x=685;ranged.y=-731;ranged.z=-209.29f;units.push_back(&geddon);
 PlayerbotAI casterAI(&ranged);casterAI.spellRange=30;
 assert(PlanGeddonFormation(&casterAI,&geddon,p));assert(std::hypot(p.destination.x-geddon.x,p.destination.y-geddon.y)<=31.1f);
 tanks[0].x=650;brain[0]->context.geddon.value={};assert(PlanGeddonFormation(brain[0],&geddon,p));assert(std::fabs(p.destination.x-643.981873f)<0.01f);
 for(auto*b:brain)delete b;
 std::cout<<"PASS real four-tank/two-mob pickup, direct Attack, native knockdown backup, 60-yard victim, ownership/CC/instance guards and gathering\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-loose-') as tmp:
  p=Path(tmp);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
