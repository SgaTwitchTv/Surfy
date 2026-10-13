import {el,action,form,notice,table} from './dom.mjs';
import {filters} from './filters.mjs';
import {stamp,ZONE} from './dates.mjs';
import {labels,statuses,STATES,EVENTS} from './validation.mjs';
const choose=values=>[['','Wszystkie'],...values.map(v=>[v,labels[v]||v])];
export function listView(records,kind) {
  records.leave();const app=records.app;app.active=kind;app.menu();const screen=app.screen;
  screen.replaceChildren(el('p','Twoje dane · '+ZONE,'eyebrow'),el('h2',kind==='trips'?'Moje przejazdy':'Moje obserwacje'));
  const toolbar=el('div','','actions');if(kind==='trips')toolbar.append(action('Nowy przejazd',()=>records.create(),'primary'));
  screen.append(toolbar,notice(kind==='trips'?'Planowanie i historia własnych przejazdów. Demo zapisuje dane syntetyczne.':'Kolor, typ i ważność dotyczą wartości po korektach. Czas otrzymania nie oznacza chwili zmiany światła.'));
  const specs=[{name:'from',label:'Data od · Warszawa',type:'date',required:false},{name:'to',label:'Data do (włącznie)',type:'date',required:false},{name:'route_id',label:'Trasa · identyfikator',required:false,max:120}];
  if(kind==='trips')specs.push({name:'status',label:'Status',options:choose(statuses),required:false},{name:'archived',label:'Archiwum',options:[['false','Aktywne rekordy'],['true','Archiwalne']]});
  else specs.push({name:'trip_id',label:'Przejazd · ID (opcjonalnie)',required:false,max:32},{name:'signal_id',label:'Sygnalizator',required:false,max:120},{name:'state',label:'Kolor efektywny',options:choose(STATES),required:false},{name:'event_type',label:'Rodzaj efektywny',options:choose(EVENTS),required:false},{name:'source',label:'Źródło',options:choose(['MANUAL','CV']),required:false},{name:'valid',label:'Ważność efektywna',options:[['','Wszystkie'],['true','Ważne'],['false','Nieważne']],required:false});
  specs.push({name:'sort',label:'Sortowanie',options:[['desc','Najnowsze'],['asc','Najstarsze']]});
  const filterForm=form(specs,{},async body=>{const query=filters(body,kind);records.page.reset(query);await load();},'Zastosuj filtry');filterForm.classList.add('filters');screen.append(filterForm);
  screen.append(el('p','Dni w Europe/Warsaw; koniec wybranego dnia to początek następnego, z uwzględnieniem DST.','muted'));
  const content=el('div'),feedback=notice(''),pager=el('div','','pagination');screen.append(content,feedback,pager);
  const first=action('Pierwsza strona',()=>{records.page.reset(records.page.filters);load().catch(app.fail.bind(app));});
  const next=action('Następna strona',()=>load().catch(app.fail.bind(app)));pager.append(first,next);
  async function load() {
    content.replaceChildren(notice('Ładowanie danych…'));next.disabled=true;feedback.textContent='';
    try {await records.page.load((query,signal)=>app.api.request('/'+kind,{query,signal}),result=>{
      if(!content.isConnected)return;
      content.replaceChildren();const items=result.items;
      if(!items.length)content.append(notice('Brak danych dla wybranych filtrów.'));
      else if(kind==='trips')content.append(table(['Tytuł','Utworzono','Trasa','Tryb','Status','Akcje'],items.map(t=>{
        const title=el('strong',t.title),buttons=el('div','','row-actions');buttons.append(action('Szczegóły',()=>records.detail(t.id)));
        return [title,stamp(t.created_at),t.route_version_id||'Bez trasy',labels[t.mode],labels[t.status]+(t.archived_at?' · Archiwum':''),buttons];
      })));
      else content.append(table(['Otrzymano','Przejazd','Sygnalizator','Źródło','Kolor efektywny','Zdarzenie','Ważność','Korekta / akcja'],items.map(o=>{
        const buttons=el('div','','row-actions');buttons.append(el('span',o.correction_revision?'Korekta #'+o.correction_revision:'Oryginał'),action('Historia / korekta',()=>records.history(o)));
        const time=el('div',stamp(o.server_received_at));if(o.historical)time.append(el('small','Adnotacja historyczna','tag'));
        return [time,action('Przejazd '+o.trip_id.slice(0,8),()=>records.detail(o.trip_id)),o.signal_id,labels[o.source],labels[o.effective.state],labels[o.effective.event_type],o.effective.valid?'Ważna':'Nieważna',buttons];
      })));
      next.disabled=!result.page.next_cursor;feedback.textContent=result.page.next_cursor?'Dostępna kolejna strona.':'Koniec wyników.';
    });}catch(error){if(content.isConnected){content.replaceChildren(notice('Nie udało się wczytać danych.'),action('Ponów pobranie',()=>load()));feedback.textContent='Błąd pobrania; filtry zachowane.';next.disabled=!records.page.cursor;app.fail(error);}}
  }
  records.page.reset(filters({},kind));load().catch(error=>{if(content.isConnected){content.replaceChildren(notice('Nie udało się wczytać danych.'));feedback.textContent=error.message;app.fail(error);}});
}
