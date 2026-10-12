'use strict';
// Browser adapter; unknown or stale inputs never produce a speed command.
function schoolGuidance(speed, limit, recommendation, eligible) {
 const r = recommendation;
 const finite = x => typeof x === 'number' && Number.isFinite(x);
 if (!eligible || !finite(speed) || speed < 0 || !finite(limit) || limit <= 0 || r?.status !== 'READY' || !['HOLD','ACCELERATE','BRAKE','COAST','ENGINE_BRAKE','STOP'].includes(r.action) ||
     ![r.target_kmh,r.range_min_kmh,r.range_max_kmh].every(finite) ||
     r.range_min_kmh < 0 || r.range_min_kmh > r.range_max_kmh || r.range_max_kmh > limit ||
     r.target_kmh < r.range_min_kmh || r.target_kmh > r.range_max_kmh) return null;
 return {range:[r.range_min_kmh,r.range_max_kmh], action:
  speed > limit || ['BRAKE','COAST','ENGINE_BRAKE','STOP'].includes(r.action) || speed > r.range_max_kmh + .8 ? 'Zwolnij' :
  speed < r.range_min_kmh - .8 && speed < limit ? 'Przyspiesz' : 'Utrzymaj prędkość'};
}
if (typeof module !== 'undefined') module.exports={schoolGuidance};
if (typeof document !== 'undefined') {
 const $ = id => document.getElementById(id);
 const el = (tag, value, className) => {const node=document.createElement(tag);if(value!=null)node.textContent=value;if(className)node.className=className;return node;};
 const names={DRIVER:'Kierowca',ANALYST:'Analityk',ADMIN:'Administrator',GREEN:'Zielone',RED:'Czerwone',YELLOW:'Żółte',UNKNOWN:'Nieznane',PLANNED:'Planowany',RECORDING:'Nagrywany',COMPLETE:'Zakończony'};
 const date = x => new Date(x*1000).toLocaleString('pl-PL');
 const fields = form => Object.fromEntries(new FormData(form));
 let user=null,csrf='',trips=[],observations=[],routes=[],snapshot=null,map=null,signals=[],view='navigation',lastUpdate=0,busy=false;
 function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
 async function api(path,data){
  const response=await fetch(path,{credentials:'same-origin',headers:data?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},method:data?'POST':'GET',body:data?JSON.stringify(data):undefined});
  const result=await response.json();
  if(!response.ok){if(response.status===401&&user){user=null;authView();}throw new Error(result.error||'Nie można wykonać operacji');}
  return result;
 }
 let actionQueue=Promise.resolve();
 function act(fn){actionQueue=actionQueue.then(async()=>{busy=true;try{await fn();}catch(e){notice(e.message,true);}finally{busy=false;}});return actionQueue;}
 function form(id,fn){$(id).addEventListener('submit',e=>{e.preventDefault();if($(id).reportValidity())act(()=>fn(fields($(id))));});}
 function authView(){ $('auth').hidden=!!user;$('portal').hidden=!user;$('account').hidden=!user; }
 function authTab(name){for(const key of ['login','register','request','reset'])$(key+'-form').hidden=key!==name;document.querySelectorAll('[data-auth]').forEach(n=>n.setAttribute('aria-pressed',String(n.dataset.auth===name)));}
 document.querySelectorAll('[data-auth]').forEach(n=>n.onclick=()=>authTab(n.dataset.auth));
 form('login-form',async data=>{await api('/school/api/login',data);await init();notice('Zalogowano.');});
 form('register-form',async data=>{const r=await api('/school/api/register',data);notice(r.message);$('register-form').reset();authTab('login');});
 form('request-form',async data=>notice((await api('/school/api/request-reset',data)).message));
 form('reset-form',async data=>{notice((await api('/school/api/reset-password',data)).message);history.replaceState(null,'','/');$('reset-form').reset();authTab('login');});
 $('logout').onclick=()=>act(async()=>{await api('/school/api/logout',{});user=null;csrf='';snapshot=null;authView();notice('Wylogowano.');});
 function setView(name){view=name;for(const key of ['navigation','trips','observations','admin'])$(key+'-view').hidden=key!==name;document.querySelectorAll('[data-view]').forEach(n=>n.setAttribute('aria-pressed',String(n.dataset.view===name)));}
 document.querySelectorAll('[data-view]').forEach(n=>n.onclick=()=>{setView(n.dataset.view);act(refresh);});
 function option(select,value,label){const o=el('option',label);o.value=value;select.append(o);}
 function cell(row,value,sub){const c=el('td',value);if(sub)c.append(el('small',sub));row.append(c);return c;}
 function button(parent,label,fn){const b=el('button',label);b.type='button';b.onclick=()=>act(fn);parent.append(b);}
 function empty(tbody,columns){if(!tbody.children.length){const row=el('tr');const c=cell(row,'Brak wyników. Utwórz przejazd lub zmień filtr.');c.colSpan=columns;c.className='empty';tbody.append(row);}}
 async function refresh(){
  if(!user)return;
  trips=await api('/school/api/trips?'+new URLSearchParams(fields($('trip-filter'))));
  observations=await api('/school/api/observations?'+new URLSearchParams(fields($('observation-filter'))));
  renderTrips();renderObservations();
  if(user.role==='ADMIN'&&view==='admin')await renderUsers();
 }
 function renderTrips(){
  const body=$('trip-rows');body.replaceChildren();
  for(const t of trips){const row=el('tr');cell(row,t.title,t.owner);cell(row,t.route_id);cell(row,date(t.created));cell(row,t.interrupted?'Przerwany zapis':names[t.status]||t.status);const actions=cell(row,'');
   if(t.owner_id===user.id||user.role==='ADMIN')button(actions,'Edytuj',()=>edit('Opis przejazdu',[{name:'title',label:'Nazwa',value:t.title,max:120},{name:'note',label:'Notatka',value:t.note,max:1000,optional:true}],async data=>{await api('/school/api/trips/update',{id:t.id,...data});await refresh();}));
   if(t.status==='COMPLETE'&&t.run_id){const a=el('a','Eksport ZIP');a.href='/school/api/export?id='+encodeURIComponent(t.id);actions.append(a);}
   body.append(row);
  }empty(body,5);
  // Navigation selector must not inherit table filters or other users' trips.
  refreshTripSelector();
 }
 async function refreshTripSelector(){try{const own=await api('/school/api/trips');const value=$('active-trip').value;$('active-trip').replaceChildren();for(const t of own.filter(t=>t.owner_id===user.id))option($('active-trip'),t.id,t.title+' • '+(t.interrupted?'Przerwany zapis':names[t.status]||t.status));if(own.some(t=>t.id===value&&t.owner_id===user.id))$('active-trip').value=value;await renderNavSignals();}catch(e){notice(e.message,true);}}
 function renderObservations(){
  const body=$('observation-rows');body.replaceChildren();
  for(const o of observations){const row=el('tr');cell(row,o.signal,o.trip);cell(row,o.owner,date(o.created));cell(row,names[o.state]);cell(row,names[o.effective_state],o.correction_count+' korekt');cell(row,o.kind==='STATE_START'?'Początek fazy':'Widziany kolor');const actions=cell(row,'');
   button(actions,'Koryguj',()=>edit('Korekta obserwacji',[{name:'state',label:'Kolor',value:o.effective_state,options:['GREEN','RED','YELLOW','UNKNOWN']},{name:'reason',label:'Powód',min:3,max:500}],async data=>{notice((await api('/school/api/corrections',{id:o.id,...data})).message);await refresh();}));
   button(actions,'Historia',async()=>{const rows=await api('/school/api/corrections?id='+encodeURIComponent(o.id));$('correction-history').replaceChildren(...rows.map(r=>el('p',`${names[r.state]} • ${r.actor} • ${date(r.created)}\n${r.reason}`)));if(!rows.length)$('correction-history').append(el('p','Brak korekt.'));$('history-dialog').showModal();});body.append(row);
  }empty(body,6);
 }
 async function renderUsers(){const rows=await api('/school/api/users');$('user-rows').replaceChildren();for(const u of rows){const row=el('tr');cell(row,u.name);cell(row,u.email);cell(row,names[u.role]);cell(row,u.active?'Aktywne':'Zablokowane');const actions=cell(row,'');button(actions,'Uprawnienia',()=>edit('Uprawnienia '+u.name,[{name:'role',label:'Rola',value:u.role,options:['DRIVER','ANALYST','ADMIN']},{name:'active',label:'Status',value:String(!!u.active),options:['true','false']}],async data=>{notice((await api('/school/api/users',{id:u.id,role:data.role,active:data.active==='true'})).message);await renderUsers();}));$('user-rows').append(row);}const requests=await api('/school/api/reset-requests');$('reset-requests').replaceChildren(...requests.map(r=>el('p',r.email+' • '+date(r.requested))));if(!requests.length)$('reset-requests').append(el('p','Brak próśb o reset.'));}
 let saveEdit;
 function edit(title,definitions,save){$('edit-title').textContent=title;$('edit-fields').replaceChildren();for(const f of definitions){const label=el('label',f.label),input=el(f.options?'select':f.name==='note'?'textarea':'input');input.name=f.name;input.required=!f.optional;if(f.options)for(const value of f.options)option(input,value,names[value]||({'true':'Aktywne','false':'Zablokowane'}[value])||value);else{input.maxLength=f.max||120;input.minLength=f.min||1;}input.value=f.value||'';label.append(input);$('edit-fields').append(label);}saveEdit=save;$('edit-dialog').showModal();}
 form('edit-form',async data=>{await saveEdit(data);$('edit-dialog').close();});$('cancel').onclick=()=>$('edit-dialog').close();$('close-history').onclick=()=>$('history-dialog').close();
 form('trip-filter',refresh);form('observation-filter',refresh);
 form('trip-form',async data=>{await api('/school/api/trips',data);$('trip-form').reset();notice('Dodano przejazd. Wybierz go w nawigacji.');await refresh();});
 form('passenger-form',async data=>{const trip_id=$('active-trip').value;if(!trip_id)throw new Error('Najpierw utwórz przejazd.');await api('/school/api/observations',{trip_id,...data});notice('Zapisano obserwację z czasem serwera.');await refresh();});
 for(const [id,command] of [['start-demo','start'],['start-live','live'],['pause','pause'],['finish','finish']])$(id).onclick=()=>act(async()=>{const trip_id=$('active-trip').value;if(!trip_id)throw new Error('Najpierw utwórz przejazd.');notice((await api('/school/api/navigation',{command,trip_id})).message);await refresh();await poll();});
 $('pair').onclick=()=>act(async()=>{const r=await api('/school/api/pair-code',{});$('pair-code').textContent='Kod: '+r.code+' • ważny 5 minut';});
 $('active-trip').onchange=()=>act(renderNavSignals);
 async function renderNavSignals(){
  const tid=$('active-trip').value,own=await api('/school/api/trips');const t=own.find(t=>t.id===tid);let rows=[];
  if(t?.route_id==='synthetic_s1_s5')rows=['S1','S2','S3','S4','S5'].map(id=>({id,name:id}));
  else if(snapshot?.mapping?.selected_route?.route_id===t?.route_id)rows=snapshot.mapping.selected_route.stop_lines.map(l=>({id:l.stop_line_id,name:l.source?.label||l.stop_line_id}));
  $('nav-signal').replaceChildren();for(const r of rows)option($('nav-signal'),r.id,r.name);
 }
 function gauge(speed,range){const ns='http://www.w3.org/2000/svg',point=(f,r)=>{const a=(-165+150*f)*Math.PI/180;return [210+r*Math.cos(a),230+r*Math.sin(a)];};$('gauge-bars').replaceChildren();$('gauge-labels').replaceChildren();for(let i=0;i<40;i++){const a=point(i/40,185),b=point((i+.6)/40,185),path=document.createElementNS(ns,'path');path.setAttribute('d',`M ${a} L ${b}`);path.setAttribute('class','gauge-bar'+(speed!=null&&i*80/40<=speed?' lit':'')+(range&&i*80/40>=range[0]&&i*80/40<=range[1]?' range':''));$('gauge-bars').append(path);}for(let i=0;i<=80;i+=10){const p=point(i/80,158),t=document.createElementNS(ns,'text');t.setAttribute('x',p[0]);t.setAttribute('y',p[1]);t.setAttribute('class','gauge-label');t.textContent=i;$('gauge-labels').append(t);}$('speed').textContent=speed==null?'—':Math.round(speed);}
 function navigation(stale=false){if(!snapshot)return;const s=snapshot,sim=s.view_mode==='SIMULATION';const fresh=!stale&&(sim||s.external_status?.live_control_eligible===true);const sample=sim?s.position:s.external_position;const speed=fresh&&Number.isFinite(sample?.speed_mps)?sample.speed_mps*3.6:null;const route=s.mapping?.selected_route,match=s.mapping?.result;const section=route?.speed_sections?.find(x=>x.start_s_m<=match?.accepted_s_m&&match.accepted_s_m<=x.end_s_m);const limit=sim?s.speed_limit_mps*3.6:section?.verification?.status==='FIELD_CHECKED'?section.limit_mps*3.6:null;
  const guide=schoolGuidance(speed,limit,sim?s.recommendation:s.mapping?.live_recommendation,fresh&&!s.incident&&(sim?s.available:s.mapping?.recommendation_eligibility?.allowed));
  gauge(speed,guide?.range);$('speed-limit').textContent=limit==null?'—':Math.round(limit);$('guidance').textContent=guide?.action||'Brak rekomendacji';$('range').textContent=guide?`${guide.range.map(x=>Math.round(x)).join('–')} km/h • ${sim?'tylko symulacja':'zweryfikowany model'}`:stale?'Utrata połączenia — wskazania wygasły':sim?'Brak wiarygodnego rozwiązania':'Fazy, geometria, limity i GPS wymagają weryfikacji';
  $('route-title').textContent=sim?'Trasa demonstracyjna S1–S5':route?.name||'Wybierz przejazd GPS';$('data-source').textContent=sim?'Dane syntetyczne • punkty umowne na mapie OSM':'Android GPS • stany świateł niepotwierdzone';$('gps-status').textContent=stale?'Utrata połączenia':sim?'Symulacja • '+(s.running?'w ruchu':'pauza'):'GPS: '+(s.external_status?.freshness_status||'brak danych');
  signals=sim?s.signals.filter(x=>!x.passed).map(x=>({id:x.signal_id,name:x.name,state:stale?'UNKNOWN':x.state,distance:x.distance_m,position:x.road_position_m})): (route?.stop_lines||[]).filter(x=>match?.accepted_s_m==null||x.s_m>=match.accepted_s_m).map(x=>({id:x.stop_line_id,name:x.source?.label||x.stop_line_id,state:'UNKNOWN',distance:match?.accepted_s_m==null?null:x.s_m-match.accepted_s_m,coords:[(x.coordinates[0][0]+x.coordinates[1][0])/2,(x.coordinates[0][1]+x.coordinates[1][1])/2]}));
  $('next-signals').replaceChildren(...signals.slice(0,5).map(x=>{const row=el('div',null,'signal-row');row.append(el('span',null,'signal-dot '+x.state));const copy=el('span',x.name,'signal-copy');copy.append(el('small',(names[x.state]||x.state)+' • '+(sim?'prognoza syntetyczna':'brak zweryfikowanej fazy')));row.append(copy,el('span',x.distance==null?'—':Math.round(x.distance)+' m','signal-distance'));return row;}));drawMap();
 }
 function interpolate(line,fraction){const lengths=[0];for(let i=1;i<line.length;i++){const a=line[i-1],b=line[i];lengths.push(lengths[i-1]+Math.hypot((b[0]-a[0])*Math.cos(a[1]*Math.PI/180),b[1]-a[1]));}const target=Math.max(0,Math.min(1,fraction))*lengths.at(-1);let i=1;while(i<line.length-1&&lengths[i]<target)i++;const part=(target-lengths[i-1])/(lengths[i]-lengths[i-1]||1);return [line[i-1][0]+(line[i][0]-line[i-1][0])*part,line[i-1][1]+(line[i][1]-line[i-1][1])*part];}
 function drawMap(){if(!map||!snapshot)return;const canvas=$('road-map'),box=canvas.getBoundingClientRect();if(!box.width||!box.height)return;const dpr=devicePixelRatio||1;canvas.width=box.width*dpr;canvas.height=box.height*dpr;const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);const w=box.width,h=box.height;ctx.fillStyle='#172f2b';ctx.fillRect(0,0,w,h);
  const sim=snapshot.view_mode==='SIMULATION',route=sim?map.demo_route:snapshot.mapping?.selected_route?.coordinates||[];const end=Math.max(...snapshot.signals.map(x=>x.road_position_m||0),1);const origin=sim?interpolate(route,snapshot.position.road_position_m/end):(snapshot.external_position?[snapshot.external_position.longitude,snapshot.external_position.latitude]:route[0]);if(!origin)return;const heading=sim?Math.PI:(snapshot.external_position?.heading_deg||0)*Math.PI/180;
  const project=p=>{const dx=(p[0]-origin[0])*111195*Math.cos(origin[1]*Math.PI/180),dy=(p[1]-origin[1])*111195;const right=dx*Math.cos(heading)-dy*Math.sin(heading),forward=dx*Math.sin(heading)+dy*Math.cos(heading);const depth=1+forward/700;if(depth<.25||forward>4500||forward< -240)return null;const scale=h/650;return [w/2+right*scale/depth,h*.8-forward*scale*.65/depth];};
  function line(coords,colour,width,fill=false){ctx.beginPath();let begun=false;for(const p of coords){const q=project(p);if(!q){begun=false;continue;}if(!begun){ctx.moveTo(...q);begun=true;}else ctx.lineTo(...q);}ctx.strokeStyle=colour;ctx.lineWidth=width;if(fill){ctx.fillStyle=colour;ctx.fill();}else ctx.stroke();}
  for(const f of map.features){if(f.geometry.type==='Polygon')line(f.geometry.coordinates[0],'#213d35',1,true);else if(f.geometry.type==='LineString')line(f.geometry.coordinates,'#36534a',f.properties.kind==='secondary'?8:3);}
  line(route,'#a7df86',7);line(route,'#d8edb6',2);
  ctx.font='11px Segoe UI';for(const x of signals){const coords=sim?interpolate(route,x.position/end):x.coords;const p=project(coords);if(!p||p[1]<140||p[1]>h-30)continue;ctx.beginPath();ctx.arc(...p,7,0,2*Math.PI);ctx.fillStyle={GREEN:'#8bc773',RED:'#ef8672',YELLOW:'#ecc871'}[x.state]||'#b5c0b4';ctx.fill();ctx.fillStyle='#e5f2d8';ctx.fillText(x.name.slice(0,28),p[0]+13,p[1]+4);}
  ctx.save();ctx.translate(w/2,h*.8);ctx.beginPath();ctx.moveTo(0,-18);ctx.lineTo(13,12);ctx.lineTo(0,7);ctx.lineTo(-13,12);ctx.closePath();ctx.fillStyle='#fff';ctx.shadowColor='#9cea85';ctx.shadowBlur=18;ctx.fill();ctx.restore();
 }
 async function poll(){if(!user||view!=='navigation')return;try{snapshot=await api('/school/api/navigation');lastUpdate=performance.now();navigation();}catch(e){navigation(true);}}
 async function init(){const result=await api('/school/api/me');user=result.user;csrf=user.csrf;authView();$('who').textContent=user.name+' • '+names[user.role];$('scope').textContent=user.role==='DRIVER'?'Widoczne są wyłącznie Twoje dane.':'Wgląd we wszystkie dane • korekty z audytem';$('admin-tab').hidden=user.role!=='ADMIN';$('lab-link').hidden=user.role!=='ADMIN';$('mode-label').textContent=result.demo?'DEMO • WYŁĄCZNIE DANE SYNTETYCZNE':'TWÓJ PANEL';document.querySelector('.demo-hint').hidden=!result.demo;routes=await api('/school/api/routes');$('new-route').replaceChildren();for(const r of routes.filter(r=>r.status!=='DAMAGED'))option($('new-route'),r.route_id,r.name);map=await api('/school/api/map');await refresh();await poll();}
 setInterval(()=>{if(user&&view==='navigation')poll();},750);setInterval(()=>{if(user&&view==='navigation'&&performance.now()-lastUpdate>2000)navigation(true);},500);window.addEventListener('resize',drawMap);
 const reset=location.hash.startsWith('#reset=')?location.hash.slice(7):'';if(reset){authTab('reset');$('reset-form').elements.token.value=reset;history.replaceState(null,'','/');}
 api('/health').then(r=>document.querySelector('.demo-hint').hidden=!r.demo).catch(()=>{});
 init().catch(e=>{if(!e.message.includes('Zaloguj'))notice(e.message,true);authView();});
}

