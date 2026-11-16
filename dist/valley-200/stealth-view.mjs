// Per-hero material instances prevent one concealed ally changing the whole team.
export class HeroVisibilityView{
 constructor(state,actors,{team='Light'}={}){this.state=state;this.team=team;this.roots=new Map();this.materials=new Map();for(const a of actors.values())if(a.motion==='hero'){this.roots.set(a.owner,a.go);const entries=[];a.go.traverse(o=>{if(!o.isMesh)return;const original=o.material,mat=original.clone();mat.onBeforeCompile=original.onBeforeCompile;mat.customProgramCacheKey=original.customProgramCacheKey;o.material=mat;entries.push({mat,opacity:mat.opacity,transparent:mat.transparent,depthWrite:mat.depthWrite});});this.materials.set(a.owner,entries);}}
 status(hero){return this.state.stealth.renderState(hero,this.team);}
 visible(hero){return this.status(hero).visible;}
 apply(){for(const h of this.state.heroes){const go=this.roots.get(h.id);if(!go)continue;const status=this.status(h);go.visible=status.visible;for(const entry of this.materials.get(h.id)){const {mat}=entry,transparent=entry.transparent||status.opacity<1,depthWrite=entry.depthWrite&&status.opacity===1;if(mat.transparent!==transparent||mat.depthWrite!==depthWrite){mat.transparent=transparent;mat.depthWrite=depthWrite;mat.needsUpdate=true;}mat.opacity=entry.opacity*status.opacity;}}}
}
