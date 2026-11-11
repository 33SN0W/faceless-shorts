// Unified Independent Art Style Engine + Mobile Safe-Zone Captions for 33SN0W Video Studio.
// Supports all 13 independent Art Styles + custom reference-derived styles across both 2D Canvas and 3D WebGL formats.

const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));

export const SAFE_ZONE = {
  top: 280,       // YouTube Shorts / IG Reels top header clearance
  bottom: 1470,   // Clearance above channel handle, title, and progress bar
  left: 70,       // Left margin
  right: 940,     // Right margin clear of Like/Comment/Share/Remix action stack
  captionY: 1380, // Universal safe caption baseline
  captionMaxW: 840
};

export const ART_STYLES = {
  default: {
    id: 'default',
    name: 'Native Format Default',
    timeStep: 0,
    caption: null,
    webgl: {},
    apply: null,
  },
  'pixel-art': {
    id: 'pixel-art',
    name: 'Pixel Art',
    timeStep: 1 / 15,
    caption: { font: '900 84px FreeMono, Inter', color: '#FFF3D6', hiColor: '#FFD43B', stroke: '#14121D', strokeW: 16, y: 1360, uppercase: true },
    webgl: { aperture: 0, bloom: 0.1, sat: 1.2, grain: 0 },
    apply(ctx, W, H, t, st) {
      const pw = 180, ph = 320;
      const lc = getLow(pw, ph);
      lc.ctx.imageSmoothingEnabled = false;
      lc.ctx.drawImage(ctx.canvas, 0, 0, pw, ph);
      const img = lc.ctx.getImageData(0, 0, pw, ph), d = img.data;
      for (let i = 0; i < d.length; i += 4) {
        d[i]     = (d[i]     >> 5) * 36;
        d[i + 1] = (d[i + 1] >> 5) * 36;
        d[i + 2] = (d[i + 2] >> 5) * 36;
      }
      lc.ctx.putImageData(img, 0, 0);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, W, H);
      ctx.drawImage(lc.cv, 0, 0, W, H);
      ctx.restore();
    }
  },
  chalkboard: {
    id: 'chalkboard',
    name: 'Chalkboard',
    timeStep: 1 / 12,
    caption: { font: '800 82px Inter', color: '#F3F0E6', hiColor: '#F6D365', stroke: '#111814', strokeW: 14, y: 1370 },
    webgl: { aperture: 0, bloom: 0.05, sat: 0.9, grain: 0 },
    apply(ctx, W, H, t) {
      const ew = 270, eh = 480;
      const lc = getLow(ew, eh);
      lc.ctx.drawImage(ctx.canvas, 0, 0, ew, eh);
      const src = lc.ctx.getImageData(0, 0, ew, eh), s = src.data;
      const out = lc.ctx.createImageData(ew, eh), o = out.data;
      for (let y = 0; y < eh; y++) {
        for (let x = 0; x < ew; x++) {
          const i = (y * ew + x) * 4;
          const lum = (s[i] * 0.3 + s[i + 1] * 0.59 + s[i + 2] * 0.11);
          const xr = x < ew - 1 ? (s[i + 4] * 0.3 + s[i + 5] * 0.59 + s[i + 6] * 0.11) : lum;
          const yd = y < eh - 1 ? (s[i + ew * 4] * 0.3 + s[i + ew * 4 + 1] * 0.59 + s[i + ew * 4 + 2] * 0.11) : lum;
          const edge = Math.min(255, (Math.abs(lum - xr) + Math.abs(lum - yd)) * 2.6);
          const bright = Math.max(0, (lum - 165) * 1.4);
          const chalk = Math.min(1, Math.max(edge / 255, bright / 255 * 0.65));
          // Mix slate background (#18221D) with pastel-tinted chalk
          o[i]     = Math.round(24  * (1 - chalk) + Math.min(248, 170 + s[i] * 0.34) * chalk);
          o[i + 1] = Math.round(34  * (1 - chalk) + Math.min(246, 175 + s[i + 1] * 0.32) * chalk);
          o[i + 2] = Math.round(29  * (1 - chalk) + Math.min(238, 165 + s[i + 2] * 0.32) * chalk);
          o[i + 3] = 255;
        }
      }
      lc.ctx.putImageData(out, 0, 0);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(lc.cv, 0, 0, W, H);
      // Overlay subtle chalk dust texture
      ctx.globalAlpha = 0.22;
      ctx.globalCompositeOperation = 'screen';
      ctx.fillStyle = getPattern('chalk', ctx);
      ctx.fillRect(0, 0, W, H);
      // Slate vignette
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      drawVignette(ctx, W, H, 0.38);
      ctx.restore();
    }
  },
  'glow-sketch': {
    id: 'glow-sketch',
    name: 'Glow Sketch',
    timeStep: 0,
    caption: { font: '900 84px Inter', color: '#EAF8FF', hiColor: '#00E5FF', stroke: '#050814', strokeW: 16, y: 1370, uppercase: true },
    webgl: { bloom: 0.45, sat: 1.25, vignette: 0.3 },
    apply(ctx, W, H, t) {
      const ew = 270, eh = 480;
      const lc = getLow(ew, eh);
      lc.ctx.drawImage(ctx.canvas, 0, 0, ew, eh);
      const src = lc.ctx.getImageData(0, 0, ew, eh), s = src.data;
      const out = lc.ctx.createImageData(ew, eh), o = out.data;
      const pulse = 0.9 + 0.1 * Math.sin(t * 4);
      for (let y = 0; y < eh; y++) {
        for (let x = 0; x < ew; x++) {
          const i = (y * ew + x) * 4;
          const lum = s[i] * 0.3 + s[i + 1] * 0.59 + s[i + 2] * 0.11;
          const xr = x < ew - 1 ? (s[i + 4] * 0.3 + s[i + 5] * 0.59 + s[i + 6] * 0.11) : lum;
          const yd = y < eh - 1 ? (s[i + ew * 4] * 0.3 + s[i + ew * 4 + 1] * 0.59 + s[i + ew * 4 + 2] * 0.11) : lum;
          const edge = Math.min(1, Math.max(0, ((Math.abs(lum - xr) + Math.abs(lum - yd)) - 12) / 58));
          const warm = s[i] > s[i + 2] + 25;
          const nr = warm ? 255 : 0;
          const ng = warm ? (s[i + 1] > 140 ? 185 : 55) : 230;
          const nb = warm ? (s[i + 1] > 140 ? 25 : 150) : 255;
          const k = edge * pulse;
          o[i]     = Math.round(6 + s[i] * 0.08 + nr * k);
          o[i + 1] = Math.round(9 + s[i + 1] * 0.08 + ng * k);
          o[i + 2] = Math.round(20 + s[i + 2] * 0.1 + nb * k);
          o[i + 3] = 255;
        }
      }
      lc.ctx.putImageData(out, 0, 0);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(lc.cv, 0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = 0.55;
      ctx.filter = 'blur(8px)';
      ctx.drawImage(lc.cv, 0, 0, W, H);
      ctx.filter = 'none';
      ctx.restore();
    }
  },
  'ps2-retro': {
    id: 'ps2-retro',
    name: 'PS2 Retro 3D',
    timeStep: 0,
    caption: { font: '900 82px Inter', color: '#FFF6DE', hiColor: '#FFD43B', stroke: '#111420', strokeW: 16, y: 1370 },
    webgl: { aperture: 0, bloom: 0.32, sat: 1.05, warm: 0.03 },
    apply(ctx, W, H) {
      const pw = 270, ph = 480;
      const lc = getLow(pw, ph);
      lc.ctx.drawImage(ctx.canvas, 0, 0, pw, ph);
      const img = lc.ctx.getImageData(0, 0, pw, ph), d = img.data;
      const bayer = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
      for (let y = 0; y < ph; y++) {
        for (let x = 0; x < pw; x++) {
          const i = (y * pw + x) * 4;
          const th = (bayer[(y & 3) * 4 + (x & 3)] - 7.5) * 1.6;
          d[i]     = clamp(Math.round((d[i]     + th) / 24) * 24, 0, 255);
          d[i + 1] = clamp(Math.round((d[i + 1] + th) / 24) * 24, 0, 255);
          d[i + 2] = clamp(Math.round((d[i + 2] + th) / 24) * 24, 0, 255);
        }
      }
      lc.ctx.putImageData(img, 0, 0);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(lc.cv, 0, 0, W, H);
      ctx.globalAlpha = 0.10;
      ctx.fillStyle = getPattern('scanlines', ctx);
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
    }
  },
  'comic-art': {
    id: 'comic-art',
    name: 'Comic Art',
    timeStep: 0,
    caption: { font: '900 88px Inter', color: '#FFFFFF', hiColor: '#FFD12E', stroke: '#121118', strokeW: 18, y: 1360, uppercase: true },
    webgl: { bloom: 0.12, sat: 1.25, grain: 0 },
    apply(ctx, W, H) {
      const wc = getWork(W, H);
      wc.ctx.filter = 'contrast(1.18) saturate(1.25)';
      wc.ctx.drawImage(ctx.canvas, 0, 0);
      wc.ctx.filter = 'none';
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(wc.cv, 0, 0);
      // Ben-Day Halftone overlay
      ctx.globalCompositeOperation = 'multiply';
      ctx.globalAlpha = 0.15;
      ctx.fillStyle = getPattern('halftone', ctx);
      ctx.fillRect(0, 0, W, H);
      // Crisp comic ink panel border
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      ctx.strokeStyle = '#121118';
      ctx.lineWidth = 22;
      ctx.strokeRect(11, 11, W - 22, H - 22);
      ctx.strokeStyle = '#FAF5E8';
      ctx.lineWidth = 4;
      ctx.strokeRect(24, 24, W - 48, H - 48);
      ctx.restore();
    }
  },
  'flat-vector': {
    id: 'flat-vector',
    name: 'Flat Vector',
    timeStep: 0,
    caption: { font: '900 86px Inter', color: '#FFFFFF', hiColor: '#FFD166', stroke: '#1D2026', strokeW: 16, y: 1380 },
    webgl: { bloom: 0.08, sat: 1.22, grain: 0, vignette: 0.05 },
    apply(ctx, W, H) {
      const wc = getWork(W, H);
      wc.ctx.filter = 'contrast(1.08) saturate(1.22)';
      wc.ctx.drawImage(ctx.canvas, 0, 0);
      wc.ctx.filter = 'none';
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(wc.cv, 0, 0);
      ctx.restore();
    }
  },
  'minimal-line': {
    id: 'minimal-line',
    name: 'Minimal Line',
    timeStep: 0,
    caption: { font: '700 80px Caladea, Georgia, serif', color: '#1C1D21', hiColor: '#D9383A', stroke: '#F7F4EB', strokeW: 14, y: 1380 },
    webgl: { bloom: 0, sat: 0.4, grain: 0, vignette: 0 },
    apply(ctx, W, H) {
      const ew = 270, eh = 480;
      const lc = getLow(ew, eh);
      lc.ctx.drawImage(ctx.canvas, 0, 0, ew, eh);
      const src = lc.ctx.getImageData(0, 0, ew, eh), s = src.data;
      const out = lc.ctx.createImageData(ew, eh), o = out.data;
      for (let y = 0; y < eh; y++) {
        for (let x = 0; x < ew; x++) {
          const i = (y * ew + x) * 4;
          const lum = s[i] * 0.3 + s[i + 1] * 0.59 + s[i + 2] * 0.11;
          const xr = x < ew - 1 ? (s[i + 4] * 0.3 + s[i + 5] * 0.59 + s[i + 6] * 0.11) : lum;
          const yd = y < eh - 1 ? (s[i + ew * 4] * 0.3 + s[i + ew * 4 + 1] * 0.59 + s[i + ew * 4 + 2] * 0.11) : lum;
          const edge = clamp((Math.abs(lum - xr) + Math.abs(lum - yd) - 10) / 50, 0, 1);
          // Warm sketchbook paper (#F7F4EB) with crisp charcoal lines + subtle accent hue preservation
          const redAccent = s[i] > s[i + 1] + 55 && s[i] > s[i + 2] + 55;
          const pr = redAccent ? 225 : 247;
          const pg = redAccent ? 105 : 244;
          const pb = redAccent ? 95  : 235;
          o[i]     = Math.round(pr * (1 - edge) + 28 * edge);
          o[i + 1] = Math.round(pg * (1 - edge) + 29 * edge);
          o[i + 2] = Math.round(pb * (1 - edge) + 33 * edge);
          o[i + 3] = 255;
        }
      }
      lc.ctx.putImageData(out, 0, 0);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(lc.cv, 0, 0, W, H);
      ctx.globalCompositeOperation = 'multiply';
      ctx.globalAlpha = 0.08;
      ctx.fillStyle = getPattern('paper', ctx);
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
    }
  },
  'cgi-motion': {
    id: 'cgi-motion',
    name: 'CGI Motion',
    timeStep: 0,
    caption: { font: '900 84px Inter', color: '#FFFFFF', hiColor: '#FFD43B', stroke: '#0D1018', strokeW: 16, y: 1390 },
    webgl: { bloom: 0.38, aperture: 0.0028, maxblur: 0.009, sat: 1.16, vignette: 0.22 },
    apply(ctx, W, H) {
      const wc = getWork(W, H);
      wc.ctx.filter = 'contrast(1.10) saturate(1.14)';
      wc.ctx.drawImage(ctx.canvas, 0, 0);
      wc.ctx.filter = 'none';
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(wc.cv, 0, 0);
      // Soft highlight glow bloom
      ctx.globalCompositeOperation = 'screen';
      ctx.globalAlpha = 0.14;
      ctx.filter = 'blur(12px)';
      ctx.drawImage(wc.cv, 0, 0);
      ctx.filter = 'none';
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      drawVignette(ctx, W, H, 0.24);
      ctx.restore();
    }
  },
  'lego-world': {
    id: 'lego-world',
    name: 'LEGO World',
    timeStep: 1 / 15,
    caption: { font: '900 84px Inter', color: '#FFFFFF', hiColor: '#FFD500', stroke: '#1B2A34', strokeW: 16, y: 1360, uppercase: true },
    webgl: { aperture: 0.003, bloom: 0.16, sat: 1.28, grain: 0 },
    apply(ctx, W, H) {
      const bw = 108, bh = 192; // 10x10 px brick grid
      const lc = getLow(bw, bh);
      lc.ctx.drawImage(ctx.canvas, 0, 0, bw, bh);
      const wc = getWork(W, H);
      wc.ctx.filter = 'contrast(1.12) saturate(1.26)';
      wc.ctx.drawImage(ctx.canvas, 0, 0);
      wc.ctx.filter = 'none';
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(wc.cv, 0, 0);
      // Blend crisp block grid softly so silhouettes stay readable while clearly brick-quantized
      ctx.globalAlpha = 0.35;
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(lc.cv, 0, 0, W, H);
      // Overlay specular plastic stud grid
      ctx.imageSmoothingEnabled = true;
      ctx.globalCompositeOperation = 'overlay';
      ctx.globalAlpha = 0.36;
      ctx.fillStyle = getPattern('lego', ctx);
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
    }
  },
  'explainer-2d': {
    id: 'explainer-2d',
    name: 'Explainer 2D',
    timeStep: 0,
    caption: { font: '900 84px Inter', color: '#FFFFFF', hiColor: '#F59E0B', stroke: '#1E293B', strokeW: 15, y: 1380, pillBg: 'rgba(15, 23, 42, 0.86)' },
    webgl: { bloom: 0.05, sat: 1.08, grain: 0, vignette: 0.05 },
    apply(ctx, W, H) {
      const wc = getWork(W, H);
      wc.ctx.filter = 'brightness(1.03) contrast(1.06) saturate(1.08)';
      wc.ctx.drawImage(ctx.canvas, 0, 0);
      wc.ctx.filter = 'none';
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(wc.cv, 0, 0);
      ctx.globalAlpha = 0.12;
      ctx.fillStyle = getPattern('dotgrid', ctx);
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
    }
  },
  'vintage-film': {
    id: 'vintage-film',
    name: 'Vintage Film',
    timeStep: 1 / 24,
    caption: { font: '700 78px Caladea, Georgia, serif', color: '#F5E9D3', hiColor: '#D94E41', stroke: '#1E1714', strokeW: 14, y: 1390 },
    webgl: { bloom: 0.2, sat: 0.8, warm: 0.06, grain: 0.035, vignette: 0.45 },
    apply(ctx, W, H, t) {
      const wc = getWork(W, H);
      wc.ctx.filter = 'sepia(0.36) contrast(1.08) saturate(0.84) brightness(0.96)';
      wc.ctx.drawImage(ctx.canvas, 0, 0);
      wc.ctx.filter = 'none';
      const weaveX = Math.sin(t * 19.3) * 1.5;
      const weaveY = Math.cos(t * 23.7) * 1.2;
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = '#14100E';
      ctx.fillRect(0, 0, W, H);
      ctx.drawImage(wc.cv, weaveX, weaveY);
      // 16mm grain pattern offset per frame
      ctx.globalCompositeOperation = 'overlay';
      ctx.globalAlpha = 0.16;
      ctx.translate(((t * 173) % 128), ((t * 241) % 128));
      ctx.fillStyle = getPattern('grain', ctx);
      ctx.fillRect(-128, -128, W + 256, H + 256);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      // Subtle vertical film scratch line periodically
      if (Math.sin(t * 7.1) > 0.72) {
        const sx = 180 + ((Math.floor(t * 24) * 317) % 720);
        ctx.globalCompositeOperation = 'screen';
        ctx.globalAlpha = 0.22;
        ctx.strokeStyle = '#F2DEC0';
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(sx, 0); ctx.lineTo(sx + 2, H); ctx.stroke();
      }
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      drawVignette(ctx, W, H, 0.48);
      ctx.restore();
    }
  },
  claymation: {
    id: 'claymation',
    name: 'Claymation',
    timeStep: 1 / 12, // Authentic stop-motion "on twos" cadence!
    caption: { font: '900 84px Inter', color: '#FFF8EB', hiColor: '#F2C64B', stroke: '#2C2224', strokeW: 16, y: 1360 },
    webgl: { aperture: 0.0035, bloom: 0.18, sat: 1.16, warm: 0.03 },
    apply(ctx, W, H) {
      const wc = getWork(W, H);
      wc.ctx.filter = 'contrast(1.06) saturate(1.15)';
      wc.ctx.drawImage(ctx.canvas, 0, 0);
      wc.ctx.filter = 'none';
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(wc.cv, 0, 0);
      // Clay micro-bump fingerprint texture
      ctx.globalCompositeOperation = 'soft-light';
      ctx.globalAlpha = 0.18;
      ctx.fillStyle = getPattern('clay', ctx);
      ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      drawVignette(ctx, W, H, 0.22);
      ctx.restore();
    }
  },
  watercolour: {
    id: 'watercolour',
    name: 'Watercolour',
    timeStep: 0,
    caption: { font: '700 80px Caladea, Georgia, serif', color: '#28242C', hiColor: '#B83630', stroke: '#F6EFE2', strokeW: 14, y: 1380, stripBg: '#F6EFE2' },
    webgl: { bloom: 0.12, sat: 0.9, warm: 0.03, grain: 0 },
    apply(ctx, W, H) {
      const wc = getWork(W, H);
      wc.ctx.filter = 'saturate(0.92) brightness(1.04) contrast(0.98)';
      wc.ctx.drawImage(ctx.canvas, 0, 0);
      wc.ctx.filter = 'none';
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(wc.cv, 0, 0);
      // Soft watercolor pigment bleed pass
      ctx.globalCompositeOperation = 'soft-light';
      ctx.globalAlpha = 0.35;
      ctx.filter = 'blur(4px)';
      ctx.drawImage(wc.cv, 0, 0);
      ctx.filter = 'none';
      // Cold-press cotton paper grain multiply
      ctx.globalCompositeOperation = 'multiply';
      ctx.globalAlpha = 0.22;
      ctx.fillStyle = getPattern('paper', ctx);
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
    }
  }
};

