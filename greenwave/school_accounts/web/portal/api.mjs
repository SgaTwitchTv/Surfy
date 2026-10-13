export class APIError extends Error {
  constructor(status,payload={}) { super(payload.message || 'Operacja nie powiodła się.'); this.status=status; this.code=payload.code; this.fields=payload.fields||{}; }
}
export function errorText(error) {
  if(error.status===401) return 'Sesja wygasła lub dane logowania są nieprawidłowe. Zaloguj się ponownie.';
  if(error.code==='ARTIFACT_INVALID') return 'Integralność plików nie została potwierdzona. Eksport jest niedostępny.';
  if(error.status===409) return 'Konflikt danych lub zajęta sesja. Odśwież stan i świadomie ponów zapis.';
  if(error.status===404) return 'Zasób lub kontekst jest niedostępny. Nie można wznowić dawnego nagrania.';
  if(error.code==='REAUTH_REQUIRED') return 'Potwierdź tożsamość hasłem i świadomie ponów operację.';
  if(error.status===403) return 'Brak uprawnienia lub wygasła sesja formularza.';
  if(error.status===429) return 'Za dużo prób. Spróbuj później.';
  if(error.code==='INVALID_TOKEN') return 'Link jest nieprawidłowy lub wygasł.';
  if(error.status===422) return 'Sprawdź poprawność formularza.';
  return 'Błąd sieci lub serwera. Wynik zapisu może być nieznany. Ponów świadomie tę samą operację.';
}
export class API {
  constructor(state,fetcher=globalThis.fetch.bind(globalThis)) { this.state=state; this.fetcher=fetcher; this.pending=new Set(); }
  abort() { for(const c of this.pending) c.abort(); this.pending.clear(); }
  async download(path) {
    // HEAD checks integrity and access without constructing or cancelling a ZIP.
    const epoch=this.state.epoch,controller=new AbortController();this.pending.add(controller);
    try {
      const response=await this.fetcher('/school/api/v1'+path,{method:'HEAD',credentials:'same-origin',cache:'no-store',signal:controller.signal});
      if(epoch!==this.state.epoch)throw new DOMException('Stale account','AbortError');
      if(!response.ok) {if(response.status===401)this.state.clear();throw new APIError(response.status,{code:response.headers?.get('X-School-Error')});}
      const link=document.createElement('a');link.href='/school/api/v1'+path;link.download='greenwave-trip.zip';document.body.append(link);link.click();link.remove();
    } finally {this.pending.delete(controller);}
  }
  async request(path,{method='GET',body,query,signal,key}={}) {
    const epoch=this.state.epoch,controller=new AbortController();this.pending.add(controller);
    const relay=()=>controller.abort(); signal?.addEventListener('abort',relay,{once:true}); if(signal?.aborted) controller.abort();
    const timer=setTimeout(()=>controller.abort(),15000);
    const options={method,credentials:'same-origin',cache:'no-store',signal:controller.signal,headers:{}};
    if(body!==undefined) { options.headers={'Content-Type':'application/json','X-CSRF-Token':this.state.csrf()};options.body=JSON.stringify(body); }
    if(key) options.headers['Idempotency-Key']=key;
    try {
      const response=await this.fetcher('/school/api/v1'+path+(query?'?'+new URLSearchParams(query):''),options);
      const payload=response.status===204?{}:await response.json();
      if(epoch!==this.state.epoch) throw new DOMException('Stale account','AbortError');
      if(!response.ok) { if(response.status===401) this.state.clear(); throw new APIError(response.status,payload.error); }
      return payload.data;
    } catch(error) {if(error instanceof APIError||error.name==='AbortError')throw error;throw new APIError(0,{code:'NETWORK_ERROR'});}
    finally { clearTimeout(timer);signal?.removeEventListener('abort',relay);this.pending.delete(controller); }
  }
}
