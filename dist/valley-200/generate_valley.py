#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Долина Осколков — автономный генератор Blender 4.0+.

Запуск: blender -b --python generate_valley.py -- --out ./output --render
Из Text Editor: Run Script. Создаёт отдельную сцену, не очищает пользовательскую.
Координаты: X/Y — земля, Z — высота. Размер игровой земли строго 200 x 200.
Внешние библиотеки, ассеты и аддоны не требуются. Проверено Blender 4.3.2.
"""
from __future__ import annotations
import argparse
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from contextlib import contextmanager
import bpy
import bmesh
from mathutils import Vector

PI = math.pi
SCENE_NAME = "ValleyOfShards_200"
PREFIX = "VOS200::"

# -----------------------------------------------------------------------------
# 1. Декларативная расстановка. Номера T1/T2/T3 соответствуют запросу, не индексам.
# -----------------------------------------------------------------------------
TOWERS = {
    "Top": {"Light": [(3, -65, -20), (2, -65, 20), (1, -65, 50)],
            "Dark":  [(1, -35, 65), (2, 0, 65), (3, 45, 65)]},
    "Mid": {"Light": [(3, -55, -55), (2, -40, -35), (1, -15, -15)],
            "Dark":  [(1, 15, 15), (2, 35, 35), (3, 55, 55)]},
    "Bot": {"Light": [(3, -40, -65), (2, 0, -65), (1, 40, -65)],
            "Dark":  [(1, 65, -45), (2, 65, -5), (3, 65, 35)]},
}
BASES = {"Light": (-75, -75), "Dark": (75, 75)}
BOSSES = {"SolarColossus": (-86, 86), "NightLeviathan": (86, -86)}
FOUNTAINS = {"Light": (-89, -89), "Dark": (89, 89)}
CLEARINGS = {"West": (-45, -10), "North": (15, 45),
             "East": (45, -10), "South": (-15, -45)}
CAMPS = [
    (1, "MoonWolf", (-55, -25)), (2, "StoneCentipede", (-55, 15)),
    (3, "RiftWraith", (-25, -10)), (4, "MagmaGuardian", (-40, -45)),
    (5, "AzureGolem", (0, -50)), (6, "CrystalCrab", (30, -45)),
    (7, "MagmaGuardian", (50, 20)), (8, "MoonWolf", (55, -25)),
    (9, "RiftWraith", (25, 0)), (10, "AzureGolem", (35, 45)),
    (11, "StoneCentipede", (0, 45)), (12, "CrystalCrab", (-25, 45)),
]
LANE_CONTROL = {
    "Top": [(-75,-75),(-65,-62),(-65,-20),(-65,20),(-65,50),
            (-65,56),(-60.5,60.5),(-56,65),(-35,65),(0,65),(45,65),(62,65),(75,75)],
    "Mid": [(-75,-75),(-55,-55),(-40,-35),(-15,-15),(0,0),
            (15,15),(35,35),(55,55),(75,75)],
    "Bot": [(-75,-75),(-62,-65),(-40,-65),(0,-65),(40,-65),
            (56,-65),(60.5,-60.5),(65,-56),(65,-45),(65,-5),(65,35),(65,62),(75,75)],
}
# Центральный участок — NW -> SE. Концы огибают угловые арены.
RIVER_CONTROL = [(-112,112),(-100,100),(-86,86),(-60.5,60.5),(-30,30),(0,0),(30,-30),(60.5,-60.5),(86,-86),(100,-100),(112,-112)]
STONE_BRIDGES = [("Top",(-60.5,60.5)), ("Mid",(0,0)), ("Bot",(60.5,-60.5))]
ENERGY_BRIDGES = [("Dawn",(-30,30)), ("Dusk",(30,-30))]
# У каждой точки есть собственный короткий проход, поперечные стенки и 24 HP.
CRYSTAL_GATES = [
    ((-47,3), CLEARINGS["West"]), ((-33,-11), CLEARINGS["West"]),
    ((-45,24),(-30,30)), ((3,37), CLEARINGS["North"]),
    ((34,-1), CLEARINGS["East"]), ((53,3), CLEARINGS["East"]),
    ((20,-35),(22,-39)), ((44,-25), (55,-25)),
]
BOSS_APPROACHES = [
    [(-69,50),(-82,55),(-91,65),(-92,76),(-86,86)],
    [(-35,69),(-44,80),(-61,91),(-74,91),(-86,86)],
    [(40,-69),(51,-82),(66,-94),(76,-92),(86,-86)],
    [(69,-45),(83,-51),(94,-65),(91,-76),(86,-86)],
]
TOWER_PASSAGES = [
    ("Light","Top",3,[(-61,-20),(-55,-25)]),
    ("Light","Top",2,[(-61,20),(-55,15)]),
    ("Light","Top",1,[(-61,50),(-53,42)]),
    ("Dark","Top",1,[(-35,61),(-25,45)]),
    ("Dark","Top",2,[(0,61),(0,45)]),
    ("Dark","Top",3,[(45,61),(35,45)]),
    ("Light","Mid",3,[(-58,-52),(-55,-42),(-55,-25)]),
    ("Light","Mid",2,[(-43,-32),(-55,-25)]),
    ("Light","Mid",1,[(-18,-12),(-25,-10)]),
    ("Dark","Mid",1,[(18,12),(25,0)]),
    ("Dark","Mid",2,[(38,32),(50,20)]),
    ("Dark","Mid",3,[(58,52),(55,43),(35,45)]),
    ("Light","Bot",3,[(-40,-61),(-40,-45)]),
    ("Light","Bot",2,[(0,-61),(0,-50)]),
    ("Light","Bot",1,[(40,-61),(30,-45)]),
    ("Dark","Bot",1,[(61,-45),(55,-25)]),
    ("Dark","Bot",2,[(61,-5),(55,10),(50,20)]),
    ("Dark","Bot",3,[(61,35),(50,20)]),
]
FOREST_PATHS = [
    [(-65,20),(-55,15),(-47,3),(-45,-10),(-55,-25)],
    [(-55,-55),(-40,-45),(-15,-45),(0,-50),(30,-45),(40,-65)],
    [(-35,65),(-25,45),(0,45),(15,45),(35,45),(45,65)],
    [(65,-5),(45,-10),(25,0),(34,-1),(50,20),(65,35)],
    [(-45,-10),(-33,-11),(-25,-10),(-15,-15)],
    [(-55,15),(-46,17),(-38.84,21.16)],
    [(-21.16,38.84),(-15,45),(15,45)],
    [(15,45),(3,37),(-6,24),(-15,15)],
    [(45,-10),(53,3),(50,20)],
    [(30,-45),(23,-43),(21.16,-38.84)],
    [(38.84,-21.16),(43,-14),(45,-10)],
    [(-15,-45),(-3,-34),(6,-25),(15,-15)],
]


@dataclass
class Config:
    output: Path
    seed: int = 1649
    terrain_cells: int = 104
    tree_count: int = 130
    bush_count: int = 60
    road_width: float = 10.4
    river_half_width: float = 6.6
    resolution: int = 1440
    samples: int = 32
    render: bool = False
    detail_renders: bool = False
    labels: bool = True
    camera_elevation: float = 55.0  # градусов над горизонтальной плоскостью
    frames: int = 240
    fps: int = 24


def srgb(hex_color: str):
    h = hex_color.lstrip("#")
    values = [int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values)


def smooth(a,b,x):
    t = max(0.0,min(1.0,(x-a)/(b-a)))
    return t*t*(3-2*t)


def distance_to_segment(p,a,b):
    dx,dy = b[0]-a[0],b[1]-a[1]
    t = max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
    return math.hypot(p[0]-a[0]-dx*t,p[1]-a[1]-dy*t)


def route_distance(p,route):
    return min(distance_to_segment(p,a,b) for a,b in zip(route,route[1:]))


def catmull(points,steps=5):
    result=[]
    for i in range(len(points)-1):
        a=Vector(points[max(0,i-1)]);b=Vector(points[i]);c=Vector(points[i+1]);d=Vector(points[min(len(points)-1,i+2)])
        for j in range(steps):
            t=j/steps
            p=(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)*.5
            result.append(tuple(p))
    result.append(tuple(points[-1]))
    return result


def route_length(points):
    return sum(math.dist(a,b) for a,b in zip(points,points[1:]))


def route_sample(points,distance):
    for a,b in zip(points,points[1:]):
        length=math.dist(a,b)
        if distance<=length:
            t=max(0,distance/length)
            return tuple(a[i]+(b[i]-a[i])*t for i in range(len(a)))
        distance-=length
    return tuple(points[-1])


def path_samples(points,spacing):
    length=route_length(points);n=max(1,math.ceil(length/spacing))
    return [route_sample(points,length*i/n) for i in range(n+1)]


def action_curves(owner):
    """Legacy Actions (4.0–4.3) и layered/slot Actions (4.4+)."""
    animation=owner.animation_data
    if not animation or not animation.action:return []
    action=animation.action
    if hasattr(action,"fcurves"):return list(action.fcurves)
    result=[];slot=getattr(animation,"action_slot",None)
    for layer in getattr(action,"layers",[]):
        for strip in layer.strips:
            if slot is not None and hasattr(strip,"channelbag"):
                bag=strip.channelbag(slot)
                if bag:result.extend(bag.fcurves)
    return result


def set_input(node,name,value,old_name=None):
    socket=node.inputs.get(name) or (node.inputs.get(old_name) if old_name else None)
    if socket is not None:socket.default_value=value


class Context:
    def __init__(self,config):
        self.cfg=config;self.rng=random.Random(config.seed)
        self.materials={};self.cache={};self.parent=None;self.groups={};self.registry={};self.path_layer=0
        self.lanes={name:catmull(points) for name,points in LANE_CONTROL.items()}
        self.river=catmull(RIVER_CONTROL,7)
        self.paths=[catmull(points,3) for points in FOREST_PATHS]
        self.paths += [catmull(points,3) for _,_,_,points in TOWER_PASSAGES]
        self.paths += [catmull(points,3) for points in BOSS_APPROACHES]
        self.paths += [[BASES[t],FOUNTAINS[t]] for t in BASES]
        self.gates=[]
        for center,toward in CRYSTAL_GATES:
            direction=(Vector(toward)-Vector(center)).normalized()
            self.gates.append([tuple(Vector(center)+direction*s) for s in (-7,7)])
        self.paths+=self.gates
        # Повторный запуск заменяет ТОЛЬКО сцену/блоки данных нашего namespace.
        temporary=None
        if bpy.context.window and bpy.context.window.scene.name==SCENE_NAME:
            other=next((s for s in bpy.data.scenes if s.name!=SCENE_NAME),None)
            if other is None:temporary=bpy.data.scenes.new(PREFIX+"Temporary");other=temporary
            bpy.context.window.scene=other
        scene=bpy.data.scenes.get(SCENE_NAME)
        if scene:bpy.data.scenes.remove(scene)
        for obj in list(bpy.data.objects):
            if obj.name.startswith(PREFIX):bpy.data.objects.remove(obj,do_unlink=True)
        for collection in list(bpy.data.collections):
            if collection.name.startswith(PREFIX):bpy.data.collections.remove(collection)
        for blocks in [bpy.data.meshes,bpy.data.curves,bpy.data.materials,bpy.data.cameras,bpy.data.lights,bpy.data.worlds,bpy.data.actions]:
            for block in list(blocks):
                if block.name.startswith(PREFIX) and block.users==0:blocks.remove(block)
        self.scene=bpy.data.scenes.new(SCENE_NAME)
        if bpy.context.window:bpy.context.window.scene=self.scene
        if temporary:bpy.data.scenes.remove(temporary)
        self.scene["generator_version"]="2.0"
        self.scene["seed"]=config.seed
        self.scene["playable_bounds"]=[-100,100,-100,100]
        self.scene["coordinate_system"]="Blender XY ground; Z up"
        self.group("Terrain")
        self.font=None
        for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]:
            if Path(path).exists():
                self.font=bpy.data.fonts.load(path,check_existing=True);break

    def group(self,name):
        if name not in self.groups:
            c=bpy.data.collections.new(PREFIX+name);self.scene.collection.children.link(c);self.groups[name]=c
        self.collection=self.groups[name]
        return self.collection

    @contextmanager
    def root(self,name,position=(0,0,0),category=None,rotation=0,scale=1):
        previous=self.parent
        obj=bpy.data.objects.new(PREFIX+name,None);self.collection.objects.link(obj)
        obj.location=position;obj.rotation_euler.z=rotation;obj.scale=(scale,scale,scale)
        if previous:obj.parent=previous
        if category:obj["category"]=category
        self.parent=obj
        try:yield obj
        finally:self.parent=previous

    def mesh(self,name,vertices,faces,material,indices=None,uv=None,bevel=0,smooth_faces=False):
        mesh=bpy.data.meshes.new(PREFIX+name);mesh.from_pydata(vertices,[],faces);mesh.update()
        materials=[material] if isinstance(material,str) else material
        for name_ in materials:mesh.materials.append(self.materials[name_])
        if indices:
            for p,i in zip(mesh.polygons,indices):p.material_index=i
        if bevel:
            bm=bmesh.new();bm.from_mesh(mesh)
            bmesh.ops.bevel(bm,geom=list(bm.edges),offset=bevel,segments=2,affect="EDGES",clamp_overlap=True)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
        else:
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
        if smooth_faces:
            for face in mesh.polygons:face.use_smooth=True
        layer=mesh.uv_layers.new(name="PaintedUV")
        for loop in mesh.loops:
            co=mesh.vertices[loop.vertex_index].co
            layer.data[loop.index].uv=uv[loop.vertex_index] if uv else (co.x*.19+co.z*.08,co.y*.19+co.z*.05)
        return self.object(name,mesh)

    def object(self,name,data,location=(0,0,0),scale=(1,1,1),rotation=None):
        obj=bpy.data.objects.new(PREFIX+name,data);self.collection.objects.link(obj)
        obj.location=location;obj.scale=scale
        if rotation:obj.rotation_euler=rotation
        if self.parent:obj.parent=self.parent
        return obj

    def box(self,name,p,size,mat,bevel=.08,angle=0):
        key=("box",tuple(size),min(bevel,min(size)*.22),mat)
        if key not in self.cache:
            bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
            for v in bm.verts:v.co.x*=size[0];v.co.y*=size[1];v.co.z*=size[2]
            if key[2]:bmesh.ops.bevel(bm,geom=list(bm.edges),offset=key[2],segments=3,affect="EDGES",clamp_overlap=True)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            mesh=bpy.data.meshes.new(PREFIX+name+" prototype");bm.to_mesh(mesh);bm.free();mesh.materials.append(self.materials[mat]);mesh.update()
            layer=mesh.uv_layers.new(name="PaintedUV")
            for loop in mesh.loops:
                v=mesh.vertices[loop.vertex_index].co;layer.data[loop.index].uv=(v.x*.19+v.z*.08,v.y*.19+v.z*.05)
            self.cache[key]=mesh
        return self.object(name,self.cache[key],p,rotation=(0,0,angle))

    def sphere(self,name,p,size,mat,level=2):
        key=("sphere",level,mat)
        if key not in self.cache:
            bm=bmesh.new();bmesh.ops.create_icosphere(bm,subdivisions=level,radius=1)
            mesh=bpy.data.meshes.new(PREFIX+name+" prototype");bm.to_mesh(mesh);bm.free();mesh.materials.append(self.materials[mat]);mesh.update()
            for f in mesh.polygons:f.use_smooth=True
            self.cache[key]=mesh
        return self.object(name,self.cache[key],p,size)

    def loft(self,name,rings,mat,sides=12,bevel=0,smooth_faces=False):
        verts=[];faces=[]
        # ring=(x,y,z,radius_x,radius_y), цвета/профиль не зашиты в модель.
        for x,y,z,rx,ry in rings:
            verts.extend((x+math.cos(i*2*PI/sides)*rx,y+math.sin(i*2*PI/sides)*ry,z) for i in range(sides))
        for j in range(1,len(rings)):
            for i in range(sides):faces.append(((j-1)*sides+i,(j-1)*sides+(i+1)%sides,j*sides+(i+1)%sides,j*sides+i))
        faces.extend([tuple(reversed(range(sides))),tuple((len(rings)-1)*sides+i for i in range(sides))])
        return self.mesh(name,verts,faces,mat,bevel=bevel,smooth_faces=smooth_faces)

    def cylinder(self,name,p,radius,depth,mat,sides=20,bevel=.06):
        return self.loft(name,[(p[0],p[1],p[2]-depth/2,radius,radius),(p[0],p[1],p[2]+depth/2,radius,radius)],mat,sides,bevel)

    def curve(self,name,points,radius,mat,cyclic=False):
        data=bpy.data.curves.new(PREFIX+name,"CURVE");data.dimensions="3D";data.resolution_u=1;data.bevel_depth=radius;data.bevel_resolution=2
        spline=data.splines.new("POLY");spline.points.add(len(points)-1)
        for p,co in zip(spline.points,points):p.co=(*co,1)
        spline.use_cyclic_u=cyclic;data.materials.append(self.materials[mat])
        return self.object(name,data)

    def ring(self,name,p,radius,tube,mat):
        return self.curve(name,[(p[0]+radius*math.cos(i*2*PI/48),p[1]+radius*math.sin(i*2*PI/48),p[2]) for i in range(48)],tube,mat,True)

    def limb(self,name,a,b,r1,r2,mat,sides=10):
        direction=Vector(b)-Vector(a);length=direction.length
        obj=self.loft(name,[(0,0,0,r1,r1),(0,0,length*.75,r1*.78+r2*.22,r1*.78+r2*.22),(0,0,length,r2,r2)],mat,sides,smooth_faces=True)
        obj.location=a;obj.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
        return obj

    def crystal(self,name,p,radius,height,mat,tilt=(0,0,0)):
        obj=self.loft(name,[(0,0,0,radius*.58,radius*.58),(0,0,height*.13,radius,radius),
                            (0,0,height*.73,radius*.81,radius*.81),(0,0,height,0.005,0.005)],mat,6,bevel=.018)
        obj.location=p;obj.rotation_euler=tilt
        if mat in {"BlueCrystal","RedCrystal","Amethyst","SunGlow"}:
            previous=self.parent;self.parent=obj
            a=-PI/3;normal=Vector((math.cos(a),math.sin(a),0));tangent=Vector((-normal.y,normal.x,0));base=normal*(radius*.89+.026)
            pts=[tuple(base-tangent*radius*.045+Vector((0,0,height*.25))),tuple(base+tangent*radius*.018+Vector((0,0,height*.25))),tuple(base*.86+Vector((0,0,height*.69)))]
            self.mesh("Inset crystal refracted facet",pts,[(0,1,2)],"CrystalEdge")
            self.parent=previous
        return obj

    def text(self,name,text,p,size=1.7,mat="Ink",rotation=(0,0,0)):
        if not self.cfg.labels:return None
        data=bpy.data.curves.new(PREFIX+name,"FONT");data.body=text;data.align_x="CENTER";data.align_y="CENTER";data.size=size;data.extrude=.003
        if self.font:data.font=self.font
        data.materials.append(self.materials[mat]);return self.object(name,data,p,rotation=rotation)

    def height(self,x,y):
        p=(x,y);rd=route_distance(p,self.river)
        if rd<self.cfg.river_half_width+1.5:
            return -2.4*(1-smooth(self.cfg.river_half_width-.4,self.cfg.river_half_width+1.5,rd))
        return 0.0  # Visual walkable ground is flat; only the non-walkable river bed is recessed.

    def clear_for_foliage(self,p,radius=1):
        if max(abs(p[0]),abs(p[1]))>95:return False
        if any(math.dist(p,q)<9+radius for q in FOUNTAINS.values()):return False
        if min(route_distance(p,r) for r in BOSS_APPROACHES)<6+radius:return False
        if min(route_distance(p,r) for r in self.lanes.values())<self.cfg.road_width/2+radius+1.4:return False
        if route_distance(p,self.river)<self.cfg.river_half_width+radius+1.2:return False
        if min(route_distance(p,r) for r in self.paths)<2.1+radius:return False
        if any(math.dist(p,q)<11.5+radius for q in CLEARINGS.values()):return False
        if any(math.dist(p,q)<15.8+radius for q in list(BASES.values())+list(BOSSES.values())):return False
        if any(math.dist(p,q)<5.3+radius for _,_,q in CAMPS):return False
        if any(math.dist(p,(x,y))<3.3+radius for lanes in TOWERS.values() for entries in lanes.values() for _,x,y in entries):return False
        if any(math.dist(p,q)<3.1+radius for q,_ in CRYSTAL_GATES):return False
        if any(math.dist(p,q)<14+radius for _,q in ENERGY_BRIDGES):return False
        return True

# -----------------------------------------------------------------------------
# 2. Hand-painted/stylized PBR: цветовая растяжка, мазки шума, мягкий микрорельеф.
# -----------------------------------------------------------------------------
def painted_material(ctx,name,dark,light,roughness=.8,metallic=0,emission=0,alpha=1):
    mat=bpy.data.materials.new(PREFIX+name);mat.use_nodes=True
    mat.diffuse_color=(*srgb(light),alpha)
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    output=nodes.new("ShaderNodeOutputMaterial");shader=nodes.new("ShaderNodeBsdfPrincipled")
    shader.location=(520,80);output.location=(800,80)
    links.new(shader.outputs["BSDF"],output.inputs["Surface"])
    coords=nodes.new("ShaderNodeTexCoord");coords.location=(-850,150)
    noise=nodes.new("ShaderNodeTexNoise");noise.inputs["Scale"].default_value=2.8;noise.inputs["Detail"].default_value=2.5;noise.inputs["Roughness"].default_value=.7;noise.location=(-630,150)
    links.new(coords.outputs["Generated"],noise.inputs["Vector"])
    ramp=nodes.new("ShaderNodeValToRGB");ramp.location=(-370,180);ramp.color_ramp.elements[0].position=.17;ramp.color_ramp.elements[0].color=(*srgb(dark),1);ramp.color_ramp.elements[1].position=.82;ramp.color_ramp.elements[1].color=(*srgb(light),1)
    links.new(noise.outputs["Fac"],ramp.inputs["Fac"]);links.new(ramp.outputs["Color"],shader.inputs["Base Color"])
    set_input(shader,"Roughness",roughness);set_input(shader,"Metallic",metallic);set_input(shader,"Alpha",alpha)
    if emission:
        links.new(ramp.outputs["Color"],shader.inputs.get("Emission Color") or shader.inputs["Emission"])
        set_input(shader,"Emission Strength",emission)
    if name not in {"BlueCrystal","RedCrystal","Amethyst","SunGlow","BlueEnergy","GoldEnergy"}:
        bump=nodes.new("ShaderNodeBump");bump.inputs["Strength"].default_value=.16;bump.inputs["Distance"].default_value=.065;links.new(noise.outputs["Fac"],bump.inputs["Height"]);links.new(bump.outputs["Normal"],shader.inputs["Normal"])
    if alpha<1:
        if hasattr(mat,"surface_render_method"):mat.surface_render_method="DITHERED"
        elif hasattr(mat,"blend_method"):mat.blend_method="BLEND"
    ctx.materials[name]=mat
    return mat


def water_material(ctx,name,dark,light,outer=False):
    mat=painted_material(ctx,name,dark,light,.17,.12,.20 if outer else .16)
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
    tex=nodes.new("ShaderNodeTexCoord");mapping=nodes.new("ShaderNodeMapping");mapping.name="Animated water flow"
    links.new(tex.outputs["UV"],mapping.inputs["Vector"])
    driver=mapping.inputs["Location"].driver_add("default_value",1).driver;driver.expression="-frame/95.0"
    noise=next(n for n in nodes if n.type=="TEX_NOISE");links.new(mapping.outputs["Vector"],noise.inputs["Vector"]);noise.inputs["Scale"].default_value=4.5
    wave=nodes.new("ShaderNodeTexWave");wave.wave_type="BANDS";wave.bands_direction="X";wave.inputs["Scale"].default_value=5;wave.inputs["Distortion"].default_value=4.8;wave.inputs["Detail"].default_value=2.5;links.new(mapping.outputs["Vector"],wave.inputs["Vector"])
    bump=next((n for n in nodes if n.type=="BUMP"),None)
    if bump:links.new(wave.outputs["Color"],bump.inputs["Height"]);bump.inputs["Distance"].default_value=.055;bump.inputs["Strength"].default_value=.28
    set_input(shader,"Coat Weight",.45,"Clearcoat");set_input(shader,"Coat Roughness",.12,"Clearcoat Roughness")
    return mat


def create_materials(ctx):
    specs={
        "Grass":("427C38","A0BF5B",.92,0,0), "Moss":("387F3D","A1C75A",.9,0,0),
        "Earth":("695035","B49663",.98,0,0), "EarthEdge":("5B4939","957449",.93,0,0),
        "Lane":("B6A185","E6D5B7",.76,0,0), "LaneLight":("C3AF93","EDDFC6",.75,0,0),
        "LaneWarm":("A9967E","D6C0A5",.78,0,0), "LaneJoint":("655E50","9B8D70",.95,0,0),
        "Stone":("6B8077","BDCAAA",.85,0,0), "Marble":("C1C8B4","FFF3D6",.58,.06,0),
        "StoneDark":("212336","534454",.73,.15,0), "Obsidian":("161625","3C2A4F",.29,.38,0),
        "Gold":("9C6A25","FFD371",.38,.72,0), "Bronze":("583E31","BD8651",.47,.65,0),
        "Wood":("3D3025","997348",.92,0,0),
        "CrimsonStone":("311A29","8E4550",.65,.10,0), "CrystalEdge":("93CFEA","E7FAFF",.18,.12,1.15),
        "DawnGlow":("E98518","FFD990",.22,.08,2.1), "DuskGlow":("7116B0","FA57E3",.22,.12,2.2),
        "HealGlow":("24B991","A7F8D3",.3,.02,.7), "HeroBlue":("233E78","528ED0",.66,.15,0),
        "HeroRed":("6A233A","BF5260",.66,.15,0),
        "GrassBlade":("4E8D39","BAD36A",.88,0,0), "FlowerBlue":("597BB9","BCDEF1",.72,0,.05),
        "FlowerCream":("D0AB5A","FFF2AD",.73,0,0),
        "PineDark":("143D31","296A43",.94,0,0), "Pine":("246C3F","4C9250",.9,0,0),
        "PineLight":("468644","87B65B",.87,0,0), "Bush":("4B8D2E","B8D94C",.89,0,0),
        "BushTip":("85AD35","E0EA72",.84,0,0),
        "BlueCrystal":("086AAB","39CFFF",.20,.16,2.5),
        "RedCrystal":("A7092D","FF3C55",.20,.15,1.45),
        "Amethyst":("5825A3","BD54F6",.22,.22,1.45),
        "SunGlow":("D99020","FFF0AC",.22,.15,2.0),
        "GoldEnergy":("DFAD35","FFF3B2",.24,.05,2.2),
        "BlueEnergy":("287FCA","9BEDFF",.15,.05,1.7),
        "Foam":("79D3DB","DBFFF2",.33,0,.4), "Ink":("182C30","2F4642",.9,0,0),
        "Wolf":("88A0B1","E2E7E1",.88,0,0), "Fur":("5E3926","A87948",.92,0,0),
        "FurDark":("342A27","6A4933",.94,0,0), "Ivory":("C2BFA5","FFF0D1",.56,.05,0),
        "PurpleHide":("382043","9461A9",.63,.05,0), "BlueHide":("365873","79B4CC",.72,.05,0),
        "LavaRock":("3E303C","89715B",.87,.05,0), "Lava":("DD3A12","FFB638",.4,0,1.8),
        "Spirit":("2E7881","97EDBC",.7,.05,.3), "Petal":("704E96","CE9BCE",.76,0,0),
    }
    for name,(dark,light,rough,metal,emission) in specs.items():painted_material(ctx,name,dark,light,rough,metal,emission,.46 if name=="BlueEnergy" else 1)
    water_material(ctx,"RiverWater","057C89","24B7B1")
    water_material(ctx,"SkyWater","228FBD","78D9F1",True)
    create_painted_textures(ctx)

# -----------------------------------------------------------------------------
# 3. Террейн, дорожки, река, арочные мосты, водопады.
# -----------------------------------------------------------------------------
def create_terrain(ctx):
    ctx.group("Terrain");n=ctx.cfg.terrain_cells;vertices=[];faces=[]
    for j in range(n+1):
        y=-100+200*j/n
        for i in range(n+1):
            x=-100+200*i/n;vertices.append((x,y,ctx.height(x,y)))
    for j in range(n):
        for i in range(n):
            k=j*(n+1)+i;faces.append((k,k+1,k+n+2,k+n+1))
    ground=ctx.mesh("PlayableTerrain_200x200",vertices,faces,"Grass",smooth_faces=True)
    bm=bmesh.new();bm.from_mesh(ground.data);bm.normal_update();bmesh.ops.reverse_faces(bm,faces=[f for f in bm.faces if f.normal.z<0]);bm.to_mesh(ground.data);bm.free();ground.data.update()
    ground["category"]="playable_terrain";ground["width"]=200;ground["height"]=200
    # Вертикальная толща острова — отдельный меш, не растягивает игровую землю.
    for side in range(4):
        verts=[];fs=[]
        for i in range(n+1):
            t=-100+200*i/n;x,y=(t,-100) if side==0 else (100,t) if side==1 else (-t,100) if side==2 else (-100,-t)
            verts.extend([(x,y,ctx.height(x,y)),(x,y,-20)])
            if i:fs.append((2*i-2,2*i-1,2*i+1,2*i))
        ctx.mesh("Layered cliff earth side",verts,fs,"Stone")
    ctx.group("Backdrop")
    ctx.mesh("Outer blue lake",[(-145,-145,-22),(145,-145,-22),(145,145,-22),(-145,145,-22)],[(0,1,2,3)],"SkyWater",uv=[(0,0),(14,0),(14,14),(0,14)])


def add_prism(vertices,faces,quad,bottom,top):
    k=len(vertices);vertices.extend([(x,y,bottom) for x,y in quad]+[(x,y,top) for x,y in quad])
    faces.extend([(k+3,k+2,k+1,k),(k+4,k+5,k+6,k+7),
                  (k,k+1,k+5,k+4),(k+1,k+2,k+6,k+5),(k+2,k+3,k+7,k+6),(k+3,k,k+4,k+7)])


def create_path(ctx,points,width,material="Earth",name="Woodland trail"):
    points=path_samples(points,1.3);verts=[];faces=[]
    # Разные тропы могут пересекаться: миллиметровый сдвиг убирает coplanar faces.
    surface_z=.10137+ctx.path_layer*.000531;ctx.path_layer+=1
    for i,p in enumerate(points):
        a=points[max(0,i-1)];b=points[min(i+1,len(points)-1)];d=Vector(b)-Vector(a);d.normalize();n=Vector((-d.y,d.x))
        for side in [-1,1]:verts.append((p[0]+n.x*width*.5*side,p[1]+n.y*width*.5*side,surface_z))
        if i:
            q=len(verts)-4;mid=((points[i-1][0]+p[0])*.5,(points[i-1][1]+p[1])*.5)
            if route_distance(mid,ctx.river)>ctx.cfg.river_half_width+.15:faces.append((q,q+2,q+3,q+1))
    return ctx.mesh(name,verts,faces,material)


def create_lane(ctx,name,points):
    ctx.group("Roads");w=ctx.cfg.road_width;sample=path_samples(points,1.75)
    create_path(ctx,points,w+.5,"LaneJoint",name+" road foundation")
    groups=[([],[]) for _ in range(3)];columns=6;curb_v=[];curb_f=[]
    layer_z={"Top":0,"Mid":.009,"Bot":.018}[name]
    for row,(a,b) in enumerate(zip(sample,sample[1:])):
        d=Vector(b)-Vector(a);d.normalize();middle=(Vector(a)+Vector(b))*.5
        ta=(Vector(b)-Vector(sample[max(0,row-1)])).normalized();tb=(Vector(sample[min(len(sample)-1,row+2)])-Vector(a)).normalized()
        na=Vector((-ta.y,ta.x));nb=Vector((-tb.y,tb.x))
        if route_distance(middle,ctx.river)<ctx.cfg.river_half_width+.65:continue
        for col in range(columns):
            lo=-w/2+col*w/columns;hi=lo+w/columns
            q=[Vector(a)+na*lo,Vector(b)+nb*lo,Vector(b)+nb*hi,Vector(a)+na*hi]
            c=sum(q,Vector((0,0)))/4;q=[tuple(c+(p-c)*.956) for p in q]
            index=(col+int(middle.x*7+middle.y*3))%3;vs,fs=groups[index];add_prism(vs,fs,q,.08+layer_z,.30+layer_z)
        for side in [-1,1]:
            lo=side*(w/2+.04);hi=side*(w/2+.47)
            q=[Vector(a)+na*lo,Vector(b)+nb*lo,Vector(b)+nb*hi,Vector(a)+na*hi]
            c=sum(q,Vector((0,0)))/4;q=[tuple(c+(v-c)*.96) for v in q]
            add_prism(curb_v,curb_f,q,.10+layer_z,.39+layer_z)
        # Отдельные инкрустированные сегменты светящейся золотой оси.
        ctx.curve(name+" divine center inlay",[(a[0],a[1],.324+layer_z),(b[0],b[1],.324+layer_z)],.075,"SunGlow")
    if curb_v:ctx.mesh(name+" hand cut edging stones",curb_v,curb_f,"LaneLight",bevel=.035)
    for mat,(vertices,faces) in zip(["Lane","LaneLight","LaneWarm"],groups):
        if vertices:ctx.mesh(name+" individually bevelled pavers",vertices,faces,mat,bevel=.035)


def create_river(ctx):
    ctx.group("River");points=path_samples(ctx.river,1.0);vertices=[];uv=[];faces=[];travel=0
    for i,p in enumerate(points):
        a=points[max(0,i-1)];b=points[min(i+1,len(points)-1)];d=(Vector(b)-Vector(a)).normalized();normal=Vector((-d.y,d.x))
        if i:travel+=math.dist(points[i-1],p)
        for j in range(5):
            t=j/4;s=(t-.5)*2;vertices.append((p[0]+normal.x*s*ctx.cfg.river_half_width,p[1]+normal.y*s*ctx.cfg.river_half_width,-.74-abs(s)*.04));uv.append((t,travel*.065))
        if i:
            for j in range(4):k=(i-1)*5+j;faces.append((k,k+5,k+6,k+1))
    water=ctx.mesh("Turquoise diagonal living river",vertices,faces,"RiverWater",uv=uv,smooth_faces=True);water["category"]="river"
    # Пенистые полоски следуют руслу по настоящим ключам, а не одной линейной оси.
    length=route_length(points)
    for i in range(58):
        x=math.sin(i*2.39)*2.8;shape=[(x+.07*math.sin(j*1.5),-.45+j*.18,0) for j in range(6)]
        obj=ctx.curve("Animated river foam",shape,.028,"Foam")
        for frame in range(1,ctx.cfg.frames+2,12):
            s=(length*i/58+(frame-1)*.075)%length;p=route_sample(points,s);q=route_sample(points,min(length,s+.3));obj.location=(p[0],p[1],-.69);obj.rotation_euler.z=-math.atan2(q[0]-p[0],q[1]-p[1]);obj.keyframe_insert("location",frame=frame);obj.keyframe_insert("rotation_euler",frame=frame)
        for curve in action_curves(obj):
            for key in curve.keyframe_points:key.interpolation="LINEAR"
            curve.modifiers.new("CYCLES")


def create_bridge(ctx,name,position,energy=None):
    ctx.group('Bridges');width=5.8 if energy else 9.4;span=22 if energy else 18.5
    with ctx.root(name,(*position,0),'energy_bridge' if energy else 'stone_bridge',rotation=-PI/4) as root:
        root['bridge_kind']=energy or 'stone';root['passage_width']=width;root['span']=span
        root['physics_y']=0
        if energy:
            root['dynamic_index']=0 if energy=='dawn' else 1;root['starts_closed']=True
            root['first_open_seconds']=120;root['period_seconds']=120;root['warning_seconds']=15
            stone='Marble' if energy=='dawn' else 'Obsidian';metal='Gold' if energy=='dawn' else 'Bronze';glow='DawnGlow' if energy=='dawn' else 'DuskGlow'
            with ctx.root('Dynamic forest bridge deck',(0,0,0)):
                for j in range(29):
                    y=-span/2+(j+.5)*span/29;z=.22+.50*(1-(y/(span/2))**2)
                    for k in range(4):ctx.box('Divine forest bridge carved stone tile',((k-1.5)*width/4,y,z),(width/4-.04,span/29-.04,.20),stone,.045)
                    ctx.box('Forest bridge luminous rune spine',(0,y,z+.115),(.11,span/29*.86,.025),glow,.01)
                for side in [-1,1]:
                    line=[(side*(width/2+.04),-span/2+i*span/40,.82+.50*(1-((-span/2+i*span/40)/(span/2))**2)) for i in range(41)]
                    ctx.curve('Forest bridge arched metallic rail',line,.095,metal)
                    for j in range(10):
                        y=-span/2+j*span/9;z=.22+.50*(1-(y/(span/2))**2)
                        ctx.box('Forest bridge detailed parapet post',(side*(width/2+.04),y,z+.37),(.30,.35,.77),stone,.055)
                        ctx.crystal('Forest bridge rune lantern',(side*(width/2+.04),y,z+.77),.10,.35,glow)
                for y in [-6,0,6]:
                    z=.35+.50*(1-(y/(span/2))**2);ctx.ring('Forest bridge engraved celestial seal',(0,y,z),.48,.027,glow)
            for side in [-1,1]:
                for end in [-1,1]:
                    x=side*(width/2+.28);y=end*span/2;ctx.cylinder('Forest bridge permanent bank pedestal',(x,y,.38),.58,.90,stone,12)
                    ctx.crystal('Forest bridge permanent ward beacon',(x,y,.90),.20,1.1,glow)
            return root
        def z(y):return .24+1.5*max(0,1-(y/(span/2))**2)
        vertices=[];faces=[]
        for j in range(25):
            a=-span/2+j*span/25;b=-span/2+(j+1)*span/25
            for k in range(6):
                x=-width/2+(k+.5)*width/6;q=[(x-width/12+.035,a+.025),(x+width/12-.035,a+.025),(x+width/12-.035,b-.025),(x-width/12+.035,b-.025)];n=len(vertices)
                vertices.extend([(xx,yy,z(yy)-.28) for xx,yy in q]+[(xx,yy,z(yy)) for xx,yy in q]);faces.extend([(n+3,n+2,n+1,n),(n+4,n+5,n+6,n+7),(n,n+1,n+5,n+4),(n+1,n+2,n+6,n+5),(n+2,n+3,n+7,n+6),(n+3,n,n+4,n+7)])
        ctx.mesh('Stone arch bridge bevelled deck',vertices,faces,'LaneLight',bevel=.04)
        for side in [-1,1]:
            points=[(side*(width/2+.1),-span/2+i*span/40,z(-span/2+i*span/40)-.42) for i in range(41)]
            ctx.curve('Stone structural arch rib',points,.38,'Stone');ctx.curve('Golden bridge handrail',[(x,y,zz+1.55) for x,y,zz in points],.085,'Gold')
            for j in range(9):
                y=-span/2+j*span/8;ctx.box('Bridge parapet carved post',(side*(width/2+.1),y,z(y)+.44),(.32,.38,.90),'Marble',.055)
        ctx.curve('Bridge divine center line',[(0,-span/2+i*span/40,z(-span/2+i*span/40)+.025) for i in range(41)],.07,'SunGlow')
        return root


def create_waterfall(ctx,name,points,width=5.0):
    ctx.group("Waterfalls");path=catmull(points,7);verts=[];uv=[];faces=[];travel=0
    for i,p in enumerate(path):
        a=path[max(0,i-1)];b=path[min(i+1,len(path)-1)];dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy) or 1;nx,ny=-dy/l,dx/l
        if i:travel+=math.dist(path[i-1],p)
        for j in range(5):t=j/4;verts.append((p[0]+nx*(t-.5)*width,p[1]+ny*(t-.5)*width,p[2]+.05*math.sin(i*1.2+j)));uv.append((t,travel*.1))
        if i:
            for j in range(4):k=(i-1)*5+j;faces.append((k,k+5,k+6,k+1))
    obj=ctx.mesh(name,verts,faces,"SkyWater",uv=uv,smooth_faces=True);obj["category"]="waterfall"
    for offset in [-.34,.28]:ctx.curve("Cascade bright falling lace",[(p[0]+offset*width,p[1]-.045,p[2]+.07) for p in path],.048,"Foam")
    end=points[-1]
    for j in range(4):
        ring=ctx.ring("Animated waterfall bubbling ring",(end[0],end[1],end[2]+.08+j*.018),1.6+j*.4,.038,"Foam")
        for axis in range(3):ring.driver_add("scale",axis).driver.expression=f".35+((frame+{j*13})%58)/58.0"
    for j in range(14):
        drop=ctx.sphere("Animated waterfall spray",(end[0],end[1],end[2]+.3),(.11,.12,.30),"Foam",1);phase=j*7
        drop.driver_add("location",0).driver.expression=f"{end[0]:.4f}+{math.sin(j*2.4)*2.5:.4f}*((frame+{phase})%36)/36.0"
        drop.driver_add("location",1).driver.expression=f"{end[1]:.4f}+{math.cos(j*2.4)*2:.4f}*((frame+{phase})%36)/36.0"
        drop.driver_add("location",2).driver.expression=f"{end[2]+.2:.4f}+3.2*sin(pi*((frame+{phase})%36)/36.0)"


def create_rock(ctx,name,p,scale=(2,2,3),material="Stone",seed=0):
    rings=[]
    for i,(z,r) in enumerate([(-.5,.72),(-.3,1),(.12,.92),(.19,.78),(.61,.76),(.72,.48)]):
        rings.append((math.sin(seed+i)*.12*scale[0],math.cos(seed+i)*.1*scale[1],z*scale[2],r*scale[0],r*scale[1]))
    obj=ctx.loft(name,rings,material,8,bevel=.08);obj.location=p;obj.rotation_euler.z=seed*.71
    return obj


def create_cliffs_and_waterfalls(ctx):
    ctx.group("Backdrop")
    # Просветы в скалах оставляют полосу воды видимой по всей длине водопада.
    flows=[("WestUpper",[(-99,49,-.4),(-104,48,-1.6),(-110,45,-13),(-116,43,-21.8)]),
           ("WestLower",[(-99,-35,-.4),(-105,-36,-2),(-110,-39,-14),(-116,-41,-21.8)]),
           ("SouthWest",[(-30,-99,-.4),(-31,-105,-1.8),(-33,-112,-13),(-35,-118,-21.8)]),
           ("SouthEast",[(40,-99,-.4),(42,-106,-2),(45,-112,-14),(47,-118,-21.8)]),
           ("EastLower",[(99,-49,-.4),(105,-50,-1.8),(111,-52,-13),(118,-53,-21.8)]),
           ("EastUpper",[(99,44,-.4),(105,45,-1.7),(111,47,-14),(118,49,-21.8)])]
    starts=[p[0][:2] for _,p in flows]
    for side in range(4):
        for j in range(35):
            t=-100+j*200/34;x,y=(t,-101) if side==0 else (101,t) if side==1 else (t,101) if side==2 else (-101,t)
            if any(math.dist((x,y),p)<5.6 for p in starts):continue
            seed=j+side*31;zz=-11.8+math.sin(seed*1.93)*.8+(y-x)/200*3.8;height=16.0+(j%3)*.5
            create_rock(ctx,"Weathered continuous island escarpment",(x,y,zz),(5.6+(j%2)*.6,5.2,height),seed=seed)
            if j%3==0:
                offset=Vector((x,y)).normalized()*7
                create_rock(ctx,"Lower buttress geological terrace",(x+offset.x,y+offset.y,-16+(seed+4)*.004),(6.4,5.7,12),seed=seed+4)
    for name,points in flows:create_waterfall(ctx,name,points)

# -----------------------------------------------------------------------------
# 4. Сосны, кусты, руины, расчищенные поляны и затворы коротких проходов.
# -----------------------------------------------------------------------------
def create_tree(ctx,position,height=9.0,variant=0):
    key=("pine",variant%5)
    if key not in ctx.cache:
        verts=[];faces=[];indices=[];n=20
        for tier in range(6):
            z=1.8+tier*1.09;r=3.0-tier*.39;phase=tier*.34+variant*.21;start=len(verts)
            for dz,rr in [(0,.81),(.15,1),(.67,.65),(1.55,.28),(2.35,.012)]:
                for j in range(n):
                    angle=j*2*PI/n+phase;radius=r*rr*(1 if j%2==0 else .66)*(1+.07*math.sin(j*3+variant))
                    verts.append((math.cos(angle)*radius,math.sin(angle)*radius,z+dz+.08*math.sin(j*2.1)))
            faces.append(tuple(start+j for j in reversed(range(n))));indices.append(0)
            for row in range(4):
                for j in range(n):
                    faces.append((start+row*n+j,start+row*n+(j+1)%n,start+(row+1)*n+(j+1)%n,start+(row+1)*n+j));indices.append(1 if j%4==0 else 2 if row<2 else 3)
        start=len(verts)
        for z,r in [(0,.27),(1.4,.22),(6.9,.11)]:
            verts.extend((math.cos(j*2*PI/10)*r,math.sin(j*2*PI/10)*r,z) for j in range(10))
        for row in range(2):
            for j in range(10):faces.append((start+row*10+j,start+row*10+(j+1)%10,start+(row+1)*10+(j+1)%10,start+(row+1)*10+j));indices.append(0)
        for branch in range(18):
            a=branch*2.39996+variant*.21;z=2.35+(branch%5)*1.03;r=2.7-(branch%5)*.36;start=len(verts)
            for side,dist,dz in [(-1,.25,.25),(-1,.85,-.1),(0,1.12,-.30),(1,.85,-.1),(1,.25,.25),(0,.6,.32)]:
                verts.append((math.cos(a)*r*dist-math.sin(a)*side*.24,math.sin(a)*r*dist+math.cos(a)*side*.24,z+dz))
            for f in [(0,1,5),(1,2,5),(2,3,5),(3,4,5),(4,0,5)]:faces.append(tuple(start+i for i in f));indices.append(2 if branch%3 else 3)
        for j in range(5):
            a=j*2*PI/5+variant*.1;start=len(verts)
            for da,r,z in [(-.12,.22,.02),(-.20,.65,0),(.20,.65,0),(.12,.22,.02),(0,.24,.62)]:verts.append((math.cos(a+da)*r,math.sin(a+da)*r,z))
            for f in [(0,1,4),(1,2,4),(2,3,4),(3,0,4)]:faces.append(tuple(start+i for i in f));indices.append(0)
        proto=ctx.mesh("Lush pine prototype",verts,faces,["Wood","PineDark","Pine","PineLight"],indices)
        ctx.cache[key]=proto.data;bpy.data.objects.remove(proto,do_unlink=True)
    obj=ctx.object("Forest pine",ctx.cache[key],position,(height/9,height/9,height/9),rotation=(0,0,variant*.71))
    obj["category"]="tree";obj["trunk_radius"]=height*.03
    obj.driver_add("rotation_euler",1).driver.expression=f".007*sin(frame*.027+{variant*.57})"
    return obj


def create_bush(ctx,position,scale=1.0,variant=0):
    key=("bush",variant%4)
    if key not in ctx.cache:
        rng=random.Random(510+variant%4);verts=[];faces=[];indices=[]
        for j in range(30):
            a=j*2.39996;r=rng.uniform(.1,1.0);h=rng.uniform(.75,1.5);start=len(verts)
            # Объёмная складка листа: центральный гребень и отогнутый кончик.
            pts=[(-.02,0,0),(-.27,.40,h*.37),(-.19,.81,h*.77),(0,1.12,h),(.19,.81,h*.77),(.27,.40,h*.37),(0,.56,h*.63)]
            for x,y,z in pts:
                y=y*.7+r;verts.append((math.cos(a)*y-math.sin(a)*x,math.sin(a)*y+math.cos(a)*x,z))
            for face in [(0,1,6),(1,2,6),(2,3,6),(3,4,6),(4,5,6),(5,0,6)]:faces.append(tuple(start+i for i in face));indices.append(1 if j%3==0 else 0)
        proto=ctx.mesh("Folded lime foliage prototype",verts,faces,["Bush","BushTip"],indices)
        ctx.cache[key]=proto.data;bpy.data.objects.remove(proto,do_unlink=True)
    obj=ctx.object("Bright ambush bush",ctx.cache[key],position,(scale,scale,scale),rotation=(0,0,variant*.47));obj["category"]="bush";obj["concealment_zone"]=True
    return obj


def create_wall(ctx,name,position,length=5.5,angle=0,broken=False):
    with ctx.root(name,position,"ruin",angle) as root:
        blocks=max(2,round(length/1.15));length=blocks*1.15
        for row in range(3):
            for i in range(blocks):
                if broken and row==2 and i>blocks//2:continue
                x=(i-(blocks-1)/2)*1.15+(row%2)*.10
                ctx.box("Ruin softly chamfered masonry",(x,0,.32+row*.58),(1.10,.86,.54),"Stone",.075)
        for side in [-1,1]:
            x=side*(length/2+.17);ctx.box("Ancient squared terminal pier",(x,0,1.05),(.87,1.10,2.10),"Marble",.10);ctx.box("Golden pier coping",(x,0,2.13),(1.02,1.23,.22),"LaneLight",.05)
        ctx.box("Carved ruin coping",(0,0,1.83),(length+.3,1.01,.22),"LaneLight",.06)
        for j in range(3):ctx.sphere("Moss growing on old stone",(-length*.28+j*length*.24,-.43,1.69),(.36,.13,.16),"Moss",1)
        return root


def create_ruin_arch(ctx,position,angle=0):
    with ctx.root("Antique arch",position,"ruin",angle):
        for side in [-1,1]:
            ctx.cylinder("Ruined fluted column",(side*2.1,0,2.0),.46,4,"Marble",12)
            ctx.box("Classical column capital",(side*2.1,0,4.04),(1.19,1.10,.36),"LaneLight",.07)
            for j in range(8):
                a=j*PI/4;ctx.limb("Column carved flute",(side*2.1+.45*math.cos(a),.45*math.sin(a),.5),(side*2.1+.45*math.cos(a),.45*math.sin(a),3.75),.037,.037,"LaneLight",6)
        for j in range(15):
            a=(j+.5)*PI/15
            ctx.box("Bevelled ancient arch voussoir",(math.cos(a)*2.1,0,4.0+math.sin(a)*2.1),(.48,1.0,.57),"Marble",.065)


def create_clearing(ctx,name,position):
    ctx.group("Clearings")
    with ctx.root("Clearing "+name,(*position,0),"clearing") as root:
        root["radius"]=10.5
        ctx.cylinder("Cleared warm earth",(0,0,.035),10.6,.08,"Earth",64,.015)
        for j in range(18):
            a=j*2*PI/18;ctx.sphere("Clearing boundary pebble",(10.8*math.cos(a),10.8*math.sin(a),.16),(.35,.25,.16),"Stone",1)
        # Clearing names are interface labels, keeping the ground free from text overlays.


def create_forest(ctx):
    ctx.group("Ruins");ruins=[]
    for ci,center in enumerate(CLEARINGS.values()):
        for j in range(8):
            a=j*PI/4+.19;position=(center[0]+14.2*math.cos(a),center[1]+14.2*math.sin(a))
            if not ctx.clear_for_foliage(position,.1):continue
            if any(min(route_distance((position[0]+math.cos(a+PI/2)*off,position[1]+math.sin(a+PI/2)*off),r) for r in ctx.paths)<2.8 for off in [-2.8,0,2.8]):continue
            create_wall(ctx,"Forest clearing wall",(*position,ctx.height(*position)),4.4,a+PI/2,(j+ci)%2==0);ruins.append(position)
    for p,angle in [((-88,24),0),((-9,88),0),((91,10),PI/2),((12,-87),0)]:
        create_ruin_arch(ctx,(*p,ctx.height(*p)),angle)
    ctx.group("Forest");positions=[];attempts=0
    while len(positions)<ctx.cfg.tree_count and attempts<35000:
        attempts+=1
        core=len([q for q in positions if max(abs(q[0]),abs(q[1]))<60])
        limit=59 if core<min(180,int(ctx.cfg.tree_count*.5)) and attempts%4!=0 else 94
        p=(ctx.rng.uniform(-limit,limit),ctx.rng.uniform(-limit,limit))
        if not ctx.clear_for_foliage(p,1.0):continue
        if any(math.dist(p,q)<(3.5 if max(abs(p[0]),abs(p[1]))<60 else 4.4) for q in positions) or any(math.dist(p,q)<4.7 for q in ruins):continue
        positions.append(p);height=ctx.rng.uniform(7.2,10.4);create_tree(ctx,(*p,ctx.height(*p)),height,len(positions)%23)
    # Кусты вдоль границ полян и троп, а не случайно в центре дороги.
    bushes=[]
    for i in range(3500):
        if len(bushes)>=ctx.cfg.bush_count:break
        if i<120:
            center=list(CLEARINGS.values())[i%4];a=i*2.39996;p=(center[0]+ctx.rng.uniform(11.5,14)*math.cos(a),center[1]+ctx.rng.uniform(11.5,14)*math.sin(a))
        else:p=(ctx.rng.uniform(-91,91),ctx.rng.uniform(-91,91))
        if min(route_distance(p,r) for r in ctx.lanes.values())<6.2 or route_distance(p,ctx.river)<5.3:continue
        if any(math.dist(p,c)<10.6 for c in CLEARINGS.values()):continue
        if any(math.dist(p,c)<15.7 for c in list(BASES.values())+list(BOSSES.values())):continue
        if any(math.dist(p,c)<4.1 for _,_,c in CAMPS):continue
        if any(math.dist(p,c)<2.4 for c,_ in CRYSTAL_GATES):continue
        if any(math.dist(p,q)<3.3 for q in bushes):continue
        bushes.append(p);create_bush(ctx,(*p,ctx.height(*p)),ctx.rng.uniform(.9,1.45),len(bushes)%17)
    ctx.registry["trees"]=positions;ctx.registry["bushes"]=bushes
    print(f"FOREST: {len(positions)} trees, {len(bushes)} bushes",flush=True)


def create_crystal_gate(ctx,index,position,toward):
    ctx.group("CrystalGates");direction=(Vector(toward)-Vector(position)).normalized();angle=-math.atan2(direction.x,direction.y)
    with ctx.root(f"CrystalGate {index:02d}",(*position,.10),"crystal_gate",angle) as root:
        root["gate_index"]=index;root["durability"]=24.0;root["respawn_seconds"]=60.0
        root["blocks_shortcut"]=True
        root["side"]="Light" if index in [1,2,3,7] else "Dark"
        root["route_role"]={1:"ambush",2:"hunt",3:"rescue",7:"invasion",4:"ambush",5:"hunt",6:"rescue",8:"invasion"}[index]
        for j,(x,y,z,r,h) in enumerate([(0,0,0,.86,4.6),(-1.0,.10,0,.48,2.9),(.98,.10,0,.54,3.3),(-.40,-.65,0,.36,2.2),(.5,.55,0,.40,2.4)]):
            obj=ctx.crystal("Destructible amethyst shard",(x,y,z),r,h,"Amethyst",(0,(j-2)*.13,j*.28));obj["rest_location"]=list(obj.location);obj["rest_rotation"]=list(obj.rotation_euler);obj["rest_scale"]=list(obj.scale)
        for side in [-1,1]:
            # Стенки обрамляют затвор; сами кристаллы закрывают середину.
            for j in range(2):ctx.box("Crystal narrow passage sidewall",(side*(2.9+j*1.07),0,.55),(1.02,1.4,1.1),"Stone",.10)
            ctx.crystal("Passage flank quartz",(side*3.85,0,1.1),.18,.8,"Amethyst")
        ctx.registry[f"crystal_{index}"]=root
        return root


def damage_crystal(root,amount=4.0,frame=None):
    """Blender-превью разрушения. root — Empty с category='crystal_gate'.
    Игровой контроллер должен отдельно применять коллизии и таймер возрождения.
    """
    if root.get("category")!="crystal_gate":raise ValueError("Expected a crystal gate root")
    if not math.isfinite(amount):raise ValueError("Damage must be finite")
    if amount<=0:return
    previous=float(root.get("durability",24));root["durability"]=max(0,previous-amount)
    if previous<=0 or root["durability"]>0:return
    start=bpy.context.scene.frame_current if frame is None else frame
    for i,obj in enumerate(root.children):
        if "rest_location" not in obj:continue
        obj.location=obj["rest_location"];obj.scale=obj["rest_scale"];obj.rotation_euler=obj["rest_rotation"]
        for path in ["location","scale","rotation_euler"]:obj.keyframe_insert(path,frame=start)
        a=i*2.39996;obj.location+=Vector((math.cos(a)*3,math.sin(a)*3,1.8));obj.rotation_euler.x+=.7;obj.keyframe_insert("location",frame=start+10);obj.keyframe_insert("rotation_euler",frame=start+10)
        obj.location.z-=2;obj.scale=(.001,.001,.001);obj.keyframe_insert("location",frame=start+23);obj.keyframe_insert("scale",frame=start+23)


def restore_crystal(root,frame=None):
    """Анимация появления того же затвора, без пересоздания модели."""
    if root.get("category")!="crystal_gate":raise ValueError("Expected a crystal gate root")
    start=bpy.context.scene.frame_current if frame is None else frame
    root["durability"]=24.0
    for obj in root.children:
        if "rest_location" not in obj:continue
        obj.animation_data_clear();obj.location=obj["rest_location"];obj.rotation_euler=obj["rest_rotation"];obj.scale=(.001,.001,.001);obj.keyframe_insert("scale",frame=start);obj.scale=obj["rest_scale"];obj.keyframe_insert("scale",frame=start+20)

# -----------------------------------------------------------------------------
# 5. Башни, Нексусы и арены. Каждая функция строит независимую модель.
# -----------------------------------------------------------------------------
def create_tower(ctx,team,tier,position,lane="Mid"):
    ctx.group("Towers");light=team=="Light";stone="Marble" if light else "StoneDark";metal="Gold" if light else "Bronze";glow="BlueCrystal" if light else "RedCrystal"
    with ctx.root(f"Tower {team} {lane} T{tier}",(*position,.32),"tower") as root:
        root["team"]=team;root["tier"]=tier;root["lane"]=lane;root["health"]={1:3600,2:4400,3:5400}[tier]
        ctx.loft("Tower bevelled stepped foundation",[(0,0,0,2.55,2.55),(0,0,.28,2.55,2.55),(0,0,.43,2.20,2.20),(0,0,.75,2.20,2.20),(0,0,.85,1.72,1.72)],stone,24,.075)
        ctx.loft("Tower tapered fluted shaft",[(0,0,.78,1.53,1.53),(0,0,1.1,1.43,1.43),(0,0,3.35,1.12,1.12),(0,0,3.75,1.48,1.48),(0,0,4.0,1.58,1.58)],stone,16,.06)
        for z,r in [(.3,2.43),(.85,1.84),(1.12,1.45),(3.65,1.43),(4.04,1.58)]:ctx.ring("Tower chased metallic band",(0,0,z),r,.055,metal)
        for j in range(8):
            a=j*PI/4;x,y=math.cos(a),math.sin(a)
            ctx.limb("Tower carved stone flute",(x*1.42,y*1.42,1.18),(x*1.17,y*1.17,3.30),.075,.06,"LaneLight" if light else "Bronze",8)
            ctx.crystal("Tower inset luminous rune",(x*1.30,y*1.30,2.0),.075,.56,glow)
        with ctx.root("Tower floating focus",(0,0,4.0)) as focus:
            ctx.crystal("Tower floating main crystal",(0,0,.15),.69,3.15,glow)
            for j in range(3):
                a=j*2*PI/3;x,y=math.cos(a),math.sin(a)
                ctx.crystal("Tower orbiting splinter",(x*1.02,y*1.02,.38),.22,1.35,glow,(.12*y,-.12*x,0))
            focus.driver_add("location",2).driver.expression="4.0+.16*sin(frame*.055)"
            focus.driver_add("rotation_euler",2).driver.expression="frame*.006"
        for j in range(3):
            a=j*2*PI/3;x,y=math.cos(a),math.sin(a)
            ctx.curve("Tower sweeping crystal cradle",[(x*1.65,y*1.65,3.60),(x*1.77,y*1.77,4.45),(x*1.29,y*1.29,5.40),(x*.93,y*.93,5.88)],.115,metal)
        ctx.ring("Tower spell focusing halo",(0,0,5.1),1.24,.035,glow)
        ctx.text("Tower tier label",f"T{tier}",(0,-2.0,.045),1.0)
        return root


def create_nexus(ctx,team,position):
    ctx.group("Bases");light=team=="Light";stone="Marble" if light else "CrimsonStone";metal="Gold" if light else "Bronze";glow="BlueCrystal" if light else "RedCrystal"
    with ctx.root("Nexus "+team,(*position,.12),"nexus") as root:
        root["team"]=team
        ctx.cylinder("Nexus plaza round foundation",(0,0,.1),14.1,.35,stone,64,.08)
        # Мраморные ступени и неглубокая чаша фонтана.
        ctx.loft("Royal fountain stepped bowl",[(0,0,.28,7.8,7.8),(0,0,.60,7.8,7.8),(0,0,.8,7.1,7.1),(0,0,1.2,6.7,6.7)],stone,48,.08)
        ctx.cylinder("Nexus turquoise fountain water" if light else "Crimson arcane basin",(0,0,1.24),6.05,.045,"RiverWater" if light else "RedCrystal",64,.01)
        for r in [7.2,10.4,13.55]:ctx.ring("Nexus plaza golden circuit",(0,0,.32 if r>8 else 1.23),r,.065,metal)
        ctx.loft("Nexus inner crystal altar",[(0,0,1.2,2.6,2.6),(0,0,1.8,2.6,2.6),(0,0,2.2,1.9,1.9)],stone,16,.08)
        with ctx.root("Nexus hovering energy",(0,0,2.45)) as focus:
            ctx.crystal("Nexus tall radiant crystal",(0,0,0),1.45,10.2,glow)
            focus.driver_add("location",2).driver.expression="2.45+.20*sin(frame*.035)";focus.driver_add("rotation_euler",2).driver.expression="frame*.0035"
        for j in range(8):
            a=j*PI/4;x,y=math.cos(a),math.sin(a)
            if light:
                ctx.curve("Nexus golden rising arch",[(x*6.8,y*6.8,.8),(x*6.3,y*6.3,4.4),(x*4.5,y*4.5,7.5),(x*2.7,y*2.7,8.2)],.24,metal)
                ctx.cylinder("Marble sanctuary pillar",(x*6.7,y*6.7,2.25),.68,3.4,stone,12)
            else:
                ctx.crystal("Citadel obsidian spire",(x*6.3,y*6.3,.6),.88,6.3+(j%3)*.6,"Obsidian",(y*.17,-x*.17,0))
                ctx.crystal("Citadel burning ember",(x*5.4,y*5.4,3.5),.27,2.1,glow)
            ctx.crystal("Nexus outer ward shard",(x*4.0,y*4.0,1.8),.40,3.2,glow)
        if light:
            for j in range(6):
                a=j*PI/3
                points=[(math.cos(a)*(3.8+t*2.0),math.sin(a)*(3.8+t*2.0),1.3+2.6*math.sin(t*PI)) for t in [i/18 for i in range(19)]]
                ctx.curve("Fountain water arc",points,.055,"SkyWater")
        return root


def create_arena(ctx,name,position,dark=False):
    ctx.group("Arenas");stone="StoneDark" if dark else "LaneLight";trim="Amethyst" if dark else "Gold"
    with ctx.root(name,(*position,.12),"arena") as root:
        ctx.cylinder("Arena raised circular foundation",(0,0,.12),15.6,.65,stone,64,.09)
        verts=[];faces=[]
        for row in range(5):
            lo=1.3+row*2.8;hi=lo+2.74;n=20+row*12
            for j in range(n):
                a=j*2*PI/n+.008;b=(j+1)*2*PI/n-.008
                quad=[(lo*math.cos(a),lo*math.sin(a)),(hi*math.cos(a),hi*math.sin(a)),(hi*math.cos(b),hi*math.sin(b)),(lo*math.cos(b),lo*math.sin(b))]
                add_prism(verts,faces,quad,.42,.58)
        ctx.mesh("Arena individual radial stone sectors",verts,faces,stone,bevel=.045)
        for r in [3.5,7.4,11.1,14.8]:ctx.ring("Arena ornamental sun circuit",(0,0,.64),r,.035,trim)
        for j in range(24):
            a=j*2*PI/24
            approaches=BOSS_APPROACHES[2:4] if dark else BOSS_APPROACHES[:2]
            allowed=[math.atan2(r[-2][1]-position[1],r[-2][0]-position[0]) for r in approaches]
            if any(abs(math.atan2(math.sin(a-v),math.cos(a-v)))<.34 for v in allowed):continue
            x,y=15.1*math.cos(a),15.1*math.sin(a)
            ctx.box("Arena crenellated boundary",(x,y,1.0),(.9,1.6,1.7),stone,.11,a)
            if j%2==0:
                ctx.crystal("Arena perimeter crystal",(x,y,1.9),.28,1.7,"Amethyst" if dark else "SunGlow")
        return root

# -----------------------------------------------------------------------------
# 6. Стилизованные фигуры монстров. Без внешних моделей, каждый вид — своя функция.
# -----------------------------------------------------------------------------
def create_wolf(ctx):
    ctx.sphere("Wolf elongated ribcage",(0,.15,1.6),(.83,1.38,.80),"Wolf")
    ctx.sphere("Wolf proud breast",(0,-.75,1.77),(.76,.76,.91),"Wolf")
    ctx.sphere("Wolf angular head",(0,-1.42,2.36),(.58,.70,.53),"Wolf")
    ctx.sphere("Wolf tapered muzzle",(0,-1.98,2.15),(.35,.56,.26),"Wolf")
    ctx.sphere("Wolf wet nose",(0,-2.47,2.18),(.24,.14,.15),"Obsidian",1)
    for side in [-1,1]:
        for y in [-.77,1.02]:
            ctx.limb("Wolf upper leg",(side*.52,y,1.4),(side*.64,y+.13,.66),.23,.16,"Wolf")
            ctx.limb("Wolf lower leg",(side*.64,y+.13,.66),(side*.67,y-.02,.22),.14,.10,"Wolf")
            ctx.sphere("Wolf paw",(side*.67,y-.14,.15),(.23,.35,.17),"Ivory",1)
        ctx.crystal("Wolf sharply pricked ear",(side*.42,-1.26,2.7),.23,.83,"Wolf",(.10,side*.18,0))
        ctx.sphere("Wolf crystal blue eye",(side*.44,-1.84,2.5),(.09,.11,.07),"BlueCrystal",1)
        for j in range(5):
            ctx.crystal("Wolf folded neck fur",(side*(.52+j*.025),-.99+j*.20,1.76),.16,.60,"Ivory",(.6,side*.7,0))
    ctx.curve("Wolf expressive sweeping tail",[(0,1.2,1.7),(.15,2.0,1.8),(.40,2.55,1.45),(.55,2.85,1.12)],.23,"Wolf")


def create_spider(ctx,giant=False):
    body="PurpleHide" if giant else "BlueHide"
    ctx.sphere("Spider broad abdomen",(0,.67,1.45),(1.02,1.40,.80),body)
    ctx.sphere("Spider cephalothorax",(0,-.68,1.28),(.76,.77,.57),"Obsidian")
    for side in [-1,1]:
        for j in range(4):
            y=-.98+j*.60;knee=(side*(2.0+math.sin(j)*.3),y+(j-1.5)*.36,1.7)
            ctx.limb("Spider proximal articulated leg",(side*.60,y,1.35),knee,.15,.11,body)
            ctx.limb("Spider tapering distal leg",knee,(side*(2.6+math.sin(j)*.22),y+(j-1.5)*.7,.08),.11,.015,"Obsidian")
        ctx.curve("Spider ivory mandible",[(side*.26,-1.20,1.1),(side*.44,-1.7,.88),(side*.15,-1.75,.71)],.10,"Ivory")
        for j in range(3):ctx.sphere("Spider luminous eye",(side*(.16+j*.18),-1.31+j*.10,1.57-j*.04),(.10,.075,.10),"RedCrystal",1)
    for j in range(5):ctx.crystal("Spider dorsal amethyst marking",(0,.1+j*.34,2.12),.12,.23,"Amethyst")


def create_elemental(ctx):
    ctx.sphere("Elemental luminous heart",(0,0,1.7),(.68,.55,1.13),"BlueCrystal")
    for j in range(9):
        a=j*2.39996;r=1.05 if j%2 else .85;z=.55+(j%3)*.78
        obj=ctx.sphere("Orbiting elemental stone",(math.cos(a)*r,math.sin(a)*r,z),(.41,.32,.52),"Stone",1)
        obj.driver_add("location",2).driver.expression=f"{z:.3f}+.12*sin(frame*.05+{j})"
    for side in [-1,1]:ctx.sphere("Elemental white eye",(side*.19,-.54,2.12),(.075,.06,.11),"SunGlow",1)
    ctx.ring("Elemental levitation sigil",(0,0,.20),1.20,.025,"BlueCrystal")


def create_boar(ctx):
    ctx.sphere("Boar massive rounded barrel",(0,.1,1.32),(1.00,1.52,.90),"FurDark")
    ctx.sphere("Boar lowered head",(0,-1.27,1.25),(.77,.91,.71),"Fur")
    ctx.sphere("Boar broad snout",(0,-2.0,1.0),(.50,.36,.35),"FurDark")
    for side in [-1,1]:
        for y in [-.8,1.0]:
            ctx.limb("Boar short powerful leg",(side*.65,y,1.13),(side*.70,y,.19),.23,.15,"Fur")
            ctx.box("Boar cloven hoof",(side*.70,y-.08,.15),(.34,.49,.29),"Obsidian",.07)
        ctx.curve("Boar curved ivory tusk",[(side*.46,-1.83,.89),(side*.77,-2.09,1.0),(side*.80,-2.11,1.40)],.10,"Ivory")
        ctx.crystal("Boar alert ear",(side*.60,-1.04,1.75),.24,.55,"Fur",(.2,side*.45,0))
        ctx.sphere("Boar amber eye",(side*.53,-1.77,1.50),(.095,.09,.075),"SunGlow",1)
    for j in range(7):ctx.crystal("Boar back bristled mane",(0,-.7+j*.34,1.97),.17,.48,"Fur",(.50,0,0))


def create_golem(ctx,gold=False,solar=False):
    rock="Marble" if solar else "Gold" if gold else "BlueHide";trim="Gold" if solar or gold else "Stone"
    glow="SunGlow" if solar or gold else "BlueCrystal"
    ctx.sphere("Golem heavy faceted torso",(0,0,2.73),(1.46,.85,1.55),rock,2)
    ctx.sphere("Golem lower stone hips",(0,.05,1.48),(1.00,.70,.57),trim,1)
    ctx.sphere("Golem sculpted stone head",(0,-.05,4.12),(.70,.68,.77),rock,2)
    ctx.sphere("Golem inset energy breast core",(0,-.81,2.88),(.58,.16,.66),glow,2)
    for side in [-1,1]:
        ctx.sphere("Golem rounded shoulder boulder",(side*1.57,0,3.36),(.83,.82,.86),trim,2)
        ctx.limb("Golem massive upper arm",(side*1.62,0,3.18),(side*2.06,-.18,2.18),.51,.43,rock)
        ctx.sphere("Golem colossal knuckled fist",(side*2.13,-.32,1.69),(.67,.72,.71),rock,2)
        for j in range(3):ctx.sphere("Golem separated stone knuckle",(side*2.13+(j-1)*.30,-.94,1.78),(.19,.16,.24),trim,1)
        ctx.limb("Golem sturdy thigh",(side*.67,.03,1.45),(side*.79,-.04,.58),.45,.39,rock)
        ctx.sphere("Golem broad stone foot",(side*.80,-.31,.31),(.61,.85,.34),trim,2)
        ctx.box("Golem bright watchful eye",(side*.24,-.66,4.25),(.24,.09,.105),glow,.025)
        ctx.curve("Golem luminous breast fracture",[(side*.50,-.80,3.50),(side*.76,-.82,3.2),(side*.62,-.85,3.0),(side*.91,-.69,2.61)],.038,glow)
    if solar:
        for j in range(7):
            a=(j-3)*.32;ctx.crystal("Colossus seven solar crown rays",(math.sin(a)*.65,.03,4.63+math.cos(a)*.25),.12,1.0 if j%2 else .72,"SunGlow",(0,-a*.65,0))
        ctx.ring("Colossus hovering solar nimbus",(0,0,5.83),1.47,.050,"SunGlow")
        ctx.ring("Colossus etched gold nimbus",(0,0,5.89),1.68,.065,"Gold")


def create_spirit(ctx):
    ctx.loft("Spirit flowing leaf robe",[(0,0,.25,.92,.69),(0,0,.8,.66,.50),(0,0,1.65,.46,.40),(0,0,2.0,.43,.38)],"Spirit",12,smooth_faces=True)
    ctx.sphere("Spirit hood",(0,0,2.10),(.65,.57,.77),"PineLight")
    ctx.sphere("Spirit shadowed face",(0,-.48,2.11),(.41,.12,.40),"Obsidian")
    for side in [-1,1]:
        ctx.sphere("Spirit brilliant eye",(side*.17,-.59,2.2),(.07,.045,.10),"BlueEnergy",1)
        ctx.curve("Spirit vine-like arm",[(side*.40,0,1.7),(side*.97,-.10,1.24),(side*1.15,-.39,1.66)],.11,"Spirit")
        for j in range(3):ctx.crystal("Spirit leaf crown",(side*.25,-.05,2.65+j*.02),.12,.6,"BushTip",(0,side*(.3+j*.23),0))
    ctx.ring("Spirit floating rune",(0,0,.13),1.15,.022,"BlueEnergy")


def create_harpy(ctx):
    ctx.sphere("Harpy feathered breast",(0,0,1.75),(.65,.54,.99),"Petal")
    ctx.sphere("Harpy crowned head",(0,-.13,2.95),(.45,.42,.48),"PurpleHide")
    ctx.limb("Harpy hooked ivory beak",(0,-.48,2.96),(0,-.95,2.72),.19,.015,"Ivory")
    for side in [-1,1]:
        ctx.sphere("Harpy amber eye",(side*.27,-.46,3.09),(.07,.06,.08),"SunGlow",1)
        ctx.limb("Harpy powerful bird leg",(side*.32,.1,1.05),(side*.43,-.02,.25),.15,.10,"Gold")
        for j in range(3):ctx.limb("Harpy curved talon",(side*.43,-.02,.25),(side*.43+(j-1)*.20,-.53,.10),.06,.008,"Obsidian",7)
        for j in range(10):
            x0=side*.40;y0=.10;z0=2.34;x1=side*(1.45+j*.15);y1=-.3+j*.20;z1=2.93-j*.11
            ctx.limb("Harpy sculpted flight feather",(x0,y0,z0),(x1,y1,z1),.15,.014,"Petal" if j%2 else "PurpleHide",7)
        ctx.curve("Harpy leading wing bone",[(side*.35,0,2.3),(side*1.4,-.25,2.95),(side*2.40,.12,2.6)],.10,"Gold")
    for j in range(3):ctx.crystal("Harpy swept crown feather",((j-1)*.18,.06,3.32),.105,.68,"Gold",(.32,0,0))


def create_bear(ctx):
    ctx.sphere("Bear heavy torso",(0,.24,1.66),(1.22,1.75,1.05),"Fur")
    ctx.sphere("Bear muscular shoulder hump",(0,-.88,1.95),(1.05,.98,1.09),"FurDark")
    ctx.sphere("Bear broad head",(0,-1.62,1.85),(.91,.80,.76),"Fur")
    ctx.sphere("Bear pale muzzle",(0,-2.23,1.62),(.55,.44,.34),"Ivory")
    ctx.sphere("Bear black nose",(0,-2.60,1.69),(.29,.14,.19),"Obsidian",1)
    for side in [-1,1]:
        ctx.sphere("Bear rounded ear",(side*.69,-1.39,2.40),(.25,.21,.29),"FurDark")
        ctx.sphere("Bear eye",(side*.51,-2.16,2.05),(.07,.07,.07),"SunGlow",1)
        for y in [-.95,1.2]:
            ctx.limb("Bear strong foreleg",(side*.77,y,1.5),(side*.84,y-.12,.24),.34,.25,"FurDark")
            ctx.sphere("Bear heavy paw",(side*.84,y-.25,.21),(.36,.49,.24),"Fur")
            for j in range(3):ctx.limb("Bear visible ivory claw",(side*.84+(j-1)*.17,y-.58,.24),(side*.84+(j-1)*.17,y-.83,.12),.045,.005,"Ivory",6)


def create_scorpion(ctx):
    ctx.sphere("Scorpion armored body",(0,.18,.90),(1.11,1.64,.62),"Bronze")
    for j in range(5):ctx.box("Scorpion overlapping dorsal plate",(0,-.85+j*.50,1.26), (1.45,.47,.25),"Gold",.09)
    for side in [-1,1]:
        for j in range(4):
            y=-.55+j*.55;knee=(side*1.8,y+.2,1.0)
            ctx.limb("Scorpion articulated leg",(side*.8,y,.85),knee,.12,.085,"Bronze")
            ctx.limb("Scorpion needle foot",knee,(side*2.3,y-.04,.08),.085,.009,"Obsidian")
        ctx.curve("Scorpion powerful pincer arm",[(side*.65,-.9,.90),(side*1.4,-1.7,.8),(side*1.7,-2.3,1.05)],.18,"Bronze")
        for finger in [-1,1]:
            ctx.curve("Scorpion open claw",[(side*1.7,-2.3,1.05),(side*1.7+finger*.4,-2.78,1.24),(side*1.7+finger*.13,-3.2,1.3)],.15,"Gold")
        ctx.sphere("Scorpion ember eye",(side*.29,-1.20,1.24),(.085,.08,.08),"RedCrystal",1)
    tail=[(0,1.23,1.0),(0,1.92,1.25),(0,2.36,1.9),(0,2.35,2.72),(0,1.95,3.41),(0,1.23,3.74),(0,.62,3.49)]
    for j,(a,b) in enumerate(zip(tail,tail[1:])):
        ctx.limb("Scorpion segmented rising tail",a,b,.31-j*.028,.29-j*.028,"Bronze")
        ctx.sphere("Scorpion polished tail joint",b,(.29-j*.023,)*3,"Gold",1)
    ctx.limb("Scorpion venomous crystal sting",tail[-1],(0,.30,2.99),.18,.005,"Amethyst",8)


def create_leviathan(ctx):
    points=[(1.8,2.2,.75),(2.4,.9,1.10),(1.6,-.1,1.70),(.20,0,2.12),
            (-1.0,1.3,1.91),(-.7,2.8,1.40),(.55,3.6,1.0),(1.9,4.15,.70),(1.6,5.3,.50),(.2,5.9,.70)]
    radii=[.85,1.06,1.15,1.12,.97,.72,.55,.37,.22,.02]
    create_swept_body(ctx,"Leviathan continuous sculpted serpent",points,radii,"PurpleHide")
    ctx.curve("Leviathan curved rising neck",[(.2,0,2.0),(.2,-1.0,3.0),(.1,-1.85,3.85)],.70,"PurpleHide")
    ctx.sphere("Leviathan sculpted dragon skull",(.1,-2.08,4.0),(.92,1.0,.65),"PurpleHide",2)
    ctx.sphere("Leviathan long predatory muzzle",(.1,-3.02,3.72),(.62,1.03,.38),"Obsidian",2)
    ctx.sphere("Leviathan carved lower jaw",(.1,-2.91,3.40),(.57,.85,.18),"Petal",2)
    for j,p in enumerate(points[:-2]):ctx.crystal("Leviathan dorsal amethyst blade",(p[0],p[1],p[2]+radii[j]*.8),.24*(1-j*.07),1.5-j*.13,"Amethyst",(.1,0,0))
    for side in [-1,1]:
        ctx.sphere("Leviathan luminous watchful eye",(.1+side*.72,-2.55,4.13),(.15,.15,.11),"Amethyst",1)
        ctx.curve("Leviathan swept crown horn",[(.1+side*.64,-1.75,4.42),(.1+side*.96,-1.05,5.11),(.1+side*1.1,-.24,5.50)],.16,"Ivory")
        for j in range(4):ctx.limb("Leviathan ivory fang",(.1+side*.46,-3.5+j*.27,3.67),(.1+side*.44,-3.5+j*.27,3.39),.06,.004,"Ivory",6)
        ctx.curve("Leviathan powerful foreleg",[(side*.90,-.2,2.1),(side*1.6,-1.0,.83),(side*1.85,-1.64,.28)],.26,"PurpleHide")
        for j in range(3):ctx.limb("Leviathan hooked talon",(side*1.85+(j-1)*.18,-1.63,.32),(side*1.85+(j-1)*.18,-2.16,.15),.07,.003,"Ivory",6)
        wing=[(side*.80,.28,2.4),(side*2.05,.32,4.0),(side*4.8,.65,5.5),(side*5.45,1.45,3.65),
              (side*4.1,1.73,3.0),(side*4.9,2.86,2.0),(side*3.2,2.72,2.22),(side*3.12,4.0,1.38),(side*1.0,3.03,1.89)]
        center=(side*2.85,1.8,3.3);verts=[center];faces=[];n=len(wing)
        for rr in [.28,.62,1.0]:
            for p in wing:
                v=Vector(center)+(Vector(p)-Vector(center))*rr;v.z+=math.sin(rr*PI)*.25;verts.append(tuple(v))
        for j in range(n):faces.append((0,1+j,1+(j+1)%n))
        for row in range(2):
            for j in range(n):faces.append((1+row*n+j,1+row*n+(j+1)%n,1+(row+1)*n+(j+1)%n,1+(row+1)*n+j))
        ctx.mesh("Leviathan curved scalloped wing membrane",verts,faces,"Petal",smooth_faces=True)
        ctx.curve("Leviathan obsidian leading wing bone",wing[:4],.16,"Obsidian")
        for j in [3,5,7]:
            ctx.curve("Leviathan anatomical wing rib",[wing[0],center,wing[j]],.09,"PurpleHide")
            ctx.curve("Leviathan iridescent wing vein",[(x,y-.03,z+.04) for x,y,z in [wing[0],center,wing[j]]],.026,"Amethyst")


MONSTER_BUILDERS = {
    "Wolf":create_wolf, "Spider":create_spider,
    "GiantSpider":lambda ctx:create_spider(ctx,True),
    "Elemental":create_elemental, "Boar":create_boar,
    "Golem":create_golem, "GoldenGolem":lambda ctx:create_golem(ctx,True),
    "ForestSpirit":create_spirit, "Harpy":create_harpy,
    "Bear":create_bear, "GiantScorpion":create_scorpion,
    "SolarColossus":lambda ctx:create_golem(ctx,True,True),
    "NightLeviathan":create_leviathan,
}


def create_monster(ctx,kind,position,scale=1.0,boss=False):
    with ctx.root(kind,position,"boss" if boss else "monster",scale=scale) as root:
        root["monster_kind"]=kind;MONSTER_BUILDERS[kind](ctx);decorate_monster(ctx,kind)
        return root


def create_camp(ctx,index,kind,position):
    ctx.group("MonsterCamps")
    with ctx.root(f"Camp {index:02d}",(*position,.10),"camp") as root:
        root["camp_index"]=index;root["monster_kind"]=kind
        ctx.cylinder("Camp natural clearing",(0,0,-.01),5.45,.10,"Earth",48,.02)
        for j in range(10):
            a=j*2*PI/10;ctx.sphere("Camp edge mossy pebble",(5.35*math.cos(a),5.35*math.sin(a),.12),(.30,.26,.20),"Moss",1)
        count=3 if kind in {"Wolf","Elemental","ForestSpirit"} else 2 if kind in {"Boar","Golem","Harpy","Bear"} else 1
        scale=.95 if kind in {"Wolf","Boar","Bear"} else .81 if kind=="Golem" else 1.3 if kind in {"GiantSpider","GiantScorpion"} else 1.05
        for j in range(count):
            p=(0,0,.10) if count==1 else ((j-(count-1)/2)*2.8, .6 if j%2 else -.3,.10)
            create_monster(ctx,kind,p,scale*(1.1 if j==0 and count>1 else 1))
        ctx.text("Camp number",str(index),(0,-4.4,.057),1.5)
        return root

# -----------------------------------------------------------------------------
# 7. Свет, камера, рендер и экспорт описания сцены.
# -----------------------------------------------------------------------------
def create_lighting_and_camera(ctx):
    scene=ctx.scene;ctx.group("Lighting")
    world=bpy.data.worlds.new(PREFIX+"Soft blue fantasy sky");world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(*srgb("B5D9EE"),1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=.65;scene.world=world
    data=bpy.data.lights.new(PREFIX+"Warm fantasy sun","SUN");data.energy=2.6;data.color=srgb("FFE2AC");data.angle=math.radians(12)
    sun=ctx.object("Warm fantasy sun",data,(0,0,140),rotation=(math.radians(22),math.radians(-26),math.radians(-25)))
    area_data=bpy.data.lights.new(PREFIX+"Blue sky fill","AREA");area_data.energy=18000;area_data.shape="DISK";area_data.size=140;area_data.color=srgb("B5DDF6")
    area=ctx.object("Blue sky fill",area_data,(20,25,110));area.rotation_euler=(Vector((0,0,0))-area.location).to_track_quat('-Z','Y').to_euler()
    camera_data=bpy.data.cameras.new(PREFIX+"Orthographic 55 degree camera");camera_data.type="ORTHO";camera_data.ortho_scale=315;camera_data.lens=50;camera_data.clip_end=1200
    e=math.radians(ctx.cfg.camera_elevation);target=Vector((0,0,-1));position=Vector((0,-340*math.cos(e),340*math.sin(e)))+target
    camera=ctx.object("Main map camera",camera_data,position);camera.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler();scene.camera=camera
    camera["elevation_degrees"]=ctx.cfg.camera_elevation
    scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=ctx.cfg.samples
    scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.07;scene.cycles.adaptive_min_samples=8
    scene.cycles.max_bounces=5;scene.cycles.diffuse_bounces=2;scene.cycles.glossy_bounces=2
    # В отдельных сборках Blender отсутствует OIDN. Не делать рендер зависимым от него.
    try:scene.cycles.denoiser="OPENIMAGEDENOISE";scene.cycles.use_denoising=True
    except (TypeError,ValueError):scene.cycles.use_denoising=False
    scene.render.resolution_x=ctx.cfg.resolution;scene.render.resolution_y=ctx.cfg.resolution;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG";scene.render.film_transparent=False
    scene.render.fps=ctx.cfg.fps;scene.frame_start=1;scene.frame_end=ctx.cfg.frames
    scene.view_settings.view_transform="AgX"
    try:scene.view_settings.look="AgX - Medium High Contrast"
    except (TypeError,ValueError):pass
    scene.view_settings.exposure=.3
    # Совместимый с Blender 4.0–4.3 композитор: небольшое свечение, без белой засветки.
    scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layer=nodes.new("CompositorNodeRLayers");glare=nodes.new("CompositorNodeGlare");glare.glare_type="FOG_GLOW";glare.quality="MEDIUM";glare.threshold=2;glare.size=7;glare.mix=-.92;output=nodes.new("CompositorNodeComposite")
    scene.node_tree.links.new(layer.outputs["Image"],glare.inputs["Image"]);scene.node_tree.links.new(glare.outputs["Image"],output.inputs["Image"])
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                area.spaces.active.region_3d.view_perspective="CAMERA"
                area.spaces.active.clip_end=1500


def validate_scene(ctx):
    roots=[o for o in ctx.scene.objects if o.get("category")]
    def items(category):return [o for o in roots if o.get("category")==category]
    towers=items("tower");assert len(towers)==18
    for lane,teams in TOWERS.items():
        for team,entries in teams.items():
            for tier,x,y in entries:
                obj=next(o for o in towers if o["lane"]==lane and o["team"]==team and o["tier"]==tier)
                assert math.hypot(obj.location.x-x,obj.location.y-y)<1e-6,(lane,team,tier)
    assert len(items("nexus"))==2 and len(items("boss"))==2
    assert len(items("neutral"))==24 and len(items("minion_template"))==6
    assert len(items("fountain"))==2 and len(items("hero"))==10
    assert all(abs(o.location.z)<1e-8 for o in items("hero"))
    assert len(TOWER_PASSAGES)==18 and len(BOSS_APPROACHES)==4
    assert len(items("stone_bridge"))==3 and len(items("energy_bridge"))==2
    assert len(items("camp"))==12 and len(items("crystal_gate"))==8 and len(items("clearing"))==4
    for _,kind,_ in CAMPS:assert kind in MONSTER_BUILDERS
    ground=items("playable_terrain")[0]
    assert min(v.co.x for v in ground.data.vertices)==-100 and max(v.co.x for v in ground.data.vertices)==100
    assert min(v.co.y for v in ground.data.vertices)==-100 and max(v.co.y for v in ground.data.vertices)==100
    assert len(items("tree"))>=min(130,ctx.cfg.tree_count),"Insufficient forest; check placement filters"
    # Не маскируем недобор густоты леса молчаливым успехом.
    for obj in items("tree"):
        assert all(math.dist(obj.location.xy,p)>11.5 for p in CLEARINGS.values()),"A tree intrudes into a clearing"
    for obj in ctx.scene.objects:
        if obj.type=="MESH":
            assert len(obj.data.vertices)>0 and all(math.isfinite(v) for p in obj.data.vertices for v in p.co),obj.name
    assert ctx.scene.camera.data.type=="ORTHO"
    ctx.scene.frame_set(1)
    invalid=[]
    for obj in ctx.scene.objects:
        if obj.animation_data:
            for curve in obj.animation_data.drivers:
                if not curve.driver.is_valid:invalid.append((obj.name,curve.data_path))
    assert not invalid,invalid
    print("VALIDATION PASS: 200x200, 18 exact towers, 2 bases, 2 bosses, 12 camps, 4 clearings, 8 gates, 3 stone + 2 energy bridges",flush=True)
    return {"categories":{key:len(items(key)) for key in sorted({o["category"] for o in roots})},"objects":len(ctx.scene.objects),"unique_meshes":len({o.data for o in ctx.scene.objects if o.type=="MESH"})}


def export_layout(ctx,validation):
    def xy(p):return {"X":p[0],"Y":p[1]}
    data={"name":"Долина Осколков","generator_version":"3.0","seed":ctx.cfg.seed,"coordinate_system":"X/Y ground, Z height","playable_size":200,
          "towers":[{"team":team,"lane":lane,"tier":tier,"position":xy((x,y))} for lane,teams in TOWERS.items() for team,entries in teams.items() for tier,x,y in entries],
          "bases":{key:xy(p) for key,p in BASES.items()},"bosses":{key:xy(p) for key,p in BOSSES.items()},
          "clearings":{key:xy(p) for key,p in CLEARINGS.items()},"fountains":{key:xy(p) for key,p in FOUNTAINS.items()},
          "tower_passages":[{"team":t,"lane":lane,"tier":tier,"points":[xy(p) for p in route]} for t,lane,tier,route in TOWER_PASSAGES],
          "boss_approaches":[{"boss":i//2,"points":[xy(p) for p in route],"width":8} for i,route in enumerate(BOSS_APPROACHES)],
          "forest_paths":[[xy(p) for p in route] for route in FOREST_PATHS],
          "river_half_width":ctx.cfg.river_half_width,"neutral_catalog":{"total":26,"forest":22,"rift":2,"bosses":2},"backdrop_trees":ctx.registry["backdrop_tree_count"],"physics_plane_y":0,"colliders":export_colliders(ctx),
          "camps":[{"id":i,"kind":kind,"position":xy(p)} for i,kind,p in CAMPS],
          "river":[xy(p) for p in ctx.river],"lanes":{key:[xy(p) for p in points] for key,points in ctx.lanes.items()},
          "stone_bridges":[{"lane":key,"position":xy(p)} for key,p in STONE_BRIDGES],"energy_bridges":[{"kind":key,"position":xy(p)} for key,p in ENERGY_BRIDGES],
          "crystals":[{"id":i+1,"position":xy(p),"durability":24,"respawn_seconds":60,"side":"Light" if i in [0,1,2,6] else "Dark","role":["ambush","hunt","rescue","ambush","hunt","rescue","invasion","invasion"][i],"short_path":[xy(q) for q in ctx.gates[i]]} for i,(p,_) in enumerate(CRYSTAL_GATES)],
          "trees":[xy(p) for p in ctx.registry["trees"]],"validation":validation}
    (ctx.cfg.output/"ValleyOfShards.layout.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")


# -----------------------------------------------------------------------------
# Художественная проработка 1.1: органические поверхности и природные переходы.
# -----------------------------------------------------------------------------
def create_swept_body(ctx,name,points,radii,material,sides=16):
    samples=catmull(points,6);vertices=[];faces=[]
    for i,p in enumerate(samples):
        t=i/(len(samples)-1)*(len(radii)-1);j=min(len(radii)-2,int(t));f=t-j;r=radii[j]*(1-f)+radii[j+1]*f
        tangent=Vector(samples[min(i+1,len(samples)-1)])-Vector(samples[max(0,i-1)]);rotation=tangent.to_track_quat('Z','Y')
        for k in range(sides):
            a=k*2*PI/sides;v=rotation@Vector((math.cos(a)*r,math.sin(a)*r*.90,0))+Vector(p);vertices.append(tuple(v))
        if i:
            for k in range(sides):faces.append(((i-1)*sides+k,(i-1)*sides+(k+1)%sides,i*sides+(k+1)%sides,i*sides+k))
    faces.extend([tuple(reversed(range(sides))),tuple((len(samples)-1)*sides+k for k in range(sides))])
    return ctx.mesh(name,vertices,faces,material,smooth_faces=True)


def create_detail_leaf(ctx,name,base,tip,width,material):
    a=Vector(base);b=Vector(tip);d=b-a;normal=Vector((-d.y,d.x,0)).normalized()
    if normal.length<.01:normal=Vector((1,0,0))
    center=a+d*.48+Vector((0,0,width*.25));vertices=[tuple(a),tuple(a+d*.30-normal*width*.55),tuple(a+d*.72-normal*width*.38),tuple(b),tuple(a+d*.72+normal*width*.38),tuple(a+d*.30+normal*width*.55),tuple(center)]
    return ctx.mesh(name,vertices,[(0,1,6),(1,2,6),(2,3,6),(3,4,6),(4,5,6),(5,0,6)],material)


def decorate_monster(ctx,kind):
    if kind in {"Wolf","Bear","Boar"}:
        fur="Ivory" if kind=="Wolf" else "Fur" if kind=="Bear" else "FurDark"
        for side in [-1,1]:
            for j in range(5):
                x=side*(.50+j*.045);y=-.8+j*.23;z=2.05-j*.03
                create_detail_leaf(ctx,"Layered sculpted animal ruff",(x,y,z),(x+side*.27,y+.32,z-.41),.28,fur)
        if kind=="Wolf":
            for side in [-1,1]:
                ctx.curve("Wolf expressive silver brow",[(side*.25,-1.90,2.67),(side*.44,-1.83,2.64),(side*.56,-1.70,2.58)],.035,"Ivory")
            for j in range(4):ctx.crystal("Wolf small moon dorsal gem",(0,-.2+j*.36,2.19),.09,.28,"BlueCrystal")
        elif kind=="Bear":
            for side in [-1,1]:ctx.curve("Bear mossy shoulder sigil",[(side*.80,-.81,2.55),(side*1.0,-.53,2.30),(side*.87,-.24,2.25)],.035,"Spirit")
    elif kind in {"Spider","GiantSpider"}:
        for j in range(5):
            y=.05+j*.38;ctx.curve("Spider polished abdominal carapace seam",[(-.67,y,1.87),(0,y,2.22),(.67,y,1.87)],.035,"Gold")
        for side in [-1,1]:
            for j in range(4):ctx.sphere("Spider articulated jade knee",(side*(2+math.sin(j)*.3),-.98+j*.6+(j-1.5)*.36,1.7),(.16,.16,.17),"BlueHide" if kind=="Spider" else "Amethyst",1)
    elif kind in {"Golem","GoldenGolem","SolarColossus"}:
        gold=kind!="Golem";glow="SunGlow" if gold else "BlueCrystal"
        for side in [-1,1]:
            for j in range(3):
                ctx.crystal("Golem inset shoulder mineral",(side*(1.32+j*.23),-.48,3.75-j*.18),.11,.45,glow,(.22,side*.4,0))
            ctx.curve("Golem chased breastplate trim",[(side*.23,-.86,3.57),(side*.75,-.79,3.72),(side*1.12,-.63,3.26)],.055,"Gold" if gold else "Ivory")
        if kind=="SolarColossus":
            # The shield is deliberately stone-and-gold, distinct from the jungle golem.
            center=Vector((-2.18,-1.08,2.44));outline=[(-.91,.75),(-.77,1.08),(.77,1.08),(.91,.75),(.72,-.55),(0,-1.13),(-.72,-.55)]
            for inset,mat,y in [(1.0,"Gold",0),(.84,"Marble",-.13)]:
                verts=[tuple(center+Vector((x*inset,yy+y,z*inset))) for yy in [-.10,.10] for x,z in outline];n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
                ctx.mesh("Colossus royal sun shield",verts,faces,mat,bevel=.045)
            ctx.sphere("Colossus shield solar disc",tuple(center+Vector((0,-.28,.17))),(.31,.08,.31),"SunGlow",2)
            for j in range(8):
                a=j*PI/4;ctx.limb("Colossus shield sunburst",tuple(center+Vector((math.cos(a)*.37,-.29,.17+math.sin(a)*.37))),tuple(center+Vector((math.cos(a)*.58,-.29,.17+math.sin(a)*.58))),.035,.014,"Gold",6)
    elif kind=="ForestSpirit":
        for side in [-1,1]:
            for j in range(4):create_detail_leaf(ctx,"Spirit layered living leaf mantle",(side*.36,.14+j*.12,1.83),(side*(.70+j*.09),.24+j*.15,.50),.45,"PineLight" if j%2 else "Bush")
        ctx.sphere("Spirit amber collar gem",(0,-.44,1.68),(.14,.08,.17),"SunGlow",1)
    elif kind=="Harpy":
        for side in [-1,1]:
            for j in range(7):
                create_detail_leaf(ctx,"Harpy overlapping sculpted flight plume",(side*.62,.1,2.39),(side*(1.63+j*.17),.23+j*.16,2.77-j*.10),.21,"Ivory" if j%3==0 else "Petal")
    elif kind=="GiantScorpion":
        for j in range(5):ctx.crystal("Scorpion dorsal venom mineral",(0,-.60+j*.42,1.44),.13,.40,"Amethyst")
    elif kind=="NightLeviathan":
        for side in [-1,1]:
            for j in range(8):
                create_detail_leaf(ctx,"Leviathan layered iridescent neck scale",(.1+side*.40,-.55-j*.15,2.5+j*.14),(.1+side*.68,-.32-j*.15,2.3+j*.14),.24,"PurpleHide" if j%2 else "Petal")
            for j in range(3):ctx.crystal("Leviathan cheek amethyst fan",(.1+side*.74,-1.78+j*.18,4.04),.10,.51,"Amethyst",(.2,side*.85,0))


def create_environment_details(ctx):
    ctx.group("BotanicalDetails");rng=random.Random(ctx.cfg.seed+812);tufts=0;flowers=0;cliffs=0
    # Small geometry at path edges makes natural transitions without covering the lanes.
    for attempt in range(6500):
        if tufts>=650:break
        p=(rng.uniform(-94,94),rng.uniform(-94,94))
        if min(route_distance(p,r) for r in ctx.lanes.values())<6.1:continue
        if route_distance(p,ctx.river)<5.2:continue
        if any(math.dist(p,c)<10.6 for c in CLEARINGS.values()):continue
        if any(math.dist(p,c)<15.5 for c in list(BASES.values())+list(BOSSES.values())):continue
        if any(math.dist(p,c)<3.4 for _,_,c in CAMPS):continue
        path=min(route_distance(p,r) for r in ctx.paths)
        if path<2.05:continue
        if path>6 and rng.random()<.7:continue
        z=ctx.height(*p);verts=[];faces=[]
        for j in range(7):
            a=j*2.39996+attempt;r=rng.uniform(.05,.34);h=rng.uniform(.23,.62);w=.045
            x=p[0]+math.cos(a)*r;y=p[1]+math.sin(a)*r;k=len(verts)
            verts.extend([(x-math.sin(a)*w,y+math.cos(a)*w,z),(x+math.sin(a)*w,y-math.cos(a)*w,z),(x+math.cos(a)*.16,y+math.sin(a)*.16,z+h)]);faces.append((k,k+1,k+2))
        ctx.mesh("Path edge hand painted grass tuft",verts,faces,"GrassBlade");tufts+=1
        if tufts%15==0:
            for j in range(3):
                q=(p[0]+j*.20,p[1]+j*.15,z+.28+j*.08)
                ctx.limb("Wildflower stalk",(q[0],q[1],z),q,.013,.009,"GrassBlade",5)
                for k in range(4):
                    a=k*PI/2;ctx.sphere("Woodland flower petal",(q[0]+math.cos(a)*.075,q[1]+math.sin(a)*.075,q[2]),(.08,.06,.035),"FlowerBlue" if tufts%30 else "FlowerCream",1)
            flowers+=1
    # Exposed jungle strata only on elevated ground, outside all protected routes.
    for i in range(1000):
        if cliffs>=34:break
        p=(rng.uniform(-58,58),rng.uniform(-58,58));h=ctx.height(*p)
        if h<2.6 or not ctx.clear_for_foliage(p,.35):continue
        if any(math.dist(p,q)<2.0 for q in ctx.registry["trees"]):continue
        create_rock(ctx,"Exposed mossy jungle terrace",(*p,h-.55),(1.45,1.05,1.7),seed=i)
        ctx.sphere("Jungle cliff painted moss",(p[0]-.2,p[1],h+.54),(1.02,.75,.15),"Moss",1);cliffs+=1
    # A scattering of natural stones/reeds is not a continuous bank wall.
    ctx.group("Riverbanks");samples=path_samples(ctx.river,5.5)
    for i,p in enumerate(samples[2:-2]):
        if any(math.dist(p,q)<11 for _,q in STONE_BRIDGES+ENERGY_BRIDGES):continue
        a=samples[max(0,i+1)];b=samples[min(len(samples)-1,i+3)];d=(Vector(b)-Vector(a)).normalized();normal=Vector((-d.y,d.x))
        side=-1 if i%2 else 1;q=Vector(p)+normal*side*5.55
        if min(route_distance(q,r) for r in ctx.lanes.values())<6.2:continue
        z=ctx.height(*q)
        ctx.sphere("Riverbank softened moss stone",(q.x,q.y,z+.12),(.60,.44,.30),"Stone",1)
        for j in range(3):create_detail_leaf(ctx,"Riverbank bright folded reed",(q.x+j*.12,q.y,z),(q.x+.1+j*.12,q.y+.28,z+.65+j*.1),.11,"Bush")
    print("POLISH DETAILS",tufts,"grass clumps",flowers,"flower clusters",cliffs,"jungle strata",flush=True)


def create_painted_textures(ctx):
    """Tileable image detail maps, generated in Blender and packed into the scene."""
    from array import array
    from mathutils.noise import noise as pnoise
    target=ctx.cfg.output/'textures';target.mkdir(exist_ok=True)
    groups={
        'painted_stone':{'Stone','Marble','Lane','LaneLight','LaneWarm','StoneDark','CrimsonStone','Obsidian','Gold','Bronze'},
        'painted_earth':{'Grass','Moss','Earth','EarthEdge','LaneJoint'},
        'painted_foliage':{'Pine','PineDark','PineLight','Bush','BushTip','GrassBlade','Fur','FurDark','Wolf','Petal','PurpleHide','BlueHide'},
        'flowing_water':{'RiverWater','SkyWater'},
    }
    for kind,names in groups.items():
        size=512;image=bpy.data.images.new(PREFIX+kind,width=size,height=size,alpha=True);image.colorspace_settings.name='Non-Color';pixels=array('f')
        for j in range(size):
            v=j/size;sv=math.sin(v*2*PI);cv=math.cos(v*2*PI)
            for i in range(size):
                u=i/size;su=math.sin(u*2*PI);cu=math.cos(u*2*PI)
                n=pnoise(Vector((cu*2,sv*2,su+cv))*3.0,noise_basis='PERLIN_ORIGINAL')
                brush=math.sin(2*PI*(u*17+v*3)+su*1.7)*math.sin(2*PI*(v*29-u*7))
                if kind=='flowing_water':value=.89+.065*n+.04*math.sin(2*PI*(v*19+u*2)+su*3)
                elif kind=='painted_foliage':value=.91+.06*n+.025*brush
                else:value=.91+.065*n+.025*brush
                value=max(.74,min(1,value));pixels.extend((value,value,value,1))
        image.pixels.foreach_set(pixels);image.filepath_raw=str(target/(kind+'.png'));image.file_format='PNG';image.save();image.pack()
        for name in names:
            mat=ctx.materials[name];nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');base=next(l.from_socket for l in links if l.to_socket==shader.inputs['Base Color'])
            tex=nodes.new('ShaderNodeTexImage');tex.name='Surface painted detail';tex.image=image;tex.extension='REPEAT'
            uv=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeMapping');mapping.inputs['Scale'].default_value=(3,3,3);links.new(uv.outputs['UV'],mapping.inputs['Vector']);links.new(mapping.outputs['Vector'],tex.inputs['Vector'])
            mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;links.new(base,mix.inputs[1]);links.new(tex.outputs['Color'],mix.inputs[2]);links.new(mix.outputs[0],shader.inputs['Base Color'])
    print('PAINTED TEXTURES: 4 packed tileable 512x512 detail maps',flush=True)


def create_small_paving(ctx,name,points,width=3.6):
    ctx.group('SidePassages');samples=path_samples(catmull(points,4),1.5);verts=[];faces=[];level=.17+ctx.path_layer*.001;ctx.path_layer+=1
    for i,(a,b) in enumerate(zip(samples,samples[1:])):
        mid=(Vector(a)+Vector(b))*.5
        if route_distance(mid,ctx.river)<ctx.cfg.river_half_width+.6:continue
        ta=(Vector(b)-Vector(samples[max(0,i-1)])).normalized();tb=(Vector(samples[min(len(samples)-1,i+2)])-Vector(a)).normalized();na=Vector((-ta.y,ta.x));nb=Vector((-tb.y,tb.x))
        for j in range(3):
            lo=-width/2+j*width/3;hi=lo+width/3;q=[Vector(a)+na*lo,Vector(b)+nb*lo,Vector(b)+nb*hi,Vector(a)+na*hi];c=sum(q,Vector((0,0)))/4
            add_prism(verts,faces,[tuple(c+(p-c)*.95) for p in q],level-.08,level)
    if verts:ctx.mesh(name,verts,faces,'LaneWarm',bevel=.028)


def create_fountain(ctx,team,position):
    ctx.group('Fountains');glow='BlueCrystal' if team=='Light' else 'RedCrystal'
    with ctx.root('Healing fountain '+team,(*position,0),'fountain') as root:
        root['team']=team;root['trigger_radius']=6.6;root['health_per_second']=300;root['mana_per_second']=180;root['physics_y']=0
        ctx.loft('Fountain raised marble platform',[(0,0,.05,7,7),(0,0,.24,7,7),(0,0,.35,6.5,6.5),(0,0,.66,6.5,6.5)],'Marble' if team=='Light' else 'CrimsonStone',48,.06)
        for r in [4.6,5.8,6.3]:ctx.ring('Fountain healing rune circle',(0,0,.70),r,.045,'HealGlow')
        for j in range(12):
            a=j*PI/6;x,y=math.cos(a),math.sin(a)
            ctx.curve('Fountain carved healing rune',[(x*5.0,y*5.0,.71),(x*5.4-y*.14,y*5.4+x*.14,.71),(x*5.8,y*5.8,.71)],.035,'HealGlow')
        for side in [-1,1]:
            ctx.cylinder('Fountain team beacon pillar',(side*5.7,0,1.0),.45,1.8,'Marble' if team=='Light' else 'StoneDark',12)
            ctx.crystal('Fountain allied crystal beacon',(side*5.7,0,1.9),.19,1.0,glow)
        ctx.cylinder('Fountain pale healing field',(0,0,.69),4.4,.025,'HealGlow',48,.008)
        return root


def create_hero(ctx,team,index,position):
    ctx.group('Heroes');cloth='HeroBlue' if team=='Light' else 'HeroRed';glow='BlueCrystal' if team=='Light' else 'RedCrystal'
    with ctx.root(f'Hero {team} {index}',(*position,0),'hero') as root:
        root['team']=team;root['hero_index']=index;root['physics_y']=0;root['controllable']=team=='Light' and index==0
        with ctx.root('Hero visual body',(0,0,.30)):
            ctx.loft('Hero sculpted breastplate',[(0,0,.9,.42,.29),(0,0,1.65,.58,.34),(0,0,1.88,.46,.28)],'Marble' if team=='Light' else 'StoneDark',10,.045)
            ctx.sphere('Hero helmet',(0,-.02,2.20),(.36,.32,.41),'Gold' if team=='Light' else 'Bronze',2)
            ctx.box('Hero inset dark visor',(0,-.31,2.21),(.44,.08,.15),'Obsidian',.025)
            for side in [-1,1]:
                ctx.box('Hero glowing visor eye',(side*.12,-.36,2.22),(.14,.025,.043),glow,.008)
                ctx.sphere('Hero rounded shoulder plate',(side*.63,0,1.73),(.30,.35,.32),'Gold' if team=='Light' else 'Bronze',1)
                ctx.limb('Hero armored forearm',(side*.67,0,1.65),(side*.79,-.1,1.02),.15,.12,'Marble' if team=='Light' else 'StoneDark')
                ctx.limb('Hero armored leg',(side*.24,0,1.01),(side*.28,0,.30),.18,.14,cloth)
                ctx.box('Hero bevelled boots',(side*.28,-.10,.21),(.35,.58,.32),'StoneDark',.07)
            ctx.mesh('Hero flowing team cape',[(-.40,.25,1.87),(.40,.25,1.87),(.70,.6,.43),(.27,.70,.63),(0,.72,.36),(-.70,.6,.43)],[(0,1,2,3,4,5)],cloth)
            ctx.limb('Hero engraved sword blade',(.88,-.16,.86),(.88,-.16,2.07),.075,.012,'Ivory',6)
            ctx.box('Hero sword golden guard',(.88,-.16,1.0),(.40,.13,.09),'Gold',.02)
            ctx.crystal('Hero chest team gem',(0,-.36,1.45),.13,.36,glow)
        return root


def create_gameplay_geometry(ctx):
    for team,lane,tier,route in TOWER_PASSAGES:create_small_paving(ctx,f'{team} {lane} T{tier} paved side passage',route,3.6)
    for i,route in enumerate(BOSS_APPROACHES):
        ctx.group('BossApproaches');create_path(ctx,catmull(route,4),8,'Earth',f'Permanent broad boss entrance {i+1}')
        # An approach floor conceals water only after it reaches the suspended arena.
        p=route[-2];ctx.group('ArenaGateways')
        for side in [-1,1]:ctx.cylinder('Boss approach gate column',(p[0]+side*4.2,p[1],1.7),.44,3.4,'Marble',12)
    for team,p in FOUNTAINS.items():
        create_small_paving(ctx,team+' fountain access',[BASES[team],p],5.4)
        for i in range(5):
            a=i*2*PI/5;create_hero(ctx,team,i,(p[0]+math.cos(a)*2.6,p[1]+math.sin(a)*2.6))
    ctx.group('ArenaSupports')
    for center in BOSSES.values():
        for j in range(12):
            a=j*PI/6;x,y=14*math.cos(a),14*math.sin(a)
            if abs(x+y)<8:continue
            ctx.cylinder('Suspended arena stone support',(center[0]+x,center[1]+y,-2.1),.68,4.4,'Stone',12)
        ctx.ring('Arena suspended lower cornice',(*center,-.03),15.5,.32,'Stone')
    # A dedicated physical plane has no terrain height; the movement mask is exported separately.
    ctx.group('Physics')
    collider=ctx.mesh('Logical collision plane Y0',[(-114,-114,0),(114,-114,0),(114,114,0),(-114,114,0)],[(0,1,2,3)],'Stone')
    collider.hide_render=True;collider.display_type='WIRE';collider['physics_only']=True;collider['plane_height']=0


def export_colliders(ctx):
    result=[]
    prefixes=('Ruin softly chamfered masonry','Ancient squared terminal pier','Crystal narrow passage sidewall')
    for obj in ctx.scene.objects:
        if obj.type!='MESH' or not obj.name.removeprefix(PREFIX).startswith(prefixes):continue
        corners=[obj.matrix_world@Vector(p) for p in obj.bound_box];lo=[min(p[i] for p in corners) for i in range(2)];hi=[max(p[i] for p in corners) for i in range(2)]
        result.append({'min':lo,'max':hi,'height':0})
    return result


# -----------------------------------------------------------------------------
# 3.0: 26 authored neutrals, articulated minion templates and open playable forest.
# -----------------------------------------------------------------------------
CAMP_RULES={'MagmaGuardian':(1,100),'AzureGolem':(1,100),'MoonWolf':(3,65),'StoneCentipede':(2,75),'RiftWraith':(3,65),'CrystalCrab':(1,75)}
RIFT_SPAWNS=[('Watcher',(-15,15)),('RiftRay',(15,-15))]
_old_leviathan=create_leviathan
_old_bush=create_bush
_old_tree=create_tree

def create_combat_materials(ctx):
    for name,dark,light,emission in [('Emerald','176548','78DC73',0),('MintLeaf','4C9639','C3F17B',0),('MagmaCore','AD1207','FF6B2A',2.3),('RiftMist','343A88','8786FF',.65),('ObsidianScale','0B0B21','352546',0),('BlueArmor','123B83','318FEB',0),('RedArmor','6D0B22','D53B50',0)]:painted_material(ctx,name,dark,light,roughness=.6,emission=emission,alpha=.65 if name=='RiftMist' else 1)


def rematerial_descendants(root,mapping):
    for obj in root.children_recursive:
        if obj.type!='MESH':continue
        if not any(m.name.removeprefix(PREFIX) in mapping for m in obj.data.materials):continue
        obj.data=obj.data.copy()
        for i,m in enumerate(obj.data.materials):
            key=m.name.removeprefix(PREFIX)
            if key in mapping:obj.data.materials[i]=mapping[key]


def create_magma_guardian(ctx):
    root=ctx.parent;create_golem(ctx)
    rematerial_descendants(root,{'BlueHide':ctx.materials['StoneDark'],'BlueCrystal':ctx.materials['MagmaCore'],'Stone':ctx.materials['Bronze']})
    for j in range(7):
        a=j*2.39996;ctx.crystal('Magma glowing fissure crystal',(math.cos(a)*1.1,math.sin(a)*.7,2.1+j%3*.5),.20,.9,'MagmaCore',(.2,.4,a))


def create_azure_golem(ctx):
    create_golem(ctx)
    for side in [-1,1]:
        ctx.crystal('Azure shoulder crystalline crest',(side*1.6,0,4.0),.27,1.1,'BlueCrystal')
        ctx.curve('Azure ancient luminous rune',[(side*.8,-.80,2.2),(side*.5,-.96,2.55),(side*.9,-.80,2.85)],.045,'BlueCrystal')


def create_centipede(ctx):
    for j in range(8):
        y=(j-3.5)*.6;z=.72+math.sin(j*.5)*.1
        ctx.sphere('Centipede carved stone carapace',(math.sin(j*.6)*.13,y,z),(1.0-j*.035,.47,.55),'Stone',2)
        ctx.crystal('Centipede emerald dorsal crystal',(0,y,z+.43),.18,.65,'Emerald')
        for side in [-1,1]:
            ctx.limb('Centipede jointed walking leg',(side*.7,y,z),(side*1.3,y-.10,.42),.12,.075,'StoneDark',8)
            ctx.limb('Centipede pointed foot',(side*1.3,y-.1,.42),(side*1.65,y-.3,.05),.075,.012,'Emerald',8)
    for side in [-1,1]:
        ctx.sphere('Centipede emerald eye',(side*.43,-2.48,.89),(.12,.10,.11),'Emerald',1)
        ctx.curve('Centipede curved ivory mandible',[(side*.55,-2.4,.61),(side*.8,-2.9,.45),(side*.32,-3.05,.45)],.095,'Ivory')


def create_wraith(ctx):
    ctx.loft('Wraith tapered floating veil',[(0,.25,.45,.04,.04),(0,.10,.9,.6,.45),(0,0,1.8,.75,.5),(0,0,2.25,.45,.35)],'RiftMist',16)
    ctx.sphere('Wraith shadowed face',(0,-.25,2.18),(.43,.33,.50),'Obsidian',2)
    for side in [-1,1]:
        ctx.sphere('Wraith luminous violet eye',(side*.17,-.56,2.27),(.09,.04,.10),'Amethyst',1)
        ctx.sphere('Wraith floating armored shoulder',(side*.88,0,1.97),(.35,.43,.35),'StoneDark',1)
        ctx.crystal('Wraith orbiting broken armor',(side*.78,-.1,1.2),.21,.86,'Amethyst',(0,side*.5,0))
    ctx.ring('Wraith levitation aura',(0,0,.40),.95,.04,'Amethyst')


def create_crab(ctx):
    ctx.sphere('Crab massive golden faceted shell',(0,0,1.05),(1.6,1.15,.86),'Gold',2)
    ctx.sphere('Crab lower obsidian armor',(0,0,.75),(1.35,1.02,.56),'Obsidian',2)
    for j in range(7):
        a=j*2.39996;ctx.crystal('Crab royal amethyst carapace',(math.cos(a)*.9,math.sin(a)*.6,1.55),.24,.85,'Amethyst',(.1,.2,a))
    for side in [-1,1]:
        for j in range(3):
            a=(side*.9,-.7+j*.7,.9);b=(side*2.05,-.9+j*.8,.7);c=(side*2.5,-1.0+j*.9,.05)
            ctx.limb('Crab golden jointed leg',a,b,.15,.10,'Gold');ctx.limb('Crab claw foot',b,c,.10,.015,'Obsidian')
        ctx.curve('Crab massive claw arm',[(side*1.1,-.6,1),(side*1.9,-1.6,1.1),(side*2.1,-2.1,1.5)],.25,'Gold')
        for f in [-1,1]:ctx.curve('Crab articulated amethyst pincer',[(side*2.1,-2.1,1.5),(side*2.1+f*.5,-2.55,1.7),(side*2.1+f*.18,-2.95,1.7)],.18,'Amethyst')
        ctx.limb('Crab raised eye stalk',(side*.55,-.75,1.5),(side*.7,-1.35,2.12),.10,.07,'Gold');ctx.sphere('Crab curious violet eye',(side*.7,-1.4,2.13),(.18,.14,.18),'Amethyst',2)


def create_watcher(ctx):
    ctx.sphere('Watcher floating azure spirit',(0,0,1.6),(.93,.6,.95),'BlueCrystal',2)
    ctx.sphere('Watcher giant white eye',(0,-.55,1.85),(.66,.14,.62),'Ivory',2)
    ctx.sphere('Watcher blue iris',(0,-.71,1.86),(.34,.07,.35),'BlueHide',2);ctx.sphere('Watcher deep pupil',(0,-.78,1.86),(.17,.04,.22),'Obsidian',2)
    for side in [-1,1]:ctx.curve('Watcher ethereal trailing fin',[(side*.6,0,1.6),(side*1.45,.25,2.15),(side*1.8,.55,1.5),(side*.9,.8,.8)],.13,'RiftMist')
    ctx.ring('Watcher luminous orbit',(0,0,.65),1.25,.035,'BlueCrystal')


def create_rift_ray(ctx):
    ctx.sphere('Rift ray translucent body',(0,0,1.4),(.65,1.3,.32),'RiftMist',2)
    for side in [-1,1]:
        vertices=[(0,-1.1,1.45),(side*.6,-.8,1.55),(side*2.6,.1,1.3),(side*1.7,.7,1.04),(side*.5,1.25,1.4),(0,.7,1.4)]
        ctx.mesh('Rift ray broad spectral wing',vertices,[(0,1,2,3,4,5)],'RiftMist',smooth_faces=True)
        ctx.curve('Rift ray luminous wing edge',vertices[1:5],.045,'Amethyst')
        ctx.sphere('Rift ray sapphire eye',(side*.27,-.95,1.6),(.10,.12,.08),'BlueCrystal',1)
    ctx.curve('Rift ray long curling tail',[(0,.7,1.4),(0,2.0,1.3),(.4,3.1,1.6),(.7,3.8,1.9)],.11,'RiftMist')


def create_leviathan(ctx):
    root=ctx.parent;_old_leviathan(ctx)
    rematerial_descendants(root,{'PurpleHide':ctx.materials['ObsidianScale'],'Petal':ctx.materials['RiftMist']})
    for j in range(9):
        a=j*2*PI/9;ctx.crystal('Leviathan orbiting amethyst satellite',(math.cos(a)*4.8,math.sin(a)*4.8,2.5+math.sin(a*2)),.27,1.3,'Amethyst',(.2,.4,a))
    for r in [4.7,5.4]:ctx.ring('Leviathan royal purple aura',(0,0,.3),r,.055,'Amethyst')

MONSTER_BUILDERS.update({'MagmaGuardian':create_magma_guardian,'AzureGolem':create_azure_golem,'MoonWolf':create_wolf,'StoneCentipede':create_centipede,'RiftWraith':create_wraith,'CrystalCrab':create_crab,'Watcher':create_watcher,'RiftRay':create_rift_ray,'NightLeviathan':create_leviathan})

def create_camp(ctx,index,kind,position):
    ctx.group('MonsterCamps');count,respawn=CAMP_RULES[kind]
    with ctx.root(f'Camp {index:02d}',(*position,.10),'camp') as root:
        root['camp_index']=index;root['monster_kind']=kind;root['side']='Light' if index<=6 else 'Dark';root['spawn_seconds']=20;root['respawn_seconds']=respawn;root['member_count']=count
        ctx.cylinder('Camp natural clearing',(0,0,-.01),5.45,.10,'Earth',48,.02)
        for j in range(10):
            a=j*2*PI/10;ctx.sphere('Camp edge mossy pebble',(5.35*math.cos(a),5.35*math.sin(a),.12),(.30,.26,.20),'Moss',1)
        for j in range(count):
            p=(0,0,.10) if count==1 else ((j-(count-1)/2)*2.7,0 if j==0 else .6,.10)
            scale={'MoonWolf':.85,'StoneCentipede':.85,'RiftWraith':1.15,'CrystalCrab':1.1,'MagmaGuardian':1.0,'AzureGolem':1.0}[kind]*(1 if j==0 else .68)
            with ctx.root(kind,p,'neutral',scale=scale) as creature:
                creature['monster_kind']=kind;creature['camp_index']=index;creature['member_index']=j;creature['spawn_seconds']=20;creature['respawn_seconds']=respawn;creature['side']=root['side'];creature['leader']=j==0
                MONSTER_BUILDERS[kind](ctx)
                if kind=='MoonWolf':
                    for k in range(4):ctx.crystal('Moon wolf blue dorsal crystal',(0,-.3+k*.45,2.25),.16,.7,'BlueCrystal',(.1,0,0))
        return root


def create_rift_neutrals(ctx):
    ctx.group('RiftCreatures')
    for kind,p in RIFT_SPAWNS:
        with ctx.root(kind,(*p,0),'neutral') as root:
            root['monster_kind']=kind;root['camp_index']=0;root['member_index']=0;root['spawn_seconds']=60;root['respawn_seconds']=90;MONSTER_BUILDERS[kind](ctx)
    for root in [o for o in ctx.scene.objects if o.get('category')=='boss']:
        solar=root['monster_kind']=='SolarColossus';root['spawn_seconds']=180 if solar else 420;root['respawn_seconds']=180 if solar else 240


def create_bush(ctx,position,scale=1,variant=0):
    with ctx.root('Volumetric ambush thicket',position,'bush',scale=scale) as root:
        root['concealment_zone']=True;root['radius']=2.0*scale
        for j in range(7):
            a=j*2.39996;r=.2 if j==0 else .95;ctx.sphere('Bush plump emerald leaf crown',(math.cos(a)*r,math.sin(a)*r,.75+(j%3)*.18),(.95,.78,.85),'MintLeaf' if j%3 else 'Emerald',2)
        for j in range(18):
            a=j*2.39996;ctx.crystal('Bush folded sunlit leaf',(math.cos(a)*1.2,math.sin(a)*1.2,.95),.17,.7,'MintLeaf',(math.sin(a)*.5,math.cos(a)*.5,a))
        return root


def create_forest(ctx):
    ctx.group('Ruins');ruins=[]
    for ci,center in enumerate(CLEARINGS.values()):
        for j in range(8):
            a=j*PI/4+.19;p=(center[0]+14.2*math.cos(a),center[1]+14.2*math.sin(a))
            if not ctx.clear_for_foliage(p,.1):continue
            if any(min(route_distance((p[0]+math.cos(a+PI/2)*off,p[1]+math.sin(a+PI/2)*off),r) for r in ctx.paths)<2.8 for off in [-2.8,0,2.8]):continue
            create_wall(ctx,'Forest clearing wall',(*p,ctx.height(*p)),4.4,a+PI/2,(j+ci)%2==0);ruins.append(p)
    ctx.group('Forest');positions=[];attempts=0
    while len(positions)<ctx.cfg.tree_count and attempts<35000:
        attempts+=1;p=(ctx.rng.uniform(-94,94),ctx.rng.uniform(-94,94))
        if not ctx.clear_for_foliage(p,1.2) or any(math.dist(p,q)<7.4 for q in positions) or any(math.dist(p,q)<4.7 for q in ruins):continue
        positions.append(p);o=create_tree(ctx,(*p,0),ctx.rng.uniform(5.8,7.0),len(positions)%23);o.scale.x*=1.12;o.scale.y*=1.12
    bushes=[]
    # Readable river entrances, lane corners and camp mouths; kept off the walking centreline.
    candidates=[(-42,27),(-23,39),(22,-40),(42,-24),(-54,49),(-38,58),(56,38),(45,-57),(-58,-38),(-33,-49),(53,-42),(-13,-22),(13,23)]
    for _,_,c in CAMPS:
        candidates.extend([(c[0]-4.5,c[1]+4.5),(c[0]+4.5,c[1]+4.5)])
    candidates += [(c[0]+12*math.cos(j*2.39996),c[1]+12*math.sin(j*2.39996)) for c in CLEARINGS.values() for j in range(10)]
    for p in candidates:
        if len(bushes)>=ctx.cfg.bush_count:break
        if min(route_distance(p,r) for r in ctx.lanes.values())<5.4 or route_distance(p,ctx.river)<7.5:continue
        if any(math.dist(p,c)<2.8 for c,_ in CRYSTAL_GATES) or any(math.dist(p,c)<3.4 for c in bushes):continue
        if any(math.dist(p,c)<11 for c in CLEARINGS.values()):continue
        bushes.append(p);create_bush(ctx,(*p,0),1.05+len(bushes)%3*.12,len(bushes)%17)
    ctx.registry['trees']=positions;ctx.registry['bushes']=bushes
    print('OPEN FOREST',len(positions),'playable trees;',len(bushes),'volumetric ambush bushes',flush=True)


def create_outer_landscape(ctx):
    rng=random.Random(ctx.cfg.seed+440);ctx.group('OuterLandscape');count=0
    for side in range(4):
        for j in range(10):
            t=-112+j*224/9;depth=119+(j%3)*5
            x,y=(t,-depth) if side==0 else (depth,t) if side==1 else (t,depth) if side==2 else (-depth,t)
            if any(math.dist((x,y),q)<18 for q in [(-116,43),(-116,-41),(-35,-118),(47,-118),(118,-53),(118,49)]):continue
            cap=-2.0+(y-x)/220*2.0;create_rock(ctx,'Outer forest stepped crag',(x,y,cap-9.2),(14.5,13.0,13),seed=j+side*47)
            outward=Vector((x,y)).normalized()*5.5
            create_rock(ctx,'Outer continuous lower forest shelf',(x+outward.x,y+outward.y,cap-14.5),(16,13,12),seed=400+j+side*47)
            for k in range(7):
                a=k*2.39996;px=x+math.cos(a)*rng.uniform(1,7.5);py=y+math.sin(a)*rng.uniform(1,7.5)
                if k%3:
                    o=create_tree(ctx,(px,py,cap),rng.uniform(8,12),j*4+k);o['category']='backdrop_tree'
                else:
                    with ctx.root('Outer broadleaf elder',(px,py,cap),'backdrop_tree'):
                        ctx.limb('Deciduous twisting trunk',(0,0,0),(.25,0,5),.45,.18,'Wood')
                        for q in range(7):
                            a=q*2.39996;ctx.sphere('Deciduous layered emerald crown',(math.cos(a)*1.5,math.sin(a)*1.5,5+q%3*.7),(2.0,1.8,1.9),'Emerald' if q%2 else 'PineLight',2)
                count+=1
            if j%4==1:
                create_ruin_arch(ctx,(x,y,cap),j*.7)
    ctx.registry['backdrop_tree_count']=count


def minion_cylinder(ctx,*args,rotation=(0,0,0)):
    obj=ctx.cylinder(*args);obj.rotation_euler=rotation;return obj


def create_minion_template(ctx,team,kind):
    ctx.group('MinionTemplates');ctx.collection.hide_render=True
    armor='BlueArmor' if team=='Light' else 'RedArmor';glow='BlueCrystal' if team=='Light' else 'RedCrystal'
    with ctx.root(f'Minion template {team} {kind}',(0,0,0),'minion_template') as root:
        root['template_key']=team+'_'+kind;root['team']=team;root['minion_kind']=kind;root['physics_y']=0
        def part(name,p):
            return ctx.root('Minion articulated '+name,p)
        if kind=='Guard':
            ctx.loft('Guard sturdy stone cuirass',[(0,0,.65,.44,.32),(0,0,1.45,.6,.4),(0,0,1.7,.45,.32)],armor,12,.05)
            ctx.sphere('Guard crowned helmet',(0,0,1.96),(.43,.37,.43),'Gold',2);ctx.box('Guard inset helmet visor',(0,-.36,1.98),(.48,.08,.15),'Obsidian',.025);ctx.crystal('Guard helmet glowing crest',(0,0,2.28),.17,.59,glow)
            for side in [-1,1]:
                with part('leg_left' if side<0 else 'leg_right',(side*.25,0,.75)) as o:
                    o['minion_part']='leg_left' if side<0 else 'leg_right';ctx.limb('Guard segmented shin',(0,0,0),(0,0,-.5),.19,.15,armor);ctx.box('Guard golden sabaton',(0,-.13,-.53),(.42,.6,.30),'Gold',.06)
            with part('shield',(-.74,-.12,1.3)) as o:
                o['minion_part']='shield';ctx.box('Guard enormous tower shield',(0,-.14,-.1),(.95,.25,1.6),'Gold',.12);ctx.box('Guard embossed shield face',(0,-.29,-.1),(.77,.09,1.38),armor,.10);ctx.crystal('Guard shield central jewel',(0,-.38,-.25),.17,.65,glow)
            with part('blade',(.65,0,1.38)) as o:
                o['minion_part']='blade';ctx.limb('Guard armored striking arm',(0,0,0),(.08,-.18,-.35),.17,.14,armor);ctx.box('Guard energy blade crossguard',(.08,-.18,-.15),(.50,.13,.10),'Gold',.02);ctx.crystal('Guard long luminous energy blade',(.08,-.18,-.12),.10,1.35,glow)
        elif kind=='Caster':
            ctx.loft('Caster floating embroidered cloak',[(0,.1,.38,.77,.59),(0,0,.8,.58,.42),(0,0,1.7,.38,.31)],armor,16,.025)
            ctx.loft('Caster pointed mage hood',[(0,0,1.55,.52,.44),(0,0,2.0,.45,.39),(0,.2,2.9,.02,.02)],armor,12)
            ctx.sphere('Caster shadowed hood interior',(0,-.37,1.96),(.30,.12,.32),'Obsidian',2)
            for side in [-1,1]:ctx.sphere('Caster glowing eye',(side*.12,-.49,2.01),(.07,.035,.08),glow,1)
            for j in range(5):ctx.crystal('Caster cloak crystalline stitch',((j-2)*.22,-.4,.66),.085,.38,glow)
            with part('staff',(.78,-.02,1.3)) as o:
                o['minion_part']='staff';ctx.limb('Caster golden staff shaft',(0,0,-.9),(0,0,1.0),.065,.065,'Gold');ctx.ring('Caster open staff halo',(0,0,1.0),.32,.055,'Gold').rotation_euler=(PI/2,0,0);ctx.crystal('Caster levitating staff crystal',(0,0,.86),.20,.74,glow)
        else:
            ctx.box('Siege massive stone gun carriage',(0,0,.75),(1.7,2.6,.72),armor,.14);ctx.box('Siege golden reinforced rail',(0,0,1.2),(1.5,2.4,.21),'Gold',.06)
            for side in [-1,1]:
                for axle in [-1,1]:
                    with part(f'wheel_{side}_{axle}',(side*1.03,axle*.88,.55)) as o:
                        o['minion_part']='wheel';minion_cylinder(ctx,'Siege carved golden wheel',(0,0,0),.54,.26,'Gold',16,rotation=(0,PI/2,0));minion_cylinder(ctx,'Siege crystal wheel hub',(side*.16,0,0),.19,.08,glow,12,rotation=(0,PI/2,0))
            with part('cannon',(0,0,1.52)) as o:
                o['minion_part']='cannon';minion_cylinder(ctx,'Siege reinforced cannon barrel',(0,-.4,0),.45,2.25,'Gold',16,rotation=(PI/2,0,0));minion_cylinder(ctx,'Siege obsidian muzzle bore',(0,-1.57,0),.34,.04,'Obsidian',16,rotation=(PI/2,0,0));ctx.crystal('Siege enormous charged cannon crystal',(0,-1.1,-.1),.23,.8,glow,(PI/2,0,0))
            for side in [-1,1]:ctx.crystal('Siege side energy reservoir',(side*.55,.65,1.23),.17,.75,glow)
        return root


def build_map(config):
    if bpy.app.version<(4,0,0):raise RuntimeError("Blender 4.0 or newer is required")
    config.output.mkdir(parents=True,exist_ok=True);ctx=Context(config)
    create_materials(ctx);create_combat_materials(ctx);print("MATERIALS READY",flush=True)
    create_terrain(ctx)
    for name,points in ctx.lanes.items():create_lane(ctx,name,points)
    ctx.group("Trails")
    for i,points in enumerate(ctx.paths):create_path(ctx,points,3.5,name=f"Forest trail {i+1}")
    create_river(ctx)
    for lane,p in STONE_BRIDGES:create_bridge(ctx,lane+" arched stone bridge",p)
    for name,p in ENERGY_BRIDGES:create_bridge(ctx,name+" dynamic forest bridge",p,"dawn" if name=="Dawn" else "dusk")
    for name,p in CLEARINGS.items():create_clearing(ctx,name,p)
    for team,p in BASES.items():create_nexus(ctx,team,p)
    for team,p in FOUNTAINS.items():create_fountain(ctx,team,p)
    for lane,teams in TOWERS.items():
        for team,entries in teams.items():
            for tier,x,y in entries:create_tower(ctx,team,tier,(x,y),lane)
    create_arena(ctx,"Dawn arena",BOSSES["SolarColossus"])
    create_arena(ctx,"Night Leviathan lair",BOSSES["NightLeviathan"],True)
    ctx.group("Bosses")
    create_monster(ctx,"SolarColossus",(-86,91,.76),2.05,True)
    create_monster(ctx,"NightLeviathan",(86,-86,.76),1.65,True)
    for i,kind,p in CAMPS:create_camp(ctx,i,kind,p)
    create_rift_neutrals(ctx)
    for team in ["Light","Dark"]:
        for kind in ["Guard","Caster","Siege"]:create_minion_template(ctx,team,kind)
    for i,(p,toward) in enumerate(CRYSTAL_GATES,1):create_crystal_gate(ctx,i,p,toward)
    create_gameplay_geometry(ctx);create_forest(ctx);create_environment_details(ctx);create_cliffs_and_waterfalls(ctx);create_outer_landscape(ctx);create_lighting_and_camera(ctx)
    validation=validate_scene(ctx);export_layout(ctx,validation)
    scene=ctx.scene;scene.frame_set(1)
    # Пакуем найденный системный шрифт. Процедурным материалам нечего искать на диске.
    if ctx.font:
        try:ctx.font.pack()
        except (AttributeError,RuntimeError):pass
    path=config.output/"ValleyOfShards.blend";scene.render.filepath=str(config.output/"ValleyOfShards.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    print(f"SAVED {path}",flush=True)
    if config.render:
        bpy.ops.render.render(write_still=True,scene=scene.name)
        print("OVERVIEW RENDERED",flush=True)
    if config.detail_renders:render_details(ctx)
    print("GENERATION COMPLETE",json.dumps(validation,ensure_ascii=False),flush=True)
    return ctx


def render_details(ctx):
    scene=ctx.scene;camera=scene.camera;old=(camera.location.copy(),camera.rotation_euler.copy(),camera.data.ortho_scale,scene.render.resolution_x,scene.render.resolution_y)
    shots=[("Valley_Detail",(-31,-53,66),(-20,0,1),100),
           ("Valley_Dawn",(-94,48,38),(-72,72,2),52)]
    for name,position,target,scale in shots:
        camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
        scene.render.resolution_x=1280;scene.render.resolution_y=960;scene.render.filepath=str(ctx.cfg.output/(name+".png"));bpy.ops.render.render(write_still=True,scene=scene.name)
    camera.location,camera.rotation_euler,camera.data.ortho_scale,scene.render.resolution_x,scene.render.resolution_y=old


def parse_args():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    parser=argparse.ArgumentParser(description="Generate the 200x200 Valley of Shards in Blender 4.0+")
    script=Path(__file__).resolve() if "__file__" in globals() else None
    default=(script.parent if script and script.is_file() else Path(bpy.path.abspath("//")))/"output"
    parser.add_argument("--out",type=Path,default=default);parser.add_argument("--seed",type=int,default=1649)
    parser.add_argument("--render",action="store_true");parser.add_argument("--detail-renders",action="store_true")
    parser.add_argument("--resolution",type=int,default=1440);parser.add_argument("--samples",type=int,default=32)
    parser.add_argument("--trees",type=int,default=130);parser.add_argument("--no-labels",action="store_true")
    args=parser.parse_args(argv)
    if args.trees<0 or args.trees>1000:parser.error("--trees must be between 0 and 1000")
    if args.resolution<320 or args.resolution>8192:parser.error("--resolution must be between 320 and 8192")
    if args.samples<1:parser.error("--samples must be positive")
    return Config(output=args.out.resolve(),seed=args.seed,render=args.render,detail_renders=args.detail_renders,resolution=args.resolution,samples=args.samples,tree_count=args.trees,labels=not args.no_labels)


if __name__=="__main__":
    build_map(parse_args())
