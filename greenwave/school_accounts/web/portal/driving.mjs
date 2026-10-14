const finite=value=>typeof value==='number'&&Number.isFinite(value);
export function guidance({speed,limit,recommendation:r,eligible,previous='HOLD'}) {
  const blocked={action:'UNAVAILABLE',range:null,target:null};
  if(!eligible||!finite(speed)||speed<0||!finite(limit)||limit<=0||r?.status!=='READY')return blocked;
  if(!['HOLD','ACCELERATE','BRAKE','COAST','ENGINE_BRAKE','STOP'].includes(r.action))return blocked;
  const low=r.range_min_kmh,high=r.range_max_kmh,target=r.target_kmh;
  if(![low,high,target].every(finite)||low<0||low>high||target<low||target>high||high>limit)return blocked;
  let action='HOLD';
  const wide=high-low>=3,slowEnter=wide?high-.8:high+.8,slowExit=wide?high-1.5:high+.2;
  const accelerateEnter=wide?low+.8:low-.8,accelerateExit=wide?low+1.5:low-.2;
  if(r.action==='STOP'||high===0)action='STOP';
  else if(['BRAKE','COAST','ENGINE_BRAKE'].includes(r.action)||speed>limit||speed>=slowEnter||previous==='SLOW'&&speed>slowExit)action='SLOW';
  else if(low>0&&(speed<=accelerateEnter||previous==='ACCELERATE'&&speed<accelerateExit)&&speed<limit)action='ACCELERATE';
  return {action,range:[low,high],target};
 }
 export function perspective(point,origin,bearing,width,height,zoom=1,latitude=52) {
  const metres=6371008.8*Math.cos(latitude*Math.PI/180),dx=(point[0]-origin[0])*metres,dy=(point[1]-origin[1])*metres;
  const angle=bearing*Math.PI/180,right=dx*Math.cos(angle)+dy*Math.sin(angle),forward=dx*Math.sin(angle)-dy*Math.cos(angle);
  const depth=1+forward/480;if(depth<.3||forward>2200||forward< -160)return null;
  const scale=height/520*zoom;
  return [width/2+right*scale/depth,height*.79-forward*scale*.63/depth];
 }
export function displayState(state,ageMilliseconds,previous='HOLD') {
 const fresh=state?.active!==false&&Number.isFinite(ageMilliseconds)&&ageMilliseconds>=0&&ageMilliseconds<1500;
 const sim=state?.mode==='SIMULATION';
 const speed=fresh&&finite(state?.speed_mps)?state.speed_mps*3.6:null;
 const limit=finite(state?.speed_limit_mps)?state.speed_limit_mps*3.6:null;
 const eligible=fresh&&state?.active!==false&&(sim||state?.eligibility?.allowed===true);
 const advice=guidance({speed,limit,recommendation:sim?state?.simulation_recommendation:state?.live_recommendation,eligible,previous});
 return {speed,limit,advice,connected:fresh,reason:fresh?reasonText((state?.eligibility?.reason_codes||[]).slice(0,2)):'Utrata połączenia · brak świeżego stanu',synthetic:sim};
}
export function projectedRoad(point, origin, heading, width, height) {
 if(!point||!origin||![...point,...origin,heading,width,height].every(finite))return null;
 // Local WGS84 metric projection, north upward; no synthetic normalization of GPS.
 const factor=Math.cos(origin[1]*Math.PI/180);if(Math.abs(factor)<1e-6||width<=0||height<=0)return null;
 const coordinate=p=>[p[0]*Math.PI/180,-p[1]*Math.PI/180/factor];
 return perspective(coordinate(point),coordinate(origin),heading,width,height,1,origin[1]);
}

export function reasonText(codes=[]) {
 const labels={POSITION_NOT_FRESH_OR_UNVERIFIED:'GPS nieświeży lub niewiarygodny',ROUTE_NOT_MATCHED:'Pozycja niedopasowana do trasy',FORWARD_DIRECTION_NOT_CONFIRMED:'Kierunek jazdy niepotwierdzony',SPEED_UNAVAILABLE:'Prędkość nieznana',GEOMETRY_NOT_FIELD_VERIFIED:'Geometria trasy niepotwierdzona w terenie',NEXT_STOP_LINE_UNAVAILABLE:'Brak następnej linii zatrzymania',STOP_LINE_NOT_FIELD_VERIFIED:'Linia zatrzymania niepotwierdzona',SIGNAL_ID_UNAVAILABLE:'Nieznany sygnalizator',SPEED_LIMIT_NOT_FIELD_VERIFIED:'Limit prędkości niezweryfikowany',LIVE_PHASE_DATA_UNAVAILABLE:'Brak wiarygodnych faz świateł',PREDICTION_CLOCK_UNAVAILABLE:'Zegar predykcji niepotwierdzony',NAVIGATION_CLOSED:'Sesja jazdy zakończona'};
 return codes.map(code=>labels[code]||'Brak wiarygodnych danych').join(' · ');
}
