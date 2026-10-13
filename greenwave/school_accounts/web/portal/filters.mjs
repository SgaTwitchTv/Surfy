import {STATES,EVENTS,statuses} from './validation.mjs';
import {dayRange} from './dates.mjs';
export function filters(body,kind) {
  const result={scope:'own',limit:'25',sort:body.sort||'desc'};
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
