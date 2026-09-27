// Dedicated test server only: changes a synthetic observation, never a real run.
const {chromium}=require(process.env.GW_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const url=process.env.GW_TEST_URL||'http://127.0.0.1:8766',output=path.resolve('artifacts/driver-ui');
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1360,height:1050},colorScheme:'light'}),errors=[],external=[];
  page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(!request.url().startsWith(url)&&!request.url().startsWith('data:'))external.push(request.url());});
  await page.goto(url);await page.waitForFunction(()=>typeof state!=='undefined'&&state&&mapData);
  await page.locator('#session-controls summary').click();
  await page.locator('#view-mode').selectOption('SIMULATION');
  await page.locator('#dataset').selectOption('synthetic_s1_s5');
  await page.locator('#reset').click();await page.waitForFunction(()=>state.model_version===0&&!busy);
  await page.locator('#session-controls summary').click();
  await page.locator('#driver-command[data-action="ACCELERATE"]').waitFor();
  assert.equal(await page.locator('#tab-ui').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('#gauge-speed').textContent(),'0');
  await page.screenshot({path:path.join(output,'desktop-light.png'),fullPage:true});
  await page.locator('#tab-navigation').click();await page.locator('#map-canvas').waitFor({state:'visible'});
  await page.waitForFunction(()=>hitPoints.length===5);
  const version=await page.evaluate(()=>state.model_version);
  await page.locator('#green').click();await page.waitForFunction(v=>state.model_version>v,version);
  await page.locator('#tab-laboratory').click();
  const before=await page.evaluate(()=>({session:state.session_id,version:state.model_version,history:state.history_total}));
  for(const scenario of ['no_camera','good_detection','multiple_lamps','unknown_color','conflict','lost_image','stale_gps','wrong_direction','phone_disconnected']){
   await page.locator('#vision-scenario').selectOption(scenario);
   assert.match(await page.locator('#vision-status').textContent(),/DEMO.*ZABLOKOWANA/);
  }
  assert.deepEqual(await page.evaluate(()=>({session:state.session_id,version:state.model_version,history:state.history_total})),before);
  await page.locator('#vision-scenario').selectOption('conflict');
  await page.screenshot({path:path.join(output,'laboratory.png'),fullPage:true});
  await page.locator('#tab-ui').click();await page.emulateMedia({colorScheme:'dark'});
  await page.screenshot({path:path.join(output,'desktop-dark.png'),fullPage:true});
  for(const width of [390,320]){
   await page.setViewportSize({width,height:1000});
   const layout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
   assert.ok(layout.scroll<=layout.width,JSON.stringify(layout));
   await page.screenshot({path:path.join(output,`phone-${width}.png`),fullPage:true});
   await page.locator('#session-controls summary').click();
   const expanded=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
   assert.ok(expanded.scroll<=expanded.width,JSON.stringify(expanded));
   await page.locator('#session-controls summary').click();
  }
  // Replay must not inherit an active synthetic acceleration arrow.
  await page.locator('#session-controls summary').click();
  await page.locator('#view-mode').selectOption('GPS_REPLAY');
  await page.waitForFunction(()=>state.view_mode==='GPS_REPLAY');
  await page.locator('#driver-command[data-action="UNAVAILABLE"]').waitFor();
  assert.equal(await page.locator('#gauge-speed').textContent(),'—');
  await page.locator('#view-mode').selectOption('LIVE');await page.waitForFunction(()=>state.view_mode==='LIVE');
  assert.equal(await page.locator('#driver-command').getAttribute('data-action'),'UNAVAILABLE');
  assert.equal(await page.locator('#driver-green').isDisabled(),true);
  await page.locator('#view-mode').selectOption('SIMULATION');await page.waitForFunction(()=>state.view_mode==='SIMULATION');
  // Withdraw instructions when the HTTP stream stalls, without a server mutation.
  await page.route('**/api/state',route=>route.abort());
  await page.locator('#driver-command[data-action="UNAVAILABLE"]').waitFor();
  assert.equal(await page.locator('#gauge-speed').textContent(),'—');
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  await page.unroute('**/api/state');
  await page.locator('#reset').click();await page.waitForFunction(()=>state.model_version===0&&!busy);
  console.log(JSON.stringify({result:'PASS',errors,external,screenshots:output}));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
