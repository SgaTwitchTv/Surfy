const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require(process.env.GW_PLAYWRIGHT_MODULE||'playwright');
const url=process.env.GW_TEST_URL||'http://127.0.0.1:8779';
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const dir='artifacts/school';fs.mkdirSync(dir,{recursive:true});
 const errors=[];const title='Browser acceptance '+Date.now();
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.locator('#login-form').waitFor();
  await page.screenshot({path:dir+'/login-desktop.png',fullPage:true});
  await page.locator('#login-form [name=email]').fill('driver@demo.local');
  await page.locator('#login-form [name=password]').fill('GreenWave-demo-2026');
  await page.locator('#login-form button').click();
  await page.locator('#portal').waitFor();
  await page.locator('#active-trip option').first().waitFor({state:'attached'});
  await page.screenshot({path:dir+'/navigation-desktop.png',fullPage:true});
  await page.locator('[data-view=trips]').click();
  await page.locator('#trip-form [name=title]').fill(title);
  await page.locator('#trip-form button').click();
  await page.locator('#trip-rows').getByText(title,{exact:false}).waitFor();
  await page.locator('#trip-filter [name=q]').fill(title);
  await page.locator('#trip-filter button').click();
  await page.waitForFunction(()=>document.querySelector('#trip-rows').children.length===1);
  await page.getByRole('button',{name:'Edytuj',exact:true}).click();
  await page.locator('#edit-fields [name=note]').fill('Corrected title, raw GPS unchanged.');
  await page.locator('#edit-form button.primary').click();
  await page.locator('#edit-dialog').waitFor({state:'hidden'});
  await page.screenshot({path:dir+'/trips-desktop.png',fullPage:true});
  await page.locator('[data-view=navigation]').click();
  await page.locator('#active-trip').selectOption({label:title+' • Planowany'});
  await page.locator('#start-demo').click();
  await page.waitForFunction(()=>document.querySelector('#gps-status').textContent.includes('w ruchu'));
  await page.locator('#passenger-form button').click();
  await page.locator('#notice').filter({hasText:'Zapisano obserwację'}).waitFor();
  await page.locator('#finish').click();
  await page.locator('#notice').filter({hasText:'Zaktualizowano przejazd'}).waitFor();
  await page.locator('[data-view=observations]').click();
  await page.locator('#observation-rows tr').first().getByRole('button',{name:'Koryguj'}).click();
  await page.locator('#edit-fields [name=state]').selectOption('RED');
  await page.locator('#edit-fields [name=reason]').fill('Browser test correction');
  await page.locator('#edit-form button.primary').click();
  await page.locator('#edit-dialog').waitFor({state:'hidden'});
  await page.locator('#observation-filter [name=state]').selectOption('RED');
  await page.locator('#observation-filter button').click();
  await page.waitForFunction(()=>document.querySelector('#observation-rows').textContent.includes('Czerwone'));
  await page.screenshot({path:dir+'/observations-desktop.png',fullPage:true});
  for(const size of [{width:390,height:844},{width:320,height:740},{width:844,height:390}]){
   await page.setViewportSize(size);await page.locator('[data-view=navigation]').click();
   await page.waitForTimeout(900);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal page overflow '+size.width);
   await page.screenshot({path:dir+'/navigation-'+size.width+'.png',fullPage:true});
  }
  // Network loss clears all guidance and current speed.
  await page.route('**/school/api/navigation',route=>route.abort());
  await page.waitForFunction(()=>document.querySelector('#guidance').textContent==='Brak rekomendacji');
  await page.waitForFunction(()=>document.querySelector('#speed').textContent==='—');
  assert.deepEqual(errors,[]);
  console.log('PASS: login, trips, recording, observation, correction, filters, 3 mobile layouts, network loss.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});

