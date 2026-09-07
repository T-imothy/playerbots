"""Reproduce item-cheat bypass and execute the native-inventory admission fix."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/UseItemAction.cpp').read_text()
method=block(source,'bool RequiresItemToUse(')
old=method.replace('{ 6948, 40582, 19183, 24494, 31088, 32408 }','{ 6948, 40582 }')
assert old!=method
code=r'''
#include <unordered_set>
#include <iostream>
using uint32=unsigned;enum{INVTYPE_NON_EQUIP=0,ITEM_CLASS_QUEST=12,ITEM_CLASS_GEM=3};enum class BotCheatMask{item};
struct ItemPrototype{unsigned ItemId=0,InventoryType=0,StartQuest=0,Class=0;};struct Player{};
struct PlayerbotAI{bool cheat=true;bool HasCheat(BotCheatMask){return cheat;}};
__METHOD__
int main(){PlayerbotAI ai;Player bot;ItemPrototype item;
 for(bool cheat:{false,true}){ai.cheat=cheat;
 for(unsigned id:{19183u,24494u,31088u,32408u}){item.ItemId=id;item.Class=id==31088?15:0;
 if(!RequiresItemToUse(&item,&ai,&bot))return 1;}}
 ai.cheat=true;item.Class=0;item.ItemId=13444;
 if(RequiresItemToUse(&item,&ai,&bot))return 2; // Ordinary consumable cheat is preserved.
 item.ItemId=6948;if(!RequiresItemToUse(&item,&ai,&bot))return 3;
 item.ItemId=123;item.InventoryType=1;if(!RequiresItemToUse(&item,&ai,&bot))return 4;
 item.InventoryType=0;item.Class=ITEM_CLASS_QUEST;if(!RequiresItemToUse(&item,&ai,&bot))return 5;
 std::cout<<"PASS: real encounter items/charges required; normal consumable policy preserved\n";
}
'''
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='encounter-item-ownership-') as folder:
        tmp=Path(folder)
        for label,body,expected in (('before',old,1),('after',method,0)):
            (tmp/'test.cpp').write_text(code.replace('__METHOD__',body))
            subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
            result=subprocess.run([str(tmp/'test.exe')],cwd=tmp)
            assert result.returncode==expected,(era,label,result.returncode)
        print('PASS:',era,'old bypass reproduced and repaired')
use=block(source,'bool UseAction::UseItemInternal(')
assert use.index('RequiresItemToUse(proto, ai, bot)')<use.index('spell->SetCastItem(itemUsed)')<use.index('spell->ForceSpellStart(&targets)')
