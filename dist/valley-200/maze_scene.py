"""Blender construction of the authored forest maze. Geometry and collision share one plan."""
import math,random,json
from pathlib import Path
import bpy
from mathutils import Vector
import maze_plan as mp
G={}
def xy(p):return (p[0],-p[1])
def curve(points):return G['path_samples'](G['catmull'](points,10),.32)
def world(p):return [float(p[0]),float(-p[1])]
def add_route(specs,points,width,tag):
 pts=curve(points)
 for a,b in zip(pts,pts[1:]):specs.append(mp.capsule(world(a),world(b),width/2,tag))

def surface_specs(ctx):
 specs=[]
 for lane,points in ctx.lanes.items():
  for a,b in zip(points,points[1:]):specs.append(mp.capsule(world(a),world(b),ctx.cfg.road_width/2,'lane'))
 for points in G['FOREST_PATHS']+G['BUSH_ACCESS']:add_route(specs,points,mp.TRAIL_WIDTH,'trail')
 for t,lane,tier,points in G['TOWER_PASSAGES']:add_route(specs,points,mp.TRAIL_WIDTH,'tower_trail')
 for points in G['GATE_PATHS']:add_route(specs,points,mp.GATE_WIDTH,'gate_trail')
 for points in G['BOSS_APPROACHES']:add_route(specs,points,4,'boss_approach')
 for points in G['MOUNTAIN_ROUTES']:add_route(specs,points,mp.MOUNTAIN_WIDTH,'mountain')
 for t,lane,tier,points in G['MOUNTAIN_PASSAGES']:add_route(specs,points,mp.TRAIL_WIDTH,'mountain_link')
 for room in mp.ROOMS_BLUE+mp.mirrored_rooms():specs.append(mp.disc(room['center'],room['radius'],room['kind']))
 for team,p in G['BASES'].items():
  specs.append(mp.disc(world(p),15.1,'base'));specs.append(mp.disc(world(G['FOUNTAINS'][team]),7,'fountain'))
  add_route(specs,[p,G['FOUNTAINS'][team]],5.4,'base_access')
 for p in G['BOSSES'].values():specs.append(mp.disc(world(p),15.2,'arena'))
 for p,angle,role,half,radius in mp.BUSH_BLUE:
  d=(math.cos(math.radians(angle))*half,math.sin(math.radians(angle))*half)
  for sign in [1,-1]:specs.append(mp.capsule([(p[0]-d[0])*sign,(p[1]-d[1])*sign],[(p[0]+d[0])*sign,(p[1]+d[1])*sign],radius,'bush'))
 for lane,p in G['STONE_BRIDGES']:specs.append(mp.rectangle(world(p),10.6,4,-math.pi/4,'stone_bridge'))
 for kind,p in G['ENERGY_BRIDGES']:specs.append(mp.rectangle(world(p),11.5,2.2,-math.pi/4,'energy_bridge'))
 return specs

def create_flat_soil(ctx,name,points,width=mp.TRAIL_WIDTH):
 pts=curve(points);v=[];faces=[];colors=[];fractions=[-1,-.85,-.55,0,.55,.85,1];level=.06+ctx.path_layer*.00019;ctx.path_layer+=1
 for i,p in enumerate(pts):
  d=(Vector(pts[min(len(pts)-1,i+1)])-Vector(pts[max(0,i-1)])).normalized();n=Vector((-d.y,d.x))
  for f in fractions:
   offset=f*(width*.5+.28+.025*math.sin(i*.37));x=p[0]+n.x*offset;y=p[1]+n.y*offset;v.append((x,y,level))
   edge=G['smooth'](.60,1,abs(f));c=tuple(c*(.97+.025*math.cos(i*.31)) for c in G['srgb']('C49A6C'));colors.append(G['blend_color'](c,G['forest_color'](x,y),edge))
  if i:
   k0=(i-1)*len(fractions)
   if G['route_distance'](p,ctx.river)>7.2:
    for j in range(6):k=k0+j;faces.append((k,k+7,k+8,k+1))
 obj=ctx.mesh(name,v,faces,'TrailBlend',smooth_faces=True);G['paint_mesh'](ctx,obj,colors);obj['surface_type']='warm_ochre_trail';obj['walkable_width']=width;return obj

def pair_route(ctx,name,points,width):
 before=G['snapshot'](ctx);create_flat_soil(ctx,name,points,width);G['mirror_created'](ctx,before,name)

