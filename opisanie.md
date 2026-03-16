# Ecosystem — подробное описание функций платформы

## Общая картина
- Django 4.0.7 + Python 3.8, DRF для API, Celery/Redis используются при наличии, SQLite в dev (PostgreSQL в проде).
- Роли: студент, преподаватель, админ, родитель; `dashboard_router` отправляет в соответствующий кабинет.
- Основные домены: уроки/курсы, тесты и диагностики, адаптивные рекомендации, кодовые упражнения, классы и задания, проекты с рубриками, сообщество, геймификация, уведомления и глубокая аналитика.

## Учебный контент и структура данных
- Иерархия: `Subject` → `Course` (уровни beginner/intermediate/advanced, цели `CourseGoal`) → `Module` (порядок) → `Lesson`.
- `Lesson`: тип (standard/interactive/project/quiz), возрастные диапазоны, длительность, сложность, XP-награда (0–500, дефолт 50), краткое описание/теория/промпты для обсуждений, сюжетный якорь, домашнее расширение, режим работы (solo/pairs/small_group/whole_class), треки контента, эмодзи/тема героя, флаг featured и fun_fact. Автогенерирует slug, дефолтные промпты, треки, режим коллаборации, базовые навыки (`Skill`), цели урока (`LessonObjective`), рефлексивные вопросы (`LessonReflectionPrompt`) и сегменты медиа.
- Связанные сущности урока:
  - `LessonPrerequisite` — последовательности внутри предмета.
  - `LessonMedia` + `LessonMediaSegment` — видео/аудио/слайды, нарезка на сегменты; сервис `LessonMediaService` строит embed-ссылки (YouTube/Vimeo) и трекает прогресс (`VideoProgress`, закрытие при ≥80%).
  - `LessonResource` — материалы (article/video/worksheet/interactive) с порядком.
  - `LessonModule` + `ModuleProgress` — микро-блоки (concept/example/practice/quiz) с зависимостями.
  - `LessonSection` + `SectionProgress` — последовательные секции урока с условиями открытия, мини-викторинами и замером времени.
  - `LessonPractice` — драг-н-дроп/парные задания (`data.draggables/targets`), `has_pairs` для шаблонов.
  - `LessonHint` — многоуровневые подсказки с задержками, `LessonEasterEgg` (XP/баджи/разблокировки по условию).
  - `LessonDownload` — офлайн-кэш (контент, ссылки на медиа, срок годности, размер файла); `OfflineProgressQueue` копит несинхронизированный прогресс.
  - Коммуникации: `LessonComment` (+лайки `CommentLike`, счётчики/модерация), `LessonRating` (1–5 + отзыв), `LessonFeedback` (детализированные оценки качества контента/сложности/примеров, рекомендации, время прохождения).
  - Аналитика: `LessonAnalytics` хранит просмотры, уникальные, завершения, время (avg/median), оценки, completion rate, drop-off, ошибки, рейтинг, соц.метрики.
- `TopicTag` и `Skill` — таксономия тем и навыков; уроки могут быть привязаны к нескольким темам/скиллам.

## Прогресс, планы и персонализация
- `LessonProgress` фиксирует завершение, быстрейшее время, очки, дату; метод `mark_completed` начисляет XP (из поля урока) и обновляет streak.
- `LearningPlan` (7/14/30 дней, статус active/completed/cancelled) + `LearningPlanItem` (pending/done/skipped, дедлайн/порядок) — расписанные планы.
- `LearningPath` + `LearningPathLesson` — рекомендованные дорожки с темой/аудиторией/сложностью; `LearningRecommendation` — записи «что пройти и почему» (score, reason, consumed).
- Дополнительный прогресс: `VideoProgress`, `ModuleProgress`, `SectionProgress`; `LessonStreak` по предметам; `LessonDownload` и `OfflineProgressQueue` для PWA/оффлайна.
- Персонализация: `LessonPersonalization` (показывать подсказки/доп.примеры, сложность контента, темп, предпочитаемый медиа-формат, факт.время).

