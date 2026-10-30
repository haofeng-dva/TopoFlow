/* TopoFlow hero 光环着色器
 * 移植自 grampixel.jp 的 hero-reflect.js（其自述：由 Originkit Reflect Shader 预设移植为原生 JS）
 * 本适配版：tint 改为品牌琥珀金 #F2B146，悬停区域改为 #heroTop，其余逻辑保持一致。
 * 仅用于毕业设计演示。 */
/* Reflect Shader（Originkit）を React なしの素の JS に移植。設定値・ホバー効果は元コードと同じ。残像を追加 */
(() => {
  const wrap = document.getElementById('heroReflectWrap');
  const canvas = document.getElementById('heroReflect');
  const hoverArea = document.getElementById('heroTop');
  if (!wrap || !canvas || !hoverArea) return;
  const gl = canvas.getContext('webgl', { antialias: false, alpha: true, premultipliedAlpha: true });
  if (!gl) return;

  /* GPUを使わないソフトウェア描画の環境（GPUのない端末、PageSpeed Insights などの計測環境）では、
     連続アニメーションがページ全体を止めてしまうため、1枚だけ描いて静止させる */
  const isSoftwareGL = (() => {
    try {
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      const name = String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
      return /swiftshader|llvmpipe|softpipe|software|basic render/i.test(name);
    } catch (e) { return false; }
  })();

  /* 設定値（Originkit プリセット：brightness 61 / thickness 120 / bandGap 21 / hover 50） */
  const P = { tint: '#F2B146', speed: 50, brightness: 61, thickness: 120, chromatic: 10, bandGap: 21, zoom: 295, hover: 50 };
  const MAX_DPR = 2, BASE_RATE = 3, LINE_COUNT = 5, FOLLOW_RATE = 8, HOVER_REACH_PX = 260;
  /* 残像の設定 */
  const TRAIL = {
    keep: 0.90,    // 1フレームで残る明るさ（0で残像なし / 1に近いほど長く残る）
    spread: 1.004, // 残像が外へ流れる量（1で流れない）
  };

  const VERT = 'attribute vec2 aPosition;void main(){gl_Position=vec4(aPosition,0.0,1.0);}';
  const FRAG = `
precision highp float;
#define MAXLINES 12
uniform vec2  uResolution;
uniform float uTime;
uniform float uLineWidth;
uniform float uSpread;
uniform float uBands;
uniform float uScale;
uniform float uIntensity;
uniform int   uLineCount;
uniform vec3  uTint;
uniform vec2  uPointer;
uniform float uHover;
uniform float uReach;
uniform sampler2D uPrev;
uniform float uKeep;
uniform float uSpreadTrail;
float channel(vec2 uv, float r, float t, float jf) {
  float sum = 0.0;
  float band = mod(uv.x + uv.y, uBands);
  for (int i = 0; i < MAXLINES; i++) {
    if (i < uLineCount) {
      float d = fract(t - uSpread * jf + float(i) * 0.01) * 5.0 - r + band;
      sum += uLineWidth * float(i * i) / max(abs(d), 1e-4);
    }
  }
  return sum;
}
void main() {
  vec2 s = (gl_FragCoord.xy * 2.0 - uResolution) / min(uResolution.x, uResolution.y);
  s *= uScale;
  vec2 uv = s - uPointer * min(uHover, 1.0);
  float reach = max(uReach, 1e-3);
  float r = length(uv);
  float t = uTime * 0.05;
  vec3 color = vec3(channel(uv, r, t, 0.0), channel(uv, r, t, 1.0), channel(uv, r, t, 2.0));
  float dp = length(s - uPointer) / reach;
  float glow = uHover * exp(-dp * dp);
  vec3 c = min(color * uIntensity * (1.0 + glow) * uTint, vec3(1.0));
  /* 残像：前のフレームを少し外へ広げ、少し暗くして重ねる */
  vec2 q = gl_FragCoord.xy / uResolution;
  vec2 pq = (q - 0.5) / uSpreadTrail + 0.5;
  vec3 prev = texture2D(uPrev, pq).rgb * uKeep - 1.5 / 255.0;
  c = max(c, max(prev, vec3(0.0)));
  gl_FragColor = vec4(c, 1.0);
}`;
  /* 画面へ写すだけのシェーダー */
  const COPY = 'precision highp float;uniform sampler2D uTex;uniform vec2 uRes;void main(){gl_FragColor=texture2D(uTex,gl_FragCoord.xy/uRes);}';
  const parseColor = (s) => {
    s = (s || '').trim();
    if (s[0] === '#') {
      let h = s.slice(1);
      if (h.length === 3 || h.length === 4) h = h.slice(0, 3).split('').map((c) => c + c).join('');
      const n = parseInt(h.slice(0, 6), 16);
      if (Number.isNaN(n)) return [1, 1, 1];
      return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
    }
    return [1, 1, 1];
  };

  const sh = (type, src) => { const x = gl.createShader(type); gl.shaderSource(x, src); gl.compileShader(x); return x; };
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT));
  gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
  gl.useProgram(prog);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const aPos = gl.getAttribLocation(prog, 'aPosition');
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
  const copyProg = gl.createProgram();
  gl.attachShader(copyProg, sh(gl.VERTEX_SHADER, VERT));
  gl.attachShader(copyProg, sh(gl.FRAGMENT_SHADER, COPY));
  gl.bindAttribLocation(copyProg, aPos, 'aPosition');
  gl.linkProgram(copyProg);
  const cU = { tex: gl.getUniformLocation(copyProg, 'uTex'), res: gl.getUniformLocation(copyProg, 'uRes') };
  gl.useProgram(prog);

  /* 前のフレームを保存する2枚の描画先（交互に使う） */
  let targets = [], cur = 0;
  const makeTargets = (w, h) => {
    targets.forEach((t) => { gl.deleteTexture(t.tex); gl.deleteFramebuffer(t.fb); });
    targets = [0, 1].map(() => {
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      const fb = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT);
      return { tex, fb };
    });
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  };
  const U = (n) => gl.getUniformLocation(prog, n);
  const u = { res: U('uResolution'), time: U('uTime'), lw: U('uLineWidth'), spread: U('uSpread'), bands: U('uBands'),
    scale: U('uScale'), inten: U('uIntensity'), count: U('uLineCount'), tint: U('uTint'),
    pointer: U('uPointer'), hover: U('uHover'), reach: U('uReach'), prev: U('uPrev'), keep: U('uKeep'), spreadT: U('uSpreadTrail') };

  const resize = () => {
    /* ソフトウェア描画では解像度を1/4（面積1/16）に下げて、1枚だけ描く */
    const dpr = isSoftwareGL ? 0.5 : Math.min(window.devicePixelRatio || 1, MAX_DPR);
    const w = Math.max(1, Math.round((canvas.clientWidth || 1) * dpr));
    const h = Math.max(1, Math.round((canvas.clientHeight || 1) * dpr));
    if (canvas.width !== w || canvas.height !== h || !targets.length) { canvas.width = w; canvas.height = h; makeTargets(w, h); }
    gl.viewport(0, 0, w, h);
    gl.useProgram(prog);
    gl.uniform2f(u.res, w, h);
  };
  resize();
  new ResizeObserver(resize).observe(canvas);

  /* ホバー：元コードと同じく、ポインターの位置に光が寄る */
  const ptr = { tx: 0, ty: 0, x: 0, y: 0, inside: 0, ease: 0 };
  hoverArea.addEventListener('pointermove', (e) => {
    const r = wrap.getBoundingClientRect();
    const w = r.width || 1, h = r.height || 1, m = Math.min(w, h);
    const ox = e.clientX - r.left, oy = e.clientY - r.top;
    ptr.tx = (ox * 2 - w) / m; ptr.ty = (h - oy * 2) / m; ptr.inside = 1;
  });
  hoverArea.addEventListener('pointerleave', () => { ptr.tx = 0; ptr.ty = 0; ptr.inside = 0; });

  let t = 0, last = 0, running = false, visible = true;
  let staticFrames = 0;
  const frame = (now) => {
    if (!running) return;
    if (isSoftwareGL && staticFrames++ > 0) { running = false; return; }   /* 静止表示（1枚だけ） */
    requestAnimationFrame(frame);
    const dt = last ? Math.min((now - last) / 1000, 1 / 15) : 0;
    last = now;
    t = (t + BASE_RATE * (P.speed / 50) * dt) % 20000;
    gl.uniform1f(u.time, t);
    gl.uniform1f(u.lw, P.thickness / 10000);
    gl.uniform1f(u.spread, P.chromatic / 1000);
    gl.uniform1f(u.bands, Math.max(P.bandGap, 1) / 100);
    gl.uniform1f(u.scale, P.zoom / 100);
    gl.uniform1f(u.inten, P.brightness / 100);
    gl.uniform1i(u.count, LINE_COUNT);
    const [cr, cg, cb] = parseColor(P.tint);
    gl.uniform3f(u.tint, cr, cg, cb);
    const k = 1 - Math.exp(-dt * FOLLOW_RATE);
    ptr.x += (ptr.tx - ptr.x) * k; ptr.y += (ptr.ty - ptr.y) * k; ptr.ease += (ptr.inside - ptr.ease) * k;
    const scale = P.zoom / 100;
    const side = Math.max(1, Math.min(canvas.clientWidth || 1, canvas.clientHeight || 1));
    gl.uniform2f(u.pointer, ptr.x * scale, ptr.y * scale);
    gl.uniform1f(u.hover, (P.hover / 100) * ptr.ease);
    gl.uniform1f(u.reach, ((HOVER_REACH_PX * 2) / side) * scale);

    /* 1. 新しい絵＋前のフレームの残像を描画先へ */
    const src = targets[cur], dst = targets[1 - cur];
    gl.bindFramebuffer(gl.FRAMEBUFFER, dst.fb);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, src.tex);
    gl.uniform1i(u.prev, 0);
    const f = dt * 60;                                    // 画面の更新頻度が違っても同じ長さになるように
    gl.uniform1f(u.keep, Math.pow(TRAIL.keep, f));
    gl.uniform1f(u.spreadT, Math.pow(TRAIL.spread, f));
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    cur = 1 - cur;

    /* 2. 画面へ写す */
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.useProgram(copyProg);
    gl.bindTexture(gl.TEXTURE_2D, dst.tex);
    gl.uniform1i(cU.tex, 0);
    gl.uniform2f(cU.res, canvas.width, canvas.height);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.useProgram(prog);
  };
  const start = () => { if (running || !visible || document.hidden) return; running = true; last = 0; requestAnimationFrame(frame); };
  const stop = () => { running = false; };
  new IntersectionObserver((e) => { visible = e[0].isIntersecting; visible ? start() : stop(); }).observe(hoverArea);
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
  start();
})();