def create_routes(ctx):
 ctx.group('ForestTrails')
 for i,r in enumerate(mp.FOREST_BLUE):pair_route(ctx,f'Winding readable woodland corridor {i+1}',[xy(p) for p in r],mp.TRAIL_WIDTH)
 for i,r in enumerate(mp.GATE_PATHS_BLUE):pair_route(ctx,f'Narrow crystal neck {i+1}',[xy(p) for p in r],mp.GATE_WIDTH)
 for lane,tier,r in mp.PASSAGES_BLUE:pair_route(ctx,f'Rounded {lane} T{tier} forest entrance',[xy(p) for p in r],mp.TRAIL_WIDTH)
 for i,r in enumerate(G['SOLAR_APPROACHES_XZ']):pair_route(ctx,f'Winding arena approach {i+1}',[xy(p) for p in r],4)
 for i,r in enumerate(mp.BUSH_ACCESS_BLUE):pair_route(ctx,f'Concealed grass bend {i+1}',[xy(p) for p in r],mp.TRAIL_WIDTH)
 before=G['snapshot'](ctx);G['create_small_paving'](ctx,'Fountain tiled access',[G['BASES']['Light'],G['FOUNTAINS']['Light']],5.4);G['mirror_created'](ctx,before,'Base access')

def create_mountain(ctx):
 ctx.group('MountainTrails')
 for i,points in enumerate(G['MOUNTAIN_ROUTES'][:2]):
  before=G['snapshot'](ctx);create_flat_soil(ctx,f'Narrow shared mountain ledge {i+1}',points,mp.MOUNTAIN_WIDTH);line=G['path_samples'](curve(points),3.5)
  for j,(a,b) in enumerate(zip(line,line[1:])):
   d=(Vector(b)-Vector(a)).normalized();n=Vector((-d.y,d.x));p=(Vector(a)+Vector(b))*.5
   if n.dot(p)<0:n=-n
   q=p+n*(mp.MOUNTAIN_WIDTH/2+1.1);angle=math.atan2(d.y,d.x);length=math.dist(a,b)
   ctx.box('Mountain rock ledge foundation',(p.x,p.y,-3.1),(length+.25,mp.MOUNTAIN_WIDTH+1.8,6),'Stone',.09,angle)
   ctx.box('Outer ledge retaining masonry',(q.x,q.y,.1),(length-.08,.85,.65),'Stone',.07,angle)
   rail=ctx.box('Mountain retaining collision',(q.x,q.y,.5),(length,.75,1.5),'Stone',0,angle);rail.hide_render=True;rail['physics_only']=True;rail['obstacle_collider']=True;rail['obstacle_kind']='retaining'
  G['mirror_created'](ctx,before,'Mountain shelf pairs')
 for t,lane,tier,r in G['MOUNTAIN_PASSAGES'][:6]:pair_route(ctx,f'Curved {t} {lane} T{tier} mountain connection',r,mp.TRAIL_WIDTH)

def create_clearing(ctx,name,position):
 ctx.group('Clearings');radius=mp.BATTLE_RADIUS
 with ctx.root('Clearing '+name,(*position,0),'clearing') as root:
  root['radius']=radius;n=72;v=[(0,0,.066)];faces=[];colors=[]
  def c(x,y,r):
   x+=position[0];y+=position[1];f=max(0,min(1,.5+.28*math.cos(x*.45+y*.23)+.19*math.cos(y*.61-x*.18)))
   p=G['blend_color'](G['srgb']('9BB068'),G['srgb']('C49A6C'),f);return G['blend_color'](p,G['forest_color'](x,y),G['smooth'](radius-.2,radius+.28,r))
  colors.append(c(0,0,0))
  for row,r in enumerate([1.8,3.6,5.4,radius-.2,radius,radius+.28]):
   for j in range(n):
    a=j*2*math.pi/n;x=math.cos(a)*r;y=math.sin(a)*r;v.append((x,y,.066));colors.append(c(x,y,r))
    if row==0:faces.append((0,1+j,1+(j+1)%n))
    else:faces.append((1+(row-1)*n+j,1+row*n+j,1+row*n+(j+1)%n,1+(row-1)*n+(j+1)%n))
  obj=ctx.mesh('Compact mottled battle clearing',v,faces,'ClearingBlend',smooth_faces=True);G['paint_mesh'](ctx,obj,colors,'ClearingBlend');return root

