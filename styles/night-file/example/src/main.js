// Boot: fonts -> script + art style + timing -> 3D engine + sets -> captions -> shots.
import { W, H, setCtx, ctx, clamp } from './core/lib.js';
import { T, loadTiming } from './core/timing.js';
import { buildCaptions, drawCaption, captionList } from './core/captions.js';
import { makeEngine, RES, AA } from './core/engine.js';
import { resolveArtStyle, quantizeTime, applyArtStyle, drawSafeZoneOverlay } from './core/art_style.js';
import { buildShots } from './shots.js';

const cv = document.getElementById('cv'), GL = document.getElementById('gl');
setCtx(cv.getContext('2d'));
const OP = (window.OP = { ready: false, _artStyle: null, _safeZones: false });

function draw(t) {
  t = clamp(t, 0, T.dur - 1e-4);
  const qt = quantizeTime(t, OP._artStyle, T.dur);
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.letterSpacing = '0px';
  const S = OP._shots; let i = S.length - 1; while (i > 0 && S[i].at > qt) i--;
  const sh = S[i], end = i < S.length - 1 ? S[i + 1].at : T.dur, d = end - sh.at, lt = Math.max(0, qt - sh.at);
  const blit = () => ctx.drawImage(GL, 0, 0, W, H);
  ctx.save(); sh.draw(lt, d, qt, blit); ctx.restore();
  ctx.globalAlpha = 1; ctx.letterSpacing = '0px';
  applyArtStyle(ctx, W, H, qt, OP._artStyle);
  const fade = Math.min(clamp(t / 0.25), clamp((T.dur - t) / 0.4));
  if (fade < 1) { ctx.fillStyle = '#000'; ctx.globalAlpha = 1 - fade; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
  drawCaption(t);
  if (OP._safeZones) drawSafeZoneOverlay(ctx, W, H);
}

(async () => {
  try {
    await Promise.allSettled([
      document.fonts.load('900 100px Inter'),
      document.fonts.load('800 100px Inter'),
      document.fonts.load('700 100px Caladea'),
      document.fonts.load('700 100px FreeMono')
    ]);
    const q = new URLSearchParams(location.search);
    const script = await (await fetch('script.json', { cache: 'no-store' })).json();
    OP._artStyle = resolveArtStyle(script, q.get('artStyle'));
    OP._safeZones = q.has('safezones') || !!script.safeZoneOverlay;
    await loadTiming();
    buildCaptions(script);
    GL.width = Math.round(1080 * RES); GL.height = Math.round(1920 * RES);
    const E = makeEngine(GL, { w: GL.width, h: GL.height, samples: AA });
    const origRender = E.render.bind(E);
    E.render = (scene, cam, look = {}) => origRender(scene, cam, { ...look, ...(OP._artStyle?.webgl || {}) });
    const { shots, cues } = buildShots(E);
    shots.sort((a, b) => a.at - b.at);
    OP._shots = shots; OP.script = script;
    OP.duration = () => T.dur;
    OP.draw = draw;
    OP.frame = (t, q = 0.92) => { draw(t); return cv.toDataURL('image/jpeg', q); };
    OP.shots = () => shots.map((s, i) => ({ id: s.id, at: +s.at.toFixed(3), end: +(i < shots.length - 1 ? shots[i + 1].at : T.dur).toFixed(3), note: s.note || '' }));
    OP.captions = () => captionList().map((c) => ({ s: +c.s.toFixed(3), e: +c.e.toFixed(3), text: c.words.map((w) => (w.hi ? '*' : '') + w.txt).join(' ') }));
    OP.cues = () => cues.slice().sort((a, b) => a.t - b.t);
    OP.ready = true;
    if (!q.has('capture')) {
      if (q.has('t')) draw(+q.get('t'));
      else {
        const audio = new Audio('data/mix.wav'); let t0 = null; const btn = document.getElementById('play'); btn.hidden = false;
        btn.onclick = () => { btn.hidden = true; t0 = performance.now(); audio.currentTime = 0; audio.play().catch(() => {}); };
        const loop = (now) => { const t = t0 == null ? 0 : (now - t0) / 1000; draw(t); if (t0 != null && t > T.dur) { t0 = null; btn.hidden = false; } requestAnimationFrame(loop); };
        requestAnimationFrame(loop);
      }
    }
  } catch (e) { OP.bootError = String(e && e.stack || e); console.error(e); }
})();
