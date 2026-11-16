"""Canonical MOBA forest topology and shared geometric surface contract (X/Z world)."""
from __future__ import annotations
import math
TRAIL_WIDTH=3.0
GATE_WIDTH=3.0
MOUNTAIN_WIDTH=3.8
APPROACH_WIDTH=4.0
DOOR_HALF_WIDTH=2.15
BUSH_RADIUS=1.2
BATTLE_RADIUS=6.8
CAMP_RADII={1:5.1,2:5.2,3:5.2,4:5.1,5:4.0,6:5.0}
ROOMS_BLUE=[
 {'key':'West','kind':'clearing','center':[-48,12],'radius':BATTLE_RADIUS,'doors':[-112.62,156.80,-20.56]},
 {'key':'South','kind':'clearing','center':[-12,48],'radius':BATTLE_RADIUS,'doors':[-100,-35,168]},
 {'key':'Camp1','kind':'camp','camp':1,'center':[-62,18],'radius':5.1,'doors':[90,-120.96,-23.20]},
 {'key':'Camp2','kind':'camp','camp':2,'center':[-58,-12],'radius':5.2,'doors':[-150,67.38,-50]},
 {'key':'Camp3','kind':'camp','camp':3,'center':[-32,6],'radius':5.2,'doors':[159.44,50,-100]},
 {'key':'Camp4','kind':'camp','camp':4,'center':[-45,55],'radius':5.1,'doors':[90,-10]},
 {'key':'Camp5','kind':'camp','camp':5,'center':[-6,58],'radius':4.0,'doors':[180,90,0]},
 {'key':'Camp6','kind':'camp','camp':6,'center':[22,56],'radius':5.0,'doors':[180,90,-45]}]
ROOMS={r['key']:r for r in ROOMS_BLUE}
def neg(p):return (-p[0],-p[1])
def point(room,door,offset=0):
 r=ROOMS[room];a=math.radians(r['doors'][door]);d=r['radius']+offset
 return (r['center'][0]+math.cos(a)*d,r['center'][1]+math.sin(a)*d)
def leg(room,door):return [point(room,door,-1.4),point(room,door,0),point(room,door,2.5)]
def room_link(a,ai,b,bi,via=()):
 # Close pockets connect directly; long links use radial door anchors before turning.
 if not via and math.dist(ROOMS[a]['center'],ROOMS[b]['center'])-ROOMS[a]['radius']-ROOMS[b]['radius']<6:
  return [point(a,ai,-1.4),point(a,ai),point(b,bi),point(b,bi,-1.4)]
 return leg(a,ai)+list(via)+list(reversed(leg(b,bi)))
def to_room(start,via,room,door):return [start]+list(via)+list(reversed(leg(room,door)))
BLUE_GATES=[(-10,32),(-68,8),(8,56)]
# The six side tower entrances are intentionally S-curves instead of right-angle tees.
PASSAGES_BLUE=[
 ('Top',3,to_room((-75.5,36),[(-71,37),(-67,33),(-64,28)],'Camp1',0)),
 ('Top',2,to_room((-75.5,5),[(-72,6),(-68,8)],'Camp1',1)),
 ('Top',1,to_room((-75.5,-25),[(-71,-26),(-67,-24),(-65,-20)],'Camp2',0)),
 ('Bot',3,to_room((-44,75.5),[(-47,72),(-48,67)],'Camp4',0)),
 ('Bot',2,to_room((-14,75.5),[(-10,72),(-7,67)],'Camp5',1)),
 ('Bot',1,to_room((16,75.5),[(20,72),(25,68)],'Camp6',1)),
 ('Mid',3,to_room((-51.5,47),[(-55,44),(-58,36),(-60,29)],'Camp1',0)),
 ('Mid',2,to_room((-28,33.5),[(-24,36),(-19,35),(-16,29),(-10,28),(-10,30),(-10,32),(-10,34),(-10,36)],'South',0)),
 ('Mid',1,to_room((-18,13),[(-22,15),(-25,14)],'Camp3',1))]
