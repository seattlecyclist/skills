import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {GTAOPass} from 'three/addons/postprocessing/GTAOPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';

/* Build walkthrough viewer: renders window.PLAN (assets/engine.js + the build file) in a lit shop,
   steps through the assembly, labels new parts, and re-runs the physics check in the viewer's browser.
   Nothing in here is specific to one build: sizes, the room, lights and text all come from PLAN. */
const P=window.PLAN, U=P.U, IN=0.0254/U, $=id=>document.getElementById(id);
const META=P.meta, B=P.BOUNDS;
// the shop is laid out in inches around the finished piece; Bi is the piece's bounds in inches
const Bi={min:B.min.map(v=>v/U),max:B.max.map(v=>v/U)};
const CXi=(Bi.min[0]+Bi.max[0])/2, CYi=(Bi.min[1]+Bi.max[1])/2;
const CX=CXi*U, CY=CYi*U;
const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------------- renderer, camera, controls ---------------- */
const canvas=$('c');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});
const small=Math.min(innerWidth,innerHeight)<700;
renderer.setPixelRatio(Math.min(devicePixelRatio,small?2:1.75));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=0.86;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const MAXANISO=renderer.capabilities.getMaxAnisotropy();

const scene=new THREE.Scene();
scene.background=new THREE.Color('#15110E');
/* ---------------- the room, sized to the piece and the assembly tables (inches) ---------------- */
const TBi=P.TABLES.map(T=>({min:T.min.map(v=>v/U),max:T.max.map(v=>v/U),name:T.name}));
const tMin=k=>Math.min(...TBi.map(T=>T.min[k]),1e9), tMax=k=>Math.max(...TBi.map(T=>T.max[k]),-1e9);
const PZi=Math.max(...P.PENDANTS.map(p=>p.z/U),0);
const ROOM={x0:Math.min(Bi.min[0]-150,tMin(0)-56),x1:Math.max(Bi.max[0]+144,tMax(0)+60),
  y0:Math.min(Bi.min[1]-170,tMin(1)-114),y1:Bi.max[1]+70,h:Math.max(120,PZi+28,Bi.max[2]+40)};
// everything that depends on how big the scene is scales from the 96″ bench the viewer was tuned on
const KS=Math.max(1,Math.hypot(ROOM.x1-ROOM.x0,ROOM.y1-ROOM.y0)/472);
const SS=Math.max(1,Math.max(Bi.max[0]-Bi.min[0],Bi.max[1]-Bi.min[1],Bi.max[2]-Bi.min[2])/96);
scene.fog=new THREE.Fog('#15110E',11*KS,26*KS);
const pmrem=new THREE.PMREMGenerator(renderer);
scene.environment=pmrem.fromScene(new RoomEnvironment(renderer),0.04).texture;

const camera=new THREE.PerspectiveCamera(40,1,0.05,60*KS);
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;controls.dampingFactor=0.08;
controls.maxPolarAngle=Math.PI*0.49;controls.minDistance=0.35;controls.maxDistance=7.5*KS;
controls.rotateSpeed=0.7;controls.zoomSpeed=0.9;

// plan units (x right, y to the back, z up) to world metres, the piece centred on the origin
const W=(x,y,z)=>new THREE.Vector3((x-CX)*IN,z*IN,(CY-y)*IN);
const Wi=(x,y,z)=>W(x*U,y*U,z*U);
const root=new THREE.Group();
root.rotation.x=-Math.PI/2;root.scale.setScalar(IN);root.position.set(-CX*IN,0,CY*IN);
scene.add(root);

