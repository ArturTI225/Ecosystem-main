# 🎓 Ecosystem — AI-First Educational Platform

> Production-ready educational ecosystem with adaptive learning, gamification, analytics and AI assistance.

---

## 📌 Purpose of This Repository

This repository represents **Ecosystem**, a modular, scalable educational platform designed for:
- students
- teachers
- parents
- administrators

The system is **AI-first**, **event-driven**, and **analytics-heavy**, built to support adaptive learning, project-based assessment, and safe AI assistance.

This README is the **single source of truth** for:
- architecture rules
- extension checklist
- AI-agent behavior constraints

---

## 🧱 Tech Stack

- **Backend**: Django 4.0.7, Python 3.8
- **API**: Django REST Framework
- **Async**: Celery + Redis (optional fallback supported)
- **DB**: SQLite (dev), PostgreSQL (production)
- **Auth**: Token-based
- **PWA**: Service Worker + Offline Sync
- **AI**: External LLM via internal AI service layer

---

## 👥 User Roles

| Role | Capabilities |
|----|----|
| Student | Lessons, tests, projects, AI hints |
| Teacher | Classes, assignments, analytics, moderation |
| Parent | Read-only child progress |
| Admin | Global analytics, content & user control |

Routing handled by `dashboard_router`.

---

## 🧠 Core Domains

- Lessons & Courses
- Adaptive Learning & Diagnostics
- Tests & Assessments
- Code Exercises
- Projects & Rubrics
- Gamification & Rewards
- Community & Feedback
- Notifications
- Analytics & BI
- AI Assistance

---

## ✅ MASTER CHECKLIST — PLATFORM EXTENSION

### 1️⃣ Architecture & Technical Debt

- [ ] PostgreSQL migration (JSONB for analytics)
- [ ] Strict service layer (no business logic in views/models)
- [ ] Domain Events (LessonCompleted, XPGranted, TestFailed)
- [x] Idempotency keys for critical endpoints
- [x] BaseServiceResult abstraction
- [x] Profiling tools (dev only)

---

### 2️⃣ Security (CRITICAL)

#### Code Execution
- [x] ❌ No subprocess execution in production
- [ ] Docker / gVisor sandbox
- [ ] CPU ≤ 1 core, RAM ≤ 256MB
- [ ] No network access
- [ ] Read-only filesystem
- [ ] Execution timeout ≤ 3 seconds

#### Platform
- [x] Global rate limiting
- [x] Anti-cheat detection
- [x] Immutable audit trail
- [x] Role-based permission matrix

---

### 3️⃣ AI Core Expansion

- [ ] AI Orchestrator with `AIRequestContext`
- [ ] AIResponsePolicy (verbosity, limits, refusal rules)
- [x] Explain mistakes (tests & code)
- [x] Socratic follow-ups
- [x] Personalized practice generation
- [x] Teacher insights summaries
- [x] Parent progress summaries
- [x] AI cost tracking
- [x] Hallucination guards

---

### 4️⃣ Adaptive Learning 2.0

- [ ] Skill → Subskill → Prerequisite graph
- [ ] Mastery model with decay
- [ ] Section-level adaptive difficulty
- [ ] Dynamic lesson length

---

### 5️⃣ Content Quality

- [ ] Lesson versioning
- [ ] A/B testing
- [x] Automatic difficulty mismatch detection
- [x] Lesson Health Score

---

### 6️⃣ Projects & Peer Review

- [ ] Anonymous peer reviews
- [ ] AI-assisted rubric feedback
- [ ] Conflict resolution flow
- [ ] Plagiarism detection
- [ ] Portfolio export

---

### 7️⃣ Community

- [x] Reputation system
- [x] Trusted contributor roles
- [x] Toxicity auto-moderation
- [x] Teacher-curated answers

---

### 8️⃣ Gamification (Advanced)

- [x] Seasonal events
- [x] Skill-based leaderboards
- [x] XP decay (optional)
- [x] Cosmetic avatar perks
- [x] Streak freeze tokens

---

### 9️⃣ Analytics & BI

- [x] Funnel analytics
- [x] Cohort analysis
- [x] Predictive risk scoring
- [x] Teacher early-warning alerts
- [x] CSV / BigQuery export

---

### 🔟 PWA / Offline

- [ ] Offline test queue
- [x] Conflict resolution policy
- [ ] Sync retry with backoff
- [ ] Visual offline indicators

---

### 1️⃣1️⃣ DevOps & DX

- [x] Feature flags
- [x] Seed demo data
- [x] OpenAPI auto sync
- [ ] CI: tests, lint, security scan
- [ ] Rollback-safe migrations

---

## 🤖 AI CODEX AGENT — STRICT RULES

### 🔒 General

1. ❌ NEVER put business logic in views or models  
2. ✅ ALL logic lives in services  
3. ❌ No logic duplication  
4. ✅ One service = one responsibility  

---

### 🧱 Architecture

- Services must be:
  - stateless
  - testable
  - explicit
- Side-effects only via:
  - events
  - dedicated services

---

### 🤖 AI Behavior

- AI NEVER:
  - solves tasks
  - gives full answers
  - outputs final code
- AI ONLY:
  - explains
  - hints
  - asks guiding questions
- Every AI response:
  - grounded in lesson/skill
  - logged
  - token-limited

---

### 🔐 Security

- All user input is hostile
- Code execution only in sandbox
- Limits enforced server-side

---

### 📊 Analytics

- Every action → EventLog
- No hidden calculations
- Metrics computed async & idempotent

---

### 🧪 Testing

- New service → tests
- New logic → tests
- Edge cases mandatory

---

### 🧭 Decision Priority

1. Security  
2. Clarity  
3. Scalability  
4. Performance  
5. Code aesthetics  

---

### 🧩 Style Rules

- No magic numbers
- No hidden conditions
- Comments explain **why**, not **what**
- Naming must be self-describing

---

## 🧠 Final Note

This platform is intentionally designed for:
- AI extensibility
- Safe learning assistance
- Data-driven decisions
- Long-term scalability

Any contribution **must follow this README**.

---

© Ecosystem Platform
