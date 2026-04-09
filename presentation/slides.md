---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    padding: 40px;
  }
  h1 {
    font-size: 2.2em;
    margin-bottom: 0.3em;
  }
  h2 {
    font-size: 1.6em;
    color: #4338ca;
    margin-bottom: 0.6em;
  }
  .title-info {
    font-size: 1.1em;
    color: #555;
    line-height: 1.8;
  }
  .feature-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    font-size: 0.9em;
  }
  .links-table {
    width: 100%;
    font-size: 1em;
  }
  .link-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 0;
    border-bottom: 1px solid #e5e7eb;
  }
  .emoji {
    font-size: 2em;
  }
---

<!-- _class: lead -->

# 📅 Schedule Bot

### Zakhar Zaitcev
z.zaitcev@innopolis.university
CSE-05

---

## Контекст

| | |
|---|---|
| **Конечные пользователи** | Студенты и преподаватели Sirius University |
| **Проблема** | Расписание в Google Sheets — неудобно с телефона, нет быстрого поиска, сложно найти кабинет или преподавателя |
| **Идея** | Расписание в один тап + AI-бот, отвечающий на вопросы естественным языком |

---

## Выполнение

**Как создан:**
FastAPI web UI + Nanobot AI-агент + MCP-сервер + синхронизация из Google Sheets → кэш в SQLite

| Версия 1 | Версия 2 |
|---|---|
| LLM-бот с запросами на естественном языке | Кнопка «Вся неделя» — фикс бага (итерация DAYS) |
| Базовый web-чат | Правка URL Google Sheets (опечатка в ID) |
| MCP-сервер с 6 инструментами | Standalone web UI без LLM |
| Авто-синк из Sheets | README + MIT License |

---

## Демонстрация

<div style="display:flex;justify-content:center;align-items:center;min-height:300px;">

### 🎬 Видео-демонстрация Версии 2

*[Вставить записанное видео (до 2 мин с голосом)]*

</div>

---

<!-- _class: lead -->

## Ссылки

<div style="display:flex; justify-content:space-around; margin-top:30px;">

<div style="text-align:center; flex:1;">

**📂 GitHub-репозиторий**

`https://github.com/ZZInfaZV/schedule-bot`

![QR: GitHub](https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=https://github.com/ZZInfaZV/se-toolkit-hackathon)

</div>

<div style="text-align:center; flex:1;">

**🚀 Развёрнутый продукт**

`http://10.93.25.141:8080`

![QR: Live](https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=http://10.93.25.141:8080)

</div>

</div>
