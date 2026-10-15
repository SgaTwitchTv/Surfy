// Actual backend + production KDF, temporary synthetic DB, no public provisioning.
const {chromium}=require('./browser_test_support.cjs');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process'),readline=require('node:readline');
const child=spawn(process.env.GW_PYTHON||'python',['-m','scripts.school_browser_fixture'],{env:{...process.env,GW_RESOURCE_FIXTURE:'1',GW_SCHOOL_UI_FIXTURE:'1'},stdio:['pipe','pipe','pipe']});
let stderr='';child.stderr.on('data',d=>stderr+=d);const PASS='Browser password 123!';
(async()=>{
 const config=await new Promise((resolve,reject)=>{const rl=readline.createInterface({input:child.stdout});rl.once('line',line=>{rl.close();resolve(JSON.parse(line));});child.once('exit',code=>reject(new Error('Fixture exited '+code)));});
 const browser=await chromium.launch({channel:'msedge',headless:true});const out=path.resolve(process.env.GW_SCREENSHOT_ROOT||'docs/school-app/screenshots');fs.mkdirSync(out,{recursive:true});
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
   await overflow();if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-trips.png'),fullPage:true});if(!(await page.locator('details').evaluate(n=>n.open)))await page.locator('summary').click();
   const firstText=await page.locator('table tbody').textContent();await button('Następna strona').click();await page.waitForFunction(()=>document.querySelector('#screen').textContent.includes('Koniec wyników.'));assert.notEqual(await page.locator('table tbody').textContent(),firstText);
   console.log('UI pagination first '+label);await button('Pierwsza strona').click();await page.locator('table tbody tr').nth(24).waitFor();
   await button('Nowy przejazd').click();let d=page.locator('dialog');await d.waitFor();await d.locator('input[name=title]').fill('');await button('Utwórz przejazd',d).click();assert.match(await d.locator('[data-error=title]').textContent(),/1–120/);
   await d.locator('input[name=title]').focus();await page.keyboard.press('Tab');assert.equal(await d.locator('textarea[name=note]').evaluate(n=>n===document.activeElement),true);await page.keyboard.press('Shift+Tab');assert.equal(await d.locator('input[name=title]').evaluate(n=>n===document.activeElement),true);await page.keyboard.press('Escape');await d.waitFor({state:'detached'});assert.equal(await button('Nowy przejazd').evaluate(n=>n===document.activeElement),true);
   await button('Nowy przejazd').click();d=page.locator('dialog');const title='Przejazd '+label+' <img src=x onerror=window.__xss=1>',editedTitle='Poranny przejazd · '+label;
   await d.locator('input[name=title]').fill(title);await d.locator('textarea[name=note]').fill(('Syntetyczny zapis obserwacji: start przy dworcu i zakończenie odcinka demonstracyjnego bez prawdziwego GPS. '.repeat(4)).trim());
   await button('Utwórz przejazd',d).click();await page.getByRole('heading',{name:title,exact:true}).waitFor();assert.equal(await page.evaluate(()=>window.__xss),undefined);assert.equal(await page.locator('#screen img').count(),0);
   const tid=await page.locator('dd').first().textContent();
   let loseStart=true;const startKeys=[];await page.route('**/school/api/v1/navigation',async route=>{startKeys.push(route.request().headers()['idempotency-key']);if(loseStart){loseStart=false;await route.fetch();await route.abort('failed');}else await route.continue();});
   await button('Rozpocznij zapis syntetyczny').click();await page.getByRole('status').filter({hasText:'Start niepotwierdzony'}).waitFor();await button('Rozpocznij zapis syntetyczny').click();await button('Zakończ zapis').waitFor();assert.ok(startKeys.length===2&&startKeys[0]===startKeys[1],'start must reuse its original key');await page.unroute('**/school/api/v1/navigation');
   await button('Obserwacja pasażera').click();d=page.locator('dialog');await d.locator('input[name=signal_id]').fill('synthetic-light');await d.locator('select[name=state]').selectOption('UNKNOWN');await d.locator('select[name=event_type]').selectOption('STATE_START');
   await button('Zapisz obserwację',d).click();assert.match(await d.locator('[data-error=event_type]').textContent(),/Nieznany/);
   await d.locator('select[name=state]').selectOption('RED');await d.locator('select[name=event_type]').selectOption('STATE_SEEN');await button('Zapisz obserwację',d).click();await d.waitFor({state:'detached'});await page.locator('table tbody tr').first().waitFor();
   let loseFinish=true,releasePoll;const pollGate=new Promise(r=>releasePoll=r),finishKeys=[];
   await page.route('**/school/api/v1/navigation/**',async route=>{if(route.request().method()==='GET'){await pollGate;try{await route.continue();}catch{}}else{finishKeys.push(route.request().headers()['idempotency-key']);if(loseFinish){loseFinish=false;await route.fetch();await route.abort('failed');}else await route.continue();}});
   await button('Zakończ zapis').click();await page.getByRole('status').filter({hasText:'Nieznany wynik finalizacji'}).waitFor();await button('Zakończ zapis').click();await button('Adnotacja historyczna').waitFor();assert.ok(finishKeys.length===2&&finishKeys[0]===finishKeys[1],'finish must reuse its original key');releasePoll();await page.unroute('**/school/api/v1/navigation/**');await overflow();
   // Render maximum-length unbroken data; preserve originals when annotating a closed trip.
   await button('Adnotacja historyczna').click();d=page.locator('dialog');await d.locator('input[name=signal_id]').fill('S'.repeat(120));await d.locator('select[name=state]').selectOption('OFF');await button('Zapisz obserwację',d).click();await d.waitFor({state:'detached'});await page.locator('tbody tr').nth(1).waitFor();await overflow();
   await button('Edytuj metadane').click();d=page.locator('dialog');await d.locator('input[name=title]').fill('T'.repeat(120));await d.locator('textarea[name=note]').fill('N'.repeat(1000));await button('Zapisz',d).click();await d.waitFor({state:'detached'});await page.getByRole('heading',{name:'T'.repeat(120),exact:true}).waitFor();await overflow();

   // Response-loss simulation: server commits metadata, browser sees a network failure.
   await button('Edytuj metadane').click();d=page.locator('dialog');await d.locator('input[name=title]').fill(editedTitle);await d.locator('textarea[name=note]').fill('Syntetyczny przejazd od dworca do centrum. Bez prawdziwego GPS; obserwacje zapisane osobno, z zachowaniem historii korekt.');
   let lost=true;await page.route('**/school/api/v1/trips/'+tid,async route=>{if(route.request().method()==='PATCH'&&lost){lost=false;await route.fetch();await route.abort('failed');}else await route.continue();});
   await button('Zapisz',d).click();await d.getByRole('status').filter({hasText:'nieznany'}).waitFor();assert.equal(await d.locator('input[name=title]').inputValue(),editedTitle);
   await button('Zapisz',d).click();await button('Użyj aktualnej rewizji do ponownego zapisu',d).waitFor();await button('Użyj aktualnej rewizji do ponownego zapisu',d).click();await button('Zapisz',d).click();await d.waitFor({state:'detached'});await page.unroute('**/school/api/v1/trips/'+tid);
   await page.getByRole('heading',{name:editedTitle,exact:true}).waitFor();await page.locator('table tbody tr').nth(1).waitFor();await overflow();if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-trip.png'),fullPage:true});
   await page.getByRole('row').filter({hasText:'synthetic-light'}).getByRole('button',{name:'Historia / korekta',exact:true}).click();await page.getByRole('heading',{name:'Obserwacja · synthetic-light',exact:true}).waitFor();await button('Dodaj korektę').click();d=page.locator('dialog');await d.locator('select[name=state]').selectOption('GREEN');await d.locator('input[name=reason]').fill('Poprawka syntetyczna');await button('Zapisz korektę',d).click();await d.waitFor({state:'detached'});await page.getByRole('cell',{name:'Poprawka syntetyczna',exact:true}).waitFor();
   await overflow();if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-corrections.png'),fullPage:true});
   await menu('Moje obserwacje');if(!(await page.locator('details').evaluate(n=>n.open)))await page.locator('summary').click();await page.locator('input[name=trip_id]').fill(tid);await page.locator('select[name=state]').selectOption('GREEN');await button('Zastosuj filtry').click();await page.waitForFunction(()=>document.querySelectorAll('tbody tr').length===1);
   assert.match(await page.locator('tbody').textContent(),/Zielone/);await overflow();if(width<721){const wrap=page.locator('.table-scroll');await wrap.focus();await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>document.querySelector('.table-scroll').scrollLeft>0);await wrap.evaluate(n=>n.scrollLeft=0);}if(label!=='narrow')await page.screenshot({path:path.join(out,label+'-observations.png'),fullPage:true});
   // Hold an older RED response; changing filters aborts it before GREEN becomes current.
   let releaseOld,seenOld,held=true;const heldResponse=new Promise(r=>releaseOld=r),receivedOld=new Promise(r=>seenOld=r);
   await page.route('**/school/api/v1/observations?*',async route=>{if(new URL(route.request().url()).searchParams.get('state')==='RED'&&held){held=false;const reply=await route.fetch();seenOld();await heldResponse;try{await route.fulfill({response:reply});}catch{}}else await route.continue();});
   await page.locator('select[name=state]').selectOption('RED');await button('Zastosuj filtry').click();await receivedOld;
   await page.locator('select[name=state]').selectOption('GREEN');await button('Zastosuj filtry').click();await page.waitForFunction(()=>document.querySelectorAll('tbody tr').length===1);releaseOld();await page.unroute('**/school/api/v1/observations?*');assert.match(await page.locator('tbody').textContent(),/Zielone/);
   await page.locator('select[name=state]').selectOption('RED');await button('Zastosuj filtry').click();await page.getByRole('status').filter({hasText:'Brak danych dla wybranych filtrów'}).waitFor();
   await page.locator('input[name=trip_id]').fill('');await page.locator('select[name=state]').selectOption('');await button('Zastosuj filtry').click();await page.locator('table tbody tr').nth(24).waitFor();await button('Następna strona').click();await page.waitForFunction(()=>document.querySelector('#screen').textContent.includes('Koniec wyników.'));
   await menu('Moje przejazdy');if(!(await page.locator('details').evaluate(n=>n.open)))await page.locator('summary').click();await page.locator('select[name=status]').selectOption('COMPLETE');await button('Zastosuj filtry').click();await page.getByText(editedTitle,{exact:true}).waitFor();await page.getByRole('row').filter({hasText:editedTitle}).getByRole('button',{name:'Szczegóły',exact:true}).click();await button('Udostępnij analitykowi').click();d=page.locator('dialog');await d.locator('input[name=analyst_email]').fill('analyst@example.test');await button('Udostępnij',d).click();await button('Cofnij udostępnienie').waitFor();
   await button('Cofnij udostępnienie').click();const oldShare=await page.evaluate(async tid=>(await fetch('/school/api/v1/trips/'+tid).then(r=>r.json())).data.share.id,tid);
   assert.equal((await post('/trips/'+tid+'/share',{expected_share_id:oldShare},'DELETE')).status,204);const regrant=await post('/trips/'+tid+'/share',{analyst_email:'analyst@example.test'});assert.equal(regrant.status,201);
   await button('Cofnij zgodę',page.locator('dialog')).click();await button('Cofnij udostępnienie').waitFor();assert.equal(await page.evaluate(async tid=>(await fetch('/school/api/v1/trips/'+tid).then(r=>r.json())).data.share.id,tid),regrant.body.data.id);
   await button('Cofnij udostępnienie').click();await button('Cofnij zgodę',page.locator('dialog')).click();await button('Udostępnij analitykowi').waitFor();
   const download=page.waitForEvent('download');await button('Eksportuj przejazd').click();const file=await download;assert.equal(fs.readFileSync(await file.path()).subarray(0,2).toString(),'PK');
   await button('Archiwizuj przejazd').click();d=page.locator('dialog');await d.locator('input[name=reason]').fill('Archiwum demonstracyjne');await button('Potwierdź archiwizację',d).click();await page.getByRole('heading',{name:'Moje przejazdy',exact:true}).waitFor();
   if(!(await page.locator('details').evaluate(n=>n.open)))await page.locator('summary').click();await page.locator('select[name=archived]').selectOption('true');await button('Zastosuj filtry').click();await page.getByText(editedTitle,{exact:true}).waitFor();
   // A known FINISH revision conflict requires an explicit updated-revision confirmation.
   await button('Nowy przejazd').click();d=page.locator('dialog');await d.locator('input[name=title]').fill('Konflikt FINISH '+label);await button('Utwórz przejazd',d).click();await page.getByRole('heading',{name:'Konflikt FINISH '+label,exact:true}).waitFor();const conflictTid=await page.locator('dd').first().textContent();
   const started=page.waitForResponse(r=>r.url().endsWith('/school/api/v1/navigation')&&r.request().method()==='POST');await button('Rozpocznij zapis syntetyczny').click();const conflictNav=(await (await started).json()).data;await button('Zakończ zapis').waitFor();
   let releaseRevisionPoll;const revisionGate=new Promise(r=>releaseRevisionPoll=r);await page.route('**/school/api/v1/navigation/'+conflictNav.id,async route=>{await revisionGate;try{await route.continue();}catch{}});
   assert.equal((await post('/trips/'+conflictTid,{expected_revision:conflictNav.revision,title:'Konflikt FINISH '+label,note:'Równoległa zmiana metadanych.'},'PATCH')).status,200);
   await button('Zakończ zapis').click();await button('Sprawdź aktualną rewizję finalizacji').waitFor();releaseRevisionPoll();await page.unroute('**/school/api/v1/navigation/'+conflictNav.id);
   await button('Sprawdź aktualną rewizję finalizacji').click();await button('Potwierdź użycie aktualnej rewizji').click();await button('Zakończ zapis').waitFor();await button('Zakończ zapis').click();await button('Adnotacja historyczna').waitFor();
   await button('Powrót do przejazdów').click();await page.locator('table').waitFor();
   console.log('UI session expiry '+label);
   // Hold a real list read before server logout, then let it receive the real401.
   // Pending requests may otherwise correctly clear the DOM before a later click.
   let releaseExpired,readExpired;const expiredGate=new Promise(r=>releaseExpired=r),expiredRead=new Promise(r=>readExpired=r);
   await page.route('**/school/api/v1/trips?*',async route=>{readExpired();await expiredGate;await route.continue();});
   const deniedList=page.waitForResponse(r=>r.url().includes('/school/api/v1/trips?')&&r.request().method()==='GET'&&r.status()===401);
   await button('Pierwsza strona').click();await expiredRead;
   try{assert.equal((await post('/auth/logout',{})).status,204);}finally{releaseExpired();}
   await deniedList;await page.locator('input[name=email]').waitFor();await page.unroute('**/school/api/v1/trips?*');
   assert.equal(await page.locator('table').count(),0);assert.equal(await page.locator('dialog').count(),0);
   await login('other');await menu('Moje przejazdy');assert.doesNotMatch(await page.locator('#screen').textContent(),/Historia demonstracyjna|Poranny przejazd|Konflikt FINISH/);await overflow();assert.equal(await page.evaluate(()=>localStorage.length),0);
   await button('Konto').click();await button('Wyloguj').click();await page.locator('input[name=email]').waitFor();assert.equal(await page.locator('table').count(),0);
   assert.deepEqual(errors,[]);report.push({label,width,height,status:'PASS'});await context.close();console.log('PASS '+label+': full records flow, filters/pages, validation, conflict/network loss, session switch, focus, overflow');
  }
  fs.mkdirSync('artifacts',{recursive:true});fs.writeFileSync('artifacts/stage7-browser.json',JSON.stringify(report,null,2));
 }finally{await browser.close();if(!child.stdin.writableEnded)child.stdin.end('stop\n');}
 if(stderr)throw new Error('Fixture stderr: '+stderr);
})().catch(e=>{console.error(e.stack.replace(/(#(?:verify|reset)=)[A-Za-z0-9_-]+/g,'$1[redacted]'));if(!child.stdin.writableEnded)child.stdin.end('stop\n');process.exitCode=1;});
