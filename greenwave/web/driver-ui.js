'use strict';
// UI adapter only. It never creates phase observations or relaxes backend gates.
(function(root) {
 const finite = value => typeof value === 'number' && Number.isFinite(value);
 function guidance({speed,limit,recommendation:r,eligible,previous='HOLD'}) {
  const blocked={action:'UNAVAILABLE',range:null,target:null};
  if(!eligible||!finite(speed)||speed<0||!finite(limit)||limit<=0||r?.status!=='READY')return blocked;
  if(!['HOLD','ACCELERATE','BRAKE','COAST','ENGINE_BRAKE','STOP'].includes(r.action))return blocked;
  const low=r.range_min_kmh,high=r.range_max_kmh,target=r.target_kmh;
  if(![low,high,target].every(finite)||low<0||low>high||target<low||target>high||high>limit)return blocked;
  let action='HOLD';
  const wide=high-low>=3,slowEnter=wide?high-.8:high+.8,slowExit=wide?high-1.5:high+.2;
  const accelerateEnter=wide?low+.8:low-.8,accelerateExit=wide?low+1.5:low-.2;
  if(r.action==='STOP'||high===0)action='STOP';
  else if(['BRAKE','COAST','ENGINE_BRAKE'].includes(r.action)||speed>limit||speed>=slowEnter||previous==='SLOW'&&speed>slowExit)action='SLOW';
  else if(low>0&&(speed<=accelerateEnter||previous==='ACCELERATE'&&speed<accelerateExit)&&speed<limit)action='ACCELERATE';
  return {action,range:[low,high],target};
 }
 function perspective(point,origin,bearing,width,height,zoom=1,latitude=52) {
  const metres=6371008.8*Math.cos(latitude*Math.PI/180),dx=(point[0]-origin[0])*metres,dy=(point[1]-origin[1])*metres;
  const angle=bearing*Math.PI/180,right=dx*Math.cos(angle)+dy*Math.sin(angle),forward=dx*Math.sin(angle)-dy*Math.cos(angle);
  const depth=1+forward/480;if(depth<.3||forward>2200||forward< -160)return null;
  const scale=height/520*zoom;
  return [width/2+right*scale/depth,height*.79-forward*scale*.63/depth];
 }
 const api={guidance,perspective};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(typeof document==='undefined')return;
 root.DriverUI=api;
 const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
 const number=(value,digits=0)=>finite(value)?value.toFixed(digits):'—';
 let bindings,screen='ui',zoom=1,command='HOLD',commandKey='',lastReceived=0,networkLost=true,bearing=0,bearingKey='',vision=[];
 let mapHits=[];
 const svg=(tag,attrs,text)=>{const node=document.createElementNS(NS,tag);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);if(text!=null)node.textContent=text;return node;};
 const colourNames={RED:'czerwone',GREEN:'zielone',YELLOW:'żółte',RED_YELLOW:'czerwono-żółte',OFF:'zgaszone',UNKNOWN:'nieznane',CONFLICT:'konflikt',UNCERTAIN:'niepewne'};
 function switchScreen(value) {
  screen=value;
  for(const name of ['ui','navigation','laboratory'])$('tab-'+name).setAttribute('aria-pressed',String(name===screen));
  $('driver-screen').hidden=screen!=='ui';$('navigation-screen').hidden=screen!=='navigation';$('vision-lab').hidden=screen!=='laboratory';
  document.querySelectorAll('.lab-only,main#app > details:not(#session-controls)').forEach(node=>node.hidden=screen!=='laboratory');
  $('session-controls').open=screen!=='ui';
  $('screen-description').textContent=({ui:'Mapa w perspektywie · ekran kierowcy',navigation:'Mapa z góry · odległości i obserwacje',laboratory:'GPS, kamera i historia · narzędzia diagnostyczne'})[screen];
  bindings?.redraw();render();if(screen==='laboratory')renderVision();
 }
 function context() {
  const state=bindings?.state();if(!state)return null;
  const mode=state.view_mode,sim=mode==='SIMULATION',replay=mode==='GPS_REPLAY',recording=bindings.replay();
  const sample=sim?state.position:replay?recording?.sample?.position:state.external_position;
  const match=replay?recording?.mapping:state.mapping?.result,route=state.mapping?.selected_route;
  const section=route?.speed_sections?.find(item=>finite(match?.accepted_s_m)&&item.start_s_m<=match.accepted_s_m&&match.accepted_s_m<=item.end_s_m);
  const age=performance.now()-lastReceived,connected=!networkLost&&age<1500;
  const fresh=sim?connected:!replay&&connected&&state.external_status?.live_control_eligible===true;
  const limit=sim?state.speed_limit_mps*3.6:section?.verification?.status==='FIELD_CHECKED'?section.limit_mps*3.6:null;
  const recommendation=sim?state.recommendation:state.mapping?.live_recommendation;
  const eligible=fresh&&!state.incident&&(sim?state.available===true:state.mapping?.recommendation_eligibility?.allowed===true);
  return {state,sim,replay,sample,match,route,fresh,connected,limit,recommendation,eligible,
   speed:fresh&&finite(sample?.speed_mps)?sample.speed_mps*3.6:null};
 }
 function renderGauge(speed,limit,range) {
  const maximum=Math.max(70,Math.min(160,Math.ceil((limit||50)/10)*10+20));
  const point=(fraction,radius)=>{const angle=(-155+130*fraction)*Math.PI/180;return [300+radius*Math.cos(angle),290+radius*Math.sin(angle)];};
  const segments=[];
  for(let i=0;i<45;i++){
   const from=point(i/45,245),to=point((i+.72)/45,245),value=(i+.5)/45*maximum;
   const zone=!range?'neutral':value<range[0]||value>range[1]?'outside':'optimal';
   segments.push(svg('path',{d:`M${from} L${to}`,class:`gauge-segment ${zone}${finite(speed)&&value<=speed?' lit':''}`}));
  }
  if(range){for(const [fraction,label] of [[range[0]/maximum,'MIN'],[range[1]/maximum,'MAX']]){const a=point(fraction,259),b=point(fraction,234);segments.push(svg('path',{d:`M${a} L${b}`,class:'gauge-boundary'}));}}
  if(range&&range[0]===range[1]){const [cx,cy]=point(range[0]/maximum,245);segments.push(svg('circle',{cx,cy,r:7,class:'gauge-target-point'}));}
  $('gauge-segments').replaceChildren(...segments);
  const ticks=[];for(let value=0;value<=maximum;value+=10){const [x,y]=point(value/maximum,215);ticks.push(svg('text',{x,y:y+4,'text-anchor':'middle',class:'gauge-tick'},value));}
  $('gauge-ticks').replaceChildren(...ticks);$('gauge-speed').textContent=number(speed);
  $('driver-gauge').setAttribute('aria-label',`Prędkość ${number(speed)} km/h. ${range?'Zalecany zakres '+range.join('–')+' km/h.':'Brak zalecanego zakresu.'}`);
 }
 function signalRows(c) {
  if(c.sim)return (c.state.signals||[]).filter(signal=>!signal.passed).map(signal=>({id:signal.signal_id,name:signal.name,
   distance:signal.road_position_m-c.state.position.road_position_m,state:signal.state,source:'Prognoza modelu · symulacja'}));
  return (c.route?.stop_lines||[]).filter(line=>!finite(c.match?.accepted_s_m)||line.s_m>=c.match.accepted_s_m).map(line=>{
   const last=(c.state.mapping?.route_observations||[]).findLast(event=>event.route_id===c.route.route_id&&event.stop_line_id===line.stop_line_id);
   return {id:line.stop_line_id,name:line.source?.label||line.stop_line_id,distance:finite(c.match?.accepted_s_m)?line.s_m-c.match.accepted_s_m:null,
    state:(c.fresh&&c.match?.status==='MATCHED'&&c.match?.direction==='FORWARD'?root.VisionWorkbenchUI?.signal(line.stop_line_id,c.route)?.state:null)||'UNKNOWN',source:(c.fresh&&c.match?.status==='MATCHED'&&c.match?.direction==='FORWARD'&&root.VisionWorkbenchUI?.signal(line.stop_line_id,c.route))?'Kamera · przypisanie ręczne · bez sterowania prędkością':last?`Historia: ${colourNames[last.state]||last.state} · ${last.timestamp_utc||last.timestamp||'czas w historii'}`:'Brak aktualnego źródła stanu',verification:line.verification?.status};
  });
 }
 function renderSignals(c) {
  $('driver-route-name').textContent=c.sim?'Punkty syntetyczne na trasie demo':c.route?.name||c.route?.route_id||'Wybierz trasę GPS u góry';
  const rows=signalRows(c),selection=bindings.selection();
  $('driver-signals').replaceChildren(...rows.slice(0,5).map(row=>{
   const button=document.createElement('button');button.type='button';button.className='signal';button.setAttribute('aria-pressed',String(selection===row.id));
   const dot=document.createElement('span');dot.className='dot';dot.dataset.state=row.state;dot.textContent=['UNKNOWN','CONFLICT'].includes(row.state)?'?':'';
   const content=document.createElement('span');content.className='signal-content';
   const heading=document.createElement('span');heading.className='signal-heading';
   const name=document.createElement('strong');name.textContent=row.name;const distance=document.createElement('span');distance.className='signal-distance';distance.textContent=number(row.distance)+' m';heading.append(name,distance);
   const source=document.createElement('div');source.className='signal-window';source.textContent=row.source;
   const status=document.createElement('div');status.className='signal-state';status.textContent=(colourNames[row.state]||row.state)+(row.verification?' · '+row.verification:'');content.append(heading,status,source);button.append(dot,content);
   button.addEventListener('click',()=>{bindings.select(row.id);render();});return button;
  }));
  if(!rows.length){const note=document.createElement('p');note.className='driver-source-note';note.textContent='Brak kolejnych punktów. Wybierz trasę lub wróć do początku odcinka.';$('driver-signals').append(note);}
  const chosen=(c.sim?c.state.signals:c.route?.stop_lines||[]).find(row=>(row.signal_id||row.stop_line_id)===selection);
  $('driver-selected').textContent='Obserwujesz: '+(chosen?.name||chosen?.source?.label||selection||'—');
  for(const color of ['green','yellow','red'])$('driver-'+color).disabled=document.getElementById(color).disabled;
  $('driver-kind').value=$('kind').value;$('driver-feedback').textContent=$('feedback').textContent;
 }
 function render() {
  const c=context();if(!c||!bindings)return;
  const key=[c.state.session_id,c.state.view_mode,c.route?.geometry_hash,c.recommendation?.signal_id,c.recommendation?.range_min_kmh,c.recommendation?.range_max_kmh].join(':');
  if(key!==commandKey){command='HOLD';commandKey=key;}
  const result=guidance({speed:c.speed,limit:c.limit,recommendation:c.recommendation,eligible:c.eligible,previous:command});command=result.action;
  renderGauge(c.speed,c.limit,result.range);
  $('driver-zone-legend').hidden=!result.range;
  const words={ACCELERATE:['↑','Przyspiesz'],SLOW:['↓','Zwolnij'],HOLD:['→','Utrzymuj'],STOP:['↓','Zatrzymaj się'],UNAVAILABLE:['—','Brak rekomendacji']};
  $('driver-command').dataset.action=command;$('driver-arrow').textContent=words[command][0];$('driver-command-label').textContent=words[command][1];
  $('driver-band').textContent=result.range?`Zakres ${result.range.join('–')} km/h · cel ${number(result.target)} · limit ${number(c.limit)} km/h`:'Zakres prędkości niedostępny';
  $('driver-mode').textContent=c.sim?'SYMULACJA · dane testowe':c.replay?'REPLAY · bez rekomendacji live':'TELEFON NA ŻYWO';
  $('driver-config-summary').textContent='· '+(c.sim?'Symulacja':c.replay?'Nagranie GPS':'Telefon na żywo')+(c.route?' · '+(c.route.name||c.route.route_id):'');
  $('driver-freshness').textContent=c.sim?'Sonda symulacji':c.replay?'Pozycja historyczna':c.fresh?`GPS FRESH · ${number(c.sample?.gps_accuracy_m)} m`:'GPS nieaktualny lub niezweryfikowany';
  $('driver-reason').textContent=!c.connected?'Brak świeżej odpowiedzi serwera — rekomendacja wycofana.':command!=='UNAVAILABLE'?(c.sim?'Wynik symulacji. Nie jest rekomendacją dla rzeczywistej jazdy.':'Rekomendacja backendu. Obowiązuje ograniczenie prędkości.'):c.replay?'Replay służy analizie, nie sterowaniu jazdą.':bindings.reason(c);
  renderSignals(c);if(screen==='ui')drawMap(c);
 }
 function palette() {
  const names=['bg','panel','text','muted','green','red','yellow','road','block','park','line'];const probe=$('driver-reason'),style=getComputedStyle(document.documentElement),result={};
  const old=probe.style.color;for(const name of names){probe.style.color=style.getPropertyValue('--'+name);result[name]=getComputedStyle(probe).color;}probe.style.color=old;return result;
 }
 function drawMap(c) {
  const data=bindings.map(),canvas=$('driver-map-canvas'),parent=canvas.parentElement,w=parent.clientWidth,h=parent.clientHeight;
  if(!w||!h)return;const dpr=window.devicePixelRatio||1;canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
  const p=palette();ctx.fillStyle=p.bg;ctx.fillRect(0,0,w,h);mapHits=[];if(!data)return;
  const project=bindings.project,route=c.sim?data.projectedRoute:(c.route?.coordinates||[]).map(project);
  const hasPosition=c.sim||finite(c.sample?.longitude)&&finite(c.sample?.latitude);
  const position=c.sim?bindings.demoLocation(c.state.position.road_position_m/(c.state.signals.at(-1)?.road_position_m||1)):
   finite(c.sample?.longitude)&&finite(c.sample?.latitude)?project([c.sample.longitude,c.sample.latitude]):route[0];
  if(!position){$('driver-map-status').textContent='Brak pozycji lub wybranej trasy';return;}
  const latitude=c.sample?.latitude??c.route?.coordinates?.[0]?.[1]??52;
  let desired=bearing,orientation='kierunek ostatnio znany';
  if(!c.sim&&c.fresh&&finite(c.sample.heading_deg)&&c.speed>3){desired=c.sample.heading_deg;orientation='kierunek GPS';}
  else if(route.length>1&&(c.sim||!hasPosition||c.match?.status==='MATCHED'&&c.match?.direction==='FORWARD')){
   let near=0,min=Infinity;for(let i=0;i<route.length-1;i++){const delta=Math.hypot(route[i][0]-position[0],route[i][1]-position[1]);if(delta<min){min=delta;near=i;}}
   const a=route[near],b=route[near+1];desired=Math.atan2(b[0]-a[0],-(b[1]-a[1]))*180/Math.PI;orientation='orientacja wybranej trasy';
  }
  const key=[c.state.session_id,c.state.view_mode,c.route?.geometry_hash].join(':');if(key!==bearingKey){bearingKey=key;bearing=desired;}else if(c.fresh||c.sim||c.replay)bearing+=(((desired-bearing)%360+540)%360-180)*.25;
  const screenPoint=point=>perspective(point,position,bearing,w,h,zoom,latitude);
  ctx.save();ctx.beginPath();ctx.rect(0,230,w,h-230);ctx.clip();
  function path(points,closed=false){const transformed=points.map(screenPoint);if(closed&&transformed.some(point=>!point))return false;ctx.beginPath();let moving=false;for(const point of transformed){if(!point){moving=false;continue;}if(moving)ctx.lineTo(...point);else ctx.moveTo(...point);moving=true;}if(closed)ctx.closePath();return transformed.some(Boolean);}
  const radius=2200/(6371008.8*Math.cos(latitude*Math.PI/180));
  for(const feature of data.features){if(!feature.projected.some(point=>Math.abs(point[0]-position[0])<radius&&Math.abs(point[1]-position[1])<radius))continue;const polygon=feature.geometry.type==='Polygon';if(!path(feature.projected,polygon))continue;if(polygon){ctx.fillStyle=feature.properties.kind==='park'?p.park:p.block;ctx.fill();}else{ctx.strokeStyle=p.road;ctx.lineWidth=['primary','secondary','tertiary'].includes(feature.properties.kind)?8:3;ctx.stroke();}}
  if(route.length&&path(route)){ctx.strokeStyle=p.green;ctx.lineWidth=6;ctx.lineJoin='round';ctx.stroke();}
  const rows=signalRows(c);for(const row of rows.slice(0,12)){
   const raw=c.sim?bindings.demoLocation(c.state.signals.find(signal=>signal.signal_id===row.id).road_position_m/(c.state.signals.at(-1)?.road_position_m||1)):
    (()=>{const coordinates=c.route.stop_lines.find(line=>line.stop_line_id===row.id).coordinates;return project([(coordinates[0][0]+coordinates[1][0])/2,(coordinates[0][1]+coordinates[1][1])/2]);})();
   const point=screenPoint(raw);if(!point||point[0]<30||point[0]>w-30||point[1]<240||point[1]>h-90)continue;const [x,y]=point;mapHits.push({x,y,id:row.id});
   ctx.fillStyle=p.panel;ctx.fillRect(x-10,y-25,20,47);ctx.strokeStyle=row.id===bindings.selection()?p.green:p.line;ctx.lineWidth=2;ctx.strokeRect(x-10,y-25,20,47);
   for(const [i,color] of ['RED','YELLOW','GREEN'].entries()){ctx.beginPath();ctx.arc(x,y-17+i*14,4,0,Math.PI*2);ctx.fillStyle=(row.state===color||row.state==='RED_YELLOW'&&['RED','YELLOW'].includes(color))?p[{RED:'red',YELLOW:'yellow',GREEN:'green'}[color]]:p.line;ctx.fill();}
   if(['UNKNOWN','UNCERTAIN','CONFLICT'].includes(row.state)){ctx.font='bold 14px Segoe UI';ctx.textAlign='center';ctx.fillStyle=p.text;ctx.fillText('?',x,y+6);}
   ctx.font='12px Segoe UI';ctx.textAlign=x>w/2?'right':'left';const labelX=x+(x>w/2?-17:17),available=x>w/2?labelX-10:w-labelX-10;
   let label=row.name;while(label.length>1&&ctx.measureText(label+'…').width>available)label=label.slice(0,-1);if(label!==row.name)label+='…';
   ctx.lineWidth=4;ctx.strokeStyle=p.bg;ctx.strokeText(label,labelX,y-9);ctx.fillStyle=p.text;ctx.fillText(label,labelX,y-9);
  }
  if(hasPosition){const x=w/2,y=h*.79;ctx.beginPath();ctx.moveTo(x,y-17);ctx.lineTo(x-11,y+12);ctx.lineTo(x,y+6);ctx.lineTo(x+11,y+12);ctx.closePath();ctx.fillStyle=c.sim||c.fresh?p.green:p.muted;ctx.fill();ctx.strokeStyle=p.panel;ctx.lineWidth=3;ctx.stroke();}ctx.restore();
  const coordinate=c.sim?null:c.sample;const covered=c.sim||(data.sources||[]).some(source=>source.bbox&&coordinate&&coordinate.longitude>=source.bbox[0]&&coordinate.longitude<=source.bbox[2]&&coordinate.latitude>=source.bbox[1]&&coordinate.latitude<=source.bbox[3]);
  $('driver-map-status').textContent=!hasPosition?'Brak pozycji · podgląd geometrii od początku trasy':`${!covered?'Brak lokalnego podkładu · ':''}${!c.sim&&!c.fresh?'Pozycja diagnostyczna · ':''}${orientation}`;
 }
 async function loadVision(){try{const response=await fetch('/api/vision-demos',{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);vision=await response.json();renderVision();}catch(error){$('vision-status').textContent='Nie udało się wczytać scenariuszy: '+error.message;}}
 function renderVision(){
  const demo=vision.find(item=>item.scenario===$('vision-scenario').value);if(!demo)return;
  const explanations={no_camera:'Brak kamery i śladów.',good_detection:'Przypisanie ręczne CONFIRMED; obserwacja pozostaje demonstracją.',multiple_lamps:'Dwa niezależne ślady; brak automatycznego wyboru lampy.',unknown_color:'Kolor UNKNOWN — wynik modelu nie potwierdza stanu.',conflict:'Konflikt lamp — nie wybieramy automatycznie zielonego.',lost_image:'Obraz utracony; ślad LOST nie potwierdza początku fazy.',stale_gps:'GPS STALE — brak świeżej pozycji.',wrong_direction:'REVERSE — przeciwny kierunek, brak przypisania do linii.',phone_disconnected:'Telefon rozłączony — transmisja niedostępna.'};
  $('vision-status').textContent=`DEMO · kamera ${demo.camera_status} · GPS ${demo.gps_status} · telefon ${demo.phone_status} · rekomendacja live ZABLOKOWANA. ${explanations[demo.scenario]||''}`;
  const canvas=$('vision-canvas'),w=canvas.parentElement.clientWidth||600,h=260;canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d'),p=palette();ctx.fillStyle=p.bg;ctx.fillRect(0,0,w,h);ctx.fillStyle=p.muted;ctx.font='14px Segoe UI';ctx.fillText(demo.detections.length?'Syntetyczne bbox — brak obrazu kamery':'Brak obrazu / wykryć',16,28);
  for(const envelope of demo.detections){const d=envelope.data,[x1,y1,x2,y2]=d.bbox_xyxy;ctx.strokeStyle=({GREEN:p.green,RED:p.red,YELLOW:p.yellow})[d.state]||p.muted;ctx.lineWidth=2;ctx.strokeRect(x1/d.frame.width*w,y1/d.frame.height*h,(x2-x1)/d.frame.width*w,(y2-y1)/d.frame.height*h);ctx.fillStyle=p.text;ctx.fillText(d.state,x1/d.frame.width*w,y1/d.frame.height*h-5);}
  $('vision-detections').replaceChildren(...demo.detections.map(envelope=>{const d=envelope.data,a=demo.associations.find(item=>item.data.track_id===d.track_id)?.data;const line=document.createElement('p');line.textContent=`${d.track_id} · ${colourNames[d.state]} · wynik modelu ${number(d.model_score,2)} · ${a?.status||'UNASSIGNED'} · ${a?.display_name||'bez przypisania'}`;return line;}));
 }
 api.mount=config=>{bindings=config;for(const value of ['ui','navigation','laboratory'])$('tab-'+value).addEventListener('click',()=>switchScreen(value));
  for(const color of ['green','yellow','red'])$('driver-'+color).addEventListener('click',()=>{$('kind').value=$('driver-kind').value;$(color).click();});
  $('driver-kind').addEventListener('change',()=>{$('kind').value=$('driver-kind').value;});$('vision-scenario').addEventListener('change',renderVision);
  $('driver-zoom-in').addEventListener('click',()=>{zoom=Math.min(3,zoom*1.25);render();});$('driver-zoom-out').addEventListener('click',()=>{zoom=Math.max(.5,zoom/1.25);render();});$('driver-center').addEventListener('click',()=>{zoom=1;render();});
  $('driver-map-canvas').addEventListener('click',event=>{const hit=mapHits.find(point=>Math.hypot(point.x-event.offsetX,point.y-event.offsetY)<28);if(hit){bindings.select(hit.id);render();}});
  new ResizeObserver(()=>{render();if(screen==='laboratory')renderVision();}).observe($('driver-screen'));matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{render();renderVision();});
  switchScreen('ui');loadVision();setInterval(()=>{if(networkLost||performance.now()-lastReceived>=1500)render();},300);
 };
 api.received=()=>{lastReceived=performance.now();networkLost=false;render();};api.disconnected=()=>{networkLost=true;command='HOLD';render();};api.render=render;
})(typeof window!=='undefined'?window:globalThis);
