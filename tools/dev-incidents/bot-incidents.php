<?php
declare(strict_types=1);
header('Cache-Control: no-store');
if (!in_array($_SERVER['REMOTE_ADDR'] ?? '', ['127.0.0.1', '::1'], true)) {
    http_response_code(403); exit('DEV only');
}
if (isset($_GET['data'])) {
    header('Content-Type: application/json; charset=utf-8');
    $realm = $_GET['realm'] ?? 'classic';
    if (!in_array($realm, ['classic','tbc','wotlk'], true)) { http_response_code(400); exit('{}'); }
    // Fixed local DEV paths; never accept an arbitrary filename or share.
    $root = 'C:/Users/root/Desktop/WorkFolder/Arch4/candidate/'.$realm.'/logs/';
    $events = []; $dropped = 0; $modified = 0;
    foreach (['PlayerbotIncidents.jsonl.1','PlayerbotIncidents.jsonl'] as $name) {
        $path = $root.$name;
        if (!is_file($path)) continue;
        $modified = max($modified, (int)filemtime($path));
        $f = fopen($path,'rb'); if (!$f) continue;
        $offset = max(0, (int)filesize($path)-2*1024*1024);
        fseek($f,$offset); if ($offset) fgets($f);
        while (($line = fgets($f,4096)) !== false) {
            $row = json_decode($line,true);
            if (!is_array($row)) continue;
            if (isset($row['dropped_records'])) { $dropped += (int)$row['dropped_records']; continue; }
            if (!isset($row['bot'],$row['kind'],$row['run'],$row['started_ms'])) continue;
            $key = $row['run'].':'.$row['bot'].':'.$row['kind'].':'.$row['started_ms'];
            $events[$key] = $row;
            if (count($events)>4000) array_shift($events);
        }
        fclose($f);
    }
    $events = array_values($events);
    usort($events, function($a,$b) { return ($b['time'] ?? 0) <=> ($a['time'] ?? 0); });
    echo json_encode(['realm'=>$realm,'modified'=>$modified,'dropped'=>$dropped,'episodes'=>array_slice($events,0,1000)],JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}
?>
<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DEV bot incidents</title>
<style>body{font:16px system-ui;background:#10171d;color:#e5edf5;margin:32px}a{color:#92caff}select,input{font:inherit;padding:8px;background:#1e2c38;color:inherit;border:1px solid #607181}table{border-collapse:collapse;width:100%;margin-top:20px}th,td{text-align:left;padding:9px;border-bottom:1px solid #35414c}small,p{color:#adbccb}.controls{display:flex;gap:16px;align-items:center}td{font-size:14px}#status{min-height:24px}</style>
<h1>DEV bot incidents</h1><p>Recent problem episodes by bot. “Resolved” means an observed recovery. “Observation ended” means tracking stopped or expired; it does not prove a fix. An open record is the last observed state, not a live health check.</p>
<div class="controls"><label>Realm <select id="realm"><option>classic</option><option>tbc</option><option>wotlk</option></select></label><label>Bot GUID <input id="bot" inputmode="numeric" placeholder="All bots"></label><a href="dev-core-diagnostics.html">Core diagnostics</a></div>
<p id="status">Loading…</p><table><thead><tr><th>Last event</th><th>Bot</th><th>Problem</th><th>State</th><th>Observed duration</th><th>Map / instance</th><th>Action / target</th></tr></thead><tbody id="rows"></tbody></table>
<script>
const realm=document.querySelector('#realm'),filter=document.querySelector('#bot'),rows=document.querySelector('#rows'),status=document.querySelector('#status');let snapshot=null,busy=false;
function render(){rows.replaceChildren();if(!snapshot)return;const list=snapshot.episodes.filter(x=>!filter.value||String(x.bot)===filter.value.trim());for(const e of list){const tr=document.createElement('tr');for(const value of [new Date(e.time*1000).toLocaleString(),e.bot,e.kind.replaceAll('_',' '),e.state.replaceAll('_',' '),(e.duration_ms/1000).toFixed(1)+'s',e.map+' / '+e.instance,e.action||e.target||'—']){const td=document.createElement('td');td.textContent=String(value);tr.append(td)}rows.append(tr)}status.textContent=list.length+' episodes in the bounded log window. Dropped records in this window: '+snapshot.dropped+'. '+(snapshot.modified?'Last log write '+new Date(snapshot.modified*1000).toLocaleString(): 'No incident log yet; the realm may be stopped, diagnostics disabled, or no episode has met its threshold.');}
async function refresh(){if(busy)return;busy=true;const selected=realm.value;try{const response=await fetch('bot-incidents.php?data=1&realm='+encodeURIComponent(selected),{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);const value=await response.json();if(selected===realm.value){snapshot=value;render()}}catch(e){status.textContent='Unable to read DEV incidents: '+e.message}finally{busy=false}}
realm.onchange=()=>{snapshot=null;rows.replaceChildren();refresh()};filter.oninput=render;refresh();setInterval(refresh,10000);
</script></html>
