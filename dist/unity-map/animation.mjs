import * as THREE from '../assets/three.module.js';

export function blenderClips(definitions=[]){
 return definitions.map(spec=>{
  const tracks=[];
  for(const track of spec.Tracks){
   const node=track.Path.split('/').at(-1),times=track.Keys.map(k=>k.Time);
   tracks.push(new THREE.VectorKeyframeTrack(node+'.position',times,track.Keys.flatMap(k=>[k.Position[0],k.Position[1],-k.Position[2]])));
   tracks.push(new THREE.QuaternionKeyframeTrack(node+'.quaternion',times,track.Keys.flatMap(k=>[-k.Rotation[0],-k.Rotation[1],k.Rotation[2],k.Rotation[3]])));
   tracks.push(new THREE.VectorKeyframeTrack(node+'.scale',times,track.Keys.flatMap(k=>k.Scale)));
  }
  const clip=new THREE.AnimationClip(spec.Name,spec.Duration,tracks);clip.userData={loop:spec.Loop};return clip;
 });
}

export function attachAnimation(root,clips){
 if(!clips?.length)return null;
 const mixer=new THREE.AnimationMixer(root),actions=new Map();
 for(const clip of clips){const action=mixer.clipAction(clip);action.setLoop(clip.userData.loop?THREE.LoopRepeat:THREE.LoopOnce,clip.userData.loop?Infinity:1);action.clampWhenFinished=true;actions.set(clip.name,action);}
 let playing=null;
 return {mixer,play(name,restart=false){const action=actions.get(name);if(!action||name===playing&&!restart)return;const old=actions.get(playing);if(!playing||name==='Spawn'){if(old)old.stop();action.reset().stopFading().setEffectiveWeight(1).play();mixer.update(0);}else{action.reset().fadeIn(.12).play();if(old&&old!==action)old.fadeOut(.12);}playing=name;},update(dt){mixer.update(dt);}};
}
