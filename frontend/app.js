'use strict';
const $ = (id) => document.getElementById(id);
const api = (p, o) => fetch(p, o).then(r => r.json());

/* ── Iconos (SVG inline, estilo Lucide, sin CDN) ───────────────────────── */
const ICONS = {
  scan:'<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
  cpu:'<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
  clock:'<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  film:'<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18M3 7.5h4M3 12h18M3 16.5h4M17 3v18M17 7.5h4M17 16.5h4"/>',
  play:'<polygon points="6 3 20 12 6 21 6 3"/>',
  stop:'<rect width="14" height="14" x="5" y="5" rx="2"/>',
  undo:'<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  trash:'<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M10 11v6M14 11v6"/>',
  route:'<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
  layers:'<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 12.5-9.17 4.16a2 2 0 0 1-1.66 0L2 12.5"/><path d="m22 17.5-9.17 4.16a2 2 0 0 1-1.66 0L2 17.5"/>',
  download:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
  alert:'<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4M12 17h.01"/>',
  activity:'<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  eye:'<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  car:'<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/>',
  shield:'<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
  face:'<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" x2="9.01" y1="9" y2="9"/><line x1="15" x2="15.01" y1="9" y2="9"/>',
  sliders:'<line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/><line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/><line x1="1" x2="7" y1="14" y2="14"/><line x1="9" x2="15" y1="8" y2="8"/><line x1="17" x2="23" y1="16" y2="16"/>',
  'mouse-pointer':'<path d="M12.586 12.586 19 19"/><path d="M3.688 3.037a.497.497 0 0 0-.651.651l6.5 15.999a.501.501 0 0 0 .947-.062l1.569-6.083a2 2 0 0 1 1.448-1.479l6.124-1.579a.5.5 0 0 0 .063-.947z"/>',
  timer:'<line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="12" y1="14" y2="9"/><circle cx="12" cy="14" r="8"/>',
  x:'<path d="M18 6 6 18M6 6l12 12"/>',
};
function svg(n){ return `<svg viewBox="0 0 24 24">${ICONS[n]||''}</svg>`; }
function hydrateIcons(root){ (root||document).querySelectorAll('i[data-ico]').forEach(el=>{ if(!el.firstChild) el.innerHTML=svg(el.dataset.ico); }); }

const PALETTE = ['#E19100','#2D6CDF','#129A6B','#7C5CE0','#E5484D','#0EA5A5','#6FA80C'];
const SEV = { critical:'#E5484D', warning:'#E19100', info:'#2D6CDF', ok:'#129A6B' };
const MODCOL = { Garaje:'#E19100', Vigilancia:'#E5484D', Rostros:'#129A6B' };

/* Config por caso de uso */
const UC = {
  garaje:     { det:'vehiculos', tool:'cochera',    drawLbl:'Dibujar cochera', cfg:'Dibuja las cocheras', ph:'cocheras',
                title:'Garaje / Cocheras', need:(z)=>z.some(x=>x.type==='cochera'), msg:'Dibuja al menos una cochera' },
  vigilancia: { det:'personas',  tool:'vigilancia', drawLbl:'Dibujar zona',    cfg:'Dibuja las zonas',    ph:'zonas vigiladas',
                title:'Vigilancia de zonas', need:(z)=>z.some(x=>x.type==='vigilancia'), msg:'Dibuja al menos una zona vigilada' },
  rostros:    { det:'rostros',   tool:null,         drawLbl:'—',               cfg:'Sin zonas (automático)', ph:'captura de rostros',
                title:'Captura de rostros', need:()=>true, msg:'' },
};

const st = { usecase:'garaje', video:null, tool:null, zones:[], draft:[], streaming:false, statusTimer:null, videoStem:'' };

/* ── init ──────────────────────────────────────────────────────────────── */
(async function init(){
  hydrateIcons();
  const d = await api('/api/videos');
  $('devicePill').textContent = d.device;
  $('tarifaTag').textContent = `S/ ${(d.tarifa_hora??5).toFixed(2)} / hora`;
  const sel = $('videoSelect');
  sel.innerHTML = d.videos.length
    ? d.videos.map(v=>`<option>${v}</option>`).join('')
    : '<option value="">(coloca .mp4 en videos/)</option>';
  $('confRange').value = d.default_conf ?? 0.30;
  $('confVal').textContent = (+$('confRange').value).toFixed(2);
  tickClock(); setInterval(tickClock, 1000);
  applyUsecase();
  if (d.videos.length){ sel.value=d.videos[0]; await loadVideo(d.videos[0]); }
})();
function tickClock(){ $('clock').textContent = new Date().toLocaleTimeString('es-PE',{hour:'2-digit',minute:'2-digit',second:'2-digit'}); }
$('confRange').addEventListener('input', e=>{ $('confVal').textContent=(+e.target.value).toFixed(2); });