FOREST_BLUE=[
 room_link('Camp1',2,'West',1),
 room_link('Camp2',1,'West',0,[(-58,-2),(-57,1)]),
 room_link('West',2,'Camp3',0),
 leg('Camp2',2)+[(-50,-21),(-44,-23),(-38,-22),(-35,-19.5),(-32,-18)],
 leg('Camp3',2)+[(-34,-6),(-37,-12),(-35,-19.5),(-32,-18)],
 to_room((-34,28.5),[(-37,24),(-35,16)],'Camp3',1),
 to_room((-10,16),[(-3,22),(2,32),(0,39)],'South',1),
 room_link('Camp4',1,'South',2,[(-35,55.5),(-28,53),(-24,51)]),
 room_link('Camp4',0,'Camp5',0,[(-33,66),(-22,65),(-16,61)]),
 room_link('Camp5',2,'Camp6',0,[(4,57),(8,56),(12,56.2)]),
 leg('Camp6',2)+[(32,49),(28,43),(22,40),(18,36),(18,32)]]
GATE_PATHS_BLUE=[PASSAGES_BLUE[7][2],PASSAGES_BLUE[1][2],FOREST_BLUE[9]]
BUSH_BLUE=[]
# Long central pockets, dry river bank pockets; the doorway grass is radial and narrow.
BUSH_BLUE += [((-24,13),-35,'mid',2.2,.9),((-21.15,35.98),-10,'mid',2.2,.9)]
BUSH_BLUE += [((-35,-19.5),30,'river',1.6,.9),((18,36),90,'river',1.6,.9)]
for key in ['West','South']:
 for j,a in enumerate(ROOMS[key]['doors']):BUSH_BLUE.append((point(key,j,-.15),a,'clearing_'+key.lower(),1.25,.9))
BUSH_BLUE += [
 (point('Camp1',0,2),90,'magma',1.2,.9),
 (point('Camp4',0,2),90,'azure',1.2,.9),
 (point('Camp5',1,2),90,'centipedes',1.2,.9),
 ((-87.5,37.4),15,'side_turn',1.5,.9),((-47.4,87.5),75,'side_turn',1.5,.9),
 ((-87.5,7.4),15,'side_turn',1.4,.9),
 (point('Camp2',0,2),-150,'wolves',1.2,.9),
 (point('Camp6',2,2),-45,'crab',1.2,.9),
 ((-55,-72),-35,'boss',1.4,.9),((-72,-55),-55,'boss',1.4,.9)]
# Additive grass is linked only to the nearby corridor, never across a room wall.
BUSH_ACCESS_BLUE=[[(-22,15),(-24,13)]]
# Two additional dry pockets at the exits of the central stone bridge.
BUSH_BLUE += [((-10,5),45,'mid_shore',1.35,.9),((-5,10),45,'mid_shore',1.35,.9)]
BUSH_BLUE=[(p,a,role,h,BUSH_RADIUS) for p,a,role,h,r in BUSH_BLUE]
BUSH_ACCESS_BLUE += [[(-18,13),(-15,9),(-10,5)],[(-10,16),(-6,14),(-5,10)]]

# Only these separator islands receive trees. Each accepted island holds 3–6
# trees; all remaining unwalkable ground is a readable mossy rock/ruin mass.
GROVE_ANCHORS=[(-14.7,32),(-5.3,32),
 (-61,44),(-60,31),(-56,4),(-44,-3),(-29,-5),(-45,-25),(-24,31),(-34,65),(3,42),(7,68),(34,55),(1,29),
 (-71,49),(-68,-7),(-61,-34),(-53,-25),(-42,-13),(-34,-13),(-23,-8),(-15,3),
 (-55,26),(-35,27),(-25,36),(-4,31),(4,39),(8,47),(34,41),(40,62),(-24,64),(-58,62),(-67,64),(-35,40),
 (-87,56),(-87,24),(-87,-8),(-87,-38),(-51,87),(-19,87),(13,87),(43,87),
 (-70,0),(-41,36),(-21,57),(21,65),(-54,18),(-34,-23),(-7,24),(-16,-1),
 (-73,58),(-69,68),(4,73),(46,73),(-73,-44),(-44,-35),(-17,-4),(-2,13),(-54,69),(-30,18),(-36,48),(-72,18)]

