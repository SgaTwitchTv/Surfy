// Run: node tests/mobile_flow.cjs
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
async function main(){
 const elements=Object.fromEntries(['start','stop','status','measurements'].map(id=>[id,{disabled:true,textContent:'',handlers:{},addEventListener(e,f){this.handlers[e]=f}}]));
 let success, failure, cleared=0, posted;
 const context={document:{getElementById:id=>elements[id],querySelector:()=>({content:'test-token'})},window:{isSecureContext:true},navigator:{geolocation:{watchPosition(ok,bad){success=ok;failure=bad;return 7},clearWatch(){cleared++}}},AbortSignal,
 fetch:async(url,options)=>{if(url==='/api/state')return {ok:true,json:async()=>({session_id:'session'})};posted=JSON.parse(options.body);return {ok:true,json:async()=>({external_position:{speed_mps:posted.speed_mps,raw_speed_mps:posted.speed_mps,calculated_speed_mps:null,speed_source:posted.speed_mps==null?'UNAVAILABLE':'DEVICE',position_quality:'GOOD'},external_status:{diagnostic:'Telefon podał prędkość bezpośrednio.'}})}}};
 vm.runInNewContext(readFileSync('greenwave/web/mobile.js','utf8'),context);
 assert.equal(elements.start.disabled,false);
 elements.start.handlers.click();
 assert.match(elements.status.textContent,/Uruchamiam GPS/);
 await success({timestamp:12000,coords:{latitude:52.2,longitude:20.9,speed:10,heading:180,accuracy:4}});
 assert.equal(posted.session_id,'session');assert.equal(posted.speed_mps,10);
 assert.equal(posted.source,'WEB_GEOLOCATION');
 assert.match(elements.measurements.textContent,/36.0 km\/h/);
 assert.match(elements.measurements.textContent,/źródło|telefon/);
 assert.match(elements.status.textContent,/odbiór 1 próbek/);
 await success({timestamp:13000,coords:{latitude:52.2,longitude:20.9,speed:null,heading:null,accuracy:4}});
 assert.equal(posted.speed_mps,null);
 elements.stop.handlers.click();assert.equal(cleared,1);
 elements.start.handlers.click();failure({message:'denied'});
 assert.match(elements.status.textContent,/denied/);assert.equal(elements.start.disabled,false);
 context.window.isSecureContext=false;elements.start.handlers.click();
 assert.match(elements.status.textContent,/localhost/);
 console.log('PASS: init, click, GPS, session, confirmed transmission, missing speed, stop, retry, HTTP feedback');
}
main().catch(e=>{console.error(e);process.exitCode=1});
