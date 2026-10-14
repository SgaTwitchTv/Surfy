import {el,notice,action,form,table,dialog} from './dom.mjs';
import {rules} from './validation.mjs';
export async function devicesView(app) {
 app.records.leave();app.active='devices';app.menu();const epoch=app.state.epoch,serial=app.records.serial,screen=app.screen;screen.replaceChildren(el('h2','Moje urządzenia'),notice('Telefon służy wyłącznie do telemetrii GPS. Parowanie wymaga HTTPS i aktywnej sesji przeglądarki.'));
 const current=()=>epoch===app.state.epoch&&serial===app.records.serial&&app.active==='devices';
 try {const result=await app.api.request('/devices');if(!current())return;
  screen.append(table(['Etykieta','Stan','Akcje'],result.items.map(d=>[d.label,d.status,(()=>{const actions=el('div','','actions');actions.append(action('Edytuj etykietę',()=>{let modal;modal=dialog('Etykieta urządzenia',form([{name:'label',label:'Etykieta',max:80,value:d.label}],{label:v=>v.length>=1&&v.length<=80?'':'1–80 znaków'},async body=>{await app.api.request('/devices/'+d.id,{method:'PATCH',body});modal.close();if(current())devicesView(app);},'Zapisz etykietę'));}),action('Cofnij urządzenie',async()=>{try{await app.api.request('/devices/'+d.id,{method:'DELETE',body:{reason:'Cofnięcie urządzenia przez właściciela'}});if(current())devicesView(app);}catch(e){app.fail(e);}}));return actions;})()])));
  if(app.state.value.demo){screen.append(notice('Demo HTTP działa bez telefonu. Parowanie dostępne w profilu HTTPS.'));return;}
  screen.append(form([{name:'label',label:'Etykieta telefonu',max:80}],{label:v=>v.length>=1&&v.length<=80?'':'1–80 znaków'},async body=>{
   const data=await app.api.request('/pairing-challenges',{method:'POST',body});if(!current())return;
   const code=el('p',data.code,'pairing-code'),box=el('section');box.append(notice('Kod jednorazowy, ważny 5 minut. Wpisz go w aplikacji Android.'),code,action('Cofnij kod',async()=>{await app.api.request('/pairing-challenges/'+data.id,{method:'DELETE',body:{}});box.remove();}));screen.append(box);
   setTimeout(()=>{code.textContent='Kod wygasł';},Math.max(0,data.expires_at-Date.now()));
  },'Utwórz kod parowania'));
 }catch(e){app.fail(e);}
}
