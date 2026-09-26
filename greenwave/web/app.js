'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="greenwave-token"]').content;
let state = null, selected = 'S1', selectedRouteStop = '', mapData = null, busy = false, queue = Promise.resolve();
let liveTrail=[],liveMatchedTrail=[],liveSampleKey='';
let requestId = 0, displayedId = 0, historyKey = '', listSession = '', runsKey = '';
let replayState=null,gpsReplayState=null,replayRuns=[],routesKey='';
const colours = {GREEN:'Zielone',YELLOW:'Żółte',RED:'Czerwone',UNKNOWN:'Stan nieznany',UNCERTAIN:'Blisko zmiany fazy'};
const reasonLabels={NO_SAMPLE:'brak próbki',NO_ROUTE_SELECTED:'nie wybrano trasy',LOCATION_MISSING:'brak pozycji',RECEIPT_STALE:'brak nowego odbioru',MEASUREMENT_STALE:'pomiar jest za stary',FRESHNESS_UNKNOWN:'wiek pomiaru nieznany',FRESHNESS_UNKNOWN_REPLAY_ONLY:'stary log bez pełnej informacji o wieku',GPS_ACCURACY_LIMITED:'dokładność GPS poza limitem',NO_CANDIDATE:'brak pobliskiego odcinka',IMPOSSIBLE_TRANSITION:'niemożliwy skok pozycji',AMBIGUOUS_CANDIDATES:'kilka równie możliwych odcinków',NEEDS_CONFIRMATION:'potrzebna kolejna próbka',REVERSE_DIRECTION:'przeciwny kierunek',POSITION_NOT_FRESH_OR_UNVERIFIED:'pozycja nie jest świeża',ROUTE_NOT_MATCHED:'brak pewnego dopasowania',FORWARD_DIRECTION_NOT_CONFIRMED:'niepotwierdzony kierunek',SPEED_UNAVAILABLE:'brak prędkości',GEOMETRY_NOT_FIELD_VERIFIED:'geometria bez odbioru terenowego',NEXT_STOP_LINE_UNAVAILABLE:'brak następnej linii',STOP_LINE_NOT_FIELD_VERIFIED:'linia bez odbioru terenowego',SIGNAL_ID_UNAVAILABLE:'brak powiązania sygnału',SPEED_LIMIT_NOT_FIELD_VERIFIED:'limit bez odbioru terenowego',LIVE_PHASE_DATA_UNAVAILABLE:'brak zweryfikowanych faz',PREDICTION_CLOCK_UNAVAILABLE:'brak zgodnego zegara predykcji'};
const reasonsText = values => (values||[]).map(value=>reasonLabels[value]||value).join(', ');
const fmt = (value, digits=1) => value == null ? '—' : Number(value).toFixed(digits);
const shortName = name => name.split(' × ').pop();

