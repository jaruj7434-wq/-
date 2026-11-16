const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const out=process.argv[2],dur=+process.argv[3],fps=30;fs.mkdirSync(out,{recursive:true});
const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:720,height:1280}});p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8765/index.html');await p.waitForFunction('window.ready===true',{timeout:60000});
const n=Math.round(dur*fps);const t0=Date.now();
for(let i=0;i<n;i++){await p.evaluate(t=>renderAt(t),i/fps);await p.screenshot({path:`${out}/f${String(i).padStart(5,'0')}.jpg`,type:'jpeg',quality:92});
 if(i%150==0)console.log(i,n,((Date.now()-t0)/1000).toFixed(0)+'s');}
await b.close();console.log('done');})();
