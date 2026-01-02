# 🏗️ Архитектура платформы Ecosystem

## 📐 Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                     ECOSYSTEM PLATFORM                          │
│                 Образовательная платформа                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        СЛОЙ ПОЛЬЗОВАТЕЛЕЙ                        │
├─────────────────────────────────────────────────────────────────┤
│  👨‍🎓 Студент  │  👨‍🏫 Учитель  │  👨‍👩‍👧 Родитель  │  👨‍💼 Админ  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    СЛОЙ ПРЕДСТАВЛЕНИЙ (Views)                    │
├─────────────────────────────────────────────────────────────────┤
│  Dashboard  │  Lessons  │  Classroom  │  Analytics  │  Profile  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    СЛОЙ БИЗНЕС-ЛОГИКИ (Services)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │   Assessment     │  │  Notifications   │                    │
│  │   - Analytics    │  │  - Templates     │                    │
│  │   - Adaptive     │  │  - Digests       │                    │
│  │   - Plans        │  │  - Reminders     │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  Achievements    │  │  Teacher Tools   │                    │
│  │  - Badges        │  │  - Class Stats   │                    │
│  │  - Challenges    │  │  - Reports       │                    │
│  │  - Leaderboard   │  │  - Insights      │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  Gamification    │  │   AI Assistant   │                    │
│  │  - XP/Levels     │  │  - Hints         │                    │
│  │  - Missions      │  │  - Explanations  │                    │
│  │  - Rewards       │  │  - Keywords      │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      СЛОЙ МОДЕЛЕЙ (Models)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Обучение:           Геймификация:        Классы:              │
│  • Lesson            • Badge              • Classroom           │
│  • Test              • Mission            • Assignment          │
│  • Practice          • UserBadge          • Submission          │
│  • LessonProgress    • Reward             • Membership          │
│                                                                  │
│  Пользователи:       Социальное:         Система:              │
│  • UserProfile       • CommunityThread    • Notification        │
│  • ExperienceLog     • CommunityReply     • AIHintRequest       │
│  • ParentChildLink   • Project            • DailyChallenge      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    СЛОЙ ДАННЫХ (Database)                        │
├─────────────────────────────────────────────────────────────────┤
│              SQLite (dev) / PostgreSQL (prod)                    │
│                    + Redis (кеширование)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Поток данных

### 1. Студент завершает урок

```
Студент → View (lesson_detail) → Service (assessment) → Model (LessonProgress)
    ↓
Service (gamification) → Model (UserProfile) → +XP
    ↓
Service (achievements) → Model (Badge) → Проверка условий
    ↓
Service (notifications) → Model (Notification) → Уведомление
```

### 2. Учитель проверяет класс

```
Учитель → View (classroom_analytics) → Service (teacher_analytics)
    ↓
Models (Classroom, LessonProgress, TestAttempt) → Агрегация данных
    ↓
Service → Вычисление метрик → View → Шаблон → Отображение
```

### 3. Система проверяет достижения

```
Celery Task (periodic) → Service (achievements.AchievementEngine)
    ↓
For each User → check_and_award()
    ↓
Models (TestAttempt, LessonProgress) → Проверка условий
    ↓
Model (UserBadge) → Создание значка
    ↓
Service (notifications) → Уведомление пользователя
```

---

## 🎯 Новые модули в архитектуре

### Assessment Enhanced
```
┌────────────────────────────────────────┐
│    assessment_enhanced.py              │
├────────────────────────────────────────┤
│  get_student_performance_analytics()   │
│  ├─ TestAttempt (aggregate)            │
│  ├─ LessonProgress (filter)            │
│  └─ Analytics Dict                     │
│                                        │
│  get_adaptive_difficulty()             │
│  ├─ TestAttempt (analyze)              │
│  └─ Recommended Difficulty             │
│                                        │
│  generate_practice_plan()              │
│  ├─ Weak topics                        │
│  ├─ Incomplete lessons                 │
│  └─ 7-day Plan                         │
└────────────────────────────────────────┘
```

### Notifications Enhanced
```
┌────────────────────────────────────────┐
│   notifications_enhanced.py            │
├────────────────────────────────────────┤
│  NotificationTemplate                  │
│  ├─ 10+ шаблонов                       │
│  └─ create(template, user, **kwargs)   │
│                                        │
│  send_bulk_notification()              │
│  ├─ Filter by preferences              │
│  └─ Bulk create                        │
│                                        │
│  schedule_assignment_reminders()       │
│  ├─ Find due assignments               │
│  └─ Send notifications                 │
└────────────────────────────────────────┘
```

