const test=require('node:test'),assert=require('node:assert/strict');
const {schoolGuidance}=require('../greenwave/web/school.js');
const ready={status:'READY',target_kmh:40,range_min_kmh:35,range_max_kmh:45,action:'HOLD'};
test('only eligible bounded predictions produce guidance',()=>{
 assert.equal(schoolGuidance(20,50,ready,true).action,'Przyspiesz');
 assert.equal(schoolGuidance(47,50,ready,true).action,'Zwolnij');
 assert.equal(schoolGuidance(40,50,ready,true).action,'Utrzymaj prędkość');
 for(const r of [{...ready,status:'UNKNOWN'},{...ready,range_max_kmh:60},{...ready,target_kmh:null},{...ready,target_kmh:70},{...ready,range_min_kmh:-1}])assert.equal(schoolGuidance(20,50,r,true),null);
 assert.equal(schoolGuidance(20,50,ready,false),null);
 assert.equal(schoolGuidance(null,50,ready,true),null);
 assert.equal(schoolGuidance(20,null,ready,true),null);
});
