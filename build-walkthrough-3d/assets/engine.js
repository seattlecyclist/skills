/* Build walkthrough engine: rigid bodies made of boxes and cylinders, an assembly sequence of moves,
   pose evaluation at any (step, time), and the physics check that proves every move.

   A build file does:
     const K = Walkthrough.create({units:'in'});
     const {body, inBody, box, cyl, step, mv, at, HOME, drop, slide, orbit} = K;
     ... parts, fixtures, steps ...
     PLAN = K.finish({meta:{...}});

   Coordinates: x along the piece (left to right), y front (0) to back, z up from the floor (z = 0).
   Units are inches by default ({units:'mm'} for millimetres). Nothing here touches the DOM, so the
   same file runs in Node (scripts/verify.js) and in the page. */
(function(root){
"use strict";

function create(opt){
opt=opt||{};
const UNITS=opt.units==='mm'?'mm':'in';
const U=UNITS==='mm'?25.4:1;          // units per inch
const EPS=1e-4*U;

/* ---------- parts and bodies ---------- */
const PARTS=[], BODY={}, BODIES=[], STATIC=[], GROUNDS=[], TABLES=[], PENDANTS=[];
let uid=0, curBody=null;
// a body is one rigid thing that moves as a unit; o: {parent, virtual, loose, temp, pivot, sizeText, listAs}
function body(id,label,o){
  if(BODY[id])throw new Error('duplicate body id '+id);
  if(o&&o.parent&&!BODY[o.parent])throw new Error('body '+id+': parent '+o.parent+' is not defined yet');
  const b=Object.assign({id,label,parent:null,parts:[],events:[],loose:false,children:[]},o||{});
  BODY[id]=b;BODIES.push(b);if(b.parent)BODY[b.parent].children.push(id);return b;
}
function inBody(id,fn){if(!BODY[id])throw new Error('inBody: no body '+id);const prev=curBody;curBody=id;fn();curBody=prev;}
// a part is an axis-aligned box (min, max) in finished position; o: {mat, color, ply, plyBase, decal, note, profile, tape}
function box(name,group,a,b,o){
  if(!curBody)throw new Error('box "'+name+'" is not inside inBody()');
  for(let i=0;i<3;i++)if(!(b[i]>a[i]))throw new Error('box "'+name+'": max must exceed min on every axis');
  const p=Object.assign({id:'p'+(uid++),kind:'box',name,group,min:a.slice(),max:b.slice(),mat:'ply',body:curBody},o||{});
  PARTS.push(p);BODY[p.body].parts.push(p);return p;
}
// a cylinder along 'x', 'y' or 'z', centred on c; it is checked as its bounding box
function cyl(name,group,axis,c,r,len,o){
  if(!curBody)throw new Error('cyl "'+name+'" is not inside inBody()');
  const h=len/2,mn=c.slice(),mx=c.slice(),ai={x:0,y:1,z:2}[axis];
  for(let i=0;i<3;i++){if(i===ai){mn[i]=c[i]-h;mx[i]=c[i]+h}else{mn[i]=c[i]-r;mx[i]=c[i]+r}}
  const p=Object.assign({id:'p'+(uid++),kind:'cyl',name,group,axis,c,r,len,min:mn,max:mx,mat:'steel',body:curBody},o||{});
  PARTS.push(p);BODY[p.body].parts.push(p);return p;
}

/* ---------- the shop: things the moves must avoid ---------- */
// an assembly table: parts may rest on its top, and nothing may pass through it
function table(min,max,name){const T={min:min.slice(),max:max.slice(),name:name||'Assembly table',kind:'table'};STATIC.push(T);GROUNDS.push(T);TABLES.push(T);return T;}
// a pendant light hanging from the ceiling, its shade bottom at z
function pendant(x,y,z){const r=7*U;const p={x,y,z,min:[x-r,y-r,z],max:[x+r,y+r,z+80*U],name:'Pendant light',kind:'pendant'};STATIC.push(p);PENDANTS.push(p);return p;}
// any other fixed obstacle (a wall, a post, a machine), drawn as a plain dark block
function obstacle(min,max,name){const o={min:min.slice(),max:max.slice(),name:name||'Obstacle',kind:'obstacle'};STATIC.push(o);return o;}

/* ---------- helpers ---------- */
function fmt(v){
  if(UNITS==='mm')return Math.round(v)+' mm';
  const s=v<0?'-':'';v=Math.abs(v);let w=Math.floor(v+1e-9),n=Math.round((v-w)*16);if(n===16){w++;n=0}let d=16;while(n&&n%2===0){n/=2;d/=2}
  const fr={'1/2':'½','1/4':'¼','3/4':'¾','1/8':'⅛','3/8':'⅜','5/8':'⅝','7/8':'⅞'}[n+'/'+d];
  return s+(n?(w?w+(fr?'':'-'):'')+(fr||n+'/'+d):w)+'″';}
function bodyBounds(b){const mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];
  const ps=b.virtual?allParts(b):b.parts;
  ps.forEach(p=>{if(p.decal)return;for(let i=0;i<3;i++){mn[i]=Math.min(mn[i],p.min[i]);mx[i]=Math.max(mx[i],p.max[i]);}});return {min:mn,max:mx};}
function allParts(b){return b.parts.concat(b.children.flatMap(c=>allParts(BODY[c])));}
function sizeText(b){
  if(b.sizeText)return b.sizeText;
  const bb=bodyBounds(b);return [0,1,2].map(i=>bb.max[i]-bb.min[i]).sort((a,c)=>a-c).map(fmt).join(' × ');}

/* ---------- 3×4 affine matrices ---------- */
function mMul(a,b){const r=new Array(12);
  for(let i=0;i<3;i++){for(let j=0;j<3;j++)r[i*4+j]=a[i*4]*b[j]+a[i*4+1]*b[4+j]+a[i*4+2]*b[8+j];
    r[i*4+3]=a[i*4]*b[3]+a[i*4+1]*b[7]+a[i*4+2]*b[11]+a[i*4+3];}return r;}
function mApply(m,p){return [m[0]*p[0]+m[1]*p[1]+m[2]*p[2]+m[3],m[4]*p[0]+m[5]*p[1]+m[6]*p[2]+m[7],m[8]*p[0]+m[9]*p[1]+m[10]*p[2]+m[11]];}
function mRot(axis,deg,pv){const a=deg*Math.PI/180,c=Math.cos(a),s=Math.sin(a);
  const R=axis==='x'?[1,0,0,0, 0,c,-s,0, 0,s,c,0]:axis==='z'?[c,-s,0,0, s,c,0,0, 0,0,1,0]:[c,0,s,0, 0,1,0,0, -s,0,c,0];
  return mMul([1,0,0,pv[0],0,1,0,pv[1],0,0,1,pv[2]],mMul(R,[1,0,0,-pv[0],0,1,0,-pv[1],0,0,1,-pv[2]]));}
// a pose is {off:[dx,dy,dz], rot:deg, axis:'x'|'y'|'z'} relative to the body's finished place; rotation is about the body's pivot
function poseMatrix(b,pose){
  const o=pose.off||[0,0,0], rot=pose.rot||0;
  let m=[1,0,0,o[0],0,1,0,o[1],0,0,1,o[2]];
  if(rot){const pv=b.pivot||centerOf(b);m=mMul(m,mRot(pose.axis||b.axis||'y',rot,pv));}
  return m;
}
function centerOf(b){const bb=bodyBounds(b);return [0,1,2].map(i=>(bb.min[i]+bb.max[i])/2);}

/* ---------- assembly sequence ---------- */
const STEPS=[];
let SI=-1;
// camera preset: look at target from an azimuth (0 = straight in from the front, + = from the right), an elevation and a distance
function orbit(t,az,el,d){const a=az*Math.PI/180,e=el*Math.PI/180;return {target:t,pos:[t[0]+d*Math.sin(a)*Math.cos(e),t[1]-d*Math.cos(a)*Math.cos(e),t[2]+d*Math.sin(e)]};}
// a step: {key, title, text, cam, sheet?, intro?}; moves added after it belong to it
function step(o){if(!o.title||!o.cam)throw new Error('step needs a title and a cam');SI=STEPS.length;o.moves=[];o.idx=SI;STEPS.push(o);return o;}
const DUR=1.3;
// move body id along path (poses, last one is where it ends); o: {delay, dur, remove, seg}
function mv(id,path,o){
  o=o||{};const b=BODY[id];if(!b)throw new Error('mv: no body '+id);if(SI<0)throw new Error('mv before the first step');
  const ev={step:SI,path:path.map(p=>Object.assign({off:[0,0,0],rot:0},p)),delay:o.delay||0,dur:o.dur||DUR,remove:!!o.remove,body:id,seg:o.seg};
  b.events.push(ev);STEPS[SI].moves.push(ev);return ev;
}
const at=(x,y,z)=>({off:[x,y,z]});
const HOME={off:[0,0,0]};
const drop=(h)=>[at(0,0,h),HOME];
const slide=(dx,dy,dz)=>[at(dx,dy,dz||0),HOME];

/* ---------- evaluation: where is every body at (step, time) ---------- */
let LAST=0;
function ease(t){return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;}
function lerp(a,b,t){return a+(b-a)*t;}
function pathPose(ev,u){
  const P=ev.path; if(P.length===1||u<=0)return P[0]; if(u>=1)return P[P.length-1];
  const n=P.length-1, w=ev.seg||new Array(n).fill(1/n);
  let acc=0,i=0;for(;i<n-1;i++){if(u<acc+w[i])break;acc+=w[i];}
  const t=ease(Math.min(1,(u-acc)/w[i])),a=P[i],b=P[i+1];
  return {rot:lerp(a.rot||0,b.rot||0,t),axis:b.axis||a.axis,off:[0,1,2].map(j=>lerp(a.off[j],b.off[j],t))};
}
// state of one body at step s, seconds into the step (Infinity = finished). Step 0 shows the finished piece.
function bodyState(b,s,time){
  if(s===0){s=LAST;time=Infinity;}
  let ev=null,cur=null;
  for(const e of b.events){if(e.step<s)ev=e;else if(e.step===s)cur=e;}
  let pose,op=1,vis=true,moving=false;
  if(cur){
    const u=time===Infinity?1:Math.max(0,Math.min(1,(time-cur.delay)/cur.dur));
    pose=pathPose(cur,u);moving=u<1;
    const first=b.events[0]===cur;
    if(first)op=Math.min(1,u/0.12+(time===Infinity?1:0));
    if(cur.remove){op=u>=1?0:Math.min(op,(1-u)/0.25);if(u>=1)vis=false;}
    if(first&&u<=0&&time!==Infinity)op=0;
  }else if(ev){
    pose=ev.path[ev.path.length-1];if(ev.remove)vis=false;
  }else if(b.events.length){vis=false;pose=HOME;}
  else{pose=HOME;}
  return {vis,op:Math.max(0,Math.min(1,op)),M:poseMatrix(b,pose),moving};
}
function evaluate(s,time){
  const out={};
  const visit=b=>{const c=bodyState(b,s,time);
    if(!b.parent){out[b.id]=c;}
    else{const p=out[b.parent];out[b.id]={vis:p.vis&&c.vis,op:Math.min(p.op,c.op),M:mMul(p.M,c.M),moving:c.moving||p.moving};}
    b.children.forEach(id=>visit(BODY[id]));};
  BODIES.forEach(b=>{if(!b.parent)visit(b);});
  return out;
}

/* ---------- physics checks ---------- */
function partAABB(p,M){
  const mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];
  for(let i=0;i<8;i++){const q=mApply(M,[i&1?p.max[0]:p.min[0],i&2?p.max[1]:p.min[1],i&4?p.max[2]:p.min[2]]);
    for(let j=0;j<3;j++){if(q[j]<mn[j])mn[j]=q[j];if(q[j]>mx[j])mx[j]=q[j];}}
  return {min:mn,max:mx};
}
function overlap(a,b){let d=1e9;for(let i=0;i<3;i++){const o=Math.min(a.max[i],b.max[i])-Math.max(a.min[i],b.min[i]);if(o<=EPS)return 0;d=Math.min(d,o);}return d;}
// face contact: touching on one axis, overlapping with positive area on the other two; below = a rests on b
function touch(a,b){let gapAxis=-1,area=1;
  for(let i=0;i<3;i++){const o=Math.min(a.max[i],b.max[i])-Math.max(a.min[i],b.min[i]);
    if(o>EPS){area*=o;continue;} if(o<-EPS)return null; if(gapAxis>=0)return null; gapAxis=i;}
  if(gapAxis<0)return null;
  const below=gapAxis===2&&Math.abs(a.min[2]-b.max[2])<=EPS;
  const dir=Math.abs(a.max[gapAxis]-b.min[gapAxis])<=EPS?1:-1;
  return {axis:gapAxis,area,below,dir};
}
function boxesAt(st){
  const out={};
  BODIES.forEach(b=>{if(b.virtual)return;const s=st[b.id];if(!s.vis)return;
    out[b.id]=b.parts.filter(p=>!p.decal).map(p=>partAABB(p,s.M));});
  return out;
}
function unionBox(list){const mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];list.forEach(a=>{for(let i=0;i<3;i++){mn[i]=Math.min(mn[i],a.min[i]);mx[i]=Math.max(mx[i],a.max[i]);}});return {min:mn,max:mx};}
const label=id=>{const b=BODY[id];return b.parent?BODY[b.parent].label+' · '+b.label:b.label;};
const FLOOR={min:[-1e7,-1e7,-1],max:[1e7,1e7,0],name:'Floor'};
// everything a body touches at rest at the end of step s: [{other, axis, dir}] (dir +1: the other is on the + side)
function contacts(s,id){
  const st=evaluate(s,Infinity),bx=boxesAt(st),out=[];if(!bx[id])return out;
  Object.keys(bx).forEach(o=>{if(o===id)return;for(const a of bx[id])for(const c of bx[o]){const t=touch(a,c);if(t){out.push({other:o,axis:t.axis,dir:t.dir});return;}}});
  return out;
}

