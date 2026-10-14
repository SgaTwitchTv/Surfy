const test=require('node:test'),assert=require('node:assert/strict');
const modulePath='../greenwave/school_accounts/web/portal/driving.mjs';
test('stale, unknown speed, invalid solver and live gate clear guidance',async()=>{const{displayState}=await import(modulePath);
 const recommendation={status:'READY',action:'HOLD',range_min_kmh:25,range_max_kmh:40,target_kmh:30};
 const state={mode:'LIVE',speed_mps:5,speed_limit_mps:50/3.6,eligibility:{allowed:true},live_recommendation:recommendation};
 assert.equal(displayState(state,0).advice.action,'ACCELERATE');
 for(const s of [state,{...state,speed_mps:null},{...state,eligibility:{allowed:false}},{...state,live_recommendation:{...recommendation,range_max_kmh:60}}])assert.equal(displayState(s,s===state?1500:0).advice.range,null);
 assert.equal(displayState(state,1500).speed,null);
});
test('synthetic advice remains explicitly synthetic, replay never eligible',async()=>{const{displayState}=await import(modulePath);assert.equal(displayState({mode:'SIMULATION'},0).synthetic,true);assert.equal(displayState({mode:'GPS_REPLAY',eligibility:{allowed:false}},0).advice.action,'UNAVAILABLE');});
test('map projection requires real coordinates and unknown position is absent',async()=>{const{projectedRoad}=await import(modulePath);assert.equal(projectedRoad(null,[21,52],0,650,400),null);assert.equal(projectedRoad([NaN,52],[21,52],0,650,400),null);assert.deepEqual(projectedRoad([21,52],[21,52],0,650,400),[325,316]);});

test('ended contexts and concrete gate reasons never retain a live command',async()=>{const{displayState,reasonText}=await import(modulePath);assert.equal(displayState({active:false,mode:'LIVE',speed_mps:10,eligibility:{allowed:true}},0).advice.range,null);assert.match(reasonText(['SPEED_UNAVAILABLE','NAVIGATION_CLOSED','unknown']),/Prędkość nieznana/);assert.equal(reasonText([]),'');});

test('guidance respects stopping, braking, limit and hysteresis',async()=>{const{guidance}=await import(modulePath);const base={speed:30,limit:50,eligible:true,recommendation:{status:'READY',action:'HOLD',range_min_kmh:25,range_max_kmh:40,target_kmh:30}};
 assert.equal(guidance(base).action,'HOLD');assert.equal(guidance({...base,speed:42}).action,'SLOW');assert.equal(guidance({...base,speed:39,previous:'SLOW'}).action,'SLOW');assert.equal(guidance({...base,speed:24}).action,'ACCELERATE');assert.equal(guidance({...base,speed:26,previous:'ACCELERATE'}).action,'ACCELERATE');
 for(const action of ['BRAKE','COAST','ENGINE_BRAKE'])assert.equal(guidance({...base,recommendation:{...base.recommendation,action}}).action,'SLOW');
 assert.equal(guidance({...base,recommendation:{...base.recommendation,action:'STOP',range_min_kmh:0,range_max_kmh:0,target_kmh:0}}).action,'STOP');
 for(const r of [{...base.recommendation,status:'INFEASIBLE'},{...base.recommendation,action:'invalid'},{...base.recommendation,range_min_kmh:45},{...base.recommendation,target_kmh:60},null])assert.equal(guidance({...base,recommendation:r}).action,'UNAVAILABLE');
 assert.equal(guidance({...base,limit:null}).range,null);assert.equal(guidance({...base,speed:-1}).range,null);
});
test('north is ahead and out-of-view/polar points are absent',async()=>{const{projectedRoad}=await import(modulePath);assert.ok(projectedRoad([21,52.001],[21,52],0,650,400)[1]<316);assert.equal(projectedRoad([21,51.99],[21,52],0,650,400),null);assert.equal(projectedRoad([21,52.1],[21,52],0,650,400),null);assert.equal(projectedRoad([21,90],[21,90],0,650,400),null);assert.equal(projectedRoad([21,52],[21,52],0,0,400),null);});
