import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from './dist/assets/three.module.js';
import {blenderClips,attachAnimation} from './dist/unity-map/animation.mjs';
const source='/workspace/work/shattered-world-moba/Assets/ShatteredWorld/Art/Source';
const manifest=JSON.parse(fs.readFileSync(`${source}/ArtManifest.json`,'utf8'));let count=0;
for(const model of manifest.Models){
 const name=model.Name;if(!JSON.parse(fs.readFileSync(`${source}/${model.File}`,'utf8')).Clips)continue;
 const data=JSON.parse(fs.readFileSync(`${source}/${name}.meshdata.json`,'utf8')),clips=blenderClips(data.Clips);
 for(const spec of data.Clips){count++;
  const root=new THREE.Group(),visual=new THREE.Group();visual.name='Visual';root.add(visual);
  for(const chunk of data.Chunks){const part=new THREE.Object3D();part.name=chunk.Name;part.position.set(chunk.Position[0],chunk.Position[1],-chunk.Position[2]);visual.add(part);}
  const animator=attachAnimation(root,clips);animator.play(spec.Name);const keyIndex=Math.floor(spec.Tracks[0].Keys.length/2),time=spec.Tracks[0].Keys[keyIndex].Time;animator.mixer.setTime(time);
  for(const track of spec.Tracks){const key=track.Keys[keyIndex],part=root.getObjectByName(track.Path.split('/').at(-1));assert.ok(part,track.Path);const position=new THREE.Vector3(key.Position[0],key.Position[1],-key.Position[2]),rotation=new THREE.Quaternion(-key.Rotation[0],-key.Rotation[1],key.Rotation[2],key.Rotation[3]).normalize();assert.ok(part.position.distanceTo(position)<1e-4,`${name} ${spec.Name} position`);assert.ok(part.quaternion.angleTo(rotation)<1e-3,`${name} ${spec.Name} quaternion`);assert.ok(part.scale.distanceTo(new THREE.Vector3(...key.Scale))<1e-4,`${name} ${spec.Name} scale`);}
  if(spec.Name==='Spawn'){animator.play('Spawn',true);assert.ok(visual.scale.x<.03,'spawn must start at authored small scale');}
 }
 console.log('PASS Three.js mixer/native Blender keys',name,data.Clips.length+' clips');
}
assert.equal(count,100);console.log('PASS 100 Blender clips');
console.log('ANIMATION CPU CHECK COMPLETE; this is not a WebGL/browser test.');
