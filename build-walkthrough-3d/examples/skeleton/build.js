/* START HERE: a small plywood bookcase, the shortest build that uses every part of the API.
   Copy this file, keep the shape, replace the parts and steps.

   Coordinates in inches: x left to right, y front (0) to back, z up from the floor (z = 0).
   Every part is modelled in its FINISHED position; a move's path says where it comes from. */
(function(root){
"use strict";
const K=root.Walkthrough.create({units:'in'});
const {body,inBody,box,cyl,step,mv,at,HOME,drop,slide,orbit}=K;

/* ---------- driving dimensions: every other number derives from these ---------- */
const W=30, D=11.25, H=36, T=0.75, KICK=3, BACK=0.25, PIN_R=0.125, GAP=1/16;
const SHELF_Z=[14,25];                 // top of each shelf pin

/* ---------- the shop: an assembly table to lay parts on (optional) ---------- */
K.table([-60,-40,0],[-24,-10,34],'Assembly table');

/* ---------- parts: one body per thing that moves on its own ---------- */
body('SL','Side, left');   inBody('SL',()=>box('Left side','case',[0,0,0],[T,D,H]));
body('SR','Side, right');  inBody('SR',()=>box('Right side','case',[W-T,0,0],[W,D,H]));
body('KK','Toe kick');     inBody('KK',()=>box('Toe kick','case',[T,1,0],[W-T,1+T,KICK]));
body('BT','Bottom');       inBody('BT',()=>box('Bottom','case',[T,0,KICK],[W-T,D,KICK+T]));
body('TP','Top',{loose:true}); inBody('TP',()=>box('Top','case',[0,0,H],[W,D,H+T]));
// not loose: it is nailed on, so it only has to touch the case, not sit on something
body('BK','Back panel'); inBody('BK',()=>box('Back, ¼″ ply','back',[0,D,KICK],[W,D+BACK,H+T],{color:'#D9BF92'}));

// shelf pins: hardware, four per shelf; a cylinder is checked as its bounding box
SHELF_Z.forEach((z,s)=>{
  [[T,1],[W-T,-1]].forEach(([x,dir],side)=>[2,D-2].forEach((y,k)=>{
    const id='PN'+s+side+k;
    body(id,'Shelf pin',{sizeText:'¼″ pin',listAs:'Shelf pin'});
    inBody(id,()=>cyl('Shelf pin','pin','x',[x+dir*0.25,y,z-PIN_R],PIN_R,0.5,{mat:'brass',note:'¼″ brass shelf pin'}));
  }));
  // shelves are loose: the check proves each one SITS on its pins
  body('SH'+s,'Shelf',{loose:true});
  inBody('SH'+s,()=>box('Shelf','shelf',[T+GAP,0,z],[W-T-GAP,D-0.75,z+T]));
});

/* ---------- the sequence: step() then the moves that belong to it ---------- */
step({key:'start',intro:true,title:'Your bookcase',
  text:'A 30″ × 36″ bookcase in ¾″ plywood: two sides, a toe kick, a fixed bottom and top, two adjustable shelves and a ¼″ back.',
  cam:orbit([15,6,20],-30,18,90)});

step({key:'left-side',title:'Stand up the left side',sheet:'A-1',
  text:'Clamp a square to it so it stands plumb. The shelf pin holes face in.',
  cam:orbit([10,6,18],-35,20,75)});
mv('SL',drop(8));

step({key:'kick-bottom',title:'Glue in the toe kick and the bottom',sheet:'A-1',
  text:'The kick sits 1″ back from the front edge. The bottom rests on it, flush with the front.',
  cam:orbit([15,6,6],-30,25,70)});
mv('KK',slide(0,-20,0));
mv('BT',slide(0,-24,0),{delay:0.5});

step({key:'right-side',title:'Close up with the right side',sheet:'A-1',
  text:'Slide it in against the kick and bottom, then screw through both sides.',
  cam:orbit([20,6,16],30,20,80)});
mv('SR',slide(18,0,0));

step({key:'top',title:'Set the top on',sheet:'A-2',
  text:'The top overhangs nothing: it sits on the sides, flush all round.',
  cam:orbit([15,6,30],-25,30,80)});
mv('TP',drop(10));

step({key:'back',title:'Nail on the back',sheet:'A-2',
  text:'Square the case by its diagonals before the back goes on; the back holds it square from then on.',
  cam:orbit([15,6,20],155,20,85)});
mv('BK',slide(0,14,0));

step({key:'shelves',title:'Push in the pins and slide in the shelves',sheet:'A-3',
  text:'Four pins per shelf at the same height. The shelves are 1/16″ short each side so they drop in easily.',
  cam:orbit([15,4,18],-20,15,75)});
SHELF_Z.forEach((z,s)=>{
  ['0','1'].forEach(side=>['0','1'].forEach(k=>mv('PN'+s+side+k,slide(side==='0'?3:-3,0,0),{delay:s*1.4})));
  mv('SH'+s,slide(0,-18,0),{delay:s*1.4+0.7});
});

root.PLAN=K.finish({meta:{
  title:'Plywood Bookcase',
  eyebrow:'Step-by-step build',
  thing:'bookcase',
  about:[['Overall','30″ W × 11½″ D × 36¾″ H'],['Stock','¾″ plywood, ¼″ back']],
  links:[],
  sheetLabel:'Sheet'
}});
})(typeof window!=='undefined'?window:globalThis);