def room_intervals(room):
 r=room['radius']+.46;half=math.asin(min(.8,mp.DOOR_HALF_WIDTH/r));cuts=[]
 for a in room['doors']:
  a=math.radians(a)%(2*math.pi)
  for off in [-2*math.pi,0,2*math.pi]:
   lo=max(0,a-half+off);hi=min(2*math.pi,a+half+off)
   if hi>lo:cuts.append((lo,hi))
 cuts.sort();free=[];start=0
 for lo,hi in cuts:
  if lo>start:free.append((start,lo))
  start=max(start,hi)
 if start<2*math.pi:free.append((start,2*math.pi))
 return free

def wall_decoration(ctx,segments,label):
 """Actual inset fissures, gold cartouches and irregular moss caps, batched."""
 channels={m:([],[]) for m in ['StoneDark','Gold','Moss']}
 for index,(a,b,n,h) in enumerate(segments):
  d=Vector((b[0]-a[0],b[1]-a[1]));length=d.length
  if length<.1:continue
  d.normalize();p=(Vector(a)+Vector(b))*.5;nn=Vector(n)
  # A thin dark zig-zag sits on the outer masonry face, rather than painting
  # a straight line across the entire mesh.
  v,f=channels['StoneDark'];path=[(p+d*offset+nn*.015,z) for offset,z in [(-.13,.3),(.05,.64),(-.08,.91),(.16,1.2)]]
  for (u,z),(w,zz) in zip(path,path[1:]):
   k=len(v);v.extend([(u.x-d.x*.025,u.y-d.y*.025,z),(u.x+d.x*.025,u.y+d.y*.025,z),(w.x+d.x*.025,w.y+d.y*.025,zz),(w.x-d.x*.025,w.y-d.y*.025,zz)]);f.append((k,k+1,k+2,k+3))
  if index%2==0:
   v,f=channels['Gold'];q=p+nn*.018
   for off,z0,z1 in [(0,.74,1.18),(-.13,.84,.93),(.13,.98,1.07)]:
    u=q+d*off;quad=[tuple(u+d*dx+nn*dy) for dx,dy in [(-.036,-.015),(.036,-.015),(.036,.025),(-.036,.025)]];G['add_prism'](v,f,quad,z0,z1)
  v,f=channels['Moss']
  for j in range(2):
   q=p+d*((j-.5)*length*.32)-nn*.23;r=.22+.08*((index+j)%3);poly=[]
   for k in range(7):
    angle=k*2*math.pi/7;rr=r*(1+.15*math.sin(k*2.2+index));poly.append((q.x+math.cos(angle)*rr,q.y+math.sin(angle)*rr))
   G['add_prism'](v,f,poly,h-.04,h+.045+.035*j)
 for material,(v,f) in channels.items():
  if f:ctx.mesh(label+' '+material+' carved detail',v,f,material)

