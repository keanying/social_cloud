/*
 * 控制台交互层（参考 HeroUI / Inspira UI 的交互模式，原生实现，不改变任何业务逻辑）
 * - 按压涟漪 + 轻微缩放（HeroUI Button）
 * - 设置页标签的滑动指示块（HeroUI Tabs）
 * - 图标按钮的气泡提示（HeroUI Tooltip）
 * - 表格异步加载时的顶部进度条（HeroUI Progress）
 * - 概览数字滚动（Inspira Number Ticker）与彩色卡片聚光（Inspira Card Spotlight）
 * 系统开启「减少动态效果」时只保留提示与进度条。
 */
(function () {
    'use strict';
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ---------- 按压涟漪 ---------- */
    const PRESSABLE = '.cs-round, .cs-icon-btn, .cs-row-btn, .cs-rail a, .cs-pills a, .cs-seg a, .tab-nav-btn, .cs-content button.bg-brand, .cs-content a.bg-brand, .cs-auth button[type="submit"]';
    if (!reduce) {
        document.addEventListener('pointerdown', (e) => {
            const el = e.target.closest(PRESSABLE);
            if (!el || el.disabled) return;
            el.classList.add('cs-pressable');
            const rect = el.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height) * 2;
            const ripple = document.createElement('span');
            ripple.className = 'cs-ripple';
            ripple.style.width = ripple.style.height = `${size}px`;
            ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
            ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
            el.appendChild(ripple);
            ripple.addEventListener('animationend', () => ripple.remove());
        }, { passive: true });
    }

    /* ---------- 气泡提示 ---------- */
    const TIP_TARGETS = '.cs-round[title], .cs-icon-btn[title], .action-dropdown-trigger[title], .cs-bubbles span[title]';
    let tipEl = null;
    function showTip(el) {
        const text = el.getAttribute('data-tip-text');
        if (!text) return;
        if (!tipEl) {
            tipEl = document.createElement('div');
            tipEl.className = 'cs-tooltip';
            tipEl.setAttribute('role', 'tooltip');
            document.body.appendChild(tipEl);
        }
        tipEl.textContent = text;
        tipEl.classList.add('is-on');
        const r = el.getBoundingClientRect();
        const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
        let top = r.top - h - 8;
        let below = false;
        if (top < 8) { top = r.bottom + 8; below = true; }
        tipEl.classList.toggle('is-below', below);
        tipEl.style.top = `${top}px`;
        tipEl.style.left = `${Math.min(window.innerWidth - w - 8, Math.max(8, r.left + r.width / 2 - w / 2))}px`;
    }
    function hideTip() { if (tipEl) tipEl.classList.remove('is-on'); }
    function bindTips(root) {
        root.querySelectorAll(TIP_TARGETS).forEach((el) => {
            if (el.hasAttribute('data-tip-text')) return;
            el.setAttribute('data-tip-text', el.getAttribute('title'));
            if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', el.getAttribute('title'));
            el.removeAttribute('title');
        });
    }
    document.addEventListener('pointerover', (e) => { const el = e.target.closest('[data-tip-text]'); if (el) showTip(el); });
    document.addEventListener('pointerout', (e) => { if (e.target.closest('[data-tip-text]')) hideTip(); });
    document.addEventListener('focusin', (e) => { const el = e.target.closest('[data-tip-text]'); if (el) showTip(el); });
    document.addEventListener('focusout', hideTip);
    window.addEventListener('scroll', hideTip, true);

    /* ---------- 标签滑动指示块 ---------- */
    function bindTabCursor() {
        const first = document.querySelector('.tab-nav-btn');
        if (!first) return;
        const group = first.parentElement;
        if (group.querySelector('.cs-tab-cursor')) return;
        group.classList.add('cs-tabs');
        const cursor = document.createElement('span');
        cursor.className = 'cs-tab-cursor';
        group.prepend(cursor);
        const place = (animate) => {
            const active = [...group.querySelectorAll('.tab-nav-btn')].find((b) => b.classList.contains('bg-white'));
            if (!active) return;
            cursor.style.transition = animate && !reduce ? '' : 'none';
            cursor.style.width = `${active.offsetWidth}px`;
            cursor.style.height = `${active.offsetHeight}px`;
            cursor.style.transform = `translate(${active.offsetLeft}px, ${active.offsetTop}px)`;
            group.querySelectorAll('.tab-nav-btn').forEach((b) => b.classList.toggle('is-active', b === active));
        };
        new MutationObserver(() => place(true)).observe(group, { attributes: true, subtree: true, attributeFilter: ['class'] });
        window.addEventListener('resize', () => place(false));
        place(false);
    }

    /* ---------- 数字滚动 ---------- */
    function tickNumbers(root) {
        if (reduce) return;
        root.querySelectorAll('.cs-kpi-num, .cs-tile .big').forEach((el) => {
            if (el.dataset.ticked) return;
            const raw = el.textContent.trim();
            const m = raw.match(/^([+]?)([\d,]+(?:\.\d+)?)(%?)$/);
            if (!m) return;
            el.dataset.ticked = '1';
            const [, prefix, numText, suffix] = m;
            const end = parseFloat(numText.replace(/,/g, ''));
            const decimals = (numText.split('.')[1] || '').length;
            const grouped = numText.includes(',');
            if (!end) return;
            const fmt = (v) => {
                const s = v.toFixed(decimals);
                return prefix + (grouped ? Number(s).toLocaleString('en-US', { minimumFractionDigits: decimals }) : s) + suffix;
            };
            const t0 = performance.now(), dur = 900;
            const step = (t) => {
                const p = Math.min(1, (t - t0) / dur);
                el.textContent = fmt(end * (1 - Math.pow(1 - p, 3)));
                if (p < 1) requestAnimationFrame(step); else el.textContent = raw;
            };
            el.textContent = fmt(0);
            requestAnimationFrame(step);
        });
    }

    /* ---------- 彩色卡片聚光 ---------- */
    if (!reduce) {
        document.addEventListener('pointermove', (e) => {
            const card = e.target.closest('.cs-tile');
            if (!card) return;
            const r = card.getBoundingClientRect();
            card.style.setProperty('--mx', `${e.clientX - r.left}px`);
            card.style.setProperty('--my', `${e.clientY - r.top}px`);
        }, { passive: true });
    }

    /* ---------- 表格异步加载进度条 ---------- */
    function bindLoadingBar() {
        const main = document.querySelector('.cs-content > main');
        if (!main) return;
        const bar = document.createElement('div');
        bar.className = 'cs-progress';
        bar.setAttribute('aria-hidden', 'true');
        document.body.appendChild(bar);
        new MutationObserver(() => {
            const loading = main.classList.contains('pointer-events-none');
            bar.classList.toggle('is-on', loading);
            main.classList.toggle('cs-loading', loading);
            if (!loading) { bindTips(main); tickNumbers(main); }
        }).observe(main, { attributes: true, attributeFilter: ['class'] });
    }

    function init() {
        bindTips(document);
        bindTabCursor();
        tickNumbers(document);
        bindLoadingBar();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
