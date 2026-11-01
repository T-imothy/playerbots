"""Use the selected core's actual BG enums, or explicit standalone fixtures.

Native builds pass --core <source> --era ONE/TWO. Standalone runs cover all
three eras with the corresponding event numbering and Wrath node names.
"""
from pathlib import Path
import re, sys

def variants(*maps):
    av_old = ['FIRSTAID_STATION','STORMPIKE_GRAVE','STONEHEART_GRAVE','SNOWFALL_GRAVE',
        'ICEBLOOD_GRAVE','FROSTWOLF_GRAVE','FROSTWOLF_HUT','DUNBALDAR_SOUTH','DUNBALDAR_NORTH',
        'ICEWING_BUNKER','STONEHEART_BUNKER','ICEBLOOD_TOWER','TOWER_POINT','FROSTWOLF_ETOWER','FROSTWOLF_WTOWER']
    av_wrath = ['GY_DUN_BALDAR','GY_STORMPIKE','GY_STONEHEARTH','GY_SNOWFALL','GY_ICEBLOOD',
        'GY_FROSTWOLF','GY_FROSTWOLF_KEEP','DUNBALDAR_SOUTH','DUNBALDAR_NORTH','ICEWING_BUNKER',
        'STONEHEART_BUNKER','ICEBLOOD_TOWER','TOWER_POINT','FROSTWOLF_EAST','FROSTWOLF_WEST']
    eras = [sys.argv[sys.argv.index('--era')+1]] if '--era' in sys.argv else ['ZERO','ONE','TWO']
    core = Path(sys.argv[sys.argv.index('--core')+1]) if '--core' in sys.argv else None
    for era in eras:
        values = {}
        if 'AV' in maps:
            prefix='BG_AV_NODE_' if era=='TWO' else 'BG_AV_NODES_'
            values.update({prefix+n:i for i,n in enumerate(av_wrath if era=='TWO' else av_old)})
            values.update(BG_AV_MAX_NODES=15,BG_AV_BOSS_A=61,BG_AV_BOSS_H=62)
            values.update({'BG_AV_NODE_STATUS_'+n:i for i,n in enumerate([
                'ALLY_CONTESTED','ALLY_OCCUPIED','HORDE_CONTESTED','HORDE_OCCUPIED','NEUTRAL_CONTESTED','NEUTRAL_OCCUPIED'])})
        if 'AB' in maps:
            values['BG_AB_MAX_NODES']=5
            values.update({'BG_AB_NODE_STATUS_'+n:i for i,n in enumerate([
                'NEUTRAL','ALLY_CONTESTED','HORDE_CONTESTED','ALLY_OCCUPIED','HORDE_OCCUPIED'])})
        if core:
            actual={}
            for bg in maps:
                header=(core/f'src/game/BattleGround/BattleGround{bg}.h').read_text()
                actual.update({n:int(v) for n,v in re.findall(r'\b(BG_\w+)\s*=\s*(\d+)\b',header)})
            for name,value in values.items():
                assert name in actual,(core,name)
                assert actual[name]==value,(core,name,value,actual[name])
            values={name:actual[name] for name in values}
        yield era,'enum {'+','.join(f'{n}={v}' for n,v in values.items())+'};'
