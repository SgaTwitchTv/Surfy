export class SessionState {
  constructor() { this.value=null; this.preauth=null; this.epoch=0; this.listeners=new Set(); }
  set(value) { this.epoch++; this.value=value; this.preauth=null; for(const fn of this.listeners) fn(value); }
  clear() { this.set(null); }
  csrf() { return this.value?.csrf || this.preauth?.csrf || ''; }
}
export class LatestQuery {
  constructor() { this.serial=0; this.controller=null; this.filters={}; this.cursor=null; }
  reset(filters={}) { this.cancel(); this.filters={...filters}; this.cursor=null; }
  cancel() { this.serial++; this.controller?.abort(); this.controller=null; }
  async load(read,apply) {
    this.cancel(); const serial=this.serial; this.controller=new AbortController();
    try { const result=await read({...this.filters,...(this.cursor?{cursor:this.cursor}:{})},this.controller.signal);
      if(serial!==this.serial) return false;
      this.cursor=result.page.next_cursor || null; apply(result); return true;
    } catch(error) { if(serial!==this.serial || error.name==='AbortError') return false; throw error; }
  }
}
function canonical(value) {
  if(Array.isArray(value)) return value.map(canonical);
  if(value && typeof value==='object') return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));
  return value;
}
export class OperationKeys {
  constructor(generate=()=>crypto.randomUUID().replaceAll('-','')) { this.generate=generate; this.entries=new Map(); }
  key(name,payload) { const fingerprint=JSON.stringify(canonical(payload)),old=this.entries.get(name);
    if(!old || old.fingerprint!==fingerprint) this.entries.set(name,{fingerprint,key:this.generate()});
    return this.entries.get(name).key;
  }
  done(name) { this.entries.delete(name); }
  clear() { this.entries.clear(); }
}
