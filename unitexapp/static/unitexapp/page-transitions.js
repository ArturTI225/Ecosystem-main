(() => {
    const OVERLAY_SELECTOR = '[data-page-transition]';
    const MAIN_SELECTOR = '#main';
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const EASING = 'cubic-bezier(0.65, 0, 0.35, 1)';
    const DURATION = 450;
    const scrollPositions = new Map();

    const shouldReduceMotion = () => prefersReducedMotion.matches;

    const playOverlay = (phase) => {
        const overlay = document.querySelector(OVERLAY_SELECTOR);
        if (!overlay || shouldReduceMotion()) {
            if (phase === 'reveal' && overlay) {
                overlay.style.transform = 'scaleY(0)';
                overlay.style.display = 'none';
            }
            return Promise.resolve();
        }
        overlay.style.display = 'block';

        const frames = phase === 'cover'
            ? [
                { transform: 'scaleY(0)', transformOrigin: 'top center' },
                { transform: 'scaleY(1)', transformOrigin: 'top center' }
            ]
            : [
                { transform: 'scaleY(1)', transformOrigin: 'bottom center' },
                { transform: 'scaleY(0)', transformOrigin: 'bottom center' }
            ];

        try {
            const animation = overlay.animate(frames, {
                duration: DURATION,
                easing: EASING,
                fill: 'forwards'
            });
            return animation.finished.then(() => {
                if (phase === 'reveal') {
                    overlay.style.display = 'none';
                }
            }).catch(() => {});
        } catch (error) {
            if (phase === 'reveal') {
                overlay.style.display = 'none';
            }
            return Promise.resolve();
        }
    };

    const executeInlineScripts = (container) => {
        if (!container) {
            return;
        }
        const scripts = container.querySelectorAll('script[data-unitex-page-script]');
        scripts.forEach(original => {
            const clone = document.createElement('script');
            Array.from(original.attributes).forEach(({ name, value }) => {
                if (name === 'data-unitex-page-script') {
                    return;
                }
                clone.setAttribute(name, value);
            });
            clone.textContent = original.textContent;
            document.body.appendChild(clone);
            document.body.removeChild(clone);
        });
    };

    const focusMain = (container) => {
        const main = container?.querySelector(MAIN_SELECTOR);
        if (main && typeof main.focus === 'function') {
            requestAnimationFrame(() => {
                main.focus({ preventScroll: true });
            });
        }
    };

    const shouldPrevent = ({ el }) => {
        if (!el) {
            return false;
        }
        const href = el.getAttribute('href') || '';
        return href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:') || el.hasAttribute('data-barba-prevent');
    };

    const shouldRestoreScroll = (trigger) => trigger === 'popstate';

    const handleScrollRestoration = (trigger, namespace) => {
        const stored = scrollPositions.get(namespace);
        const target = shouldRestoreScroll(trigger) && typeof stored === 'number' ? stored : 0;
        window.scrollTo(0, target);
    };

    const bootstrap = () => {
        if (typeof window === 'undefined' || typeof window.barba === 'undefined') {
            return;
        }

        window.history.scrollRestoration = 'manual';

        window.barba.init({
            prefetch: true,
            prevent: shouldPrevent,
            schema: {
                wrapper: '[data-barba=\"wrapper\"]',
                container: '[data-barba=\"container\"]'
            },
            transitions: [{
                name: 'unitex-overlay',
                async leave(data) {
                    scrollPositions.set(data.current.namespace, window.scrollY);
                    await playOverlay('cover');
                },
                beforeEnter(data) {
                    handleScrollRestoration(data.trigger, data.next.namespace);
                },
                async enter(data) {
                    executeInlineScripts(data.next.container);
                    await playOverlay('reveal');
                    focusMain(data.next.container);
                }
            }]
        });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootstrap, { once: true });
    } else {
        bootstrap();
    }
})();