/* ---------------- procedural textures ---------------- */
function rng(seed){return function(){seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function canvasTex(w,h,draw,o){
  o=o||{};const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d');draw(g,w,h);
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.anisotropy=MAXANISO;
  if(o.srgb!==false)t.colorSpace=THREE.SRGBColorSpace;return t;
}
function noise(g,w,h,amt,r){const d=g.getImageData(0,0,w,h),a=d.data;for(let i=0;i<a.length;i+=4){const n=(r()-.5)*amt;a[i]+=n;a[i+1]+=n;a[i+2]+=n*.8;}g.putImageData(d,0,0);}
function grain(g,w,h,r,o){
  // long wavy fibres running along u
  for(let i=0;i<o.lines;i++){
    const y0=r()*h,amp=r()*o.wave,f=(0.002+r()*0.006),ph=r()*6.3,a=o.a0+r()*o.a1;
    g.strokeStyle=`rgba(${o.col[0]},${o.col[1]},${o.col[2]},${a})`;g.lineWidth=o.w0+r()*o.w1;g.beginPath();
    for(let x=-8;x<=w+8;x+=12){const y=y0+amp*Math.sin(x*f+ph)+amp*.35*Math.sin(x*f*3.1+ph*2);x<0?g.moveTo(x,y):g.lineTo(x,y);}
    g.stroke();
    if(y0<o.wave*2){g.save();g.translate(0,h);g.stroke();g.restore();}
  }
}
function woodFace(seed,base,light,dark,fibre,o){
  o=o||{};
  return canvasTex(1024,1024,(g,w,h)=>{
    const r=rng(seed);
    g.fillStyle=base;g.fillRect(0,0,w,h);
    // broad rotary-cut figure: soft bands along the grain
    for(let i=0;i<(o.bands||16);i++){const y=r()*h,bh=30+r()*150,col=r()<.5?light:dark,a=.05+r()*.1;
      for(const dy of [-h,0,h]){const gr=g.createLinearGradient(0,y+dy-bh,0,y+dy+bh);gr.addColorStop(0,'rgba(0,0,0,0)');gr.addColorStop(.5,col.replace('A',a));gr.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=gr;g.fillRect(0,y+dy-bh,w,bh*2);}}
    for(let i=0;i<50;i++){const x=r()*w,y=r()*h,rx=60+r()*260,ry=6+r()*30,col=r()<.5?light:dark;g.fillStyle=col.replace('A',.04+r()*.05);
      for(const dx of [-w,0,w])for(const dy of [-h,0,h]){g.beginPath();g.ellipse(x+dx,y+dy,rx,ry,0,0,Math.PI*2);g.fill();}}
    grain(g,w,h,r,{lines:o.lines||1000,wave:o.wave||4,col:fibre,a0:.025,a1:o.fa||.09,w0:.5,w1:1.6});
    if(o.knots)for(let k=0;k<o.knots;k++){const x=r()*w,y=r()*h;for(let i=8;i>0;i--){g.strokeStyle=`rgba(${fibre[0]-30},${fibre[1]-30},${fibre[2]-20},${.08+i*.02})`;g.lineWidth=2;g.beginPath();g.ellipse(x,y,i*4.5,i*2.2,0,0,Math.PI*2);g.stroke();}
      g.fillStyle='rgba(80,45,20,.55)';g.beginPath();g.ellipse(x,y,7,4,0,0,Math.PI*2);g.fill();}
    noise(g,w,h,o.noise||9,r);
  });
}
// ½″ Baltic birch edge: 9 plies, alternating long grain and cross grain, with dark glue lines
function plyEdge(seed){
  return canvasTex(512,144,(g,w,h)=>{
    const r=rng(seed),n=9,ph=h/n;
    for(let k=0;k<n;k++){
      const y=k*ph,cross=k%2===1;
      g.fillStyle=cross?'#D7B987':'#E8D2A8';g.fillRect(0,y,w,ph+1);
      if(cross){for(let i=0;i<900;i++){g.fillStyle=`rgba(120,82,40,${.08+r()*.14})`;g.fillRect(r()*w,y+r()*ph,1+r()*1.5,1+r()*2.5);}}
      else{for(let i=0;i<26;i++){g.strokeStyle=`rgba(140,98,52,${.06+r()*.12})`;g.lineWidth=.6+r();const yy=y+r()*ph;g.beginPath();g.moveTo(0,yy);g.lineTo(w,yy+(r()-.5)*2);g.stroke();}}
      g.fillStyle='rgba(78,52,24,.55)';g.fillRect(0,y,w,1.2);
    }
    noise(g,w,h,10,r);
  });
}
const FACE_TEX=[11,23,37].map(s=>woodFace(s,'#DEC295','rgba(250,232,196,A)','rgba(196,152,96,A)',[150,106,56]));
const EDGE_TEX=plyEdge(5);
const PINE_TEX=woodFace(71,'#DDB57C','rgba(246,214,160,A)','rgba(176,118,56,A)',[150,90,36],{lines:700,wave:9,fa:.16,knots:2,bands:22});
const OAK_TEX=woodFace(91,'#B98D5E','rgba(220,180,130,A)','rgba(120,80,45,A)',[90,56,28],{lines:900,wave:5,fa:.14});
const MAPLE_TEX=woodFace(97,'#D9B98C','rgba(240,214,170,A)','rgba(170,120,70,A)',[130,90,50],{lines:800,wave:3,fa:.08});

const FLOOR_TEX=canvasTex(2048,2048,(g,w,h)=>{
  const r=rng(3),ppi=w/96,rowH=6*ppi;
  for(let row=0;row<16;row++){
    let x=-r()*60*ppi;const y=row*rowH;
    while(x<w){const len=(34+r()*60)*ppi,t=r();
      const c=[118+t*36-r()*14,80+t*22-r()*8,50+t*14-r()*6];
      g.fillStyle=`rgb(${c[0]|0},${c[1]|0},${c[2]|0})`;
      for(const dx of [0,w]){g.fillRect(x-dx,y,len,rowH);}
      g.save();g.beginPath();g.rect(x,y,len,rowH);g.rect(x-w,y,len,rowH);g.clip();
      const rr=rng((row*97+x)|0);
      grain(g,w,h,rr,{lines:28,wave:3,col:[70,40,18],a0:.05,a1:.18,w0:.6,w1:2});
      for(let i=0;i<4;i++){const yy=y+rr()*rowH;const gr=g.createLinearGradient(0,yy-14,0,yy+14);gr.addColorStop(0,'rgba(0,0,0,0)');gr.addColorStop(.5,`rgba(${rr()<.5?'255,220,170':'60,30,10'},.08)`);gr.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=gr;g.fillRect(x,yy-14,len,28);}
      g.restore();
      g.fillStyle='rgba(28,16,8,.85)';g.fillRect(x,y,2.5,rowH);g.fillRect(x-w,y,2.5,rowH);
      x+=len;}
    g.fillStyle='rgba(28,16,8,.9)';g.fillRect(0,y,w,2.5);g.fillStyle='rgba(255,230,190,.08)';g.fillRect(0,y+2.5,w,1.5);
  }
  noise(g,w,h,8,r);
});
const WALL_TEX=canvasTex(1024,1024,(g,w,h)=>{
  const r=rng(8),bh=h/8;
  for(let i=0;i<8;i++){const t=r();g.fillStyle=`rgb(${58+t*6|0},${73+t*6|0},${66+t*5|0})`;g.fillRect(0,i*bh,w,bh);
    for(let k=0;k<60;k++){g.fillStyle=`rgba(${r()<.5?'255,255,255':'0,0,0'},.025)`;g.fillRect(r()*w,i*bh+r()*bh,40+r()*240,1+r()*2);}
    g.fillStyle='rgba(8,12,10,.85)';g.fillRect(0,i*bh+bh-4,w,4);g.fillStyle='rgba(255,255,255,.07)';g.fillRect(0,i*bh,w,2);}
  noise(g,w,h,6,r);
});
const PEG_TEX=canvasTex(512,512,(g,w,h)=>{
  const r=rng(12);g.fillStyle='#8E6B48';g.fillRect(0,0,w,h);noise(g,w,h,14,r);
  for(let x=16;x<w;x+=32)for(let y=16;y<h;y+=32){g.fillStyle='#2B1D12';g.beginPath();g.arc(x,y,4.2,0,7);g.fill();g.fillStyle='rgba(255,230,190,.12)';g.beginPath();g.arc(x+.8,y+1.2,4.2,0,3.2);g.fill();}
});
const SKY_TEX=canvasTex(1024,512,(g,w,h)=>{
  const gr=g.createLinearGradient(0,0,0,h);gr.addColorStop(0,'#7FA9CF');gr.addColorStop(.55,'#E9D3AE');gr.addColorStop(1,'#F6D9A6');g.fillStyle=gr;g.fillRect(0,0,w,h);
  const sg=g.createRadialGradient(w*.7,h*.32,4,w*.7,h*.32,300);sg.addColorStop(0,'rgba(255,248,225,1)');sg.addColorStop(.25,'rgba(255,226,170,.55)');sg.addColorStop(1,'rgba(255,220,160,0)');g.fillStyle=sg;g.fillRect(0,0,w,h);
  const r=rng(4);g.filter='blur(5px)';
  for(let i=0;i<70;i++){const x=r()*w,y=h*.62+r()*h*.18,rad=30+r()*70;g.fillStyle=`rgba(${48+r()*30|0},${72+r()*30|0},${44+r()*20|0},.9)`;g.beginPath();g.arc(x,y,rad,0,7);g.fill();}
  g.fillStyle='#4B5E3A';g.fillRect(0,h*.78,w,h*.22);
  g.filter='blur(14px)';g.fillStyle='rgba(255,236,200,.35)';g.fillRect(0,h*.5,w,h*.12);
},{});
const TRACK_TEX=canvasTex(64,96,(g,w,h)=>{
  g.fillStyle='#3B4046';g.fillRect(0,0,w,h);g.fillStyle='#16191C';g.fillRect(0,h*.32,w,h*.36);
  g.fillStyle='rgba(255,255,255,.18)';g.fillRect(0,h*.3,w,2);g.fillRect(0,h*.68,w,2);g.fillStyle='rgba(255,255,255,.08)';g.fillRect(0,2,w,2);
});
// a stick-on tape for a part from a to b (inches) that reads out from zero in both directions
function tapeTex(a,b,zero){
  const ppi=96,w=Math.min(8192,Math.round((b-a)*ppi)),h=48;
  return canvasTex(w,h,(g)=>{
    g.fillStyle='#E7C230';g.fillRect(0,0,w,h);
    g.fillStyle='#16130F';g.font='600 17px "IBM Plex Mono",monospace';g.textAlign='center';g.textBaseline='top';
    const left=(a+b)/2<zero;for(let s=0;s<=Math.ceil(Math.max(Math.abs(a-zero),Math.abs(b-zero)))*16;s++){const rd=s/16,x=left?zero-rd:zero+rd,px=(x-a)*w/(b-a);if(px<-2||px>w+2)continue;
      const L=s%16===0?.62:s%8===0?.46:s%4===0?.34:s%2===0?.24:.15;
      g.fillRect(px-0.8,h-h*L,1.6,h*L);
      if(s%16===0&&rd>0){g.fillStyle=rd%12===0?'#B5261B':'#16130F';g.fillText(String(rd),px+(left?-11:11),3);g.fillStyle='#16130F';}}
  });
}

/* ---------------- materials ---------------- */
const std=(o)=>new THREE.MeshStandardMaterial(Object.assign({envMapIntensity:.45},o));
const M={
  face:FACE_TEX.map(t=>std({map:t,roughness:.6})),
  edge:std({map:EDGE_TEX,roughness:.72}),
  pine:std({map:PINE_TEX,roughness:.66}),
  track:std({color:'#3A3F45',metalness:.7,roughness:.38}),
  trackTop:std({map:TRACK_TEX,metalness:.65,roughness:.4}),
  tape:std({color:'#E7C230',roughness:.5}),
  stops:std({color:'#B8352B',metalness:.25,roughness:.42}),
  slide:std({color:'#B9BDC2',metalness:.9,roughness:.32}),
  steel:std({color:'#3B3F44',metalness:.6,roughness:.45}),
  rubber:std({color:'#1E1F21',roughness:.85}),
  zinc:std({color:'#B9BDC2',metalness:.9,roughness:.32}),
  brass:std({color:'#B48A3C',metalness:.8,roughness:.35}),
  black:std({color:'#1E2124',roughness:.5}),
  alu:std({color:'#B9BFC5',metalness:.85,roughness:.32}),
  blade:std({color:'#D7DADD',metalness:1,roughness:.22}),
  pull:std({color:'#3D2C1B',roughness:.9}),
  invisible:new THREE.MeshBasicMaterial({visible:false})
};
const WALNUT_TEX=woodFace(83,'#6B4A33','rgba(150,110,80,A)','rgba(60,38,24,A)',[50,30,18],{lines:900,wave:5,fa:.16});
const CHERRY_TEX=woodFace(87,'#B5714A','rgba(220,150,110,A)','rgba(130,70,40,A)',[110,55,30],{lines:900,wave:4,fa:.12});
const MDF_TEX=canvasTex(256,256,(g,w,h)=>{const r=rng(17);g.fillStyle='#A88462';g.fillRect(0,0,w,h);noise(g,w,h,18,r);});
const WOOD={pine:PINE_TEX,oak:OAK_TEX,maple:MAPLE_TEX,walnut:WALNUT_TEX,cherry:CHERRY_TEX,mdf:MDF_TEX};
const woodMats={},paintMats={},tapeMats={};
function woodMat(name,color){const k=name+(color||'');return woodMats[k]||(woodMats[k]=std({map:WOOD[name],color:color||'#ffffff',roughness:name==='mdf'?.85:.62}));}
// metals and plastics by name, or any colour as a painted finish
function hardMat(p){
  if(p.color&&(!p.mat||p.mat==='paint'||!M[p.mat])){const k=p.color+(p.metal?'m':'');return paintMats[k]||(paintMats[k]=std({color:p.color,roughness:p.metal?.35:.5,metalness:p.metal?.8:0}));}
  return M[p.mat]||M.steel;
}

/* ---------------- box geometry with real-size UVs ---------------- */
// faces in order +x,-x,+y,-y,+z,-z (plan axes); each face is its own material group
function boxGeo(mn,mx,uvFn){
  const pos=[],nor=[],uv=[],idx=[];let vi=0;const geo=new THREE.BufferGeometry();
  for(let fi=0;fi<6;fi++){
    const n=fi>>1,s=fi%2?-1:1,a=(n+1)%3,b=(n+2)%3;
    const vs=[[0,0],[1,0],[1,1],[0,1]].map(([i,j])=>{const v=[0,0,0];v[n]=s>0?mx[n]:mn[n];v[a]=i?mx[a]:mn[a];v[b]=j?mx[b]:mn[b];return v;});
    vs.forEach(v=>{pos.push(v[0],v[1],v[2]);const nn=[0,0,0];nn[n]=s;nor.push(...nn);const t=uvFn(n,v);uv.push(t[0],t[1]);});
    (s>0?[0,1,2,0,2,3]:[0,2,1,0,3,2]).forEach(o=>idx.push(vi+o));
    geo.addGroup(fi*6,6,fi);vi+=4;
  }
  geo.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  geo.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));
  geo.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
  geo.setIndex(idx);return geo;
}
const sizes=(mn,mx)=>[0,1,2].map(i=>mx[i]-mn[i]);
const LAYER=0.5*U;   // sheet-goods ply stripes repeat every ½″ of thickness
let uvSeed=rng(99);
// Baltic birch: face grain along the longest side, ply stripes across the thickness on every edge
function birch(p){
  const s=sizes(p.min,p.max);let t=0;for(let i=1;i<3;i++)if(s[i]<s[t]-1e-9)t=i;
  const base=p.plyBase!==undefined?p.plyBase:p.min[t];
  const o=[0,1,2].filter(i=>i!==t),lg=s[o[0]]>=s[o[1]]?o[0]:o[1],sh=lg===o[0]?o[1]:o[0];
  const ou=uvSeed()*10,ov=uvSeed()*10;
  const geo=boxGeo(p.min,p.max,(n,v)=>n===t?[v[lg]/(24*U)+ou,v[sh]/(24*U)+ov]:[v[n===lg?sh:lg]/(12*U)+ou,(v[t]-base)/LAYER]);
  const fm=M.face[Math.floor(uvSeed()*3)];
  return {geo,mats:[0,1,2,3,4,5].map(fi=>(fi>>1)===t?fm:M.edge)};
}
function solidWood(mn,mx,mat,tile){
  tile=tile||24*U;const s=sizes(mn,mx);const lg=s.indexOf(Math.max(...s));const ou=uvSeed()*10,ov=uvSeed()*10;
  return boxGeo(mn,mx,(n,v)=>{const o=[0,1,2].filter(i=>i!==n);const u=o.includes(lg)?lg:o[0],w=o.find(i=>i!==u);return [v[u]/tile+ou,v[w]/tile+ov];});
}