def grove_clusters(plan):
 """Deterministic compact plantings; positions never occupy a reserved floor."""
 occupied=[];clusters=[]
 for anchor in GROVE_ANCHORS:
  candidates=[]
  for iz in range(-4,5):
   for ix in range(-4,5):
    p=(anchor[0]+ix*.95,anchor[1]+iz*.95)
    if math.dist(p,anchor)>4.4 or p[0]-p[1]>=-14.5 or max(map(abs,p))>93:continue
    if plan.clearance(p)<1.40:continue
    candidates.append(p)
  candidates.sort(key=lambda p:(math.dist(p,anchor),p))
  group=[];desired=6
  for p in candidates:
   if any(math.dist(p,q)<3.65 for q in occupied) or any(math.dist(p,q)<2.0 for q in group):continue
   group.append(p)
   if len(group)>=desired:break
  if len(group)<3:continue
  if len(occupied)+len(group)>248:break
  clusters.append({'center':anchor,'points':group});occupied+=group
 return clusters

# Walls run up to the three permanent bridge decks; the two dynamic bridges
# have wide openings aligned with their actual deck and bank approaches.
SHORE_INTERVALS=[(-55,-29),(-21,-4),(4,21),(29,55)]
SHORE_OFFSET=8.0
SHORE_THICKNESS=1.0


def mirrored_rooms():
 out=[]
 for r in ROOMS_BLUE:
  q={**r,'center':list(neg(r['center'])),'doors':[a+180 for a in r['doors']],'key':{'West':'East','South':'North'}.get(r['key'],r['key']+'Red')}
  if 'camp' in r:q['camp']=r['camp']+6
  out.append(q)
 return out

def capsule(a,b,r,tag):return {'kind':'capsule','a':list(a),'b':list(b),'r':r,'tag':tag}
def disc(p,r,tag):return {'kind':'disc','p':list(p),'r':r,'tag':tag}
def rectangle(p,hx,hz,angle,tag):return {'kind':'rect','p':list(p),'hx':hx,'hz':hz,'angle':angle,'tag':tag}

def bounds(s,expand=0):
 if s['kind']=='capsule':
  a,b=s['a'],s['b'];r=s['r']+expand;return (min(a[0],b[0])-r,min(a[1],b[1])-r,max(a[0],b[0])+r,max(a[1],b[1])+r)
 if s['kind']=='disc':
  x,z=s['p'];r=s['r']+expand;return x-r,z-r,x+r,z+r
 x,z=s['p'];r=math.hypot(s['hx'],s['hz'])+expand;return x-r,z-r,x+r,z+r