function verify(o){
  o=o||{};const N=o.samples||48, issues=[];let checks=0;
  const grounds=[FLOOR].concat(GROUNDS);
  // parts of one glued sub-assembly that sit still this step are not tested against each other
  const sameGroup=(a,b,s)=>{const A=BODY[a],B=BODY[b];return A.parent&&A.parent===B.parent&&!A.events.some(e=>e.step===s)&&!B.events.some(e=>e.step===s);};
  const leaves=b=>b.virtual?b.children.flatMap(c=>leaves(BODY[c])):[b.id];
  for(let s=1;s<=LAST;s++){
    const S=STEPS[s];
    const movers=new Set();S.moves.forEach(m=>leaves(BODY[m.body]).forEach(id=>movers.add(id)));
    for(let k=0;k<=N;k++){
      const t=S.dur*k/N, st=evaluate(s,t), bx=boxesAt(st), ids=Object.keys(bx);
      const ub={};ids.forEach(id=>ub[id]=unionBox(bx[id]));
      movers.forEach(m=>{
        if(!bx[m])return;
        bx[m].forEach(a=>{checks++;if(a.min[2]<-EPS)issues.push({step:s,t:+t.toFixed(2),kind:'floor',a:label(m)});
          STATIC.forEach(T=>{if(overlap(a,T))issues.push({step:s,t:+t.toFixed(2),kind:'static',a:label(m),b:T.name});});});
        ids.forEach(oid=>{
          if(oid===m||(movers.has(oid)&&oid<m)||sameGroup(m,oid,s))return;
          if(!overlap(ub[m],ub[oid]))return;
          for(const a of bx[m])for(const c of bx[oid]){checks++;const d=overlap(a,c);if(d){issues.push({step:s,t:+t.toFixed(2),kind:'collision',a:label(m),b:label(oid),depth:+d.toFixed(4)});return;}}
        });
      });
    }
    // at rest: every group reaches the floor or a table, every placed body touches something, loose ones sit on something
    const st=evaluate(s,Infinity), bx=boxesAt(st), ids=Object.keys(bx);
    const adj={};ids.forEach(i=>adj[i]=new Set());
    const ub={};ids.forEach(id=>ub[id]=unionBox(bx[id]));
    for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){
      const A=ids[i],B=ids[j];const ua=ub[A],ubb=ub[B];
      let near=true;for(let q=0;q<3;q++)if(ua.min[q]>ubb.max[q]+EPS||ubb.min[q]>ua.max[q]+EPS)near=false;
      if(!near)continue;
      outer:for(const a of bx[A])for(const c of bx[B]){if(touch(a,c)){adj[A].add(B);adj[B].add(A);break outer;}}
    }
    const grounded=new Set();
    ids.forEach(id=>{if(bx[id].some(a=>grounds.some(g=>{const t=touch(a,g);return t&&t.below;})))grounded.add(id);});
    const seen=new Set(grounded),q=[...grounded];while(q.length){const v=q.pop();adj[v].forEach(w=>{if(!seen.has(w)){seen.add(w);q.push(w);}});}
    ids.forEach(id=>{if(!seen.has(id))issues.push({step:s,kind:'floating',a:label(id)});});
    S.moves.forEach(m=>{
      if(m.remove)return;const b=BODY[m.body];
      const list=leaves(b);
      const parts=list.flatMap(c=>bx[c]||[]), others=ids.filter(i=>!list.includes(i)).flatMap(i=>bx[i]).concat(grounds);
      let any=false,sits=false;
      parts.forEach(a=>others.forEach(c=>{const t=touch(a,c);if(t){any=true;if(t.below)sits=true;}}));
      if(!any)issues.push({step:s,kind:'no-contact',a:b.label});
      if((b.loose||b.virtual)&&!sits)issues.push({step:s,kind:'unsupported',a:b.label});
    });
  }
  // finished piece: no two parts share any volume
  const st=evaluate(LAST,Infinity),bx=boxesAt(st),ids=Object.keys(bx);
  for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++)
    for(const a of bx[ids[i]])for(const c of bx[ids[j]]){checks++;const d=overlap(a,c);if(d)issues.push({step:LAST,kind:'final-overlap',a:label(ids[i]),b:label(ids[j]),depth:+d.toFixed(4)});}
  // every part must be placed by some step
  BODIES.forEach(b=>{if(b.virtual||b.temp)return;let x=b,placed=false;while(x){if(x.events.length){placed=true;break;}x=x.parent&&BODY[x.parent];}
    if(!placed)issues.push({step:0,kind:'never-placed',a:label(b.id)});});
  return {ok:issues.length===0,issues,checks,steps:LAST,parts:PARTS.filter(p=>!p.decal).length,bodies:BODIES.filter(b=>!b.virtual).length};
}