/* ---------------- the piece: one THREE.Group per rigid body ---------------- */
const VIS={};      // body id -> {group, mats:Set, meshes:[]}
const pickables=[];
function partMesh(p){
  let geo,mats;
  if(p.kind==='cyl'){
    geo=new THREE.CylinderGeometry(p.r,p.r,p.len,p.r>3*U?64:28);
    if(p.axis==='x')geo.rotateZ(Math.PI/2);else if(p.axis==='z')geo.rotateX(Math.PI/2);
    geo.translate(p.c[0],p.c[1],p.c[2]);
    mats=WOOD[p.mat]?woodMat(p.mat,p.color):hardMat(p);
  }
  else if(p.mat==='ply'||p.mat==='bb'){({geo,mats}=birch(p));if(p.color){const t=std({color:p.color,roughness:.55});mats=mats.map(()=>t);}}
  else if(WOOD[p.mat]){geo=solidWood(p.min,p.max);mats=woodMat(p.mat,p.color);}
  else if(p.decal){geo=solidWood(p.min,p.max);mats=p.color?hardMat(p):M.pull;}
  else if(p.profile==='ttrack'){const ax=sizes(p.min,p.max)[0]>=sizes(p.min,p.max)[1]?0:1;geo=boxGeo(p.min,p.max,(n,v)=>ax===0?[v[0]/(2*U),(v[1]-p.min[1])/(p.max[1]-p.min[1])]:[v[1]/(2*U),(v[0]-p.min[0])/(p.max[0]-p.min[0])]);mats=[M.track,M.track,M.track,M.track,M.trackTop,M.track];}
  else if(p.tape){
    const k=p.min[0]+'|'+p.max[0]+'|'+p.tape.zero;
    tapeMats[k]=tapeMats[k]||std({map:tapeTex(p.min[0]/U,p.max[0]/U,p.tape.zero/U),roughness:.5});
    geo=boxGeo(p.min,p.max,(n,v)=>[(v[0]-p.min[0])/(p.max[0]-p.min[0]),(v[1]-p.min[1])/(p.max[1]-p.min[1])]);mats=[M.tape,M.tape,M.tape,M.tape,tapeMats[k],M.tape];}
  else{
    const s=sizes(p.min,p.max),r=Math.min(0.3*U,Math.min(...s)*0.3);
    geo=new RoundedBoxGeometry(s[0],s[1],s[2],2,r);geo.translate((p.min[0]+p.max[0])/2,(p.min[1]+p.max[1])/2,(p.min[2]+p.max[2])/2);
    mats=hardMat(p);
  }
  return new THREE.Mesh(geo,mats);
}
P.BODIES.forEach(b=>{
  if(b.virtual)return;
  const g=new THREE.Group();g.matrixAutoUpdate=false;root.add(g);
  const v={group:g,meshes:[],mats:new Map(),body:b};VIS[b.id]=v;
  const clone=m=>{if(!v.mats.has(m)){const c=m.clone();c.userData.base=m;v.mats.set(m,c);}return v.mats.get(m);};
  b.parts.forEach(p=>{
    const mesh=partMesh(p);
    mesh.material=Array.isArray(mesh.material)?mesh.material.map(clone):clone(mesh.material);
    mesh.castShadow=!p.decal;mesh.receiveShadow=true;mesh.userData={part:p,body:b};
    g.add(mesh);v.meshes.push(mesh);pickables.push(mesh);
  });
});
const m4=new THREE.Matrix4();
function applyState(st,hiStep,hiT){
  for(const id in VIS){
    const v=VIS[id],s=st[id];
    const show=s.vis&&s.op>0.002;v.group.visible=show;if(!show)continue;
    const m=s.M;m4.set(m[0],m[1],m[2],m[3],m[4],m[5],m[6],m[7],m[8],m[9],m[10],m[11],0,0,0,1);
    v.group.matrix.copy(m4);v.group.matrixWorldNeedsUpdate=true;
    const op=s.op,tr=op<0.999;
    const glow=hiStep!==null?highlight(v.body,hiStep,hiT):0;
    v.mats.forEach(mat=>{
      if(mat.transparent!==tr){mat.transparent=tr;mat.needsUpdate=true;}
      mat.opacity=op;mat.depthWrite=op>0.5;
      mat.emissive.setRGB(0.55*glow,0.33*glow,0.08*glow);
    });
  }
}
// new parts glow amber while they move in and for a moment after they land
function highlight(b,s,t){
  const ev=b.events.find(e=>e.step===s)||(b.parent&&P.BODY[b.parent].events.find(e=>e.step===s));
  if(!ev||ev.remove)return 0;
  const end=ev.delay+ev.dur;
  if(t<ev.delay)return 0;if(t<end)return 0.55;return Math.max(0,0.55*(1-(t-end)/1.4));
}

