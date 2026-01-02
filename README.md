# 🎓 Ecosystem - Образовательная платформа

> Интерактивная платформа для онлайн-обучения с геймификацией, аналитикой и AI-помощником

[![Django](https://img.shields.io/badge/Django-4.0.7-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Содержание

- [О проекте](#о-проекте)
- [Возможности](#возможности)
- [Новые модули](#новые-модули)
- [Быстрый старт](#быстрый-старт)
- [Документация](#документация)
- [Технологии](#технологии)

---

## 🎯 О проекте

**Ecosystem** - это комплексная образовательная платформа, которая объединяет:

- 📚 **Обучающий контент** - уроки, тесты, практические задания
- 🎮 **Геймификацию** - XP, уровни, значки, миссии, достижения
- 👥 **Классы** - управление группами, задания, проверка работ
- 📊 **Аналитику** - детальная статистика успеваемости
- 🤖 **AI-помощник** - интеллектуальные подсказки
- 🔔 **Уведомления** - система оповещений и напоминаний

### Роли пользователей:
- **👨‍🎓 Студент** - проходит уроки, получает достижения
- **👨‍🏫 Учитель** - создает задания, анализирует прогресс
- **👨‍👩‍👧 Родитель** - отслеживает успехи ребенка
- **👨‍💼 Админ** - управляет платформой

---

## ✨ Возможности

### Для студентов:
- ✅ Интерактивные уроки с теорией и практикой
- ✅ Тесты с мгновенной проверкой
- ✅ Система XP и уровней
- ✅ Значки и достижения
- ✅ Персонализированные рекомендации
- ✅ Рейтинги и соревнования
- ✅ AI-подсказки при затруднениях
- ✅ Отслеживание прогресса

### Для учителей:
- ✅ Создание классов и заданий
- ✅ Проверка работ студентов
- ✅ Детальная аналитика класса
- ✅ Выявление отстающих
- ✅ Статистика по заданиям
- ✅ Анализ сложности уроков

### Для родителей:
- ✅ Просмотр прогресса ребенка
- ✅ Еженедельные отчеты
- ✅ Связь с учителями

---

## 🆕 Новые модули (v2.0)

### 1. **Расширенная аналитика студентов**
📊 Детальный анализ успеваемости с выявлением слабых тем

```python
from estudy.services.assessment_enhanced import get_student_performance_analytics

analytics = get_student_performance_analytics(user)
# Получите: успеваемость, слабые темы, скорость обучения
```

**Возможности:**
- Автоматическое выявление слабых тем
- Адаптивная рекомендация сложности
- Персонализированный план обучения на 7 дней
- Метрики скорости обучения

### 2. **Умная система уведомлений**
🔔 Шаблоны уведомлений и автоматические напоминания

```python
from estudy.services.notifications_enhanced import NotificationTemplate

NotificationTemplate.create('level_up', recipient=user, level=5)
```

**Возможности:**
- 10+ готовых шаблонов
- Дайджесты (дневные/недельные)
- Автоматические напоминания о дедлайнах
- Отчеты родителям

### 3. **Продвинутые достижения**
🏆 Автоматическая система достижений и челленджей

```python
from estudy.services.achievements import AchievementEngine

new_badges = AchievementEngine.check_and_award(user)
```

**Возможности:**
- 10+ типов достижений (скорость, серии, количество)
- Недельные челленджи
- Глобальные и классовые рейтинги
- Соревновательные миссии

### 4. **Аналитика для учителей**
📈 Инструменты анализа класса и студентов

```python
from estudy.services.teacher_analytics import TeacherAnalytics

overview = TeacherAnalytics.get_classroom_overview(classroom)
struggling = TeacherAnalytics.identify_struggling_students(classroom)
```

**Возможности:**
- Обзор класса с ключевыми метриками
- Детальные отчеты по студентам
- Автоматическое выявление отстающих
- Анализ реальной сложности уроков

---

## 🚀 Быстрый старт

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/your-username/ecosystem.git
cd ecosystem
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv myenv
myenv\Scripts\activate  # Windows
# source myenv/bin/activate  # Linux/Mac
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Примените миграции:**
```bash
python manage.py migrate
```

5. **Создайте суперпользователя:**
```bash
python manage.py createsuperuser
```

6. **Запустите сервер:**
```bash
python manage.py runserver
```

7. **Откройте в браузере:**
```
http://127.0.0.1:8000/
```

### Быстрый тест новых функций

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from estudy.services.assessment_enhanced import get_student_performance_analytics

user = User.objects.first()
analytics = get_student_performance_analytics(user)
print(f"Успеваемость: {analytics['success_rate']}%")
```

Подробнее: [QUICKSTART.md](QUICKSTART.md)

---

## 📚 Документация

- **[IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md)** - полный план улучшений и развития
- **[USAGE_EXAMPLES.py](USAGE_EXAMPLES.py)** - примеры использования всех функций
- **[QUICKSTART.md](QUICKSTART.md)** - руководство по быстрому старту
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - архитектура платформы
- **[CHECKLIST.md](CHECKLIST.md)** - чек-лист внедрения
- **[FINAL_REPORT.md](FINAL_REPORT.md)** - итоговый отчет

---

## 🛠 Технологии

### Backend:
- **Django 4.0.7** - web-фреймворк
- **Python 3.8+** - язык программирования
- **SQLite** (dev) / **PostgreSQL** (prod) - база данных

### Frontend:
- HTML5, CSS3, JavaScript
- Bootstrap - UI framework

### Дополнительно:
- Django Signals - для событий
- JSON Fields - для гибких данных
- Caching - для производительности

### Рекомендуется:
- **Redis** - кеширование
- **Celery** - фоновые задачи
- **Django REST Framework** - API

---

## 📊 Структура проекта

```
ecosystem/
├── estudy/                    # Основное приложение
│   ├── models.py              # Модели данных (25+ моделей)
│   ├── views.py               # Представления
│   ├── urls.py                # URL маршруты
│   ├── services/              # Бизнес-логика
│   │   ├── assessment.py      # Базовая оценка
│   │   ├── assessment_enhanced.py  # ✨ Расширенная аналитика
│   │   ├── notifications_enhanced.py  # ✨ Умные уведомления
│   │   ├── achievements.py    # ✨ Продвинутые достижения
│   │   ├── teacher_analytics.py  # ✨ Аналитика учителей
│   │   ├── gamification.py    # Геймификация
│   │   ├── ai.py              # AI помощник
│   │   └── ...
│   ├── templates/             # HTML шаблоны
│   └── static/                # Статические файлы
├── inregistrare/              # Регистрация/авторизация
├── unitexapp/                 # Дополнительное приложение
├── unitex_school/             # Настройки проекта
├── manage.py
├── requirements.txt
└── README.md                  # Этот файл
```

---

## 🎓 Основные модели

```python
# Обучение
Lesson          # Урок
Test            # Тест
LessonProgress  # Прогресс по уроку
TestAttempt     # Попытка теста

# Геймификация
UserProfile     # Профиль пользователя
Badge           # Значок
Mission         # Миссия
UserBadge       # Выданный значок

# Классы
Classroom       # Класс
ClassAssignment # Задание
Submission      # Сданная работа

# Проекты
Project         # Проект
ProjectSubmission  # Сданный проект

# Система
Notification    # Уведомление
DailyChallenge  # Ежедневный челлендж
```

---

## 🔧 Конфигурация

### Настройки окружения

Создайте `.env` файл:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379/0
```

### Email (опционально)

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
```

---

## 🧪 Тестирование

```bash
# Запустить все тесты
python manage.py test

# Запустить тесты конкретного приложения
python manage.py test estudy

# С отчетом о покрытии
coverage run --source='.' manage.py test
coverage report
```

---

## 📈 Метрики

### Пользовательские:
- **Активные пользователи** (DAU/MAU)
- **Retention rate** (7/30 дней)
- **Среднее время сессии**
- **Уроков на пользователя**

### Учебные:
- **Средняя успеваемость** по тестам
- **Скорость прохождения** уроков
- **Процент завершения** курсов

### Технические:
- **Время загрузки** страницы < 2s
- **API response time** < 200ms
- **Error rate** < 1%
- **Uptime** > 99.9%

---

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта!

1. Fork репозиторий
2. Создайте ветку: `git checkout -b feature/amazing-feature`
3. Commit изменения: `git commit -m 'Add amazing feature'`
4. Push в ветку: `git push origin feature/amazing-feature`
5. Создайте Pull Request

---

## 📝 Changelog

### v2.0.0 (9 ноября 2025)
✨ **Новые возможности:**
- Расширенная аналитика студентов
- Умная система уведомлений
- Продвинутые достижения
- Аналитика для учителей

📚 **Документация:**
- Полный план улучшений
- Примеры использования
- Архитектура системы

### v1.0.0
- Базовый функционал платформы
- Уроки, тесты, геймификация
- Классы и задания

---

## 📞 Поддержка

- **Email:** support@ecosystem.edu
- **Документация:** [docs](IMPROVEMENT_PLAN.md)
- **Issues:** [GitHub Issues](https://github.com/your-username/ecosystem/issues)

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для деталей.

---

## 👏 Благодарности

- Django Community
- Bootstrap Team
- Все контрибьюторы проекта

---

## 🚀 Roadmap

### Q4 2025
- [ ] API для мобильного приложения
- [ ] Улучшенная проверка кода
- [ ] Интеграция с GitHub

### Q1 2026
- [ ] Система сертификатов
- [ ] Peer-to-peer обучение
- [ ] PWA и офлайн режим

### Q2 2026
- [ ] Интерактивные симуляции
- [ ] Расширенный AI функционал
- [ ] Мобильные приложения (iOS/Android)

---

**Создано с ❤️ командой Ecosystem**

*Последнее обновление: 9 ноября 2025* 