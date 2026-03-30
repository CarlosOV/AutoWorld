// ─── State ───────────────────────────────────────────────
let worldData = {agents:[], events:[], civilizations:[], discoveries:{}};
let agentPositions = {}; // name → {x, y, tx, ty, color}
let popupQueue = [];
let lastEventId = 0;

const CIV_COLORS = ['#4a8fd4','#c44a4a','#4ab870','#c9a84c','#8a4ac4','#4ac4c4','#c47a4a'];
const MOOD_COLORS = {happy:'#4ab870',sad:'#4a8fd4',angry:'#c44a4a',furious:'#e03030',neutral:'#a0b0c8',curious:'#c9a84c',excited:'#e0c040'};
const EVT_ICONS = {world_event:'🌐',agent_reaction:'💬',war:'⚔️',peace:'🕊️',discovery:'🔬',birth:'👶',death:'💀',gossip:'🗣️',personal_story:'📖',era_change:'🌅',civilization_formed:'🏰',default:'📜'};
const EPIC_WORDS = ['war','guerra','death','muerte','revolution','battle','conquest','apocalypse','betrayal','traición'];
const AGENT_EMOJIS = ['🧙','🛡️','⚔️','👸','🤴','🧝','🧟','🧚','🔮','🏹','⚗️','📜','🎭','🌿','🔱'];

// ─── Fetch & Render ───────────────────────────────────────
async function fetchState() {
  try {
    const res = await fetch('/api/state');
    const d = await res.json();
    worldData = d;
    render(d);
    checkNewEvents(d.events);
    return d;
  } catch(e) { console.error('fetchState error:', e); }
}

function render(d) {
  const wname = d.world_name || 'AutoWorld';
  window._worldName = wname;
  document.getElementById('world-title').textContent = '🌍 ' + wname;
  document.title = '🌍 ' + wname;
  document.getElementById('era-badge').textContent = d.era || 'Primordial Age';
  document.getElementById('era-overlay').textContent = d.era || 'The Primordial Age';
  document.getElementById('year-badge').textContent = d.year || 'Year 1';
  document.getElementById('h-agents').textContent = d.agents?.length || 0;
  document.getElementById('h-civs').textContent = d.civilizations?.length || 0;
  document.getElementById('h-events').textContent = d.events?.length || 0;
  const wars = (d.civilizations||[]).filter(c=>c.status==='war').length;
  document.getElementById('h-wars').textContent = wars;

  updateAgentPositions(d.agents || []);
  drawMap();
  renderAgents(d.agents || []);
  renderCivs(d.civilizations || [], d.discoveries || {});
  updateTicker(d.events || []);
}

function checkNewEvents(events) {
  if (!events.length) return;
  const newest = events[0];
  const newId = newest.id || 0;
  if (lastEventId && newId > lastEventId) {
    showEventPopup(newest);
  }
  if (newId) lastEventId = Math.max(lastEventId, newId);
  loadEvents(true);
}

// ─── Terrain Generation — heightmap noise ────────────────
let terrainCache = null, terrainSeed = 0;

// Seeded RNG — deterministic float 0..1
function srand(s){let x=Math.sin(s+1)*43758.5453123;return x-Math.floor(x);}
// Smooth noise via trig harmonics (avoids JS int overflow)
function snoise(x,y,s){
  return (Math.sin(x*1.7+y*3.1+s*7.3)*.4+Math.sin(x*3.3+y*1.9+s*2.1)*.3+
          Math.sin(x*5.1+y*5.7+s*4.4)*.2+Math.sin(x*9.2+y*8.3+s*1.1)*.1)*.5+.5;
}
function fbm(x,y,s,oct=4){
  let v=0,a=.5,f=1,t=0;
  for(let i=0;i<oct;i++){v+=snoise(x*f,y*f,s+i*3.7)*a;t+=a;a*=.55;f*=2.1;}
  return v/t;
}