/* ---------------- the shop ---------------- */
// laid out in inches whatever the plan's units; the shop group scales inches to plan units
const shop=new THREE.Group();shop.scale.setScalar(U);root.add(shop);
let target=shop;
function add(geo,mats,o){o=o||{};const m=new THREE.Mesh(geo,mats);m.castShadow=o.cast!==false;m.receiveShadow=true;(o.parent||target).add(m);return m;}
// shop dressing is drawn for the reference room R0 and moved with whichever wall or corner it belongs to
const R0={x0:-150,x1:240,y0:-170,y1:96};
function inGroup(dx,dy,fn){const g=new THREE.Group();g.position.set(dx,dy,0);shop.add(g);const prev=target;target=g;fn();target=prev;}
function wood(mn,mx,mat,o){return add(solidWood(mn,mx,mat,o&&o.tile),mat,o);}
function rbox(mn,mx,mat,r,o){const s=sizes(mn,mx);const g=new RoundedBoxGeometry(s[0],s[1],s[2],2,Math.min(r,Math.min(...s)/2.01));g.translate((mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2);return add(g,mat,o);}
function cylZ(x,y,z0,z1,r,mat,o){const g=new THREE.CylinderGeometry(o&&o.r2!==undefined?o.r2:r,r,z1-z0,o&&o.seg||24,1,o&&o.open);g.rotateX(Math.PI/2);g.translate(x,y,(z0+z1)/2);return add(g,mat,o);}
function cylAxis(c,axis,r,len,mat,o){const g=new THREE.CylinderGeometry(r,r,len,o&&o.seg||20);if(axis==='x')g.rotateZ(Math.PI/2);if(axis==='z')g.rotateX(Math.PI/2);g.translate(...c);return add(g,mat,o);}

// floor
{const g=new THREE.PlaneGeometry(ROOM.x1-ROOM.x0,ROOM.y1-ROOM.y0);g.translate((ROOM.x0+ROOM.x1)/2,(ROOM.y0+ROOM.y1)/2,0);
  const uv=g.attributes.uv;for(let i=0;i<uv.count;i++)uv.setXY(i,uv.getX(i)*(ROOM.x1-ROOM.x0)/96,uv.getY(i)*(ROOM.y1-ROOM.y0)/96);
  add(g,std({map:FLOOR_TEX,roughness:.5,envMapIntensity:.35}),{cast:false});}
// walls: only the inside faces render, so the camera can look in from outside the room
const wallMat=std({map:WALL_TEX,roughness:.85,envMapIntensity:.2});
function wall(mn,mx,inner,reveal){
  const g=boxGeo(mn,mx,(n,v)=>{const o=[0,1,2].filter(i=>i!==n);const u=o[0]===2?o[1]:o[0];return [v[u]/48,v[2]/48];});
  const mats=[0,1,2,3,4,5].map(fi=>fi===inner||(reveal&&reveal.includes(fi))?wallMat:M.invisible);
  return add(g,mats);
}
const WIN={x0:CXi-44,x1:CXi+44,z0:46,z1:104};
wall([ROOM.x0,ROOM.y1,0],[WIN.x0,ROOM.y1+4,ROOM.h],3,[0]);
wall([WIN.x1,ROOM.y1,0],[ROOM.x1,ROOM.y1+4,ROOM.h],3,[1]);
wall([WIN.x0,ROOM.y1,0],[WIN.x1,ROOM.y1+4,WIN.z0],3,[4]);
wall([WIN.x0,ROOM.y1,WIN.z1],[WIN.x1,ROOM.y1+4,ROOM.h],3,[5]);
wall([ROOM.x0-4,ROOM.y0,0],[ROOM.x0,ROOM.y1,ROOM.h],0);
wall([ROOM.x1,ROOM.y0,0],[ROOM.x1+4,ROOM.y1,ROOM.h],1);
// baseboards
const trimMat=std({color:'#2A3330',roughness:.6});
wood([ROOM.x0,ROOM.y1-0.75,0],[ROOM.x1,ROOM.y1,5],trimMat);
wood([ROOM.x0,ROOM.y0,0],[ROOM.x0+0.75,ROOM.y1,5],trimMat);
wood([ROOM.x1-0.75,ROOM.y0,0],[ROOM.x1,ROOM.y1,5],trimMat);
// steel window, glass, sill, and the garden beyond
const black=std({color:'#1B1D1F',metalness:.55,roughness:.45});
inGroup(CXi-48,ROOM.y1-R0.y1,()=>{const ROOM=R0,WIN={x0:4,x1:92,z0:46,z1:104};
[4,26,48,70,92].forEach(x=>rbox([x-0.9,ROOM.y1+0.5,WIN.z0],[x+0.9,ROOM.y1+2.5,WIN.z1],black,.15));
[WIN.z0,75,WIN.z1].forEach(z=>rbox([WIN.x0,ROOM.y1+0.5,z-0.9],[WIN.x1,ROOM.y1+2.5,z+0.9],black,.15));
{const g=new THREE.PlaneGeometry(WIN.x1-WIN.x0,WIN.z1-WIN.z0);g.rotateX(Math.PI/2);g.translate((WIN.x0+WIN.x1)/2,ROOM.y1+1.6,(WIN.z0+WIN.z1)/2);
  add(g,new THREE.MeshPhysicalMaterial({color:'#dfeaf0',transparent:true,opacity:.08,roughness:.04,metalness:0,envMapIntensity:1}),{cast:false});}
wood([WIN.x0-3,ROOM.y1-5,WIN.z0-1.5],[WIN.x1+3,ROOM.y1,WIN.z0],std({map:OAK_TEX,roughness:.5}));
{const g=new THREE.PlaneGeometry(520,300);g.rotateX(Math.PI/2);g.translate(60,ROOM.y1+120,80);
  const m=new THREE.MeshBasicMaterial({map:SKY_TEX,fog:false});const s=add(g,m,{cast:false});s.receiveShadow=false;}
// plant on the sill
{const pot=std({color:'#B4643E',roughness:.8});cylZ(80,ROOM.y1-2.5,WIN.z0,WIN.z0+5,2.4,pot,{r2:2.9});
  const leaf=std({color:'#3F6B35',roughness:.6});const r=rng(6);
  for(let i=0;i<9;i++){const g=new THREE.SphereGeometry(1,12,8);g.scale(1.1,0.45,2.6);g.rotateX(-0.6+r()*.4);g.rotateZ(r()*6.3);g.translate(80+(r()-.5)*4,ROOM.y1-2.5+(r()-.5)*3,WIN.z0+7+r()*4);add(g,leaf);}}
});

// assembly tables (sub-assemblies are laid up on them)
TBi.forEach(T=>{const top=std({map:OAK_TEX,color:'#8E6A4C',roughness:.5}),leg=std({map:OAK_TEX,roughness:.6});
  wood([T.min[0],T.min[1],T.max[2]-1.5],[T.max[0],T.max[1],T.max[2]],top);
  [[T.min[0]+2,T.min[1]+2],[T.max[0]-5,T.min[1]+2],[T.min[0]+2,T.max[1]-5],[T.max[0]-5,T.max[1]-5]].forEach(([x,y])=>wood([x,y,0],[x+3,y+3,T.max[2]-1.5],leg));
  wood([T.min[0]+2,T.min[1]+2.5,24],[T.max[0]-2,T.min[1]+4.5,28.5],leg);wood([T.min[0]+2,T.max[1]-4.5,24],[T.max[0]-2,T.max[1]-2.5,28.5],leg);
  wood([T.min[0]+3,T.min[1]+3,8],[T.max[0]-3,T.max[1]-3,8.75],top);
  // a few offcuts and a glue bottle on the shelf
  const r=rng(31);for(let i=0;i<4;i++){const x=T.min[0]+6+r()*20,y=T.min[1]+6+i*6;wood([x,y,8.75],[x+10+r()*12,y+3+r()*2,9.25],M.face[i%3]);}
  cylZ(T.max[0]-10,T.min[1]+12,8.75,15,1.4,std({color:'#E8E2D2',roughness:.5}));cylZ(T.max[0]-10,T.min[1]+12,15,16.5,0.6,std({color:'#C9472E',roughness:.5}));});
// other fixed obstacles from the plan
P.STATIC.filter(o=>o.kind==='obstacle').forEach(o=>rbox(o.min.map(v=>v/U),o.max.map(v=>v/U),std({color:'#3A3F44',roughness:.6}),.3));

// traditional workbench, pegboard and shelf on the left wall
inGroup(ROOM.x0-R0.x0,ROOM.y0-R0.y0,()=>{const ROOM=R0;const top=std({map:MAPLE_TEX,roughness:.5}),leg=std({map:OAK_TEX,roughness:.6}),x0=ROOM.x0+1,y0=-136,y1=-36;
  wood([x0,y0,31],[x0+24,y1,35],top,{tile:30});
  [[x0+2,y0+4],[x0+17,y0+4],[x0+2,y1-8],[x0+17,y1-8]].forEach(([x,y])=>wood([x,y,0],[x+4,y+4,31],leg));
  wood([x0+2,y0+5,6],[x0+21,y0+7,10],leg);wood([x0+2,y1-7,6],[x0+21,y1-5,10],leg);wood([x0+4,y0+8,6],[x0+19,y1-8,7],leg);
  wood([x0+24,y0+2,8],[x0+26.5,y0+12,35],top);cylAxis([x0+27.5,y0+7,26],'x',0.6,8,M.steel);
  // hand plane, mallet and square on the bench
  rbox([x0+10,-80,35],[x0+12.4,-70,36.6],M.steel,.3);cylAxis([x0+11.2,-76,38],'y',0.5,3,std({color:'#7A3F1D',roughness:.5}));
  rbox([x0+10.6,-73,36.6],[x0+11.8,-71.5,38.6],std({color:'#7A3F1D',roughness:.5}),.3);
  cylAxis([x0+15,-58,36.2],'y',0.55,11,leg);rbox([x0+12.5,-63.5,35],[x0+17.5,-60.5,37.6],std({map:MAPLE_TEX,roughness:.5}),.4);
  const peg=std({map:PEG_TEX,roughness:.8});
  const pg=boxGeo([ROOM.x0,-136,42],[ROOM.x0+0.4,-36,90],(n,v)=>[v[1]/16,v[2]/16]);add(pg,[peg,peg,peg,peg,peg,peg]);
  // chisels
  const handle=std({color:'#8A4B22',roughness:.45});
  [0,1,2,3,4].forEach(i=>{const y=-128+i*2.6;cylZ(ROOM.x0+1.4,y,70,75,0.42,handle);rbox([ROOM.x0+1.2,y-0.3+i*0.02,62],[ROOM.x0+1.6,y+0.3-i*0.02,70],M.blade,.05);});
  // backsaw
  rbox([ROOM.x0+1,-112,58],[ROOM.x0+1.1,-98,63],M.blade,.02);rbox([ROOM.x0+0.8,-98.5,57],[ROOM.x0+1.6,-94,64.5],handle,.4);rbox([ROOM.x0+0.9,-112,62.6],[ROOM.x0+1.3,-98,63.2],std({color:'#B48A3C',metalness:.8,roughness:.35}),.05);
  // squares and a hammer
  rbox([ROOM.x0+0.8,-88,72],[ROOM.x0+1.4,-87,84],M.alu,.05);rbox([ROOM.x0+0.8,-88,83],[ROOM.x0+1.4,-80,84],M.alu,.05);
  rbox([ROOM.x0+0.8,-74,58],[ROOM.x0+1.6,-73,72],handle,.3);rbox([ROOM.x0+0.6,-75.5,71],[ROOM.x0+1.8,-71.5,73],M.steel,.3);
  // marking gauge and pencils
  rbox([ROOM.x0+0.8,-62,64],[ROOM.x0+1.4,-61.2,74],handle,.2);rbox([ROOM.x0+0.6,-63.6,69],[ROOM.x0+2.2,-59.6,71.2],handle,.3);
  // shelf with jars
  wood([ROOM.x0,-136,93],[ROOM.x0+9,-36,94],std({map:OAK_TEX,roughness:.55}));
  const glass=new THREE.MeshPhysicalMaterial({color:'#e8efe9',transparent:true,opacity:.35,roughness:.08,envMapIntensity:1});
  const lid=std({color:'#C1912F',metalness:.8,roughness:.35});
  for(let i=0;i<7;i++){const y=-128+i*6.2,hh=4.5+(i%3)*1.5;cylZ(ROOM.x0+4.5,y,94,94+hh,2,glass,{cast:false});cylZ(ROOM.x0+4.5,y,94+hh,94+hh+0.6,2.05,lid);
    cylZ(ROOM.x0+4.5,y,94.05,94+hh*0.6,1.75,std({color:['#7A5332','#9A9C9E','#C8A46A'][i%3],roughness:.8}),{cast:false});}
  // stool
  const st=std({map:OAK_TEX,roughness:.55});cylZ(-104,-92,24,25.6,7,st,{seg:40});
  [[0,1],[2.1,1],[4.2,1]].forEach(([a])=>{const g=new THREE.CylinderGeometry(0.65,0.8,25,12);g.rotateX(Math.PI/2);g.rotateY(0.12);g.rotateZ(a);g.translate(-104+Math.cos(a)*4.6,-92+Math.sin(a)*4.6,12);add(g,st);});
});

// right wall: Baltic birch sheets leaning against it and a rack of hardwood boards
inGroup(ROOM.x1-R0.x1,ROOM.y0-R0.y0,()=>{const ROOM=R0;
{const sheetsG=new THREE.Group();target.add(sheetsG);
  for(let i=0;i<5;i++){const g=new THREE.Group();sheetsG.add(g);
    const t=i===4?0.75:0.5,y0=-58+i*0.2,p={min:[0,y0,0],max:[t,y0+60,60]};
    const {geo,mats}=birch(p);const m=add(geo,mats,{parent:g});
    g.position.set(ROOM.x1-4.6-i*0.62,0,0);g.rotation.y=-0.075;}
  const arm=std({color:'#24282C',metalness:.6,roughness:.5});
  const boards=[['#6B4A33',[1,1.0]],['#A0603E',[1,1.0]],['#C59A63',[1,1.0]],['#6B4A33',[1,1]],['#B98D5E',[1,1]]];
  [60,74,88].forEach((z,k)=>{
    [-140,-104,-68].forEach(y=>rbox([ROOM.x1-16,y,z-2],[ROOM.x1,y+1.5,z],arm,.2));
    for(let i=0;i<3;i++){const c=boards[(k*2+i)%boards.length][0],w=5+((i*7+k*3)%4);
      wood([ROOM.x1-15+i*(w+0.4),-146,z],[ROOM.x1-15+i*(w+0.4)+w,-60,z+1+(i%2)*0.75],std({map:OAK_TEX,color:c,roughness:.6}),{tile:40});}});
}
});
// clamp rack and a pinned drawing on the back wall, right of the window
inGroup(ROOM.x1-R0.x1,ROOM.y1-R0.y1,()=>{const ROOM=R0;
{const rail=std({color:'#24282C',metalness:.6,roughness:.5});
  wood([148,ROOM.y1-3,72],[232,ROOM.y1,75],std({map:OAK_TEX,roughness:.55}));
  for(let i=0;i<9;i++){const x=152+i*8.8,bar=34+(i%3)*8;
    rbox([x,ROOM.y1-5,74-bar+3],[x+0.6,ROOM.y1-3.4,76],M.slide,.05);
    rbox([x-1.2,ROOM.y1-6.5,72],[x+1.8,ROOM.y1-1.8,78],std({color:i%2?'#C33B2C':'#1E2124',roughness:.45}),.4);
    rbox([x-1.2,ROOM.y1-6.5,74-bar+1],[x+1.8,ROOM.y1-1.8,74-bar+7],std({color:'#1E2124',roughness:.45}),.4);}
  const sheet=canvasTex(768,544,(g,w,h)=>{
    g.fillStyle='#F2EFE6';g.fillRect(0,0,w,h);g.strokeStyle='#1B2630';g.lineWidth=3;g.strokeRect(14,14,w-28,h-28);
    g.fillStyle='#1B2630';g.font='700 34px "Barlow Condensed",sans-serif';g.fillText(META.title.toUpperCase().slice(0,40),34,62);
    g.font='500 20px "IBM Plex Mono",monospace';g.fillText('FRONT ELEVATION'+(META.rev?'  ·  REV '+META.rev:''),34,92);
    // a front elevation of the finished piece: every part's outline, seen from the front
    const ox=60,oy=130,bw=w-120,bh=h-210,sx=Bi.max[0]-Bi.min[0],sz=Bi.max[2]-Bi.min[2],k=Math.min(bw/sx,bh/sz);
    const fst=P.evaluate(P.LAST,Infinity);g.strokeStyle='#2D5B98';g.lineWidth=1.2;
    P.BODIES.forEach(b=>{if(b.virtual||b.temp||!fst[b.id].vis)return;b.parts.forEach(pt=>{if(pt.decal)return;
      const a=P.mApply(fst[b.id].M,pt.min),c=P.mApply(fst[b.id].M,pt.max);
      const x0=Math.min(a[0],c[0])/U-Bi.min[0],x1=Math.max(a[0],c[0])/U-Bi.min[0],z0=Math.min(a[2],c[2])/U-Bi.min[2],z1=Math.max(a[2],c[2])/U-Bi.min[2];
      g.strokeRect(ox+x0*k,oy+bh-z1*k,(x1-x0)*k,(z1-z0)*k);});});
    g.fillStyle='#2D5B98';g.font='18px "IBM Plex Mono",monospace';g.textAlign='center';
    g.fillText(P.fmt(sx*U)+' OVERALL',ox+sx*k/2,oy+bh+34);
  });
  const sg=new THREE.PlaneGeometry(30,21.25);sg.rotateX(Math.PI/2);sg.rotateZ(Math.PI);sg.translate(116,ROOM.y1-0.3,70);
  add(sg,std({map:sheet,roughness:.9,envMapIntensity:.15}),{cast:false});
  cylAxis([116,ROOM.y1-0.6,80.2],'y',0.45,0.6,std({color:'#C33B2C',roughness:.4}));}

});
// cabinet table saw, front right
inGroup(ROOM.x1-R0.x1,ROOM.y0-R0.y0,()=>{
{const cx=176,cy=-84,dark=std({color:'#2C3135',roughness:.55,metalness:.2}),iron=std({color:'#9EA4AA',metalness:.85,roughness:.38});
  rbox([cx-10.5,cy-10.5,4],[cx+10.5,cy+10.5,34],dark,.5);rbox([cx-12,cy-12,0],[cx+12,cy+12,4],std({color:'#1C1F22',roughness:.6}),.3);
  rbox([cx-20,cy-14,34],[cx+20,cy+13.5,35.5],iron,.15);
  rbox([cx+20,cy-14,34.2],[cx+40,cy+13.5,35.5],std({color:'#303539',roughness:.5}),.15);
  rbox([cx-22,cy-16.5,32.5],[cx+42,cy-14,34.5],M.steel,.3);
  rbox([cx+12,cy-16,35.5],[cx+15,cy+13.5,38.5],std({color:'#1E2124',roughness:.45}),.4);
  const bl=new THREE.CylinderGeometry(5,5,0.12,64);bl.rotateZ(Math.PI/2);bl.translate(cx-2,cy-1,32.4);add(bl,M.blade);
  rbox([cx-2.6,cy-1.5,35.4],[cx-1.4,cy+6,37.6],std({color:'#C33B2C',roughness:.45}),.3);
  cylAxis([cx-2,cy-11,26],'y',3,1.2,M.blade);}
// dust extractor beside it
{const x=140,y=-112,body=std({color:'#3E4247',roughness:.5}),lid=std({color:'#6FA33D',roughness:.5});
  rbox([x-8,y-12,1.5],[x+8,y+12,17],body,1.2);rbox([x-8.2,y-12.2,17],[x+8.2,y+12.2,21],lid,1);
  [[-6,-9],[6,-9],[-6,9],[6,9]].forEach(([a,b])=>cylAxis([x+a,y+b,1.5],'x',1.5,1.2,M.rubber));
  const tor=new THREE.TorusGeometry(5,1.1,12,40);tor.rotateY(Math.PI/2);tor.translate(x,y+4,27);add(tor,std({color:'#1F2225',roughness:.7}));}
});

// pendant lights
const bulbMat=new THREE.MeshStandardMaterial({color:'#fff2d6',emissive:'#ffcf8a',emissiveIntensity:6});
const shadeMat=std({color:'#1E2A26',metalness:.4,roughness:.45,side:THREE.DoubleSide});
P.PENDANTS.forEach(q=>{const p={x:q.x/U,y:q.y/U,z:q.z/U};
  cylZ(p.x,p.y,p.z+6,ROOM.h,0.15,std({color:'#111'}),{cast:false});
  const g=new THREE.CylinderGeometry(1.4,7,7,40,1,true);g.rotateX(Math.PI/2);g.translate(p.x,p.y,p.z+3.5);add(g,shadeMat,{cast:false});
  const b=new THREE.SphereGeometry(1.7,20,14);b.translate(p.x,p.y,p.z+2.4);add(b,bulbMat,{cast:false});
  const L=new THREE.PointLight('#ffc98a',(small?5:6)*Math.min(4,1+(p.z-92)/60),0,2);L.position.copy(Wi(p.x,p.y,p.z+1));scene.add(L);
});

/* ---------------- light ---------------- */
scene.add(new THREE.HemisphereLight('#ffe8c8','#4a3424',0.3));
const sun=new THREE.DirectionalLight('#ffd3a0',3.0);
sun.position.copy(Wi(CXi+122*SS,CYi+417*SS,330*SS));sun.target.position.copy(Wi(CXi-8*SS,CYi-13,0));scene.add(sun,sun.target);
sun.castShadow=true;sun.shadow.mapSize.set(small?2048:4096,small?2048:4096);
Object.assign(sun.shadow.camera,{left:-7*KS,right:7*KS,top:7*KS,bottom:-7*KS,near:1,far:30*KS});
sun.shadow.bias=-0.0003;sun.shadow.normalBias=0.02;sun.shadow.radius=3;
const key=new THREE.SpotLight('#fff0dc',small?70:80,0,0.62,0.9,2);
key.position.copy(Wi(CXi-108*SS,CYi-183*SS,190*SS));key.target.position.copy(Wi(CXi-8*SS,CYi-3,18*SS));scene.add(key,key.target);
key.castShadow=true;key.shadow.mapSize.set(2048,2048);key.shadow.bias=-0.0002;key.shadow.normalBias=0.02;key.shadow.radius=4;key.shadow.camera.near=1;key.shadow.camera.far=16*KS;

/* ---------------- post-processing ---------------- */
let composer=null,gtao=null;
function setupComposer(){
  if(small)return;
  try{
    composer=new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene,camera));
    gtao=new GTAOPass(scene,camera,innerWidth,innerHeight);
    gtao.output=GTAOPass.OUTPUT.Default;
    gtao.blendIntensity=0.85;
    gtao.updateGtaoMaterial({radius:0.22,distanceExponent:1.4,thickness:1,scale:1,samples:16});
    gtao.updatePdMaterial({lumaPhi:10,depthPhi:2,normalPhi:3,radius:6,rings:2,samples:16});
    composer.addPass(gtao);composer.addPass(new OutputPass());
  }catch(e){composer=null;}
}
setupComposer();