function showError(message) { $('error').textContent = message; $('error').hidden = !message; if(message.startsWith('Brak połączenia'))$('phone-status').textContent='Brak połączenia z serwerem — pomiary nieaktualne'; }
async function request(url, body) {
 const id = ++requestId;
 const response = await fetch(url, body === undefined ? {cache:'no-store',signal:AbortSignal.timeout(4000)} : {
  signal:AbortSignal.timeout(4000),
  method:'POST', headers:{'Content-Type':'application/json','X-GreenWave-Token':token},
  body:JSON.stringify({...body,session_id:state.session_id})
 });
 const result = await response.json();
 if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
 if (id >= displayedId) {displayedId = id; state = result; render();}
 return result;
}
function action(url, body, feedback) {
 queue = queue.then(async()=>{
  if (!state) return;
  busy = true; renderDisabled();
  try {await request(url, body); showError(''); if(feedback) $('feedback').textContent=feedback;}
  catch(error){showError(error.message);}
  finally{busy=false;renderDisabled();}
 });
 return queue;
}
async function dedicatedPost(url, body) {
 if(!state)throw new Error('Brak stanu aplikacji.');
 const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-GreenWave-Token':token},
  body:JSON.stringify({...body,session_id:state.session_id})});
 const result=await response.json();if(!response.ok)throw new Error(result.error||`HTTP ${response.status}`);return result;
}
function renderDisabled() {
 document.querySelectorAll('.server-action').forEach(control=>control.disabled=busy || !state);
 if(state&&state.view_mode!=='SIMULATION')for(const id of ['green','yellow','red'])$(id).disabled=busy||state.view_mode!=='LIVE'||!selectedRouteStop;
 if(state?.view_mode==='SIMULATION'&&state.mapping?.selected_route&&state.external_status?.state==='RECEIVING')for(const id of ['green','yellow','red'])$(id).disabled=true;
 if(state){const last=state.signals.at(-1);$('play').disabled=busy || state.view_mode!=='SIMULATION' || !state.available || !last || state.position.road_position_m>=last.road_position_m;
  $('speed').disabled=busy || !state.available || state.follow_recommendation; $('jitter').disabled=busy || !state.available;
  if(state.incident)$('play').disabled=true;
 }
}
function reset() {action('/api/reset',{dataset:$('dataset').value,jitter:$('jitter').checked},'Nowa sesja. Historia wcześniejszych obserwacji pozostaje w pamięci.');}
function recording() {action('/api/recording',{command:state.recording.active?'stop':'start'},state.recording.active?'Zapis przejazdu zakończony.':'Nagranie rozpoczęte.');}
$('dataset').addEventListener('change',()=>{if($('dataset').value==='zwirki_wigury')$('jitter').checked=false;reset();});
$('reset').addEventListener('click',reset);
$('jitter').addEventListener('change',reset);
$('play').addEventListener('click',()=>action('/api/control',{running:!state.running}));
$('follow').addEventListener('change',()=>action('/api/control',{follow_recommendation:$('follow').checked}));
$('rate').addEventListener('change',()=>action('/api/control',{rate:Number($('rate').value)}));
$('speed').addEventListener('input',()=>{$('speed-value').textContent=$('speed').value+' km/h';});
$('speed').addEventListener('change',()=>action('/api/control',{speed_kmh:Number($('speed').value)}));
$('record').addEventListener('click',recording);
$('view-mode').addEventListener('change',()=>action('/api/view',{mode:$('view-mode').value}));
$('route').addEventListener('change',()=>{liveMatchedTrail=[];action('/api/mapping/select',{route_id:$('route').value||null}).then(async()=>{if(gpsReplayState?.loaded){const response=await fetch('/api/gps-replay/state',{cache:'no-store'});if(response.ok){gpsReplayState=await response.json();renderGpsReplay();drawMap();}}});});
for(const [button,colour] of [['green','GREEN'],['yellow','YELLOW'],['red','RED']]) {
 $(button).addEventListener('click',()=>{
  const kind=$('kind').value;
  if(state.view_mode==='LIVE'){
   const point=selectedRouteStop;
   action('/api/observe-route',{stop_line_id:point,state:colour,event_type:kind},
    `Zapisano ${point}: ${colours[colour].toLowerCase()} · ${kind==='STATE_START'?'zmiana fazy teraz':'kolor widziany teraz'}. Położenie punktu jest robocze.`);
  }else{
   const point=selected;
   action('/api/observe',{signal_id:point,state:colour,event_type:kind},
    `Przyjęto ${point}: ${colours[colour]}. ${kind==='STATE_START'?'Prognoza została ponownie oceniona.':'Zapisano aktualnie widoczny kolor, bez przesuwania początku fazy.'}`);
  }
 });
}
function selectSignal(id) {selected=id;renderSignals();drawMap();}
function windowLabel(signal) {
 if(!signal.windows.length) return signal.reason;
 const window=signal.windows.find(w=>w.end>state.model_time) || signal.windows[0];
 const start=window.start-state.model_time, end=window.end-state.model_time;
 return (start<=0?`Zielone wg modelu do ${fmt(Math.max(0,end),0)} s`:`Zielone za ${fmt(start,0)}–${fmt(end,0)} s`)+` · margines ±${fmt(window.uncertainty_seconds)} s`;
}
function renderSignals() {
 if(!state) return;
 if(state.view_mode!=='SIMULATION'){
  listSession='';
  const route=state.mapping?.selected_route,lines=route?.stop_lines||[];
  $('signal-aside-description').textContent='Punkty robocze · pasażer potwierdza właściwy sygnalizator';
  if(!lines.some(line=>line.stop_line_id===selectedRouteStop))selectedRouteStop=lines[0]?.stop_line_id||'';
  $('signals').replaceChildren();
  for(const line of lines){
   const button=document.createElement('button');button.type='button';button.className='signal';
   button.setAttribute('aria-pressed',String(line.stop_line_id===selectedRouteStop));
   const last=(state.mapping?.route_observations||[]).findLast(item=>item.route_id===route.route_id&&item.stop_line_id===line.stop_line_id);
   button.textContent=`${line.source?.label||line.stop_line_id} · ${fmt(line.s_m,0)} m · ${line.verification.status}${last?' · ostatnio widziane: '+colours[last.state]:''}`;
   button.addEventListener('click',()=>{selectedRouteStop=line.stop_line_id;renderSignals();drawMap();});
   $('signals').append(button);
  }
  $('selected-label').textContent=selectedRouteStop?`Obserwujesz ${lines.find(line=>line.stop_line_id===selectedRouteStop)?.source?.label||selectedRouteStop}`:'Nie wybrano punktu';
  const recent=(state.mapping?.route_observations||[]).filter(item=>item.route_id===route?.route_id).slice(-5).reverse();
  $('route-observation-history').textContent=recent.length?'Ostatnie obserwacje: '+recent.map(item=>`${item.stop_line_id} ${colours[item.state]} ${item.event_type==='STATE_START'?'zmiana':'widziane'} · ${item.timestamp.slice(11,19)} UTC`).join(' | '):'Brak obserwacji tej trasy.';
  return;
 }
 $('signal-aside-description').textContent='Prosto · stany prognozowane i obserwacje';
 $('route-observation-history').textContent='';
 if(!state.signals.length){$('signals').replaceChildren();$('selected-label').textContent='Brak punktów';return;}
 if(listSession!==state.session_id){
  listSession=state.session_id;
  if(!state.signals.some(s=>s.signal_id===selected))selected=state.signals[0].signal_id;
  $('signals').replaceChildren();
  state.signals.forEach(s=>{
   const button=document.createElement('button');button.type='button';button.className='signal';button.dataset.signal=s.signal_id;
   button.innerHTML='<span class="dot" aria-hidden="true"></span><span class="signal-content"><span class="signal-heading"><span class="signal-title"></span><span class="signal-distance"></span></span><div class="signal-state"></div><div class="signal-window"></div><div class="signal-observation"></div></span>';
   button.addEventListener('click',()=>selectSignal(s.signal_id));$('signals').appendChild(button);
  });
 }
 state.signals.forEach(s=>{
  const button=$('signals').querySelector(`[data-signal="${s.signal_id}"]`);
  button.classList.toggle('passed',s.passed);button.setAttribute('aria-pressed',String(s.signal_id===selected));
  button.querySelector('.signal-title').textContent=`${s.signal_id} · ${shortName(s.name)}`;
  button.querySelector('.signal-distance').textContent=s.passed?'minięte':s.distance_m==null?'—':fmt(s.distance_m,0)+' m';
  button.querySelector('.dot').dataset.state=s.state;
  button.querySelector('.dot').textContent=s.passed?'✓':['UNKNOWN','UNCERTAIN'].includes(s.state)?'?':'';
  button.querySelector('.signal-state').textContent=colours[s.state]+(s.state==='UNKNOWN'?'':' · prognoza');
  button.querySelector('.signal-window').textContent=windowLabel(s);
  const observation=s.last_observation,age=s.observation_age_seconds;
  button.querySelector('.signal-observation').textContent=observation?
   `${age>=0&&age<=state.settings.observation_state_ttl_seconds?'Świeża':'Ostatnia'} obserwacja: ${colours[observation.state].toLowerCase()} · ${age<0?'czas w przyszłości':fmt(age,0)+' s temu'}`:'';
  button.setAttribute('aria-label',`${s.signal_id} ${shortName(s.name)}. ${colours[s.state]}. Wybierz do obserwacji.`);
 });
 const s=state.signals.find(s=>s.signal_id===selected);
 $('selected-label').textContent=`Obserwujesz ${selected} · ${shortName(s.name)}`;
}
function fillTable(target, rows) {
 const body=$(target);body.replaceChildren();
 for(const row of rows){const tr=document.createElement('tr');for(const text of row){const td=document.createElement('td');td.textContent=text;tr.appendChild(td);}body.appendChild(tr);}
}
function renderDebug() {
 if(!$('debug').open || !state)return;
 $('version').textContent='Wersja modelu '+state.model_version;
 fillTable('debug-rows',state.signals.map(s=>[
  s.signal_id,s.signal_type,colours[s.truth_state],`${s.state} / ${s.nominal_state}`,
  `${fmt(s.offset)} s / ${fmt(s.residual_seconds)} s`,
  `${fmt(s.age_seconds)} s / ${fmt(Math.max(0,s.valid_until-state.model_time))} s`,
  `±${fmt(s.uncertainty_seconds)} s${s.uncertainty_assumed?' (założenie)':''}\nIndeks: ${fmt(s.confidence,2)}`,
  s.source+(s.reason?'\n'+s.reason:''),s.windows.map(w=>
   `[${fmt(w.start-state.model_time)}, ${fmt(w.end-state.model_time)}) s ±${fmt(w.uncertainty_seconds)}\nWnętrze: ${w.interior_start==null?'brak':`[${fmt(w.interior_start-state.model_time)}, ${fmt(w.interior_end-state.model_time)}) s`}`).join('\n') || 'Brak okien'
 ]));
 $('relations').textContent=state.relations.length?state.relations.map(r=>`${r.source_signal_id} → ${r.target_signal_id}: +${fmt(r.green_start_delta_seconds)} s; margines ${fmt(r.uncertainty_seconds)} s · ${r.data_quality}`).join('\n'):'Brak relacji. Żadna obserwacja nie przesuwa innych świateł.';
 $('settings').textContent=`Horyzont ${state.settings.horizon_seconds} s · ważność ${state.settings.max_age_seconds} s · wzrost marginesu ${state.settings.drift_seconds_per_second} s/s · założona niepewność kliknięcia ${state.settings.assumed_manual_uncertainty_seconds} s`;
 $('resync').textContent=state.last_change?`Ostatnia resynchronizacja: ${state.last_change.signal_ids.join(', ')} · wersja ${state.last_change.model_version}`:'Brak resynchronizacji w tej sesji.';
}
function renderHistory() {
 if(!state)return;
 $('history-count').textContent=`(${state.history_total})`;
 if(!$('history').open)return;
 const key=state.history_total+':'+state.session_id;
 if(key===historyKey)return;
 historyKey=key;
 fillTable('history-rows',state.history.map(o=>[o.timestamp,fmt(o.simulation_seconds,3)+' s',o.session_id.slice(0,8)+'\n'+o.corridor_id,o.signal_id,colours[o.state],o.event_type,o.source,o.out_of_order?'SPÓŹNIONE':'OK']));
}
function renderRuns(){
 if(!state)return;
 const r=state.recording||{};
 $('record').textContent=r.active?'■ Zatrzymaj nagranie':'● Rozpocznij nagranie';
 $('record-status').textContent=r.active?`Nagrywanie ${r.run_id.slice(0,8)} · ${r.records||0} rekordów`:'Brak aktywnego nagrania';
 if(!$('runs').open&&!$('replay').open&&!$('gps-replay').open&&!$('analysis').open)return;
 const key=(r.run_id||'')+':'+(r.records||0)+':'+r.active;if(key===runsKey)return;runsKey=key;
 fetch('/api/runs',{cache:'no-store'}).then(x=>x.json()).then(runs=>{
  const list=$('run-list');list.replaceChildren();
  const ids=['replay-run','gps-replay-run','analysis-run','gps-baseline','gps-candidate'],selectedRuns={};for(const id of ids){selectedRuns[id]=$(id).value;$(id).replaceChildren();}
  replayRuns=runs.filter(run=>run.status==='COMPLETED');const gpsRuns=replayRuns.filter(run=>(run.external_samples??0)>0);
  const addRuns=(id,values)=>values.forEach(run=>{const option=document.createElement('option');option.value=run.run_id;const started=run.start_time?new Date(run.start_time).toLocaleString('pl-PL'):'—';option.textContent=`${started} · ${run.external_samples??0} GPS · ${run.run_id.slice(0,8)}`;$(id).append(option);});
  addRuns('replay-run',replayRuns);addRuns('analysis-run',replayRuns);for(const id of ['gps-replay-run','gps-baseline','gps-candidate'])addRuns(id,gpsRuns);
  for(const [id,value] of Object.entries(selectedRuns)){if([...$(id).options].some(o=>o.value===value))$(id).value=value;}if(gpsRuns.length>1&&!selectedRuns['gps-candidate'])$('gps-candidate').selectedIndex=gpsRuns.length-1;
  if(!runs.length){list.textContent='Brak zapisanych przejazdów.';return;}
  for(const run of runs){const row=document.createElement('p');row.className='run-row';const label=document.createElement('span');const started=run.start_time?new Date(run.start_time).toLocaleString('pl-PL'):'—';label.textContent=`${started} · ${run.corridor_id} · ${run.status} · ${run.records??'—'} rekordów · ${run.external_samples??'—'} GPS`;row.append(label);if(run.status==='COMPLETED'){const link=document.createElement('button');link.type='button';link.textContent='Pobierz ZIP';link.addEventListener('click',async()=>{try{const response=await fetch('/api/runs/'+run.run_id+'.zip',{headers:{'X-GreenWave-Token':token}});if(!response.ok)throw new Error('Eksport nagrania nie powiódł się.');const blob=await response.blob();const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download='greenwave-'+run.run_id+'.zip';anchor.click();URL.revokeObjectURL(url);}catch(error){showError(error.message);}});row.append(' ',link);}list.append(row);}
 }).catch(()=>{});
}
async function replayRequest(command,value){if(!state)return;const response=await fetch('/api/replay',{method:'POST',headers:{'Content-Type':'application/json','X-GreenWave-Token':token},body:JSON.stringify({session_id:state.session_id,command,value})});const result=await response.json();if(!response.ok)throw new Error(result.error||'Replay error');replayState=result;renderReplay();}
function renderReplay(){if(!replayState)return;$('replay-time').textContent=`${fmt(replayState.model_seconds)} / ${fmt(replayState.duration)} s`;$('replay-seek').max=replayState.duration;$('replay-seek').value=replayState.model_seconds;$('replay-status').textContent=replayState.loaded?`${replayState.run_id.slice(0,8)} · ${replayState.running?'odtwarzanie':'pauza'} · ${replayState.event||'—'} · ${replayState.position==null?'—':fmt(replayState.position,1)+' m'}`:'Wybierz zakończone nagranie.';}
async function gpsReplayRequest(command,value){gpsReplayState=await dedicatedPost('/api/gps-replay',{command,value});renderGpsReplay();drawMap();}
function renderGpsReplay(){
 if(!gpsReplayState)return;
 $('gps-replay-time').textContent=`${fmt(gpsReplayState.timeline_seconds)} / ${fmt(gpsReplayState.duration)} s`;
 $('gps-replay-seek').max=gpsReplayState.duration;$('gps-replay-seek').value=gpsReplayState.timeline_seconds;
 const position=gpsReplayState.sample?.position,match=gpsReplayState.mapping;
 $('gps-replay-status').textContent=gpsReplayState.loaded?`${gpsReplayState.run_id.slice(0,8)} · ${gpsReplayState.cursor}/${gpsReplayState.sample_count} próbek · ${gpsReplayState.running?'odtwarzanie':'pauza'} · GPS ${position?fmt(position.latitude,6)+', '+fmt(position.longitude,6):'—'} · ${position?.speed_mps==null?'brak prędkości':fmt(position.speed_mps*3.6,1)+' km/h ('+position.speed_source+')'} · dokładność ${fmt(position?.gps_accuracy_m,1)} m · pomiar ${gpsReplayState.sample?.phone_timestamp_seconds==null?'—':new Date(gpsReplayState.sample.phone_timestamp_seconds*1000).toLocaleTimeString('pl-PL')} · odbiór ${gpsReplayState.sample?.received_at?new Date(gpsReplayState.sample.received_at).toLocaleTimeString('pl-PL'):'—'} · dopasowanie ${match?.status||'—'}`:'Wybierz zakończone nagranie zawierające GPS.';
 if(state?.view_mode==='GPS_REPLAY'){$('current-speed').textContent=fmt(position?.speed_mps==null?null:position.speed_mps*3.6,0);$('position').textContent=`GPS ${fmt(position?.latitude,6)}, ${fmt(position?.longitude,6)}`;renderMapping();}
}
$('gps-replay-load').addEventListener('click',async()=>{try{await action('/api/view',{mode:'GPS_REPLAY'});await gpsReplayRequest('load',$('gps-replay-run').value);await request('/api/state');resetMap();}catch(error){showError(error.message);}});
$('gps-replay-play').addEventListener('click',()=>gpsReplayRequest('play').catch(e=>showError(e.message)));
$('gps-replay-pause').addEventListener('click',()=>gpsReplayRequest('pause').catch(e=>showError(e.message)));
$('gps-replay-reset').addEventListener('click',()=>gpsReplayRequest('reset').catch(e=>showError(e.message)));
$('gps-replay-rate').addEventListener('change',()=>gpsReplayRequest('rate',Number($('gps-replay-rate').value)).catch(e=>showError(e.message)));
$('gps-replay-seek').addEventListener('change',()=>gpsReplayRequest('seek',Number($('gps-replay-seek').value)).catch(e=>showError(e.message)));
async function waitForMappingAnalysis(job){
 $('mapping-analysis-result').textContent='Analiza działa w tle…';
 while(job.status==='RUNNING'){
  await new Promise(resolve=>setTimeout(resolve,250));
  const response=await fetch('/api/mapping/jobs/'+job.job_id,{cache:'no-store',headers:{'X-GreenWave-Token':token}});
  job=await response.json();if(!response.ok)throw new Error(job.error||`HTTP ${response.status}`);
 }
 if(job.status==='FAILED')throw new Error(job.error||'Analiza mapowania nie powiodła się.');
 $('mapping-analysis-result').textContent=formatMappingReview(job.result)+'\n\nPełny raport:\n'+JSON.stringify(job.result,null,2);
}
async function loadSignalHistory(){
 const route=$('route').value;
 const response=await fetch('/api/observation-history'+(route?'?route_id='+encodeURIComponent(route):''),{cache:'no-store',headers:{'X-GreenWave-Token':token}});
 const history=await response.json();if(!response.ok)throw new Error(history.error||`HTTP ${response.status}`);
 const body=$('signal-history-rows');body.replaceChildren();
 for(const point of history.points)for(const event of point.observations){
  const row=document.createElement('tr');
  const labels={KEEP:'uwzględnione',RAPID_DUPLICATE:'szybki duplikat',REPEATED_STATE_REVIEW:'powtórzony kolor — do przeglądu'};
  const values=[`${point.route_id}\n${event.geometry_version||'—'} / ${point.geometry_hash.slice(0,12)}\n${point.stop_line_id}`,
   `${event.direction_description||'kierunek nieznany dla tej geometrii'}\n${event.direction||'—'} / ${event.movement||'—'}`,
   `${new Date(event.timestamp).toLocaleString('pl-PL')}\n${event.run_id.slice(0,8)} · rekord ${event.record_sequence}`,
   `${event.state} · ${event.reviewed_type}\n${event.source||'—'} · ${event.interpretation_source}`,
   `${event.gps_freshness||'—'} · dokładność ${event.gps_accuracy_m==null?'—':fmt(event.gps_accuracy_m,1)+' m'}\n${event.latitude??'—'}, ${event.longitude??'—'}`,
   labels[event.classification]||event.classification];
  for(const value of values){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}body.append(row);
 }
 $('signal-history-status').textContent=`${history.observation_count} obserwacji · ${history.points.length} punktów w osobnych geometriach. ${history.observation_count?'':'Kliknij „Importuj / odśwież nagrania”, aby wczytać zakończone przejazdy.'}`;
}
$('signal-history-load').addEventListener('click',()=>loadSignalHistory().catch(e=>showError(e.message)));
async function loadSignalCompleteness(){
 const route=$('route').value;
 const response=await fetch('/api/observation-history/completeness'+(route?'?route_id='+encodeURIComponent(route):''),{cache:'no-store',headers:{'X-GreenWave-Token':token}});
 const report=await response.json();if(!response.ok)throw new Error(report.error||`HTTP ${response.status}`);
 const labels={NO_DATA:'BRAK DANYCH',PARTIAL_DATA:'DANE CZĘŚCIOWE',REPEATED_INTERVALS:'SĄ POWTÓRZENIA — MODEL JESZCZE NIEZWERYFIKOWANY'};
 const output=['KOMPLETNOŚĆ OBSERWACJI — nie jest oceną gotowości rekomendacji live'];
 for(const point of report.points){
  output.push(`\n${point.route_id} · ${point.stop_line_id} · geometria ${point.geometry_hash.slice(0,12)}\n${labels[point.status]}`);
  output.push(`Obserwacje: ${point.observation_count} · przejazdy z obserwacjami: ${point.run_count} · początki faz: ${point.start_count} · tylko widziany kolor: ${point.seen_count}\nSzybkie duplikaty: ${point.duplicate_count} · powtórzenia do przeglądu: ${point.repeated_review_count}\nPoczątki kolorów: ${Object.entries(point.start_color_counts).map(([k,v])=>k+': '+v).join(' · ')||'brak'}\nGPS: ${Object.entries(point.freshness_counts).map(([k,v])=>k+': '+v).join(' · ')||'brak'}`);
  for(const interval of point.intervals)output.push(`Para ${interval.transition}: ${fmt(interval.seconds,2)} s · przejazd ${interval.run_id.slice(0,8)} · rekordy ${interval.start_record}–${interval.end_record}${interval.interpretation==='TRANSITION_INTERVAL_ONLY'?' (odstęp zmian, nie długość fazy)':''}`);
  output.push(`Powroty do początku tego samego koloru: ${point.recurrences.length} (mogły obejmować pominięte cykle).`);
  if(point.verification)output.push(`Weryfikacja: trasa ${point.verification.geometry} · linia ${point.verification.stop_line} · limit ${point.verification.speed_limit}`);
  output.push('Do zebrania / sprawdzenia:\n'+point.missing.map(item=>'• '+item).join('\n'));
 }
 output.push('\nNie łączymy odcinków pomiędzy nagraniami. Kliknięcia zawierają czas reakcji. Brakujące kolory i czasy nie są uzupełniane założeniami.');
 $('signal-completeness-result').textContent=output.join('\n');
}
$('signal-completeness-load').addEventListener('click',()=>loadSignalCompleteness().catch(e=>showError(e.message)));
$('signal-history-sync').addEventListener('click',async()=>{
 const button=$('signal-history-sync');button.disabled=true;$('signal-history-status').textContent='Importowanie zakończonych nagrań…';
 try{const result=await dedicatedPost('/api/observation-history/sync',{});await loadSignalHistory();await loadSignalCompleteness();
  $('signal-history-status').textContent+=` Sprawdzono ${result.imported_runs} nagrań. Błędy: ${result.errors.length}.`;
  if(result.errors.length)$('signal-history-status').textContent+=' '+result.errors.map(e=>`${e.run_id.slice(0,8)}: ${e.error}`).join(' · ');
 }catch(e){showError(e.message);}finally{button.disabled=false;}
});
function formatMappingReview(result){
 const review=result.observation_review;
 if(!review)return 'Brak zestawienia obserwacji.';
 const output=['OBSERWACJE ŚWIATEŁ I PRZEJAZDY',review.attestation?'Momenty zmian potwierdzone przez użytkownika; oryginalne kliknięcia zachowane.':'Bez dodatkowego potwierdzenia: STATE_SEEN oznacza tylko zaobserwowany kolor.'];
 const labels={KEEP:'uwzględnione',RAPID_DUPLICATE:'szybki duplikat — pominięty w czasach',REPEATED_STATE_REVIEW:'powtórzony kolor — do przeglądu, pominięty w czasach'};
 for(const point of review.points){
  output.push('\n'+point.stop_line_id);
  for(const event of point.observations){
   const time=new Date(event.timestamp).toLocaleTimeString('pl-PL',{hour12:false});
   const distance=event.candidate_distance_to_line_m==null?'brak dystansu':`${fmt(event.candidate_distance_to_line_m,1)} m do linii${event.distance_is_accepted?'':' (robocza projekcja)'}`;
   output.push(`${time} · ${event.state} · ${event.reviewed_type} · ${labels[event.classification]}\n  GPS ${event.gps_freshness||'—'} · dopasowanie ${event.reprocessed_match_status||'brak próbki'} · ${distance} · prędkość ${event.speed_mps==null?'—':fmt(event.speed_mps*3.6,1)+' km/h'}`);
  }
  if(!point.observations.length)output.push('Brak kliknięć.');
  for(const interval of point.intervals)output.push(`${interval.from_state} → ${interval.to_state}: ${fmt(interval.seconds,2)} s${interval.meaning==='OBSERVED_RED_INTERVAL'?' — zaobserwowany odcinek czerwonego':' — odstęp kliknięć, nie czas samego zielonego'}`);
  for(const crossing of point.crossings){
   output.push(`Przekroczenie linii: ${crossing.status}${crossing.reason_code?' · '+crossing.reason_code:''} · czas nagrania ${fmt(crossing.time_start_seconds,2)}–${fmt(crossing.time_end_seconds,2)} s`);
   if(crossing.status==='UNCONFIRMED')output.push(`  Przed: ${crossing.before_match?.status||'—'} / ${crossing.before_match?.direction||'—'} · po: ${crossing.after_match?.status||'—'} / ${crossing.after_match?.direction||'—'}`);
  }
  if(!point.crossings.length)output.push('Brak potwierdzenia przekroczenia linii.');
 }
 output.push('\nCzasy zawierają opóźnienie reakcji pasażera. Nie wyznaczamy cyklu ani czasu żółtego. Potwierdzenie algorytmu nie weryfikuje położenia linii w terenie.');
 return output.join('\n');
}
$('mapping-analysis').addEventListener('click',async()=>{try{const runId=gpsReplayState?.run_id||$('gps-replay-run').value;await waitForMappingAnalysis(await dedicatedPost('/api/mapping/analyze',{run_id:runId,write:true}));}catch(error){showError(error.message);}});
function formatGpsAnalysis(result){
 const gps=result.gps_quality,percent=value=>value==null?'—':fmt(value*100,1)+'%',seconds=value=>value==null?'—':fmt(value,2)+' s';
 if(!gps||gps.status==='NO_DATA')return `GPS: BRAK DANYCH\n${gps?.issues?.join('\n')||'Nagranie nie zawiera raportu GPS.'}\n\nMetryki symulacji:\n${JSON.stringify({...result,gps_quality:undefined},null,2)}`;
 const labels={READY:'GOTOWE DO PORÓWNANIA',DEGRADED:'DANE O OGRANICZONEJ JAKOŚCI',INSUFFICIENT:'ZA MAŁO DANYCH'};
 const sources=(Object.entries(gps.speed.source_counts).map(([key,value])=>`${key}: ${value}`).join(' · ')||'brak')+`\nŹródła lokalizacji: ${Object.entries(gps.location_source_counts||{}).map(([key,value])=>`${key}: ${value}`).join(' · ')||'brak'}`;
 const issues=gps.issues.length?gps.issues.map(issue=>'• '+issue).join('\n'):'Brak problemów według przyjętych progów.';
 return `GPS: ${labels[gps.status]||gps.status}\nPróbki: ${gps.sample_count} · czas: ${fmt(gps.duration_seconds,1)} s · częstotliwość: ${fmt(gps.sample_rate_hz,2)} Hz\nOdstęp odbioru: mediana ${seconds(gps.receipt_interval_median_seconds)} · p95 ${seconds(gps.receipt_interval_p95_seconds)} · największa luka ${seconds(gps.largest_gap_seconds)}\nOdstęp pomiarów telefonu: mediana ${seconds(gps.phone_interval_median_seconds)} · p95 ${seconds(gps.phone_interval_p95_seconds)} · największa luka ${seconds(gps.largest_phone_gap_seconds)}\nLuki telefonu >2 s: ${gps.phone_gaps_over_2_seconds} · dodatkowe luki transportu >2 s: ${gps.transport_only_gaps_over_2_seconds} · cofnięcia czasu: ${gps.phone_timestamp_regressions}\n\nDokładność GPS: mediana ${fmt(gps.accuracy.median_m,1)} m · p95 ${fmt(gps.accuracy.p95_m,1)} m · zakres ${fmt(gps.accuracy.minimum_m,1)}–${fmt(gps.accuracy.maximum_m,1)} m\n≤10 m: ${percent(gps.accuracy.within_10m_ratio)} · ≤25 m: ${percent(gps.accuracy.within_25m_ratio)} · ≤50 m: ${percent(gps.accuracy.within_50m_ratio)}\nPróbki użyteczne: ${gps.usable_samples}/${gps.sample_count} (${percent(gps.usable_ratio)})\n\nPrędkość końcowa dostępna: ${percent(gps.speed.final_available_ratio)} · surowa: ${percent(gps.speed.raw_available_ratio)} · wyliczona: ${percent(gps.speed.calculated_available_ratio)}\nŹródła prędkości: ${sources}\nMaksymalna prędkość końcowa: ${gps.speed.maximum_final_mps==null?'—':fmt(gps.speed.maximum_final_mps*3.6,1)+' km/h'}\nPrzejścia postój/ruch: ${gps.movement_transitions} · rozpoczęcia ruchu: ${gps.movement_starts} · potwierdzenia postoju: ${gps.stop_confirmations}\nSurowa długość śladu GPS: ${fmt(gps.raw_path_distance_m,1)} m\n\nOcena:\n${issues}`;
}
$('replay-load').addEventListener('click',()=>replayRequest('load',$('replay-run').value).catch(e=>showError(e.message)));
$('analysis-load').addEventListener('click',async()=>{try{const response=await fetch('/api/analysis/'+$('analysis-run').value,{cache:'no-store'});const result=await response.json();if(!response.ok)throw new Error(result.error||'Analiza nie powiodła się.');$('analysis-result').textContent=formatGpsAnalysis(result);}catch(error){showError(error.message);}});
$('gps-compare').addEventListener('click',async()=>{try{const query=new URLSearchParams({baseline:$('gps-baseline').value,greenwave:$('gps-candidate').value});const response=await fetch('/api/analysis/compare?'+query,{cache:'no-store'});const result=await response.json();if(!response.ok)throw new Error(result.error||'Porównanie nie powiodło się.');const first=result.baseline.gps_quality,second=result.greenwave.gps_quality;$('gps-compare-result').textContent=`Baza: ${JSON.stringify(first.location_source_counts||{})}\nKandydat: ${JSON.stringify(second.location_source_counts||{})}\n\nZmiana (kandydat − baza):\n${JSON.stringify(result.gps_delta,null,2)}\n\n${result.interpretation}`;}catch(error){showError(error.message);}});
$('replay-play').addEventListener('click',()=>replayRequest('play').catch(e=>showError(e.message)));$('replay-pause').addEventListener('click',()=>replayRequest('pause').catch(e=>showError(e.message)));$('replay-rate').addEventListener('change',()=>replayRequest('rate',Number($('replay-rate').value)).catch(e=>showError(e.message)));$('replay-seek').addEventListener('change',()=>replayRequest('seek',Number($('replay-seek').value)).catch(e=>showError(e.message)));
$('debug').addEventListener('toggle',renderDebug);
$('history').addEventListener('toggle',()=>{historyKey='';renderHistory();});
function renderRouteControls(){
 const routes=state.routes||[],selectedRoute=state.mapping?.selected_route?.route_id||'';
 const key=routes.map(r=>`${r.route_id}:${r.geometry_version||r.status}`).join('|');
 if(key!==routesKey){routesKey=key;const select=$('route');select.replaceChildren();const none=document.createElement('option');none.value='';none.textContent='Bez trasy';select.append(none);for(const route of routes){const option=document.createElement('option');option.value=route.route_id;option.disabled=route.status!=='OK';const verification=route.geometry_verification?.status||route.status;option.textContent=`${route.name} · ${verification}`;select.append(option);}}
 $('route').value=selectedRoute;$('view-mode').value=state.view_mode;
}
function renderMapping(){
 const mapping=state.mapping||{},replay=state.view_mode==='GPS_REPLAY'?gpsReplayState:null,result=replay?.mapping||mapping.result||{},route=mapping.selected_route,next=replay?.next_stop_line||mapping.next_stop_line,gate=mapping.recommendation_eligibility||{};
 const reasons=reasonsText(result.reason_codes)||'brak';
 $('mapping-values').textContent=`Trasa: ${route?route.name+' · '+route.geometry_verification.status:'bez trasy — wybierz Trasa GPS'}\nStatus: ${result.status||'NO_ROUTE'} · kierunek: ${result.direction||'UNKNOWN'}\nPozycja na trasie: ${fmt(result.accepted_s_m)} m · odchylenie: ${fmt(result.cross_track_m)} m · niepewność: ${fmt(result.position_uncertainty_m)} m\nNastępny punkt: ${next?next.stop_line_id+' · '+fmt(next.distance_m,0)+' m':route?'brak kolejnego punktu lub pewnego dopasowania':'niedostępny bez wybranej trasy'}\nWiek pomiaru ≥ ${fmt(result.measurement_age_lower_bound_seconds,2)} s · odbioru ${fmt(result.receipt_age_seconds,2)} s\nPrzyczyny: ${reasons}\nRekomendacja live: ${gate.allowed?'dostępna':'niedostępna'}${gate.reason_codes?.length?' · '+reasonsText(gate.reason_codes):''}`;
}
function render() {
 const phone=state.external_position, connection=state.external_status;
 const quality={GOOD:'dobra',FAIR:'średnia',POOR:'ograniczona',UNUSABLE:'zbyt słaba',UNKNOWN:'nieznana',MISSING:'brak pozycji'};
 const speedSource={DEVICE:'telefon',CALCULATED:'wyliczona z GPS',STATIONARY_FILTER:'potwierdzony postój',UNAVAILABLE:'brak'};
 $('phone-status').textContent=!connection?'Uruchom ponownie serwer, aby włączyć status GPS.':connection.state==='WAITING'?'Oczekiwanie na telefon':connection.state==='STALE'?'Brak nowych lub świeżych próbek telefonu':connection.live_control_eligible?'Odbieram świeże dane · gotowe do mapowania live':'Odbieram dane · bez potwierdzonej świeżości sterowania';
 $('phone-values').textContent=phone?`GPS: ${fmt(phone.latitude,6)}, ${fmt(phone.longitude,6)}\nPrędkość końcowa: ${fmt(phone.speed_mps==null?null:phone.speed_mps*3.6)} km/h · źródło: ${speedSource[phone.speed_source]||phone.speed_source}\nSurowa: ${fmt(phone.raw_speed_mps==null?null:phone.raw_speed_mps*3.6)} km/h · wyliczona: ${fmt(phone.calculated_speed_mps==null?null:phone.calculated_speed_mps*3.6)} km/h\nDokładność: ${fmt(phone.gps_accuracy_m)} m · jakość: ${quality[phone.position_quality]||phone.position_quality} · kierunek: ${fmt(phone.heading_deg)}°\nOd odbioru: ${fmt(connection?.age_seconds)} s · odstęp próbek: ${fmt(connection?.sample_interval_seconds)} s\nOdebrano: ${connection?.received_count??'—'} · użyteczne: ${connection?.usable_count??'—'} · odrzucone jakościowo: ${connection?.quality_rejected_count??'—'}\n${connection?.diagnostic||''}`:'Brak pomiarów';
 $('dataset').value=state.dataset;$('jitter').checked=state.jitter;
 if(phone?.latitude!=null&&phone?.longitude!=null){const key=phone.device_id?`${phone.device_id}:${phone.stream_id}:${phone.sample_sequence}`:`${phone.elapsed_seconds}:${phone.latitude}:${phone.longitude}`;if(key!==liveSampleKey){liveSampleKey=key;liveTrail.push({latitude:phone.latitude,longitude:phone.longitude,accepted:phone.usable_for_live});const match=state.mapping?.result;if(match?.accepted_latitude!=null&&match?.accepted_longitude!=null)liveMatchedTrail.push({latitude:match.accepted_latitude,longitude:match.accepted_longitude});if(liveTrail.length>1200)liveTrail.shift();if(liveMatchedTrail.length>1200)liveMatchedTrail.shift();}}
 if(phone)$('phone-values').textContent+=`\nŹródło lokalizacji: ${phone.source}${phone.device_id?' · '+phone.device_id.slice(0,8):''} · stan ruchu: ${connection?.motion_state??'—'} · transmisje: ${connection?.transmission_count??'—'} · duplikaty: ${connection?.duplicate_count??'—'}\nŚwieżość: ${connection?.freshness_status??'UNKNOWN'} · wiek pomiaru ≥ ${fmt(connection?.measurement_age_lower_bound_seconds,2)} s`;
 renderRouteControls();renderMapping();
 $('play').textContent=state.running?'Pauza':'Start';$('rate').value=String(state.rate);
 $('follow').checked=state.follow_recommendation;
 renderRecommendation();
 if(document.activeElement!==$('speed')){$('speed').value=state.speed_setting_kmh;$('speed-value').textContent=fmt(state.speed_setting_kmh,0)+' km/h';}
 const displayPosition=state.view_mode==='GPS_REPLAY'?gpsReplayState?.sample?.position:state.view_mode==='LIVE'?phone:null;
 $('current-speed').textContent=state.view_mode==='SIMULATION'?(state.available?fmt(state.position.speed_mps*3.6,0):'—'):fmt(displayPosition?.speed_mps==null?null:displayPosition.speed_mps*3.6,0);
 const acceptedS=state.view_mode==='GPS_REPLAY'?gpsReplayState?.mapping?.accepted_s_m:state.mapping?.result?.accepted_s_m;
 const liveSection=state.mapping?.selected_route?.speed_sections?.find(section=>acceptedS!=null&&section.start_s_m<=acceptedS&&acceptedS<=section.end_s_m);
 $('limit').textContent=state.view_mode==='SIMULATION'?(state.speed_limit_mps==null?'?':fmt(state.speed_limit_mps*3.6,0)):(liveSection?.limit_mps==null?'?':fmt(liveSection.limit_mps*3.6,0));
 $('warning').textContent=state.view_mode==='SIMULATION'&&state.mapping?.selected_route&&connection?.state==='RECEIVING'?'TELEFON WYSYŁA GPS, ALE WIDOK TO SYMULACJA. Wybierz „Telefon na żywo”, aby zapisywać kolory świateł wybranej trasy.':state.view_mode==='SIMULATION'?(state.available?'DANE SYNTETYCZNE: czasy, odległości i limit są testowe. Punkty S1–S5 rozmieszczono przykładowo na mapie — nie są zweryfikowanymi liniami zatrzymania.':'DANE NIEZWERYFIKOWANE: brak faz, geometrii i limitu.'):(state.mapping?.result?.status==='STALE'?'POMIAR NIEAKTUALNY: mapa pokazuje ostatnią pozycję diagnostycznie.':'TRYB GPS: kolor świateł pozostaje nieznany bez osobnego źródła faz.');
 const next=state.signals.find(s=>!s.passed);
 const mappedNext=state.view_mode==='GPS_REPLAY'?gpsReplayState?.next_stop_line:state.mapping?.next_stop_line;
 $('next-signal').textContent=state.view_mode==='SIMULATION'?(state.available?(next?`Następny: ${next.signal_id} · ${shortName(next.name)}`:'Koniec trasy testowej'):'Brak zweryfikowanej pozycji'):(mappedNext?`Następny: ${mappedNext.stop_line_id} · ${fmt(mappedNext.distance_m,0)} m`:state.mapping?.selected_route?'Brak kolejnego punktu lub pewnego dopasowania':'Nie wybrano trasy GPS');
 $('position').textContent=state.view_mode==='SIMULATION'?(state.available?`Pozycja sondy ${fmt(state.position.road_position_m,0)} m`:'Symulacja pozycji wyłączona'):`GPS ${fmt(displayPosition?.latitude,6)}, ${fmt(displayPosition?.longitude,6)}`;
 $('session').textContent=`Sesja ${state.session_id.slice(0,8)} · ${state.running?'symulacja działa':'symulacja zatrzymana'}`;
 $('time').textContent=`Czas modelu ${fmt(state.model_time)} s · ${state.timebase==='SIMULATION'?'symulacja':'od początku sesji UTC'}`;
 $('utc').textContent=`UTC ${state.utc.replace('T',' ').replace('+00:00','')}`;
 $('signal-aside').hidden=state.view_mode!=='SIMULATION'&&!state.mapping?.selected_route?.stop_lines?.length;$('map').classList.toggle('mapping-live',state.view_mode!=='SIMULATION');
 renderSignals();renderDebug();renderHistory();renderRuns();renderReplay();renderGpsReplay();renderDisabled();drawMap();
}

