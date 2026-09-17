(() => {
 'use strict';
 const el=id=>document.getElementById(id);
 const token=document.querySelector('meta[name="greenwave-token"]').content;
 let watch=null, sent=0, busy=false, generation=0, wakeLock=null, lastGpsAt=null;
 const format=(v,d=1)=>v==null?'brak pomiaru':Number(v).toFixed(d);
 const speedLabel={DEVICE:'telefon',CALCULATED:'wyliczona z GPS',STATIONARY_FILTER:'potwierdzony postój',UNAVAILABLE:'brak'};
 const qualityLabel={GOOD:'dobra',FAIR:'średnia',POOR:'ograniczona',UNUSABLE:'zbyt słaba',UNKNOWN:'nieznana',MISSING:'brak pozycji'};
 const message=text=>{el('status').textContent=text;};
 async function keepScreenAwake(){
  if(!('wakeLock' in navigator)||document.visibilityState==='hidden')return;
  try{wakeLock=await navigator.wakeLock.request('screen')}catch(_error){wakeLock=null}
 }
 function stop(){
  generation++;
  if(watch!==null)navigator.geolocation.clearWatch(watch);
  watch=null;lastGpsAt=null;
  if(wakeLock){wakeLock.release().catch(()=>{});wakeLock=null}
  el('start').disabled=false;el('stop').disabled=true;
 }
 async function transmit(position,run){
  if(busy||run!==generation)return;
  busy=true;
  const c=position.coords;
  const details='GPS: '+format(c.latitude,6)+', '+format(c.longitude,6)+'\nPrędkość surowa telefonu: '+format(c.speed==null?null:c.speed*3.6)+' km/h\nDokładność: '+format(c.accuracy)+' m\nKierunek: '+format(c.heading)+'°';
  el('measurements').textContent=details+'\nWysłano próbek: '+sent;
  try{
   const stateResponse=await fetch('/api/state',{cache:'no-store',signal:AbortSignal.timeout(5000)});
   if(!stateResponse.ok)throw Error('Odczyt sesji: HTTP '+stateResponse.status);
   const session=(await stateResponse.json()).session_id;
   if(run!==generation)return;
   const response=await fetch('/api/position',{method:'POST',signal:AbortSignal.timeout(5000),headers:{'Content-Type':'application/json','X-GreenWave-Token':token},body:JSON.stringify({session_id:session,timestamp_seconds:position.timestamp/1000,latitude:c.latitude,longitude:c.longitude,speed_mps:c.speed,heading_deg:c.heading,gps_accuracy_m:c.accuracy,acceleration_mps2:null,source:'WEB_GEOLOCATION'})});
   const result=await response.json();
   if(!response.ok)throw Error(result.error||('HTTP '+response.status));
   if(run!==generation)return;
   sent++;const processed=result.external_position||{}, status=result.external_status||{};
   message('GPS działa — komputer potwierdził odbiór '+sent+' próbek.');
   el('measurements').textContent=details+'\nPrędkość użyta: '+format(processed.speed_mps==null?null:processed.speed_mps*3.6)+' km/h ('+(speedLabel[processed.speed_source]||processed.speed_source||'brak')+')\nJakość pozycji: '+(qualityLabel[processed.position_quality]||processed.position_quality||'nieznana')+'\n'+(status.diagnostic||'')+'\nWysłano próbek: '+sent;
  }catch(error){if(run===generation)message('Błąd transmisji: '+error.message)}
  finally{busy=false}
 }
 el('start').addEventListener('click',()=>{
  message('Uruchamiam GPS — oczekiwanie na zgodę i pomiar…');
  if(!window.isSecureContext){message('GPS wymaga localhost przez USB lub HTTPS. Otwórz http://localhost:8765/mobile po adb reverse.');return}
  if(!navigator.geolocation){message('Przeglądarka nie udostępnia lokalizacji.');return}
  stop();const run=generation;
  el('start').disabled=true;el('stop').disabled=false;
  lastGpsAt=Date.now();keepScreenAwake();
  try{watch=navigator.geolocation.watchPosition(p=>{lastGpsAt=Date.now();return transmit(p,run)},error=>{if(run!==generation)return;stop();message('Błąd GPS: '+error.message+' Możesz ponowić pomiar.');},{enableHighAccuracy:true,maximumAge:0,timeout:15000})}
  catch(error){stop();message('Nie można uruchomić GPS: '+error.message)}
 });
 el('stop').addEventListener('click',()=>{stop();message('Pomiary zatrzymane.');});
 el('start').disabled=false;
 message('Gotowe — kliknij Uruchom pomiary.');
 if(typeof setInterval==='function')setInterval(()=>{if(watch!==null&&lastGpsAt!==null){const age=Math.floor((Date.now()-lastGpsAt)/1000);if(age>5)message('Brak nowej pozycji GPS od '+age+' s. Pozostaw ekran włączony i kartę na pierwszym planie.')}},1000);
 if(document.addEventListener)document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&watch!==null)keepScreenAwake()});
})();