/* ---------------- sizing and camera framing ---------------- */
let viewOffsetY=0;
function resize(){
  const w=innerWidth,h=innerHeight;renderer.setSize(w,h,false);
  camera.aspect=w/h;camera.fov=w/h<0.8?58:w/h<1.2?48:40;
  // keep the subject centred in the part of the screen the step card leaves clear
  const card=document.querySelector('.dock').getBoundingClientRect();
  const top=70,bottom=w<760?card.top:h-24;
  viewOffsetY=Math.round(h/2-(top+bottom)/2);
  camera.setViewOffset(w,h,0,viewOffsetY,w,h);
  camera.updateProjectionMatrix();
  if(composer){composer.setSize(w,h);}
  dirty=true;
}
// a camera preset is written for a 40° landscape view; narrower screens step back to keep the same width in frame
function framed(c){
  const pos=W(...c.pos),tgt=W(...c.target);
  const vf=camera.fov*Math.PI/360,hf=Math.atan(Math.tan(vf)*camera.aspect),want=Math.atan(Math.tan(20*Math.PI/180)*1.6);
  const k=Math.max(1,Math.tan(want)/Math.tan(hf))*1*(Math.tan(20*Math.PI/180)/Math.tan(vf));
  return {pos:tgt.clone().add(pos.sub(tgt).multiplyScalar(Math.max(0.75,k))),tgt};
}