## Диагностика и адаптивность
- `DiagnosticTest`/`DiagnosticAttempt` — входные тесты с рекомендацией курса/модуля/уровня.
- `AdaptiveLearningEngine`:
  - `get_next_lesson_recommendation` — подбирает урок по успешности (≥85% advanced, ≥65% intermediate, иначе beginner, исключая завершённые).
  - `should_skip_basics` — если по базовым урокам ≥80% правильных, можно пропустить beginner.
  - `generate_personalized_content` — флаги доп.примеров/продвинутых тем/темпа + доп.практика на слабые темы.
  - `update_personalization`, `get_learning_path_recommendation`.
- `learning_paths` сервис:
  - `build_learning_path` — создаёт `LearningPlan` и равномерно раскладывает уроки по дням.
  - `detect_weak_topics` — по попыткам тестов и `TopicTag` (<70% при min_attempts) формирует список слабых тем.
  - `generate_micro_remediation_tasks` — микрозадания по слабым темам (пересмотреть конспект, повторить вопрос, объяснить коллеге).

## Оценивание и тесты
- `Test` (вопрос, правильный/неправильные ответы, лимит времени, бонусный порог, очки, пояснение, связка с уроком/сложностью).
- `process_test_attempt` (service `assessment`): лимит 3 попытки/час + 60 сек кулдаун, проверка тайм-аута, расчёт бонуса по времени, запись `TestAttempt`, подозрения при слишком быстрых промахах → `EventLog`. При правильном ответе — XP/завершение урока через `record_lesson_completion`.
- Расширенная аналитика `assessment_enhanced`:
  - `get_student_performance_analytics` — попытки, %успеха, среднее время, разрез по сложностям, топ слабых уроков (успех <60% при ≥3 попытках), прогресс за 7 дней, бонусы.
  - `get_adaptive_difficulty_recommendation` — повысить/понизить сложность урока по успеху (≥90% вверх, <50% вниз).
  - `get_test_insights` — попытки, %успеха, среднее время, топ ошибок, оценка сложности, счётчик бонусов.
  - `generate_personalized_practice_plan` — план на N дней: сначала слабые темы, затем новые незавершённые.
  - `compare_students`, `get_learning_velocity` (уроков/неделю, тренд), `get_question_bank`, `sample_questions_for_lesson`.

## Кодовые упражнения
- `CodeExercise`/`CodeSubmission`: языки python/js/html/sql, тесткейсы JSON, стартер-код, подсказки, сложность и очки. `CodeSubmission` хранит вывод/ошибку/время, индексируется по пользователю и упражнению.
- `CodeRunner.run_python_code` — запускает код через `subprocess` без песочницы (dev), таймаут 5с, сравнение stdout с expected; возвращает `CodeRunResult`. **Не безопасно для продакшена без контейнеризации.**
- `code_similarity` — токенизация + `SequenceMatcher`, `is_suspicious_similarity` (по умолчанию порог 80%).
- `smart_hints.SmartHintSystem` — контекстные подсказки по секции/времени, AI-хинты по ошибкам (SyntaxError/NameError/TypeError/и т.д.), рекомендации похожих уроков.

## Геймификация и вознаграждения
- Профиль (`UserProfile`): роль, XP/level/streak, любимый предмет, weekly_goal, цели обучения (skills/grades/career/fun), тема/маскот, родительский email, локаль, флаги онбординга. `add_xp` повышает уровень (формула `100 + level^2 * 25`, прогресс к следующему уровню), логирует `ExperienceLog` и отправляет уведомление.
- Награды:
  - `Badge` + `UserBadge`, `check_and_award_rewards` (пороги 3/5/10/20 уроков, XP, уведомление, `Reward/UserReward` при ≥10 уроках).
  - `AchievementEngine` правила: speed_demon (10 бонусов), week_warrior (7-дневный стрик), month_master (30), century_club (100 уроков), subject_explorer (5 предметов), helpful_hero (50 комментариев), perfectionist (20 правильных подряд), night_owl/early_bird (10 ночных/утренних).
  - `LessonChallenge` (speed/accuracy/creativity/combo, целевое время/точность, награда XP/бадж), `LessonEasterEgg`, `AvatarUnlock`.
- Миссии/челленджи:
  - `Mission`/`UserMission` (daily/weekly/once, target_value, reward_points/badge). `gamification.ensure_default_missions` создаёт базовые (дневной урок, 3 квиза/неделю, загрузка проекта), `register_progress` сбрасывает по частоте.
  - `DailyChallenge` и `ChallengeManager` (создание недельного челленджа, прогресс, выдача наград, активные челленджи).
  - Лидеры: `LeaderboardManager` (глобальный/классовый, период all_time/week/month, ранги по XP/завершениям), `LeaderboardSnapshot`.
