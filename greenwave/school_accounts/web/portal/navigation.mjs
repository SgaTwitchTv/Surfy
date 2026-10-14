import {el,action,notice} from './dom.mjs';
import {labels} from './validation.mjs';
import {driveView} from './drive_view.mjs';
export function navigationView(records,trip,container) {
  const app=records.app,panel=el('div','','recording-panel');container.append(panel);
  panel.append(el('h3','Nawigacja · symulacja demonstracyjna'),notice('Syntetyczny zapis testowy M8. Bez telefonu i kamery; obliczenia dotyczą wyłącznie zestawu demo.'));
  const display=driveView(panel);let lastState=null,received=0;
  const diagnostics=el('details'),summary=el('summary','Laboratorium · szczegóły jakości GPS'),diagnosticText=el('pre');diagnostics.append(summary,diagnosticText);container.append(diagnostics);
  const freshness=setInterval(()=>{if(!panel.isConnected||epoch!==app.state.epoch){clearInterval(freshness);return;}if(lastState)display.render(lastState,performance.now()-received);},300);
  let device=null;
  if(trip.mode==='LIVE'){panel.firstElementChild.textContent='Nawigacja · GPS telefonu';panel.children[1].textContent='Dane GPS z autoryzowanego telefonu. Bez zweryfikowanych faz, linii i limitów nie pokazujemy rady live.';panel.append(notice('Telefon wymaga wcześniejszego parowania z tej sesji. Brak danych nie daje rekomendacji live.'));if(app.state.value.demo){panel.append(notice('LIVE wymaga profilu HTTPS. Demo HTTP używa symulacji.'));return;}const devices=document.createElement('select');devices.setAttribute('aria-label','Własny sparowany telefon');panel.append(devices);app.api.request('/devices').then(result=>{if(!panel.isConnected)return;for(const d of result.items.filter(d=>d.status==='ACTIVE')){const option=el('option',d.label);option.value=d.id;devices.append(option);}device=devices.value;});devices.addEventListener('change',()=>device=devices.value);}
  const status=notice(labels[trip.status]),buttons=el('div','','actions');panel.append(status,buttons);
  const epoch=app.state.epoch,serial=records.serial;
  function render() {
    buttons.replaceChildren();const nav=records.navigation.get(trip.id);
    if(trip.status==='PLANNED'||(!nav&&['STARTING','RECORDING'].includes(trip.status)&&records.operations.entries.has('start:'+trip.id)))buttons.append(action(trip.status==='PLANNED'?(trip.mode==='LIVE'?'Rozpocznij zapis GPS':'Rozpocznij zapis syntetyczny'):'Ponów ten sam start (wynik nieznany)',async()=>{
      const body={trip_id:trip.id,...(trip.mode==='LIVE'?{device_id:device}:{})},key=records.operations.key('start:'+trip.id,body),button=buttons.querySelector('button');button.disabled=true;
      try {const data=await app.api.request('/navigation',{method:'POST',body,key});records.navigation.set(trip.id,data);records.detail(trip.id);}
      catch(error){app.fail(error);status.textContent='Start niepotwierdzony. Nie wysyłaj nowego klucza; odśwież stan lub ponów tę samą operację.';button.disabled=false;}
    },'primary'));
    else if(nav&&['RECORDING','FINALIZING'].includes(trip.status))buttons.append(action('Zakończ zapis',async()=>{
      const name='finish:'+nav.id,existing=records.operations.entries.get(name),body=existing?.body||{command:'FINISH',expected_revision:nav.revision};
      const key=records.operations.key(name,body);records.operations.entries.get(name).body=body;const button=buttons.querySelector('button');button.disabled=true;
      try {await app.api.request('/navigation/'+nav.id+'/control',{method:'POST',body,key});records.operations.done(name);records.navigation.delete(trip.id);records.detail(trip.id);app.message('Zapis zakończony i sprawdzony.');}
      catch(error){app.fail(error);button.disabled=false;if(error.status===409){status.textContent='Konflikt stanu lub rewizji. Wczytaj aktualny stan przed nowym żądaniem.';buttons.append(action('Sprawdź aktualną rewizję finalizacji',async()=>{try{const current=await app.api.request('/navigation/'+nav.id);status.textContent=labels[current.status]+' · rewizja '+current.revision;buttons.append(action('Potwierdź użycie aktualnej rewizji',()=>{records.navigation.set(trip.id,current);records.operations.done(name);records.detail(trip.id);}));}catch(readError){app.fail(readError);}}));}else status.textContent='Nieznany wynik finalizacji. Ponów identyczne żądanie lub odśwież stan.';}
    },'primary'));
    else if(['STARTING','RECORDING','FINALIZING'].includes(trip.status))panel.append(notice('Brak uchwytu tej sesji. Nie można wznowić dawnego runu. Wylogowanie kończy zapis po stronie serwera; po przerwaniu utwórz nowy przejazd.'));
    else if(trip.status==='INTERRUPTED')panel.append(notice('Zapis przerwany. Utwórz nowy planowany przejazd; starego runu nie wznawiamy.'));
  }
  render();const initial=records.navigation.get(trip.id);if(initial){lastState=initial;received=performance.now();display.render(initial);}
  async function poll() {
    if(epoch!==app.state.epoch||serial!==records.serial||!panel.isConnected)return;
    const nav=records.navigation.get(trip.id);if(!nav)return;
    try {const data=await app.api.request('/navigation/'+nav.id);if(epoch!==app.state.epoch||serial!==records.serial||!panel.isConnected)return;records.navigation.set(trip.id,data);status.textContent=labels[data.status];lastState=data;received=performance.now();display.render(data);diagnosticText.textContent=JSON.stringify({quality:data.quality,eligibility:data.eligibility,match:data.mapping?.result},null,2);nav.revision=data.revision;
      if(data.mode==='SIMULATION'&&!buttons.querySelector('[data-pause]')){const pause=action('Pauza / wznowienie',async()=>{pause.disabled=true;try{const current=records.navigation.get(trip.id);const updated=await app.api.request('/navigation/'+current.id+'/control',{method:'POST',body:{command:current.running?'PAUSE':'RESUME',expected_revision:current.control_revision}});records.navigation.set(trip.id,updated);lastState=updated;received=performance.now();display.render(updated);}catch(e){app.fail(e);}finally{pause.disabled=false;}});pause.dataset.pause='true';buttons.append(pause);}
      if(!['RECORDING','FINALIZING','STARTING'].includes(data.status)){records.navigation.delete(trip.id);records.operations.done('finish:'+nav.id);records.detail(trip.id);return;}}
    catch(error){if(epoch!==app.state.epoch||serial!==records.serial)return;app.fail(error);records.navigation.delete(trip.id);lastState=null;display.render(null,Infinity);status.textContent='Kontekst niedostępny. Nie wznawiamy nagrania.';return;}
    records.timer=setTimeout(poll,700);
  }
  if(records.navigation.has(trip.id)&&['STARTING','RECORDING','FINALIZING'].includes(trip.status))records.timer=setTimeout(poll,700);
}