/* ---------------- steps, URL and UI ---------------- */
const STEPS=P.STEPS,LAST=P.LAST;
let cur=-1,t=0,playing=false,tween=null,dirty=true,showLabels=true;
const prog=$('progress');
STEPS.forEach((s,i)=>{const a=document.createElement('a');a.href=i?'#step-'+i:'#overview';a.title=(i?'Step '+i+': ':'')+s.title;a.setAttribute('aria-label',a.title);prog.appendChild(a);});
function hashStep(){const m=location.hash.match(/^#step-(\d+)$/);if(m)return Math.max(0,Math.min(LAST,+m[1]));return 0;}

// the parts a step adds, grouped by what the card calls them (body.listAs, or its label without left/right) and size
const STRIP=new RegExp(META.listStrip||'^(Left|Right) ');
const sideless=l=>l.replace(STRIP,'').replace(/,? (left|right)$/i,'');
function partsOf(s){
  const groups=new Map();
  s.moves.forEach(m=>{
    if(m.remove)return;const b=P.BODY[m.body];
    // a sub-assembly whose parts arrive in this same step is listed part by part; one already glued up is listed whole
    if(b.virtual&&s.moves.some(o=>P.BODY[o.body].parent===b.id))return;
    const size=P.sizeText(b),name=b.listAs||sideless(b.label),key=name+'|'+size;
    const g=groups.get(key)||{label:name.replace(/^./,c=>c.toUpperCase()),size,n:0,ids:[]};g.n++;g.ids.push(b.id);groups.set(key,g);
  });
  return [...groups.values()];
}
const removedOf=s=>s.moves.filter(m=>m.remove).length;
function renderCard(){
  const s=STEPS[cur];
  $('sNum').textContent=cur?'Step '+cur+' of '+LAST:'Overview · '+LAST+' steps';
  const sh=$('sSheet');sh.hidden=!s.sheet;sh.textContent=s.sheet?(s.sheet==='Shop'?'Shop fixture':(META.sheetLabel?META.sheetLabel+' ':'')+s.sheet):'';
  $('sTitle').textContent=s.title;$('sText').textContent=s.text;
  const ul=$('sParts');ul.innerHTML='';
  const groups=cur?partsOf(s):[];
  groups.forEach(g=>{const li=document.createElement('li');li.innerHTML='<span class="q">'+g.n+'×</span><span class="n"></span><span class="d"></span>';li.children[1].textContent=g.label;li.children[2].textContent=g.size;ul.appendChild(li);});
  if(cur&&removedOf(s)){const li=document.createElement('li');li.innerHTML='<span class="q">−'+removedOf(s)+'</span><span class="n">Temporary pieces come off</span><span class="d"></span>';ul.appendChild(li);}
  ul.hidden=!ul.children.length;
  [...prog.children].forEach((a,i)=>{a.className=i<cur?'done':i===cur?'cur':'';if(i===cur)a.setAttribute('aria-current','step');else a.removeAttribute('aria-current');});
  $('bPrev').disabled=cur===0;
  $('bNextT').textContent=cur===0?'Start building':cur===LAST?'Finished '+META.thing:'Next';
  $('bNext').setAttribute('aria-label',cur===0?'Start building':cur===LAST?'Show the finished '+META.thing:'Next step');
  document.title=(cur?'Step '+cur+' · ':'')+META.title;
}
function go(i,o){
  o=o||{};i=Math.max(0,Math.min(LAST,i));
  const changed=i!==cur;cur=i;
  t=reduceMotion||cur===0?Infinity:-0.35;playing=t!==Infinity;
  if(changed||o.recam)flyTo(STEPS[cur].cam,o.instant);
  controls.autoRotate=cur===0&&!reduceMotion;controls.autoRotateSpeed=0.35;
  renderCard();resize();clearLabels();dirty=true;
  const h=cur?'#step-'+cur:'#overview';if(location.hash!==h&&!(cur===0&&!location.hash))history.replaceState(null,'',h);
}
function flyTo(c,instant){
  const f=framed(c);
  if(instant||reduceMotion){camera.position.copy(f.pos);controls.target.copy(f.tgt);tween=null;controls.update();return;}
  tween={p0:camera.position.clone(),t0:controls.target.clone(),p1:f.pos,t1:f.tgt,u:0};
}
$('bNext').onclick=()=>go(cur===LAST?0:cur+1);
$('bPrev').onclick=()=>go(cur-1);
$('bReplay').onclick=()=>{go(cur,{recam:true});};
$('tView').onclick=()=>flyTo(STEPS[cur].cam);
$('tLabels').onclick=e=>{showLabels=!showLabels;e.currentTarget.setAttribute('aria-pressed',String(showLabels));clearLabels();dirty=true;};
$('tInfo').onclick=e=>{const on=$('info').hidden;$('info').hidden=!on;e.currentTarget.setAttribute('aria-pressed',String(on));};
addEventListener('hashchange',()=>{const i=hashStep();if(i!==cur)go(i);});
addEventListener('keydown',e=>{
  if(e.target.closest&&e.target.closest('input,textarea'))return;
  if(e.key==='ArrowRight'||e.key==='PageDown'){go(cur+1);e.preventDefault();}
  else if(e.key==='ArrowLeft'||e.key==='PageUp'){go(cur-1);e.preventDefault();}
  else if(e.key==='Home'){go(0);}else if(e.key==='End'){go(LAST);}
  else if(e.key==='r'||e.key==='R'){go(cur,{recam:true});}
});
controls.addEventListener('start',()=>{tween=null;controls.autoRotate=false;$('tip').hidden=true;});
controls.addEventListener('change',()=>{dirty=true;});
addEventListener('resize',resize);

/* ---------------- labels for the parts added in a step ---------------- */
const labelsEl=$('labels'),labelPool=[];
function clearLabels(){labelPool.forEach(l=>l.el.classList.remove('on'));}
function labelTargets(){
  if(!cur||!showLabels)return [];
  const out=[];
  partsOf(STEPS[cur]).slice(0,innerWidth<760?3:6).forEach(g=>{
    const id=g.ids[0],b=P.BODY[id];
    const bb=P.bodyBounds(b),c=[(bb.min[0]+bb.max[0])/2,(bb.min[1]+bb.max[1])/2,bb.max[2]];
    out.push({id,text:g.label,size:(g.n>1?g.n+' × ':'')+g.size,c});
  });
  return out;
}
const v3=new THREE.Vector3();
function updateLabels(st,done){
  const L=done?labelTargets():[];
  while(labelPool.length<L.length){const el=document.createElement('div');el.className='lab';el.innerHTML='<span><b></b><em></em></span>';labelsEl.appendChild(el);labelPool.push({el});}
  // project each anchor, then nudge labels up so none sit on top of another
  const placed=[];
  L.forEach((d,i)=>{
    const s=st[d.id]||st[P.BODY[d.id].parent];const p=P.mApply(s.M,d.c);
    v3.set((p[0]-CX)*IN,(p[2]+0.6*U)*IN,(CY-p[1])*IN).project(camera);
    d.x=(v3.x*.5+.5)*innerWidth;d.y=(-v3.y*.5+.5)*innerHeight;d.off=0;d.hide=v3.z>1;d.w=Math.max(d.text.length*7.6,d.size.length*7.4)+20;
    // keep the whole label on screen, even when its part is near the edge
    d.x=Math.max(d.w/2+6,Math.min(innerWidth-d.w/2-6,d.x));
  });
  L.filter(d=>!d.hide).sort((a,b)=>b.y-a.y).forEach(d=>{
    for(let k=0;k<8;k++){const top=d.y-d.off;const hit=placed.find(q=>Math.abs(q.x-d.x)<(q.w+d.w)/2+4&&Math.abs((q.y-q.off)-top)<44);if(!hit)break;d.off+=(top-(hit.y-hit.off))+46;}
    placed.push(d);
  });
  labelPool.forEach((l,i)=>{
    const d=L[i];if(!d||d.hide){l.el.classList.remove('on');return;}
    if(l.el.firstChild.firstChild.textContent!==d.text||l.el.firstChild.lastChild.textContent!==d.size){l.el.firstChild.firstChild.textContent=d.text;l.el.firstChild.lastChild.textContent=d.size;}
    l.el.style.setProperty('--stem',(18+d.off)+'px');
    l.el.style.transform=`translate(${d.x.toFixed(1)}px,${d.y.toFixed(1)}px) translate(-50%,-100%)`;l.el.classList.add('on');
  });
}

/* ---------------- tap a part to measure it ---------------- */
const ray=new THREE.Raycaster(),ndc=new THREE.Vector2();let down=null;
canvas.addEventListener('pointerdown',e=>{down={x:e.clientX,y:e.clientY};});
canvas.addEventListener('pointerup',e=>{
  if(!down||Math.hypot(e.clientX-down.x,e.clientY-down.y)>6){down=null;return;}down=null;
  const r=canvas.getBoundingClientRect();ndc.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);
  ray.setFromCamera(ndc,camera);
  const hit=ray.intersectObjects(pickables.filter(m=>m.parent.visible),false)[0];
  const tip=$('tip');
  if(!hit){tip.hidden=true;return;}
  const {part,body}=hit.object.userData;
  const d=[0,1,2].map(i=>part.max[i]-part.min[i]).sort((a,b)=>a-b);
  const nm=body.parent?P.BODY[body.parent].label+' · '+body.label:body.label;
  tip.innerHTML='<b></b><span></span>';tip.firstChild.textContent=nm;
  tip.lastChild.textContent=part.note||d.map(P.fmt).join(' × ');
  const x=Math.min(e.clientX,innerWidth-300);tip.style.left=x+'px';tip.style.top=e.clientY+'px';tip.hidden=false;
});

/* ---------------- loop ---------------- */
const clock=new THREE.Clock();
let lastSt=null;
function frame(){
  requestAnimationFrame(frame);
  const dt=Math.min(clock.getDelta(),0.05);
  if(tween){tween.u=Math.min(1,tween.u+dt/1.3);const k=tween.u<.5?4*tween.u**3:1-(-2*tween.u+2)**3/2;
    camera.position.lerpVectors(tween.p0,tween.p1,k);controls.target.lerpVectors(tween.t0,tween.t1,k);if(tween.u>=1)tween=null;dirty=true;}
  if(playing){t+=dt;const D=STEPS[cur].dur;if(t>D+1.6)playing=false;dirty=true;}
  const moved=controls.update();
  if(!dirty&&!moved&&!controls.autoRotate)return;
  dirty=false;
  const st=P.evaluate(cur,playing?Math.max(0,t):(t===Infinity?Infinity:t));
  applyState(st,cur>0?cur:null,t===Infinity?99:t);
  lastSt=st;
  updateLabels(st,cur>0&&(t===Infinity||t>STEPS[cur].dur+0.15));
  if(composer)composer.render();else renderer.render(scene,camera);
}

/* ---------------- start ---------------- */
$('iParts').textContent=P.PARTS.filter(p=>!p.decal&&!P.BODY[p.body].temp).length+' pieces in '+P.BODIES.filter(b=>!b.virtual&&!b.temp).length+' assemblies';
const first=hashStep();
cur=-1;go(first,{instant:true});
if(first>0){t=-0.6;}
resize();
requestAnimationFrame(()=>{frame();setTimeout(()=>$('loading').classList.add('gone'),250);});
// re-run the physics check in the viewer's own browser
setTimeout(()=>{
  const r=P.verify({samples:24});const el=$('iCheck');
  el.className='check '+(r.ok?'ok':'bad');
  el.lastChild.textContent=r.ok?'Checked just now in this browser: across all '+r.steps+' steps no part passes through another while it moves, every part lands on or against something already there, and the finished '+META.thing+' has no overlapping parts.'
    :'The physics check found '+r.issues.length+' problems, starting at step '+r.issues[0].step+': '+r.issues[0].kind+', '+r.issues[0].a+'.';
},1200);
window.__view={settle(x){t=x===undefined?Infinity:x;playing=false;tween=null;controls.autoRotate=false;dirty=true;},go,get step(){return cur},camera,controls,renderer,scene,ready:true};