function blobPath(ctx, cx, cy, r, spikes, rng){
  // Generate base vertices around a circle with strong noise
  const n=spikes||24;
  let pts=[];
  for(let i=0;i<n;i++){
    const a=(i/n)*Math.PI*2;
    // Strong radial variation: big bays and peninsulas
    const peninsula=(rng()-.5)*.60;  // ±30%
    const jag=(rng()-.5)*.20;        // ±10% fine detail
    const rad=r*(0.65+peninsula+jag);
    const stretchX=.82+rng()*.36;
    pts.push({
      x:cx+Math.cos(a)*rad*stretchX,
      y:cy+Math.sin(a)*rad*(2-stretchX)*.68
    });
  }
  // Fractal subdivision — add midpoints with displacement (2 passes)
  for(let pass=0;pass<2;pass++){
    const newPts=[];
    for(let i=0;i<pts.length;i++){
      const p=pts[i], q=pts[(i+1)%pts.length];
      newPts.push(p);
      // Midpoint with perpendicular displacement
      const mx=(p.x+q.x)/2, my=(p.y+q.y)/2;
      const dx=q.x-p.x, dy=q.y-p.y;
      const len=Math.sqrt(dx*dx+dy*dy);
      const disp=(rng()-.5)*len*(pass===0?.4:.2);
      newPts.push({x:mx+(-dy/len)*disp, y:my+(dx/len)*disp});
    }
    pts=newPts;
  }
  // Draw
  ctx.beginPath();
  ctx.moveTo(pts[0].x,pts[0].y);
  for(let i=1;i<pts.length;i++){
    const prev=pts[i-1], curr=pts[i], next=pts[(i+1)%pts.length];
    const cpx=(prev.x+curr.x*2+next.x)/4;
    const cpy=(prev.y+curr.y*2+next.y)/4;
    ctx.quadraticCurveTo(curr.x,curr.y,cpx,cpy);
  }
  ctx.closePath();
}