/* ── caso de uso ───────────────────────────────────────────────────────── */
document.querySelectorAll('.uc').forEach(b=>b.onclick=()=>{
  if(st.streaming){ toast('Detén el proceso para cambiar de módulo'); return; }
  document.querySelectorAll('.uc').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');
  st.usecase=b.dataset.uc; st.tool=null; st.draft=[];
  applyUsecase();
});
function applyUsecase(){
  const u=UC[st.usecase];
  $('ucTitle').textContent=u.title;
  $('drawLbl').textContent=u.drawLbl;
  $('stepCfgTxt').textContent=u.cfg;
  $('phCfg').textContent=u.ph;
  $('drawBtn').dataset.active='0';
  $('drawBtn').disabled = !u.tool;
  document.querySelectorAll('.mod-panel').forEach(p=>p.style.display=(p.dataset.mod===st.usecase)?'block':'none');
  renderChips(); redraw(); updateSteps();
}

/* zonas visibles según módulo */
function visibleZones(){ const t=UC[st.usecase].tool; return t?st.zones.filter(z=>z.type===t):[]; }

/* ── carga de video ────────────────────────────────────────────────────── */
async function loadVideo(name){
  st.video=name; st.videoStem=name.replace(/\.[^.]+$/,''); st.streaming=false; stopStream();
  $('placeholder').style.display='none';
  const img=$('frameImg'); img.style.display='block';
  img.onload=()=>{ sizeEditor(); redraw(); };
  img.src=`/api/video/${encodeURIComponent(name)}/frame?t=${Date.now()}`;
  const cfg=await api(`/api/video/${encodeURIComponent(name)}/zones`);
  st.zones=(cfg.zones||[]).map((z,i)=>({...z,color:z.color||PALETTE[i%PALETTE.length]}));
  st.draft=[]; renderChips(); redraw(); updateSteps();
}
$('videoSelect').addEventListener('change', e=>{ if(e.target.value) loadVideo(e.target.value); });

/* ── geometría editor ──────────────────────────────────────────────────── */
function imgRect(){
  const img=$('frameImg'), vp=$('viewport');
  const cw=vp.clientWidth, ch=vp.clientHeight;
  const nw=img.naturalWidth||cw, nh=img.naturalHeight||ch;
  const s=Math.min(cw/nw, ch/nh), w=nw*s, h=nh*s;
  return { x:(cw-w)/2, y:(ch-h)/2, w, h };
}
function sizeEditor(){ const vp=$('viewport'), cv=$('editor'); cv.width=vp.clientWidth; cv.height=vp.clientHeight; }
window.addEventListener('resize', ()=>{ sizeEditor(); redraw(); });
function toNorm(cx,cy){ const r=imgRect(); return [(cx-r.x)/r.w,(cy-r.y)/r.h]; }
function toPx(nx,ny){ const r=imgRect(); return [r.x+nx*r.w, r.y+ny*r.h]; }

/* ── herramienta de dibujo ─────────────────────────────────────────────── */
$('drawBtn').onclick=()=>toggleTool();
function toggleTool(){
  const t=UC[st.usecase].tool;
  if(!t) return;
  st.tool=(st.tool===t)?null:t; st.draft=[];
  $('drawBtn').dataset.active=st.tool?'1':'0';
  const h=$('hint');
  if(st.tool){ h.style.display='block'; h.textContent='Clic para marcar puntos · doble clic para cerrar'; }
  else h.style.display='none';
  redraw();
}
$('editor').addEventListener('click', e=>{
  if(!st.tool||st.streaming) return;
  const r=$('editor').getBoundingClientRect();
  const [nx,ny]=toNorm(e.clientX-r.left, e.clientY-r.top);
  if(nx<0||nx>1||ny<0||ny>1) return;
  st.draft.push([nx,ny]);
  redraw();
});
$('editor').addEventListener('dblclick', e=>{
  if(!st.tool||st.streaming) return;
  if(st.draft.length<3){ toast('Marca al menos 3 puntos'); return; }
  const type=st.tool;
  const name=prompt(type==='cochera'?'Nombre de la cochera (ej. "Cochera 1"):':'Nombre de la zona (ej. "Patio"):');
  if(!name) return;
  const color=PALETTE[st.zones.length%PALETTE.length];
  st.zones.push({ id:'z'+(st.zones.length+1)+'_'+Date.now().toString(36), name, type, color, points:st.draft.slice() });
  st.draft=[]; toggleTool(); afterEdit();
});
$('undoBtn').onclick=()=>{
  if(st.draft.length){ st.draft.pop(); redraw(); return; }
  const vis=visibleZones();
  if(vis.length){ const last=vis[vis.length-1]; st.zones=st.zones.filter(z=>z!==last); }
  afterEdit();
};
$('clearBtn').onclick=()=>{
  const t=UC[st.usecase].tool;
  if(t) st.zones=st.zones.filter(z=>z.type!==t);
  st.draft=[]; afterEdit();
};
function afterEdit(){ renderChips(); redraw(); updateSteps(); }

