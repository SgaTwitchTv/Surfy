// API read smoke in real browser sessions; target tables remain stage7.
const {chromium}=require('./browser_test_support.cjs');
const assert=require('node:assert/strict'),{spawn}=require('node:child_process'),readline=require('node:readline');
const child=spawn(process.env.GW_PYTHON||'python',['-m','scripts.school_browser_fixture'],{env:{...process.env,GW_RESOURCE_FIXTURE:'1'},stdio:['pipe','pipe','pipe']});
let stderr='';child.stderr.on('data',d=>stderr+=d);
(async()=>{
 const config=await new Promise((resolve,reject)=>{const rl=readline.createInterface({input:child.stdout});rl.once('line',line=>{rl.close();resolve(JSON.parse(line));});child.once('exit',code=>reject(new Error('Fixture exited '+code)));});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  for(const [label,width,height] of [['desktop',1280,900],['phone',390,844]]){
   for(const who of ['driver','analyst','admin']){
    const context=await browser.newContext({viewport:{width,height}}),page=await context.newPage();
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(config.url);await page.locator('input[name=email]').fill(who+'@example.test');
    await page.locator('input[name=password]').fill('Browser password 123!');await page.getByRole('button',{name:'Potwierdź',exact:true}).click();
    await page.getByRole('heading',{name:'Twoje konto',exact:true}).waitFor();
    async function read(path){return page.evaluate(async path=>{const r=await fetch('/school/api/v1'+path);return {status:r.status,body:await r.json()};},path);}
    assert.equal((await read('/trips')).status,200);
    assert.equal((await read('/trips/'+config.trips.other)).status,404);
    assert.equal((await read('/trips/'+config.trips.shared)).status,who==='admin'?404:200);
    if(who==='analyst'){assert.equal((await read('/trips?scope=shared')).body.data.items.length,1);assert.equal((await read('/trips/'+config.trips.shared+'/export')).status,404);}
    assert.equal(await page.locator('body').evaluate(n=>n.scrollWidth<=innerWidth),true);
    await page.getByRole('button',{name:'Wyloguj',exact:true}).click();await page.locator('input[name=email]').waitFor();
    assert.equal((await read('/trips')).status,401);assert.deepEqual(errors,[]);await context.close();
   }
   console.log('PASS '+label+': login, own/shared reads, foreign/admin/export denial, logout 401');
  }
 }finally{await browser.close();if(!child.stdin.writableEnded)child.stdin.end('stop\n');}
 if(stderr)throw new Error('Fixture stderr: '+stderr);
})().catch(e=>{console.error(e.message);if(!child.stdin.writableEnded)child.stdin.end('stop\n');process.exitCode=1;});