const actions={HOLD:'Utrzymuj tempo',ACCELERATE:'Łagodnie przyspieszaj',COAST:'Puść gaz',ENGINE_BRAKE:'Hamuj silnikiem',BRAKE:'Hamuj',STOP:'Zatrzymaj się / czekaj'};
function renderRecommendation(){
 if(state.view_mode!=='SIMULATION'){
  const eligibility=state.mapping?.recommendation_eligibility||{},recommendation=state.mapping?.live_recommendation;
  $('target-value').textContent=recommendation?.target_kmh??'—';$('target-range').textContent=recommendation?.status==='READY'?`Zakres ${recommendation.range_min_kmh}–${recommendation.range_max_kmh} km/h · ${recommendation.signal_id}`:`Brak rekomendacji live · ${reasonsText(eligibility.reason_codes)}`;
  $('driving-action').textContent=recommendation?.status==='READY'?(actions[recommendation.action]||recommendation.action):'Pozycja i dystanse · tryb diagnostyczny';return;
 }
 const r=state.recommendation;
 $('target-value').textContent=r.target_kmh??'—';
 $('target-range').textContent=r.status==='READY'?`Zakres ${r.range_min_kmh}–${r.range_max_kmh} km/h · ${r.signal_id}`:r.reason;
 const message=r.status==='COMPLETE'?'Koniec odcinka':!r.signal_id&&r.status!=='UNSAFE'?'Brak rekomendacji':(actions[r.action]||r.action)+(r.status==='READY'?' · '+r.signal_id:'');
 if($('driving-action').textContent!==message)$('driving-action').textContent=message;
 if(state.incident)showError(state.incident);
 if(!$('solver-debug').open)return;
 $('solver-status').textContent=`${r.status} · ${r.reason} ${r.arrival_at==null?'':`Przejazd za ${fmt(r.arrival_at-state.model_time)} s.`}`;
 const plan=state.trajectory;
 $('trajectory-status').textContent=plan?`${plan.status==='COMPLETE'?'Plan w całym horyzoncie':plan.status==='PARTIAL'?'Plan częściowy':'Brak planu'} · ${plan.legs.length} punktów${plan.boundary?' · granica planu: '+plan.boundary:''}. Cele są warunkowe względem prognoz; kolejne odcinki będą przeliczane.`:'Brak aktywnej trajektorii.';
 fillTable('trajectory-legs',(plan?.legs||[]).map(l=>[l.signal_id,`${l.target_kmh} km/h`,`${fmt(l.arrival_at-state.model_time)} s`,`${fmt(l.crossing_speed_mps*3.6,0)} km/h`,`${l.stops} / ${fmt(l.wait_seconds)} s`]));
 const cost=plan?.cost;
 $('trajectory-cost').textContent=cost?`Koszt ${fmt(cost.total)} = postoje ${fmt(cost.weighted.stops)} + hamowanie ${fmt(cost.weighted.braking)} + zmiany przyspieszenia ${fmt(cost.weighted.variation)} + czas ${fmt(cost.weighted.time)} + ryzyko ${fmt(cost.weighted.risk)}. Wagi: data/trajectory.json.`:'';
 const baseline=plan?.baseline;
 $('trajectory-baseline').textContent=baseline?.complete?`Porównanie planów z tej samej pozycji: M4 ${cost.raw.stops} zatrzymań, ${fmt(cost.raw.time)} s; wybór lokalny ${baseline.cost.raw.stops} zatrzymań, ${fmt(baseline.cost.raw.time)} s, koszt ${fmt(baseline.cost.total)}. To prognozy, nie pomiary przejazdu.`:baseline?'Wybór lokalny nie znalazł pełnego planu w tym horyzoncie.':'';
 $('trajectory-alternatives').textContent=(plan?.alternatives||[]).map(a=>`Cel ${a.target_kmh} · postoje ${a.stops} · koszt ${fmt(a.cost)}`).join(' | ');
 const v=state.vehicle_settings;
 $('solver-dynamics').textContent=`Przyspieszenie pojazdu ${fmt(state.acceleration_mps2,2)} m/s² · reakcja ${v.reaction_delay} s · komfort +${v.comfortable_acceleration} / −${v.comfortable_deceleration} m/s² · M4: przeszukiwanie kombinacji zielonych okien`;
 fillTable('solver-candidates',r.candidates.map(c=>[`${c.target_kmh} (${c.range_min_kmh}–${c.range_max_kmh}) km/h`,c.mode,`${fmt(c.window_start-state.model_time)}–${fmt(c.window_end-state.model_time)} s`,`${fmt(c.arrival_at-state.model_time)} s`,`${fmt(c.acceleration_mps2,2)} / ${fmt(c.deceleration_mps2,2)} m/s²`]));
 $('crossings').textContent='Przekroczenia linii: '+(state.crossings.map(c=>`${c.signal_id} ${colours[c.state]} @ ${fmt(c.time)} s`).join(' · ')||'brak');
}
$('solver-debug').addEventListener('toggle',()=>{if(state)renderRecommendation();});
$('runs').addEventListener('toggle',()=>{if(state)renderRuns();});
$('replay').addEventListener('toggle',()=>{if(state){renderRuns();renderReplay();}});
$('gps-replay').addEventListener('toggle',()=>{if(state){renderRuns();renderGpsReplay();}});
$('analysis').addEventListener('toggle',()=>{if(state)renderRuns();});