def create_shore_walls(ctx):
 ctx.group('RiverParapets');ctx.registry['shore_walls']=[]
 n=Vector((-1/math.sqrt(2),-1/math.sqrt(2))) # Blender X/Y of the blue bank normal.
 for index,(lo,hi) in enumerate(mp.SHORE_INTERVALS):
  before=G['snapshot'](ctx);a=Vector((lo,-lo))+n*mp.SHORE_OFFSET;b=Vector((hi,-hi))+n*mp.SHORE_OFFSET
  d=(b-a).normalized();th=mp.SHORE_THICKNESS*.5;poly=[tuple(a-n*th),tuple(b-n*th),tuple(b+n*th),tuple(a+n*th)]
  with ctx.root('Continuous river parapet '+str(index+1),(0,0,0),'shore_wall') as root:
   root['blocks_movement']=True;root['interval_start']=lo;root['interval_end']=hi;root['bank_offset']=mp.SHORE_OFFSET
   v=[];f=[];G['add_prism'](v,f,[tuple(a-n*.7),tuple(b-n*.7),tuple(b+n*.7),tuple(a+n*.7)],-1.15,.22);ctx.mesh('River parapet rock foundation',v,f,'StoneDark',bevel=.035)
   v=[];f=[];count=math.ceil((b-a).length/1.45);segments=[]
   for j in range(count):
    u=a+(b-a)*(j/count);w=a+(b-a)*((j+1)/count)
    for row in range(3):G['add_prism'](v,f,[tuple(u+d*.018-n*.47),tuple(w-d*.018-n*.47),tuple(w-d*.018+n*.47),tuple(u+d*.018+n*.47)],.23+row*.46,.66+row*.46)
    G['add_prism'](v,f,[tuple(u-n*.57),tuple(w-n*.57),tuple(w+n*.57),tuple(u+n*.57)],1.62,1.82)
    if j%2==0:segments.append((tuple(u+n*.48),tuple(w+n*.48),tuple(n),1.82))
    if j%6==0:
     p=(u+w)*.5;angle=math.atan2(d.y,d.x);ctx.box('River carved terminal pier',(p.x,p.y,1.02),(1.03,1.2,2.05),'Stone',.06,angle);ctx.box('River gold capped pier',(p.x,p.y,2.10),(1.15,1.32,.18),'Gold',.045,angle)
   mesh=ctx.mesh('Continuous chamfered river masonry',v,f,'Stone',bevel=.028);mesh['collider_type']='MeshCollider';mesh['blocks_movement']=True
   wall_decoration(ctx,segments,'River ruin')
  G['mirror_created'](ctx,before,'Opposite river parapet')
  for sign in [1,-1]:
   q=[[float(x)*sign,float(y)*sign] for x,y in poly]
   ctx.registry.setdefault('maze_colliders',[]).append({'min':[min(p[i] for p in q) for i in [0,1]],'max':[max(p[i] for p in q) for i in [0,1]],'polygon':q,'perimeter':False,'kind':'shore_wall','height':0})
   ctx.registry['shore_walls'].append({'a':[float(a.x)*sign,float(-a.y)*sign],'b':[float(b.x)*sign,float(-b.y)*sign],'width':mp.SHORE_THICKNESS,'bank_offset':mp.SHORE_OFFSET})

def room_walls(ctx,room):
 ctx.group('PocketWalls');before=G['snapshot'](ctx);cx,cz=room['center'];R=room['radius'];polygons=[];v=[];f=[];segments=[]
 def quad(a,b,inner,outer):return [(cx+math.cos(a)*inner,-cz-math.sin(a)*inner),(cx+math.cos(b)*inner,-cz-math.sin(b)*inner),(cx+math.cos(b)*outer,-cz-math.sin(b)*outer),(cx+math.cos(a)*outer,-cz-math.sin(a)*outer)]
 with ctx.root('Enclosing '+room['key']+' ruin ring',(0,0,0),'room_wall') as root:
  root['room_key']=room['key'];root['door_count']=len(room['doors']);root['blocks_movement']=True
  for lo,hi in room_intervals(room):
   count=max(1,math.ceil((hi-lo)*(R+.46)/1.3))
   for j in range(count):
    a=lo+(hi-lo)*j/count;b=lo+(hi-lo)*(j+1)/count
    collision=quad(a,b,R+.08,R+.85);polygons.append(collision)
    for row in range(3):
     q=quad(a+.006,b-.006,R+.10,R+.83);G['add_prism'](v,f,q,.06+row*.51,.52+row*.51)
    G['add_prism'](v,f,quad(a+.003,b-.003,R+.02,R+.91),1.60,1.78)
    if j%3==0:
     u=(cx+math.cos(a)*(R+.84),-cz-math.sin(a)*(R+.84));w=(cx+math.cos(b)*(R+.84),-cz-math.sin(b)*(R+.84));mid=(a+b)*.5;segments.append((u,w,(math.cos(mid),-math.sin(mid)),1.78))
   for a in [lo,hi]:
    p=(cx+math.cos(a)*(R+.46),-cz-math.sin(a)*(R+.46),.95)
    pier=ctx.box('Forest room doorway pier',p,(.86,1.02,1.9),'Stone',.065,-a+math.pi/2);pier['obstacle_collider']=True;pier['obstacle_kind']='room_pier'
    ctx.box('Mossy room pier coping',(p[0],p[1],1.96),(1.00,1.15,.20),'LaneLight',.04,-a+math.pi/2)
    ctx.box('Ancient pier gold inlay',(p[0],p[1],1.57),(.92,1.07,.10),'Gold',.025,-a+math.pi/2)
   # Broken fluted column drums sit above solid wall, never inside a doorway.
   if hi-lo>.65:
    a=(lo+hi)*.5;p=(cx+math.cos(a)*(R+.45),-cz-math.sin(a)*(R+.45))
    ctx.cylinder('Broken antique column drum',(*p,2.05),.28,.55,'Marble',10,.025)
    ctx.box('Chipped fallen column capital',(*p,2.36),(.69,.58,.12),'LaneLight',.025,-a+.2)
  mesh=ctx.mesh('Continuous bevelled enclosing masonry',v,f,'Stone',bevel=.025);mesh['blocks_movement']=True;mesh['collider_type']='MeshCollider'
  wall_decoration(ctx,segments,'Forest pocket ruin')
 G['mirror_created'](ctx,before,'Enclosed room pairs')
 for poly in polygons:
  for sign in [1,-1]:
   q=[[sign*x,sign*y] for x,y in poly];ctx.registry.setdefault('maze_colliders',[]).append({'min':[min(p[i] for p in q) for i in [0,1]],'max':[max(p[i] for p in q) for i in [0,1]],'polygon':q,'perimeter':False,'kind':'room_wall','height':0})
 return len(polygons)*2

