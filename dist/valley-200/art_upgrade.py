"""Reference palette, carved assets and painted surfaces for Blender 4.0+."""
import math,random
import bpy
from mathutils import Vector
G={};PI=math.pi
def shader(m):return next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
def tint(ctx,name,dark,light,rough=None,metal=None,emission=None):
 m=ctx.materials[name];r=next(n for n in m.node_tree.nodes if n.type=='VALTORGB');r.color_ramp.elements[0].color=(*G['srgb'](dark),1);r.color_ramp.elements[-1].color=(*G['srgb'](light),1);m.diffuse_color=(*G['srgb'](light),1)
 for k,v in [('Roughness',rough),('Metallic',metal),('Emission Strength',emission)]:
  if v is not None:shader(m).inputs[k].default_value=v
def texture_link(ctx,m,img):
 n=m.node_tree.nodes;l=m.node_tree.links;s=shader(m);tex=n.get('Surface painted detail')
 if tex:tex.image=img;return
 base=next((a.from_socket for a in l if a.to_socket==s.inputs['Base Color']),None);tex=n.new('ShaderNodeTexImage');tex.name='Surface painted detail';tex.image=img;tex.extension='REPEAT';uv=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeMapping');mapping.inputs['Scale'].default_value=(3,3,3);l.new(uv.outputs['UV'],mapping.inputs['Vector']);l.new(mapping.outputs['Vector'],tex.inputs['Vector'])
 if base:
  mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;l.new(base,mix.inputs[1]);l.new(tex.outputs['Color'],mix.inputs[2]);l.new(mix.outputs[0],s.inputs['Base Color'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.24;bump.inputs['Distance'].default_value=.055;l.new(tex.outputs['Color'],bump.inputs['Height']);l.new(bump.outputs['Normal'],s.inputs['Normal'])
def image(name):return bpy.data.images[G['PREFIX']+name]
def painted_textures(ctx):
 import numpy as np
 target=ctx.cfg.output/'textures';target.mkdir(parents=True,exist_ok=True);n=768;y,x=np.mgrid[0:n,0:n]/n;t=2*PI
 noise=np.sin(t*(x*7+y*3))*.35+np.cos(t*(y*11-x*5))*.23+np.sin(t*(x*37-y*23))*.16+np.cos(t*(x*113+y*83))*.09
 veins=np.abs(np.sin(t*(x*3+y+np.sin(t*y*2)*.13+np.sin(t*x*7)*.02)));cracks=np.clip((.043-veins)/.043,0,1);rows=np.floor(y*16);sx=(x*20+rows*.5)%1;sy=y*16%1;scales=np.sqrt(((sx-.5)/.53)**2+((sy-.37)/.76)**2)
 patterns={'painted_stone':np.clip(.94+.12*noise-.30*cracks+.045*np.sin(t*(x*53+y*17)),.53,1.08),'painted_earth':np.clip(.95+.14*noise+.05*np.sin(t*(x*73-y*41)),.69,1.06),'painted_foliage':np.clip(.96+.12*noise+.055*np.sin(t*(x*31+y*13)),.68,1.08),'flowing_water':np.clip(.97+.045*noise+.06*np.sin(t*(y*23+x*2)+np.sin(t*x*5)*1.8),.76,1.08),'creature_scales':np.clip(.96+.12*noise-.23*np.exp(-((scales-.82)/.055)**2)+.08*np.exp(-((scales-.65)/.08)**2),.6,1.08),'embroidered_cloth':np.clip(.97+.055*noise+.035*np.sin(t*x*192)*np.sin(t*y*192)-.1*np.cos(t*x*12)**12,.72,1.06)}
 groups={'painted_stone':{'Stone','Marble','Lane','LaneLight','LaneWarm','StoneDark','CrimsonStone','Obsidian','Gold','Bronze'},'painted_earth':{'Earth','EarthEdge','Grass','Moss'},'painted_foliage':{'Pine','PineDark','PineLight','Bush','BushTip','GrassBlade','Wolf','Fur','FurDark','PurpleHide','BlueHide','Petal'},'flowing_water':{'RiverWater','SkyWater'}}
 for name,value in patterns.items():
  img=bpy.data.images.new(G['PREFIX']+name,width=n,height=n,alpha=True);img.colorspace_settings.name='Non-Color';rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=value[:,:,None];img.pixels.foreach_set(rgba.ravel());img.filepath_raw=str(target/(name+'.png'));img.file_format='PNG';img.save();img.pack()
  for material in groups.get(name,set()):texture_link(ctx,ctx.materials[material],img)
 print('PAINTED TEXTURES: 6 packed tileable 768x768 maps with veins, scales and woven cloth',flush=True)
def materials(ctx):
 G['_art_materials'](ctx)
 for row in [('Lane','846D63','B89B87',.78,.02),('LaneWarm','90766B','C5A48A',.77,.02),('LaneLight','AA9481','DFCAA2',.68,.04),('LaneJoint','433D34','6E6253',.98,0),('Stone','657A71','B8C4A0',.81,.02),('Marble','C8CAB3','FFF0C9',.46,.10),('Gold','BB7A17','FFE078',.30,.72),('Obsidian','090C17','282039',.24,.42),('Wolf','93ABC4','F2F4EF',.78,0),('PurpleHide','482267','AC55C2',.52,.08)]:tint(ctx,*row)
 for row in [('BlueCrystal','0058C2','18CCFF',.17,.24,1.0),('RedCrystal','C2002D','FF3856',.17,.24,1.25),('RiverWater','007EAA','19C5DC',.13,.13,.24),('SkyWater','2CA3D7','84E8FF',.16,.10,.25),('DawnGlow','FFC129','FFF6CA',.20,.15,1.9),('DuskGlow','7021B2','EF52FF',.20,.18,1.75)]:tint(ctx,*row)
def combat_materials(ctx):
 G['_art_combat_materials'](ctx)
 for name in ['BlueArmor','RedArmor','RiftMist']:texture_link(ctx,ctx.materials[name],image('embroidered_cloth'))
 for name in ['ObsidianScale','Emerald','MagmaCore']:texture_link(ctx,ctx.materials[name],image('creature_scales'))
 for row in [('BlueArmor','094AA1','248AF5',.45,.20),('RedArmor','9A1238','F33E62',.45,.20),('ObsidianScale','110B26','63327E',.31,.23),('Emerald','147A49','66D975',.54,.08)]:tint(ctx,*row)
def shield(ctx,name,p,width,height,mat='Gold',depth=.10):
 outline=[(-.42,.50),(.42,.50),(.53,.27),(.42,-.24),(.20,-.45),(0,-.57),(-.20,-.45),(-.42,-.24),(-.53,.27)];n=len(outline);v=[(p[0]+x*width,p[1]+yy,p[2]+z*height) for yy in [depth,-depth] for x,z in outline];v.append((p[0],p[1]-depth*1.8,p[2]+height*.08));f=[tuple(reversed(range(n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]+[(n+i,n+(i+1)%n,2*n) for i in range(n)];return ctx.mesh(name,v,f,mat,bevel=.025)
def scale_plates(ctx,name,centres,mat='Gold',radius=.3):
 v=[];f=[]
 for j,p in enumerate(centres):
  k=len(v);r=radius*(.9+.12*math.sin(j*2.4));v.extend([(p[0]+x*r,p[1]+y*r,p[2]+z*r) for x,y,z in [(-1,0,0),(-.6,-.8,.1),(.6,-.8,.1),(1,0,0),(.55,.9,0),(-.55,.9,0),(0,-.12,.5)]]);f.extend((k+a,k+b,k+6) for a,b in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0)]);f.append(tuple(k+a for a in reversed(range(6))))
 return ctx.mesh(name,v,f,mat,bevel=.014)
def tower(ctx,team,tier,position,lane='Mid'):
 ctx.group('Towers');light=team=='Light';stone='Marble' if light else 'CrimsonStone';glow='BlueCrystal' if light else 'RedCrystal'
 with ctx.root(f'Tower {team} {lane} T{tier}',(*position,.32),'tower',rotation=0 if light else PI) as root:
  root['team']=team;root['tier']=tier;root['lane']=lane;root['health']={1:6500,2:8000,3:10000}[tier];root['minion_damage_reduction']=.20;root['art_revision']='jewel_sanctuary_2009'
  ctx.loft('Tower carved layered circular plinth',[(0,0,0,2.55,2.55),(0,0,.25,2.55,2.55),(0,0,.4,2.32,2.32),(0,0,.68,2.30,2.30),(0,0,.8,1.77,1.77)],stone,32,.045)
  for z,r in [(.28,2.48),(.74,2.05),(1.08,1.33),(2.95,1.43),(3.35,1.55)]:ctx.ring('Tower chased metallic band',(0,0,z),r,.075,'Gold')
  ctx.loft('Tower fluted tapering altar',[(0,0,.78,1.48,1.48),(0,0,1.0,1.36,1.36),(0,0,2.6,1.13,1.13),(0,0,2.98,1.50,1.50),(0,0,3.34,1.55,1.55)],stone,20,.04)
  for j in range(12):
   a=j*2*PI/12;c,s=math.cos(a),math.sin(a);ctx.box('Tower chamfered radial plinth block',(c*2.03,s*2.03,.58),(.72,.48,.43),stone,.055,a+PI/2)
   if j%2==0:ctx.limb('Tower gilded fluted buttress',(c*1.30,s*1.30,1.13),(c*1.13,s*1.13,2.85),.065,.045,'Gold',8);ctx.crystal('Tower cut-in luminous sigil',(c*1.26,s*1.26,1.75),.085,.62,glow)
  with ctx.root('Tower floating focus',(0,0,3.4)) as focus:
   ctx.crystal('Tower floating main crystal',(0,0,.15),.92,3.65,glow)
   for j in range(3):
    a=j*2*PI/3;ctx.crystal('Tower orbiting splinter',(math.cos(a)*1.18,math.sin(a)*1.18,.48),.25,1.65,glow,(0,.16,a))
   focus.driver_add('location',2).driver.expression='3.4+.14*sin(frame*.055)';focus.driver_add('rotation_euler',2).driver.expression='frame*.006'
  for j in range(3):
   a=j*2*PI/3;c,s=math.cos(a),math.sin(a);G['create_swept_body'](ctx,'Tower sculpted golden crystal claw',[(c*1.57,s*1.57,2.85),(c*1.80,s*1.80,3.85),(c*1.46,s*1.46,4.85),(c*.95,s*.95,5.16)],[.22,.18,.12,.012],'Gold',10)
  ctx.ring('Tower spell focusing halo',(0,0,4.65),1.34,.048,glow);ctx.ring('Tower ground protection rune',(0,0,.32),2.20,.035,glow);return root
def wraith(ctx):
 ctx.loft('Wraith layered spectral cloak',[(0,.25,.28,.035,.035),(0,.17,.65,.68,.43),(0,0,1.2,.56,.42),(0,0,1.85,.42,.32)],'RiftMist',24)
 v=[(-.54,-.30,1.85),(-.46,-.53,2.46),(0,-.22,3.04),(.46,-.53,2.46),(.54,-.30,1.85),(-.30,-.48,2.04),(-.26,-.58,2.38),(0,-.39,2.70),(.26,-.58,2.38),(.30,-.48,2.04)];ctx.mesh('Wraith pointed sculpted hollow cowl',v,[(i,i+1,6+i,5+i) for i in range(4)]+[(0,5,9,4)],'PurpleHide',bevel=.025);ctx.sphere('Wraith deep faceless shadow',(0,-.27,2.25),(.32,.16,.39),'Obsidian',2)
 for side in [-1,1]:
  ctx.crystal('Wraith burning slit eye',(side*.14,-.48,2.27),.065,.23,'Amethyst',(0,side*.22,0));shield(ctx,'Wraith broken shoulder armor',(side*.73,-.02,1.94),.56,.65,'ObsidianScale');ctx.curve('Wraith trailing claw arm',[(side*.52,0,1.74),(side*.95,-.1,1.40),(side*1.12,-.33,1.03)],.10,'RiftMist')
  for j in range(3):ctx.limb('Wraith ivory claw',(side*1.12+(j-1)*.08,-.34,1.08),(side*1.10+(j-1)*.12,-.50,.72),.035,.004,'Amethyst',6)
  ctx.crystal('Wraith floating armor shard',(side*.66,.08,.95),.22,.85,'Amethyst',(0,side*.4,0))
 ctx.ring('Wraith levitation aura',(0,0,.35),.88,.035,'Amethyst')
def creature_detail(ctx,kind):
 root=ctx.parent;root['art_revision']='sculpted_2009';root['painted_detail']=True
 if kind=='MoonWolf':
  G['decorate_monster'](ctx,'Wolf')
  for side in [-1,1]:
   for y in [-.77,1.02]:
    for j in range(3):ctx.limb('Moonwolf sculpted ivory claw',(side*.67+(j-1)*.10,y-.35,.15),(side*.67+(j-1)*.11,y-.54,.08),.035,.004,'Ivory',6)
   for j in range(4):ctx.limb('Moonwolf canine fang',(side*.23,-1.87-j*.13,2.08),(side*.23,-1.89-j*.13,1.95),.028,.003,'Ivory',6)
 elif kind in {'MagmaGuardian','AzureGolem','SolarColossus'}:
  glow='MagmaCore' if kind=='MagmaGuardian' else 'BlueCrystal' if kind=='AzureGolem' else 'SunGlow';plate='Bronze' if kind=='MagmaGuardian' else 'BlueHide' if kind=='AzureGolem' else 'Gold';shield(ctx,'Ancient guardian ridged breastplate',(0,-.78,2.85),1.8,1.7,plate,.13);ctx.crystal('Guardian deep radiant chest core',(0,-1.03,2.4),.27,1.20,glow)
  for side in [-1,1]:
   shield(ctx,'Guardian faceted shoulder pauldron',(side*1.40,-.38,3.4),1.13,.95,plate,.18)
   for j in range(3):ctx.curve('Guardian carved luminous fissure',[(side*(.38+j*.18),-.97,2.40),(side*(.50+j*.18),-1.0,2.72),(side*(.35+j*.18),-.98,3.0)],.023,glow)
  if kind=='SolarColossus':
   for j in range(12):
    a=j*2*PI/12;ctx.limb('Colossus solar crown ray',(math.cos(a)*.61,0,4.65+math.sin(a)*.61),(math.cos(a)*1.02,0,4.65+math.sin(a)*1.02),.065,.013,'Gold',8)
 elif kind=='StoneCentipede':scale_plates(ctx,'Centipede overlapping carved scale plates',[(side*.4,(j-3.5)*.6,.94+math.sin(j*.5)*.1) for j in range(8) for side in [-1,1]],'Emerald',.43)
 elif kind=='CrystalCrab':
  scale_plates(ctx,'Crab overlapping sculpted carapace',[(math.cos(j*PI/4)*.8,math.sin(j*PI/4)*.6,1.66) for j in range(8)],'Gold',.45)
  for side in [-1,1]:
   for j in range(4):ctx.crystal('Crab serrated claw tooth',(side*2.12+(j-1.5)*.08,-2.44-j*.11,1.72),.045,.19,'Ivory',(.7,0,0))
 elif kind=='RiftWraith':
  for side in [-1,1]:ctx.curve('Wraith embroidered collar glyph',[(side*.12,-.45,1.88),(side*.32,-.44,1.65),(side*.21,-.46,1.28)],.025,'Amethyst')
 elif kind=='Watcher':
  for j in range(6):
   a=j*PI/3;ctx.crystal('Watcher carved orbit rune',(math.cos(a)*1.16,0,1.6+math.sin(a)*1.16),.075,.30,'Gold',(0,0,a))
 elif kind=='RiftRay':
  for o in list(root.children):
   if 'broad spectral wing' in o.name:bpy.data.objects.remove(o,do_unlink=True)
  for side in [-1,1]:
   v=[];f=[];rows=12;cols=16
   for i in range(rows+1):
    u=i/rows;span=2.65*math.sin(PI*(.10+.79*u))
    for j in range(cols+1):
     t=j/cols;v.append((side*(.35+span*t),-1.05+u*2.2+.20*math.sin(t*PI),1.40+.25*math.sin(t*PI)-.25*t*t+.12*math.sin(u*PI)))
     if i and j:k=i*(cols+1)+j;f.append((k-cols-2,k-cols-1,k,k-1))
   obj=ctx.mesh('Rift ray sculpted curved wing',v,f,'RiftMist',smooth_faces=True);mod=obj.modifiers.new('Real membrane thickness','SOLIDIFY');mod.thickness=.065
 elif kind=='NightLeviathan':
  for side in [-1,1]:
   scale_plates(ctx,'Leviathan overlapping obsidian armor',[(.1+side*(.45+.03*j),-.6-j*.14,2.6+j*.15) for j in range(13)],'ObsidianScale',.27);ctx.curve('Leviathan flared draconic brow',[(.1+side*.35,-2.83,4.34),(.1+side*.72,-2.58,4.46),(.1+side*1.03,-1.96,4.45)],.09,'ObsidianScale')
   for j in range(6):ctx.crystal('Leviathan amethyst cheek scale',(.1+side*.75,-2.55+j*.15,3.84),.09,.32,'Amethyst',(.3,side*.5,0))
def minion(ctx,team,kind):
 root=G['_art_minion'](ctx,team,kind);saved=ctx.parent;ctx.parent=root;root['art_revision']='heraldic_2009';armor='BlueArmor' if team=='Light' else 'RedArmor'
 if kind=='Guard':
  shield(ctx,'Guard sculpted chest cuirass',(0,-.36,1.21),.76,.82,armor);ctx.curve('Guard breastplate golden chevron',[(-.34,-.48,1.46),(0,-.56,1.24),(.34,-.48,1.46)],.028,'Gold')
  for side in [-1,1]:shield(ctx,'Guard layered gilded pauldron',(side*.53,-.04,1.59),.52,.50,'Gold')
  joint=next(o for o in root.children if o.get('minion_part')=='shield');ctx.parent=joint
  for o in list(joint.children):
   if 'enormous tower shield' in o.name or 'embossed shield face' in o.name:bpy.data.objects.remove(o,do_unlink=True)
  shield(ctx,'Guard sculpted heraldic shield rim',(0,-.14,-.1),1.05,1.65,'Gold');shield(ctx,'Guard convex enamel shield',(0,-.25,-.1),.87,1.42,armor,.065)
 elif kind=='Caster':
  for o in list(root.children):
   if 'floating embroidered cloak' in o.name:bpy.data.objects.remove(o,do_unlink=True)
  v=[];f=[];n=32
  for row in range(7):
   t=row/6;z=.37+t*1.36;r=.76-.39*t
   for j in range(n):
    a=j*2*PI/n;rr=r*(1+.08*math.sin(a*8)*(1-t*.5));v.append((math.cos(a)*rr,math.sin(a)*rr*.78,.06*math.cos(a*6)*(1-t)+z))
    if row:k=row*n+j;f.append((k-n,k-n+(1 if j<n-1 else 1-n),k+(1 if j<n-1 else 1-n),k))
  ctx.mesh('Caster tailored folded cloth mantle',v,f,armor,smooth_faces=True)
  for j in range(8):
   a=j*PI/4;ctx.curve('Caster gold embroidered hem',[(math.cos(a+k*.10)*.78,math.sin(a+k*.10)*.60,.45+.06*math.cos(a*6)) for k in range(6)],.018,'Gold')
  joint=next(o for o in root.children if o.get('minion_part')=='staff');ctx.parent=joint
  for side in [-1,1]:ctx.curve('Caster celestial staff crescent',[(side*.12,0,.68),(side*.38,0,1.04),(side*.22,0,1.45)],.055,'Gold')
 else:
  for joint in root.children:
   if joint.get('minion_part')=='wheel':
    ctx.parent=joint
    for j in range(8):
     a=j*PI/4;ctx.limb('Siege carved wheel spoke',(0,0,0),(0,math.cos(a)*.46,math.sin(a)*.46),.055,.045,'Bronze',6)
   elif joint.get('minion_part')=='cannon':
    ctx.parent=joint
    for y in [-1.22,-.55,.22]:ctx.ring('Siege reinforced engraved barrel ring',(0,y,0),.48,.055,'Bronze').rotation_euler.x=PI/2
  ctx.parent=root
  for side in [-1,1]:shield(ctx,'Siege ridged flank armor',(side*.74,-.66,.94),.54,.70,'Gold')
 ctx.parent=saved;return root
def rock(ctx,name,p,scale=(2,2,3),material='Stone',seed=0):
 if material!='Stone':return G['_art_rock'](ctx,name,p,scale,material,seed)
 if 'CliffPaint' not in ctx.materials:
  m=G['painted_material'](ctx,'CliffPaint','3D5661','C0B7A0',.89);c=m.node_tree.nodes.new('ShaderNodeVertexColor');c.layer_name='ValleyPaint';m.node_tree.links.new(c.outputs['Color'],shader(m).inputs['Base Color']);texture_link(ctx,m,image('painted_stone'))
 key=('cliff2009',seed%9)
 if key not in ctx.cache:
  v=[];f=[];colors=[];n=12
  for row,(z,r) in enumerate([(-.50,.78),(-.32,1.0),(-.05,.95),(.02,.79),(.24,.82),(.30,.67),(.54,.71),(.61,.53),(.72,.48)]):
   for j in range(n):
    a=j*2*PI/n;rr=r*(1+.12*math.sin(j*2.3+seed%9));v.append((math.cos(a)*rr+.10*math.sin(row+seed),math.sin(a)*rr+.07*math.cos(row),z+.014*math.sin(j*2)));color=G['blend_color'](G['srgb']('3E5966'),G['srgb']('ACA998'),.24+row*.075)
    if row==8:color=G['blend_color'](color,G['srgb']('577B43'),.65)
    colors.append(color)
    if row:k=row*n+j;f.append((k-n,k-n+(1 if j<n-1 else 1-n),k+(1 if j<n-1 else 1-n),k))
  f.extend([tuple(reversed(range(n))),tuple(8*n+j for j in range(n))]);proto=ctx.mesh('Stratified hand sculpted cliff prototype',v,f,'CliffPaint');G['paint_mesh'](ctx,proto,colors,'CliffPaint');ctx.cache[key]=proto.data;bpy.data.objects.remove(proto,do_unlink=True)
 return ctx.object(name,ctx.cache[key],p,scale,rotation=(0,0,seed*.71))
def forest_mass(ctx,plan):
 result=G['_art_mass'](ctx,plan);seen=set()
 for o in ctx.scene.objects:
  if o.get('category')!='forest_mass' or o.data.as_pointer() in seen:continue
  seen.add(o.data.as_pointer());colors=[]
  for v in o.data.vertices:
   p=v.co;t=G['smooth'](.22,2.2,plan.clearance((p.x,-p.y))) if p.z>0 else 0;colors.append(G['blend_color'](G['srgb']('657F71'),G['forest_color'](p.x,p.y),t))
  G['paint_mesh'](ctx,o,colors,'ForestGround')
 return result
def lighting(ctx):
 G['_art_lighting'](ctx);s=ctx.scene;s.camera.data.ortho_scale=282;s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=-.55
 glare=next((n for n in s.node_tree.nodes if n.type=='GLARE'),None)
 if glare:glare.mix=-.82
def install(g):
 global G;G=g
 for name,key in [('create_materials','materials'),('create_combat_materials','combat_materials'),('create_minion_template','minion'),('create_rock','rock'),('create_lighting_and_camera','lighting')]:g['_art_'+key]=g[name]
 g.update(create_painted_textures=painted_textures,create_materials=materials,create_combat_materials=combat_materials,create_tower=tower,create_minion_template=minion,create_rock=rock,create_lighting_and_camera=lighting)
 for kind,old in list(g['MONSTER_BUILDERS'].items()):
  if kind not in {'MagmaGuardian','AzureGolem','MoonWolf','StoneCentipede','RiftWraith','CrystalCrab','Watcher','RiftRay','SolarColossus','NightLeviathan'}:continue
  def build(ctx,kind=kind,old=old):(wraith if kind=='RiftWraith' else old)(ctx);creature_detail(ctx,kind)
  g['MONSTER_BUILDERS'][kind]=build
 import maze_scene
 g['_art_mass']=maze_scene.make_mass;maze_scene.make_mass=forest_mass
