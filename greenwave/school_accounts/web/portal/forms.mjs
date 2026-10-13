import {el,action,form,dialog,notice} from './dom.mjs';
import {rules,STATES,EVENTS,labels} from './validation.mjs';
const options=values=>values.map(v=>[v,labels[v]||v]);
export async function createTrip(records) {
  const app=records.app,epoch=app.state.epoch;
  try {
    const routes=await app.api.request('/config/versions',{query:{kind:'ROUTE',status:'PUBLISHED',limit:'100'}});
    if(epoch!==app.state.epoch)return;
    const routeOptions=[['','Bez trasy — dane syntetyczne'],...routes.items.map(r=>[r.id,r.logical_id+' · wersja '+r.version])];
    const body=el('div');body.append(notice('Tworzysz plan syntetycznego zapisu testowego, bez prawdziwego GPS. Live jest niepodłączone. Lista tras pokazuje do 100 opublikowanych wersji.'));
    let d;body.append(form([{name:'title',label:'Tytuł',max:120},{name:'note',label:'Notatka',type:'textarea',max:1000,required:false},{name:'mode',label:'Tryb',options:[['SIMULATION','Syntetyczny zapis testowy']]},{name:'route_version_id',label:'Wersja trasy',options:routeOptions,required:false}],{title:rules.title,note:rules.note,mode:v=>v==='SIMULATION'?'':'Wybierz tryb syntetyczny.',route_version_id:v=>routeOptions.some(o=>o[0]===v)?'':'Wybierz opublikowaną trasę.'},async value=>{
      if(!value.route_version_id)delete value.route_version_id;const t=await app.api.request('/trips',{method:'POST',body:value});d.close();records.detail(t.id);app.message('Utworzono przejazd.');
    },'Utwórz przejazd'));d=dialog('Nowy przejazd',body);
  }catch(error){app.fail(error);}
}
export function editTrip(records,trip) {
  let current=trip,d;const content=el('div'),conflict=el('div');
  const node=form([{name:'title',label:'Tytuł',value:trip.title,max:120},{name:'note',label:'Notatka',value:trip.note,type:'textarea',max:1000,required:false}],{title:rules.title,note:rules.note},async value=>{
    try {await records.app.api.request('/trips/'+trip.id,{method:'PATCH',body:{...value,expected_revision:current.revision}});d.close();records.detail(trip.id);}
    catch(error) {if(error.status===409) {const latest=await records.app.api.request('/trips/'+trip.id);conflict.replaceChildren(notice('Aktualny rekord: '+latest.title+' · '+latest.note+' · rewizja '+latest.revision),action('Użyj aktualnej rewizji do ponownego zapisu',()=>{current=latest;conflict.replaceChildren(notice('Przejrzano nowszy rekord. Ponownie kliknij Zapisz, aby świadomie zapisać swoje pola.'));}));}throw error;}
  });content.append(node,conflict);d=dialog('Edytuj przejazd',content);
}
export function archiveTrip(records,trip) {
  let d;const content=el('div');content.append(notice('Archiwizujesz „'+trip.title+'”. Surowe dane i raporty pozostaną zapisane; zgoda analityka zostanie cofnięta. Nie ma fizycznego usuwania.'));
  content.append(form([{name:'reason',label:'Powód archiwizacji',max:500}],{reason:rules.reason},async value=>{await records.app.api.request('/trips/'+trip.id,{method:'DELETE',body:{...value,expected_revision:trip.revision}});d.close();records.list('trips');records.app.message('Przejazd zarchiwizowany.');},'Potwierdź archiwizację'));d=dialog('Archiwizacja przejazdu',content);
}
export function shareTrip(records,trip) {
  let d;const body=el('div');body.append(notice('Udostępniasz przebieg GPS, obserwacje, historię korekt i raporty tego przejazdu jednemu aktywnemu analitykowi. Bez eksportu i surowych mediów CV.'));
  body.append(form([{name:'analyst_email',label:'Dokładny email analityka',type:'email',max:254}],{analyst_email:rules.email},async value=>{await records.app.api.request('/trips/'+trip.id+'/share',{method:'POST',body:value});d.close();records.detail(trip.id);},'Udostępnij'));d=dialog('Udostępnienie przejazdu',body);
}
export function revokeTrip(records,trip) {
  let d;const content=el('div');content.append(notice('Cofnij aktualną zgodę na przejazd „'+trip.title+'”. Stare okno nie cofnie nowszego udostępnienia.'));
  content.append(form([],{},async()=>{await records.app.api.request('/trips/'+trip.id+'/share',{method:'DELETE',body:{expected_share_id:trip.share.id}});d.close();records.detail(trip.id);},'Cofnij zgodę'));d=dialog('Cofnij udostępnienie',content);
}
export function manualObservation(records,trip) {
  let d;const content=el('div'),closed=['COMPLETE','INTERRUPTED'].includes(trip.status);
  content.append(notice(closed?'Historyczna adnotacja zamkniętego przejazdu. Czas pomiaru nieznany; nie dopisuje GPS/raw i nie udaje obserwacji podczas jazdy.':'Dla pasażera w syntetycznym zapisie. Kierowca nie musi klikać podczas jazdy. Źródło MANUAL i czas otrzymania nadaje serwer.'));
  content.append(el('p','Zaobserwowano stan: widzisz aktualny kolor. Początek fazy: widzisz moment przejścia do tego koloru. Nieznany stan nie może być początkiem fazy.','muted'));
  const pending='observe:'+trip.id;if(records.operations.entries.has(pending))content.append(action('Rozpocznij osobne nowe zdarzenie',()=>{records.operations.done(pending);records.app.message('Nowe zdarzenie dostanie nowy identyfikator.');}));
  content.append(form([{name:'signal_id',label:'Sygnalizator',max:120},{name:'state',label:'Stan',options:options(STATES)},{name:'event_type',label:'Rodzaj zdarzenia',options:options(EVENTS)}],{signal_id:rules.signal_id,state:rules.state,event_type:rules.event_type},async value=>{
    const name='observe:'+trip.id,source_event_id=records.operations.key(name,value);
    const observation=await records.app.api.request('/trips/'+trip.id+'/observations',{method:'POST',body:{...value,source_event_id}});
    if(observation.journaling_state==='APPLIED')records.operations.done(name);d.close();records.detail(trip.id);records.app.message(observation.journaling_state==='FAILED'?'Fakt zapisany w bazie; zapis do raw nie powiódł się.':'Zapisano obserwację.');
  },'Zapisz obserwację'));d=dialog(closed?'Dodaj adnotację historyczną':'Obserwacja pasażera',content);
}
export function correctObservation(records,obs) {
  let current=obs,d;const content=el('div'),conflict=el('div');
  content.append(notice('Oryginał: '+labels[obs.original.state]+' / '+labels[obs.original.event_type]+'. Obecnie: '+labels[obs.effective.state]+' / '+labels[obs.effective.event_type]+'. Korekta nie zmienia GPS, źródła ani czasów.'));
  const node=form([{name:'state',label:'Stan po korekcie',value:obs.effective.state,options:options(STATES)},{name:'event_type',label:'Rodzaj po korekcie',value:obs.effective.event_type,options:options(EVENTS)},{name:'valid',label:'Ważność',value:String(obs.effective.valid),options:[['true','Ważna'],['false','Nieważna']]},{name:'reason',label:'Powód korekty',max:500}],{state:rules.state,event_type:rules.event_type,valid:rules.valid,reason:rules.reason},async value=>{
    const body={expected_revision:current.correction_revision,changes:{state:value.state,event_type:value.event_type,valid:value.valid==='true'},reason:value.reason};
    const name='correction:'+obs.id;body.client_operation_id=records.operations.key(name,body);
    try {const result=await records.app.api.request('/observations/'+obs.id+'/corrections',{method:'POST',body});records.operations.done(name);d.close();records.history(result.observation);}
    catch(error){if(error.status===409){const {findObservation}=await import('./details.mjs');const latest=await findObservation(records.app,obs);
      conflict.replaceChildren(notice(latest?'Aktualnie: '+labels[latest.effective.state]+' / rewizja '+latest.correction_revision:'Odśwież listę obserwacji, aby wczytać aktualny rekord.'));
      if(latest)conflict.append(action('Użyj aktualnej rewizji korekty',()=>{current=latest;records.operations.done(name);conflict.replaceChildren(notice('Przejrzano aktualną wartość. Ponownie zapisz korektę.'));}));}throw error;}
  },'Zapisz korektę');content.append(node,conflict,el('p','Retry identycznego żądania zachowuje klucz. Zmienione pola tworzą nową operację po świadomym zatwierdzeniu.','muted'));d=dialog('Korekta obserwacji',content);
}