function generateTerrain(W, H, worldName) {
  const S = Math.abs(hashCode(worldName||'world')) % 9999 + 1;
  if (terrainCache && terrainSeed===S && terrainCache.width===W) return terrainCache;
  terrainSeed = S; terrainCache = null;

  const off = document.createElement('canvas');
  off.width=W; off.height=H;
  const ctx = off.getContext('2d');
  let rngI=0;
  const rng=()=>srand(S*1.7+(rngI++)*0.31+rngI*rngI*0.007);

  // ── Ocean ──
  const oceanGrad=ctx.createLinearGradient(0,0,W,H);
  oceanGrad.addColorStop(0,'#0a1e40');oceanGrad.addColorStop(.5,'#0d2850');oceanGrad.addColorStop(1,'#081830');
  ctx.fillStyle=oceanGrad; ctx.fillRect(0,0,W,H);
  // Ocean texture
  for(let i=0;i<300;i++){
    const x=rng()*W, y=rng()*H, l=20+rng()*60;
    ctx.strokeStyle=`rgba(255,255,255,${.015+rng()*.02})`; ctx.lineWidth=.5;
    ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+l,y+rng()*6-3);ctx.stroke();
  }

  // ── Continents — layered approach ──
  // Each continent: deep base (dark green) → lowland → forest interior
  const continents=[
    {cx:W*(.22+rng()*.18), cy:H*(.25+rng()*.20), r:Math.min(W,H)*(.18+rng()*.10), spikes:32},
    {cx:W*(.58+rng()*.18), cy:H*(.38+rng()*.20), r:Math.min(W,H)*(.13+rng()*.08), spikes:28},
    {cx:W*(.35+rng()*.12), cy:H*(.65+rng()*.15), r:Math.min(W,H)*(.09+rng()*.05), spikes:22},
    {cx:W*(.72+rng()*.10), cy:H*(.65+rng()*.12), r:Math.min(W,H)*(.06+rng()*.04), spikes:18},
    {cx:W*(.80+rng()*.08), cy:H*(.20+rng()*.12), r:Math.min(W,H)*(.05+rng()*.03), spikes:16},
    {cx:W*(.12+rng()*.08), cy:H*(.45+rng()*.08), r:Math.min(W,H)*(.03+rng()*.02), spikes:12},
    {cx:W*(.88+rng()*.05), cy:H*(.48+rng()*.08), r:Math.min(W,H)*(.025+rng()*.02),spikes:10},
  ];

  continents.forEach(c=>{
    // Shallow water halo
    rngI-=c.spikes+1; // reset to same rng sequence for consistent shape
    const rng2=()=>srand(S*1.7+(rngI++)*0.31+rngI*rngI*0.007);
    ctx.save();
    const shallowGrad=ctx.createRadialGradient(c.cx,c.cy,c.r*.3,c.cx,c.cy,c.r*1.4);
    shallowGrad.addColorStop(0,'rgba(0,0,0,0)');shallowGrad.addColorStop(.6,'rgba(22,88,118,.5)');shallowGrad.addColorStop(1,'rgba(0,0,0,0)');
    ctx.fillStyle=shallowGrad;blobPath(ctx,c.cx,c.cy,c.r*1.35,c.spikes,rng2);ctx.fill();
    ctx.restore();
  });

  continents.forEach((c,ci)=>{
    const r2=()=>srand(S*2.3+ci*17+(rngI++)*0.41+rngI*rngI*0.011);
    // Sand/beach layer (slightly larger than land)
    ctx.fillStyle='#b8a06a';
    blobPath(ctx,c.cx,c.cy,c.r*1.06,c.spikes,r2);ctx.fill();
    // Lowland grass
    ctx.fillStyle='#7aaa3c';
    blobPath(ctx,c.cx,c.cy,c.r*.90,c.spikes,r2);ctx.fill();
    // Mid forest
    ctx.fillStyle='#3e7828';
    blobPath(ctx,c.cx,c.cy,c.r*.72,c.spikes,r2);ctx.fill();
    // Highland
    ctx.fillStyle='#8a7242';
    blobPath(ctx,c.cx,c.cy,c.r*.48,c.spikes,r2);ctx.fill();
    // Mountain rock
    ctx.fillStyle='#9a9082';
    blobPath(ctx,c.cx,c.cy,c.r*.28,Math.max(8,c.spikes-4),r2);ctx.fill();

    // Terrain texture overlay
    const texGrad=ctx.createRadialGradient(c.cx-c.r*.2,c.cy-c.r*.15,0,c.cx,c.cy,c.r);
    texGrad.addColorStop(0,'rgba(255,255,255,.06)');texGrad.addColorStop(.5,'rgba(0,0,0,.04)');texGrad.addColorStop(1,'rgba(0,0,0,.12)');
    ctx.fillStyle=texGrad;blobPath(ctx,c.cx,c.cy,c.r*1.06,c.spikes,r2);ctx.fill();

    // Mountain peaks
    const mkr=()=>srand(S*3.1+ci*23+(rngI++)*0.5);
    for(let m=0;m<8+Math.floor(c.r/18);m++){
      const a=mkr()*Math.PI*2, dist=c.r*(0.05+mkr()*.22);
      const mx=c.cx+Math.cos(a)*dist, my=c.cy+Math.sin(a)*dist*.7;
      const mh=6+mkr()*10, mw=mh*.5;
      ctx.fillStyle='rgba(75,65,58,.85)';
      ctx.beginPath();ctx.moveTo(mx,my-mh);ctx.lineTo(mx-mw,my+2);ctx.lineTo(mx+mw,my+2);ctx.closePath();ctx.fill();
      ctx.fillStyle='rgba(220,224,235,.88)';
      ctx.beginPath();ctx.moveTo(mx,my-mh);ctx.lineTo(mx-mw*.3,my-mh*.35);ctx.lineTo(mx+mw*.3,my-mh*.35);ctx.closePath();ctx.fill();
    }

    // Trees in forest ring
    const tr=()=>srand(S*4.3+ci*31+(rngI++)*0.6);
    for(let t=0;t<20+Math.floor(c.r/5);t++){
      const a=tr()*Math.PI*2, dist=c.r*(.48+tr()*.26);
      const tx2=c.cx+Math.cos(a)*dist, ty2=c.cy+Math.sin(a)*dist*.8;
      const ts=3+tr()*4;
      ctx.fillStyle=`rgba(25,65,15,${.55+tr()*.35})`;
      ctx.beginPath();ctx.arc(tx2,ty2,ts,0,Math.PI*2);ctx.fill();
      ctx.fillStyle=`rgba(45,90,25,${.4+tr()*.3})`;
      ctx.beginPath();ctx.arc(tx2-ts*.2,ty2-ts*.2,ts*.6,0,Math.PI*2);ctx.fill();
    }
  });

  // Rivers
  continents.forEach((c,ci)=>{
    if(rng()<.4) return;
    const a=rng()*Math.PI*2;
    const sx=c.cx+Math.cos(a)*c.r*.2, sy=c.cy+Math.sin(a)*c.r*.2;
    const ex=c.cx+Math.cos(a+.4)*c.r*1.1, ey=c.cy+Math.sin(a+.4)*c.r*1.0;
    ctx.strokeStyle='rgba(30,90,160,.5)'; ctx.lineWidth=1.5;
    ctx.beginPath();ctx.moveTo(sx,sy);
    ctx.quadraticCurveTo(c.cx+Math.cos(a+.2)*c.r*.7,c.cy+Math.sin(a+.2)*c.r*.7,ex,ey);ctx.stroke();
  });

  // Compass rose (bottom-right)
  const compX=W-55, compY=H-55;
  ctx.save(); ctx.globalAlpha=.35;
  ctx.strokeStyle='#c9a84c'; ctx.lineWidth=1.2;
  ctx.beginPath();ctx.moveTo(compX,compY-22);ctx.lineTo(compX,compY+22);ctx.stroke();
  ctx.beginPath();ctx.moveTo(compX-22,compY);ctx.lineTo(compX+22,compY);ctx.stroke();
  ctx.fillStyle='#c9a84c';ctx.beginPath();ctx.moveTo(compX,compY-25);ctx.lineTo(compX-4,compY-15);ctx.lineTo(compX+4,compY-15);ctx.closePath();ctx.fill();
  ctx.font='bold 9px Cinzel,serif';ctx.textAlign='center';ctx.fillText('N',compX,compY-28);
  ctx.restore();

  // Vignette
  const vig=ctx.createRadialGradient(W/2,H/2,H*.25,W/2,H/2,W*.75);
  vig.addColorStop(0,'transparent');vig.addColorStop(1,'rgba(0,0,0,.45)');
  ctx.fillStyle=vig;ctx.fillRect(0,0,W,H);

  terrainCache=off; return off;
}