### Achievements
```
┌────────────────────────────────────────┐
│         achievements.py                │
├────────────────────────────────────────┤
│  AchievementEngine                     │
│  ├─ 10+ правил достижений              │
│  ├─ check_and_award(user)              │
│  └─ Auto-create badges                 │
│                                        │
│  ChallengeManager                      │
│  ├─ Weekly/Daily challenges            │
│  ├─ Progress tracking                  │
│  └─ Award system                       │
│                                        │
│  LeaderboardManager                    │
│  ├─ Global/Classroom                   │
│  ├─ Period filters                     │
│  └─ Rank calculation                   │
└────────────────────────────────────────┘
```

### Teacher Analytics
```
┌────────────────────────────────────────┐
│      teacher_analytics.py              │
├────────────────────────────────────────┤
│  TeacherAnalytics                      │
│  ├─ get_classroom_overview()           │
│  ├─ get_student_detailed_report()      │
│  ├─ identify_struggling_students()     │
│  └─ get_lesson_difficulty_analysis()   │
│                                        │
│  AdminAnalytics                        │
│  ├─ get_platform_statistics()          │
│  └─ get_growth_metrics()               │
└────────────────────────────────────────┘
```

---

## 🔗 Связи между компонентами

```
┌─────────────────────────────────────────────────────────────┐
│                  ИНТЕГРАЦИОННАЯ СХЕМА                        │
└─────────────────────────────────────────────────────────────┘

Views ─────────┐
               ├──→ Assessment Enhanced ───┐
Forms ─────────┘                           │
                                           ├──→ Models (CRUD)
Signals ───────┐                           │
               ├──→ Gamification ──────────┤
Tasks ─────────┘                           │
                                           └──→ Database
Admin ─────────┐
               ├──→ Teacher Analytics ─────┐
API ───────────┘                           │
                                           ├──→ Cache (Redis)
Middleware ────┐                           │
               ├──→ Notifications ─────────┘
Decorators ────┘

Background Tasks (Celery):
├─ check_achievements_daily()
├─ send_assignment_reminders()
├─ send_streak_reminders()
└─ generate_weekly_reports()
```

---

## 📊 Диаграмма базы данных (основные связи)

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│     User     │◄────────│ UserProfile  │────────►│   Subject    │
└──────────────┘         └──────────────┘         └──────────────┘
       │                        │                        │
       │ has many               │ has many               │
       ▼                        ▼                        ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│TestAttempt   │         │ExperienceLog │         │   Lesson     │
└──────────────┘         └──────────────┘         └──────────────┘
       │                        │                        │
       │ belongs to             │                        │ has many
       ▼                        │                        ▼
┌──────────────┐                │                 ┌──────────────┐
│     Test     │                │                 │LessonProgress│
└──────────────┘                │                 └──────────────┘
       │                        │                        │
       │ belongs to             │                        │
       ▼                        │                        │
┌──────────────┐                │                        │
│   Lesson     │◄───────────────┘────────────────────────┘
└──────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│     User     │────────►│  UserBadge   │────────►│    Badge     │
└──────────────┘         └──────────────┘         └──────────────┘
       │
       │
       ▼
┌──────────────┐         ┌──────────────┐
│ UserMission  │────────►│   Mission    │
└──────────────┘         └──────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Classroom   │────────►│ Membership   │────────►│     User     │
└──────────────┘         └──────────────┘         └──────────────┘
       │
       │ has many
       ▼
