import {el,notice,action,form,table} from './dom.mjs';
export function visionPanel(records,trip,screen) {
 if(records.scope!=='own')return;
 const app=records.app,epoch=app.state.epoch,serial=records.serial,panel=el('section','','lab-panel');screen.append(panel);panel.append(el('h3','Laboratorium · kamera diagnostyczna'),notice('CV nie potwierdza faz ani geometrii i nie odblokowuje rekomendacji live.'));
 const valid=()=>panel.isConnected&&epoch===app.state.epoch&&serial===records.serial;let capture=null,timer=null,generation=0;
 const content=el('div');panel.append(content);
 async function load() {
  clearTimeout(timer);const version=++generation;
  try{const sources=await app.api.request('/cv/sources'),entries=await app.api.request('/trips/'+trip.id+'/cv/captures');if(!valid()||version!==generation)return;
   content.replaceChildren();
   if(trip.status==='RECORDING'&&sources.items.length)content.append(form([{name:'source',label:'Źródło skonfigurowane przez operatora',options:sources.items.map(s=>[s.id,s.id])}],{source:v=>sources.items.some(s=>s.id===v)?'':'Wybierz źródło'},async b=>{const source=sources.items.find(s=>s.id===b.source);const data=await app.api.request('/trips/'+trip.id+'/cv/captures',{method:'POST',body:{source_type:source.type,...(source.type==='FILE'?{source_ref:source.id}:{camera_index:Number(source.id.split(':')[1])}),width:320,height:240,fps:20,detection:false,realtime:true}});if(valid()){capture=data.id;generation++;await status();}},'Rozpocznij diagnostyczne CV'));
   else if(!sources.items.length)content.append(notice('Brak operatorskiego źródła kamery lub klipu. Nawigacja i zapis działają bez CV.'));
   for(const c of entries.items)content.append(action('Otwórz CV · '+c.status,async()=>{capture=c.id;generation++;await status();}));
  }catch(e){if(valid())app.fail(e);}
 }
 async function events() {const cid=capture,version=generation;const page=await app.api.request('/trips/'+trip.id+'/cv/captures/'+cid+'/events');if(!valid()||version!==generation||cid!==capture)return;
  content.append(table(['Stan wykrycia','Typ zdarzenia','Przegląd'],page.items.map(e=>{const key=crypto.randomUUID().replaceAll('-','');return [e.state+' · '+(e.reviews?.at(-1)?.status||'Nieprzejrzane'),e.event_type,form([{name:'reason',label:'Powód przeglądu',max:500},{name:'decision',label:'Decyzja',options:[['REJECTED','Odrzuć'],['ACCEPTED','Zaakceptuj diagnostycznie']]}],{reason:v=>v.length>=3?'':'Wymagane co najmniej 3 znaki'},async b=>{await app.api.request('/trips/'+trip.id+'/cv/captures/'+cid+'/reviews',{method:'POST',body:{event_id:e.id,status:b.decision,reason:b.reason,expected_revision:e.review_revision??0,client_operation_id:key}});app.message('Dodano osobny przegląd; oryginalne zdarzenie pozostaje niezmienne.');await status();},'Zapisz przegląd')];})));
 }
 async function status() {
  clearTimeout(timer);const cid=capture,version=generation;try{const data=await app.api.request('/trips/'+trip.id+'/cv/captures/'+cid);if(!valid()||version!==generation||cid!==capture)return;
   content.replaceChildren(notice(`CV · ${data.status} · ${data.frames_captured} klatek · wyłącznie diagnostyka`));
   if(data.frame_id!==null&&data.frame_id!==undefined){const image=el('img');image.alt='Diagnostyczny podgląd CV';image.className='cv-preview';image.src='/school/api/v1/trips/'+trip.id+'/cv/captures/'+capture+'/frames/'+data.frame_id;content.append(image);}
   if(['RUNNING','STARTING','STOPPING'].includes(data.status)){content.append(action('Zatrzymaj CV',async()=>{await app.api.request('/trips/'+trip.id+'/cv/captures/'+capture+'/stop',{method:'POST',body:{}});await status();}));timer=setTimeout(status,800);}else await events();
   content.append(action('Lista capture',load));
  }catch(e){if(valid()){content.replaceChildren(notice('CV niedostępne. Brak wpływu na warunki live.'));app.fail(e);}}
 }
 load();
}
