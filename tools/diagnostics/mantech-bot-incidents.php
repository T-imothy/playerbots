<?php
// Read-only, bounded snapshots. Raw 64-bit GUIDs stay strings for JSON/JavaScript.
function pb_incident_fields(string $text): array
{
    preg_match_all('/([a-z_]+)=(?:"([^"\r\n]*)"|([^\s]+))/', $text, $matches, PREG_SET_ORDER);
    $out = array();
    foreach ($matches as $m) $out[$m[1]] = isset($m[3]) && $m[3] !== '' ? $m[3] : $m[2];
    return $out;
}

function pb_incidents(string $text, ?string $session, ?string $latest, bool $enabled, bool $serverStale): array
{
    $result = array('available' => false, 'enabled' => $enabled, 'stale' => true, 'timestamp' => null,
        'active' => 0, 'overflow' => 0, 'capacity' => 1024, 'history' => 200, 'rows' => array());
    $batch = null;
    foreach (explode("\n", $text) as $line) {
        if (!preg_match('/^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) PB_(INCIDENTS_BEGIN|INCIDENT|INCIDENTS_END) (.*)$/', $line, $m)) continue;
        list(, $stamp, $kind, $payload) = $m;
        if ($session !== null && $stamp < $session) continue;
        $f = pb_incident_fields($payload);
        if ($kind === 'INCIDENTS_BEGIN') {
            $batch = null;
            foreach (array('seq', 'active', 'rows', 'overflow', 'capacity', 'history') as $key) {
                if (!isset($f[$key]) || !ctype_digit($f[$key])) continue 2;
            }
            if ((int)$f['rows'] > 1224 || (int)$f['active'] > 1024 || (int)$f['active'] > (int)$f['rows']) continue;
            $batch = array('timestamp' => $stamp, 'seq' => $f['seq'], 'expected' => (int)$f['rows'],
                'active' => (int)$f['active'], 'overflow' => (int)$f['overflow'], 'rows' => array(), 'ids' => array());
        } elseif ($batch !== null && $stamp === $batch['timestamp'] && $kind === 'INCIDENT') {
            foreach (array('id', 'bot', 'target', 'duration_ms', 'map', 'zone') as $key) {
                if (!isset($f[$key]) || !ctype_digit($f[$key]) || strlen($f[$key]) > 20) { $batch = null; continue 2; }
            }
            if (!in_array($f['type'] ?? '', array('STUCK', 'DEAD_LONG', 'ACTION_LOOP', 'UNREACHABLE_TARGET'), true) ||
                !in_array($f['state'] ?? '', array('active', 'resolved'), true) || isset($batch['ids'][$f['id']]) || count($batch['rows']) >= 1224) {
                $batch = null; continue;
            }
            $batch['ids'][$f['id']] = true;
            $row = array_intersect_key($f, array_flip(array('id', 'bot', 'type', 'state', 'target', 'duration_ms', 'map', 'zone')));
            $row['action'] = substr($f['action'] ?? '', 0, 96); $row['reason'] = substr($f['reason'] ?? '', 0, 96);
            $batch['rows'][] = $row;
        } elseif ($batch !== null && $stamp === $batch['timestamp'] && $kind === 'INCIDENTS_END') {
            $count = count($batch['rows']);
            $active = count(array_filter($batch['rows'], function ($r) { return $r['state'] === 'active'; }));
            if (($f['seq'] ?? '') === $batch['seq'] && isset($f['rows']) && ctype_digit($f['rows']) &&
                (int)$f['rows'] === $count && $batch['expected'] === $count && $active === $batch['active']) {
                $result = array_merge($result, array_intersect_key($batch, $result));
                $result['available'] = true;
            }
            $batch = null;
        }
    }
    // Both clocks come from the same server. Never label old/offline/disabled observations current.
    $delta = $latest && $result['timestamp'] ? abs(strtotime($latest . ' UTC') - strtotime($result['timestamp'] . ' UTC')) : null;
    $result['stale'] = !$enabled || $serverStale || !$result['available'] || $delta === null || $delta > 90;
    return $result;
}