// Support custom reference-derived style config from script.artStyleConfig
export function resolveArtStyle(script = {}, overrideId = null) {
  const id = overrideId || script.artStyle || 'default';
  if (id === 'custom' && script.artStyleConfig) {
    const cfg = script.artStyleConfig;
    return {
      id: 'custom',
      name: cfg.name || 'Reference Inspired',
      timeStep: cfg.stepFps ? 1 / cfg.stepFps : 0,
      caption: cfg.caption || { font: '900 84px Inter', color: '#FFFFFF', hiColor: cfg.accentColor || '#FFD43B', stroke: '#14121D', strokeW: 16, y: 1370 },
      webgl: { sat: cfg.sat ?? 1.1, warm: cfg.warm ?? 0, vignette: cfg.vignette ?? 0.2, grain: cfg.grain ?? 0.015 },
      apply(ctx, W, H, t) {
        const wc = getWork(W, H);
        wc.ctx.filter = `contrast(${cfg.contrast ?? 1.08}) saturate(${cfg.sat ?? 1.1}) brightness(${cfg.brightness ?? 1.0})`;
        wc.ctx.drawImage(ctx.canvas, 0, 0);
        wc.ctx.filter = 'none';
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.drawImage(wc.cv, 0, 0);
        if (cfg.tintColor) {
          ctx.globalCompositeOperation = 'soft-light';
          ctx.globalAlpha = cfg.tintAlpha ?? 0.18;
          ctx.fillStyle = cfg.tintColor;
          ctx.fillRect(0, 0, W, H);
        }
        if ((cfg.grain ?? 0) > 0) {
          ctx.globalCompositeOperation = 'overlay';
          ctx.globalAlpha = clamp(cfg.grain * 2, 0.04, 0.25);
          ctx.fillStyle = getPattern('grain', ctx);
          ctx.fillRect(0, 0, W, H);
        }
        ctx.globalCompositeOperation = 'source-over';
        ctx.globalAlpha = 1;
        if ((cfg.vignette ?? 0) > 0) drawVignette(ctx, W, H, cfg.vignette);
        ctx.restore();
      }
    };
  }
  return ART_STYLES[id] || ART_STYLES.default;
}