def create_fir(ctx,p,height,variant):
 if 'SprucePaint' not in ctx.materials:
  mat=G['painted_material'](ctx,'SprucePaint','1B3B1E','386D40',.86)
  shader=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');paint=mat.node_tree.nodes.new('ShaderNodeVertexColor');paint.layer_name='ValleyPaint';mat.node_tree.links.new(paint.outputs['Color'],shader.inputs['Base Color'])
 key=('sculpted_spruce_2008',variant%5)
 if key not in ctx.cache:
  verts=[];faces=[];colors=[];n=16
  for tier in range(6):
   r=1.68-tier*.235;z=1.15+tier*.78;start=len(verts);phase=tier*.31+variant*.2
   for row,(rr,zz) in enumerate([(r*.79,z),(r,z+.16),(r*.53,z+.85),(.014,z+1.62)]):
    for j in range(n):
     a=j*2*math.pi/n+phase;scallop=(1 if j%2==0 else .80)*(1+.045*math.sin(j*2.1+tier));verts.append((math.cos(a)*rr*scallop,math.sin(a)*rr*scallop,zz+.06*math.sin(j*1.7)))
     f=min(1,.08+row*.23+tier*.045);colors.append(G['blend_color'](G['srgb']('17391E'),G['srgb']('3B7346'),f))
   for row in range(3):
    for j in range(n):faces.append((start+row*n+j,start+row*n+(j+1)%n,start+(row+1)*n+(j+1)%n,start+(row+1)*n+j))
  proto=ctx.mesh('Six tier hand-painted spruce prototype',verts,faces,'SprucePaint');G['paint_mesh'](ctx,proto,colors,'SprucePaint');ctx.cache[key]=proto.data;bpy.data.objects.remove(proto,do_unlink=True)
 with ctx.root('Dense impassable spruce',(*xy(p),.1),'tree',rotation=variant*.73,scale=height/6.45) as root:
  root['grove_collider']='ForestMass';root['trunk_radius']=.45;root['lod']='six_tier_painted_2008'
  ctx.object('Layered emerald spruce crown',ctx.cache[key]);ctx.limb('Dark spruce sculpted trunk',(0,0,0),(0,0,2.6),.22,.13,'Wood',8)
  for j in range(4):
   a=j*math.pi/2;ctx.limb('Exposed spruce buttress root',(.12*math.cos(a),.12*math.sin(a),.4),(.50*math.cos(a),.50*math.sin(a),.02),.11,.035,'Wood',6)
 return root