- Сервис `gamification.record_lesson_completion` — помечает прогресс, триггерит награды/миссии, возвращает общий прогресс; `build_overall_progress` кэширует процент/кол-во уроков; `get_badge_summary` и `get_mission_context`.

## Классы, задания и родители
- `Classroom` (owner, invite_code авто, team_support/archived), `ClassroomMembership` (student/assistant/parent, approved, группа, баллы, последняя активность).
- Задания: `ClassAssignment` (due_date, points, автор), `AssignmentSubmission` (draft/submitted/returned/graded, оценка/фидбек, уникально на студента).
- Родители: `ParentChildLink` (approve/requested_at) для просмотра прогресса.
- Представления: кабинет класса (создание/вступление по коду), деталь класса (список учеников/заданий), лидерборд по классу (фильтр).

## Проекты и оценивание
- `Project` (slug, уровень, статус draft/active/retired, связка с `Rubric`), `ProjectSubmission` (статус submitted/returned/accepted, попытка, чек-лист, балл, файл), `PeerReview` (отзыв/оценка от сверстников).
- `Rubric`/`RubricCriterion` — критерии с весом/макс.баллом/порядком.
- `ProjectEvaluation` + сервис `project_evaluation.evaluate_submission` — пересчитывает нормализованный балл по весам, выставляет статус returned, сохраняет оценку/комментарий.

## Сообщество и обратная связь
- Форум: `CommunityThread` и `CommunityReply` (представления создают темы/ответы, отправляют уведомления автору).
- Комментарии к урокам: API + модерация (`moderate_comments` для преподавателя: approve/hide/delete). Подсчёт лайков/ответов, флаги is_approved/is_hidden.
- Рейтинги/фидбек: `LessonRating` (CRUD через API), `LessonFeedback` для подробных опросов качества.

## Уведомления и коммуникации
- Модель: `Notification` (категории progress/feedback/system/community, link_url, read_at) + `NotificationPreference` (email/in-app, digest daily/weekly/never, quiet hours поддерживаются в enhanced-сервисе).
- Сервис `notifications` — отправка ин-аппов и рассылки по событиям (новый урок, комментарий, рейтинг, ответ, общий фидбек).
- Расширенный сервис `notifications_enhanced`:
  - Шаблоны (`NotificationTemplate`): streak_milestone, level_up, assignment_due_soon, new_comment, project_reviewed, badge_earned, daily_reminder, weekly_summary, teacher_feedback, parent_report.
  - Массовая рассылка `send_bulk_notification`; дайджесты `get_notification_digest` (daily/weekly/monthly) и `build_weekly_digest`; подавление по «тихим часам» `enforce_quiet_hours`/`send_with_quiet_hours`.
  - Статистика `get_notification_stats`, пометка прочитанного `mark_all_as_read`, очистка старых `delete_old_notifications`.
  - Напоминания: `send_streak_reminder` (20–24ч без активности при стрике), `schedule_assignment_reminders` (дедлайн завтра), `notify_parent_about_child_progress`.
- Представление `/notifications/` — центр уведомлений + изменение предпочтений.

## Аналитика и отчётность
- `LessonAnalyticsService`:
  - `update_lesson_analytics` — суточные метрики (просмотры/уники/завершения, avg/median time, avg_score, completion rate, комменты/рейтинги, заглушки drop-off/error/load time).
  - `get_lesson_overview_stats` — агрегаты по всем урокам за 7 дней, средний рейтинг/комментарии.
  - `get_top_performing_lessons` — топ по completion_rate, просмотрам, среднему рейтингу.
  - `get_lesson_engagement_trends` — временные ряды за N дней.
- `analytics_summary`:
  - `get_student_analytics` (completion rate, avg speed, streak, avg score, mastery по `TopicTag`).
  - `detect_student_risk` (completion<50, avg_score<60, нет стрика).
  - `get_teacher_class_overview` (через LessonAnalytics или по ClassroomMembership) и `get_product_metrics` (DAU/WAU/MAU, retention 7/30, avg session time).
