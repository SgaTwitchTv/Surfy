import {el,action,notice,table} from './dom.mjs';
import {stamp} from './dates.mjs';
import {labels} from './validation.mjs';
import {editTrip,archiveTrip,shareTrip,revokeTrip,manualObservation,correctObservation} from './forms.mjs';
import {navigationView} from './navigation.mjs';
export async function tripDetail(records,id) {
  records.leave();const serial=records.serial,app=records.app;app.active='trips';app.menu();app.screen.replaceChildren(notice('Ładowanie przejazdu…'));
  let trip;try{trip=await app.api.request('/trips/'+id);}catch(error){if(serial===records.serial)app.screen.replaceChildren(notice('Nie udało się wczytać przejazdu.'),action('Powrót do przejazdów',()=>records.list('trips')));throw error;}if(serial!==records.serial)return;
  const screen=app.screen;screen.replaceChildren(el('p','Szczegóły własnego przejazdu','eyebrow'),el('h2',trip.title));
  const dl=el('dl');for(const [name,value] of [['ID',trip.id],['Notatka',trip.note||'Brak notatki'],['Utworzono',stamp(trip.created_at)],['Trasa',trip.route_version_id||'Bez trasy'],['Tryb',labels[trip.mode]],['Status',labels[trip.status]+(trip.archived_at?' · Archiwum':'')],['Rewizja',trip.revision],['Udostępnienie',trip.share?'Aktywne READ_ANALYZE':'Brak aktywnego udostępnienia']])dl.append(el('dt',name),el('dd',value));screen.append(dl);
  const actions=el('div','','actions');screen.append(actions);
  if(!trip.archived_at) {
    actions.append(action('Edytuj metadane',()=>editTrip(records,trip)));
    if(['PLANNED','COMPLETE','INTERRUPTED'].includes(trip.status))actions.append(action('Archiwizuj przejazd',()=>archiveTrip(records,trip)));
    if(['RECORDING','COMPLETE','INTERRUPTED'].includes(trip.status))actions.append(action(trip.status==='RECORDING'?'Obserwacja pasażera':'Adnotacja historyczna',()=>manualObservation(records,trip)));
    if(trip.status==='COMPLETE') {actions.append(action(trip.share?'Cofnij udostępnienie':'Udostępnij analitykowi',()=>trip.share?revokeTrip(records,trip):shareTrip(records,trip)));
      if(trip.capabilities.export)actions.append(action('Eksportuj przejazd',async()=>{try{await app.api.download('/trips/'+id+'/export');app.message('Pobieranie eksportu rozpoczęte. Serwer sprawdza integralność i uprawnienia.');}catch(error){app.fail(error);}}));}
    navigationView(records,trip,screen);
  }
  screen.append(action('Powrót do przejazdów',()=>records.list('trips')),el('h3','Obserwacje tego przejazdu'));
  const content=el('div'),feedback=notice(''),next=action('Więcej obserwacji',()=>load().catch(app.fail.bind(app)));screen.append(content,feedback,next);let cursor=null;
  async function load() {
    next.disabled=true;content.replaceChildren(notice('Ładowanie obserwacji…'));let result;try{result=await app.api.request('/observations',{query:{trip_id:id,limit:'25',...(cursor?{cursor}:{})}});}catch(error){if(serial===records.serial)content.replaceChildren(notice('Nie udało się wczytać obserwacji.'));throw error;}if(serial!==records.serial)return;
    content.replaceChildren(result.items.length?table(['Otrzymano','Sygnalizator','Kolor efektywny','Rodzaj','Historia'],result.items.map(o=>[stamp(o.server_received_at)+(o.historical?' · Historyczna':''),o.signal_id,labels[o.effective.state],labels[o.effective.event_type],action('Historia / korekta',()=>records.history(o))])):notice('Brak obserwacji.'));
    cursor=result.page.next_cursor;next.disabled=!cursor;feedback.textContent=cursor?'Dostępna kolejna strona.':'Koniec obserwacji.';
  }
  await load();
}
export async function findObservation(app,obs) {
  let cursor=null;do {const page=await app.api.request('/observations',{query:{trip_id:obs.trip_id,limit:'100',...(cursor?{cursor}:{})}});const found=page.items.find(o=>o.id===obs.id);if(found)return found;cursor=page.page.next_cursor;}while(cursor);
  throw new Error('Obserwacja niedostępna. Odśwież listę.');
}
export async function observationHistory(records,original) {
  records.leave();const serial=records.serial,app=records.app;app.active='observations';app.menu();app.screen.replaceChildren(notice('Ładowanie obserwacji…'));
  const obs=await findObservation(app,original);if(serial!==records.serial)return;
  const screen=app.screen;screen.replaceChildren(el('p','Oryginał i osobne korekty','eyebrow'),el('h2','Obserwacja · '+obs.signal_id));
  const dl=el('dl');for(const [name,value] of [['Otrzymano',stamp(obs.server_received_at)],['Zmierzono',stamp(obs.measured_at)],['Adnotacja',obs.historical?'Historyczna, bez dopisywania raw':'Zapis podczas jazdy'],['Źródło',labels[obs.source]],['Oryginał',labels[obs.original.state]+' / '+labels[obs.original.event_type]],['Efektywnie',labels[obs.effective.state]+' / '+labels[obs.effective.event_type]+' / '+(obs.effective.valid?'Ważna':'Nieważna')],['Rewizja korekt',obs.correction_revision],['Zapis zdarzenia',obs.historical?'Adnotacja w bazie, bez dopisywania logu':({APPLIED:'Potwierdzony w logu',PENDING:'W bazie; oczekuje zapisu w logu',FAILED:'W bazie; zapis do logu niepotwierdzony'}[obs.journaling_state])]])dl.append(el('dt',name),el('dd',value));screen.append(dl);
  screen.append(action('Dodaj korektę',()=>correctObservation(records,obs)),action('Szczegóły przejazdu',()=>records.detail(obs.trip_id)),el('h3','Historia korekt'));
  const content=el('div'),next=action('Następne korekty',()=>load().catch(app.fail.bind(app))),feedback=notice('');screen.append(content,next,feedback);let offset=0;
  async function load() {next.disabled=true;const data=await app.api.request('/observations/'+obs.id+'/corrections',{query:{limit:'25',offset:String(offset)}});if(serial!==records.serial)return;
    content.replaceChildren(data.items.length?table(['Nr','Autor · ID','Czas','Powód','Przed','Po'],data.items.map(c=>[c.sequence,c.actor_id,stamp(c.server_at),c.reason,labels[c.before.state]+' / '+labels[c.before.event_type]+' / '+(c.before.valid?'Ważna':'Nieważna'),labels[c.after.state]+' / '+labels[c.after.event_type]+' / '+(c.after.valid?'Ważna':'Nieważna')])):notice('Brak korekt.'));
    offset+=data.items.length;next.disabled=data.items.length<25||offset>10000;feedback.textContent=offset>10000?'Limit starszego API historii korekt. Dalszy odczyt wymaga osobnej integracji.':next.disabled?'Koniec historii korekt.':'Dostępna kolejna strona.';
  }
  await load();
}
