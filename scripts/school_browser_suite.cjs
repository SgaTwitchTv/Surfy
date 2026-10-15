// Each case starts its own actual server/SMTP/temporary DB. Continue to collect failures.
const {spawnSync}=require('node:child_process'),fs=require('node:fs'),path=require('node:path');
const output=path.resolve(process.env.GW_TEST_OUTPUT||'artifacts/stage10');fs.mkdirSync(output,{recursive:true});
const names=['accounts','resources','ui','roles','reauth','navigation'];const results=[];
for(const name of names){
 const result=spawnSync(process.execPath,['scripts/check_school_'+name+'.cjs'],{encoding:'utf8',timeout:600000,env:{...process.env,GW_SCREENSHOT_ROOT:path.join(output,'screenshots',name)},maxBuffer:8*1024*1024});
 const log=(result.stdout||'')+(result.stderr||'');fs.writeFileSync(path.join(output,'browser-'+name+'.txt'),log);
 console.log(log);results.push({name,exit:result.status,error:result.error?.code||null});
}
fs.writeFileSync(path.join(output,'browser-tests.json'),JSON.stringify(results,null,2));
if(results.some(r=>r.exit!==0))process.exitCode=1;
