// Stealth is a shared simulation rule, not a rendering-only effect.
export function bushDistance(point,bush){const dx=point.x-bush.position.x,dz=point.z-bush.position.z,c=bush.cos??Math.cos(bush.angle??0),s=bush.sin??Math.sin(bush.angle??0),along=dx*c+dz*s,across=-dx*s+dz*c;return Math.hypot(Math.max(0,Math.abs(along)-(bush.halfLength??0)),across);}
export class StealthBush{
 constructor({id,position,radius=3.2,half_length=0,angle=0}){this.id=id;this.position={x:position.X??position.x??position[0],y:0,z:position.Z??position.z??-(position.Y??position[1])};this.radius=radius;this.halfLength=half_length;this.angle=angle;this.cos=Math.cos(angle);this.sin=Math.sin(angle);this.occupants=new Set();}
 containsPoint(point,padding=0){return bushDistance(point,this)<=this.radius+padding;}
 contains(hero){return hero.alive&&this.containsPoint(hero.position);}
}
export class StealthSystem{
 constructor(specs=[],heroes=[],{actionRevealSeconds=2}={}){this.bushes=specs.map(s=>new StealthBush(s));this.heroes=new Map(heroes.map(h=>[h.id,h]));this.revealedUntil=new Map();this.membership=new Map();this.time=0;this.actionRevealSeconds=actionRevealSeconds;this.update(heroes,0);}
 update(heroes,time){this.time=time;this.heroes=new Map(heroes.map(h=>[h.id,h]));this.membership.clear();for(const b of this.bushes){b.occupants.clear();for(const h of heroes)if(b.contains(h)){b.occupants.add(h.id);const set=this.membership.get(h.id)??new Set();set.add(b.id);this.membership.set(h.id,set);}}}
 reveal(hero,time=this.time){const id=typeof hero==='number'?hero:hero.id;if(!this.heroes.has(id))return false;this.revealedUntil.set(id,Math.max(this.revealedUntil.get(id)??0,time+this.actionRevealSeconds));return true;}
 notifyDamageDealt(hero,time=this.time){return this.reveal(hero,time);}
 notifyAbilityUsed(hero,time=this.time){return this.reveal(hero,time);}
 sharesWithEnemy(hero){for(const id of this.membership.get(hero.id)??[]) {const b=this.bushes.find(b=>b.id===id);for(const occupant of b.occupants){const other=this.heroes.get(occupant);if(other?.alive&&other.team!==hero.team)return true;}}return false;}
 concealed(hero){return !!hero?.alive&&(this.membership.get(hero.id)?.size??0)>0&&(this.revealedUntil.get(hero.id)??-1)<=this.time+1e-8&&!this.sharesWithEnemy(hero);}
 canSee(observer,target){if(!target?.alive)return false;const team=typeof observer==='string'?observer:observer?.team;if(team===target.team)return true;return !this.heroes.has(target.id)||!this.concealed(target);}
 renderState(hero,team){const hidden=this.concealed(hero),ally=hero.team===team;return {visible:hero.alive&&(!hidden||ally),opacity:hidden&&ally ? .45 : 1,concealed:hidden,bushIDs:[...(this.membership.get(hero.id)??[])]};}
}
