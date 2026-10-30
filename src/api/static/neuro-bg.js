/* TopoFlow 工作台流动光背景
 * 移植自 grampixel.jp main.js 的 neuro-bg 模块（MEMBER/BLOG 区背景）。
 * 本适配版：目标 section 改为 #consoleSection，其余（调色盘/着色器/参数）保持原样。
 * 仅用于毕业设计演示。 */
(function () {
var CONFIG = {
    CYCLE_SECONDS: 6,     // 色1周の秒数（小さいほど色が速く流れる）
    HUE_NOISE_SCALE: 3.0,  // 位相ずれノイズの空間スケール（大=細かく色が分かれる）
    HUE_NOISE_AMOUNT: 0.30,// 位相ずれ量（0〜0.2。0で全画面同期）
    SATURATION_SCALE: 1.0, // 彩度倍率（パレット基準1.0）
    GLOW_KNEE: 2.4,        // トーンマップ強度（大=明るい）
    PRISM_STRENGTH: 3.2,   // 色収差の分光強度（大=虹色の縁が強い）
    LINE_SHARPNESS: 1.9,   // 光ラインの締まり（大=くっきり細い）
    RES_SCALE: 0.55        // 内部解像度（負荷対策）
  };

  /* ---- パレット定義：[色相(度・アンラップ済), 彩度0-1] 明度は一定0.82 ----
     アンラップ：18°→310°の遷移を-50°と表現し、周回の継ぎ目をなくす。
     末尾-150°+360°=210°で先頭に完全接続（無限ループ） */
  var PALETTE_HS = [
    [196, 0.34], // Cyan
    [190, 0.56], // Bright Cyan 部分強調
    [198, 0.30], // Sky Cyan
    [200, 0.28], // Sky Blue
    [188, 0.58], // Bright Cyan 部分強調
    [195, 0.34], // Cyan
    [199, 0.30], // Sky Cyan
    [192, 0.54], // Cyan 部分強調
    [198, 0.26], // 白寄り
    [195, 0.35], // Cyan
    [193, 0.36], // Cyan
    [190, 0.52], // Cyan 部分強調
    [199, 0.28], // Sky Cyan
    [196, 0.34]  // Cyan（先頭と同値）
  ];
  var LIGHTNESS = 0.82;

  /* 青系（色相180〜215°）のみ明度を少し上げて発光感を強める */
  function lightnessFor(h) {
    return LIGHTNESS;
  }
  /* シアン域(184-205°)は彩度が高いほど明度を下げ、部分的に鮮やかなシアンを出す */
  function lightnessForS(h, s) {
    var hn = ((h % 360) + 360) % 360;
    if (hn >= 184 && hn <= 205 && s >= 0.45) return LIGHTNESS - (s - 0.45) * 1.1;
    return LIGHTNESS;
  }

  function hslToRgb(h, s, l) {
    h = ((h % 360) + 360) % 360 / 360;
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p = 2 * l - q;
    function f(t) {
      t = ((t % 1) + 1) % 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    }
    return [f(h + 1/3), f(h), f(h - 1/3)];
  }

  /* パレットテクスチャ生成：セグメント間をコサインイージングで補間（段差なし） */
  function buildPaletteData(size) {
    var n = PALETTE_HS.length;
    var data = new Uint8Array(size * 4);
    for (var i = 0; i < size; i++) {
      var t = i / size * n;
      var seg = Math.floor(t);
      var f = t - seg;
      var e = 0.5 - 0.5 * Math.cos(Math.PI * f);   // コサインイージング
      var a = PALETTE_HS[seg % n], b = PALETTE_HS[(seg + 1) % n];
      var bh = b[0]; if (seg === n - 1) bh = PALETTE_HS[0][0] - 360; // 周回接続
      var h = a[0] + (bh - a[0]) * e;
      var s = (a[1] + (b[1] - a[1]) * e) * CONFIG.SATURATION_SCALE;
      var rgb = hslToRgb(h, Math.min(1, s), lightnessForS(h, s));
      data[i*4]   = Math.round(rgb[0] * 255);
      data[i*4+1] = Math.round(rgb[1] * 255);
      data[i*4+2] = Math.round(rgb[2] * 255);
      data[i*4+3] = 255;
    }
    return data;
  }

  var VS = [
    'attribute vec2 aPos;',
    'varying vec2 vUv;',
    'void main(){ vUv = aPos*0.5+0.5; gl_Position = vec4(aPos, 0.0, 1.0); }'
  ].join('\n');

  function buildFS(useDeriv) {
    var head = useDeriv
      ? '#extension GL_OES_standard_derivatives : enable\nprecision highp float;'
      : 'precision highp float;';
    var core = [
      'varying vec2 vUv;',
      'uniform float uTime;',
      'uniform vec2 uRes;',
      'uniform float uTop;',
      'uniform float uTotal;',
      'uniform float uRefH;',
      'uniform sampler2D uPalette;',
      'uniform float uCycle;',
      'uniform float uNoiseScale;',
      'uniform float uNoiseAmt;',
      'uniform float uKnee;',
      'uniform float uPrism;',
      'uniform float uSharp;',
      '',
      'vec2 rot(vec2 v, float th){',
      '  float c = cos(th); float s = sin(th);',
      '  return vec2(c*v.x + s*v.y, -s*v.x + c*v.y);',
      '}',
      '',
      '/* 位相ずれ用の軽量FBMノイズ（3オクターブ） */',
      'float hash21(vec2 q){ q = fract(q*vec2(123.34, 345.45)); q += dot(q, q+34.345); return fract(q.x*q.y); }',
      'float vnoise(vec2 p){',
      '  vec2 i = floor(p); vec2 f = fract(p);',
      '  f = f*f*(3.0-2.0*f);',
      '  float a = hash21(i); float b = hash21(i+vec2(1.0,0.0));',
      '  float c = hash21(i+vec2(0.0,1.0)); float d = hash21(i+vec2(1.0,1.0));',
      '  return mix(mix(a,b,f.x), mix(c,d,f.x), f.y);',
      '}',
      'float fbm(vec2 p){',
      '  float v = 0.0; float a = 0.5;',
      '  for(int i=0;i<2;i++){ v += a*vnoise(p); p = p*2.03 + 17.1; a *= 0.5; }',
      '  return v;',
      '}',
      '',
      'float neuro(vec2 uv, float t){',
      '  vec2 sineAcc = vec2(0.0);',
      '  vec2 res = vec2(0.0);',
      '  float scale = 8.0;',
      '  for (int j = 0; j < 15; j++) {',
      '    uv = rot(uv, 1.0);',
      '    sineAcc = rot(sineAcc, 1.0);',
      '    vec2 layer = uv*scale + float(j) + sineAcc - t;',
      '    sineAcc += sin(layer);',
      '    res += (0.5 + 0.5*cos(layer)) / scale;',
      '    scale *= 1.2;',
      '  }',
      '  return res.x + res.y;',
      '}',
      '',
      'float shape(float n){',
      '  float s = 1.2*pow(n, 3.0) + 0.2*pow(n, 10.0);',
      '  return max(0.0, s - 0.55);',
      '}',
      '',
      '/* シャープ化：芯を締めて細く明るいラインにする */',
      'float sharpen(float v, float k){',
      '  return pow(clamp(v, 0.0, 1.0), k);',
      '}',
      '',
      'void main(){',
      '  /* 結合領域のグローバル座標（px）— セクション間で連続 */',
      '  float gx = vUv.x * uRes.x;',
      '  float gyDown = uTop + (1.0 - vUv.y) * uRes.y;',
      '  vec2 uv = vec2(gx, -gyDown) * (0.62 / uRefH);',
      ''
    ];
    var colorPart = useDeriv ? [
      '  /* 軽量版：neuro1回＋勾配方向へR/G/Bを分光（プリズム効果） */',
      '  /* 常時不規則化：異なる速度のノイズを重ね、非周期の一方向ドリフトを混ぜる */',
      '  float flowT = uTime',
      '    + 3.0 * fbm(vec2(uTime * 0.043, 5.3))',
      '    + 1.6 * fbm(vec2(uTime * 0.111, 19.7))',
      '    + 0.8 * fbm(vec2(uTime * 0.229, 42.1));',
      '  vec2 drift = vec2(uTime * 0.03, uTime * 0.021);',
      '  vec2 warp = vec2(fbm(uv * 0.6 + drift),',
      '                   fbm(uv * 0.6 - drift + 4.1)) - 0.5;',
      '  vec2 uvW = uv + 0.40 * warp;',
      '  /* 2層目：別スケール1.7倍・逆方向ドリフト・別時間速度0.7倍 */',
      '  float flowT2 = uTime * 0.7 + 2.4 * fbm(vec2(uTime * 0.067, 12.9));',
      '  vec2 drift2 = vec2(-uTime * 0.024, uTime * 0.031);',
      '  vec2 uvW2 = uv * 1.7 + 0.50 * (vec2(fbm(uv*0.9+drift2+21.0), fbm(uv*0.9-drift2+33.0))-0.5) + 7.0;',
      '  /* 3層目：軽量FBMの霞。独立時間・別方向で流れ、色帯もずらす */',
      '  float lay3 = smoothstep(0.55, 0.9, fbm(uv * 2.3 + vec2(uTime * 0.05, -uTime * 0.037) + 51.0));',
      '  float n = max(neuro(uvW, flowT), 0.8 * neuro(uvW2, flowT2));',
      '  vec2 g = vec2(dFdx(n), dFdy(n));',
      '  float dn = length(g) * uPrism;',
      '  float nr = shape(n + dn);',       // 長波長=外側
      '  float ng = shape(n);',            // 中波長=芯
      '  float nb = shape(n - dn);'        // 短波長=内側
    ] : [
      '  /* 互換版：中心差分で勾配方向を求め分光（プリズム効果） */',
      '  vec2 e = vec2(0.0012, 0.0);',
      '  float flowT = uTime',
      '    + 3.0 * fbm(vec2(uTime * 0.043, 5.3))',
      '    + 1.6 * fbm(vec2(uTime * 0.111, 19.7))',
      '    + 0.8 * fbm(vec2(uTime * 0.229, 42.1));',
      '  vec2 drift = vec2(uTime * 0.03, uTime * 0.021);',
      '  vec2 warp = vec2(fbm(uv * 0.6 + drift),',
      '                   fbm(uv * 0.6 - drift + 4.1)) - 0.5;',
      '  vec2 uvW = uv + 0.40 * warp;',
      '  float flowT2 = uTime * 0.7 + 2.4 * fbm(vec2(uTime * 0.067, 12.9));',
      '  vec2 drift2 = vec2(-uTime * 0.024, uTime * 0.031);',
      '  vec2 uvW2 = uv * 1.7 + 0.50 * (vec2(fbm(uv*0.9+drift2+21.0), fbm(uv*0.9-drift2+33.0))-0.5) + 7.0;',
      '  float lay3 = smoothstep(0.55, 0.9, fbm(uv * 2.3 + vec2(uTime * 0.05, -uTime * 0.037) + 51.0));',
      '  float n = max(neuro(uvW, flowT), 0.8 * neuro(uvW2, flowT2));',
      '  float gx = neuro(uvW + e.xy, flowT) - neuro(uvW - e.xy, flowT);',
      '  float gy = neuro(uvW + e.yx, flowT) - neuro(uvW - e.yx, flowT);',
      '  float dn = length(vec2(gx, gy)) * uPrism * 0.5;',
      '  float nr = shape(n + dn);',
      '  float ng = shape(n);',
      '  float nb = shape(n - dn);'
    ];
    var tail = [
      '',
      '  /* シャープ化：各波長成分の芯を締めて細く明るいラインに */',
      '  nr = sharpen(nr, uSharp); ng = sharpen(ng, uSharp); nb = sharpen(nb, uSharp);',
      '  float m = max(nr, max(ng, nb));',
      '  float ratio = pow(m, 1.4) / max(m, 1e-5);',
      '',
      '  vec2 nrm = vec2(vUv.x, gyDown / uTotal);',
      '  float vig = 1.0 - length(nrm - 0.5);',
      '  vec3 col = vec3(nr, ng, nb) * ratio * vig;',
      '  col += vec3(lay3) * 0.16 * vig;',   // 3層目の霞を薄く加算
      '  col = 1.0 - exp(-col * uKnee);',   // トーンマップ：白飛び防止
      '',
      '  /* 色相ドリフト：時間位相＋FBMによる空間位相ずれでパレットを参照。',
      '     輝度は構造側で決まり、色相から独立（ほぼ一定） */',
      '  float phase = uTime / uCycle',
      '              + uNoiseAmt * fbm(uv * uNoiseScale + uTime * 0.01)',
      '              + 0.50 * lay3;',   // 3層目領域は別の色帯に
      '  vec3 pal = texture2D(uPalette, vec2(phase, 0.5)).rgb;',
      '  col *= pal * 1.18;',   // パレット明度0.82の逆数で輝度を維持
      '',
      '  col = clamp(col, 0.0, 1.0);',
      '  float a = max(col.r, max(col.g, col.b));',
      '  gl_FragColor = vec4(col, a);',
      '}'
    ];
    return head + '\n' + core.concat(colorPart, tail).join('\n');
  }

  var sections = [];
  ['consoleSection'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) sections.push(el);
  });
  if (sections.length === 0) return;

  function docTop(el) {
    var r = el.getBoundingClientRect();
    return r.top + (window.pageYOffset || document.documentElement.scrollTop);
  }

  var region = { top: 0, total: 1 };
  function measureRegion() {
    var tops = sections.map(docTop);
    var bottoms = sections.map(function (el, i) { return tops[i] + el.offsetHeight; });
    region.top = Math.min.apply(null, tops);
    region.total = Math.max.apply(null, bottoms) - region.top;
  }

  /* ポインター（マウス／タップ）には反応させず、uTimeのみで自動アニメーション */
  function initNeuroFX(section) {
    var canvas = section.querySelector('canvas.neuro-bg-canvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.className = 'neuro-bg-canvas';   // 配置スタイルはCSS側で定義
      canvas.setAttribute('aria-hidden', 'true');
      section.insertBefore(canvas, section.firstChild);
    }
    var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) { if (window._fxError !== undefined) window._fxError = 'WebGL非対応'; return; }

    var deriv = !!gl.getExtension('OES_standard_derivatives');
    var FS = buildFS(deriv);

    function compile(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        if (window._fxError !== undefined) window._fxError = 'シェーダーエラー: ' + gl.getShaderInfoLog(s);
        return null;
      }
      return s;
    }
    var vs = compile(gl.VERTEX_SHADER, VS);
    var fs = compile(gl.FRAGMENT_SHADER, FS);
    if (!vs || !fs) return;
    var prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      if (window._fxError !== undefined) window._fxError = 'リンクエラー: ' + gl.getProgramInfoLog(prog);
      return;
    }
    gl.useProgram(prog);

    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(prog, 'aPos');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    /* パレットテクスチャ（512x1、横方向REPEATで周回が滑らかに繋がる） */
    var palTex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, palTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 512, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, buildPaletteData(512));
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

    var U = {};
    ['uTime','uRes','uTop','uTotal','uRefH','uPalette','uCycle','uNoiseScale','uNoiseAmt','uKnee','uPrism','uSharp']
      .forEach(function (nm) { U[nm] = gl.getUniformLocation(prog, nm); });

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.clearColor(0, 0, 0, 0);

    var scale = 1;
    function resize() {
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      scale = dpr * CONFIG.RES_SCALE;
      canvas.width = Math.max(1, Math.floor(section.clientWidth * scale));
      canvas.height = Math.max(1, Math.floor(section.offsetHeight * scale));
      gl.viewport(0, 0, canvas.width, canvas.height);
      measureRegion();
    }
    resize();
    window.addEventListener('resize', resize);

    var running = false, rafId = null;
    var t0 = performance.now();
    function loop() {
      if (!running) return;
      if (window._fxFrames !== undefined) window._fxFrames++;
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, palTex);
      gl.uniform1i(U.uPalette, 0);
      gl.uniform1f(U.uTime, (performance.now() - t0) / 1000);
      gl.uniform2f(U.uRes, canvas.width, canvas.height);
      gl.uniform1f(U.uTop, (docTop(section) + canvas.offsetTop - region.top) * scale);
      gl.uniform1f(U.uTotal, region.total * scale);
      gl.uniform1f(U.uRefH, window.innerHeight * scale);
      gl.uniform1f(U.uCycle, CONFIG.CYCLE_SECONDS);
      gl.uniform1f(U.uNoiseScale, CONFIG.HUE_NOISE_SCALE);
      gl.uniform1f(U.uNoiseAmt, CONFIG.HUE_NOISE_AMOUNT);
      gl.uniform1f(U.uKnee, CONFIG.GLOW_KNEE);
      gl.uniform1f(U.uPrism, CONFIG.PRISM_STRENGTH);
      gl.uniform1f(U.uSharp, CONFIG.LINE_SHARPNESS);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      rafId = requestAnimationFrame(loop);
    }
    function start() { if (running) return; running = true; resize(); rafId = requestAnimationFrame(loop); }
    function stop() { running = false; if (rafId) cancelAnimationFrame(rafId); gl.clear(gl.COLOR_BUFFER_BIT); }

    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { e.isIntersecting ? start() : stop(); });
      }, { threshold: 0 });
      io.observe(section);
      section._fxObserver = io;
    } else { start(); }
  }

  sections.forEach(initNeuroFX);
})();
