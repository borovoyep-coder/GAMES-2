// Planar map simulation. Every logical hero/projectile is (x, 0, z); render elevation is separate.
import {MapState} from './model.mjs?v=200.4';
export const RULES=Object.freeze({hz:30,heroRadius:.6,heroSpeed:8,heroHealth:1200,heroMana:500,fountainRadius:6.6,healHP:300,healMana:180,bridgeStart:120,bridgePeriod:120,bridgeWarning:15,ejectDuration:.65,crystalHP:24,meleeCrystalDamage:4,rangedCrystalDamage:3,crystalRespawn:60,meleeRange:3.2,rangedRange:9,attackPeriod:.55,projectileSpeed:22});
const SQRT2=Math.SQRT2,EPS=1e-7;
export const xy=p=>({x:p.X??p[0],y:0,z:-(p.Y??p[1])});
export const dist=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
const lerp=(a,b,t)=>({x:a.x+(b.x-a.x)*t,y:0,z:a.z+(b.z-a.z)*t});
function segmentDistance(p,a,b){const dx=b.x-a.x,dz=b.z-a.z,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.z-a.z)*dz)/(dx*dx+dz*dz||1)));return Math.hypot(p.x-a.x-dx*t,p.z-a.z-dz*t);}
function routeDistance(p,points){let d=Infinity;for(let i=1;i<points.length;i++)d=Math.min(d,segmentDistance(p,points[i-1],points[i]));return d;}
export function bridgePhase(time){if(time<120-EPS)return {active:-1,next:120,warning:false,remaining:120-time};const cycle=Math.floor((time-120+EPS)/120),next=240+cycle*120;return {active:cycle%2,next,warning:time>=next-15-EPS,remaining:Math.max(0,next-time)};}
export function bridgeLocal(p,bridge){const dx=p.x-bridge.x,dz=p.z-bridge.z;return {along:(dx-dz)/SQRT2,across:(dx+dz)/SQRT2};}
class Heap{constructor(){this.data=[];}push(value){let i=this.data.length;this.data.push(value);while(i){const p=(i-1)>>1;if(this.data[p].f<=value.f)break;this.data[i]=this.data[p];i=p;this.data[i]=value;}}pop(){const first=this.data[0],end=this.data.pop();if(this.data.length){this.data[0]=end;let i=0;for(;;){let j=i*2+1;if(j>=this.data.length)break;if(j+1<this.data.length&&this.data[j+1].f<this.data[j].f)j++;if(this.data[i].f<=this.data[j].f)break;[this.data[i],this.data[j]]=[this.data[j],this.data[i]];i=j;}}return first;}get size(){return this.data.length;}}
export class PlanarNavigation{
 constructor(layout,entities,state){this.layout=layout;this.entities=entities;this.state=state;this.step=1;this.min=-114;this.count=229;this.revision=0;
  this.lanes=Object.values(layout.lanes).map(r=>r.map(xy));this.arenas=Object.values(layout.bosses).map(xy);this.bases=Object.values(layout.bases).map(xy);this.fountains=Object.values(layout.fountains).map(xy);this.camps=layout.camps.map(c=>xy(c.position));this.clearings=Object.values(layout.clearings).map(xy);
  this.paths=layout.forest_paths.map(r=>({points:r.map(xy),half:1.75}));this.paths.push(...layout.tower_passages.map(r=>({points:r.points.map(xy),half:1.8})),...layout.boss_approaches.map(r=>({points:r.points.map(xy),half:4})),...layout.crystals.map(c=>({points:c.short_path.map(xy),half:1.75})));
  for(const team of ['Light','Dark'])this.paths.push({points:[xy(layout.bases[team]),xy(layout.fountains[team])],half:3});
  this.river=layout.river.map(xy);this.riverHalf=layout.river_half_width;this.bridges=layout.energy_bridges.map(b=>xy(b.position));this.stone=layout.stone_bridges.map(b=>xy(b.position));this.towers=entities.filter(e=>e.category==='tower').map(e=>({...xy(e.position),id:e.id}));
  this.gates=entities.filter(e=>e.category==='crystal_gate').map(e=>({id:e.id,p:xy(e.position)}));this.trees=layout.trees.map(xy);this.rects=(layout.colliders??[]).map(r=>({minX:r.min[0],maxX:r.max[0],minZ:-r.max[1],maxZ:-r.min[1]}));
  this.mask=new Uint8Array(this.count*this.count);this.riverMask=new Uint8Array(this.mask.length);for(let z=0;z<this.count;z++)for(let x=0;x<this.count;x++){const p=this.point(z*this.count+x);this.mask[z*this.count+x]=this.staticWalkable(p)?1:0;this.riverMask[z*this.count+x]=this.isRiver(p)?1:0;}
 }
 point(i){return {x:this.min+(i%this.count)*this.step,y:0,z:this.min+Math.floor(i/this.count)*this.step};}
 index(p){const x=Math.round((p.x-this.min)/this.step),z=Math.round((p.z-this.min)/this.step);return x<0||z<0||x>=this.count||z>=this.count?-1:z*this.count+x;}
 inArena(p){return this.arenas.some(a=>dist(p,a)<=14.6);}
 onStone(p){return this.stone.some(b=>{const q=bridgeLocal(p,b);return Math.abs(q.along)<=10.6&&Math.abs(q.across)<=4.0;});}
 onBridge(p,index,padding=0){const q=bridgeLocal(p,this.bridges[index]);return Math.abs(q.along)<=11.5+padding&&Math.abs(q.across)<=2.2+padding;}
 isRiver(p){return !this.inArena(p)&&routeDistance(p,this.river)<this.riverHalf+RULES.heroRadius;}
 staticWalkable(p){const r=RULES.heroRadius;
  const inside=this.inArena(p)||this.bases.some(q=>dist(p,q)<=15.1-r)||this.fountains.some(q=>dist(p,q)<=7-r)||this.clearings.some(q=>dist(p,q)<=10.6-r)||this.camps.some(q=>dist(p,q)<=5.45-r)||this.lanes.some(q=>routeDistance(p,q)<=5.2-r)||this.paths.some(q=>routeDistance(p,q.points)<=q.half-r)||this.bridges.some((_,i)=>this.onBridge(p,i))||this.onStone(p);
  if(!inside)return false;
  if(this.towers.some(q=>(!this.state.structures||this.state.structures.get(q.id)?.alive!==false)&&dist(p,q)<2.65+r)||this.bases.some(q=>dist(p,q)<3.1+r))return false;
  if(this.trees.some(q=>dist(p,q)<.35+r))return false;
  if(this.rects.some(q=>p.x>q.minX-r&&p.x<q.maxX+r&&p.z>q.minZ-r&&p.z<q.maxZ+r))return false;
  return true;
 }
 dynamicWalkable(p,isRiver=this.isRiver(p)){
  if(isRiver&&!this.onStone(p)){const active=this.state.bridge.active;if(active<0||!this.onBridge(p,active))return false;}
  if(this.gates.some(g=>this.state.crystals.get(g.id)?.hp>0&&dist(p,g.p)<2.25+RULES.heroRadius))return false;
  return true;
 }
 walkable(p){return Number.isFinite(p.x)&&Number.isFinite(p.z)&&this.staticWalkable(p)&&this.dynamicWalkable(p);}
 gridOK(i){return i>=0&&i<this.mask.length&&this.mask[i]&&this.dynamicWalkable(this.point(i),!!this.riverMask[i]);}
 nearest(p,radius=4){if(this.walkable(p))return {...p,y:0};let best=null,error=Infinity;for(let dz=-radius;dz<=radius;dz++)for(let dx=-radius;dx<=radius;dx++){const q={x:Math.round(p.x)+dx,y:0,z:Math.round(p.z)+dz},d=dist(p,q);if(d<error&&this.walkable(q)){best=q;error=d;}}return best;}
 segmentClear(a,b){const n=Math.max(1,Math.ceil(dist(a,b)/.4));for(let i=0;i<=n;i++)if(!this.walkable(lerp(a,b,i/n)))return false;return true;}
 find(start,goal){const a=this.nearest(start,3),b=this.nearest(goal,3);if(!a||!b)return null;if(this.segmentClear(a,b))return [b];const si=this.index(a),gi=this.index(b);if(si<0||gi<0||!this.gridOK(si)||!this.gridOK(gi))return null;
  const open=new Heap(),cost=new Float64Array(this.mask.length),parent=new Int32Array(this.mask.length),seen=new Uint8Array(this.mask.length);cost.fill(Infinity);parent.fill(-1);cost[si]=0;open.push({id:si,f:dist(a,b)});const offsets=[[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[1,-1],[-1,1],[1,1]];
  while(open.size){const cur=open.pop().id;if(seen[cur])continue;seen[cur]=1;if(cur===gi){const raw=[];let i=gi;while(i!==si){raw.push(this.point(i));i=parent[i];if(i<0)return null;}raw.reverse();raw.push(b);const result=[];let anchor=a,j=0;while(j<raw.length){let k=j;while(k+1<raw.length&&this.segmentClear(anchor,raw[k+1]))k++;result.push(raw[k]);anchor=raw[k];j=k+1;}return result;}
   const x=cur%this.count,z=Math.floor(cur/this.count);for(const [dx,dz]of offsets){const nx=x+dx,nz=z+dz;if(nx<0||nz<0||nx>=this.count||nz>=this.count)continue;const n=nz*this.count+nx;if(seen[n]||!this.gridOK(n))continue;if(dx&&dz&&(!this.gridOK(z*this.count+nx)||!this.gridOK(nz*this.count+x)))continue;const g=cost[cur]+(dx&&dz?SQRT2:1);if(g<cost[n]){cost[n]=g;parent[n]=cur;open.push({id:n,f:g+dist(this.point(n),b)});}}
  }return null;
 }
}
export class PlanarWorld extends MapState{
 constructor(manifest,layout,{bots=true}={}){super(manifest.entities);this.manifest=manifest;this.layout=layout;this.entities=new Map(manifest.entities.map(e=>[e.id,e]));this.tickNumber=0;this.accumulator=0;this.bridge=bridgePhase(0);this.events=[];this.projectiles=[];this.nextProjectile=1;this.botsEnabled=bots;this.heroes=[];this.heroById=new Map();
  this.fountains=manifest.entities.filter(e=>e.category==='fountain').map(e=>({id:e.id,team:e.properties.team,position:xy(e.position),radius:RULES.fountainRadius}));
  for(const e of manifest.entities.filter(e=>e.category==='hero')){const h={id:e.id,team:e.properties.team,index:e.properties.hero_index,position:xy(e.position),spawn:xy(e.position),health:RULES.heroHealth,mana:RULES.heroMana,maxHealth:RULES.heroHealth,maxMana:RULES.heroMana,alive:true,path:[],pathRevision:0,goal:null,ejection:null,nextAttack:0,nextThink:10+e.properties.hero_index*1.4,patrolOut:false,moving:false,heading:0};this.heroes.push(h);this.heroById.set(h.id,h);if(e.properties.controllable)this.player=h;}
  this.nav=new PlanarNavigation(layout,manifest.entities,this);if(!this.player)throw new Error('Map needs one controllable hero');
 }
 emit(kind,text,data={}){this.events.push({kind,text,time:this.time,...data});}
 tick(dt){if(!Number.isFinite(dt)||dt<0)return;this.accumulator+=dt;const steps=Math.floor((this.accumulator+EPS)*RULES.hz);this.accumulator-=steps/RULES.hz;for(let i=0;i<steps;i++)this.step();}
 advanceTo(seconds){const target=Math.max(this.tickNumber,Math.round(seconds*RULES.hz));while(this.tickNumber<target)this.step();this.accumulator=0;}
 issue(command){const h=this.heroById.get(command.hero??this.player.id);if(!h||!h.alive)return {ok:false,reason:'Герой возрождается'};if(h.ejection)return {ok:false,reason:'Герой безопасно покидает закрывающийся мост'};
  if(command.type==='move'){const p={x:command.point.x,y:0,z:command.point.z};if(!this.nav.walkable(p))return {ok:false,reason:'Здесь нет доступного прохода'};const path=this.nav.find(h.position,p);if(!path)return {ok:false,reason:'Путь закрыт рекой или кристаллом'};h.path=path;h.goal=p;h.pathRevision=this.nav.revision;return {ok:true};}
  if(command.type==='crystal_attack')return this.attackCrystal(h,command.target,command.ranged?'ranged':'melee');
  if(command.type==='hero_attack')return this.attackHero(h,command.target);
  return {ok:false,reason:'Неизвестная команда'};
 }
 attackCrystal(h,id,kind='melee'){const c=this.crystals.get(id),e=this.entities.get(id);if(!c||c.hp===0)return {ok:false,reason:'Затвор уже разрушен'};if(this.time+EPS<h.nextAttack)return {ok:false,reason:'Атака восстанавливается'};const target=xy(e.position),range=kind==='ranged'?RULES.rangedRange:RULES.meleeRange;if(dist(h.position,target)>range+2.25)return {ok:false,reason:'Подойдите к кристаллу'};h.nextAttack=this.time+RULES.attackPeriod;
  if(kind==='ranged')this.projectiles.push({id:this.nextProjectile++,source:h.id,target:id,targetKind:'crystal',position:{...h.position,y:0},damage:RULES.rangedCrystalDamage,speed:RULES.projectileSpeed,team:h.team});else this.damageGate(id,RULES.meleeCrystalDamage);return {ok:true};
 }
 damageGate(id,damage){const c=this.crystals.get(id);if(!c||c.hp===0)return;super.hit(id,damage);if(c.hp===0){this.nav.revision++;this.emit('crystal','Кристальный проход открыт',{entity:id});}}
 attackHero(h,targetID){const target=this.heroById.get(targetID);if(!target||!target.alive||target.team===h.team)return {ok:false,reason:'Выберите вражеского героя'};if(this.time<h.nextAttack||h.mana<25)return {ok:false,reason:'Недостаточно маны или атака восстанавливается'};if(dist(h.position,target.position)>14)return {ok:false,reason:'Противник слишком далеко'};h.mana-=25;h.nextAttack=this.time+.7;this.projectiles.push({id:this.nextProjectile++,source:h.id,target:target.id,targetKind:'hero',position:{...h.position,y:0},damage:95,speed:24,team:h.team});return {ok:true};}
 restore(id){const c=this.crystals.get(id),e=this.entities.get(id);if(!c||!e)return false;const p=xy(e.position);if(this.heroes.some(h=>h.alive&&dist(h.position,p)<3.1))return false;const result=super.restore(id);if(result){this.nav.revision++;this.emit('crystal_restore','Кристальный затвор восстановлен',{entity:id});}return result;}
 woundPlayer(){const h=this.player;h.health=Math.max(1,h.health-650);h.mana=Math.max(0,h.mana-300);}
 step(){this.tickNumber++;this.time=this.tickNumber/RULES.hz;const dt=1/RULES.hz,previous=this.bridge,phase=bridgePhase(this.time);this.bridge=phase;
  if(previous.active!==phase.active){this.nav.revision++;if(previous.active>=0)for(const h of this.heroes)if(h.alive&&this.nav.onBridge(h.position,previous.active,.55))this.eject(h,previous.active);this.emit('bridge',phase.active===0?'Открыт Мост Рассвета':'Открыт Мост Сумерек',{active:phase.active});}
  if(phase.warning&&!previous.warning)this.emit('bridge_warning','Мост закроется через 15 секунд',{active:phase.active});
  for(const h of this.heroes){h.moving=false;if(!h.alive){if(this.time>=h.respawnAt){h.alive=true;h.health=h.maxHealth;h.mana=h.maxMana;h.position={...h.spawn,y:0};}continue;}
   if(h.ejection){const e=h.ejection,t=Math.min(1,(this.time-e.start)/RULES.ejectDuration),f=t*t*(3-2*t);h.position=lerp(e.from,e.to,f);h.moving=true;if(t>=1){h.ejection=null;h.path=[];h.goal=null;}}
   else{if(h.path.length&&h.pathRevision!==this.nav.revision){h.path=h.goal?(this.nav.find(h.position,h.goal)??[]):[];h.pathRevision=this.nav.revision;}
    let budget=RULES.heroSpeed*dt;while(h.path.length&&budget>0){const p=h.path[0],d=dist(h.position,p);if(d<.025){h.path.shift();continue;}const used=Math.min(budget,d),next=lerp(h.position,p,used/d);if(!this.nav.walkable(next)){h.path=[];break;}h.heading=Math.atan2(next.x-h.position.x,-(next.z-h.position.z));h.position=next;h.moving=true;budget-=used;if(used>=d-EPS)h.path.shift();else break;}
    if(this.botsEnabled&&h!==this.player&&this.time>=h.nextThink&&!h.path.length){this.patrol(h);h.nextThink=this.time+5;}}
   h.position.y=0;
   for(const f of this.fountains)if(f.team===h.team&&dist(h.position,f.position)<=f.radius){h.health=Math.min(h.maxHealth,h.health+RULES.healHP*dt);h.mana=Math.min(h.maxMana,h.mana+RULES.healMana*dt);}
  }
  for(let i=this.projectiles.length-1;i>=0;i--){const p=this.projectiles[i],target=p.targetKind==='hero'?this.heroById.get(p.target):null,e=this.entities.get(p.target),point=target?.position??(e?xy(e.position):null);if(!point||target&&!target.alive){this.projectiles.splice(i,1);continue;}const d=dist(p.position,point);if(d<=p.speed*dt+.1){if(p.targetKind==='crystal')this.damageGate(p.target,p.damage);else{target.health=Math.max(0,target.health-p.damage);this.onHeroDamaged?.(p.source,target);if(target.health===0){target.alive=false;target.respawnAt=this.time+12;target.path=[];target.ejection=null;}}this.projectiles.splice(i,1);}else p.position=lerp(p.position,point,p.speed*dt/d);p.position.y=0;}
  for(const [id,c]of this.crystals)if(c.hp===0&&this.time-c.brokenAt>=RULES.crystalRespawn-EPS)this.restore(id);
 }
 eject(hero,index){const b=this.nav.bridges[index],axis={x:1/SQRT2,z:-1/SQRT2},choices=[];for(const side of [-1,1]){const p={x:b.x+axis.x*side*12.6,y:0,z:b.z+axis.z*side*12.6},safe=this.nav.nearest(p,5);if(safe&&!this.nav.isRiver(safe))choices.push(safe);}if(!choices.length)throw new Error('No safe bank for bridge '+index);choices.sort((a,b)=>dist(a,hero.position)-dist(b,hero.position)||dist(a,hero.spawn)-dist(b,hero.spawn));hero.ejection={from:{...hero.position,y:0},to:choices[0],start:this.time};hero.path=[];hero.goal=null;this.emit('eject','Герой безопасно вытолкнут на берег',{hero:hero.id,bridge:index});}
 patrol(h){const light=h.team==='Light',goals=light?[{x:-65,z:-25},{x:-22,z:22},{x:25,z:65},{x:-55,z:25}]:[{x:25,z:-65},{x:22,z:-22},{x:65,z:25},{x:55,z:25}];const goal=h.patrolOut?h.spawn:goals[(h.index-1+4)%4],safe=this.nav.nearest(goal,4);if(safe){const result=this.issue({type:'move',hero:h.id,point:safe});if(result.ok)h.patrolOut=!h.patrolOut;}}
 testBridgeClosure(){let t=this.time;if(t<120)this.advanceTo(120);const next=this.bridge.next;this.advanceTo(next-3);const index=this.bridge.active;this.player.position={...this.nav.bridges[index],y:0};this.player.path=[];this.player.goal=null;this.player.health=Math.max(1,this.player.health);return index;}
 reset(){for(const c of this.crystals.values()){c.hp=24;c.brokenAt=null;c.restoredAt=-1000;}this.tickNumber=0;this.time=0;this.accumulator=0;this.bridge=bridgePhase(0);this.projectiles=[];this.events=[];this.nav.revision++;for(const h of this.heroes)Object.assign(h,{position:{...h.spawn,y:0},health:h.maxHealth,mana:h.maxMana,alive:true,path:[],goal:null,ejection:null,nextAttack:0,nextThink:10+h.index*1.4,patrolOut:false,moving:false});}
 renderHeight(p){for(const a of this.nav.arenas){const d=dist(p,a);if(d<15.8)return .70;}for(const f of this.fountains)if(dist(p,f.position)<7)return .66;for(const b of this.nav.stone){const q=bridgeLocal(p,b);if(Math.abs(q.along)<9.25&&Math.abs(q.across)<4.7)return .24+1.5*Math.max(0,1-(q.along/9.25)**2);}if(this.bridge.active>=0&&this.nav.onBridge(p,this.bridge.active))return .22+.5*Math.max(0,1-(bridgeLocal(p,this.nav.bridges[this.bridge.active]).along/11)**2);return .30;}
}