/* ---------- finish: totals, default shop, the PLAN object the page reads ---------- */
function finish(f){
  f=f||{};const meta=Object.assign({title:'Build',eyebrow:'Step-by-step build',thing:'piece',about:[],links:[]},f.meta||{});
  if(!STEPS.length||!STEPS[0].intro)throw new Error('the first step must be the overview: step({intro:true, ...})');
  LAST=STEPS.length-1;
  STEPS.forEach(s=>{s.dur=s.moves.length?Math.max(...s.moves.map(m=>m.delay+m.dur)):0;});
  // finished bounds (temporary fixtures excluded)
  const st=evaluate(LAST,Infinity),mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];
  BODIES.forEach(b=>{if(b.virtual||b.temp||!st[b.id].vis)return;b.parts.forEach(p=>{if(p.decal)return;const a=partAABB(p,st[b.id].M);for(let i=0;i<3;i++){mn[i]=Math.min(mn[i],a.min[i]);mx[i]=Math.max(mx[i],a.max[i]);}});});
  const BOUNDS={min:mn,max:mx};
  if(!PENDANTS.length&&meta.pendants!==false){
    // a row of shop lights well above the piece, plus one over each table
    const z=Math.max(92*U,mx[2]+40*U),cy=(mn[1]+mx[1])/2,n=Math.max(1,Math.round((mx[0]-mn[0])/(32*U)));
    for(let i=0;i<n;i++)pendant(mn[0]+(i+0.5)*(mx[0]-mn[0])/n,cy,z);
    TABLES.forEach(T=>pendant((T.min[0]+T.max[0])/2,(T.min[1]+T.max[1])/2,z));
  }
  return {UNITS,U,meta,PARTS,BODY,BODIES,STEPS,LAST,STATIC,TABLES,PENDANTS,BOUNDS,
    evaluate,verify,contacts,fmt,sizeText,bodyBounds,mMul,mApply,poseMatrix,label};
}

return {UNITS,U,EPS,PARTS,BODY,BODIES,STEPS,body,inBody,box,cyl,table,pendant,obstacle,step,mv,at,HOME,drop,slide,orbit,fmt,
  bodyBounds,centerOf,mMul,mApply,poseMatrix,finish};
}

root.Walkthrough={create};
})(typeof window!=='undefined'?window:globalThis);