/* ── dibujo overlay ────────────────────────────────────────────────────── */
function redraw(){
  const cv=$('editor'); if(!cv.width) sizeEditor();
  const ctx=cv.getContext('2d'); ctx.clearRect(0,0,cv.width,cv.height);
  if(st.streaming) return;
  visibleZones().forEach(z=>drawPoly(ctx,z.points,z.color,z.name));
  if(st.draft.length) drawPoly(ctx,st.draft,'#F26A21','',true);
}
function drawPoly(ctx,pts,color,label,dashed){
  if(!pts.length) return; ctx.save();
  ctx.beginPath(); pts.forEach((p,i)=>{ const [x,y]=toPx(...p); i?ctx.lineTo(x,y):ctx.moveTo(x,y); });
  if(!dashed) ctx.closePath();
  ctx.fillStyle=hexA(color,.16); ctx.fill();
  ctx.lineWidth=2.5; ctx.strokeStyle=color; if(dashed)ctx.setLineDash([7,5]); ctx.stroke();
  pts.forEach(p=>{ const [x,y]=toPx(...p); dot(ctx,x,y,color); });
  if(label){ const [x,y]=toPx(...pts[0]); ctx.setLineDash([]); ctx.fillStyle=color; ctx.font='700 13px Inter,sans-serif'; ctx.fillText(label,x+5,y-7); }
  ctx.restore();
}
function dot(ctx,x,y,c){ ctx.beginPath(); ctx.arc(x,y,4.5,0,7); ctx.fillStyle=c; ctx.fill(); ctx.lineWidth=2; ctx.strokeStyle='#fff'; ctx.stroke(); }
function hexA(h,a){ h=h.replace('#',''); return `rgba(${parseInt(h.slice(0,2),16)},${parseInt(h.slice(2,4),16)},${parseInt(h.slice(4,6),16)},${a})`; }

function renderChips(){
  const wrap=$('zoneChips'); let html='';
  visibleZones().forEach(z=>{ const idx=st.zones.indexOf(z); html+=chip(z.name,z.color,z.type==='cochera'?'car':'shield',idx); });
  wrap.innerHTML=html; hydrateIcons(wrap);
  $('noZones').style.display=html?'none':'inline';
  wrap.querySelectorAll('.x').forEach(el=>el.onclick=()=>{ st.zones.splice(+el.dataset.idx,1); afterEdit(); });
}
function chip(text,color,icon,idx){
  return `<span class="chip" style="background:${hexA(color,.1)};color:${color};border-color:${hexA(color,.35)}"><i data-ico="${icon}"></i>${text}<span class="x" data-idx="${idx}"><i data-ico="x"></i></span></span>`;
}

/* ── pasos ─────────────────────────────────────────────────────────────── */
function updateSteps(){
  const hasVideo=!!st.video, hasCfg=UC[st.usecase].need(st.zones);
  setStep(1, hasVideo?'done':'active');
  setStep(2, !hasVideo?'':(hasCfg?'done':'active'));
  setStep(3, st.streaming?'active':(hasVideo&&hasCfg?'active':''));
}
function setStep(n,state){ const el=document.querySelector(`.step[data-step="${n}"]`); el.className='step'+(state?' '+state:''); }

