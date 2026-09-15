# Local ManTech diagnostics integration

Copy `mantech-bot-incidents.php` beside your existing local diagnostics adapter. Add:

```php
require_once __DIR__ . '/mantech-bot-incidents.php';
// $root is the existing realm logs directory; $stamp is the latest diagnostic timestamp.
$result['incidents'] = pb_incidents(pb_tail($root . 'PlayerbotIncidents.log', 2097152),
    $result['session']['timestamp'] ?? null, $stamp,
    !empty($result['latest']['state']['incidents_enabled']), $result['stale']);
```

Load `mantech-bot-incidents.js` after the existing diagnostics functions, or append it to that script. Call `pbRenderIncidents(d)` after fetching diagnostics in `loadBotDiagnostics()`. It uses the existing `esc`, `pbTable`, `pbZoneNames` and `#botLiveContent` and creates its own panel. Retain the site's existing realm selection, authentication and read-only routing. No game command or database write is exposed.

These are portable integration assets; they contain no runtime credentials or fixed server addresses. Installing them on a public site is a separate deployment decision.
