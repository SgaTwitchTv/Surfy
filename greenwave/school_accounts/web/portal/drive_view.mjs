import {el,notice} from './dom.mjs';
import {displayState,projectedRoad} from './driving.mjs';
const NS='http://www.w3.org/2000/svg';
const svg=(tag,attrs={},text)=>{const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;};
const colours={RED:'Czerwone',GREEN:'Zielone',YELLOW:'Żółte',UNKNOWN:'Nieznane',RED_YELLOW:'Czerwono-żółte'};
export function driveView(panel) {
 const box=el('section','','drive-view'),head=el('div','','drive-heading'),badge=el('span','','drive-badge'),connection=el('span');head.append(badge,connection);
 const grid=el('div','','drive-grid'),map=svg('svg',{viewBox:'0 0 650 400',role:'img','aria-label':'Mapa nawigacyjna w perspektywie'}),mapBox=el('div','','drive-map');const orientation=el('p','','map-orientation');mapBox.append(map,orientation);
 const dashboard=el('div','','drive-dashboard'),gauge=svg('svg',{viewBox:'0 0 600 330',role:'img','aria-label':'Prędkościomierz'}),speed=svg('text',{x:300,y:250,'text-anchor':'middle',class:'drive-speed'}),unit=svg('text',{x:300,y:287,'text-anchor':'middle'},'km/h'),ticks=svg('g'),message=el('p','','drive-advice'),limit=el('p'),quality=notice(''),lights=el('ol','','drive-lights');
 dashboard.append(gauge,message,limit,quality);gauge.append(ticks,speed,unit);grid.append(mapBox,dashboard);box.append(head,grid,el('h4','Następne światła'),lights);panel.append(box);
 let previous='HOLD';
 function render(state,age=0) {
  const view=displayState(state,age,previous);previous=view.advice.action;
  badge.textContent=view.synthetic?'DEMO · dane syntetyczne':state?.is_mock||state?.quality?.diagnostic?.includes('lokalizację jako testową')?'TEST GPS · próbka diagnostyczna':'LIVE · pomiar telefonu';connection.textContent=view.connected?'Połączenie aktywne':'Stan nieświeży';
  speed.textContent=view.speed===null?'—':Math.round(view.speed);gauge.setAttribute('aria-label',`Prędkość ${view.speed===null?'nieznana':Math.round(view.speed)+' km/h'}`);
  ticks.replaceChildren();for(let n=0;n<=70;n+=2){const angle=(-155+n/70*130)*Math.PI/180,point=r=>[300+r*Math.cos(angle),310+r*Math.sin(angle)],a=point(260),b=point(n%10?250:240);ticks.append(svg('path',{d:`M ${a} L ${b}`,class:view.speed!==null&&n<=view.speed?'drive-tick lit':'drive-tick'}));if(n%10===0){const[x,y]=point(220);ticks.append(svg('text',{x,y,'text-anchor':'middle'},n));}}
  message.textContent=({ACCELERATE:'Przyspiesz',SLOW:'Zwolnij',STOP:'Zatrzymaj się',HOLD:'Utrzymuj prędkość',UNAVAILABLE:'Brak wiarygodnej rekomendacji'})[view.advice.action];
  if(view.advice.range)message.append(el('small',`${view.advice.range.map(v=>v.toFixed(0)).join('–')} km/h · ${view.synthetic?'obliczenie demo':'zakres dopuszczony przez backend'}`));
  limit.textContent=`Limit: ${view.limit===null?'niezweryfikowany':view.limit.toFixed(0)+' km/h'} · źródło prędkości: ${state?.speed_source??'brak'}`;
  quality.textContent=view.synthetic?'Symulacja M8. Obliczenia nie dotyczą rzeczywistej drogi.':(state?.quality?.diagnostic?.includes('lokalizację jako testową')?'Lokalizacja testowa odrzucona — nie steruje jazdą. ':'')+(view.reason||state?.quality?.state||'Brak danych');
  orientation.textContent=view.synthetic?'Schemat syntetyczny · kierunek jazdy w górę':state?.heading_deg===null?'Północ w górę · kierunek GPS nieznany':'Orientacja GPS · '+Math.round(state?.heading_deg??0)+'°';
  map.replaceChildren(svg('rect',{width:650,height:400,fill:'#111b23'}));lights.replaceChildren();
  const origin=state?.position;let signals=[];
  if(view.synthetic&&origin){
   const pos=origin.road_position_m;map.append(svg('path',{d:'M 80 400 L 280 20 L 370 20 L 580 400',fill:'#25363b'}),svg('path',{d:'M 325 20 L 325 400',stroke:'#c9f36b','stroke-width':5,'stroke-dasharray':'16 20'}));
   signals=(state.signals||[]).filter(s=>!s.passed).slice(0,5);
   for(const [index,s] of signals.entries()){const depth=1+Math.max(0,s.road_position_m-pos)/150,y=330-300*(1-1/depth);map.append(svg('circle',{cx:365,cy:y,r:index===0?14:Math.max(3,14/depth),fill:({RED:'#ff6868',GREEN:'#c9f36b',YELLOW:'#ffd263'})[s.truth_state]||'#8b9a9e'})) ;if(index===0)map.append(svg('text',{x:390,y:y+10,fill:'#eef3e9','font-size':25},s.name.split(' × ').at(-1)));}
   map.append(svg('path',{d:'M 325 310 L 308 345 L 342 345 Z',fill:'#c9f36b'}));
  } else if(origin?.latitude!==undefined&&origin?.longitude!==undefined){
   const route=state?.mapping?.selected_route,points=(route?.coordinates||[]).map(p=>projectedRoad(p,[origin.longitude,origin.latitude],state.heading_deg??0,650,400)).filter(Boolean);
   if(points.length>1)map.append(svg('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:'#c9f36b','stroke-width':7}));
   map.append(svg('path',{d:'M 325 300 L 308 336 L 342 336 Z',fill:'#c9f36b'}));
   signals=(route?.stop_lines||[]).filter(s=>s.s_m>=(state.mapping?.result?.accepted_s_m??Infinity)).slice(0,5).map(s=>({...s,name:s.source?.label||s.stop_line_id,truth_state:'UNKNOWN',distance_m:s.s_m-state.mapping.result.accepted_s_m}));
  } else map.append(svg('text',{x:325,y:200,'text-anchor':'middle',fill:'#eef3e9','font-size':30},'Brak pozycji — oczekiwanie na GPS'));
  for(const s of signals)lights.append(el('li',`${s.name} · ${Math.round(s.distance_m??0)} m · ${colours[s.truth_state]||'Nieznane'} · ${view.synthetic?'syntetyczny stan symulatora':'brak zweryfikowanej fazy'}`));
  if(!signals.length)lights.append(el('li','Brak kolejnych świateł w aktualnych danych.'));
 }
 return {render};
}