┌──────────────┐         ┌──────────────┐
│ Assignment   │────────►│  Submission  │
└──────────────┘         └──────────────┘
```

---

## 🎨 UI Flow (пример)

### Дашборд студента
```
┌─────────────────────────────────────────────────────────┐
│                   Мой прогресс                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐          │
│  │ Уровень 5 │  │  500 XP   │  │ Серия 7дн │          │
│  └───────────┘  └───────────┘  └───────────┘          │
│                                                         │
│  🏆 Новые достижения:                                  │
│  ┌─────────────────────────────────────────┐           │
│  │ ⚡ Демон скорости                        │           │
│  │    Получено 10 бонусов за скорость      │           │
│  └─────────────────────────────────────────┘           │
│                                                         │
│  📊 Твоя аналитика:                                    │
│  ┌─────────────────────────────────────────┐           │
│  │ Успеваемость: 85% ▲                     │           │
│  │ Всего попыток: 42                        │           │
│  │ Прогресс за неделю: 15% ▲               │           │
│  └─────────────────────────────────────────┘           │
│                                                         │
│  💡 Слабые темы (нужно подтянуть):                    │
│  • Циклы в Python (45%)                               │
│  • Функции (52%)                                       │
│                                                         │
│  📅 Твой план на неделю:                               │
│  День 1: Практика циклов (Приоритет: высокий)         │
│  День 2: Урок по функциям (Приоритет: высокий)        │
│  День 3: Новый урок - ООП (Приоритет: средний)        │
│                                                         │
│  🏅 Твой рейтинг: #42 в мире                          │
└─────────────────────────────────────────────────────────┘
```

### Панель учителя
```
┌─────────────────────────────────────────────────────────┐
│              Аналитика класса "Python 101"              │
│                                                         │
│  📊 Обзор:                                             │
│  ┌─────────────────────────────────────────┐           │
│  │ Всего студентов: 25                     │           │
│  │ Активных за неделю: 20 (80%)            │           │
│  │ Средняя успеваемость: 75%               │           │
│  │ Заданий выдано: 5                       │           │
│  │ Средний % сдачи: 85%                    │           │
│  └─────────────────────────────────────────┘           │
│                                                         │
│  ⚠️ Студенты с трудностями (3):                       │
│  ┌─────────────────────────────────────────┐           │
│  │ 1. student1: 35% успеваемость           │           │
│  │    • Очень низкая успеваемость          │           │
│  │    • Неактивен 10 дней                  │           │
│  │                                         │           │
│  │ 2. student2: 48% успеваемость           │           │
│  │    • Низкая успеваемость                │           │
│  │    • Мало завершенных уроков            │           │
│  └─────────────────────────────────────────┘           │
│                                                         │
│  📈 Последнее задание "Домашка #5":                    │
│  • Сдали: 20/25 (80%)                                 │
│  • Средняя оценка: 78/100                             │
│  • Не сдали: student3, student4, student5             │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 Безопасность

```
┌────────────────────────────────────────┐
│      SECURITY LAYERS                   │
├────────────────────────────────────────┤
│  Authentication                        │
│  ├─ Django Auth                        │
│  ├─ @login_required                    │
│  └─ Session management                 │
│                                        │
│  Authorization                         │
│  ├─ @role_required                     │
│  ├─ Permission checks                  │
│  └─ Ownership validation               │
│                                        │
│  Data Protection                       │
│  ├─ CSRF tokens                        │
│  ├─ XSS prevention                     │
│  ├─ SQL injection (ORM)                │
│  └─ File upload validation             │
│                                        │
│  Rate Limiting                         │
│  ├─ API throttling                     │
│  └─ Login attempts                     │
└────────────────────────────────────────┘
```

---

## 🚀 Производительность

```
┌────────────────────────────────────────┐
│   PERFORMANCE OPTIMIZATIONS            │
├────────────────────────────────────────┤
│  Database                              │
│  ├─ Indexes on frequent queries        │
│  ├─ select_related / prefetch_related  │
│  └─ Connection pooling                 │
│                                        │
│  Caching                               │
│  ├─ Redis for sessions                 │
│  ├─ Query result cache                 │
│  └─ Template fragment cache            │
│                                        │
│  Background Tasks                      │
│  ├─ Celery workers                     │
│  ├─ Periodic tasks                     │
│  └─ Async processing                   │
│                                        │
│  Frontend                              │
│  ├─ Static files compression           │
│  ├─ CDN for assets                     │
│  └─ Lazy loading                       │
└────────────────────────────────────────┘
```

---

## 📱 Будущая архитектура (с API)

```
┌───────────────────────────────────────────────────────┐
│                     CLIENTS                           │
├───────────────────────────────────────────────────────┤
│  Web App  │  Mobile iOS  │  Mobile Android  │  PWA   │
└───────────────────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────┐
│                   API GATEWAY                         │
│               (Django REST Framework)                 │
├───────────────────────────────────────────────────────┤
│  /api/v1/lessons/      │  /api/v1/progress/          │
│  /api/v1/tests/        │  /api/v1/achievements/      │
│  /api/v1/classrooms/   │  /api/v1/notifications/     │
└───────────────────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────┐
│               BUSINESS LOGIC LAYER                    │
│                   (Services)                          │
└───────────────────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────┐
│                  DATA LAYER                           │
│            (Models + Database)                        │
└───────────────────────────────────────────────────────┘
```

---

**Создано:** 9 ноября 2025  
**Версия:** 1.0
