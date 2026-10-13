import {STATES,EVENTS,statuses,text} from './validation.mjs';
import {dayRange} from './dates.mjs';
export function filters(body,kind,scope='own') {
  const result={scope,limit:'25',sort:body.sort||'desc'};
  if(!['own','shared'].includes(scope))throw new Error('Nieprawidłowy zakres.');
  if(!['asc','desc'].includes(result.sort)) throw new Error('Wybierz sortowanie.');
  Object.assign(result,dayRange(body.from,body.to));
  const names=kind==='trips'?['route_id','status','archived']:['trip_id','route_id','signal_id','state','event_type','source','valid'];
  for(const key of names) if(body[key]) result[key]=body[key];
  if(kind==='trips'&&!result.archived) result.archived='false';
  const enums={status:statuses,state:STATES,event_type:EVENTS,source:['MANUAL','CV'],valid:['true','false'],archived:['true','false']};
  for(const [name,allowed] of Object.entries(enums)) if(result[name]&&!allowed.includes(result[name]))throw new Error('Nieprawidłowy filtr '+name+'.');
  if(result.trip_id&&!/^[a-f0-9]{32}$/.test(result.trip_id)) throw new Error('Identyfikator przejazdu ma 32 znaki hex.');
  if(result.signal_id?.length>120 || result.route_id?.length>120) throw new Error('Filtr jest zbyt długi.');
  return result;
}

export function filterRules(kind) {
  const optional=check=>(value,body)=>value===undefined||value===''?'':check(value,body);
  const enumRule=values=>optional(v=>values.includes(v)?'':'Wybierz poprawny filtr.');
  const date=(v,b)=>{try{dayRange(b.from,b.to);return '';}catch(error){return error.message;}};
  const result={from:date,to:date,route_id:optional(v=>text(v,1,120)?'':'Trasa: 1–120 znaków, bez skrajnych spacji.'),sort:enumRule(['asc','desc'])};
  if(kind==='trips')Object.assign(result,{status:enumRule(statuses),archived:enumRule(['true','false'])});
  else Object.assign(result,{trip_id:optional(v=>/^[a-f0-9]{32}$/.test(v)?'':'Przejazd: 32 znaki hex.'),signal_id:optional(v=>text(v,1,120)?'':'Sygnalizator: 1–120 znaków.'),state:enumRule(STATES),event_type:enumRule(EVENTS),source:enumRule(['MANUAL','CV']),valid:enumRule(['true','false'])});
  return result;
}
