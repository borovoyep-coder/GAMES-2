const $=id=>document.getElementById(id);let bundle;
const id=new URLSearchParams(location.search).get('bundle')||'unity05';
try{
 const response=await fetch('/downloads.json');if(!response.ok)throw new Error();const manifest=await response.json();bundle=manifest.Bundles[id];if(!bundle)throw new Error();
 $('title').textContent=bundle.Title;$('description').textContent=bundle.Description;
 $('download').textContent=`Скачать ZIP · ${(bundle.Bytes/1048576).toFixed(1)} МБ`;$('download').disabled=false;
 $('other').href=id==='unity05'?'?bundle=studio05':'?bundle=unity05';$('other').textContent=id==='unity05'?'Исходники Blender':'Проект Unity';
}catch{$('title').textContent='Загрузка временно недоступна';$('description').textContent='Вернитесь к карте и попробуйте снова.';}
$('download').onclick=async()=>{
 if(!bundle)return;$('download').disabled=true;$('progress').hidden=false;$('progress').value=0;$('status').textContent='Загружаем архив…';
 try{
  const blobs=[];let completed=0;
  for(const chunk of bundle.Chunks){
   const response=await fetch('/'+chunk.File);if(!response.ok)throw new Error();const reader=response.body.getReader(),pieces=[];let received=0;
   while(true){const {value,done}=await reader.read();if(done)break;pieces.push(value);received+=value.byteLength;$('progress').value=(completed+received)/bundle.Bytes*100;$('status').textContent=`Загружено ${((completed+received)/1048576).toFixed(1)} из ${(bundle.Bytes/1048576).toFixed(1)} МБ`;}
   const blob=new Blob(pieces);if(blob.size!==chunk.Bytes)throw new Error();
   if(crypto.subtle&&chunk.Sha256){const digest=await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()),actual=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');if(actual!==chunk.Sha256)throw new Error();}
   blobs.push(blob);completed+=blob.size;
  }
  const zip=new Blob(blobs,{type:'application/zip'}),url=URL.createObjectURL(zip),link=document.createElement('a');link.href=url;link.download=bundle.Name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);$('status').textContent='Архив готов. Загрузка ZIP началась.';
 }catch{$('status').textContent='Не удалось загрузить архив целиком. Повторите попытку.';}
 finally{$('download').disabled=false;}
};