- `teacher_analytics`: обзоры класса (активность/успеваемость/сдача), отчёт по студенту (прогресс, тесты, задания, активность), аналитика задания (проценты сдачи/распределение оценок/статусы/кто не сдал), список отстающих (threshold, неактивность, мало уроков), анализ сложности урока (реальная vs заявленная, рекомендации).
- `admin_analytics`: глобальные метрики пользователей/контента/успеваемости и рост (новые пользователи/завершения, дневные срезы).
- Дашборд студента собирает `build_student_dashboard` (прогресс, бейджи, миссии, рекомендации, последние проекты, активные челленджи, нотификации, снэпшот лидерборда).

## AI и подсказки
- `ai.generate_hint`: лимит по умолчанию 20 запросов/час на пользователя (настраивается `ESTUDY_AI_HINT_LIMIT_PER_HOUR`), строит ответ по ключевым словам + подсказкам из урока/практики/теории, логирует `AIHintRequest` и `EventLog`. Представление `/lessons/<slug>/ai-hint/` возвращает ответ JSON.
- `SmartHintSystem` — контекстные подсказки по секции/времени/числу попыток, AI-хинт по ошибке кода, рекомендации связанных уроков.
- `LessonHint`/`AIHintRequest` модели позволяют хранить и отслеживать выдачу подсказок.

## API, маршруты и интеграции
- Основные view-роуты: дашборды по ролям, список уроков с фильтрами/блоками/рекомендациями, деталь урока (с проверкой prereq и обогащениями), переключение завершения `/lessons/<slug>/toggle/`, отправка теста `/tests/<id>/submit/`, миссии/лидерборд/уведомления, классы (список/деталь), проекты (список/submit), сообщество (форум), обзор `/overview/`, прогресс `/progress/`, кодовый плейграунд и API `/api/run-code/`, модерация комментариев.
- DRF endpoints (`/api/` и `/api/v1/`): список/создание комментариев урока, CRUD по комменту, список/создание ответов, like/unlike, создание/CRUD рейтинга урока, статистика урока, аналитика урока (доступно учителям/админам), список прогресса уроков пользователя. Авторизация токеном `/api/token/`.
- OpenAPI спецификация: `docs/openapi.yaml`.

## Фоновые задачи
- `tasks.py` (Celery-friendly, fallback-декоратор если Celery не установлен):
  - `send_daily_digests`, `send_weekly_digests` — создание дайджестов по предпочтениям.
  - `recalc_lesson_analytics` — пересчёт аналитики по всем урокам.
  - `check_achievements` — массовая выдача достижений.
  - `cleanup_notifications` — удаление старых прочитанных (по умолчанию 30 дней).

## Оффлайн и PWA
- `estudy/static/manifest.webmanifest` и `service-worker.js` плюс модели `LessonDownload`/`OfflineProgressQueue` обеспечивают работу в режиме PWA и синхронизацию прогресса после возврата в сеть.

## Маркетинг и аутентификация
- Приложение `unitexapp`: лендинг (`index`), формы связи (`submit_form` валидирует имя/телефон, отправляет письмо через `send_mail`, работает и для AJAX, и для обычных POST).
- Приложение `inregistrare`: регистрация/логин/логаут с безопасным `next`, профиль (`Profile` с bio/email/name/phone), редактирование профиля; шаблоны аккаунтов в `inregistrare/templates`.

## Утилиты и прочие сервисы
- `audit_logger`/`audit_trail` — логирование событий (`EventLog` типы login/lesson_view/test_start/test_submit/achievement_awarded), фильтрация по пользователям/диапазону/типам, выборка свежих просмотров урока.
- `caching.cached_get` и `invalidate_prefix` — простые обёртки над Django cache.
- `toggles.toggle_lesson_completion_service` — единообразное переключение завершения (с учётом XP/миссий).
- `lesson_quality.LessonQualityAnalyzer` — интегральный скор качества, рекомендации по улучшениям, среднее время завершения, метрики вовлечённости.
- `lesson_media.LessonMediaService` — валидация/парсинг видео-URL, трекинг прогресса.
- `onboarding` — выбор цели, назначение миссий, создание плана на 7 дней, подбор диагностического теста, отметка завершения онбординга.
- Примеры использования новых сервисов — `USAGE_EXAMPLES.py`.

Платформа готова для расширения AI-агентом: ключевые сервисы и модели разбиты на небольшие функции, метрики и уведомления централизованы, есть API-слой и заготовки фоновых задач.
