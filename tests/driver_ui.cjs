const {test}=require('node:test');
const assert=require('node:assert/strict');
const {guidance,perspective}=require('../greenwave/web/driver-ui.js');
const valid={speed:40,limit:50,eligible:true,recommendation:{status:'READY',range_min_kmh:35,range_max_kmh:45,target_kmh:40,action:'HOLD'}};
test('lower/upper bands and near-edge commands',()=>{
 assert.equal(guidance({...valid,speed:30}).action,'ACCELERATE');
 assert.equal(guidance({...valid,speed:35.5}).action,'ACCELERATE');
 assert.equal(guidance(valid).action,'HOLD');
 assert.equal(guidance({...valid,speed:44.5}).action,'SLOW');
 assert.equal(guidance({...valid,speed:55}).action,'SLOW');
});
test('hysteresis holds at an edge without alternating arrows',()=>{
 assert.equal(guidance({...valid,speed:36,previous:'ACCELERATE'}).action,'ACCELERATE');
 assert.equal(guidance({...valid,speed:36,previous:'HOLD'}).action,'HOLD');
 assert.equal(guidance({...valid,speed:37,previous:'ACCELERATE'}).action,'HOLD');
 assert.equal(guidance({...valid,speed:44,previous:'SLOW'}).action,'SLOW');
 assert.equal(guidance({...valid,speed:43,previous:'SLOW'}).action,'HOLD');
});
test('freshness, unavailable speed and invalid recommendations fail closed',()=>{
 for(const overrides of [{eligible:false},{speed:null},{speed:NaN},{limit:null},{limit:0},{recommendation:{...valid.recommendation,status:'UNKNOWN'}},
  {recommendation:{...valid.recommendation,range_max_kmh:51}},{recommendation:{...valid.recommendation,target_kmh:60}},
  {recommendation:{...valid.recommendation,range_min_kmh:46}},{recommendation:{...valid.recommendation,range_min_kmh:-1}},
  {recommendation:{...valid.recommendation,action:'UNRECOGNIZED'}}]){
  assert.deepEqual(guidance({...valid,...overrides,previous:'ACCELERATE'}),{action:'UNAVAILABLE',range:null,target:null});
 }
});
test('backend braking and stopping override a below-range acceleration prompt',()=>{
 for(const action of ['BRAKE','ENGINE_BRAKE','COAST'])assert.equal(guidance({...valid,speed:20,recommendation:{...valid.recommendation,action}}).action,'SLOW');
 assert.equal(guidance({...valid,recommendation:{...valid.recommendation,action:'STOP'}}).action,'STOP');
});
test('single-speed target at the legal limit does not flicker or ask to accelerate',()=>{
 const recommendation={...valid.recommendation,target_kmh:50,range_min_kmh:50,range_max_kmh:50};
 assert.equal(guidance({...valid,speed:50,recommendation}).action,'HOLD');
 assert.equal(guidance({...valid,speed:50.9,recommendation}).action,'SLOW');
 assert.equal(guidance({...valid,speed:49,recommendation}).action,'ACCELERATE');
});
test('camera anchor, forward orientation and clipping are consistent',()=>{
 const origin=[0,0],unit=1/(6371008.8*Math.cos(52*Math.PI/180));
 assert.deepEqual(perspective(origin,origin,0,600,800),[300,632]);
 assert.ok(perspective([0,-100*unit],origin,0,600,800)[1]<632);
 assert.ok(perspective([100*unit,0],origin,90,600,800)[1]<632);
 assert.equal(perspective([0,300*unit],origin,0,600,800),null);
});