// ─── World Map ────────────────────────────────────────────
// Compute civ centers so agents of same civ cluster together
const CIV_CENTERS = [
  {x:.25,y:.35},{x:.72,y:.28},{x:.55,y:.65},{x:.20,y:.70},{x:.80,y:.65}
];

function updateAgentPositions(agents) {
  const civs = worldData.civilizations || [];
  agents.forEach((a, i) => {
    const key = a.name;
    const civIdx = civs.findIndex(c=>c.name===a.civ);
    const color = civIdx>=0 ? CIV_COLORS[civIdx % CIV_COLORS.length] : '#607080';
    const emoji = AGENT_EMOJIS[Math.abs(hashCode(a.name)) % AGENT_EMOJIS.length];

    // Target: near civ center (with personal offset) or random if no civ
    let tx, ty;
    if (civIdx >= 0) {
      const center = CIV_CENTERS[civIdx % CIV_CENTERS.length];
      const offsetX = ((hashCode(a.name) % 200) - 100) / 1000;
      const offsetY = ((hashCode(a.name+'y') % 200) - 100) / 1000;
      tx = Math.max(0.05, Math.min(0.95, center.x + offsetX));
      ty = Math.max(0.05, Math.min(0.95, center.y + offsetY));
    } else {
      tx = typeof a.x==='number' ? a.x : 0.1 + (Math.abs(hashCode(a.name))%800)/1000;
      ty = typeof a.y==='number' ? a.y : 0.1 + (Math.abs(hashCode(a.name+'y'))%800)/1000;
    }

    if (!agentPositions[key]) {
      agentPositions[key] = {x:tx, y:ty, tx, ty, color, emoji};
    } else {
      agentPositions[key].tx = tx;
      agentPositions[key].ty = ty;
      agentPositions[key].color = color;
      agentPositions[key].emoji = emoji;
    }
  });
}

