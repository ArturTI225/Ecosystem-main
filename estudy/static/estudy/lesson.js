(() => {
    const lessonRoot = document.querySelector('.lesson-root');
    if (!lessonRoot) {
        return;
    }

    const lessonSlug = lessonRoot.dataset.lessonSlug || 'lesson';
    const PROGRESS_STEPS = ['concept', 'example', 'practice', 'test', 'summary'];
    const sectionToStage = {
        concept: 'concept',
        example: 'example',
        practice: 'practice',
        test: 'test',
        summary: 'summary'
    };

    const safeStorage = {
        get(key) {
            try {
                return window.localStorage.getItem(key);
            } catch (error) {
                console.warn('LocalStorage get failed', error);
                return null;
            }
        },
        set(key, value) {
            try {
                window.localStorage.setItem(key, value);
            } catch (error) {
                console.warn('LocalStorage set failed', error);
            }
    }
};

const getCsrfToken = () => {
    const token = document.cookie
        .split(';')
        .map((row) => row.trim())
        .find((row) => row.startsWith('csrftoken='));
    return token ? decodeURIComponent(token.split('=')[1]) : '';
};

const loadState = (key, fallback = null) => {
    const raw = safeStorage.get(key);
    if (!raw) {
            return fallback;
        }
        try {
            return JSON.parse(raw);
        } catch (error) {
            console.warn('Failed to parse stored state', error);
            return fallback;
        }
    };

    if (window.Prism?.highlightAll) {
        window.Prism.highlightAll();
    }

    const initTabs = () => {
        document.querySelectorAll('[data-tab-group]').forEach((group) => {
            const triggers = group.querySelectorAll('[data-tab-trigger]');
            const panels = group.querySelectorAll('[data-tab-panel]');
            triggers.forEach((trigger) => {
                trigger.addEventListener('click', () => {
                    const targetId = trigger.dataset.tabTrigger;
                    if (!targetId) {
                        return;
                    }
                    triggers.forEach((btn) => {
                        const isActive = btn === trigger;
                        btn.classList.toggle('is-active', isActive);
                        btn.setAttribute('aria-selected', String(isActive));
                    });
                    panels.forEach((panel) => {
                        const matches = panel.dataset.tabPanel === targetId;
                        panel.classList.toggle('is-active', matches);
                        panel.toggleAttribute('hidden', !matches);
                    });
                });
            });
        });
    };

    initTabs();

    const sections = Array.from(document.querySelectorAll('[data-lesson-section]'));
    const tocLinks = Array.from(document.querySelectorAll('[data-lesson-toc-link]'));
    const mobileSelect = document.querySelector('#lesson-mobile-toc');
    const stageButtons = new Map(
        Array.from(document.querySelectorAll('[data-progress-stage]')).map((btn) => [btn.dataset.progressStage, btn])
    );
    let activeSectionId = null;
    let activeStage = 'concept';

    const setActiveSection = (id) => {
        if (!id || activeSectionId === id) {
            return;
        }
        activeSectionId = id;
        tocLinks.forEach((link) => {
            const matches = link.getAttribute('href') === `#${id}`;
            link.classList.toggle('is-active', matches);
        });
        if (mobileSelect && mobileSelect.value !== `#${id}`) {
            mobileSelect.value = `#${id}`;
        }
        const mapped = sectionToStage[id];
        if (mapped) {
            activeStage = mapped;
            updateProgressUI();
        }
    };

    const updateActiveSectionFromScroll = () => {
        if (!sections.length) {
            return;
        }
        const threshold = window.innerHeight * 0.35;
        let candidate = sections[0].id;
        sections.forEach((section) => {
            const top = section.getBoundingClientRect().top;
            if (top <= threshold) {
                candidate = section.id;
            }
        });
        setActiveSection(candidate);
    };

    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener('click', (event) => {
            const targetId = anchor.getAttribute('href');
            if (!targetId || targetId === '#' || targetId === '#0') {
                return;
            }
            const target = document.querySelector(targetId);
            if (!target) {
                return;
            }
            event.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    tocLinks.forEach((link) => {
        link.addEventListener('click', (event) => {
            const href = link.getAttribute('href');
            if (href && href.startsWith('#')) {
                event.preventDefault();
                const target = document.querySelector(href);
                target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    mobileSelect?.addEventListener('change', (event) => {
        const target = document.querySelector(event.target.value);
        target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    let sectionUpdateScheduled = false;
    const scheduleSectionUpdate = () => {
        if (sectionUpdateScheduled) {
            return;
        }
        sectionUpdateScheduled = true;
        window.requestAnimationFrame(() => {
            updateActiveSectionFromScroll();
            sectionUpdateScheduled = false;
        });
    };

    window.addEventListener('scroll', scheduleSectionUpdate, { passive: true });
    window.addEventListener('resize', scheduleSectionUpdate);

    const progressKey = `lesson-progress-state-${lessonSlug}`;
    const defaultProgressState = PROGRESS_STEPS.reduce((acc, step) => {
        acc[step] = false;
        return acc;
    }, { summaryRewarded: false });

    const progressState = Object.assign(defaultProgressState, loadState(progressKey, {}));
    if (typeof progressState.summaryRewarded !== 'boolean') {
        progressState.summaryRewarded = false;
    }

    const progressBar = document.querySelector('[data-lesson-progress-bar]');
    const progressLabels = document.querySelectorAll('[data-lesson-progress-count]');
    const levelupBanner = document.querySelector('[data-levelup]');
    const summaryCard = document.querySelector('[data-summary-card]');

    const persistProgressState = () => {
        safeStorage.set(progressKey, JSON.stringify(progressState));
    };

    const xpCard = document.querySelector('[data-xp-card]');
    const xpAmountNode = xpCard?.querySelector('[data-xp-amount]');
    const xpLevelNode = xpCard?.querySelector('[data-xp-level]');
    const xpBadgeNode = xpCard?.querySelector('[data-xp-badge]');
    const xpStreakNode = xpCard?.querySelector('[data-xp-streak]');
    const xpMessageNode = xpCard?.querySelector('[data-xp-message]');
    const streakMessages = document.querySelectorAll('[data-streak-message]');
    const xpRewardTotal = Number.parseInt(xpCard?.dataset.xpReward || '0', 10) || 40;
    const xpStorageKey = xpCard?.dataset.xpKey || `lesson-xp-${lessonSlug}`;

    const defaultXpState = {
        total: Number.parseInt(xpAmountNode?.textContent || '0', 10) || 0,
        level: 1,
        badge: 'Beginner',
        streak: 0,
        lastPlayedAt: null
    };

    const xpState = Object.assign(defaultXpState, loadState(xpStorageKey, null) || {});

    const computeLevel = (xp) => Math.max(1, Math.floor(xp / 120) + 1);
    const computeBadge = (level) => {
        if (level >= 5) {
            return 'Legend';
        }
        if (level >= 3) {
            return 'Explorer';
        }
        return 'Beginner';
    };

    const persistXpState = () => {
        safeStorage.set(xpStorageKey, JSON.stringify(xpState));
    };

    const updateStreakMessage = () => {
        const text = xpState.streak
            ? `Tu deja ai parcurs ${xpState.streak} zile la rand. Tine-l aprins!`
            : 'Prima zi din streak incepe acum.';
        streakMessages.forEach((node) => {
            node.textContent = text;
        });
    };

    const updateXpCard = () => {
        if (!xpCard) {
            return;
        }
        if (xpAmountNode) {
            xpAmountNode.textContent = xpState.total;
        }
        if (xpLevelNode) {
            xpLevelNode.textContent = xpState.level;
        }
        if (xpBadgeNode) {
            xpBadgeNode.textContent = xpState.badge;
        }
        if (xpStreakNode) {
            xpStreakNode.textContent = xpState.streak || 0;
        }
        if (xpMessageNode) {
            xpMessageNode.textContent = xpState.streak
                ? `Tu deja ai trecut ${xpState.streak} misiuni la rand!`
                : 'Completeaza prima misiune pentru a porni streak-ul.';
        }
        updateStreakMessage();
    };

    const awardXp = (amount, reason) => {
        if (!xpCard || !amount) {
            return;
        }
        const now = new Date();
        const lastAward = xpState.lastPlayedAt ? new Date(xpState.lastPlayedAt) : null;
        xpState.total = Math.max(0, Math.round(xpState.total + amount));
        if (lastAward) {
            const diffDays = Math.floor((now - lastAward) / 86400000);
            if (diffDays === 1) {
                xpState.streak = (xpState.streak || 0) + 1;
            } else if (diffDays > 1) {
                xpState.streak = 1;
            }
        } else {
            xpState.streak = 1;
        }
        xpState.lastPlayedAt = now.toISOString();
        xpState.level = computeLevel(xpState.total);
        xpState.badge = computeBadge(xpState.level);
        xpState.lastReason = reason || '';
        persistXpState();
        updateXpCard();
    };

    updateXpCard();

    const STEP_XP = {
        example: 10,
        practice: 5,
        test: 7,
        summary: xpRewardTotal
    };

    const triggerXpReward = (step) => {
        const amount = STEP_XP[step];
        if (amount) {
            awardXp(amount, step);
        }
    };

    const updateProgressUI = () => {
        const completed = PROGRESS_STEPS.reduce((acc, step) => acc + (progressState[step] ? 1 : 0), 0);
        const percent = Math.round((completed / PROGRESS_STEPS.length) * 100);
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            progressBar.setAttribute('aria-valuenow', String(percent));
        }
        progressLabels.forEach((node) => {
            node.textContent = percent;
        });
        stageButtons.forEach((button, stage) => {
            button.classList.toggle('is-complete', !!progressState[stage]);
            button.classList.toggle('is-active', stage === activeStage);
        });
    };

    const handleSummaryUnlocked = () => {
        if (levelupBanner) {
            levelupBanner.removeAttribute('aria-hidden');
            levelupBanner.classList.add('is-visible');
        }
        summaryCard?.classList.add('is-celebrating');
        if (!progressState.summaryRewarded) {
            triggerXpReward('summary');
            progressState.summaryRewarded = true;
            persistProgressState();
        }
    };

    const setProgressStep = (step, value, { skipAuto = false } = {}) => {
        if (!(step in progressState) || progressState[step] === value) {
            return false;
        }
        progressState[step] = value;
        if (!value && step !== 'summary' && progressState.summary) {
            progressState.summary = false;
        }
        persistProgressState();
        updateProgressUI();
        if (value && step !== 'summary') {
            triggerXpReward(step);
        }
        if (step === 'summary' && value) {
            handleSummaryUnlocked();
        }
        if (!skipAuto && step !== 'summary') {
            const coreStepsComplete = PROGRESS_STEPS
                .filter((name) => name !== 'summary')
                .every((name) => progressState[name]);
            if (coreStepsComplete) {
                setProgressStep('summary', true, { skipAuto: true });
            }
        }
        return true;
    };

    updateProgressUI();

    const conceptSection = document.querySelector('#concept');
    if (conceptSection && !progressState.concept && 'IntersectionObserver' in window) {
        const conceptObserver = new IntersectionObserver((entries) => {
            if (entries.some((entry) => entry.isIntersecting)) {
                setProgressStep('concept', true);
                conceptObserver.disconnect();
            }
        }, { threshold: 0.4 });
        conceptObserver.observe(conceptSection);
    }

    document.querySelectorAll('[data-copy-code]').forEach((button) => {
        button.addEventListener('click', async () => {
            const wrapper = button.closest('[data-code-block]') || button.closest('.lesson-snippet');
            const codeElement = wrapper?.querySelector('code');
            if (!codeElement) {
                return;
            }
            try {
                await navigator.clipboard.writeText(codeElement.innerText.trim());
                const original = button.textContent;
                button.textContent = 'Copiat!';
                setTimeout(() => {
                button.textContent = original || 'Copiaza';
                }, 1600);
            } catch (error) {
                console.error('Copy failed', error);
            }
        });
    });

    const codeLab = document.querySelector('[data-code-lab]');
    if (codeLab) {
        const codeInput = codeLab.querySelector('[data-code-input]');
        const codePreviewWrapper = codeLab.querySelector('[data-code-preview]');
        const codePreview = codePreviewWrapper?.querySelector('code') || codePreviewWrapper;
        const codeOutput = codeLab.querySelector('[data-code-output]');
        const codeStatus = codeLab.querySelector('[data-code-status]');
        const stdinField = codeLab.querySelector('[data-code-stdin]');
        const runButton = codeLab.querySelector('[data-code-run]');
        const resetButton = codeLab.querySelector('[data-code-reset]');
        const rewardBadge = codeLab.querySelector('[data-code-reward]');
        const initialCode = codeInput?.value || '';
        const defaultConsoleText = codeOutput?.textContent || 'Consola asteapta sa rulezi codul...';

        const syncPreview = () => {
            if (!codeInput || !codePreview) {
                return;
            }
            codePreview.textContent = codeInput.value;
            if (window.Prism?.highlightElement) {
                window.Prism.highlightElement(codePreview);
            }
        };

        codeInput?.addEventListener('input', () => {
            syncPreview();
            setProgressStep('example', false, { skipAuto: true });
        });
        syncPreview();

        if (codeOutput) {
            codeOutput.textContent = defaultConsoleText;
        }

        let pyodideReady = null;
        const ensurePyodide = async () => {
            if (!pyodideReady) {
                pyodideReady = loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/' });
            }
            return pyodideReady;
        };

        const runPythonCode = async (sourceCode) => {
            const pyodide = await ensurePyodide();
            pyodide.globals.set('UNITEX_STDIN_RAW', (stdinField?.value || '').toString());
            await pyodide.runPythonAsync(`
from io import StringIO
import sys, builtins
from collections import deque
_unitex_stdout = sys.stdout
_unitex_stderr = sys.stderr
sys.stdout = StringIO()
sys.stderr = StringIO()
try:
    _unitex_original_input
except NameError:
    _unitex_original_input = builtins.input
_unitex_queue = deque(UNITEX_STDIN_RAW.splitlines()) if UNITEX_STDIN_RAW else deque()
def _unitex_input(prompt=None):
    return _unitex_queue.popleft() if _unitex_queue else ""
builtins.input = _unitex_input
`);
            let resultText = '';
            try {
                const result = await pyodide.runPythonAsync(sourceCode);
                const stdout = pyodide.runPython('sys.stdout.getvalue()');
                const stderr = pyodide.runPython('sys.stderr.getvalue()');
                resultText = [stdout, stderr].filter(Boolean).join('\n').trim();
                if (!resultText && typeof result !== 'undefined') {
                    resultText = String(result);
                }
            } finally {
                await pyodide.runPythonAsync(`
sys.stdout = _unitex_stdout
sys.stderr = _unitex_stderr
import builtins
builtins.input = _unitex_original_input
`);
            }
            return resultText || 'Nu exista output. Foloseste print() pentru a afisa valori.';
        };

        const showCodeReward = () => {
            if (!rewardBadge) {
                return;
            }
            rewardBadge.classList.add('is-visible');
            setTimeout(() => {
                rewardBadge.classList.remove('is-visible');
            }, 1900);
        };

        runButton?.addEventListener('click', async () => {
            if (!codeInput || !codeOutput || runButton.disabled) {
                return;
            }
            runButton.disabled = true;
            if (codeStatus) {
                codeStatus.textContent = 'Se incarca runtime-ul...';
            }
            try {
                await ensurePyodide();
                if (codeStatus) {
                    codeStatus.textContent = 'Rulez codul...';
                }
                const textResult = await runPythonCode(codeInput.value);
                codeOutput.textContent = `Rezultat:\\n${textResult}`;
                codeOutput.style.color = 'var(--lesson-success)';
                if (codeStatus) {
                    codeStatus.textContent = 'Executarea a reusit.';
                }
                const changed = setProgressStep('example', true);
                if (changed) {
                    showCodeReward();
                }
            } catch (error) {
                console.error(error);
                codeOutput.textContent = `Rezultat:\\nUps! Codul s-a oprit.\\nMesaj: ${error.message}`;
                codeOutput.style.color = 'var(--lesson-danger)';
                if (codeStatus) {
                    codeStatus.textContent = 'Incearca sa corectezi codul si ruleaza din nou.';
                }
                setProgressStep('example', false);
            } finally {
                runButton.disabled = false;
            }
        });

        resetButton?.addEventListener('click', () => {
            if (!codeInput || !codeOutput) {
                return;
            }
            codeInput.value = initialCode;
            if (stdinField) {
                stdinField.value = '';
            }
            syncPreview();
            codeOutput.textContent = defaultConsoleText;
            codeOutput.style.color = '';
            if (codeStatus) {
                codeStatus.textContent = 'Pregatit ⚡';
            }
            setProgressStep('example', false);
        });
    }

    document.querySelectorAll('[data-hint-toggle]').forEach((button) => {
        const panel = button.closest('.practice-subcard')?.querySelector('[data-hint-panel]');
        button.addEventListener('click', () => {
            if (!panel) {
                return;
            }
            const isHidden = panel.hasAttribute('hidden');
            panel.toggleAttribute('hidden', !isHidden);
            button.setAttribute('aria-expanded', String(isHidden));
        });
    });

    const practiceContainer = document.querySelector('[data-drag-container]');
    const orderFeedback = document.querySelector('[data-order-feedback]');
    const orderCelebration = document.querySelector('[data-order-celebration]');
    const practiceExplanation = document.querySelector('[data-practice-explanation]');
    const practiceDefaultExplanation = practiceExplanation?.dataset.practiceDefault || practiceExplanation?.textContent || '';
    const successMessage = document.querySelector('[data-draggable-target]')?.dataset.successMessage || 'Super! Ordinea este corecta.';

    if (practiceContainer && window.Sortable) {
        const sourceList = practiceContainer.querySelector('[data-draggable-source]');
        const dropZones = Array.from(practiceContainer.querySelectorAll('[data-drop-zone]'));

        const ensurePlaceholder = (zone) => {
            if (!zone.querySelector('[data-placeholder]')) {
                const placeholder = document.createElement('span');
                placeholder.dataset.placeholder = 'true';
                placeholder.textContent = 'Trage elementul aici';
                zone.appendChild(placeholder);
            }
        };

        const resetPractice = () => {
            if (!sourceList) {
                return;
            }
            dropZones.forEach((zone) => {
                const slot = zone.closest('.match-slot');
                const tokens = Array.from(zone.querySelectorAll('.match-token'));
                tokens.forEach((token) => {
                    token.classList.remove('match-token--compact', 'is-correct', 'is-wrong');
                    sourceList.appendChild(token);
                });
                zone.innerHTML = '';
                ensurePlaceholder(zone);
                slot?.classList.remove('is-filled', 'is-correct', 'is-wrong');
            });
            orderCelebration?.classList.remove('is-visible');
            if (orderFeedback) {
                orderFeedback.textContent = '';
                orderFeedback.classList.remove('success', 'error');
            }
            if (practiceExplanation) {
                practiceExplanation.textContent = practiceDefaultExplanation;
            }
            setProgressStep('practice', false);
        };

        if (sourceList) {
            Sortable.create(sourceList, {
                group: { name: 'lesson-practice', pull: true, put: true },
                animation: 180,
                sort: false
            });
        }

        dropZones.forEach((zone) => {
            ensurePlaceholder(zone);
            Sortable.create(zone, {
                group: { name: 'lesson-practice', pull: true, put: true },
                animation: 150,
                sort: false,
                onAdd(evt) {
                    const slot = zone.closest('.match-slot');
                    zone.querySelector('[data-placeholder]')?.remove();
                    const existing = zone.querySelectorAll('.match-token');
                    if (existing.length > 1 && sourceList) {
                        Array.from(existing)
                            .slice(0, -1)
                            .forEach((token) => sourceList.appendChild(token));
                    }
                    evt.item.classList.add('match-token--compact');
                    slot?.classList.add('is-filled');
                    orderFeedback?.classList.remove('success', 'error');
                    setProgressStep('practice', false, { skipAuto: true });
                },
                onRemove() {
                    if (!zone.querySelector('.match-token')) {
                        zone.closest('.match-slot')?.classList.remove('is-filled', 'is-correct', 'is-wrong');
                        ensurePlaceholder(zone);
                    }
                }
            });
        });

        const checkButton = document.querySelector('[data-order-check]');
        const resetButton = document.querySelector('[data-order-reset]');

        checkButton?.addEventListener('click', () => {
            if (!dropZones.length) {
                return;
            }
            let perfectMatch = true;
            let firstWrongLabel = '';
            dropZones.forEach((zone) => {
                const slot = zone.closest('.match-slot');
                slot?.classList.remove('is-correct', 'is-wrong');
                const expected = zone.dataset.expectedId;
                const token = zone.querySelector('.match-token');
                if (token && expected && token.dataset.id === expected) {
                    slot?.classList.add('is-correct');
                } else {
                    slot?.classList.add('is-wrong');
                    perfectMatch = false;
                    if (!firstWrongLabel) {
                        firstWrongLabel = slot?.querySelector('.match-slot__label')?.textContent?.trim() || '';
                    }
                }
            });

            if (perfectMatch) {
                if (orderFeedback) {
                    orderFeedback.textContent = successMessage;
                    orderFeedback.classList.add('success');
                    orderFeedback.classList.remove('error');
                }
                orderCelebration?.classList.add('is-visible');
                if (practiceExplanation) {
                    practiceExplanation.textContent = 'Ai asociat perfect toate conceptele. XP +5!';
                }
                setProgressStep('practice', true);
            } else {
                if (orderFeedback) {
                    orderFeedback.textContent = firstWrongLabel
                        ? `Mai verifica potrivirea pentru \"${firstWrongLabel}\".`
                        : 'Mai incearca – unele potriviri sunt gresite.';
                    orderFeedback.classList.add('error');
                    orderFeedback.classList.remove('success');
                }
                if (practiceExplanation) {
                    practiceExplanation.textContent = firstWrongLabel
                        ? `Indiciu: reciteste descrierea pentru \"${firstWrongLabel}\" si cauta cuvintele cheie din token.`
                        : practiceDefaultExplanation;
                }
                orderCelebration?.classList.remove('is-visible');
                setProgressStep('practice', false, { skipAuto: true });
            }
        });

        resetButton?.addEventListener('click', () => {
            resetPractice();
        });

        if (progressState.practice) {
            orderCelebration?.classList.add('is-visible');
            if (orderFeedback) {
                orderFeedback.textContent = successMessage;
                orderFeedback.classList.add('success');
            }
        }
    }

    const quizCard = document.querySelector('[data-quiz]');
    const quizForm = quizCard?.querySelector('form');
    const quizSubmitUrl = quizCard?.dataset.submitHref || quizForm?.getAttribute('action');
    const quizOptions = Array.from(quizCard?.querySelectorAll('[data-quiz-option]') ?? []);
    const quizReset = quizCard?.querySelector('[data-quiz-reset]');
    const quizFeedback = quizCard?.querySelector('[data-quiz-feedback]');
    const quizExplanationBlock = quizCard?.querySelector('[data-quiz-explanation-block]');
    const quizExplanationText = quizCard?.querySelector('[data-quiz-explanation-text]');
    const quizExplanation = quizCard?.dataset.quizExplanation || 'Gandeste-te la definitia conceptului si cum il folosesti ulterior.';
    const quizStorageKey = `lesson-quiz-${lessonSlug}`;
    const quizSubmitButton = quizForm?.querySelector('button[type="submit"]');

    const updateOptionStates = () => {
        quizOptions.forEach((label) => {
            const input = label.querySelector('input');
            label.classList.toggle('is-selected', input?.checked || false);
        });
    };

    const clearOptionHighlights = () => {
        quizOptions.forEach((label) => label.classList.remove('is-correct', 'is-wrong'));
    };

    const highlightQuizResult = ({ selectedValue, correctValue, isCorrect }) => {
        clearOptionHighlights();
        quizOptions.forEach((label) => {
            const input = label.querySelector('input');
            if (!input) {
                return;
            }
            if (input.value === selectedValue) {
                label.classList.add(isCorrect ? 'is-correct' : 'is-wrong');
            }
            if (!isCorrect && input.value === correctValue) {
                label.classList.add('is-correct');
            }
        });
    };

    const persistQuiz = (value) => {
        safeStorage.set(quizStorageKey, JSON.stringify(value));
    };

    const applyStoredQuiz = () => {
        const stored = loadState(quizStorageKey, null);
        quizForm?.reset();
        clearOptionHighlights();
        updateOptionStates();
        if (!stored || !stored.answer) {
            quizFeedback?.classList.remove('success', 'error');
            if (quizFeedback) {
                quizFeedback.textContent = '';
            }
            quizExplanationBlock?.classList.add('hidden');
            if (quizExplanationText) {
                quizExplanationText.textContent = quizExplanation;
            }
            setProgressStep('test', false);
            return;
        }
        quizForm?.querySelectorAll('input[name="answer"]').forEach((input) => {
            input.checked = input.value === stored.answer;
        });
        updateOptionStates();
        highlightQuizResult({
            selectedValue: stored.answer,
            correctValue: stored.correctAnswer || stored.answer,
            isCorrect: !!stored.correct,
        });
        if (quizFeedback) {
            quizFeedback.textContent = stored.message || '';
            quizFeedback.classList.toggle('success', !!stored.correct);
            quizFeedback.classList.toggle('error', !stored.correct);
        }
        if (quizExplanationBlock) {
            quizExplanationBlock.classList.remove('hidden');
        }
        if (quizExplanationText) {
            quizExplanationText.textContent = stored.explanation || quizExplanation;
        }
        setProgressStep('test', !!stored.correct);
    };

    quizOptions.forEach((label) => {
        const input = label.querySelector('input');
        input?.addEventListener('change', () => {
            updateOptionStates();
            clearOptionHighlights();
            quizFeedback?.classList.remove('success', 'error');
        });
    });

    quizForm?.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!quizSubmitUrl) {
            return;
        }
        const formData = new FormData(quizForm);
        const answer = formData.get('answer');
        if (!answer) {
            if (quizFeedback) {
                quizFeedback.textContent = 'Alege o variantă înainte de a trimite.';
                quizFeedback.classList.add('error');
                quizFeedback.classList.remove('success');
            }
            return;
        }
        quizFeedback?.classList.remove('success', 'error');
        if (quizFeedback) {
            quizFeedback.textContent = 'Se verifică răspunsul...';
        }
        quizSubmitButton?.setAttribute('disabled', 'disabled');
        try {
            const response = await fetch(quizSubmitUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ answer }),
            });
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }
            const data = await response.json();
            const isCorrect = Boolean(data.is_correct);
            const correctAnswer = data.correct_answer || answer;
            const explanationText = data.explanation || quizExplanation;
            highlightQuizResult({ selectedValue: answer, correctValue: correctAnswer, isCorrect });
            if (quizFeedback) {
                quizFeedback.textContent = isCorrect
                    ? 'Corect! Continuă seria.'
                    : `Răspunsul corect este: ${correctAnswer}.`;
                quizFeedback.classList.toggle('success', isCorrect);
                quizFeedback.classList.toggle('error', !isCorrect);
            }
            if (quizExplanationBlock) {
                quizExplanationBlock.classList.remove('hidden');
            }
            if (quizExplanationText) {
                quizExplanationText.textContent = explanationText;
            }
            persistQuiz({
                answer,
                correct: isCorrect,
                correctAnswer,
                explanation: explanationText,
                message: quizFeedback?.textContent,
            });
            setProgressStep('test', isCorrect);
            if (isCorrect && data.lesson_completed) {
                const toggleButton = document.querySelector('.toggle-completion');
                setLessonCompletionUI(true, toggleButton || null);
                updateProgressDisplays({
                    percent: data.progress_percent,
                    completed: data.completed_count,
                    total: data.total_lessons,
                });
            }
        } catch (error) {
            console.error('Quiz submission failed', error);
            if (quizFeedback) {
                quizFeedback.textContent = 'A apărut o eroare. Încearcă din nou.';
                quizFeedback.classList.add('error');
                quizFeedback.classList.remove('success');
            }
        } finally {
            quizSubmitButton?.removeAttribute('disabled');
        }
    });

    quizReset?.addEventListener('click', () => {
        quizForm?.reset();
        clearOptionHighlights();
        updateOptionStates();
        if (quizFeedback) {
            quizFeedback.textContent = '';
            quizFeedback.classList.remove('success', 'error');
        }
        quizExplanationBlock?.classList.add('hidden');
        if (quizExplanationText) {
            quizExplanationText.textContent = quizExplanation;
        }
        persistQuiz({});
        setProgressStep('test', false);
    });

    applyStoredQuiz();

    const wireAiHintForms = () => {
        document.querySelectorAll('[data-ai-hint-form]').forEach((form) => {
            const action = form.getAttribute('action');
            const textarea = form.querySelector('textarea[name="question"]');
            const submitButton = form.querySelector('button[type="submit"]');
            const statusNode = form.querySelector('[data-ai-hint-status]');
            const resultBlock = form.querySelector('[data-ai-hint-output]');
            const resultText = resultBlock?.querySelector('p');

            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                if (!action || !textarea) {
                    return;
                }
                const question = textarea.value.trim();
                if (question.length < 6) {
                    if (statusNode) {
                        statusNode.textContent = 'Scrie o întrebare puțin mai detaliată.';
                    }
                    return;
                }
                submitButton?.setAttribute('disabled', 'disabled');
                if (statusNode) {
                    statusNode.textContent = 'Se trimite cererea către asistent...';
                }
                resultBlock?.classList.add('hidden');
                try {
                    const response = await fetch(action, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest',
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: new URLSearchParams({ question }),
                    });
                    if (!response.ok) {
                        throw new Error(`Server responded with ${response.status}`);
                    }
                    const data = await response.json();
                    if (resultText) {
                        resultText.textContent = data.answer || 'Nu am reușit să generăm un indiciu acum.';
                    }
                    resultBlock?.classList.remove('hidden');
                    if (statusNode) {
                        statusNode.textContent = 'Gata! Vezi răspunsul mai jos.';
                    }
                } catch (error) {
                    console.error('AI hint failed', error);
                    if (statusNode) {
                        statusNode.textContent = 'Nu am putut obține indiciul. Încearcă din nou.';
                    }
                } finally {
                    submitButton?.removeAttribute('disabled');
                }
            });
        });
    };

    wireAiHintForms();

    document.querySelectorAll('[data-accordion]').forEach((accordion) => {
        const toggle = accordion.querySelector('[data-accordion-toggle]');
        const panel = accordion.querySelector('[data-accordion-panel]');
        toggle?.addEventListener('click', () => {
            if (!panel) {
                return;
            }
            const isOpen = panel.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', String(isOpen));
        });
    });

    scheduleSectionUpdate();
})();
