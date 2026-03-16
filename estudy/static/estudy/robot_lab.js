(() => {
    const root = document.querySelector("[data-robotlab-play]");
    if (!root) {
        return;
    }

    const levelDataNode = document.querySelector("#robot-lab-level-data");
    if (!levelDataNode) {
        return;
    }

    const parseJSON = (text, fallback) => {
        try {
            const value = JSON.parse(text);
            return value && typeof value === "object" ? value : fallback;
        } catch (error) {
            console.error("Failed to parse Robot Lab level JSON", error);
            return fallback;
        }
    };

    const level = parseJSON(levelDataNode.textContent || "{}", {});
    const runUrl = root.dataset.runUrl || "";
    const levelId = root.dataset.levelId || level.id || "";
    const starterCode = level.starter_code || "";
    const grid = Array.isArray(level.grid) ? level.grid.map((row) => String(row)) : [];
    const maxCols = grid.reduce((acc, row) => Math.max(acc, row.length), 0);
    const tileSprites = [1, 2, 3, 4].map((idx) => `/static/estudy/game/tiles/tile-${idx}.png`);
    const wallSprites = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((idx) => `/static/estudy/game/walls/wall-${idx}.png`);

    const gridNode = root.querySelector("[data-robot-grid]");
    const codeInput = root.querySelector("[data-code-input]");
    const runBtn = root.querySelector("[data-run-btn]");
    const resetCodeBtn = root.querySelector("[data-reset-code]");
    const statusNode = root.querySelector("[data-run-status]");
    const requestSolution = root.querySelector("[data-request-solution]");
    const traceList = root.querySelector("[data-trace-list]");

    const mentorNodes = {
        what: root.querySelector("[data-mentor-what]"),
        mistake: root.querySelector("[data-mentor-mistake]"),
        hint1: root.querySelector("[data-mentor-h1]"),
        hint2: root.querySelector("[data-mentor-h2]"),
        focus: root.querySelector("[data-mentor-focus]"),
        encourage: root.querySelector("[data-mentor-encourage]"),
        solutionWrap: root.querySelector("[data-mentor-solution-wrap]"),
        solution: root.querySelector("[data-mentor-solution]"),
    };

    const hintModal = root.querySelector("[data-hint-modal]");
    const hintModalTitle = root.querySelector("[data-hint-modal-title]");
    const hintModalContent = root.querySelector("[data-hint-modal-content]");
    const hintButtons = Array.from(root.querySelectorAll("[data-hint-open]"));
    const hintCloseButtons = Array.from(root.querySelectorAll("[data-hint-modal-close]"));

    const HINT_CONFIG = {
        what: {
            title: "Ce s-a intamplat",
            node: mentorNodes.what,
            fallback: "Ruleaza codul pentru a primi feedback pe rezultat.",
        },
        mistake: {
            title: "Explicatie",
            node: mentorNodes.mistake,
            fallback: "Explicatia apare dupa o rulare a codului.",
        },
        hint1: {
            title: "Hint 1",
            node: mentorNodes.hint1,
            fallback: "Hint-ul de nivel 1 apare dupa evaluare.",
        },
        hint2: {
            title: "Hint 2",
            node: mentorNodes.hint2,
            fallback: "Hint-ul de nivel 2 apare dupa evaluare.",
        },
        focus: {
            title: "Concept focus",
            node: mentorNodes.focus,
            fallback: "Conceptul vizat apare dupa rulare.",
        },
        encourage: {
            title: "Incurajare",
            node: mentorNodes.encourage,
            fallback: "RoboMentor iti trimite incurajare dupa rulare.",
        },
        solution: {
            title: "Solutie exemplu",
            node: mentorNodes.solution,
            fallback: "Bifeaza \"Vreau si un exemplu de solutie\", apoi ruleaza codul.",
        },
    };

    const playback = {
        trace: [],
        index: -1,
        timer: null,
        robot: null,
    };

    const getCsrfToken = () => {
        const raw = document.cookie || "";
        for (const part of raw.split(";")) {
            const item = part.trim();
            if (item.startsWith("csrftoken=")) {
                return decodeURIComponent(item.slice("csrftoken=".length));
            }
        }
        return "";
    };

    const findStart = () => {
        for (let r = 0; r < grid.length; r += 1) {
            const row = grid[r];
            for (let c = 0; c < row.length; c += 1) {
                if (row[c] === "S") {
                    return { r, c };
                }
            }
        }
        return { r: 0, c: 0 };
    };

    const startPos = findStart();
    const dirGlyph = {
        N: "↑",
        E: "→",
        S: "↓",
        W: "←",
    };

    const robotFromTrace = (traceEntry) => {
        if (!traceEntry || !Array.isArray(traceEntry.position)) {
            return null;
        }
        return {
            r: Number(traceEntry.position[0]) || 0,
            c: Number(traceEntry.position[1]) || 0,
            dir: String(traceEntry.dir || "E").toUpperCase(),
        };
    };

    const normalizeTile = (tile) => {
        if (!tile || tile === "S") {
            return ".";
        }
        return tile;
    };

    const pickSprite = (pool, r, c) => {
        if (!pool.length) {
            return "";
        }
        const index = Math.abs((r * 37 + c * 17 + r * c) % pool.length);
        return pool[index];
    };

    const tileOverlay = (tile) => {
        if (tile === "G") return "G";
        if (tile === "T") return "T";
        if (tile === "B") return "B";
        if (tile === "K") return "K";
        if (tile === "H") return "H";
        if (tile === "D") return "D";
        return "";
    };

    const renderGrid = () => {
        if (!gridNode) {
            return;
        }
        gridNode.innerHTML = "";
        gridNode.style.gridTemplateColumns = `repeat(${Math.max(1, maxCols)}, minmax(24px, 1fr))`;

        for (let r = 0; r < grid.length; r += 1) {
            const row = grid[r];
            for (let c = 0; c < maxCols; c += 1) {
                const cell = document.createElement("div");
                cell.className = "robotlab-cell";
                const tile = normalizeTile(row[c] || "#");
                let sprite = "";
                if (tile === "#") {
                    cell.classList.add("is-wall");
                    sprite = pickSprite(wallSprites, r, c);
                } else if (tile === "G") {
                    cell.classList.add("is-goal");
                    sprite = pickSprite(tileSprites, r, c);
                } else if (tile === "T") {
                    cell.classList.add("is-terminal");
                    sprite = pickSprite(tileSprites, r, c);
                } else if (tile === "B" || tile === "K") {
                    cell.classList.add("is-item");
                    sprite = pickSprite(tileSprites, r, c);
                } else if (tile === "H") {
                    cell.classList.add("is-hazard");
                    sprite = pickSprite(tileSprites, r, c);
                } else if (tile === "D") {
                    sprite = pickSprite(tileSprites, r, c);
                } else {
                    sprite = pickSprite(tileSprites, r, c);
                }
                if (sprite) {
                    cell.style.setProperty("--robotlab-cell-sprite", `url("${sprite}")`);
                }
                cell.textContent = tileOverlay(tile);

                if (playback.robot && playback.robot.r === r && playback.robot.c === c) {
                    cell.classList.add("has-robot");
                    cell.textContent = dirGlyph[playback.robot.dir] || "R";
                }
                gridNode.appendChild(cell);
            }
        }
    };

    const stopPlayback = () => {
        if (playback.timer) {
            window.clearInterval(playback.timer);
            playback.timer = null;
        }
    };

    const setStatus = (text) => {
        if (statusNode) {
            statusNode.textContent = text;
        }
    };

    const readMentorValue = (type) => {
        const config = HINT_CONFIG[type];
        if (!config) {
            return "Hint indisponibil.";
        }
        const value = config.node?.textContent?.trim() || "";
        if (value && value !== "-") {
            return value;
        }
        return config.fallback;
    };

    const updateSolutionHintButton = () => {
        const solutionButton = hintButtons.find((button) => button.dataset.hintType === "solution");
        if (!solutionButton) {
            return;
        }
        const hasSolution = Boolean(mentorNodes.solution?.textContent?.trim());
        solutionButton.disabled = !hasSolution;
        solutionButton.setAttribute("aria-disabled", String(!hasSolution));
    };

    const closeHintModal = () => {
        if (!hintModal || hintModal.hasAttribute("hidden")) {
            return;
        }
        hintModal.setAttribute("hidden", "");
        document.body.classList.remove("robotlab-modal-open");
    };

    const openHintModal = (type) => {
        const config = HINT_CONFIG[type];
        if (!config || !hintModal || !hintModalTitle || !hintModalContent) {
            return;
        }
        hintModalTitle.textContent = config.title;
        hintModalContent.textContent = readMentorValue(type);
        hintModal.removeAttribute("hidden");
        document.body.classList.add("robotlab-modal-open");
    };

    const renderTrace = () => {
        if (!traceList) {
            return;
        }
        traceList.innerHTML = "";
        if (!playback.trace.length) {
            const item = document.createElement("li");
            item.textContent = "Ruleaza codul ca sa vezi trace-ul.";
            traceList.appendChild(item);
            return;
        }
        playback.trace.forEach((entry) => {
            const li = document.createElement("li");
            const step = Number(entry.step || 0);
            const action = entry.action ? `action=${entry.action}` : "";
            const error = entry.error ? `error=${entry.error}` : "";
            const where = Array.isArray(entry.position)
                ? `pos=[${entry.position[0]},${entry.position[1]}]`
                : "";
            li.textContent = [`#${step}`, action, error, where].filter(Boolean).join(" · ");
            traceList.appendChild(li);
        });
    };

    const applyTraceIndex = (index) => {
        if (!playback.trace.length) {
            playback.robot = { r: startPos.r, c: startPos.c, dir: "E" };
            renderGrid();
            return;
        }
        const safeIndex = Math.max(-1, Math.min(index, playback.trace.length - 1));
        playback.index = safeIndex;
        if (safeIndex < 0) {
            playback.robot = { r: startPos.r, c: startPos.c, dir: "E" };
            renderGrid();
            return;
        }
        const robot = robotFromTrace(playback.trace[safeIndex]);
        playback.robot = robot || playback.robot || { r: startPos.r, c: startPos.c, dir: "E" };
        renderGrid();
    };

    const resetPlayback = () => {
        stopPlayback();
        playback.trace = [];
        playback.index = -1;
        playback.robot = { r: startPos.r, c: startPos.c, dir: "E" };
        renderGrid();
        renderTrace();
    };

    const setMentor = (mentor) => {
        if (!mentor || typeof mentor !== "object") {
            return;
        }
        if (mentorNodes.what) mentorNodes.what.textContent = mentor.what_happened || "-";
        if (mentorNodes.mistake) mentorNodes.mistake.textContent = mentor.mistake_explanation || "-";
        if (mentorNodes.hint1) mentorNodes.hint1.textContent = mentor.hint_level_1 || "-";
        if (mentorNodes.hint2) mentorNodes.hint2.textContent = mentor.hint_level_2 || "-";
        if (mentorNodes.focus) mentorNodes.focus.textContent = mentor.concept_focus || "-";
        if (mentorNodes.encourage) mentorNodes.encourage.textContent = mentor.encouragement || "-";
        if (mentor.example_solution) {
            if (mentorNodes.solutionWrap) mentorNodes.solutionWrap.hidden = false;
            if (mentorNodes.solution) mentorNodes.solution.textContent = mentor.example_solution;
        } else {
            if (mentorNodes.solutionWrap) mentorNodes.solutionWrap.hidden = true;
            if (mentorNodes.solution) mentorNodes.solution.textContent = "";
        }
        updateSolutionHintButton();
    };

    const runCode = async () => {
        if (!runUrl || !levelId || !codeInput) {
            return;
        }
        stopPlayback();
        setStatus("Rulez misiunea...");
        if (runBtn) {
            runBtn.setAttribute("disabled", "disabled");
        }
        try {
            const response = await fetch(runUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify({
                    level_id: levelId,
                    student_code: codeInput.value || "",
                    student_requested_solution: Boolean(requestSolution?.checked),
                }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || data.detail || "Run failed");
            }
            playback.trace = Array.isArray(data.execution_trace) ? data.execution_trace : [];
            playback.index = -1;
            renderTrace();
            applyTraceIndex(playback.trace.length ? 0 : -1);
            setMentor(data.mentor || {});

            const solved = Boolean(data.solved);
            const steps = Number(data.steps_used || 0);
            const xp = Number(data.xp_granted || 0);
            setStatus(
                solved
                    ? `Misiune finalizata in ${steps} pasi. XP +${xp}.`
                    : `Misiunea nu este completa. Verifica hint-urile RoboMentor.`
            );
        } catch (error) {
            setStatus(`Eroare: ${error.message}`);
        } finally {
            if (runBtn) {
                runBtn.removeAttribute("disabled");
            }
        }
    };

    root.querySelector("[data-playback-step]")?.addEventListener("click", () => {
        if (!playback.trace.length) {
            return;
        }
        const next = playback.index + 1;
        applyTraceIndex(next >= playback.trace.length ? playback.trace.length - 1 : next);
    });

    root.querySelector("[data-playback-play]")?.addEventListener("click", () => {
        if (!playback.trace.length || playback.timer) {
            return;
        }
        playback.timer = window.setInterval(() => {
            if (playback.index >= playback.trace.length - 1) {
                stopPlayback();
                return;
            }
            applyTraceIndex(playback.index + 1);
        }, 550);
    });

    root.querySelector("[data-playback-pause]")?.addEventListener("click", () => {
        stopPlayback();
    });

    root.querySelector("[data-playback-reset]")?.addEventListener("click", () => {
        applyTraceIndex(-1);
    });

    hintButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const type = button.dataset.hintType;
            if (!type) {
                return;
            }
            openHintModal(type);
        });
    });

    hintCloseButtons.forEach((button) => {
        button.addEventListener("click", () => {
            closeHintModal();
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeHintModal();
        }
    });

    runBtn?.addEventListener("click", () => {
        runCode();
    });

    resetCodeBtn?.addEventListener("click", () => {
        if (!codeInput) {
            return;
        }
        codeInput.value = starterCode;
        setStatus("Cod resetat.");
    });

    if (codeInput && !codeInput.value.trim()) {
        codeInput.value = starterCode;
    }
    resetPlayback();
    updateSolutionHintButton();
})();
