export const ZONE='Europe/Warsaw';
const civil=new Intl.DateTimeFormat('en-CA',{timeZone:ZONE,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
function parts(ms) { const p=Object.fromEntries(civil.formatToParts(new Date(ms)).map(x=>[x.type,x.value]));
  return Date.UTC(+p.year,+p.month-1,+p.day,+p.hour,+p.minute,+p.second); }
export function midnight(day,next=false) {
  if(!/^\d{4}-\d{2}-\d{2}$/.test(day)) throw new Error('Podaj poprawny dzień.');
  const [y,m,d]=day.split('-').map(Number),date=new Date(Date.UTC(y,m-1,d));
  if(y<1970 || date.toISOString().slice(0,10)!==day) throw new Error('Podaj poprawny dzień od 1970 roku.');
  const target=Date.UTC(y,m-1,d+(next?1:0)); let instant=target;
  for(let i=0;i<4;i++) { const delta=target-parts(instant); if(!delta) return new Date(instant).toISOString(); instant+=delta; }
  throw new Error('Nie można przeliczyć dnia w Europe/Warsaw.');
}
export function dayRange(from,to) {
  const result={}; if(from) result.from=midnight(from); if(to) result.to=midnight(to,true);
  if(result.from && result.to) { const difference=Date.parse(result.to)-Date.parse(result.from);
    if(difference<=0 || difference>366*86400000) throw new Error('Wybierz zakres od–do, maksymalnie 366 dni.'); }
  return result;
}
export function stamp(ms) { return ms===null || ms===undefined ? 'Nieznany' : new Intl.DateTimeFormat('pl-PL',{timeZone:ZONE,dateStyle:'medium',timeStyle:'short'}).format(new Date(ms)); }
