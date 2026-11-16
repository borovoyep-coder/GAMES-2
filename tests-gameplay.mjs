import fs from 'node:fs';import assert from 'node:assert/strict';
import {PlanarWorld,bridgePhase,bridgeLocal,RULES,xy,dist} from './dist/valley-200/gameplay.mjs';
const dir='dist/valley-200/',manifest=JSON.parse(fs.readFileSync(dir+'scene.json')),layout=JSON.parse(fs.readFileSync(dir+'layout.json'));
const w=new PlanarWorld(manifest,layout,{bots:false}),eq=(a,b)=>assert.ok(Math.abs(a-b)<1e-6,`${a} != ${b}`),gates=manifest.entities.filter(e=>e.category==='crystal_gate');
for(const [t,active,warning]of [[0,-1,false],[119.999,-1,false],[120,0,false],[224.999,0,false],[225,0,true],[239.999,0,true],[240,1,false],[345,1,true],[360,0,false],[465,0,true],[480,1,false]]){const b=bridgePhase(t);assert.equal(b.active,active);assert.equal(b.warning,warning);}
assert.equal(w.heroes.length,10);assert.equal(w.heroes.filter(h=>h.team==='Light').length,5);assert.equal(w.heroes.filter(h=>h.team==='Dark').length,5);assert.equal(w.bridge.active,-1);
console.log('PASS exact bridge schedule: closed 0–120, Dawn 120–240, Dusk 240–360, alternating; warning at 15 seconds');
// Physical movement and geometry masks: conservative state closes every gate and both forest crossings.
for(const points of w.nav.lanes){const start=w.nav.nearest(points[0],5),end=w.nav.nearest(points.at(-1),5);assert.ok(w.nav.find(start,end),'Permanent lane disconnected');}
for(const r of layout.boss_approaches){const a=xy(r.points[0]),b=xy(r.points.at(-1));assert.ok(w.nav.find(a,b),'Boss entrance disconnected');assert.ok(w.nav.find(w.player.spawn,b),'Boss not reachable from a base');}
assert.equal(layout.boss_approaches.length,4);assert.equal(layout.tower_passages.length,18);
for(const r of layout.tower_passages){const a=xy(r.points[0]),b=xy(r.points.at(-1));assert.ok(w.nav.walkable(a),'Tower passage starts in an obstacle');assert.ok(w.nav.walkable(b),'Tower passage ends in water');assert.ok(w.nav.find(a,b),'Tower passage disconnected');}
for(const p of w.nav.bridges)assert.equal(w.nav.walkable(p),false,'Closed bridge must block movement');
for(const p of w.nav.stone)assert.ok(w.nav.walkable(p),'Stone bridge must remain open');
assert.equal(w.issue({type:'move',point:{x:-40,y:17,z:-40}}).ok,false,'Unbridged river must block');
let moved=w.issue({type:'move',point:w.nav.nearest({x:-65,y:9,z:30},4)});assert.ok(moved.ok);for(let i=0;i<1200;i++){w.tick(1/30);for(const h of w.heroes)assert.equal(h.position.y,0);}assert.ok(w.player.position.x>-70,'Hero did not leave fountain');
console.log('PASS flat movement, collision masks, three permanent lanes, 18 tower paths and four boss entrances with all optional routes closed');
// Exact normal-attack damage, cooldown and delayed projectile impact; no arbitrary damage input.
for(const side of ['Light','Dark']){const same=layout.crystals.filter(c=>c.side===side);assert.equal(same.length,4);assert.equal(new Set(same.map(c=>c.role)).size,4);}
for(const [i,e]of gates.entries()){
 w.reset();const c=layout.crystals.find(c=>c.id===e.properties.gate_index),a=xy(c.short_path[0]),b=xy(c.short_path.at(-1));assert.equal(w.nav.segmentClear(a,b),false,'Intact gate does not close shortcut');const p=xy(e.position),near=w.nav.nearest({x:a.x+(p.x-a.x)*.45,y:0,z:a.z+(p.z-a.z)*.45},4);assert.ok(near);w.player.position=near;
 assert.equal(w.issue({type:'crystal_attack',target:e.id,damage:999,critical:true,spell:true}).ok,true);assert.equal(w.crystals.get(e.id).hp,20,'Injected crit/spell damage accepted');assert.equal(w.issue({type:'crystal_attack',target:e.id}).ok,false,'Cooldown ignored');
 for(let hit=1;hit<6;hit++){w.tick(.6);assert.ok(w.issue({type:'crystal_attack',target:e.id}).ok);}assert.equal(w.crystals.get(e.id).hp,0);assert.ok(w.nav.segmentClear(a,b),'Destroyed gate did not open shortcut');
 const broken=w.crystals.get(e.id).brokenAt;w.player.position={...w.player.spawn};w.advanceTo(broken+59.9);assert.equal(w.crystals.get(e.id).hp,0);w.player.position={...p};w.advanceTo(broken+60.1);assert.equal(w.crystals.get(e.id).hp,0,'Respawn must wait for occupied passage');w.player.position={...w.player.spawn};w.tick(.1);assert.equal(w.crystals.get(e.id).hp,24);
}
w.reset();{const e=gates[0],p=xy(e.position);w.player.position={x:p.x+6,y:0,z:p.z};for(let i=0;i<8;i++){const hp=w.crystals.get(e.id).hp;assert.ok(w.issue({type:'crystal_attack',target:e.id,ranged:true}).ok);assert.equal(w.crystals.get(e.id).hp,hp);for(let j=0;j<19;j++){w.tick(1/30);assert.ok(w.projectiles.every(p=>p.position.y===0));}assert.equal(w.crystals.get(e.id).hp,Math.max(0,hp-3));}assert.equal(w.crystals.get(e.id).hp,0);}
console.log('PASS all 8 shortcuts: 24 HP, six melee hits / eight ranged projectiles, cooldown, fixed damage, 60-second regeneration and occupancy delay');
// Trigger is team-specific and clamps regeneration to maxima.
w.reset();const f=w.fountains.find(f=>f.team==='Light'),enemy=w.heroes.find(h=>h.team==='Dark');w.player.position={...f.position};enemy.position={...f.position};w.player.health=100;w.player.mana=0;enemy.health=100;enemy.mana=0;w.tick(1);eq(w.player.health,400);eq(w.player.mana,180);eq(enemy.health,100);eq(enemy.mana,0);w.tick(10);eq(w.player.health,1200);eq(w.player.mana,500);w.player.position={x:f.position.x+7,y:0,z:f.position.z};w.player.health=500;w.tick(1);eq(w.player.health,500);
console.log('PASS allied fountain HP/mana restoration, enemy exclusion, trigger radius and maximum clamping');
// Smooth ejection across both shores, for all ten actors, no damage and no Y drift.
for(let bridge=0;bridge<2;bridge++)for(let side of [-1,1]){w.reset();w.advanceTo(bridge===0?120:240);const b=w.nav.bridges[bridge];for(const h of w.heroes){h.position={x:b.x+side*4/Math.SQRT2,y:0,z:b.z-side*4/Math.SQRT2};h.health=600;h.path=[];}w.advanceTo(w.bridge.next);for(const h of w.heroes){assert.ok(h.ejection);assert.equal(Math.sign(bridgeLocal(h.ejection.to,b).along),side);assert.equal(w.nav.isRiver(h.ejection.to),false);}assert.equal(w.issue({type:'move',point:w.player.spawn}).ok,false);const before={...w.player.position};w.tick(.3);assert.ok(dist(before,w.player.position)>0);assert.ok(w.player.ejection);for(let i=0;i<20;i++){w.tick(1/30);for(const h of w.heroes){eq(h.position.y,0);eq(h.health,600);}}for(const h of w.heroes){assert.equal(h.ejection,null);assert.ok(w.nav.walkable(h.position));}}
console.log('PASS four closure cases: ten heroes, nearest shore, smooth protected ejection, no bridge damage and Y=0 throughout');
w.reset();{const enemy=w.heroes.find(h=>h.team==='Dark');w.player.position={x:-45,y:0,z:10};enemy.position={x:-40,y:0,z:10};assert.ok(w.issue({type:'hero_attack',target:enemy.id}).ok);assert.equal(w.player.mana,475);while(w.projectiles.length){assert.ok(w.projectiles.every(p=>p.position.y===0));w.tick(1/30);}eq(enemy.health,1105);enemy.health=10;w.tick(1);w.issue({type:'hero_attack',target:enemy.id});w.tick(1);assert.equal(enemy.alive,false);w.tick(12);assert.ok(enemy.alive);assert.equal(enemy.position.y,0);}
console.log('PASS planar projectiles, enemy hero damage and respawn at the fountain');
console.log('GAMEPLAY 200.3 CHECKS PASSED; local simulation only, browser/WebGL/network match not executed.');