def make_mass(ctx,plan):
 import numpy as np
 axis,field=plan.field(-97,97,1);field=field-.28
 # Rock masses stop at the dry lip; the recessed river remains open water.
 x=axis[None,:];z=axis[:,None];dry=(np.abs(x-z)/math.sqrt(2)-7.5);limit=95-np.maximum(np.abs(x),np.abs(z))
 field=np.minimum(field,np.minimum(dry,limit))
 verts=[];faces=[];cache={};eligible=0
 def vert(x,z):
  k=(round(x,6),round(z,6))
  if k not in cache:
   cache[k]=len(verts);h=.78+.22*math.cos(x*.21+z*.12)+.13*math.cos(z*.41-x*.10);verts.append((x,-z,h))
  return cache[k]
 def clipped(triangle):
  out=[]
  for a,b in zip(triangle,triangle[1:]+triangle[:1]):
   if a[2]>=0:out.append(a)
   if (a[2]>=0)!=(b[2]>=0):
    t=a[2]/(a[2]-b[2]);out.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,0))
  clean=[]
  for p in out:
   if not clean or math.dist(p[:2],clean[-1][:2])>1e-7:clean.append(p)
  if len(clean)>1 and math.dist(clean[0][:2],clean[-1][:2])<1e-7:clean.pop()
  if len(clean)>=3:faces.append(tuple(vert(p[0],p[1]) for p in clean))
 for j in range(len(axis)-1):
  for i in range(len(axis)-1):
   if axis[i]+.5-(axis[j]+.5)>=0:continue
   q=[(float(axis[i]),float(axis[j]),float(field[j,i])),(float(axis[i+1]),float(axis[j]),float(field[j,i+1])),(float(axis[i+1]),float(axis[j+1]),float(field[j+1,i+1])),(float(axis[i]),float(axis[j+1]),float(field[j+1,i]))]
   if all(p[2]<0 for p in q):continue
   if all(p[2]>=0 for p in q):faces.append(tuple(vert(p[0],p[1]) for p in q));eligible+=1
   else:clipped([q[0],q[1],q[2]]);clipped([q[0],q[2],q[3]])
 # Add actual vertical cliff rims around the cut-out corridors; there is no flat green shortcut below.
 edges={}
 for face in faces:
  for a,b in zip(face,face[1:]+face[:1]):
   k=tuple(sorted((a,b)));edges[k]=None if k in edges else (a,b)
 for e in edges.values():
  if e is None:continue
  a,b=e;k=len(verts);verts.extend([(verts[a][0],verts[a][1],-.20),(verts[b][0],verts[b][1],-.20)]);faces.append((a,b,k+1,k))
 ctx.group('ForestMass');before=G['snapshot'](ctx)
 obj=ctx.mesh('Solid mossy rock grove foundation',verts,faces,'Moss',smooth_faces=False);obj['category']='forest_mass';obj['blocks_movement']=True;obj['collider_type']='MeshCollider';obj['coverage_contract']='outside_surface_specs'
 G['mirror_created'](ctx,before,'Complete forest substrate')
 ctx.registry['mass_cells']=eligible*2
 return field,axis

def create_forest(ctx):
 create_shore_walls(ctx)
 plan=mp.SurfacePlan(surface_specs(ctx));ctx.surface_plan=plan
 field,axis=make_mass(ctx,plan)
 for room in mp.ROOMS_BLUE:room_walls(ctx,room)
 ctx.group('Forest');rng=random.Random(ctx.cfg.seed+77);positions=[];groves=[]
 clusters=mp.grove_clusters(plan)
 for i,cluster in enumerate(clusters):
  ids=[]
  for j,p in enumerate(cluster['points']):
   before=G['snapshot'](ctx);o=create_fir(ctx,p,rng.uniform(5.3,6.5),i*7+j);o['grove_id']=i+1
   if math.dist(p,mp.BLUE_GATES[0])<8:o['gate_flank']=True
   G['mirror_created'](ctx,before,'Compact island grove pairs');positions.extend([xy(p),xy(mp.neg(p))]);ids.append(list(p))
  groves.append({'id':i+1,'center':list(cluster['center']),'points':ids})
 ctx.registry['groves']=groves
 ctx.registry['trees']=positions;ctx.group('TallGrass')
 for i,(p,angle,role,half,radius) in enumerate(mp.BUSH_BLUE):
  before=G['snapshot'](ctx);root=G['create_bush'](ctx,(*xy(p),.075),1,i,half,radius);root.rotation_euler.z=-math.radians(angle);root['bush_id']=i+1;root['mirror_id']=i+1+len(mp.BUSH_BLUE);root['role']=role
  pair=G['mirror_created'](ctx,before,'Authored entrance grass');other=pair[root];other['bush_id']=i+1+len(mp.BUSH_BLUE);other['mirror_id']=i+1
 ctx.registry['bushes']=[xy(p) for p,a,r,h,w in mp.BUSH_BLUE]+[xy(mp.neg(p)) for p,a,r,h,w in mp.BUSH_BLUE]
 # Small ruin fragments occupy the inter-lane separator strips, never a corridor.
 count=0;ctx.group('OuterForestRuins')
 for p in [(-87,z) for z in [-40,-10,18,42]]+[(x,-87) for x in [-35,-5,25,52]]:
  angle=math.pi/2 if p[0]==-87 else 0;d=(math.cos(angle),math.sin(angle))
  if not all(plan.clearance((p[0]+d[0]*t,p[1]+d[1]*t))>1.25 for t in [-2,0,2]):continue
  before=G['snapshot'](ctx);G['create_wall'](ctx,'Inter-lane broken ruin',(*xy(p),0),3.4,-angle,True);G['mirror_created'](ctx,before,'Outer separator ruins');count+=2
 ctx.registry['forest_wall_count']=16+count;ctx.registry['tree_count']=len(positions)
 print('MAZE FOREST',len(positions),'firs;',len(ctx.registry['maze_colliders']),'wall arc colliders;',len(ctx.registry['bushes']),'grass pockets',flush=True)

