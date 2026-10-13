import {el,action,notice} from './dom.mjs';
import {labels} from './validation.mjs';
export function navigationView(records,trip,container) {
  const app=records.app,panel=el('div','','recording-panel');container.append(panel);
  panel.append(el('h3','Syntetyczny zapis testowy'),notice('Bez prawdziwego GPS, mapy i rekomendacji live. To minimalny zapis danych, nie symulator ruchu.'));
  if(trip.mode!=='SIMULATION'){panel.append(notice('Start live nie jest jeszcze podłączony — etap 9.'));return;}
  const status=notice(labels[trip.status]),buttons=el('div','','actions');panel.append(status,buttons);
  const epoch=app.state.epoch,serial=records.serial;
  function render() {
    buttons.replaceChildren();const nav=records.navigation.get(trip.id);
    if(trip.status==='PLANNED'||(!nav&&['STARTING','RECORDING'].includes(trip.status)&&records.operations.entries.has('start:'+trip.id)))buttons.append(action(trip.status==='PLANNED'?'Rozpocznij zapis syntetyczny':'Ponów ten sam start (wynik nieznany)',async()=>{
      const body={trip_id:trip.id},key=records.operations.key('start:'+trip.id,body),button=buttons.querySelector('button');button.disabled=true;
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
  render();
  async function poll() {
    if(epoch!==app.state.epoch||serial!==records.serial||!panel.isConnected)return;
    const nav=records.navigation.get(trip.id);if(!nav)return;
    try {const data=await app.api.request('/navigation/'+nav.id);if(epoch!==app.state.epoch||serial!==records.serial||!panel.isConnected)return;records.navigation.set(trip.id,data);status.textContent=labels[data.status];
      if(!['RECORDING','FINALIZING','STARTING'].includes(data.status)){records.navigation.delete(trip.id);records.operations.done('finish:'+nav.id);records.detail(trip.id);return;}}
    catch(error){if(epoch!==app.state.epoch||serial!==records.serial)return;app.fail(error);records.navigation.delete(trip.id);status.textContent='Kontekst niedostępny. Nie wznawiamy nagrania.';return;}
    records.timer=setTimeout(poll,3000);
  }
  if(records.navigation.has(trip.id)&&['STARTING','RECORDING','FINALIZING'].includes(trip.status))records.timer=setTimeout(poll,3000);
}