function drawMap() {
  const canvas = document.getElementById('worldCanvas');
  const W = canvas.parentElement.clientWidth;
  const H = canvas.parentElement.clientHeight;
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');

  // Apply zoom/pan transform
  ctx.save();
  ctx.translate(mapPanX * W, mapPanY * H);
  ctx.scale(mapZoom, mapZoom);

  // Draw terrain (seeded from world name stored in page title)
  const terrain = generateTerrain(W, H, window._worldName || 'Inkari');
  ctx.drawImage(terrain, 0, 0, W, H);

  // Vignette
  const vig = ctx.createRadialGradient(W/2,H/2,H*.3,W/2,H/2,W*.8);
  vig.addColorStop(0,'transparent'); vig.addColorStop(1,'#00000088');
  ctx.fillStyle=vig; ctx.fillRect(0,0,W,H);

  // Civilization territories
  const civs = worldData.civilizations || [];
  civs.forEach((civ, ci) => {
    const members = (worldData.agents||[]).filter(a=>a.civ===civ.name);
    if (members.length < 2) return;
    const col = CIV_COLORS[ci % CIV_COLORS.length];
    const xs = members.map(a=>agentPositions[a.name]?.x*W||W/2);
    const ys = members.map(a=>agentPositions[a.name]?.y*H||H/2);
    const cx = xs.reduce((s,v)=>s+v,0)/xs.length;
    const cy = ys.reduce((s,v)=>s+v,0)/ys.length;
    const r  = Math.max(50, Math.sqrt(xs.length) * 60);
    const g = ctx.createRadialGradient(cx,cy,0,cx,cy,r);
    g.addColorStop(0, col+'18'); g.addColorStop(1,'transparent');
    ctx.fillStyle=g; ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.fill();
    ctx.strokeStyle=col+'33'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.stroke();
    // Civ label — readable with outline
    ctx.font='bold 12px Cinzel,serif'; ctx.textAlign='center';
    ctx.strokeStyle='rgba(0,0,0,.85)'; ctx.lineWidth=3;
    ctx.strokeText(civ.name, cx, cy-r-8);
    ctx.fillStyle=col+'ee';
    ctx.fillText(civ.name, cx, cy-r-8);
    // Status badge
    if(civ.status==='war'){
      ctx.font='10px serif'; ctx.fillText('⚔️',cx+ctx.measureText(civ.name).width/2+10, cy-r-8);
    }
  });

  // Relationship lines
  (worldData.agents||[]).forEach(a => {
    const rels = a.relationships || {};
    Object.entries(rels).forEach(([other, type]) => {
      const pa = agentPositions[a.name];
      const pb = agentPositions[other];
      if (!pa || !pb) return;
      const colors = {friend:'#4ab87044',lover:'#e0607044',enemy:'#c44a4a44',rival:'#c9a84c44'};
      const col = colors[type] || '#ffffff11';
      ctx.strokeStyle=col; ctx.lineWidth=1; ctx.setLineDash([3,6]);
      ctx.beginPath(); ctx.moveTo(pa.x*W,pa.y*H); ctx.lineTo(pb.x*W,pb.y*H); ctx.stroke();
      ctx.setLineDash([]);
    });
  });

  // Agents
  (worldData.agents||[]).forEach(a => {
    const pos = agentPositions[a.name];
    if (!pos) return;
    // Smooth movement
    pos.x += (pos.tx - pos.x) * .08;
    pos.y += (pos.ty - pos.y) * .08;
    const px = pos.x * W, py = pos.y * H;
    const moodColor = Object.entries(MOOD_COLORS).find(([k])=>a.mood?.toLowerCase().includes(k))?.[1] || '#a0b0c8';

    // Shadow
    ctx.fillStyle='#00000066'; ctx.beginPath(); ctx.ellipse(px,py+12,8,3,0,0,Math.PI*2); ctx.fill();
    // Glow
    const grd=ctx.createRadialGradient(px,py,0,px,py,18);
    grd.addColorStop(0,pos.color+'44'); grd.addColorStop(1,'transparent');
    ctx.fillStyle=grd; ctx.beginPath(); ctx.arc(px,py,18,0,Math.PI*2); ctx.fill();
    // Circle
    ctx.fillStyle='#0d1525'; ctx.beginPath(); ctx.arc(px,py,11,0,Math.PI*2); ctx.fill();
    ctx.strokeStyle=pos.color; ctx.lineWidth=2;
    ctx.beginPath(); ctx.arc(px,py,11,0,Math.PI*2); ctx.stroke();
    // Emoji
    ctx.font='13px serif'; ctx.textAlign='center'; ctx.fillText(pos.emoji, px, py+4);
    // Name
    ctx.fillStyle='#d8e0eacc'; ctx.font='10px Crimson Text,serif';
    ctx.fillText(a.name.split(' ')[0], px, py+24);
    // Mood dot
    ctx.fillStyle=moodColor; ctx.beginPath(); ctx.arc(px+9,py-9,3,0,Math.PI*2); ctx.fill();
  });
}

  ctx.restore();
}

