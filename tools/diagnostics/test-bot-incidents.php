<?php
require $argv[1];
function check($value) { if (!$value) throw new RuntimeException('Incident parser assertion failed'); }
$stamp = '2026-09-15 12:00:00';
$begin = "$stamp PB_INCIDENTS_BEGIN seq=1 active=1 rows=1 overflow=0 capacity=1024 history=200\n";
$row = "$stamp PB_INCIDENT id=1 bot=10 type=STUCK state=active target=17379390966112399999 duration_ms=60000 map=0 zone=12 action=\"<script>\" reason=\"\"\n";
$end = "$stamp PB_INCIDENTS_END seq=1 rows=1\n";
$r = pb_incidents($begin.$row.$end, null, $stamp, true, false);
check($r['available'] && !$r['stale'] && $r['active'] === 1 && $r['rows'][0]['target'] === '17379390966112399999');
check(!pb_incidents($begin.$row, null, $stamp, true, false)['available']);
check(!pb_incidents($begin.$row.str_replace('seq=1','seq=2',$end), null, $stamp, true, false)['available']);
check(!pb_incidents($begin.$row.$row.$end, null, $stamp, true, false)['available']);
check(!pb_incidents($begin.$row.$end, '2026-09-15 13:00:00', $stamp, true, false)['available']);
check(pb_incidents($begin.$row.$end, null, '2026-09-15 12:02:00', true, false)['stale']);
check(pb_incidents($begin.$row.$end, null, $stamp, false, false)['stale']);
check(pb_incidents($begin.$row.$end, null, $stamp, true, true)['stale']);
check(!pb_incidents(str_replace('rows=1','rows=999999',$begin).$row.$end, null, $stamp, true, false)['available']);
check(pb_incidents($begin.$row.$end.$begin.$row, null, $stamp, true, false)['available']);
echo "PASS incident snapshot completeness, bounds, raw GUIDs, restart and stale-data handling\n";
