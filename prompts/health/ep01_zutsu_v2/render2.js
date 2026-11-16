const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const mode=process.argv[2];const b=await chromium.launch();
const p=await b.newPage({viewport:{width:720,height:1280}});p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8766/v2/index.html');await p.waitForFunction('window.ready===true',{timeout:60000});
if(mode==='preview'){for(const t of process.argv.slice(3).map(Number)){await p.evaluate(t=>renderAt(t),t);await p.screenshot({path:`v2/prev_${t}.jpg`,type:'jpeg',quality:80});}}
else{const out='v2/frames',dur=+process.argv[3],fps=30;fs.mkdirSync(out,{recursive:true});const n=Math.round(dur*fps);
 for(let i=0;i<n;i++){await p.evaluate(t=>renderAt(t),i/fps);await p.screenshot({path:`${out}/f${String(i).padStart(5,'0')}.jpg`,type:'jpeg',quality:92});}console.log('done',n);}
await b.close();})();