// Animate map
function animateMap(){
  drawMap();
  requestAnimationFrame(animateMap);
}

// ─── Event popups ─────────────────────────────────────────
function showEventPopup(evt) {
  const icon = EVT_ICONS[evt.type] || EVT_ICONS.default;
  const isEpic = EPIC_WORDS.some(w=>evt.desc?.toLowerCase().includes(w));
  const div = document.createElement('div');
  div.className = 'event-popup';
  div.style.cssText = `top:${20+Math.random()*40}%;left:${10+Math.random()*40}%`;
  div.innerHTML = `<div class="ep-type">${icon} ${evt.type?.replace('_',' ')}</div>${evt.desc?.slice(0,180) || ''}`;
  if (isEpic) div.style.borderColor='var(--red)';
  document.querySelector('.map-overlay').appendChild(div);
  setTimeout(()=>div.remove(), 5000);
}

function updateTicker(events) {
  if (!events.length) return;
  const text = events.slice(0,5).map(e=>e.desc?.slice(0,120)).join('   ✦   ');
  document.getElementById('ticker-text').textContent = text;
}

// ─── Chronicle ────────────────────────────────────────────
let eventsOffset = 0;
const EVENTS_PAGE = 20;
let currentSearch = '', currentType = '';

async function searchEvents(q) {
  eventsOffset = 0; currentSearch = q;
  currentType = document.getElementById('filter-type').value;
  await loadEvents(true);
}

async function loadMoreEvents() { eventsOffset += EVENTS_PAGE; await loadEvents(false); }

const NOTABLE_TYPES = ['world_event','war','gossip','personal_story','discovery','birth','era_change','civilization_formed'];

async function loadEvents(reset = true) {
  // "notable" = exclude boring agent_reactions
  const filterType = currentType === 'notable' ? '' : currentType;
  const params = new URLSearchParams({limit:EVENTS_PAGE, offset:eventsOffset,
    ...(filterType&&{type:filterType}), ...(currentSearch&&{search:currentSearch})});
  const res = await fetch('/api/events?'+params);
  const d = await res.json();

  // Client-side filter for "notable"
  if (currentType === 'notable') {
    d.events = d.events.filter(e => NOTABLE_TYPES.includes(e.type));
  }
  document.getElementById('load-more-btn').style.display = eventsOffset+EVENTS_PAGE>=d.total?'none':'block';

  const html = d.events.map(e => {
    const icon = EVT_ICONS[e.type]||EVT_ICONS.default;
    const isEpic = EPIC_WORDS.some(w=>e.desc?.toLowerCase().includes(w));
    const cls = isEpic?'epic':e.type==='gossip'?'gossip':e.type==='discovery'?'discovery':'';
    const ts = (e.ts||'').replace('T',' ').slice(0,16);
    return `<div class="evt ${cls}">
      <span class="evt-icon">${icon}</span>
      <div class="evt-body"><div class="desc">${e.desc||''}</div><div class="meta">${ts}</div></div>
    </div>`;
  }).join('');

  if (reset) document.getElementById('event-list').innerHTML = html;
  else document.getElementById('event-list').innerHTML += html;
}

// ─── Agents ───────────────────────────────────────────────
function renderAgents(agents) {
  const el = document.getElementById('agents-list');
  el.innerHTML = agents.map(a => {
    const pos = agentPositions[a.name];
    const color = pos?.color || '#607080';
    const emoji = pos?.emoji || '👤';
    const mood = a.mood || 'neutral';
    const moodColor = Object.entries(MOOD_COLORS).find(([k])=>mood.toLowerCase().includes(k))?.[1]||'#a0b0c8';
    const rels = Object.entries(a.relationships||{}).slice(0,4);
    const relHTML = rels.map(([n,t])=>`<span class="rel-tag" style="border-color:${color}33">${t}: ${n.split(' ')[0]}</span>`).join('');
    return `<div class="agent-card" onclick="pingAgent('${a.name}')">
      <div class="ac-top">
        <div class="ac-avatar" style="border-color:${color};background:${color}18">${emoji}</div>
        <div class="ac-info">
          <div class="name">${a.name}</div>
          <div class="job">${a.occupation||'?'} · Age ${a.age||'?'}</div>
          <div class="civ">${a.civ||'— no civ —'}</div>
          <span class="mood-chip" style="background:${moodColor}18;color:${moodColor};border:1px solid ${moodColor}44">${mood}</span>
        </div>
      </div>
      ${relHTML ? `<div class="rels">${relHTML}</div>` : ''}
    </div>`;
  }).join('');
}

