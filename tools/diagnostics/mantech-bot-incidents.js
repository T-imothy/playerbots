function pbRenderIncidents(d) {
 let panel = document.getElementById('botIncidentPanel');
 if (!panel) {
  panel = document.createElement('section'); panel.id = 'botIncidentPanel'; panel.className = 'diagnosticPanel';
  document.getElementById('botLiveContent').appendChild(panel);
 }
 const data = d.incidents || {}, rows = data.rows || [];
 const active = rows.filter(r => r.state === 'active'), resolved = rows.filter(r => r.state === 'resolved').reverse();
 const note = !data.enabled ? 'Incident collection is disabled. Enable Diagnostics.Mode = 2 and Diagnostics.Incidents = 1.' :
  !data.available ? 'Waiting for the first complete incident snapshot.' :
  `${data.stale ? 'Historical observations' : 'Current observations'} · ${data.timestamp} · ${data.active} active · ${resolved.length} retained resolutions`;
 const columns = [['Bot GUID','bot'],['Type','type'],['Duration','duration'],['Map / zone','location'],['Target GUID','target'],['Action','action'],['Resolution','reason']];
 const display = values => values.map(r => ({...r,duration: `${Math.round(Number(r.duration_ms)/1000)}s`,location: `${r.map} / ${d.zoneNames?.[r.zone] || pbZoneNames[r.zone] || r.zone}`}));
 panel.innerHTML = `<h3>Persistent bot incidents</h3><p class="resourceNote">${esc(note)}</p>` +
  (data.overflow ? `<p class="botTelemetryNotice warning">${esc(data.overflow)} observations could not enter the bounded incident store. Coverage is incomplete.</p>` : '') +
  '<p class="resourceNote">Stuck: 60s of movement intent without progress. Dead: 120s. Action loop: sustained repeated failures. Idle or resting alone is not an incident. Observation gaps resolve as telemetry_expired or observation_reset, not confirmed recovery.</p>' +
  '<h4>Active incidents</h4>' + pbTable(columns, display(active)) + '<h4>Recently resolved</h4>' + pbTable(columns, display(resolved));
 panel.classList.toggle('pbStale', !!data.stale);
}
