// Fixed denominator: all portal code + baseline guidance/CV contract view logic.
const fs=require('node:fs'),path=require('node:path'),{fileURLToPath}=require('node:url'),{spawnSync}=require('node:child_process');
const toIstanbul=require('v8-to-istanbul'),lib=require('istanbul-lib-coverage'),report=require('istanbul-lib-report'),reports=require('istanbul-reports');
const repo=path.resolve(__dirname,'..'),output=path.resolve(process.env.GW_TEST_OUTPUT||'artifacts/stage10');
const targets=['greenwave/school_accounts/web/account.js',...fs.readdirSync(path.join(repo,'greenwave/school_accounts/web/portal')).filter(n=>n.endsWith('.mjs')).map(n=>'greenwave/school_accounts/web/portal/'+n),'greenwave/web/driver-ui.js','greenwave/web/vision-workbench-ui.js'];
function walk(dir){return fs.existsSync(dir)?fs.readdirSync(dir,{withFileTypes:true}).flatMap(d=>d.isDirectory()?walk(path.join(dir,d.name)):[path.join(dir,d.name)]):[];}
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 // New directory per invocation: stale successful runs never contribute to a failing run.
 const raw=fs.mkdtempSync(path.join(output,'v8-')),nodeRaw=path.join(raw,'node'),browserRaw=path.join(raw,'browser');
 const env={...process.env,NODE_V8_COVERAGE:nodeRaw,GW_JS_COVERAGE_DIR:browserRaw};
 const unit=spawnSync(process.execPath,['--test','tests/school_portal.cjs','tests/school_roles.cjs','tests/school_reauth.cjs','tests/school_driving.cjs','tests/driver_ui.cjs','tests/vision_workbench_ui.cjs'],{cwd:repo,env,encoding:'utf8',timeout:120000});
 fs.writeFileSync(path.join(output,'js-tests.txt'),(unit.stdout||'')+(unit.stderr||''));console.log(unit.stdout,unit.stderr||'');
 const browser=spawnSync(process.execPath,['scripts/school_browser_suite.cjs'],{cwd:repo,env,encoding:'utf8',timeout:3600000,maxBuffer:16*1024*1024});
 console.log(browser.stdout,browser.stderr||'');
 const map=lib.createCoverageMap({}),seen=new Set();
 for(const file of walk(raw).filter(f=>f.endsWith('.json'))){for(const e of JSON.parse(fs.readFileSync(file,'utf8')).result||[]){
   let name;if(e.url.startsWith('/school/static/'))name='greenwave/school_accounts/web/'+e.url.slice('/school/static/'.length);
   else if(e.url.startsWith('file:'))name=path.relative(repo,fileURLToPath(e.url)).split(path.sep).join('/');else continue;
   if(!targets.includes(name))continue;
   const filename=path.join(repo,name),source=fs.readFileSync(filename,'utf8');
   if(e.source!==undefined&&e.source!==source)throw new Error('Browser served different source: '+name);
   const converter=toIstanbul(filename,0,{source});await converter.load();converter.applyCoverage(e.functions);map.merge(converter.toIstanbul());seen.add(name);
 }}
 for(const name of targets)if(!seen.has(name)){const filename=path.join(repo,name),source=fs.readFileSync(filename,'utf8');const converter=toIstanbul(filename,0,{source});await converter.load();converter.applyCoverage([{functionName:'(empty-report)',ranges:[{startOffset:0,endOffset:source.length,count:0}],isBlockCoverage:true}]);map.merge(converter.toIstanbul());}
 const context=report.createContext({dir:path.join(output,'js'),coverageMap:map});
 for(const format of ['json','json-summary','text','lcovonly','html'])reports.create(format).execute(context);
 fs.writeFileSync(path.join(output,'js-scope.json'),JSON.stringify({targets,unexecuted:targets.filter(t=>!seen.has(t)),unitsExit:unit.status,browserExit:browser.status},null,2));
 const summary=map.getCoverageSummary().toJSON();console.log('JS final totals:',JSON.stringify(summary));
 if(unit.status!==0||browser.status!==0||summary.lines.pct<70||summary.branches.pct<70)process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exitCode=1;});
