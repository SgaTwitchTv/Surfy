const assert=require('node:assert/strict');const path=require('node:path');
const {chromium}=require(process.env.GW_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(process.env.GW_TEST_URL||'http://127.0.0.1:8767');await page.waitForFunction(()=>document.querySelector('#capture-start').onclick);
  await page.locator('#tab-laboratory').click();await page.locator('#capture-source-type').selectOption('FILE');
  await page.locator('#capture-source').fill(path.resolve('data/derived/vision-probe/decoder-smoke.avi'));
  await page.locator('#capture-detection').check();await page.locator('#capture-start').click();
  await page.waitForFunction(()=>document.querySelector('#capture-values').textContent.includes('lamp-')&&!document.querySelector('#capture-image').hidden&&document.querySelector('#capture-image').naturalWidth>0);
  const values=JSON.parse(await page.locator('#capture-values').textContent());assert(values.frames_analyzed>0);assert.equal(values.live_prediction_eligible,false);assert(values.vision.tracks.every(t=>!t.assigned));
  await page.screenshot({path:'artifacts/tracking-step6.png',fullPage:true});
  await page.locator('#capture-stop').click();await page.waitForFunction(()=>['STOPPED','ENDED'].includes(document.querySelector('#capture-status').textContent));
  assert(await page.locator('#capture-image').isHidden());assert.deepEqual(errors,[]);
  console.log('PASS: actual YOLO overlay and tracks in browser; stop removes preview');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
