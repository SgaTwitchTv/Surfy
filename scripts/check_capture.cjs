const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require(process.env.GW_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.GW_TEST_URL||'http://127.0.0.1:8767';
 try{
  await page.goto(base);await page.waitForFunction(()=>document.querySelector('#capture-start').onclick);
  await page.locator('#tab-laboratory').click();
  await page.locator('#capture-source-type').selectOption('FILE');
  await page.locator('#capture-source').fill(path.resolve('data/derived/vision-capture-smoke.avi'));
  await page.locator('#capture-start').click();
  await page.waitForFunction(()=>document.querySelector('#capture-status').textContent==='RUNNING'&&!document.querySelector('#capture-image').hidden&&document.querySelector('#capture-image').naturalWidth>0);
  const token=await page.locator('meta[name=greenwave-token]').getAttribute('content');const headers={'X-GreenWave-Token':token};
  assert.equal((await page.request.get(base+'/api/vision/status')).status(),403);
  const initial=await(await page.request.get(base+'/api/vision/status',{headers})).json();
  await page.locator('#tab-ui').click();await page.waitForTimeout(600);
  const later=await(await page.request.get(base+'/api/vision/status',{headers})).json();assert(later.frames_captured>initial.frames_captured);
  const state=await page.request.get(base+'/api/state');assert.equal(state.status(),200);
  await page.locator('#tab-laboratory').click();await page.locator('#capture-stop').click();
  await page.waitForFunction(()=>document.querySelector('#capture-status').textContent==='STOPPED');
  assert(await page.locator('#capture-image').isHidden());
  await page.locator('#capture-refresh').click();await page.locator('#capture-recordings button').first().waitFor();
  await page.locator('#capture-recordings button').first().click();
  await page.waitForFunction(()=>document.querySelector('#capture-status').textContent==='RUNNING');
  await page.locator('#capture-stop').click();await page.waitForFunction(()=>document.querySelector('#capture-status').textContent==='STOPPED');
  assert.deepEqual(errors,[]);console.log('PASS: authenticated preview, tab-independent capture, responsive server, stop hides frame and replay');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