def export_layout(ctx,validation):
 old=G['_old_export'];old(ctx,validation);p=ctx.cfg.output/'ValleyOfShards.layout.json';data=json.loads(p.read_text())
 def sample(r):return [{'X':q[0],'Y':q[1]} for q in curve(r)]
 data['generator_version']='5.1';data['forest_paths']=[sample(r) for r in G['FOREST_PATHS']];data['bush_access_paths']=[sample(r) for r in G['BUSH_ACCESS']]
 data['tower_passages']=[{'team':t,'lane':lane,'tier':tier,'points':sample(r),'width':mp.TRAIL_WIDTH} for t,lane,tier,r in G['TOWER_PASSAGES']]
 data['boss_approaches']=[{'boss':i//2,'points':sample(r),'width':4} for i,r in enumerate(G['BOSS_APPROACHES'])]
 data['mountain_routes']=[{'points':sample(r),'width':mp.MOUNTAIN_WIDTH} for r in G['MOUNTAIN_ROUTES']]
 data['mountain_passages']=[{'team':t,'lane':lane,'tier':tier,'points':sample(r),'width':mp.TRAIL_WIDTH} for t,lane,tier,r in G['MOUNTAIN_PASSAGES']]
 for c,r in zip(data['crystals'],G['GATE_PATHS']):c['short_path']=sample(r);c['width']=mp.GATE_WIDTH
 roots={o['bush_id']:o for o in ctx.scene.objects if o.get('category')=='bush'}
 for b in data['bushes']:
  o=roots[b['id']];b['radius']=o['trigger_radius'];b['half_length']=o['half_length']
 for c in data['camps']:c['radius']=mp.CAMP_RADII[(c['id']-1)%6+1]
 data['clearing_radius']=mp.BATTLE_RADIUS;data['forest_path_width']=mp.TRAIL_WIDTH
 data['rooms']=mp.ROOMS_BLUE+mp.mirrored_rooms();data['surface_specs']=ctx.surface_plan.specs
 data['groves']=ctx.registry['groves'];data['shore_walls']=ctx.registry['shore_walls'];data['colliders']+=ctx.registry['maze_colliders'];data['maze']={'generation':'readable_2008','forest_mass_meshes':2,'covered_cells':ctx.registry['mass_cells'],'tree_count':len(ctx.registry['trees']),'previous_tree_count':868,'grove_size':[3,6],'door_width':mp.DOOR_HALF_WIDTH*2,'no_open_grass':True}
 print('BAKING MAZE NAVIGATION',flush=True);data['navigation']=mp.bake_navigation(data);p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')));print('MAZE NAV BAKED',data['navigation']['count'],'x',data['navigation']['count'],data['navigation']['walkable_cells'],'walkable cells',flush=True)

def install(g):
 global G;G=g;g['_old_export']=g['export_layout'];g['_old_camp']=g['create_camp']
 def camp(ctx,index,kind,position):
  root=g['_old_camp'](ctx,index,kind,position);radius=mp.CAMP_RADII[(index-1)%6+1];root['pocket_radius']=radius
  for o in root.children:
   if 'Camp natural clearing' in o.name:o.scale.x*=radius/5.45;o.scale.y*=radius/5.45
   if 'Camp edge mossy pebble' in o.name:o.location.x*=radius/5.35;o.location.y*=radius/5.35
  return root
 g.update(create_flat_soil=create_flat_soil,create_symmetric_routes=create_routes,create_mountain_trails=create_mountain,create_clearing=create_clearing,create_forest=create_forest,export_layout=export_layout,create_camp=camp)