/* ── start / stop ──────────────────────────────────────────────────────── */
$('startBtn').onclick=start; $('stopBtn').onclick=stop;
async function start(){
  if(!st.video){ toast('Elige un video'); return; }
  if(!UC[st.usecase].need(st.zones)){ toast(UC[st.usecase].msg); if(!st.tool) toggleTool(); return; }
  await saveZones();
  const r=await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({video:st.video, conf:+$('confRange').value, detector:UC[st.usecase].det})});
  if(r.error){ toast(r.error); return; }
  st.streaming=true; redraw();
  $('frameImg').style.display='none';
  const s=$('stream'); s.style.display='block'; s.src='/stream?t='+Date.now();
  $('startBtn').disabled=true; $('stopBtn').disabled=false;
  $('liveDot').className='dot on'; $('liveTxt').textContent='Procesando';
  $('vpBadgeTxt').textContent='Análisis en vivo';
  $('procTxt').textContent='Cargando modelo…';
  $('procOverlay').style.display='flex';
  updateSteps();
  if(st.statusTimer) clearInterval(st.statusTimer);
  st.statusTimer=setInterval(poll,500);
}
async function stop(){ await fetch('/api/stop',{method:'POST'}); finishUI(); }
function stopStream(){ const s=$('stream'); s.style.display='none'; s.src=''; }
function finishUI(){
  st.streaming=false;
  $('procOverlay').style.display='none';
  $('startBtn').disabled=false; $('stopBtn').disabled=true;
  $('liveDot').className='dot'; $('liveTxt').textContent='Listo';
  $('vpBadgeTxt').textContent='Resultado';
  if(st.statusTimer){ clearInterval(st.statusTimer); st.statusTimer=null; }
  if(st.video) $('videoSelect').value=st.video;
  updateSteps();
}
function saveZones(){ return fetch(`/api/video/${encodeURIComponent(st.video)}/zones`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({zones:st.zones})}); }

/* ── poll / render ─────────────────────────────────────────────────────── */
async function poll(){
  const s=await api('/api/status');
  if(st.streaming){
    if(s.has_frame){ $('procOverlay').style.display='none'; }
    else { $('procOverlay').style.display='flex'; $('procTxt').textContent=s.model_ready?'Procesando…':'Cargando modelo…'; }
  }
  $('progressBar').style.width=(100*(s.progress||0))+'%';
  $('kDets').textContent=s.dets_frame??0;
  $('kOcupadas').textContent=`${s.ocupadas??0}/${(s.cocheras||[]).length}`;
  $('kIntrusiones').textContent=s.intrusiones??0;
  $('kRostros').textContent=s.rostros_total??0;
  $('rTotal').textContent=s.rostros_total??0;
  $('rFrame').textContent=s.dets_frame??0;
  $('liveTxt').textContent=`${s.video_time||''} / ${s.duration||''}`;
  renderCocheras(s.cocheras||[], s.ingresos??0);
  renderVigilancia(s.vigilancia||[]);
  renderFaces(s.rostros||[], s.video_stem||st.videoStem, s.rostros_total??0);
  if(s.timeline) drawFlow(s.timeline);
  renderAlerts(s.alerts||[]);
  if(s.finished){ finishUI(); toast('Procesamiento terminado · CSV listo'); }
}
function renderCocheras(list, ingresos){
  const el=$('cochTable');
  if(!list.length){ el.innerHTML='<div class="zb-empty" style="padding:10px">Dibuja cocheras sobre el video para medir ocupación y cobro.</div>'; }
  else{
    let h='<div class="row head"><span>Cochera</span><span>Tiempo</span><span>Usos</span><span>Cobro</span></div>';
    list.forEach(c=>{ h+=`<div class="row"><span style="display:flex;align-items:center;gap:7px"><span class="dot-s" style="background:${c.color}"></span>${c.name} <span class="estado ${c.estado}">${c.estado}</span></span><span>${c.estado==='ocupada'?c.cur:c.total}</span><span style="text-align:center">${c.ocupaciones}</span><span style="font-weight:700">S/ ${c.cobro_total.toFixed(2)}</span></div>`; });
    el.innerHTML=h;
  }
  $('ingresosTotal').textContent=`S/ ${(+ingresos).toFixed(2)}`;
}
function renderVigilancia(list){
  const el=$('vigTable');
  if(!list.length){ el.innerHTML='<div class="zb-empty" style="padding:10px">Dibuja zonas vigiladas para detectar intrusiones.</div>'; return; }
  let h='<div class="row head"><span>Zona</span><span>Ahora</span><span>Intrus.</span><span>Máx.</span></div>';
  list.forEach(z=>{ const hot=z.present>0;
    h+=`<div class="row"><span style="display:flex;align-items:center;gap:7px"><span class="dot-s" style="background:${hot?'#E5484D':z.color}"></span>${z.name}</span><span style="font-weight:700;color:${hot?'#E5484D':'inherit'}">${z.present}</span><span style="text-align:center">${z.intrusiones}</span><span>${z.max_dwell}</span></div>`; });
  el.innerHTML=h;
}
function renderFaces(list, stem, total){
  $('galCount').textContent=total;
  const el=$('facesGrid');
  if(!list.length){ el.innerHTML='<div class="ps-empty">Aún no hay capturas — usa el módulo Rostros.</div>'; return; }
  el.innerHTML=list.map(f=>`<div class="face-card"><img src="/rostros/${encodeURIComponent(stem)}/${encodeURIComponent(f.file)}?px=${f.px}" loading="lazy"/><div class="fc-id">ID ${f.id}</div><div class="fc-t">${f.t}</div></div>`).join('');
}
function renderAlerts(al){
  $('alertCount').textContent=al.length;
  $('noAlerts').style.display=al.length?'none':'block';
  $('alertRows').innerHTML=[...al].reverse().map(a=>`<tr><td style="font-variant-numeric:tabular-nums">${a.video_time}</td><td><span class="mtag" style="background:${hexA(MODCOL[a.modulo]||'#2D6CDF',.1)};color:${MODCOL[a.modulo]||'#2D6CDF'}">${a.modulo}</span></td><td><span class="sev"><span class="d" style="background:${SEV[a.severity]||'#2D6CDF'}"></span>${a.tipo}</span></td><td class="hide-sm">${a.detalle}</td></tr>`).join('');
}

