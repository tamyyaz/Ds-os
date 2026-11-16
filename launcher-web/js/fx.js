/* Background effects: a slow aurora (WebGL, half resolution) and drifting light motes (2D canvas).
   Both take the accent colour of the selected game. Failing to create WebGL just leaves the aurora out. */
(function () {
  "use strict";
  const FX = (window.FX = { setColors() {}, snap() {}, tick() {} });

  // ---- aurora -------------------------------------------------------------------------------
  const cv = document.getElementById("aurora");
  let gl = null, prog = null, uA, uB, uT, uAspect;
  try { gl = cv.getContext("webgl", { antialias: false, alpha: true, preserveDrawingBuffer: false }); } catch (e) { gl = null; }
  const col = { a: [0.54, 0.72, 1.0], b: [0.2, 0.2, 0.4], ta: [0.54, 0.72, 1.0], tb: [0.2, 0.2, 0.4] };

  if (gl) {
    const vs = "attribute vec2 p; varying vec2 v; void main(){ v = p * .5 + .5; gl_Position = vec4(p, 0., 1.); }";
    const fs = `precision mediump float; varying vec2 v; uniform vec3 uA, uB; uniform float uT, uAspect;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
        return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
      float fbm(vec2 p){ float s = 0., a = .5; for(int i = 0; i < 4; i++){ s += a * n(p); p *= 2.02; a *= .5; } return s; }
      void main(){
        vec2 p = vec2(v.x * uAspect, v.y);
        float t = uT * .06;
        float w = fbm(p * vec2(1.1, 2.0) + vec2(t, -t * .6) + fbm(p * 1.6 - t) * .9);
        float band = smoothstep(.35, .85, w) * (1. - smoothstep(.0, 1., v.y) * .55);
        float band2 = smoothstep(.45, .95, fbm(p * vec2(.7, 1.4) - vec2(t * .8, t) + 3.)) * .7;
        vec3 c = uA * band + uB * band2;
        float a = clamp(band * .8 + band2 * .6, 0., 1.);
        gl_FragColor = vec4(c, a);
      }`;
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; };
    prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { gl = null; } else {
      gl.useProgram(prog);
      const buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      const loc = gl.getAttribLocation(prog, "p");
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      uA = gl.getUniformLocation(prog, "uA"); uB = gl.getUniformLocation(prog, "uB");
      uT = gl.getUniformLocation(prog, "uT"); uAspect = gl.getUniformLocation(prog, "uAspect");
      gl.uniform1f(uAspect, cv.width / cv.height);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    }
  }

  // ---- motes ---------------------------------------------------------------------------------
  const mc = document.getElementById("motes");
  const mx = mc.getContext("2d");
  const motes = [];
  for (let i = 0; i < 70; i++) {
    motes.push({ x: Math.random(), y: Math.random(), z: Math.random(), s: 0.4 + Math.random() * 1.6, ph: Math.random() * 6.28 });
  }

  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  FX.setColors = (accent, deep) => { col.ta = hex(accent); col.tb = hex(deep).map((c, i) => c * 0.6 + col.ta[i] * 0.4); };

  FX.snap = () => { for (let i = 0; i < 3; i++) { col.a[i] = col.ta[i]; col.b[i] = col.tb[i]; } };

  FX.tick = (t, dt) => {
    for (let i = 0; i < 3; i++) { col.a[i] += (col.ta[i] - col.a[i]) * Math.min(1, dt * 2.2); col.b[i] += (col.tb[i] - col.b[i]) * Math.min(1, dt * 2.2); }
    if (gl) {
      gl.viewport(0, 0, cv.width, cv.height);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform3f(uA, col.a[0], col.a[1], col.a[2]);
      gl.uniform3f(uB, col.b[0], col.b[1], col.b[2]);
      gl.uniform1f(uT, t);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    const w = mc.width, h = mc.height;
    mx.clearRect(0, 0, w, h);
    const r = Math.round(col.a[0] * 255), g = Math.round(col.a[1] * 255), b = Math.round(col.a[2] * 255);
    for (const m of motes) {
      m.y -= dt * (0.012 + m.z * 0.03);
      m.x += Math.sin(t * 0.3 + m.ph) * dt * 0.006;
      if (m.y < -0.02) { m.y = 1.02; m.x = Math.random(); }
      const tw = 0.5 + 0.5 * Math.sin(t * 1.3 + m.ph);
      const rad = (1.5 + m.z * 5) * m.s;
      const gr = mx.createRadialGradient(m.x * w, m.y * h, 0, m.x * w, m.y * h, rad * 2.4);
      gr.addColorStop(0, `rgba(${r},${g},${b},${0.05 + 0.5 * m.z * tw})`);
      gr.addColorStop(1, `rgba(${r},${g},${b},0)`);
      mx.fillStyle = gr;
      mx.fillRect(m.x * w - rad * 3, m.y * h - rad * 3, rad * 6, rad * 6);
    }
  };
})();
