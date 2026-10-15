const fs=require('node:fs'),path=require('node:path');
const {chromium:engine}=require(process.env.GW_PLAYWRIGHT_MODULE||'playwright');
let serial=0;
exports.chromium={async launch(options={}){
  const channel=process.env.GW_BROWSER_CHANNEL;
  const browser=await engine.launch({...options,...(channel?{channel:channel==='chromium'?undefined:channel}:{})});
  const create=browser.newContext.bind(browser);
  browser.newContext=async options=>{
    const context=await create(options),newPage=context.newPage.bind(context),close=context.close.bind(context),pages=[];
    context.newPage=async()=>{const page=await newPage();if(process.env.GW_JS_COVERAGE_DIR){await page.coverage.startJSCoverage({resetOnNavigation:false});pages.push(page);}return page;};
    context.close=async()=>{
      for(const page of pages){if(page.isClosed())throw new Error('Coverage page closed before collection');
        const entries=(await page.coverage.stopJSCoverage()).filter(e=>/^https?:/.test(e.url)&&new URL(e.url).pathname.startsWith('/school/static/')&&/\.(mjs|js)$/.test(new URL(e.url).pathname));
        // URL path only; strip server address/query/fragment. No user data in source.
        const result=entries.map(e=>({...e,url:new URL(e.url).pathname}));
        const directory=path.resolve(process.env.GW_JS_COVERAGE_DIR);fs.mkdirSync(directory,{recursive:true});
        fs.writeFileSync(path.join(directory,`browser-${process.pid}-${++serial}.json`),JSON.stringify({result}));
      }return close();
    };return context;
  };return browser;
}};