/* ── flow chart ────────────────────────────────────────────────────────── */
function drawFlow(tl){
  const cv=$('flowChart'); const dpr=window.devicePixelRatio||1;
  const w=cv.clientWidth, h=cv.clientHeight; cv.width=w*dpr; cv.height=h*dpr;
  const ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,w,h);
  if(!tl.length) return;
  const pad={l:28,r:10,t:12,b:20}, gw=w-pad.l-pad.r, gh=h-pad.t-pad.b;
  const maxT=Math.max(1,tl[tl.length-1].t);
  const maxV=Math.max(...tl.map(p=>Math.max(p.dets,p.ocupadas,p.rostros)),1);
  const X=t=>pad.l+(t/maxT)*gw, Y=v=>pad.t+gh-(v/maxV)*gh;
  ctx.strokeStyle='#EEF1F5'; ctx.fillStyle='#8791A3'; ctx.font='10px Inter'; ctx.lineWidth=1;
  for(let i=0;i<=4;i++){ const v=maxV*i/4, y=Y(v); ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(w-pad.r,y); ctx.stroke(); ctx.fillText(Math.round(v),5,y+3); }
  ctx.beginPath(); ctx.moveTo(X(tl[0].t),Y(0)); tl.forEach(p=>ctx.lineTo(X(p.t),Y(p.dets))); ctx.lineTo(X(tl[tl.length-1].t),Y(0)); ctx.closePath();
  const g=ctx.createLinearGradient(0,pad.t,0,pad.t+gh); g.addColorStop(0,'rgba(45,108,223,.20)'); g.addColorStop(1,'rgba(45,108,223,.02)'); ctx.fillStyle=g; ctx.fill();
  line(ctx,tl,X,Y,p=>p.dets,'#2D6CDF',2.2);
  line(ctx,tl,X,Y,p=>p.ocupadas,'#E19100',1.8);
  line(ctx,tl,X,Y,p=>p.rostros,'#129A6B',1.6);
}
function line(ctx,tl,X,Y,f,color,lw){ ctx.beginPath(); tl.forEach((p,i)=>{const x=X(p.t),y=Y(f(p)); i?ctx.lineTo(x,y):ctx.moveTo(x,y);}); ctx.strokeStyle=color; ctx.lineWidth=lw; ctx.stroke(); }

/* ── export / toast ────────────────────────────────────────────────────── */
$('exportBtn').onclick=()=>{ window.location='/api/export?t='+Date.now(); };
let toastT=null;
function toast(msg){ const el=$('toast'); el.textContent=msg; el.classList.add('show'); clearTimeout(toastT); toastT=setTimeout(()=>el.classList.remove('show'),2600); }
