// Small DOM-free model: binary decoding, map coordinates and interactive crystal state.
export const toWorld=p=>[p[0],p[2]??0,-p[1]];
export const coord=p=>`${Number(p[0].toFixed(1))}, ${Number(p[1].toFixed(1))}`;
export function decodeScenePart(buffer){
 const view=new DataView(buffer);if(buffer.byteLength<4)throw new Error('Truncated scene');const size=view.getUint32(0,true);if(size>buffer.byteLength-4)throw new Error('Invalid scene header');
 const header=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,4,size))),base=4+size;
 const types={position:Float32Array,normal:Int16Array,color:Uint16Array,uv:Float32Array,index:Uint32Array,owner:Uint32Array};
 return header.meshes.map(spec=>{const mesh={actor:spec.actor,material:spec.material};for(const [key,Type] of Object.entries(types)){const a=spec[key],start=base+a.offset,bytes=a.count*Type.BYTES_PER_ELEMENT;if(a.offset%4||start+bytes>buffer.byteLength||a.count<0)throw new Error('Invalid geometry range');mesh[key]=new Type(buffer,start,a.count);}
 const n=mesh.position.length/3;if(!Number.isInteger(n)||mesh.normal.length!==n*3||mesh.color.length!==n*3||mesh.uv.length!==n*2||mesh.index.length%3||mesh.owner.length!==mesh.index.length/3)throw new Error('Invalid mesh streams');return mesh;});
}
export function routeLength(points){let d=0;for(let i=1;i<points.length;i++)d+=Math.hypot(points[i].X-points[i-1].X,points[i].Y-points[i-1].Y);return d;}
export function routeAt(points,d){for(let i=1;i<points.length;i++){const a=points[i-1],b=points[i],l=Math.hypot(b.X-a.X,b.Y-a.Y);if(d<=l){const t=Math.max(0,d/l);return {X:a.X+(b.X-a.X)*t,Y:a.Y+(b.Y-a.Y)*t,dx:(b.X-a.X)/l,dy:(b.Y-a.Y)/l};}d-=l;}const p=points.at(-1);return {...p,dx:1,dy:-1};}
export class MapState{
 constructor(entities){this.time=0;this.selected=0;this.crystals=new Map(entities.filter(e=>e.category==='crystal_gate').map(e=>[e.id,{hp:24,brokenAt:null,restoredAt:-1000}]));}
 select(id){this.selected=id;}
 hit(id,damage=4){const c=this.crystals.get(id);if(!c||c.hp===0||!Number.isFinite(damage)||damage<=0)return false;c.hp=Math.max(0,c.hp-damage);if(c.hp===0)c.brokenAt=this.time;return true;}
 restore(id){const c=this.crystals.get(id);if(!c||c.hp===24)return false;c.hp=24;c.brokenAt=null;c.restoredAt=this.time;return true;}
 tick(dt){if(!Number.isFinite(dt)||dt<0)return;this.time+=dt;for(const [id,c]of this.crystals)if(c.hp===0&&this.time-c.brokenAt>=60)this.restore(id);}
 remaining(id){const c=this.crystals.get(id);return c&&c.brokenAt!==null?Math.max(0,60-(this.time-c.brokenAt)):0;}
}
export const names={Wolf:'Лунные волки',Spider:'Кристальный паук',GiantSpider:'Гигантский паук',Elemental:'Элементали',Boar:'Лесные кабаны',Golem:'Лазурные големы',GoldenGolem:'Золотой голем',ForestSpirit:'Лесные духи',Harpy:'Гарпии',Bear:'Древние медведи',GiantScorpion:'Гигантский скорпион',SolarColossus:'Солнечный Колосс',NightLeviathan:'Ночной Левиафан'};
export function describe(entity){const p=entity.properties,category=entity.category;
 if(category==='tower')return {title:`Башня ${p.team==='Light'?'Света':'Тьмы'} · T${p.tier}`,tag:`${{Top:'Верхняя',Mid:'Центральная',Bot:'Нижняя'}[p.lane]} линия`,description:p.team==='Light'?'Мрамор и золото защищают парящий синий кристалл.':'Тёмный камень, бронза и алое сердце укрепления.',stats:[['Прочность',`${p.health} HP`],['Координаты',coord(entity.position)]]};
 if(category==='nexus')return {title:p.team==='Light'?'База Света':'База Тьмы',tag:'Нексус',description:p.team==='Light'?'Мрамор, водяные дуги и золотые арки вокруг высокого кристалла. Отдельный лечебный фонтан находится за Нексусом.':'Алый кристалл пылает в цитадели среди обсидиановых шпилей.',stats:[['Координаты',coord(entity.position)]]};
 if(category==='boss')return {title:names[p.monster_kind],tag:'Босс долины',description:p.monster_kind==='SolarColossus'?'Древний золотой исполин охраняет северную часть Арены Рассвета.':'Крылатый фиолетовый змей обвивает тёмную арену.',stats:[['Координаты',coord(entity.position)]]};
 if(category==='camp')return {title:names[p.monster_kind],tag:`Лесной лагерь ${p.camp_index}`,description:'Один из двенадцати лагерей, расположенных между линиями и боевыми полянами.',stats:[['Координаты',coord(entity.position)]]};
 if(category==='crystal_gate')return {title:`Кристальный затвор ${p.gate_index}`,tag:'Разрушаемый проход',description:'24 прочности: 6 ближних ударов или 8 дальних. Затвор открывает короткий проход и восстанавливается через 60 секунд, когда проход свободен.',stats:[['Прочность','24 HP'],['Координаты',coord(entity.position)]]};
 if(category==='energy_bridge')return {title:p.bridge_kind==='dawn'?'Мост Рассвета':'Мост Сумерек',tag:'Динамический лесной переход',description:p.bridge_kind==='dawn'?'Белый камень, золото и тёплые руны. Открывается в 2:00; дальше чередуется с Сумерками каждые две минуты.':'Обсидиан и пурпурные руны. Первый раз открывается в 4:00. За 15 секунд до закрытия мост мигает; герои плавно уходят на ближайший берег.',stats:[['Первые две минуты','Оба закрыты'],['Период','120 секунд'],['Координаты',coord(entity.position)]]};
 if(category==='fountain')return {title:p.team==='Light'?'Фонтан Света':'Фонтан Тьмы',tag:'Зона восстановления',description:'Возвышенная руническая платформа за Нексусом. Лечит только союзных героев в радиусе 6,6 единицы.',stats:[['Здоровье','+300 HP/с'],['Мана','+180 MP/с'],['Координаты',coord(entity.position)]]};
 if(category==='hero')return {title:`${p.team==='Light'?'Страж Рассвета':'Страж Сумерек'} ${p.hero_index+1}`,tag:p.controllable?'Ваш герой':'Герой локального плейтеста',description:'Персонаж движется по линиям, лесным тропам и открытым мостам. Физика и снаряды остаются на плоскости Y = 0.',stats:[['Здоровье','1200 HP'],['Мана','500 MP']]};
 if(category==='stone_bridge')return {title:'Каменный мост',tag:'Постоянный переход',description:'Арочный пролёт из светлого камня с золотой инкрустацией и фонарями.',stats:[['Координаты',coord(entity.position)]]};
 return {title:'Боевая поляна',tag:'Открытое пространство',description:'Круглая площадка без деревьев для встречи команд.',stats:[['Координаты',coord(entity.position)]]};
}
