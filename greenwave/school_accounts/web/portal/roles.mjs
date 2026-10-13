export const roleMenu=role=>[...(role==='ANALYST'?[['Udostępnione przejazdy','shared']]:[]),['Konfiguracje','configs'],...(role==='ADMIN'?[['Konta użytkowników','users'],['Audyt administracyjny','audit']]:[])];
export function canEditDraft(role,userId,config){return config.status==='DRAFT'&&(role==='ADMIN'||role==='ANALYST'&&config.creator_id===userId);}
export function canPublish(role){return role==='ADMIN';}
export function currentView(state,epoch,records,serial){return state.epoch===epoch&&records.serial===serial&&Boolean(state.value);}
export function requiresReauth(error){return error.status===403&&error.code==='REAUTH_REQUIRED';}
export function adoptRevision(record){if(!Number.isInteger(record.revision)||record.revision<1)throw new Error('Nieprawidłowa rewizja.');return record.revision;}
export function configInput(kind,text){if(new TextEncoder().encode(text).length>262144)throw new Error('Konfiguracja jest za duża.');let value;try{value=JSON.parse(text);}catch{throw new Error('Podaj poprawny JSON.');}
 const forbidden=new Set(['verified','verification','geometry_verification','data_quality','last_verified','field_checked','path','root','filename','raw_ref','token','password','owner_id']);
 const visit=(v,d=0,sourceMetadata=false)=>{if(d>20)throw new Error('Zbyt głęboka struktura.');if(v&&typeof v==='object'){for(const [k,child]of Object.entries(v)){if(forbidden.has(k.toLowerCase()))throw new Error('Flagi weryfikacji i ścieżki są zabronione.');if(k==='url'){let parsed;try{parsed=new URL(child);}catch{throw new Error('Nieprawidłowy URL źródła.');}if(!sourceMetadata||!['http:','https:'].includes(parsed.protocol)||parsed.username||parsed.password)throw new Error('URL jest tylko metadanymi źródła.');continue;}visit(child,d+1,k==='source');}}else if(typeof v==='number'&&!Number.isFinite(v))throw new Error('Liczby muszą być skończone.');};visit(value);
 const required={MODEL:['schema_version','settings','relations'],SIGNAL:['schema_version','id','name','direction','speed_limit_mps','signals'],ROUTE:['schema_version','route_id','geometry_version','name','direction_description','source','coordinates']}[kind];
 if(!required||!value||Array.isArray(value)||required.some(k=>!(k in value))||value.schema_version!==1)throw new Error('Brak wymaganych pól konfiguracji.');
 const optional=kind==='ROUTE'?['speed_sections','stop_lines']:[];
 if(Object.keys(value).some(k=>!required.includes(k)&&!optional.includes(k)))throw new Error('Nieznane pola konfiguracji.');
 const finite=v=>typeof v==='number'&&Number.isFinite(v),point=p=>Array.isArray(p)&&p.length===2&&p.every(finite)&&Math.abs(p[0])<=180&&Math.abs(p[1])<=90;
 if(kind==='ROUTE'){
  if(!Array.isArray(value.coordinates)||value.coordinates.length<2||value.coordinates.length>10000||!value.coordinates.every(point)||value.coordinates.some((p,i)=>i&&p[0]===value.coordinates[i-1][0]&&p[1]===value.coordinates[i-1][1]))throw new Error('Nieprawidłowe współrzędne trasy.');
  for(const section of value.speed_sections||[])if(!finite(section.start_s_m)||!finite(section.end_s_m)||!finite(section.limit_mps)||section.start_s_m<0||section.end_s_m<=section.start_s_m||section.limit_mps<=0)throw new Error('Nieprawidłowe ograniczenie prędkości.');
  for(const line of value.stop_lines||[])if(!Number.isInteger(line.segment_index)||line.segment_index<0||line.segment_index>=value.coordinates.length-1||!Array.isArray(line.coordinates)||line.coordinates.length!==2||!line.coordinates.every(point)||!finite(line.position_uncertainty_m)||line.position_uncertainty_m<0)throw new Error('Nieprawidłowa linia zatrzymania.');
 }else if(kind==='SIGNAL'){
  if(!Array.isArray(value.signals)||!value.signals.length||value.signals.length>1000||value.speed_limit_mps!==null&&(!finite(value.speed_limit_mps)||value.speed_limit_mps<=0))throw new Error('Nieprawidłowy korytarz.');
  const ids=new Set();let last=-1;for(const signal of value.signals){if(typeof signal.id!=='string'||!signal.id||ids.has(signal.id)||signal.direction!==value.direction||!['FIXED_TIME','COORDINATED','ACTUATED','ADAPTIVE','UNKNOWN'].includes(signal.signal_type))throw new Error('Nieprawidłowa tożsamość sygnalizatora.');ids.add(signal.id);
   for(const key of ['road_position_m','cycle_seconds','green_duration','offset','yellow_duration','latitude','longitude','confidence'])if(signal[key]!==null&&!finite(signal[key]))throw new Error('Wartości sygnału muszą być skończone lub null.');
   if(signal.road_position_m!==null){if(signal.road_position_m<=last)throw new Error('Pozycje muszą rosnąć.');last=signal.road_position_m;}
   if(signal.cycle_seconds!==null&&signal.cycle_seconds<=0||signal.green_duration!==null&&signal.green_duration<0||signal.yellow_duration!==null&&signal.yellow_duration<0||[signal.cycle_seconds,signal.green_duration,signal.yellow_duration].every(v=>v!==null)&&signal.green_duration+signal.yellow_duration>=signal.cycle_seconds)throw new Error('Cykl musi zawierać czerwoną fazę.');
  }
 }else{
  const settings=['horizon_seconds','max_age_seconds','observation_state_ttl_seconds','baseline_uncertainty_seconds','assumed_manual_uncertainty_seconds','drift_seconds_per_second','confidence_half_life_seconds','residual_scale_seconds'];
  if(!value.settings||Array.isArray(value.settings)||!Array.isArray(value.relations)||value.relations.length>1000)throw new Error('Nieprawidłowy model.');
  for(const [key,v]of Object.entries(value.settings))if(!settings.includes(key)||!finite(v)||v<0||['horizon_seconds','max_age_seconds','confidence_half_life_seconds','residual_scale_seconds'].includes(key)&&v===0||key==='horizon_seconds'&&v>600)throw new Error('Nieprawidłowe parametry modelu.');
  const pairs=new Set();for(const r of value.relations){const pair=r.source_signal_id+'>'+r.target_signal_id;if(!r.source_signal_id||!r.target_signal_id||r.source_signal_id===r.target_signal_id||pairs.has(pair)||!finite(r.green_start_delta_seconds)||!finite(r.uncertainty_seconds)||r.uncertainty_seconds<0||!r.source)throw new Error('Nieprawidłowa relacja sygnałów.');pairs.add(pair);}
 }
 return value;
}
export function editablePayload(value){const copy=structuredClone(value);const walk=v=>{if(v&&typeof v==='object')for(const key of Object.keys(v)){if(['verification','geometry_verification','verified','data_quality','last_verified'].includes(key))delete v[key];else walk(v[key]);}};walk(copy);return copy;}
