const assert=require('node:assert/strict');const {test}=require('node:test');
const UI=require('../greenwave/web/vision-workbench-ui.js');
test('map states require fresh camera, exact directional route and recent response',()=>{
 const route={route_id:'r',geometry_hash:'hash'},signal={stop_line_id:'line',route_id:'r',geometry_hash:'hash',direction:'FORWARD',state:'GREEN'};
 UI.update({source_type:'CAMERA',preview_fresh:true,signals:[signal]});assert.equal(UI.signal('line',route).state,'GREEN');
 assert.equal(UI.signal('line',{...route,geometry_hash:'different'}),undefined);
 UI.latest.source_type='FILE';assert.equal(UI.signal('line',route),null);
 UI.latest.source_type='CAMERA';UI.latest.preview_fresh=false;assert.equal(UI.signal('line',route),null);
 UI.latest.preview_fresh=true;UI.received-=1500;assert.equal(UI.signal('line',route),null);
 UI.update({source_type:'CAMERA',preview_fresh:true,signals:[{...signal,direction:'REVERSE'}]});assert.equal(UI.signal('line',route),undefined);
 UI.update(null);assert.equal(UI.signal('line',route),null);
});
