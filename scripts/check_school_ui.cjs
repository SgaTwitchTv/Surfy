// Actual backend + production KDF, temporary synthetic DB, no public provisioning.
const {chromium}=require(process.env.GW_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process'),readline=require('node:readline');
const child=spawn(process.env.GW_PYTHON||'python',['-m','scripts.school_browser_fixture'],{env:{...process.env,GW_RESOURCE_FIXTURE:'1',GW_SCHOOL_UI_FIXTURE:'1'},stdio:['pipe','pipe','pipe']});
let stderr='';child.stderr.on('data',d=>stderr+=d);const PASS='Browser password 123!';
(async()=>{
 const config=await new Promise((resolve,reject)=>{const rl=readline.createInterface({input:child.stdout});rl.once('line',line=>{rl.close();resolve(JSON.parse(line));});child.once('exit',code=>reject(new Error('Fixture exited '+code)));});
 const browser=await chromium.launch({channel:'msedge',headless:true});const out=path.resolve('docs/school-app/screenshots');fs.mkdirSync(out,{recursive:true});
 const report=[];
 try {
  for(const [label,width,height] of [['desktop',1360,900],['phone',390,844],['narrow',320,844]]) {
   const context=await browser.newContext({viewport:{width,height},timezoneId:'America/New_York'}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   const button=(name,scope=page)=>scope.getByRole('button',{name,exact:true});
   const overflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'page overflow '+label);
   async function login(who){await page.locator('input[name=email]').fill(who+'@example.test');await page.locator('input[name=password]').fill(PASS);await button('Potwierdź').click();await page.getByRole('heading',{name:'Twoje konto',exact:true}).waitFor();}
   async function menu(name){await button(name).click();await page.getByRole('heading',{name,exact:true}).waitFor();await page.waitForFunction(()=>document.querySelector('table')||document.querySelector('#screen').textContent.includes('Brak danych'));}
   async function post(path,body,method='POST'){return page.evaluate(async({path,body,method})=>{const me=await fetch('/school/api/v1/auth/me').then(r=>r.json());const r=await fetch('/school/api/v1'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':me.data.csrf},body:JSON.stringify(body)});return {status:r.status,body:r.status===204?null:await r.json()};},{path,body,method});}
   await page.goto(config.url);await login('driver');await overflow();
   if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-account.png'),fullPage:true});
   await menu('Moje przejazdy');await page.locator('table tbody tr').first().waitFor();assert.equal(await page.locator('table tbody tr').count(),25);
   await overflow();if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-trips.png'),fullPage:true});
   const firstText=await page.locator('table tbody').textContent();await button('Następna strona').click();await page.waitForFunction(()=>document.querySelector('#screen').textContent.includes('Koniec wyników.'));assert.notEqual(await page.locator('table tbody').textContent(),firstText);
   await button('Pierwsza strona').click();await page.locator('table tbody tr').nth(24).waitFor();
   await button('Nowy przejazd').click();let d=page.locator('dialog');await d.waitFor();await d.locator('input[name=title]').fill('');await button('Utwórz przejazd',d).click();assert.match(await d.locator('[data-error=title]').textContent(),/1–120/);
   await page.keyboard.press('Escape');await d.waitFor({state:'detached'});assert.equal(await button('Nowy przejazd').evaluate(n=>n===document.activeElement),true);
   await button('Nowy przejazd').click();d=page.locator('dialog');const title='Przejazd '+label+' <img src=x onerror=window.__xss=1>';
   await d.locator('input[name=title]').fill(title);await d.locator('textarea[name=note]').fill(('Syntetyczna notatka. '+('Długi tekst '.repeat(40))).trim());
   await button('Utwórz przejazd',d).click();await page.getByRole('heading',{name:title,exact:true}).waitFor();assert.equal(await page.evaluate(()=>window.__xss),undefined);assert.equal(await page.locator('#screen img').count(),0);
   const tid=await page.locator('dd').first().textContent();
   await button('Rozpocznij zapis syntetyczny').click();await button('Zakończ zapis').waitFor();
   await button('Obserwacja pasażera').click();d=page.locator('dialog');await d.locator('input[name=signal_id]').fill('synthetic-light');await d.locator('select[name=state]').selectOption('UNKNOWN');await d.locator('select[name=event_type]').selectOption('STATE_START');
   await button('Zapisz obserwację',d).click();assert.match(await d.locator('[data-error=event_type]').textContent(),/Nieznany/);
   await d.locator('select[name=state]').selectOption('RED');await d.locator('select[name=event_type]').selectOption('STATE_SEEN');await button('Zapisz obserwację',d).click();await d.waitFor({state:'detached'});await page.locator('table tbody tr').first().waitFor();
   await button('Zakończ zapis').click();await button('Adnotacja historyczna').waitFor();await overflow();if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-trip.png'),fullPage:true});
   // Response-loss simulation: server commits metadata, browser sees a network failure.
   await button('Edytuj metadane').click();d=page.locator('dialog');await d.locator('input[name=title]').fill(title+' zmiana');
   let lost=true;await page.route('**/school/api/v1/trips/'+tid,async route=>{if(route.request().method()==='PATCH'&&lost){lost=false;await route.fetch();await route.abort('failed');}else await route.continue();});
   await button('Zapisz',d).click();await d.getByRole('status').filter({hasText:'nieznany'}).waitFor();assert.equal(await d.locator('input[name=title]').inputValue(),title+' zmiana');
   await button('Zapisz',d).click();await button('Użyj aktualnej rewizji do ponownego zapisu',d).waitFor();await button('Użyj aktualnej rewizji do ponownego zapisu',d).click();await button('Zapisz',d).click();await d.waitFor({state:'detached'});await page.unroute('**/school/api/v1/trips/'+tid);
   await page.getByRole('heading',{name:title+' zmiana',exact:true}).waitFor();
   await button('Historia / korekta').first().click();await page.getByRole('heading',{name:'Obserwacja · synthetic-light',exact:true}).waitFor();await button('Dodaj korektę').click();d=page.locator('dialog');await d.locator('select[name=state]').selectOption('GREEN');await d.locator('input[name=reason]').fill('Poprawka syntetyczna');await button('Zapisz korektę',d).click();await d.waitFor({state:'detached'});await page.getByRole('cell',{name:'Poprawka syntetyczna',exact:true}).waitFor();
   await overflow();if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-corrections.png'),fullPage:true});
   await menu('Moje obserwacje');await page.locator('input[name=trip_id]').fill(tid);await page.locator('select[name=state]').selectOption('GREEN');await button('Zastosuj filtry').click();await page.waitForFunction(()=>document.querySelectorAll('tbody tr').length===1);
   assert.match(await page.locator('tbody').textContent(),/Zielone/);await overflow();if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-observations.png'),fullPage:true});
   await page.locator('select[name=state]').selectOption('RED');await button('Zastosuj filtry').click();await page.getByRole('status').filter({hasText:'Brak danych dla wybranych filtrów'}).waitFor();
   await page.locator('input[name=trip_id]').fill('');await page.locator('select[name=state]').selectOption('');await button('Zastosuj filtry').click();await page.locator('table tbody tr').nth(24).waitFor();await button('Następna strona').click();await page.waitForFunction(()=>document.querySelector('#screen').textContent.includes('Koniec wyników.'));
   await menu('Moje przejazdy');await page.locator('select[name=status]').selectOption('COMPLETE');await button('Zastosuj filtry').click();await page.getByText(title+' zmiana',{exact:true}).waitFor();await page.getByRole('row').filter({hasText:title+' zmiana'}).getByRole('button',{name:'Szczegóły',exact:true}).click();await button('Udostępnij analitykowi').click();d=page.locator('dialog');await d.locator('input[name=analyst_email]').fill('analyst@example.test');await button('Udostępnij',d).click();await button('Cofnij udostępnienie').waitFor();
   await button('Cofnij udostępnienie').click();await button('Cofnij zgodę',page.locator('dialog')).click();await button('Udostępnij analitykowi').waitFor();
   const download=page.waitForEvent('download');await button('Eksportuj przejazd').click();await download;
   await button('Archiwizuj przejazd').click();d=page.locator('dialog');await d.locator('input[name=reason]').fill('Archiwum demonstracyjne');await button('Potwierdź archiwizację',d).click();await page.getByRole('heading',{name:'Moje przejazdy',exact:true}).waitFor();
   await page.locator('select[name=archived]').selectOption('true');await button('Zastosuj filtry').click();await page.getByText(title+' zmiana',{exact:true}).waitFor();
   // Expiry is a real server logout with unchanged DOM, then the next read clears private state.
   assert.equal((await post('/auth/logout',{})).status,204);await button('Pierwsza strona').click();await page.locator('input[name=email]').waitFor();assert.equal(await page.locator('table').count(),0);assert.equal(await page.locator('dialog').count(),0);
   await login('other');await menu('Moje przejazdy');assert.doesNotMatch(await page.locator('#screen').textContent(),/Historia demonstracyjna|Przejazd desktop|Przejazd phone|Przejazd narrow/);await overflow();assert.equal(await page.evaluate(()=>localStorage.length),0);
   await button('Konto').click();await button('Wyloguj').click();await page.locator('input[name=email]').waitFor();assert.equal(await page.locator('table').count(),0);
   assert.deepEqual(errors,[]);report.push({label,width,height,status:'PASS'});await context.close();console.log('PASS '+label+': full records flow, filters/pages, validation, conflict/network loss, session switch, focus, overflow');
  }
  fs.mkdirSync('artifacts',{recursive:true});fs.writeFileSync('artifacts/stage7-browser.json',JSON.stringify(report,null,2));
 }finally{await browser.close();if(!child.stdin.writableEnded)child.stdin.end('stop\n');}
 if(stderr)throw new Error('Fixture stderr: '+stderr);
})().catch(e=>{console.error(e.message.replace(/(#(?:verify|reset)=)[A-Za-z0-9_-]+/g,'$1[redacted]'));if(!child.stdin.writableEnded)child.stdin.end('stop\n');process.exitCode=1;});