// Offline geographic map. EPSG:3857 projection; markers use demo distances only.
const canvas=$('map-canvas'),ctx=canvas.getContext('2d');
const colourProbe=document.createElement('span');colourProbe.hidden=true;document.body.appendChild(colourProbe);
let zoom=1,panX=0,panY=0,drag=null,hitPoints=[];
function project([lon,lat]){return [lon*Math.PI/180, -Math.log(Math.tan(Math.PI/4+lat*Math.PI/360))];}
function resetMap(){zoom=1;panX=panY=0;drawMap();}
$('zoom-in').addEventListener('click',()=>{zoom=Math.min(zoom*1.3,8);drawMap();});
$('zoom-out').addEventListener('click',()=>{zoom=Math.max(zoom/1.3,.5);drawMap();});
$('map-fit').addEventListener('click',resetMap);
canvas.addEventListener('pointerdown',e=>{drag={x:e.offsetX,y:e.offsetY,panX,panY,moved:false};canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(drag){const dx=e.offsetX-drag.x,dy=e.offsetY-drag.y;if(Math.hypot(dx,dy)>4)drag.moved=true;panX=drag.panX+dx;panY=drag.panY+dy;drawMap();}});
canvas.addEventListener('pointerup',e=>{if(drag&&!drag.moved){const hit=hitPoints.find(p=>Math.hypot(e.offsetX-p.x,e.offsetY-p.y)<20);if(hit){if(state?.view_mode==='SIMULATION')selectSignal(hit.id);else{selectedRouteStop=hit.id;renderSignals();drawMap();}}}drag=null;});
canvas.addEventListener('pointercancel',()=>{drag=null;});
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.5,Math.min(8,zoom*(e.deltaY<0?1.12:1/1.12)));drawMap();},{passive:false});
function demoLocation(fraction) {
 const route=mapData.projectedRoute, lengths=mapData.lengths,total=lengths.at(-1),distance=Math.max(0,Math.min(1,fraction))*total;
 let i=1;while(i<lengths.length-1&&lengths[i]<distance)i++;
 const ratio=(distance-lengths[i-1])/(lengths[i]-lengths[i-1]||1);
 return [route[i-1][0]+ratio*(route[i][0]-route[i-1][0]),route[i-1][1]+ratio*(route[i][1]-route[i-1][1])];
}
function drawMap() {
 if(!mapData)return;
 const w=$('map').clientWidth,h=$('map').clientHeight,dpr=window.devicePixelRatio||1;
 if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
 ctx.setTransform(dpr,0,0,dpr,0,0);
 const css=getComputedStyle(document.documentElement),colour=name=>css.getPropertyValue(name).trim();
 // Resolve light-dark() CSS values through the browser before assigning canvas colours.
 function resolved(name){colourProbe.style.color=colour(name);return getComputedStyle(colourProbe).color;}
 const palette={};for(const name of ['bg','panel','text','muted','line','green','red','yellow','road','block','park'])palette[name]=resolved('--'+name);
 ctx.fillStyle=palette.bg;ctx.fillRect(0,0,w,h);
 const mode=state?.view_mode||'SIMULATION';
 const selectedRoute=(state?.mapping?.selected_route?.coordinates||[]).map(project);
 const rawEntries=(mode==='GPS_REPLAY'?(gpsReplayState?.trail||[]):mode==='LIVE'?liveTrail:[]).filter(p=>p.longitude!=null&&p.latitude!=null);
 const rawTrail=rawEntries.map(p=>project([p.longitude,p.latitude]));
 const matchedTrail=(mode==='GPS_REPLAY'?(gpsReplayState?.trail||[]):liveMatchedTrail).filter(p=>p.matched_longitude!=null&&p.matched_latitude!=null||mode==='LIVE'&&p.longitude!=null&&p.latitude!=null).map(p=>project([p.matched_longitude??p.longitude,p.matched_latitude??p.latitude]));
 let route=mode==='SIMULATION'?mapData.projectedRoute:(rawTrail.length?rawTrail:selectedRoute.length?selectedRoute:mapData.projectedRoute);
 const rawPosition=mode==='GPS_REPLAY'?gpsReplayState?.sample?.position:mode==='LIVE'?state?.external_position:null;
 const sourcePosition=rawPosition?.longitude!=null?rawPosition:selectedRoute.length?{longitude:state.mapping.selected_route.coordinates[0][0],latitude:state.mapping.selected_route.coordinates[0][1]}:null;
 const localSource=(mapData.sources||[]).find(source=>source.bbox&&sourcePosition?.longitude>=source.bbox[0]&&sourcePosition.longitude<=source.bbox[2]&&sourcePosition?.latitude>=source.bbox[1]&&sourcePosition.latitude<=source.bbox[3]);
 $('map-legend').hidden=mode==='SIMULATION';
 $('map-route-notice').hidden=mode==='SIMULATION'||selectedRoute.length>1||rawTrail.length===0;
 $('map-source').textContent=mode==='SIMULATION'?'lokalny podkład Żwirki i Wigury · punkty demo':localSource?`lokalny podkład offline · dane ${localSource.extracted_on}`:'brak lokalnego podkładu dla tej pozycji';
 const replayBounds=mode==='GPS_REPLAY'&&gpsReplayState?.bounds?[project([gpsReplayState.bounds[0],gpsReplayState.bounds[1]]),project([gpsReplayState.bounds[2],gpsReplayState.bounds[3]])]:[];
 const focus=[...route,...selectedRoute,...replayBounds];if(!focus.length)return;
 const xs=focus.map(p=>p[0]),ys=focus.map(p=>p[1]);
 const cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2;
 const spanX=Math.max(1e-5,Math.max(...xs)-Math.min(...xs)),spanY=Math.max(1e-5,Math.max(...ys)-Math.min(...ys));
 const scale=Math.min((w-90)/spanX,(h-300)/spanY)*zoom;
 const toScreen=p=>[(p[0]-cx)*scale+w*.5+panX,(p[1]-cy)*scale+(h+130)/2+panY];
 function path(points){ctx.beginPath();points.forEach((p,i)=>{const [x,y]=toScreen(p);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});}
 for(const feature of mapData.features){const polygon=feature.geometry.type==='Polygon';path(feature.projected);if(polygon){ctx.closePath();ctx.fillStyle=feature.properties.kind==='park'?palette.park:palette.block;ctx.fill();}else{ctx.strokeStyle=palette.road;ctx.lineWidth=['primary','secondary','tertiary'].includes(feature.properties.kind)?8:2.5;ctx.lineCap='round';ctx.stroke();}}
 if(mode==='SIMULATION'){path(mapData.projectedRoute);ctx.strokeStyle=palette.green;ctx.lineWidth=5;ctx.stroke();}
 if(rawTrail.length>1){path(rawTrail);ctx.strokeStyle=palette.text;ctx.globalAlpha=.65;ctx.lineWidth=3;ctx.stroke();ctx.globalAlpha=1;}
 rawEntries.forEach((entry,index)=>{if(entry.accepted!==false)return;const [x,y]=toScreen(rawTrail[index]);ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fillStyle=palette.red;ctx.fill();});
 if(matchedTrail.length>1){path(matchedTrail);ctx.strokeStyle=palette.green;ctx.lineWidth=3;ctx.stroke();}
 if(selectedRoute.length>1){path(selectedRoute);ctx.strokeStyle=palette.yellow;ctx.lineWidth=4;ctx.setLineDash([12,7]);ctx.stroke();ctx.setLineDash([]);}
 const labels=new Set();ctx.font='12px Segoe UI';
 const labelNames=localSource?.bbox?.[0]>21?['1905 Roku','Andrzeja Łukasika','Obrońców','Młodzianowska','Andrzeja Dowkontta','Aleja Józefa Grzecznarowskiego','Księcia Józefa Poniatowskiego','Władysława Beliny-Prażmowskiego']:['Stefana Banacha','Księcia Trojdena','Pruszkowska','Racławicka'];
 for(const f of mapData.features){const name=f.properties.name;if(!labelNames.includes(name)||labels.has(name))continue;const p=toScreen(f.projected[Math.floor(f.projected.length/2)]);if(p[0]<60||p[0]>w-100||p[1]<245||p[1]>h-100)continue;labels.add(name);ctx.lineWidth=4;ctx.strokeStyle=palette.bg;ctx.strokeText(name,p[0],p[1]-10);ctx.fillStyle=palette.muted;ctx.fillText(name,p[0],p[1]-10);}
 hitPoints=[];
 if(mode==='SIMULATION'&&state&&state.available&&state.signals.length){const end=state.signals.at(-1).road_position_m;
  for(const s of state.signals){const [x,y]=toScreen(demoLocation(s.road_position_m/end));hitPoints.push({x,y,id:s.signal_id});ctx.beginPath();ctx.arc(x,y,s.signal_id===selected?14:11,0,Math.PI*2);ctx.fillStyle=({GREEN:palette.green,RED:palette.red,YELLOW:palette.yellow,UNCERTAIN:palette.yellow})[s.state]||palette.muted;ctx.fill();ctx.lineWidth=s.signal_id===selected?4:2;ctx.strokeStyle=palette.panel;ctx.stroke();ctx.font='600 12px Segoe UI';ctx.textAlign='center';ctx.fillStyle=palette.panel;ctx.fillText(s.signal_id,x,y+4);ctx.textAlign='start';}
  const [x,y]=toScreen(demoLocation(state.position.road_position_m/end));ctx.beginPath();ctx.arc(x,y,22,0,Math.PI*2);ctx.fillStyle=palette.green;ctx.globalAlpha=.18;ctx.fill();ctx.globalAlpha=1;ctx.beginPath();ctx.arc(x,y,9,0,Math.PI*2);ctx.fillStyle=palette.green;ctx.fill();ctx.strokeStyle=palette.panel;ctx.lineWidth=3;ctx.stroke();ctx.font='12px Segoe UI';ctx.strokeStyle=palette.bg;ctx.lineWidth=4;ctx.strokeText('Sonda',x+25,y+4);ctx.fillStyle=palette.text;ctx.fillText('Sonda',x+25,y+4);
 }
 if(mode!=='SIMULATION'){
  const position=mode==='GPS_REPLAY'?gpsReplayState?.sample?.position:state?.external_position;
  if(position?.longitude!=null&&position?.latitude!=null){const projected=project([position.longitude,position.latitude]),[x,y]=toScreen(projected);const latRad=position.latitude*Math.PI/180;const radiusProjected=(position.gps_accuracy_m||0)/(6371008.8*Math.max(.1,Math.cos(latRad)));ctx.beginPath();ctx.arc(x,y,Math.max(3,radiusProjected*scale),0,Math.PI*2);ctx.fillStyle=palette.yellow;ctx.globalAlpha=.16;ctx.fill();ctx.globalAlpha=1;ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.fillStyle=palette.text;ctx.fill();ctx.strokeStyle=palette.panel;ctx.lineWidth=3;ctx.stroke();}
 const match=mode==='GPS_REPLAY'?gpsReplayState?.mapping:state?.mapping?.result;
  if(match?.accepted_longitude!=null&&match?.accepted_latitude!=null){const [x,y]=toScreen(project([match.accepted_longitude,match.accepted_latitude]));ctx.beginPath();ctx.arc(x,y,7,0,Math.PI*2);ctx.fillStyle=palette.green;ctx.fill();ctx.strokeStyle=palette.panel;ctx.stroke();}
  for(const [index,line] of (state?.mapping?.selected_route?.stop_lines||[]).entries()){path(line.coordinates.map(project));ctx.strokeStyle=line.stop_line_id===selectedRouteStop?palette.yellow:palette.red;ctx.lineWidth=line.stop_line_id===selectedRouteStop?7:5;ctx.stroke();const midpoint=project([(line.coordinates[0][0]+line.coordinates[1][0])/2,(line.coordinates[0][1]+line.coordinates[1][1])/2]);const [x,y]=toScreen(midpoint);hitPoints.push({x,y,id:line.stop_line_id});ctx.beginPath();ctx.arc(x,y,line.stop_line_id===selectedRouteStop?11:9,0,Math.PI*2);ctx.fillStyle=palette.red;ctx.fill();ctx.lineWidth=2;ctx.strokeStyle=palette.panel;ctx.stroke();ctx.font='600 10px Segoe UI';ctx.textAlign='center';ctx.fillStyle=palette.panel;ctx.fillText(String(index+1),x,y+3);ctx.textAlign='start';if(line.stop_line_id===selectedRouteStop){ctx.font='600 12px Segoe UI';ctx.strokeStyle=palette.bg;ctx.lineWidth=4;ctx.strokeText(line.source?.label||line.stop_line_id,x+14,y-11);ctx.fillStyle=palette.text;ctx.fillText(line.source?.label||line.stop_line_id,x+14,y-11);}}
  if(mode==='GPS_REPLAY'&&gpsReplayState?.endpoints){for(const [entry,label] of [[gpsReplayState.endpoints.start,'START'],[gpsReplayState.endpoints.end,'KONIEC']]){const [x,y]=toScreen(project([entry.longitude,entry.latitude]));ctx.beginPath();ctx.arc(x,y,6,0,Math.PI*2);ctx.fillStyle=label==='START'?palette.green:palette.red;ctx.fill();ctx.fillStyle=palette.text;ctx.fillText(label,x+9,y-7);}}
 }
}
new ResizeObserver(drawMap).observe($('map'));
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',drawMap);
async function initMap(){const responses=await Promise.all(['/map-data.json','/map-data/chomiczowka.json','/map-data/arkadia.json','/map-data/radom.json'].map(url=>fetch(url)));if(responses.some(response=>!response.ok))throw new Error('Nie udało się wczytać lokalnych map.');const maps=await Promise.all(responses.map(response=>response.json()));mapData=maps[0];mapData.features=maps.flatMap(item=>item.features);mapData.sources=maps.map(item=>item.metadata);mapData.features.forEach(f=>{f.projected=(f.geometry.type==='Polygon'?f.geometry.coordinates[0]:f.geometry.coordinates).map(project);});mapData.projectedRoute=mapData.demo_route.map(project);mapData.lengths=[0];for(let i=1;i<mapData.projectedRoute.length;i++){const a=mapData.projectedRoute[i-1],b=mapData.projectedRoute[i];mapData.lengths.push(mapData.lengths.at(-1)+Math.hypot(a[0]-b[0],a[1]-b[1]));}drawMap();}
async function poll(){if(!busy){try{await request('/api/state');if(replayState?.running){const response=await fetch('/api/replay/state',{cache:'no-store'});if(response.ok){replayState=await response.json();renderReplay();}}if(gpsReplayState?.running){const response=await fetch('/api/gps-replay/state',{cache:'no-store'});if(response.ok){gpsReplayState=await response.json();renderGpsReplay();drawMap();}}}catch(error){showError('Brak połączenia z aplikacją: '+error.message);$('target-value').textContent='—';$('target-range').textContent='Dane niedostępne';$('driving-action').textContent='Rekomendacja wycofana';}}setTimeout(poll,250);}
renderDisabled();initMap().catch(error=>showError(error.message));poll();
