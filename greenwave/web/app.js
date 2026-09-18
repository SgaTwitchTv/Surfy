'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="greenwave-token"]').content;
let state = null, selected = 'S1', mapData = null, busy = false, queue = Promise.resolve();
let requestId = 0, displayedId = 0, historyKey = '', listSession = '', runsKey = '';
let replayState=null,replayRuns=[];
const colours = {GREEN:'Zielone',YELLOW:'Żółte',RED:'Czerwone',UNKNOWN:'Stan nieznany',UNCERTAIN:'Blisko zmiany fazy'};
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
function renderDisabled() {
 document.querySelectorAll('.server-action').forEach(control=>control.disabled=busy || !state);
 if(state){$('play').disabled=busy || !state.available || state.position.road_position_m>=state.signals.at(-1).road_position_m;
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
for(const [button,colour] of [['green','GREEN'],['yellow','YELLOW'],['red','RED']]) {
 $(button).addEventListener('click',()=>{
  const point=selected, kind=$('kind').value;
  action('/api/observe',{signal_id:point,state:colour,event_type:kind},
   `Przyjęto ${point}: ${colours[colour]}. ${kind==='STATE_START'?'Prognoza została ponownie oceniona.':'Zapisano aktualnie widoczny kolor, bez przesuwania początku fazy.'}`);
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
 if(!$('runs').open&&!$('replay').open&&!$('analysis').open)return;
 const key=(r.run_id||'')+':'+(r.records||0)+':'+r.active;if(key===runsKey)return;runsKey=key;
 fetch('/api/runs',{cache:'no-store'}).then(x=>x.json()).then(runs=>{
  const list=$('run-list');list.replaceChildren();
  replayRuns=runs.filter(run=>run.status==='COMPLETED');for(const id of ['replay-run','analysis-run','gps-baseline','gps-candidate'])$(id).replaceChildren();replayRuns.forEach(run=>{const option=document.createElement('option');option.value=run.run_id;const started=run.start_time?new Date(run.start_time).toLocaleString('pl-PL'):'—';option.textContent=`${started} · ${run.external_samples??0} GPS · ${run.run_id.slice(0,8)}`;for(const id of ['replay-run','analysis-run','gps-baseline','gps-candidate'])$(id).append(option.cloneNode(true));});if(replayRuns.length>1)$('gps-candidate').selectedIndex=replayRuns.length-1;
  if(!runs.length){list.textContent='Brak zapisanych przejazdów.';return;}
  for(const run of runs){const row=document.createElement('p');row.className='run-row';const label=document.createElement('span');const started=run.start_time?new Date(run.start_time).toLocaleString('pl-PL'):'—';label.textContent=`${started} · ${run.corridor_id} · ${run.status} · ${run.records??'—'} rekordów · ${run.external_samples??'—'} GPS`;row.append(label);if(run.status==='COMPLETED'){const link=document.createElement('button');link.type='button';link.textContent='Pobierz ZIP';link.addEventListener('click',async()=>{try{const response=await fetch('/api/runs/'+run.run_id+'.zip',{headers:{'X-GreenWave-Token':token}});if(!response.ok)throw new Error('Eksport nagrania nie powiódł się.');const blob=await response.blob();const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download='greenwave-'+run.run_id+'.zip';anchor.click();URL.revokeObjectURL(url);}catch(error){showError(error.message);}});row.append(' ',link);}list.append(row);}
 }).catch(()=>{});
}
async function replayRequest(command,value){if(!state)return;const response=await fetch('/api/replay',{method:'POST',headers:{'Content-Type':'application/json','X-GreenWave-Token':token},body:JSON.stringify({session_id:state.session_id,command,value})});const result=await response.json();if(!response.ok)throw new Error(result.error||'Replay error');replayState=result;renderReplay();}
function renderReplay(){if(!replayState)return;$('replay-time').textContent=`${fmt(replayState.model_seconds)} / ${fmt(replayState.duration)} s`;$('replay-seek').max=replayState.duration;$('replay-seek').value=replayState.model_seconds;$('replay-status').textContent=replayState.loaded?`${replayState.run_id.slice(0,8)} · ${replayState.running?'odtwarzanie':'pauza'} · ${replayState.event||'—'} · ${replayState.position==null?'—':fmt(replayState.position,1)+' m'}`:'Wybierz zakończone nagranie.';}
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
function render() {
 const phone=state.external_position, connection=state.external_status;
 const quality={GOOD:'dobra',FAIR:'średnia',POOR:'ograniczona',UNUSABLE:'zbyt słaba',UNKNOWN:'nieznana',MISSING:'brak pozycji'};
 const speedSource={DEVICE:'telefon',CALCULATED:'wyliczona z GPS',STATIONARY_FILTER:'potwierdzony postój',UNAVAILABLE:'brak'};
 $('phone-status').textContent=!connection?'Uruchom ponownie serwer, aby włączyć status GPS.':connection.state==='WAITING'?'Oczekiwanie na telefon':connection.state==='STALE'?'Brak nowych próbek telefonu':connection.usable_for_live?'Odbieram dane · próbka gotowa do użycia':'Odbieram dane · próbka tylko diagnostyczna';
 $('phone-values').textContent=phone?`GPS: ${fmt(phone.latitude,6)}, ${fmt(phone.longitude,6)}\nPrędkość końcowa: ${fmt(phone.speed_mps==null?null:phone.speed_mps*3.6)} km/h · źródło: ${speedSource[phone.speed_source]||phone.speed_source}\nSurowa: ${fmt(phone.raw_speed_mps==null?null:phone.raw_speed_mps*3.6)} km/h · wyliczona: ${fmt(phone.calculated_speed_mps==null?null:phone.calculated_speed_mps*3.6)} km/h\nDokładność: ${fmt(phone.gps_accuracy_m)} m · jakość: ${quality[phone.position_quality]||phone.position_quality} · kierunek: ${fmt(phone.heading_deg)}°\nOd odbioru: ${fmt(connection?.age_seconds)} s · odstęp próbek: ${fmt(connection?.sample_interval_seconds)} s\nOdebrano: ${connection?.received_count??'—'} · użyteczne: ${connection?.usable_count??'—'} · odrzucone jakościowo: ${connection?.quality_rejected_count??'—'}\n${connection?.diagnostic||''}`:'Brak pomiarów';
 $('dataset').value=state.dataset;$('jitter').checked=state.jitter;
 if(phone)$('phone-values').textContent+=`\nŹródło lokalizacji: ${phone.source}${phone.device_id?' · '+phone.device_id.slice(0,8):''} · transmisje: ${connection?.transmission_count??'—'} · duplikaty: ${connection?.duplicate_count??'—'}`;
 $('play').textContent=state.running?'Pauza':'Start';$('rate').value=String(state.rate);
 $('follow').checked=state.follow_recommendation;
 renderRecommendation();
 if(document.activeElement!==$('speed')){$('speed').value=state.speed_setting_kmh;$('speed-value').textContent=fmt(state.speed_setting_kmh,0)+' km/h';}
 $('current-speed').textContent=state.available?fmt(state.position.speed_mps*3.6,0):'—';
 $('limit').textContent=state.speed_limit_mps==null?'?':fmt(state.speed_limit_mps*3.6,0);
 $('warning').textContent=state.available?'DANE SYNTETYCZNE: czasy, odległości i limit są testowe. Punkty S1–S5 rozmieszczono przykładowo na mapie — nie są zweryfikowanymi liniami zatrzymania.':'DANE NIEZWERYFIKOWANE: brak faz, geometrii i limitu. Mapa pokazuje okolicę; pozycja i znaczniki punktów są wyłączone. Obserwacje używają czasu UTC.';
 const next=state.signals.find(s=>!s.passed);
 $('next-signal').textContent=state.available?(next?`Następny: ${next.signal_id} · ${shortName(next.name)}`:'Koniec trasy testowej'):'Brak zweryfikowanej pozycji';
 $('position').textContent=state.available?`Pozycja sondy ${fmt(state.position.road_position_m,0)} m`:'Symulacja pozycji wyłączona';
 $('session').textContent=`Sesja ${state.session_id.slice(0,8)} · ${state.running?'symulacja działa':'symulacja zatrzymana'}`;
 $('time').textContent=`Czas modelu ${fmt(state.model_time)} s · ${state.timebase==='SIMULATION'?'symulacja':'od początku sesji UTC'}`;
 $('utc').textContent=`UTC ${state.utc.replace('T',' ').replace('+00:00','')}`;
 renderSignals();renderDebug();renderHistory();renderRuns();renderReplay();renderDisabled();drawMap();
}

const actions={HOLD:'Utrzymuj tempo',ACCELERATE:'Łagodnie przyspieszaj',COAST:'Puść gaz',ENGINE_BRAKE:'Hamuj silnikiem',BRAKE:'Hamuj',STOP:'Zatrzymaj się / czekaj'};
function renderRecommendation(){
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
canvas.addEventListener('pointerup',e=>{if(drag&&!drag.moved){const hit=hitPoints.find(p=>Math.hypot(e.offsetX-p.x,e.offsetY-p.y)<20);if(hit)selectSignal(hit.id);}drag=null;});
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
 const route=mapData.projectedRoute,xs=route.map(p=>p[0]),ys=route.map(p=>p[1]);
 const cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2;
 const scale=Math.min((w-110)/(Math.max(...xs)-Math.min(...xs)),(h-370)/(Math.max(...ys)-Math.min(...ys)))*zoom;
 const toScreen=p=>[(p[0]-cx)*scale+w*.48+panX,(p[1]-cy)*scale+(h+130)/2+panY];
 function path(points){ctx.beginPath();points.forEach((p,i)=>{const [x,y]=toScreen(p);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});}
 for(const feature of mapData.features){const polygon=feature.geometry.type==='Polygon';path(feature.projected);if(polygon){ctx.closePath();ctx.fillStyle=feature.properties.kind==='park'?palette.park:palette.block;ctx.fill();}else{ctx.strokeStyle=palette.road;ctx.lineWidth=['primary','secondary','tertiary'].includes(feature.properties.kind)?8:2.5;ctx.lineCap='round';ctx.stroke();}}
 path(route);ctx.strokeStyle=palette.green;ctx.lineWidth=5;ctx.stroke();
 const labels=new Set();ctx.font='12px Segoe UI';
 for(const f of mapData.features){const name=f.properties.name;if(!['Stefana Banacha','Księcia Trojdena','Pruszkowska','Racławicka'].includes(name)||labels.has(name))continue;const p=toScreen(f.projected[Math.floor(f.projected.length/2)]);if(p[0]<60||p[0]>w-100||p[1]<245||p[1]>h-100)continue;labels.add(name);ctx.lineWidth=4;ctx.strokeStyle=palette.bg;ctx.strokeText(name,p[0],p[1]-10);ctx.fillStyle=palette.muted;ctx.fillText(name,p[0],p[1]-10);}
 hitPoints=[];
 if(state&&state.available){const end=state.signals.at(-1).road_position_m;
  for(const s of state.signals){const [x,y]=toScreen(demoLocation(s.road_position_m/end));hitPoints.push({x,y,id:s.signal_id});ctx.beginPath();ctx.arc(x,y,s.signal_id===selected?14:11,0,Math.PI*2);ctx.fillStyle=({GREEN:palette.green,RED:palette.red,YELLOW:palette.yellow,UNCERTAIN:palette.yellow})[s.state]||palette.muted;ctx.fill();ctx.lineWidth=s.signal_id===selected?4:2;ctx.strokeStyle=palette.panel;ctx.stroke();ctx.font='600 12px Segoe UI';ctx.textAlign='center';ctx.fillStyle=palette.panel;ctx.fillText(s.signal_id,x,y+4);ctx.textAlign='start';}
  const [x,y]=toScreen(demoLocation(state.position.road_position_m/end));ctx.beginPath();ctx.arc(x,y,22,0,Math.PI*2);ctx.fillStyle=palette.green;ctx.globalAlpha=.18;ctx.fill();ctx.globalAlpha=1;ctx.beginPath();ctx.arc(x,y,9,0,Math.PI*2);ctx.fillStyle=palette.green;ctx.fill();ctx.strokeStyle=palette.panel;ctx.lineWidth=3;ctx.stroke();ctx.font='12px Segoe UI';ctx.strokeStyle=palette.bg;ctx.lineWidth=4;ctx.strokeText('Sonda',x+25,y+4);ctx.fillStyle=palette.text;ctx.fillText('Sonda',x+25,y+4);
 }
}
new ResizeObserver(drawMap).observe($('map'));
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',drawMap);
async function initMap(){const response=await fetch('/map-data.json');if(!response.ok)throw new Error('Nie udało się wczytać mapy.');mapData=await response.json();mapData.features.forEach(f=>{f.projected=(f.geometry.type==='Polygon'?f.geometry.coordinates[0]:f.geometry.coordinates).map(project);});mapData.projectedRoute=mapData.demo_route.map(project);mapData.lengths=[0];for(let i=1;i<mapData.projectedRoute.length;i++){const a=mapData.projectedRoute[i-1],b=mapData.projectedRoute[i];mapData.lengths.push(mapData.lengths.at(-1)+Math.hypot(a[0]-b[0],a[1]-b[1]));}drawMap();}
async function poll(){if(!busy){try{await request('/api/state');if(replayState?.running){const response=await fetch('/api/replay/state',{cache:'no-store'});if(response.ok){replayState=await response.json();renderReplay();}}}catch(error){showError('Brak połączenia z aplikacją: '+error.message);$('target-value').textContent='—';$('target-range').textContent='Dane niedostępne';$('driving-action').textContent='Rekomendacja wycofana';}}setTimeout(poll,250);}
renderDisabled();initMap().catch(error=>showError(error.message));poll();