export function quantizeTime(t, style, dur) {
  if (!style || !style.timeStep) return t;
  const q = Math.floor(t / style.timeStep) * style.timeStep;
  return Math.min(dur - 1e-4, Math.max(0, q));
}

export function applyArtStyle(ctx, W, H, t, style) {
  if (style && typeof style.apply === 'function') {
    style.apply(ctx, W, H, t);
  }
}

export function drawSafeZoneOverlay(ctx, W, H) {
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  // Danger shaded bands (YouTube Shorts & IG Reels UI overlays)
  ctx.fillStyle = 'rgba(216, 52, 63, 0.28)';
  ctx.fillRect(0, 0, W, SAFE_ZONE.top);
  ctx.fillRect(0, SAFE_ZONE.bottom, W, H - SAFE_ZONE.bottom);
  ctx.fillRect(SAFE_ZONE.right, SAFE_ZONE.top, W - SAFE_ZONE.right, SAFE_ZONE.bottom - SAFE_ZONE.top);
  ctx.fillRect(0, SAFE_ZONE.top, SAFE_ZONE.left, SAFE_ZONE.bottom - SAFE_ZONE.top);
  // Safe core box outline
  ctx.strokeStyle = '#00E5FF';
  ctx.lineWidth = 4;
  ctx.setLineDash([16, 10]);
  ctx.strokeRect(SAFE_ZONE.left, SAFE_ZONE.top, SAFE_ZONE.right - SAFE_ZONE.left, SAFE_ZONE.bottom - SAFE_ZONE.top);
  ctx.setLineDash([]);
  ctx.fillStyle = '#00E5FF';
  ctx.font = '700 28px Inter';
  ctx.textAlign = 'left';
  ctx.fillText('SAFE ZONE (YT SHORTS + IG REELS)', SAFE_ZONE.left + 12, SAFE_ZONE.top + 36);
  ctx.restore();
}