def distance(p,s):
 x,z=p
 if s['kind']=='capsule':
  ax,az=s['a'];bx,bz=s['b'];dx=bx-ax;dz=bz-az;t=max(0,min(1,((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz or 1)))
  return math.hypot(x-ax-dx*t,z-az-dz*t)-s['r']
 if s['kind']=='disc':return math.dist(p,s['p'])-s['r']
 c=math.cos(s['angle']);ss=math.sin(s['angle']);dx=x-s['p'][0];dz=z-s['p'][1];a=abs(dx*c+dz*ss)-s['hx'];b=abs(-dx*ss+dz*c)-s['hz']
 return math.hypot(max(0,a),max(0,b))+min(max(a,b),0)

class SurfacePlan:
 def __init__(self,specs):
  self.specs=specs;self.cells={};self.tile=6
  for s in specs:
   x0,z0,x1,z1=bounds(s,3)
   for z in range(math.floor(z0/6),math.floor(z1/6)+1):
    for x in range(math.floor(x0/6),math.floor(x1/6)+1):self.cells.setdefault((x,z),[]).append(s)
 def clearance(self,p):return min((distance(p,s) for s in self.cells.get((math.floor(p[0]/6),math.floor(p[1]/6)),[])),default=100)
 def field(self,minimum=-98,maximum=98,step=1):
  import numpy as np
  axis=np.arange(minimum,maximum+step*.5,step);field=np.full((len(axis),len(axis)),50,dtype=np.float32)
  for s in self.specs:
   x0,z0,x1,z1=bounds(s,3);ix0=max(0,math.ceil((x0-minimum)/step));ix1=min(len(axis),math.floor((x1-minimum)/step)+1);iz0=max(0,math.ceil((z0-minimum)/step));iz1=min(len(axis),math.floor((z1-minimum)/step)+1)
   if ix0>=ix1 or iz0>=iz1:continue
   x=axis[ix0:ix1][None,:];z=axis[iz0:iz1][:,None];d=array_distance(x,z,s)
   part=field[iz0:iz1,ix0:ix1];np.minimum(part,d,out=part)
  return axis,field

def array_distance(x,z,s):
 import numpy as np
 if s['kind']=='capsule':
  ax,az=s['a'];bx,bz=s['b'];dx=bx-ax;dz=bz-az;t=np.clip(((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz or 1),0,1)
  return np.hypot(x-ax-dx*t,z-az-dz*t)-s['r']
 if s['kind']=='disc':return np.hypot(x-s['p'][0],z-s['p'][1])-s['r']
 c=math.cos(s['angle']);ss=math.sin(s['angle']);dx=x-s['p'][0];dz=z-s['p'][1];a=np.abs(dx*c+dz*ss)-s['hx'];b=np.abs(-dx*ss+dz*c)-s['hz']
 return np.hypot(np.maximum(0,a),np.maximum(0,b))+np.minimum(np.maximum(a,b),0)

def runs(mask):
 import numpy as np
 a=mask.ravel().astype(np.int8);edges=np.flatnonzero(np.diff(np.r_[0,a,0]));return [[int(x),int(y-x)] for x,y in zip(edges[::2],edges[1::2])]

def bake_navigation(data):
 import numpy as np
 minimum=-102;step=.25;count=817;axis=np.arange(count)*step+minimum;r=.63
 mask=np.zeros((count,count),dtype=bool)
 for s in data['surface_specs']:
  x0,z0,x1,z1=bounds(s);i=max(0,math.ceil((x0-minimum)/step));j=min(count,math.floor((x1-minimum)/step)+1);k=max(0,math.ceil((z0-minimum)/step));l=min(count,math.floor((z1-minimum)/step)+1)
  if i>=j or k>=l:continue
  x=axis[i:j][None,:];z=axis[k:l][:,None];mask[k:l,i:j] |= array_distance(x,z,s)<=-r+1e-8
 # Structures and trunks are true obstacles, not arbitrary empty grass exclusions.
 obstacles=[]
 for t in data['towers']:obstacles.append((t['position']['X'],-t['position']['Y'],2.65))
 for p in data['bases'].values():obstacles.append((p['X'],-p['Y'],3.1))
 for p in data['trees']:obstacles.append((p['X'],-p['Y'],.45))
 for cx,cz,radius in obstacles:
  rr=radius+r;i=max(0,math.floor((cx-rr-minimum)/step));j=min(count,math.ceil((cx+rr-minimum)/step)+1);k=max(0,math.floor((cz-rr-minimum)/step));l=min(count,math.ceil((cz+rr-minimum)/step)+1)
  if i<j and k<l:mask[k:l,i:j]&=np.hypot(axis[i:j][None,:]-cx,axis[k:l][:,None]-cz)>=rr
 for row in data['colliders']:
  poly=[(p[0],-p[1]) for p in row['polygon']];x0=min(p[0] for p in poly)-r;x1=max(p[0] for p in poly)+r;z0=min(p[1] for p in poly)-r;z1=max(p[1] for p in poly)+r
  i=max(0,math.floor((x0-minimum)/step));j=min(count,math.ceil((x1-minimum)/step)+1);k=max(0,math.floor((z0-minimum)/step));l=min(count,math.ceil((z1-minimum)/step)+1)
  if i>=j or k>=l:continue
  x=axis[i:j][None,:];z=axis[k:l][:,None];hit=np.zeros((l-k,j-i),dtype=bool);inside=hit.copy()
  for a,b in zip(poly,poly[1:]+poly[:1]):
   hit|=array_distance(x,z,capsule(a,b,0,'edge'))<=r
   if abs(b[1]-a[1])>1e-10:inside^=((a[1]>z)!=(b[1]>z))&(x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])
  mask[k:l,i:j]&=~(hit|inside)
 x=axis[None,:];z=axis[:,None];mask&=(np.abs(x)<=99.37)&(np.abs(z)<=99.37)
 river=np.abs(x-z)/math.sqrt(2)<data['river_half_width']+.6
 for p in data['bosses'].values():river&=np.hypot(x-p['X'],z+p['Y'])>14.6
 assert np.array_equal(mask,mask[::-1,::-1]),'Baked navigation lost 180-degree symmetry'
 return {'min':minimum,'step':step,'count':count,'radius':r,'static_runs':runs(mask),'river_runs':runs(river),'walkable_cells':int(mask.sum())}
