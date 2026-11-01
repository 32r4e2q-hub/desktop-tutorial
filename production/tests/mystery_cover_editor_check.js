// Exercise the standalone editor's state transitions without a browser or network.
// Canvas is a stub: this tests behavior, not visual fidelity.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const markup = fs.readFileSync(process.argv[2], 'utf8');
const js = markup.match(/<script>([\s\S]*?)<\/script>/)[1];
let blobs = 0, imageDraws = [];
const context = {
  clearRect(){}, drawImage(...args){imageDraws.push(args);}, fillRect(){}, strokeRect(){},
  beginPath(){}, roundRect(){}, fill(){}, stroke(){}, fillText(){}, strokeText(){},
  measureText(text){return {width:text.length*30}}, save(){}, restore(){},
};
function element(value='') { return {value, disabled:false, style:{}, files:[], handlers:{},
  addEventListener(type,handler){this.handlers[type]=handler;},
  fire(type){if(this.handlers[type])this.handlers[type]();},
}; }
const elements={canvas:element(),episode:element('1'),line1:element('逃亡78天的西口彰'),
  line2:element('却被女孩一眼认出'),save:element(),status:element(),screenshot:element(),package:element()};
elements.canvas.getContext=()=>context;
elements.canvas.toBlob=cb=>{blobs++;cb({});};
elements.save.disabled=true;
class FakeImage {
  constructor(){this.naturalWidth=0;this.naturalHeight=0;this.complete=false;}
  set src(value){this._src=value; this.naturalWidth=1920;this.naturalHeight=850;this.complete=true;
    queueMicrotask(()=>{if(this.onload)this.onload()});}
  get src(){return this._src;}
}
const url={createObjectURL(file){return `blob:${file.name||'export'}`},revokeObjectURL(){}};
const document={getElementById(id){assert.ok(elements[id],`missing ${id}`);return elements[id]},
 fonts:{load:()=>Promise.resolve()},body:{appendChild(){}},createElement(){return {click(){},remove(){}}}};
const sandbox={document,Image:FakeImage,URL:url,location:{protocol:'file:'},
 setTimeout:()=>0,console};
(async()=>{
 vm.runInNewContext(js,sandbox);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(elements.save.disabled,true,'must require screenshot');
 elements.screenshot.files=[{name:'first.jpg'}];elements.screenshot.fire('change');
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(elements.save.disabled,false);
 assert.ok(imageDraws.some(args=>args.length===9 && args[0].src==='blob:first.jpg'));
 elements.save.fire('click');assert.equal(blobs,1);
 elements.episode.value='2';elements.episode.fire('input');
 assert.equal(elements.save.disabled,true,'new episode must clear old screenshot');
 elements.screenshot.files=[{name:'second.jpg'}];elements.screenshot.fire('change');
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(elements.save.disabled,false);
 assert.ok(imageDraws.some(args=>args.length===9 && args[0].src==='blob:second.jpg'));
 elements.line1.value='';elements.line1.fire('input');assert.equal(elements.save.disabled,true);
 elements.line1.value='新标题';elements.line1.fire('input');assert.equal(elements.save.disabled,false);
 elements.episode.value='10000';elements.episode.fire('input');assert.equal(elements.save.disabled,true);
 console.log('editor screenshot selection, reset, and export gating passed');
})().catch(err=>{console.error(err);process.exitCode=1});