/** Unified style-aware & safe-zone-compliant caption renderer. */
export function drawStyledCaption(ctx, words, x = 510, yOverride = null, sc = 1, theme = {}) {
  const txtList = words.map((w) => (typeof w === 'string' ? { txt: w, hi: false } : w));
  const upper = theme.uppercase ?? false;
  const cleanWords = txtList.map((w) => ({ ...w, txt: upper ? w.txt.toUpperCase() : w.txt }));
  const y = Math.min(SAFE_ZONE.bottom - 50, yOverride ?? theme.y ?? SAFE_ZONE.captionY);
  const maxW = Math.min(SAFE_ZONE.captionMaxW, SAFE_ZONE.right - SAFE_ZONE.left - 30);
  const size = theme.size || 84;
  ctx.save();
  ctx.font = theme.font || `900 ${size}px Inter`;
  ctx.letterSpacing = '0px';
  const sp = size * 0.26;
  cleanWords.forEach((w) => (w.w = ctx.measureText(w.txt).width));
  const lineW = (ws) => ws.reduce((a, w) => a + w.w, 0) + sp * (ws.length - 1);
  let lines = [cleanWords];
  if (lineW(cleanWords) > maxW && cleanWords.length > 1) {
    let best = null;
    for (let i = 1; i < cleanWords.length; i++) {
      const a = cleanWords.slice(0, i), b = cleanWords.slice(i);
      const m = Math.max(lineW(a), lineW(b));
      if (!best || m < best.m) best = { m, l: [a, b] };
    }
    lines = best.l;
  }
  const maxLineW = Math.max(...lines.map(lineW));
  const fit = Math.min(1, maxW / Math.max(1, maxLineW));
  const finalSc = sc * fit;
  // Center safely away from the right-hand button stack
  const safeCx = Math.min(x, (SAFE_ZONE.left + SAFE_ZONE.right) / 2);
  ctx.translate(safeCx, y);
  ctx.scale(finalSc, finalSc);
  const lh = size * 1.05;

  if (theme.pillBg || theme.stripBg) {
    const padX = 34, padY = 22;
    const bw = maxLineW + padX * 2, bh = lines.length * lh + padY * 2;
    ctx.fillStyle = theme.pillBg || theme.stripBg;
    ctx.beginPath();
    ctx.roundRect(-bw / 2, -bh / 2, bw, bh, theme.stripBg ? 8 : 22);
    ctx.fill();
    if (theme.stripBg) {
      ctx.strokeStyle = 'rgba(0,0,0,0.22)';
      ctx.lineWidth = 4;
      ctx.stroke();
    }
  }

  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  ctx.lineJoin = 'round';
  const y0 = -((lines.length - 1) * lh) / 2;
  lines.forEach((ln, li) => {
    let px = -lineW(ln) / 2;
    const py = y0 + li * lh;
    for (const w of ln) {
      if (!theme.stripBg) {
        ctx.fillStyle = 'rgba(0,0,0,0.45)';
        ctx.fillText(w.txt, px + 3, py + 7);
        ctx.lineWidth = theme.strokeW ?? 16;
        ctx.strokeStyle = theme.stroke || '#0B0B10';
        ctx.strokeText(w.txt, px, py);
      }
      ctx.fillStyle = w.hi ? (theme.hiColor || '#FFD43B') : (theme.color || '#FFFFFF');
      ctx.fillText(w.txt, px, py);
      px += w.w + sp;
    }
  });
  ctx.restore();
}

