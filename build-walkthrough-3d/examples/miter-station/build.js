/* Kapex 120 Miter Station: the worked example for build-walkthrough-3d.
   A 96″ mobile bench in ½″ Baltic birch with a Festool Kapex KS 120 dropped into a 30″ bay; 280 parts, 30 steps.
   Plan coordinates in inches: x along the bench (left to right), y front (0) to back (26), z up from the floor.
   Part geometry is the drawing set's own model (Rev A), with the T-track grooves, drawer slides,
   flip-stop arms and temporary shop fixtures added so every part has somewhere real to sit. */
(function(root){
"use strict";
const K=root.Walkthrough.create({units:'in'});
const {body,inBody,box,cyl,step,mv,at,HOME,drop,slide,orbit,fmt,BODY}=K;

const L=96, D=26, H=36, CAST=4, LAY=0.5, PW=3.5, RW=3, MR=2;
const TABLE_H=4.33, PT=H-TABLE_H, FY=12, FT=1.5, FH=3.5, REV=1/16;

/* ---------- shop furniture the moves must avoid ---------- */
const TABLE=K.table([-94,-56,0],[-46,-20,34],'Assembly table');
[[16,13],[48,13],[80,13],[-70,-38]].forEach(([x,y])=>K.pendant(x,y,92));

/* ---------- cross-frames (B-101) ---------- */
const FRAMES=[{x0:0,label:'Left end frame',flip:false},{x0:32,label:'Left bay wall',flip:true},
              {x0:63,label:'Right bay wall',flip:false},{x0:95,label:'Right end frame',flip:true}];
FRAMES.forEach((f,k)=>{
  const x0=f.x0, A=f.flip?[x0+LAY,x0+1]:[x0,x0+LAY], B=f.flip?[x0,x0+LAY]:[x0+LAY,x0+1];
  const zb=CAST, zt=H-1, LIP=0.5, CH=1;
  f.id='F'+k;
  body(f.id,f.label,{virtual:true,pivot:[x0+0.5,D/2,(zb+zt)/2],frame:k,loose:true});
  const pc=(id,label,fn)=>{body(f.id+id,label,{parent:f.id});inBody(f.id+id,fn);};
  const n=(t)=>f.label+' · '+t;
  pc('pf','Post, layer 1',()=>box(n('front post, layer 1'),'frame',[A[0],0,zb],[A[1],PW,zt],{ply:0}));
  pc('pr','Post, layer 1',()=>box(n('rear post, layer 1'),'frame',[A[0],D-PW,zb],[A[1],D,zt],{ply:0}));
  pc('rt','Short rail, layer 1',()=>box(n('top rail, layer 1'),'frame',[A[0],PW,zt-RW],[A[1],D-PW,zt]));
  pc('rb','Short rail, layer 1',()=>box(n('bottom rail, layer 1'),'frame',[A[0],PW,zb],[A[1],D-PW,zb+RW]));
  pc('lt','Long rail with tenons, layer 2',()=>box(n('top rail, layer 2'),'frame',[B[0],CH,zt-RW+LIP],[B[1],D-CH,zt]));
  pc('lb','Long rail with tenons, layer 2',()=>box(n('bottom rail, layer 2'),'frame',[B[0],CH,zb],[B[1],D-CH,zb+RW-LIP]));
  pc('sf','Short post, layer 2',()=>box(n('front post, layer 2'),'frame',[B[0],CH,zb+RW-LIP],[B[1],PW-LIP,zt-RW+LIP]));
  pc('sr','Short post, layer 2',()=>box(n('rear post, layer 2'),'frame',[B[0],D-PW+LIP,zb+RW-LIP],[B[1],D-CH,zt-RW+LIP]));
  pc('pn','Infill panel',()=>box(n('infill panel'),'panel',[B[0],PW-LIP,zb+RW-LIP],[B[1],D-PW+LIP,zt-RW+LIP]));
});

/* ---------- long rails and fillers (B-102, B-103) ---------- */
function longRail(id,label,x0,x1,front,z0,z1){
  body(id,label);
  inBody(id,()=>{
    const ys=front?[[0,LAY],[LAY,1]]:[[D-1,D-LAY],[D-LAY,D]];
    ys.forEach((y,i)=>box(label+(i===(front?0:1)?' (face layer)':' (back layer)'),'frame',[x0,y[0],z0],[x1,y[1],z1]));
  });
}
const WINGS=[[1,32,'Left wing','L'],[64,95,'Right wing','R']];
const WING_OPEN=[[27,32],[18,25],[7,16]];
WINGS.forEach(([a0,b0,n,k])=>{
  const a=a0-LAY,b=b0+LAY;
  longRail('W'+k+'ft',n+' front top rail',a,b,true,32,35);
  longRail('W'+k+'fd2',n+' front divider',a,b,true,25,27);
  longRail('W'+k+'fd1',n+' front divider',a,b,true,16,18);
  longRail('W'+k+'fb',n+' front bottom rail',a,b,true,4,7);
  longRail('W'+k+'rt',n+' rear top rail',a,b,false,32,35);
  longRail('W'+k+'rb',n+' rear bottom rail',a,b,false,4,7);
  [[a,a0,'a'],[b0,b,'b']].forEach(([c0,c1,e])=>{
    [[7,16,'9″','9'],[18,25,'7″','7'],[27,32,'5″','5']].forEach(([z0,z1,t,s])=>{
      const id='W'+k+'f'+s+e; body(id,'Filler for the '+t+' opening');
      inBody(id,()=>box(n+' front filler, '+t+' opening','frame',[c0,0,z0],[c1,1,z1],{ply:0}));
    });
    const id='W'+k+'rf'+e; body(id,'Rear filler, 25″');
    inBody(id,()=>box(n+' rear filler, 25″','frame',[c0,D-1,7],[c1,D,32],{ply:0}));
  });
});
const PR=[PT-1-MR,PT-1];
longRail('Bfp','Saw bay front platform rail',33,63,true,PR[0],PR[1]);
longRail('Bfd','Saw bay front divider',33,63,true,16,18);
longRail('Bfb','Saw bay front bottom rail',33,63,true,4,7);
longRail('Brp','Saw bay rear platform rail',33,63,false,PR[0],PR[1]);
longRail('Brb','Saw bay rear bottom rail',33,63,false,4,7);
const BAY_OPEN=[[18,PR[0]],[7,16]];

/* ---------- platform and tops (B-103, B-104) ---------- */
body('PL','Saw platform, two layers glued',{loose:true});
inBody('PL',()=>{
  box('Saw platform (lower layer)','platform',[33,0,PT-1],[63,D,PT-LAY]);
  box('Saw platform (upper layer)','platform',[33,0,PT-LAY],[63,D,PT]);
});
const TRACK_Y=[3.5,8,19.5], TW=0.75, TD=0.375;
[[0,33,'Left wing top','L'],[63,96,'Right wing top','R']].forEach(([a,b,n,k])=>{
  body('T'+k+'1',n+', lower layer',{loose:true});
  inBody('T'+k+'1',()=>box(n+' (lower layer)','top',[a,0,H-1],[b,D,H-LAY]));
  body('T'+k+'2',n+', upper layer, routed for track',{loose:true});
  inBody('T'+k+'2',()=>{
    // upper layer with three ¾″ × ⅜″ grooves for the T-track
    box(n+' (upper layer, under the grooves)','top',[a,0,H-LAY],[b,D,H-TD],{plyBase:H-LAY,skin:true});
    let y=0;
    TRACK_Y.forEach(yc=>{box(n+' (upper layer)','top',[a,y,H-TD],[b,yc-TW/2,H],{plyBase:H-LAY});y=yc+TW/2;});
    box(n+' (upper layer)','top',[a,y,H-TD],[b,D,H],{plyBase:H-LAY});
  });
  TRACK_Y.forEach((yc,i)=>{
    body('T'+k+'t'+i,'T-track, '+fmt(yc)+' from the front');
    inBody('T'+k+'t'+i,()=>box(n+' T-track at '+fmt(yc)+' from front','track',[a,yc-TW/2,H-TD],[b,yc+TW/2,H+0.02],{mat:'steel',profile:'ttrack'}));
  });
});

/* ---------- drawers, slides and faces (B-106) ---------- */
const DRAWERS=[];
const SLIDE_H=1.75;
function drawer(x0,x1,z0,z1,name,k){
  const id='D'+k; DRAWERS.push({id,name,x0,x1,z0,z1});
  const bx0=x0+0.5,bx1=x1-0.5,bz0=z0+0.5,bz1=z1-0.75,by0=1.0,by1=23;
  const zc=(bz0+bz1)/2;
  body(id+'sa',name+' slide, left',{});
  inBody(id+'sa',()=>box(name+' slide, left','slide',[x0,by0,zc-SLIDE_H/2],[bx0,by1,zc+SLIDE_H/2],{mat:'zinc'}));
  body(id+'sb',name+' slide, right',{});
  inBody(id+'sb',()=>box(name+' slide, right','slide',[bx1,by0,zc-SLIDE_H/2],[x1,by1,zc+SLIDE_H/2],{mat:'zinc'}));
  body(id+'b',name+' box',{});
  inBody(id+'b',()=>{
    box(name+' box side L','box',[bx0,by0,bz0],[bx0+LAY,by1,bz1]);
    box(name+' box side R','box',[bx1-LAY,by0,bz0],[bx1,by1,bz1]);
    box(name+' box front','box',[bx0+LAY,by0,bz0],[bx1-LAY,by0+LAY,bz1]);
    box(name+' box back','box',[bx0+LAY,by1-LAY,bz0],[bx1-LAY,by1,bz1]);
    box(name+' box bottom','box',[bx0+LAY,by0+LAY,bz0],[bx1-LAY,by1-LAY,bz0+LAY]);
  });
  body(id+'f',name+' face',{});
  inBody(id+'f',()=>{
    box(name+' face (outer layer)','face',[x0+REV,0,z0+REV],[x1-REV,LAY,z1-REV]);
    box(name+' face (inner layer)','face',[x0+REV,LAY,z0+REV],[x1-REV,1,z1-REV]);
    const cx=(x0+x1)/2;
    box(name+' finger pull','decal',[cx-2.5,-0.012,z1-REV-1.1],[cx+2.5,-0.002,z1-REV-0.25],{decal:true,note:'Finger pull, 5″ wide'});
  });
}
let dk=0;
WINGS.forEach(([a,b,n])=>WING_OPEN.forEach(([z0,z1],i)=>drawer(a,b,z0,z1,n+' drawer '+(i+1),dk++)));
BAY_OPEN.forEach(([z0,z1],i)=>drawer(33,63,z0,z1,'Saw bay drawer '+(i+1),dk++));

/* ---------- fences, track, tapes, flip stops (B-105) ---------- */
const FG0=FY+0.65, FG1=FY+1.4, FGZ=H+FH-0.375;   // fence track groove
[[0,32.75,'Left fence',[6,16,26],'L'],[63.25,96,'Right fence',[70,80,90],'R']].forEach(([a,b,n,stops,k])=>{
  body('FN'+k,n+', three layers glued',{loose:true});
  inBody('FN'+k,()=>{
    box(n+' (layer 1 of 3)','fence',[a,FY,H],[b,FY+LAY,H+FH]);
    box(n+' (layer 2 of 3)','fence',[a,FY+LAY,H],[b,FY+2*LAY,FGZ],{plyBase:FY+LAY});
    box(n+' (layer 2 of 3, beside the groove)','fence',[a,FY+LAY,FGZ],[b,FG0,H+FH],{plyBase:FY+LAY});
    box(n+' (layer 3 of 3)','fence',[a,FY+2*LAY,H],[b,FY+3*LAY,FGZ],{plyBase:FY+2*LAY});
    box(n+' (layer 3 of 3, beside the groove)','fence',[a,FG1,FGZ],[b,FY+3*LAY,H+FH],{plyBase:FY+2*LAY});
  });
  body('FT'+k,n+' T-track',{});
  inBody('FT'+k,()=>box(n+' T-track','track',[a,FG0,FGZ],[b,FG1,H+FH+0.03],{mat:'steel',profile:'ttrack'}));
  body('FM'+k,n+' tape measure',{});
  inBody('FM'+k,()=>box(n+' tape measure, reads out from the blade','tape',[a,FY+0.05,H+FH],[b,FY+0.55,H+FH+0.02],{mat:'steel',tape:{zero:48}}));
  stops.forEach((x,i)=>{
    body('FS'+k+i,'Flip stop',{loose:true});
    inBody('FS'+k+i,()=>{
      box(n+' flip stop '+(i+1)+' body','stops',[x-0.8,FY-0.4,H+FH+0.03],[x+0.8,FY+FT+0.2,H+FH+0.9],{mat:'paint',color:'#B8352B'});
      box(n+' flip stop '+(i+1)+' paddle','stops',[x-0.6,FY-0.4,H+1],[x+0.6,FY-0.05,H+FH+0.03],{mat:'paint',color:'#B8352B'});
    });
  });
});

/* ---------- castors (B-107) ---------- */
const CASTORS=[[2.5,2.5],[93.5,2.5],[2.5,23.5],[93.5,23.5],[35,13],[61,13]];
CASTORS.forEach(([x,y],i)=>{
  const bid='CB'+i; body(bid,'Castor block, three layers');
  inBody(bid,()=>{
    if(i<4){const bx=x<48?[1,4.5]:[91.5,95], by=y<13?[1,4.5]:[21.5,25];
      box('Castor mounting block '+(i+1)+' (3 layers)','frame',[bx[0],by[0],CAST],[bx[1],by[1],CAST+1.5]);}
    else box('Castor mounting block '+(i+1)+' (3 layers)','frame',[x-2,y-2,CAST],[x+2,y+2,CAST+1.5]);
  });
  const cid='CA'+i; body(cid,'Leveling castor',{loose:true,sizeText:'4″ tall to the plate'});
  inBody(cid,()=>{
    const n='Leveling castor '+(i+1);
    box(n+' plate','castor',[x-1.6,y-1.6,CAST-0.2],[x+1.6,y+1.6,CAST],{mat:'steel'});
    box(n+' housing','castor',[x-1.1,y-1.3,1.6],[x+1.1,y+1.3,CAST-0.2],{mat:'steel'});
    cyl(n+' wheel','castorWheel','x',[x,y-0.4,1.2],1.2,0.9,{mat:'rubber'});
    cyl(n+' leveling pad','castorPad','z',[x,y+0.9,0.25],1.0,0.5,{mat:'rubber'});
  });
});

/* ---------- Kapex KS 120 (simplified volume, from the drawing set) ---------- */
const kx=48;
body('KX','Festool Kapex KS 120',{loose:true,sizeText:'713 × 500 mm footprint'});
inBody('KX',()=>{
  const kp=g=>Object.assign({note:'Festool KS 120 (simplified volume)'},
    {kapex:{mat:'paint',color:'#73A83F'},kapexDark:{mat:'paint',color:'#2C3034'},alu:{mat:'alu'},blade:{mat:'blade'}}[g]);
  box('Kapex base','kapexDark',[37,3,PT],[59,19,H-0.7],kp('kapexDark'));
  box('Kapex left table','alu',[34.1,5,H-0.7],[43,19,H],kp('alu'));
  box('Kapex right table','alu',[53,5,H-0.7],[61.9,19,H],kp('alu'));
  cyl('Kapex turntable','alu','z',[kx,10.5,H-0.35],5.8,0.7,kp('alu'));
  box('Kapex miter handle','kapex',[46.6,1,H-1],[49.4,4.7,H],kp('kapex'));
  box('Kapex fence, left half','alu',[36,FY,H],[47.2,FY+0.8,H+FH],kp('alu'));
  box('Kapex fence, right half','alu',[48.8,FY,H],[60,FY+0.8,H+FH],kp('alu'));
  box('Kapex tilt column','kapex',[45,17.5,H],[51,20.7,H+9.5],kp('kapex'));
  box('Kapex head and rail housing','kapex',[44.5,6,H+9.5],[51.5,20.7,H+12.5],kp('kapex'));
  cyl('Kapex motor','kapexDark','x',[54.2,12.5,H+10.2],2.3,5.6,kp('kapexDark'));
  cyl('Kapex blade, 260 mm','blade','x',[kx,10.5,H+6.2],5.1,0.12,kp('blade'));
  box('Kapex upper guard','kapex',[46.9,4.8,H+6.2],[49.1,16.2,H+11.6],kp('kapex'));
  box('Kapex handle','kapexDark',[45.2,2.6,H+11],[50.8,5.2,H+14.1],kp('kapexDark'));
});

/* ---------- temporary shop fixtures: build stands and a brace ---------- */
const STAND_Y=[[5,9],[17,21]];
FRAMES.forEach((f,k)=>{
  STAND_Y.forEach(([y0,y1],j)=>{
    const s='S'+k+j;
    body(s+'b','Build stand block, 4″ tall',{loose:true,temp:true});
    inBody(s+'b',()=>box('Build stand block','temp',[f.x0,y0,0],[f.x0+1,y1,CAST],{mat:'pine'}));
    body(s+'o','Stand cheek',{loose:true,temp:true});
    inBody(s+'o',()=>box('Stand cheek','temp',[f.x0-1.5,y0,0],[f.x0,y1,7],{mat:'pine'}));
    body(s+'i','Stand cheek',{loose:true,temp:true});
    inBody(s+'i',()=>box('Stand cheek','temp',[f.x0+1,y0,0],[f.x0+2.5,y1,7],{mat:'pine'}));
  });
});
body('BR','Temporary brace, 2×4',{loose:true,temp:true});
inBody('BR',()=>box('Temporary brace','temp',[-2,11.25,H-1],[98,14.75,H+0.5],{mat:'pine'}));

/* ---------- assembly sequence ---------- */
/* frames lie flat on the assembly table, layer 1 down; stacked one on another */
const TBL_C=[(TABLE.min[0]+TABLE.max[0])/2,(TABLE.min[1]+TABLE.max[1])/2,TABLE.max[2]];
function flatPose(k,level){
  const f=FRAMES[k],b=BODY[f.id],c=b.pivot,rot=f.flip?90:-90;
  return {rot,off:[TBL_C[0]-c[0],TBL_C[1]-c[1],TBL_C[2]+0.5+level-c[2]]};
}
// a world-space offset for a part of a frame lying flat, expressed in the frame's own coordinates
function frameLocal(k,w){const a=(FRAMES[k].flip?90:-90)*Math.PI/180,c=Math.cos(-a),s=Math.sin(-a);return [c*w[0]+s*w[2],w[1],-s*w[0]+c*w[2]];}
const fdrop=(k,h)=>[{off:frameLocal(k,[0,0,h])},HOME];

const LIFT_C=62;
function standPath(k){
  const f=FRAMES[k],c=BODY[f.id].pivot,fp=flatPose(k,k);
  const up={rot:fp.rot,off:[fp.off[0],fp.off[1],LIFT_C-c[2]]};
  return [fp,up,{rot:0,off:[0,0,LIFT_C-c[2]]},HOME];
}

step({key:'start',title:'Your miter station',
  text:'A 96″ mobile bench in ½″ Baltic birch with the Festool Kapex KS 120 dropped into a 30″ bay, so its table lands flush with 33″ wings at 36″. Every part below is cut to the drawing set.',
  cam:orbit([48,13,20],-30,18,128),intro:true});

step({key:'layer-1-posts',title:'Lay out the layer 1 posts',sheet:'B-101',
  text:'Start the left end frame flat on the assembly table. The two layer 1 posts run the full 31″ height, 22½″ apart so the rails fit between them.',
  cam:orbit([-70,-38,35],-25,42,82)});
mv('F0',[flatPose(0,0)]);
mv('F0pf',fdrop(0,10));mv('F0pr',fdrop(0,10),{delay:0.25});

step({key:'layer-1-rails',title:'Fit the layer 1 rails between them',sheet:'B-101',
  text:'The 3″ top and bottom rails sit between the posts. Square the frame across its diagonals before you glue on layer 2.',
  cam:orbit([-70,-38,35],-25,42,82)});
mv('F0rt',fdrop(0,10));mv('F0rb',fdrop(0,10),{delay:0.25});

step({key:'layer-2-rails',title:'Glue on the layer 2 rails',sheet:'B-101',
  text:'The layer 2 rails run 24″, past the layer 1 posts, so each end becomes a ½″ × 2½″ × 3½″ tenon. They stop 1″ shy of the front and back edges to leave the channel the long rails sit in.',
  cam:orbit([-70,-38,35],-25,42,82)});
mv('F0lt',fdrop(0,10));mv('F0lb',fdrop(0,10),{delay:0.25});

step({key:'layer-2-posts',title:'Glue on the short layer 2 posts',sheet:'B-101',
  text:'The layer 2 posts stop short at each end, so the layers cross at every corner and lock into a mortise and tenon. Each is 2″ wide, leaving a ½″ ledge of layer 1 showing round the opening.',
  cam:orbit([-70,-38,35],-25,42,82)});
mv('F0sf',fdrop(0,10));mv('F0sr',fdrop(0,10),{delay:0.25});

step({key:'infill-panel',title:'Drop the infill panel onto the ledge',sheet:'B-101',
  text:'The 20″ × 26″ panel rests on the ½″ ledge all round and finishes flush with layer 2. It cannot push through. Clamp or brad-nail the layers until the glue sets.',
  cam:orbit([-70,-38,35],-25,42,82)});
mv('F0pn',fdrop(0,10));

step({key:'four-frames',title:'Make three more frames the same way',sheet:'B-101',
  text:'All four cross-frames are identical: two ends and two saw bay walls. Two of them get turned round when they stand up, so the flat layer 2 face always points at the drawers.',
  cam:orbit([-70,-38,37],-30,35,115)});
[1,2,3].forEach((k,i)=>mv('F'+k,[{rot:flatPose(k,k).rot,off:flatPose(k,k).off.map((v,j)=>j===2?v+16:v)},flatPose(k,k)],{delay:i*0.55}));

step({key:'build-stands',title:'Set out the build stands',sheet:'Shop',
  text:'Eight 4″ blocks hold the frames at their finished height, the same as the castors will. A pine cheek either side of each block keeps the frame upright. Space them at 0, 32, 63 and 95″.',
  cam:orbit([48,13,4],-15,30,150)});
FRAMES.forEach((f,k)=>STAND_Y.forEach((_,j)=>{const d=(k*2+j)*0.12;
  mv('S'+k+j+'b',drop(10),{delay:d});mv('S'+k+j+'o',drop(10),{delay:d+0.05});mv('S'+k+j+'i',drop(10),{delay:d+0.1});}));

step({key:'stand-frames',title:'Stand the frames in their stands',sheet:'B-102',
  text:'Lift each frame off the stack, turn it upright and lower it between the cheeks. The right end goes first and the left end, which is at the bottom of the stack, goes last.',
  cam:orbit([14,-10,24],-8,18,235)});
[3,2,1,0].forEach((k,i)=>mv('F'+k,standPath(k),{delay:i*2.1,dur:2.6,seg:[0.22,0.5,0.28]}));

step({key:'brace',title:'Screw a temporary brace across the tops',sheet:'Shop',
  text:'A straight 2×4 holds the four frames plumb and at the right spacing until the rails tie them together. It comes off again once the top rails are in.',
  cam:orbit([48,13,24],-20,26,165)});
mv('BR',drop(14));

step({key:'bottom-rails',title:'Slide in the bottom rails',sheet:'B-102',
  text:'Each wing rail is 32″: 31″ between the frames plus ½″ into the channel at each end. The front rails slide in from the front and the rear rails from the back. The 30″ saw bay rails butt the bay walls on Dominos.',
  cam:orbit([48,13,10],-25,18,150)});
['WLfb','WRfb','Bfb'].forEach((id,i)=>mv(id,slide(0,-30,0),{delay:i*0.3}));
['WLrb','WRrb','Brb'].forEach((id,i)=>mv(id,slide(0,30,0),{delay:0.9+i*0.3}));

step({key:'nine-inch',title:'Set the 9″ fillers and the first divider',sheet:'B-102',
  text:'The fillers sit in the channel on top of the bottom rail and set the drawer opening, so there is nothing to measure. The 2″ divider sits on top of them.',
  cam:orbit([40,10,14],-30,15,130)});
['WLf9a','WLf9b','WRf9a','WRf9b'].forEach((id,i)=>mv(id,slide(0,-18,0),{delay:i*0.15}));
['WLfd1','WRfd1','Bfd'].forEach((id,i)=>mv(id,slide(0,-30,0),{delay:0.8+i*0.25}));

step({key:'seven-inch',title:'Set the 7″ fillers and the second divider',sheet:'B-102',
  text:'Same again: 7″ fillers on the divider, then the next 2″ divider on top of them. Front faces finish flush.',
  cam:orbit([40,10,20],-30,15,130)});
['WLf7a','WLf7b','WRf7a','WRf7b'].forEach((id,i)=>mv(id,slide(0,-18,0),{delay:i*0.15}));
['WLfd2','WRfd2'].forEach((id,i)=>mv(id,slide(0,-30,0),{delay:0.8+i*0.25}));

step({key:'five-inch',title:'Finish the front with the 5″ fillers and top rails',sheet:'B-102',
  text:'The 5″ fillers go in, then the 3″ top rails. Fix every rail end through post A with a Domino or two screws, and check each opening for square before the glue sets.',
  cam:orbit([40,10,26],-30,16,130)});
['WLf5a','WLf5b','WRf5a','WRf5b'].forEach((id,i)=>mv(id,slide(0,-18,0),{delay:i*0.15}));
['WLft','WRft'].forEach((id,i)=>mv(id,slide(0,-30,0),{delay:0.8+i*0.25}));

step({key:'rear-rails',title:'Close in the back of the wings',sheet:'B-102',
  text:'At the back, one 25″ filler stands in each channel and the 3″ top rail sits on it.',
  cam:orbit([48,13,20],135,32,125)});
['WLrfa','WLrfb','WRrfa','WRrfb'].forEach((id,i)=>mv(id,slide(0,18,0),{delay:i*0.15}));
['WLrt','WRrt'].forEach((id,i)=>mv(id,slide(0,30,0),{delay:0.8+i*0.25}));

step({key:'platform-rails',title:'Fit the saw bay platform rails',sheet:'B-103',
  text:'The 2″ platform rails go in front and back with their tops 30-11/16″ off the floor, 1″ below the platform top line.',
  cam:orbit([48,13,24],-15,30,120)});
mv('Bfp',slide(0,-30,0));mv('Brp',slide(0,30,0),{delay:0.3});

step({key:'remove-brace',title:'Take off the brace and the stand cheeks',sheet:'Shop',
  text:'With the rails glued in, the carcass holds itself square. The brace lifts off and the cheeks come up and out through the open top.',
  cam:orbit([48,13,20],-20,30,160)});
mv('BR',[HOME,at(0,0,18)],{remove:true});
FRAMES.forEach((f,k)=>STAND_Y.forEach((_,j)=>{const d=0.4+(k*2+j)*0.08;
  mv('S'+k+j+'o',[HOME,at(0,0,44)],{remove:true,delay:d});mv('S'+k+j+'i',[HOME,at(0,0,44)],{remove:true,delay:d+0.04});}));

step({key:'castor-blocks',title:'Glue in the castor blocks',sheet:'B-107',
  text:'Each block is three ½″ layers, 1½″ thick, glued into a corner or inside a bay wall. They go in from the open top and sit flush with the underside of the frame.',
  cam:orbit([36,13,5],-30,52,95)});
['CB0','CB1','CB2','CB3','CB4','CB5'].forEach((id,i)=>mv(id,drop(30),{delay:i*0.18}));

step({key:'castors',title:'Roll the leveling castors under the blocks',sheet:'B-107',
  text:'Each castor is 4″ to the top of its plate, the same height as the build stands, so it slides straight in under its block. Through-bolt the plates.',
  cam:orbit([22,13,5],-40,10,122)});
['CA0','CA1','CA4','CA5'].forEach((id,i)=>mv(id,slide(0,-26,0),{delay:i*0.2}));
['CA2','CA3'].forEach((id,i)=>mv(id,slide(0,26,0),{delay:0.9+i*0.2}));

step({key:'pull-stands',title:'Knock out the stand blocks',sheet:'B-107',
  text:'The bench now stands on its six castors. The end blocks slide out sideways and the bay wall blocks slide out front and back.',
  cam:orbit([48,13,4],-20,12,145)});
[['S00b',-14,0],['S01b',-14,0],['S30b',14,0],['S31b',14,0],['S10b',0,-22],['S11b',0,22],['S20b',0,-22],['S21b',0,22]]
  .forEach(([id,dx,dy],i)=>mv(id,[HOME,at(dx,dy,0)],{remove:true,delay:i*0.12}));

step({key:'platform',title:'Drop in the saw platform',sheet:'B-103',
  text:'Two ½″ layers glued flat, 30″ × 26″. It rests loose on the platform rails with its top at 31-11/16″. It gets shimmed flush once the saw is on.',
  cam:orbit([48,13,28],-10,40,120)});
mv('PL',drop(26));

step({key:'tops-lower',title:'Lay the lower layer of each wing top',sheet:'B-104',
  text:'33″ × 26″ each, resting on the frame tops and the top rails. Screw up from below through the top rails so the tops can be replaced.',
  cam:orbit([48,13,32],-15,38,150)});
mv('TL1',drop(20));mv('TR1',drop(20),{delay:0.3});

step({key:'tops-upper',title:'Add the upper layer, routed for track',sheet:'B-104',
  text:'The upper layer has three ¾″ × ⅜″ grooves at 3½″, 8″ and 19½″ from the front. Rout them before you glue the layer down.',
  cam:orbit([48,13,32],-15,38,150)});
mv('TL2',drop(20));mv('TR2',drop(20),{delay:0.3});

step({key:'top-track',title:'Set the T-track into the tops',sheet:'B-104',
  text:'Three runs per wing, full length, seated on the bottom of the groove and flush with the surface.',
  cam:orbit([20,12,36],-35,35,90)});
['TLt0','TLt1','TLt2','TRt0','TRt1','TRt2'].forEach((id,i)=>mv(id,drop(10),{delay:i*0.15}));

step({key:'slides',title:'Mount the drawer slides',sheet:'B-106',
  text:'22″ full-extension side-mount slides screw straight to the frame. Inside the wings the posts, rails and panels are flush, so no packers are needed.',
  cam:orbit([30,13,18],-30,20,110)});
DRAWERS.forEach((d,i)=>{mv(d.id+'sa',slide(0,-30,0),{delay:i*0.1});mv(d.id+'sb',slide(0,-30,0),{delay:i*0.1+0.05});});

step({key:'drawer-boxes',title:'Hang the eight drawer boxes',sheet:'B-106',
  text:'½″ boxes, 22″ deep, ½″ narrower than the opening each side for the slides. They ride ½″ above the opening and stop 1″ back from the front.',
  cam:orbit([48,13,18],25,18,150)});
DRAWERS.forEach((d,i)=>mv(d.id+'b',slide(0,-30,0),{delay:i*0.15}));

step({key:'drawer-faces',title:'Fit the drawer faces',sheet:'B-106',
  text:'Each face is two ½″ layers, inset with a 1/16″ reveal so it finishes flush with the 1″ frame. The finger pull is cut into the top edge.',
  cam:orbit([48,13,18],22,15,150)});
DRAWERS.forEach((d,i)=>mv(d.id+'f',slide(0,-16,0),{delay:i*0.15}));

step({key:'fences',title:'Set the fences on the wings',sheet:'B-105',
  text:'Each fence is three ½″ layers, 1½″ thick and 3½″ tall, with its face 12″ back from the front edge. Slotted holes let you true it to the Kapex fence with a straightedge.',
  cam:orbit([40,12,38],-30,30,110)});
mv('FNL',drop(14));mv('FNR',drop(14),{delay:0.3});

step({key:'fence-track',title:'Add the fence track and tapes',sheet:'B-105',
  text:'The T-track drops into a groove in the top of the fence. The stick-on tapes read out from the blade, so a reading on either side is the length of the part.',
  cam:orbit([20,12,39],-20,40,62)});
mv('FTL',drop(8));mv('FTR',drop(8),{delay:0.2});mv('FML',drop(6),{delay:0.6});mv('FMR',drop(6),{delay:0.8});

step({key:'flip-stops',title:'Slide on the flip stops',sheet:'B-105',
  text:'Three per side, riding in the fence track. Each one flips up out of the way, so they can share the track.',
  cam:orbit([22,12,39],-30,30,72)});
['FSL0','FSL1','FSL2','FSR0','FSR1','FSR2'].forEach((id,i)=>mv(id,drop(8),{delay:i*0.18}));

step({key:'kapex',title:'Set the Kapex in the bay',sheet:'B-103',
  text:'Bolt the saw through the platform at its four base holes. The KS 120 table sits 110 mm above its base, so on a 31-11/16″ platform it lands flush with the wings at 36″. Shim under the platform if your saw measures differently.',
  cam:orbit([48,12,38],25,26,112)});
mv('KX',drop(24),{dur:1.8});


root.PLAN=K.finish({meta:{
  title:'Kapex 120 Miter Station',
  eyebrow:'Step-by-step build · Rev A',
  thing:'bench',
  loading:'Cutting 280 parts from ½″ Baltic birch',
  intro:'Every part is generated from the same model as the Rev A drawing set, in inches, so what you see here is what the cut list says.',
  about:[['Overall','96″ L × 26″ D × 36″ H'],['Saw bay','30″ clear'],['Platform top','31-11/16″'],['Stock','½″ Baltic birch, laminated to 1″']],
  links:[['Open the drawing set','https://claude.ai/artifact/6BrpHsHH21HFX6xJZZA9zr']],
  sheetLabel:'Sheet',
  listStrip:'^(Left|Right) (wing |fence |)'   // the step card lists left and right pairs as one line
}});
})(typeof window!=='undefined'?window:globalThis);
