// Dedicated synthetic DB+SMTP, actual production KDF, desktop+phone. No token logging.
const {chromium}=require(process.env.GW_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process'),readline=require('node:readline');
const child=spawn(process.env.GW_PYTHON||'python',['-m','scripts.school_browser_fixture'],{stdio:['pipe','pipe','pipe']});
const PASS='Browser password 123!',NEW='Browser new password 456!',CHANGED='Browser changed password 789!';
let stderr='';child.stderr.on('data',d=>stderr+=d);
(async()=>{
 const config=await new Promise((resolve,reject)=>{const rl=readline.createInterface({input:child.stdout});rl.once('line',line=>{rl.close();resolve(JSON.parse(line));});child.once('exit',code=>reject(new Error('Synthetic fixture exited '+code)));});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const output=path.resolve('artifacts/school-accounts');fs.mkdirSync(output,{recursive:true});
 async function mail(address,kind){for(let i=0;i<100;i++){const response=await fetch(config.mailbox+'/messages'),messages=await response.json();const message=messages.filter(m=>m.to===address&&m.body.includes('#'+kind+'=')).at(-1);if(message)return message.body.match(/https?:\/\/[^\s]+/)[0];await new Promise(r=>setTimeout(r,100));}throw new Error('Synthetic email timeout');}
 async function login(page,address,password){await page.locator('input[name=email]').fill(address);await page.locator('input[name=password]').fill(password);await page.getByRole('button',{name:'Potwierdź',exact:true}).click();await page.getByRole('heading',{name:'Twoje konto',exact:true}).waitFor();}
 try{
  for(const [label,width,height] of [['desktop',1280,900],['phone',390,844]]){
   const context=await browser.newContext({viewport:{width,height}}),page=await context.newPage(),errors=[];
   page.on('pageerror',error=>errors.push(error.message));const address=label+'@example.test';
   await page.goto(config.url);await page.locator('input[name=email]').waitFor();
   await page.getByRole('button',{name:'Rejestracja',exact:true}).click();
   await page.locator('input[name=display_name]').fill('Synthetic '+label);await page.locator('input[name=email]').fill(address);
   await page.locator('input[name=password]').fill(PASS);await page.locator('input[name=password_confirmation]').fill('different password');
   await page.getByRole('button',{name:'Potwierdź',exact:true}).click();assert.match(await page.locator('[data-error=password_confirmation]').textContent(),/identyczne/);
   await page.locator('input[name=password_confirmation]').fill(PASS);await page.getByRole('button',{name:'Potwierdź',exact:true}).click();
   await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Sprawdź pocztę'));
   await page.goto(await mail(address,'verify'));await page.getByRole('button',{name:'Potwierdź aktywację',exact:true}).waitFor();assert.equal(new URL(page.url()).hash,'');
   await page.getByRole('button',{name:'Potwierdź aktywację',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Konto aktywne'));
   await login(page,address,PASS);assert.equal(await page.locator('body').evaluate(n=>n.scrollWidth<=innerWidth),true);
   assert.equal(await page.evaluate(()=>localStorage.length),0);await page.screenshot({path:path.join(output,label+'-account.png'),fullPage:true});
   await page.getByRole('button',{name:'Potwierdź tożsamość',exact:true}).click();await page.locator('input[name=password]').fill(PASS);await page.getByRole('button',{name:'Potwierdź',exact:true}).click();await page.getByRole('heading',{name:'Twoje konto',exact:true}).waitFor();
   await page.getByRole('button',{name:'Wyloguj',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#screen input[name=email]'));
   await page.getByRole('button',{name:'Reset hasła',exact:true}).click();await page.locator('input[name=email]').fill(address);await page.getByRole('button',{name:'Potwierdź',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Sprawdź pocztę'));
   await page.goto(await mail(address,'reset'));await page.locator('input[name=password_confirmation]').waitFor();assert.equal(new URL(page.url()).hash,'');
   await page.locator('input[name=password]').fill(NEW);await page.locator('input[name=password_confirmation]').fill(NEW);await page.screenshot({path:path.join(output,label+'-reset.png'),fullPage:true});
   await page.getByRole('button',{name:'Potwierdź',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#screen input[name=email]'));await login(page,address,NEW);
   await page.getByRole('button',{name:'Zmień hasło',exact:true}).click();await page.locator('input[name=current_password]').fill(NEW);await page.locator('input[name=new_password]').fill(CHANGED);await page.locator('input[name=password_confirmation]').fill(CHANGED);await page.getByRole('button',{name:'Potwierdź',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#screen input[name=email]'));
   await login(page,address,CHANGED);await page.getByRole('button',{name:'Wyloguj wszystkie sesje',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#screen input[name=email]'));
   assert.deepEqual(errors,[]);await context.close();console.log('PASS '+label+': register/validation/mail/verify/login/reauth/logout/reset/change/logout-all; no overflow/storage/page errors');
  }
 }finally{await browser.close();if(!child.stdin.writableEnded)child.stdin.end('stop\n');}
 if(stderr)throw new Error('Synthetic fixture stderr: '+stderr);
})().catch(error=>{console.error(error.message.replace(/(#(?:verify|reset)=)[A-Za-z0-9_-]+/g,"$1[redacted]"));if(!child.stdin.writableEnded)child.stdin.end('stop\n');process.exitCode=1;});