// ── Cached Offscreen Buffers & Procedural Textures ────────────────────────────────
let _work = null, _low = null;
const _pats = {};

function getWork(W, H) {
  if (!_work || _work.cv.width !== W || _work.cv.height !== H) {
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    _work = { cv, ctx: cv.getContext('2d') };
  }
  return _work;
}
function getLow(w, h) {
  if (!_low || _low.cv.width !== w || _low.cv.height !== h) {
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    _low = { cv, ctx: cv.getContext('2d', { willReadFrequently: true }) };
  }
  return _low;
}

function drawVignette(ctx, W, H, strength) {
  const g = ctx.createRadialGradient(W / 2, H / 2, W * 0.25, W / 2, H / 2, H * 0.65);
  g.addColorStop(0, 'rgba(0,0,0,0)');
  g.addColorStop(1, `rgba(0,0,0,${strength})`);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
}

function getPattern(kind, hostCtx) {
  if (_pats[kind]) return _pats[kind];
  const c = document.createElement('canvas');
  const rnd = (i) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  if (kind === 'halftone') {
    c.width = c.height = 16;
    const g = c.getContext('2d');
    g.fillStyle = '#FFFFFF'; g.fillRect(0, 0, 16, 16);
    g.fillStyle = '#121118';
    [[4, 4], [12, 12]].forEach(([x, y]) => { g.beginPath(); g.arc(x, y, 2.7, 0, Math.PI * 2); g.fill(); });
  } else if (kind === 'scanlines') {
    c.width = 4; c.height = 6;
    const g = c.getContext('2d');
    g.fillStyle = '#000000'; g.fillRect(0, 0, 4, 2);
  } else if (kind === 'dotgrid') {
    c.width = c.height = 36;
    const g = c.getContext('2d');
    g.fillStyle = '#1E293B'; g.beginPath(); g.arc(18, 18, 2, 0, Math.PI * 2); g.fill();
  } else if (kind === 'lego') {
    c.width = c.height = 10;
    const g = c.getContext('2d');
    g.fillStyle = 'rgba(128,128,128,0.5)'; g.fillRect(0, 0, 10, 10);
    g.strokeStyle = 'rgba(0,0,0,0.45)'; g.lineWidth = 1; g.strokeRect(0.5, 0.5, 9, 9);
    g.fillStyle = 'rgba(255,255,255,0.65)'; g.beginPath(); g.arc(5, 4.5, 2.8, 0, Math.PI * 2); g.fill();
    g.fillStyle = 'rgba(0,0,0,0.35)'; g.beginPath(); g.arc(5, 5.5, 2.8, 0, Math.PI); g.fill();
  } else if (kind === 'chalk' || kind === 'paper' || kind === 'grain' || kind === 'clay') {
    c.width = c.height = 128;
    const g = c.getContext('2d'), img = g.createImageData(128, 128), d = img.data;
    for (let i = 0; i < 128 * 128; i++) {
      const n = rnd(i + (kind === 'chalk' ? 11 : kind === 'clay' ? 37 : 73));
      const v = kind === 'chalk' ? Math.round(n * 90) : kind === 'paper' ? Math.round(215 + n * 40) : Math.round(90 + n * 85);
      d[i * 4] = v; d[i * 4 + 1] = v; d[i * 4 + 2] = v; d[i * 4 + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }
  return (_pats[kind] = hostCtx.createPattern(c, 'repeat'));
}
