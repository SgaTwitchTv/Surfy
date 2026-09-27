const assert=require('node:assert/strict');const path=require('node:path');
const {chromium}=require(process.env.GW_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1360,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.GW_TEST_URL||'http://127.0.0.1:8767';
 try{
  await page.goto(base);await page.waitForFunction(()=>document.querySelector('#capture-start').onclick);
  const token=await page.locator('meta[name=greenwave-token]').getAttribute('content');const headers={'X-GreenWave-Token':token};
  const initial=await(await page.request.get(base+'/api/state')).json();const session_id=initial.session_id;
  assert.equal((await page.request.post(base+'/api/mapping/select',{headers,data:{session_id,route_id:'arkadia_maczka_okopowa_v1'}})).status(),200);
  await page.locator('#tab-laboratory').click();await page.locator('#capture-source-type').selectOption('FILE');await page.locator('#capture-source').fill(path.resolve('data/derived/workbench-smoke.avi'));await page.locator('#capture-detection').check();await page.locator('#capture-start').click();
  await page.waitForFunction(()=>VisionWorkbenchUI.latest?.vision?.tracks?.some(t=>t.state==='RED')&&document.querySelector('#cv-line').options.length>0);
  const capture_id=await page.evaluate(()=>VisionWorkbenchUI.latest.session_id);
  await page.locator('#cv-assign').click();await page.waitForFunction(()=>document.querySelector('#cv-associations').textContent.includes('FILM HISTORYCZNY'));
  const assigned=await(await page.request.get(base+'/api/vision/status',{headers})).json();assert(assigned.signals.length>0);assert(assigned.signals.every(s=>s.historical));assert.equal(assigned.live_prediction_eligible,false);
  await page.locator('#capture-stop').click();await page.waitForFunction(()=>document.querySelector('#capture-status').textContent==='STOPPED');
  await page.locator('#capture-refresh').click();await page.waitForFunction(id=>[...document.querySelector('#cv-history-capture').options].some(o=>o.value===id),capture_id);await page.locator('#cv-history-capture').selectOption(capture_id);await page.locator('#cv-history-load').click();await page.waitForFunction(()=>document.querySelector('#cv-history').textContent.includes('STATE_SEEN'));
  await page.locator('#cv-reviewer').fill('browser-test');await page.locator('#cv-history button').filter({hasText:'Potwierdź i przypisz'}).first().click();await page.waitForFunction(()=>document.querySelector('#cv-history').textContent.includes('ACCEPTED'));
  const history=await(await page.request.get(base+'/api/vision/history?capture_id='+capture_id,{headers})).json();assert.equal(history.entries[0].review_status,'ACCEPTED');assert.equal(history.entries[0].decisions.length,1);
  assert.equal((await page.request.get(base+'/api/vision/export?capture_id='+capture_id,{headers})).status(),200);
  const download=page.waitForEvent('download');await page.locator('#cv-history-export').click();await download;
  for(const size of [{width:390,height:844},{width:844,height:390},{width:320,height:700}]){await page.setViewportSize(size);await page.waitForTimeout(300);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));}
  await page.setViewportSize({width:1360,height:900});await page.screenshot({path:'artifacts/workbench-step7.png',fullPage:true});
  await page.locator('#cv-history button').filter({hasText:'Odtwórz od zdarzenia'}).first().click();await page.waitForFunction(()=>document.querySelector('#capture-status').textContent==='RUNNING'&&!document.querySelector('#capture-image').hidden);await page.locator('#capture-stop').click();await page.waitForFunction(()=>['STOPPED','ENDED'].includes(document.querySelector('#capture-status').textContent));
  assert.deepEqual(errors,[]);console.log('PASS: actual model, manual association, historical isolation, durable review/export, event seek and mobile layouts');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
