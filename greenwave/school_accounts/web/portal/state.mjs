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

// One-shot administrative return, memory only; never an authentication credential.
export class AdministrativeDraft {
  constructor(){this.value=null;}
  clear(){this.value=null;}
  save(userId,context){
    this.clear();
    const fields=context.kind==='account'?['role','status','reason']:['reason'];
    if(!['account','publish','archive'].includes(context.kind)||!/^[a-f0-9]{32}$/.test(userId)||!/^[a-f0-9]{32}$/.test(context.id)||!Number.isInteger(context.expected_revision)||context.expected_revision<1)throw new Error('Invalid return context');
    if(Object.keys(context.fields).some(k=>!fields.includes(k))||fields.some(k=>typeof context.fields[k]!=='string'||[...context.fields[k]].length>500))throw new Error('Invalid draft fields');
    if(typeof context.expected_status!=='string')throw new Error('Invalid draft status');
    this.value={userId,kind:context.kind,id:context.id,expected_revision:context.expected_revision,expected_status:context.expected_status,fields:structuredClone(context.fields)};
    if(context.kind==='account'){
      if(typeof context.email!=='string'||context.email.length>254){this.clear();throw new Error('Invalid account lookup');}
      this.value.email=context.email;
    }
  }
  has(userId){return Boolean(this.value&&this.value.userId===userId);}
  take(userId){const value=this.value;this.clear();return value?.userId===userId?structuredClone(value):null;}
}
