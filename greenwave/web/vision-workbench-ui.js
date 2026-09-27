'use strict';
const VisionWorkbenchUI={
 latest:null,received:0,
 signal(line,route){const s=this.latest;if(!s?.preview_fresh||s.source_type!=='CAMERA'||performance.now()-this.received>1000)return null;return s.signals?.find(item=>item.stop_line_id===line&&item.route_id===route.route_id&&item.geometry_hash===route.geometry_hash&&item.direction==='FORWARD');},
 recordings(entries){const select=document.getElementById('cv-history-capture');if(!select)return;const old=select.value;select.replaceChildren(...entries.map(entry=>{const option=document.createElement('option');option.value=entry.session_id;option.textContent=entry.started_utc+' · '+entry.session_id.slice(0,8);return option;}));if(entries.some(e=>e.session_id===old))select.value=old;},
 update(status){this.latest=status;this.received=performance.now();this.refresh?.();},
 mount({api,control,state}){
  const $=id=>document.getElementById(id);let selectedTrack='',selectedLine='',history=null;
  const message=error=>$('cv-feedback').textContent=error.message||String(error);
  const post=async body=>await(await api('/api/vision/workbench',body)).json();
  function refresh(){
   const status=VisionWorkbenchUI.latest,route=state()?.mapping?.selected_route;
   const tracks=status?.preview_fresh?status.vision?.tracks||[]:[];
   const trackSelect=$('cv-track');selectedTrack=trackSelect.value||selectedTrack;
   trackSelect.replaceChildren(...tracks.map(track=>{const option=document.createElement('option');option.value=track.track_id;option.textContent=track.track_id.split(':').at(-1)+' · '+track.state;return option;}));if(tracks.some(t=>t.track_id===selectedTrack))trackSelect.value=selectedTrack;
   const lineSelect=$('cv-line');selectedLine=lineSelect.value||selectedLine;
   lineSelect.replaceChildren(...(route?.stop_lines||[]).map(line=>{const option=document.createElement('option');option.value=line.stop_line_id;option.textContent=(line.source?.label||line.stop_line_id)+' · '+line.direction+' / '+line.movement;return option;}));if(route?.stop_lines.some(l=>l.stop_line_id===selectedLine))lineSelect.value=selectedLine;
   $('cv-assign').disabled=!tracks.length||!route;$('cv-unassign').disabled=!tracks.length;
   $('cv-candidates').textContent=(status?.candidates||[]).map(c=>c.name+' · '+Math.round(c.distance_m)+' m (propozycja)').join(' | ')||'Brak pewnej propozycji GPS. Wybierz właściwy kierunek i manewr ręcznie.';
   $('cv-associations').replaceChildren(...(status?.associations||[]).map(a=>{const row=document.createElement('p');const d=a.data,s=status.signals?.find(s=>s.stop_line_id===d.stop_line_id);row.textContent=`${d.track_id.split(':').at(-1)} → ${d.display_name} · ${d.direction}/${d.movement} · ${s?.state||'UNKNOWN'} · ${s?.historical?'FILM HISTORYCZNY':'obserwacja kamery'}${s?.conflict_reason?' · konflikt MANUAL/CV':''}`;return row;}));
  }
  this.refresh=refresh;
  $('cv-assign').onclick=async()=>{try{const route=state()?.mapping?.selected_route;await post({command:'assign',track_id:$('cv-track').value,route_id:route.route_id,geometry_hash:route.geometry_hash,stop_line_id:$('cv-line').value});message('Przypisano ręcznie; utrata ciągłości unieważni przypisanie.');}catch(error){message(error);}};
  $('cv-unassign').onclick=async()=>{try{await post({command:'unassign',track_id:$('cv-track').value});message('Przypisanie usunięte.');}catch(error){message(error);}};
  async function loadHistory(before=null){try{const id=$('cv-history-capture').value;if(!id)return;history=await(await api('/api/vision/history?capture_id='+id+(before?'&before='+before:''))).json();renderHistory();}catch(error){message(error);}}
  function renderHistory(){
   $('cv-history-info').textContent=`${history.entries.length} zdarzeń na stronie · synchronizacja GPS niezweryfikowana${history.import_progress.pending?' · import trwa, odśwież ponownie':''}`;
   $('cv-history-older').disabled=!history.next_cursor;
   $('cv-history').replaceChildren(...history.entries.map(entry=>{
    const d=entry.evidence.observation.data,row=document.createElement('div');row.className='capture-recording';
    const title=document.createElement('p');title.textContent=`${d.event_type} · ${d.detection.state} · ${d.detection.track_id.split(':').at(-1)} · ${entry.review_status} · PTS ${entry.media_pts_seconds??'brak'}`;row.append(title);
    const decision=entry.decisions.at(-1);if(decision){const note=document.createElement('p');note.textContent=`${decision.reviewer} · ${decision.association?.data.display_name||'odrzucone'} · decyzji: ${entry.decisions.length}`;row.append(note);}
    const play=document.createElement('button');play.textContent='Odtwórz od zdarzenia';play.disabled=entry.media_segment==null||entry.media_pts_seconds==null;play.onclick=()=>control({command:'replay',capture_id:history.capture_id,segment:entry.media_segment,seek_seconds:Math.max(0,entry.media_pts_seconds-.5)});row.append(play);
    const clip=document.createElement('button');clip.textContent='Otwórz oryginalny film';clip.disabled=entry.media_segment==null;clip.onclick=async()=>{try{await post({command:'media-access'});const video=$('cv-video');video.src=`/api/vision/media?capture_id=${history.capture_id}&segment=${entry.media_segment}`;video.hidden=false;video.onloadedmetadata=()=>{video.currentTime=entry.media_pts_seconds||0;};video.onerror=()=>message('Przeglądarka nie obsługuje tego kodeka. Użyj „Odtwórz od zdarzenia” powyżej.');video.load();}catch(error){message(error);}};row.append(clip);
    for(const [label,status] of [['Potwierdź i przypisz','ACCEPTED'],['Odrzuć','REJECTED']]){const button=document.createElement('button');button.textContent=label;button.onclick=async()=>{try{const route=state()?.mapping?.selected_route;await post({command:'review',capture_id:history.capture_id,event_id:entry.event_id,status,reviewer:$('cv-reviewer').value,...(status==='ACCEPTED'?{route_id:route?.route_id,geometry_hash:route?.geometry_hash,stop_line_id:$('cv-line').value}:{})});await loadHistory(history.before);}catch(error){message(error);}};row.append(button);}
    const detail=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Dowody i decyzje';const pre=document.createElement('pre');pre.textContent=JSON.stringify(entry,null,2);detail.append(summary,pre);row.append(detail);return row;
   }));
   for(const entry of history.manual_entries||[]){const row=document.createElement('p');const payload=entry.payload||entry;row.textContent=`MANUAL · ${payload.stop_line_id||'punkt'} · ${payload.state||'—'} · ${payload.timestamp||entry.timestamp||'czas logu'} (porównanie osobne, bez automatycznej synchronizacji)`;$('cv-history').append(row);}
   $('cv-gps').disabled=!history.run_id;
  }
  $('cv-history-load').onclick=()=>loadHistory();
  $('cv-history-older').onclick=()=>loadHistory(history?.next_cursor);
  $('cv-history-export').onclick=async()=>{try{const id=$('cv-history-capture').value;if(!id)return;const before=history?.capture_id===id?history.before:null;const blob=await(await api('/api/vision/export?capture_id='+id+(before?'&before='+before:''))).blob();const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='cv-review-'+id.slice(0,8)+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(error){message(error);}};
  $('cv-gps').onclick=async()=>{try{if(!history?.run_id)return;const select=$('gps-replay-run');if(![...select.options].some(o=>o.value===history.run_id)){const option=document.createElement('option');option.value=history.run_id;option.textContent=history.run_id;select.append(option);}select.value=history.run_id;$('gps-replay-load').click();$('gps-replay').open=true;message('Wczytano powiązany log GPS osobno. Film i GPS nie są automatycznie zsynchronizowane.');}catch(error){message(error);}};
  refresh();
 }
};
if(typeof module!=='undefined'&&module.exports)module.exports=VisionWorkbenchUI;