function pingAgent(name) {
  const pos = agentPositions[name];
  if (!pos) return;
  // Zoom to agent location
  const canvas = document.getElementById('worldCanvas');
  const W = canvas.parentElement.clientWidth, H = canvas.parentElement.clientHeight;
  mapZoom = 3;
  mapPanX = 0.5/mapZoom - pos.tx;
  mapPanY = 0.5/mapZoom - pos.ty;
  clampPan();
  // Flash
  const orig = pos.color;
  pos.color = '#ffffff';
  setTimeout(()=>{ pos.color=orig; }, 600);
  switchTab('agents');
}

// ─── Civilizations ────────────────────────────────────────
function renderCivs(civs, discoveries) {
  const el = document.getElementById('civs-list');
  if (!civs.length) { el.innerHTML = '<div style="color:var(--text3);font-size:.82rem;padding:8px">No civilizations yet — world is in tribal age...</div>'; return; }
  el.innerHTML = civs.map((c, ci) => {
    const col = CIV_COLORS[ci % CIV_COLORS.length];
    const techs = discoveries[c.name]||[];
    const tier = c.tech_tier||0;
    const pct = Math.round(tier/10*100);
    const latest = techs.slice(-4);
    const statusCls = c.status==='war'?'status-war':c.status==='peace'?'status-peace':'status-growing';
    return `<div class="civ-card" style="border-left:3px solid ${col}">
      <div class="civ-header">
        <span style="font-size:1.3rem">${c.emoji||'🏰'}</span>
        <h3>${c.name}</h3>
        <span class="civ-status ${statusCls}">${c.status||'growing'}</span>
      </div>
      <div style="font-size:.75rem;color:var(--text3)">🏛 ${c.capital||'?'} · 👥 ${c.population||'?'} · ⚡ ${c.power||0}</div>
      <div style="font-size:.7rem;color:var(--purple2);margin-top:4px">${c.tech_tier_name||'Primitive'} (Tier ${tier})</div>
      <div class="tech-bar"><div class="tech-fill" style="width:${pct}%"></div></div>
      <div class="tech-chips">
        ${latest.map((t,i)=>`<span class="tech-chip ${i===latest.length-1?'new':''}">${t}</span>`).join('')}
        ${techs.length>4?`<span class="tech-chip" style="color:var(--text3)">+${techs.length-4}</span>`:''}
      </div>
    </div>`;
  }).join('');
}

// ─── Tabs ─────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.side-tab').forEach((t,i)=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  const tabs = ['chronicle','agents','civs'];
  const idx = tabs.indexOf(tab);
  document.querySelectorAll('.side-tab')[idx]?.classList.add('active');
  document.getElementById('tab-'+tab)?.classList.add('active');
}

// ─── Oracle ───────────────────────────────────────────────
async function askOracle(deep) {
  const q = document.getElementById('oracle-input').value.trim();
  if (!q) return;
  const el = document.getElementById('oracle-response');
  el.textContent = deep ? '🔍 Searching the ancient chronicles...' : '✨ The oracle consults the ethereal plane...';
  try {
    const res = await fetch(`/api/ask?q=${encodeURIComponent(q)}&deep=${deep}`);
    const d = await res.json();
    el.textContent = d.answer;
  } catch(e) { el.textContent = '⚠️ The oracle is silent...'; }
}

// ─── Helpers ──────────────────────────────────────────────
function hashCode(s){let h=0;for(let i=0;i<s.length;i++)h=Math.imul(31,h)+s.charCodeAt(i)|0;return Math.abs(h)}

// ─── Zoom & Pan ───────────────────────────────────────────
let mapZoom = 1, mapPanX = 0, mapPanY = 0;
let isPanning = false, panStartX = 0, panStartY = 0;

