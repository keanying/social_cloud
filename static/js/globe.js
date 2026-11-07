/*
 * 首页 Hero 地球：Canvas 2D 绘制的低多边形风格星球 + 环绕的平台标签。
 * - 大陆由固定种子的随机“板块”生成，每次加载形状一致
 * - 根据 #stage[data-state] 调整转速：idle 正常 / loading 加速 / result 放缓
 * - 尊重 prefers-reduced-motion：只绘制静态一帧
 * - 不在视口内或页面隐藏时暂停渲染
 */
(function () {
    'use strict';

    const canvas = document.getElementById('globeCanvas');
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext('2d');
    const stage = document.getElementById('stage');
    const chipLayer = document.getElementById('globeChips');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ---------- 固定种子随机数，保证每次的大陆形状一致 ----------
    let seed = 20240611;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const toVec = (lat, lon) => [Math.cos(lat) * Math.sin(lon), Math.sin(lat), Math.cos(lat) * Math.cos(lon)];
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

    const plates = [];
    for (let i = 0; i < 16; i++) {
        plates.push({ c: toVec((rnd() * 1.5 - 0.75), rnd() * Math.PI * 2), r: 0.22 + rnd() * 0.3 });
    }

    // 斐波那契球面均匀采样
    const POINTS = 5600;
    const land = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < POINTS; i++) {
        const y = 1 - (i / (POINTS - 1)) * 2;
        const r = Math.sqrt(1 - y * y);
        const th = golden * i;
        const p = [Math.cos(th) * r, y, Math.sin(th) * r];
        let score = 0;
        for (const plate of plates) {
            const d = Math.acos(Math.max(-1, Math.min(1, dot(p, plate.c))));
            score = Math.max(score, 1 - d / plate.r);
        }
        score += 0.16 * Math.sin(p[0] * 9 + p[1] * 5) * Math.cos(p[2] * 7);
        if (Math.abs(p[1]) > 0.93) score = Math.max(score, 0.35); // 两极冰盖
        if (score > 0.06) land.push({ p, h: Math.min(1, score), polar: Math.abs(p[1]) > 0.9 });
    }

    const clouds = [];
    for (let i = 0; i < 26; i++) {
        const lat = rnd() * 1.6 - 0.8;
        const lon = rnd() * Math.PI * 2;
        const puffs = 2 + Math.floor(rnd() * 3);
        for (let k = 0; k < puffs; k++) {
            clouds.push({ p: toVec(lat + (rnd() - 0.5) * 0.1, lon + (rnd() - 0.5) * 0.14), s: 0.03 + rnd() * 0.028 });
        }
    }

    // ---------- 平台标签：均匀分布在环绕轨道上 ----------
    const chips = chipLayer ? Array.from(chipLayer.querySelectorAll('.globe-chip')) : [];
    const chipOrbit = chips.map((el, i) => {
        const lat = (((i * 0.618) % 1) * 1.3 - 0.65);
        const lon = (i / chips.length) * Math.PI * 2;
        return { el, p: toVec(lat, lon) };
    });

    // ---------- 尺寸 ----------
    let size = 0;
    let dpr = 1;
    function resize() {
        const rect = canvas.getBoundingClientRect();
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        size = Math.max(1, Math.round(rect.width));
        canvas.width = size * dpr;
        canvas.height = size * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        if (reduceMotion || !running) draw();
    }

    // ---------- 绘制 ----------
    const TILT = 0.38;
    const cosT = Math.cos(TILT), sinT = Math.sin(TILT);
    const LIGHT = (() => { const v = [-0.55, -0.55, 0.65]; const n = Math.hypot(...v); return v.map((x) => x / n); })();
    let yaw = 0.6;

    function rotate(p, extraYaw) {
        const a = yaw + (extraYaw || 0);
        const ca = Math.cos(a), sa = Math.sin(a);
        const x = p[0] * ca + p[2] * sa;
        const z1 = -p[0] * sa + p[2] * ca;
        const y = p[1] * cosT - z1 * sinT;
        const z = p[1] * sinT + z1 * cosT;
        return [x, y, z];
    }

    function draw() {
        if (!size) return;
        const c = size / 2;
        const R = size * 0.36;
        ctx.clearRect(0, 0, size, size);

        // 大气光晕
        const halo = ctx.createRadialGradient(c, c, R * 0.92, c, c, R * 1.32);
        halo.addColorStop(0, 'rgba(190,210,255,0.55)');
        halo.addColorStop(1, 'rgba(190,210,255,0)');
        ctx.fillStyle = halo;
        ctx.beginPath(); ctx.arc(c, c, R * 1.32, 0, Math.PI * 2); ctx.fill();

        // 海洋
        const ocean = ctx.createRadialGradient(c - R * 0.38, c - R * 0.42, R * 0.1, c, c, R);
        ocean.addColorStop(0, '#6f95ff');
        ocean.addColorStop(0.55, '#2f55e4');
        ocean.addColorStop(1, '#1b2fae');
        ctx.fillStyle = ocean;
        ctx.beginPath(); ctx.arc(c, c, R, 0, Math.PI * 2); ctx.fill();

        // 陆地：先画深色“崖壁”，再画受光顶面，形成凸起的低多边形质感
        const front = [];
        for (const pt of land) {
            const v = rotate(pt.p);
            if (v[2] > -0.05) front.push([v, pt]);
        }
        front.sort((a, b) => a[0][2] - b[0][2]);
        const base = R * 0.033;
        for (const [v, pt] of front) {
            const lift = 1 + 0.035 * pt.h;
            const x = c + v[0] * R * lift;
            const y = c + v[1] * R * lift;
            const rr = base * (0.55 + 0.45 * Math.max(0, v[2]));
            const light = Math.max(0, dot(v, LIGHT));
            ctx.fillStyle = pt.polar ? 'rgba(160,180,215,0.9)' : `hsl(95, 48%, ${22 + light * 10}%)`;
            ctx.beginPath(); ctx.arc(x + rr * 0.15, y + rr * 0.45, rr, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = pt.polar ? `hsl(220, 40%, ${86 + light * 10}%)` : `hsl(${78 + pt.h * 10}, 72%, ${40 + light * 24}%)`;
            ctx.beginPath(); ctx.arc(x, y, rr, 0, Math.PI * 2); ctx.fill();
        }

        // 背光面阴影
        const shade = ctx.createRadialGradient(c - R * 0.5, c - R * 0.5, R * 0.3, c, c, R * 1.05);
        shade.addColorStop(0, 'rgba(255,255,255,0.10)');
        shade.addColorStop(0.6, 'rgba(10,20,90,0)');
        shade.addColorStop(1, 'rgba(8,14,70,0.42)');
        ctx.fillStyle = shade;
        ctx.beginPath(); ctx.arc(c, c, R, 0, Math.PI * 2); ctx.fill();

        // 云朵（比地表转得略快）
        for (const cl of clouds) {
            const v = rotate(cl.p, yaw * 0.18);
            if (v[2] <= 0.02) continue;
            const x = c + v[0] * R * 1.1;
            const y = c + v[1] * R * 1.1;
            const rr = R * cl.s * (0.6 + 0.4 * v[2]);
            ctx.fillStyle = 'rgba(30,40,120,0.18)';
            ctx.beginPath(); ctx.arc(x + rr * 0.25, y + rr * 0.45, rr, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = `rgba(255,255,255,${0.75 + 0.25 * v[2]})`;
            ctx.beginPath(); ctx.arc(x, y, rr, 0, Math.PI * 2); ctx.fill();
        }

        // 平台标签
        for (const chip of chipOrbit) {
            const v = rotate(chip.p, -yaw * 0.35);
            const orbit = 1.26;
            const x = v[0] * orbit, y = v[1] * orbit;
            const hidden = v[2] < 0 && Math.hypot(x, y) < 1.02;
            const depth = (v[2] + 1) / 2;
            const scale = 0.72 + depth * 0.32;
            chip.el.style.transform = `translate(-50%, -50%) translate(${(c + x * R).toFixed(1)}px, ${(c + y * R).toFixed(1)}px) scale(${scale.toFixed(3)})`;
            chip.el.style.opacity = hidden ? '0' : (0.35 + depth * 0.65).toFixed(2);
            chip.el.style.zIndex = v[2] > 0 ? '3' : '1';
        }
    }

    // ---------- 动画循环 ----------
    let running = false;
    let visible = true;
    let last = 0;
    let speed = 0.16; // 弧度 / 秒
    function targetSpeed() {
        const state = stage ? stage.dataset.state : 'idle';
        if (state === 'loading') return 1.6;
        if (state === 'result') return 0.08;
        return 0.16;
    }
    function frame(t) {
        if (!running) return;
        const dt = last ? Math.min(0.05, (t - last) / 1000) : 0;
        last = t;
        speed += (targetSpeed() - speed) * Math.min(1, dt * 2.5);
        yaw += speed * dt;
        draw();
        requestAnimationFrame(frame);
    }
    function start() {
        if (reduceMotion || running || !visible || document.hidden) return;
        running = true; last = 0;
        requestAnimationFrame(frame);
    }
    function stop() { running = false; }

    if ('ResizeObserver' in window) new ResizeObserver(resize).observe(canvas);
    window.addEventListener('resize', resize);
    resize();

    if ('IntersectionObserver' in window) {
        new IntersectionObserver((entries) => {
            visible = entries[0].isIntersecting;
            visible ? start() : stop();
        }).observe(canvas);
    }
    document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
    start();
})();