const canvas = document.getElementById('worldCanvas');

canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mx = (e.clientX - rect.left) / rect.width;
  const my = (e.clientY - rect.top) / rect.height;
  const delta = e.deltaY < 0 ? 1.15 : 0.87;
  const newZoom = Math.max(1, Math.min(6, mapZoom * delta));
  // Zoom toward mouse position
  mapPanX = mx - (mx - mapPanX) * (newZoom / mapZoom);
  mapPanY = my - (my - mapPanY) * (newZoom / mapZoom);
  mapZoom = newZoom;
  clampPan();
}, {passive: false});

canvas.addEventListener('mousedown', e => {
  if (e.button !== 0) return;
  isPanning = true;
  panStartX = e.clientX;
  panStartY = e.clientY;
  canvas.style.cursor = 'grabbing';
});
canvas.addEventListener('mousemove', e => {
  if (!isPanning) return;
  const rect = canvas.getBoundingClientRect();
  mapPanX += (e.clientX - panStartX) / rect.width / mapZoom;
  mapPanY += (e.clientY - panStartY) / rect.height / mapZoom;
  panStartX = e.clientX; panStartY = e.clientY;
  clampPan();
});
canvas.addEventListener('mouseup',   () => { isPanning = false; canvas.style.cursor = 'grab'; });
canvas.addEventListener('mouseleave',() => { isPanning = false; canvas.style.cursor = 'grab'; });
canvas.style.cursor = 'grab';

// Touch support
let lastTouchDist = 0;
canvas.addEventListener('touchstart', e => {
  if (e.touches.length === 2) {
    lastTouchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
  } else if (e.touches.length === 1) {
    isPanning = true; panStartX = e.touches[0].clientX; panStartY = e.touches[0].clientY;
  }
}, {passive:true});
canvas.addEventListener('touchmove', e => {
  if (e.touches.length === 2) {
    const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    const scale = dist / lastTouchDist;
    mapZoom = Math.max(1, Math.min(6, mapZoom * scale));
    lastTouchDist = dist; clampPan();
  } else if (isPanning && e.touches.length === 1) {
    const rect = canvas.getBoundingClientRect();
    mapPanX += (e.touches[0].clientX - panStartX) / rect.width / mapZoom;
    mapPanY += (e.touches[0].clientY - panStartY) / rect.height / mapZoom;
    panStartX = e.touches[0].clientX; panStartY = e.touches[0].clientY; clampPan();
  }
}, {passive:true});
canvas.addEventListener('touchend', () => { isPanning = false; }, {passive:true});

function clampPan() {
  const maxPan = (mapZoom - 1) / mapZoom;
  mapPanX = Math.max(-maxPan, Math.min(0, mapPanX));
  mapPanY = Math.max(-maxPan, Math.min(0, mapPanY));
}

// Add zoom buttons to overlay
const zoomBtns = document.createElement('div');
zoomBtns.style.cssText = 'position:absolute;top:50px;right:12px;display:flex;flex-direction:column;gap:4px;pointer-events:all;z-index:10';
zoomBtns.innerHTML = `
  <button onclick="zoomBy(1.3)" style="background:#0a1020cc;border:1px solid #2a3a5a;color:#c9a84c;width:28px;height:28px;border-radius:3px;cursor:pointer;font-size:1rem;line-height:1">+</button>
  <button onclick="zoomBy(0.77)" style="background:#0a1020cc;border:1px solid #2a3a5a;color:#c9a84c;width:28px;height:28px;border-radius:3px;cursor:pointer;font-size:1rem;line-height:1">−</button>
  <button onclick="resetZoom()" style="background:#0a1020cc;border:1px solid #2a3a5a;color:#607080;width:28px;height:28px;border-radius:3px;cursor:pointer;font-size:.6rem;line-height:1">⊡</button>
`;
document.querySelector('.map-overlay').appendChild(zoomBtns);

function zoomBy(f){ mapZoom=Math.max(1,Math.min(6,mapZoom*f)); clampPan(); }
function resetZoom(){ mapZoom=1; mapPanX=0; mapPanY=0; }

// ─── Init ─────────────────────────────────────────────────
fetchState().then(() => {
  animateMap(); // start animation only after first data load
});
setInterval(fetchState, 30000);
loadEvents(true);