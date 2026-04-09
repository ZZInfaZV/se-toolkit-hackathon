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

## Context

| | |
|---|---|
| **End Users** | Students and faculty of Sirius University |
| **Problem** | Schedule in Google Sheets — inconvenient on phone, no quick search, hard to find a room or instructor |
| **Idea** | Schedule in one tap + Web bot that answers questions about schedule |

---

## Implementation

**How it was built:**
FastAPI web UI + sync from Google Sheets → cache in SQLite

| Version 1 | Version 2 |
|---|---|
| Schedule bot with queries | "Whole week" button — (DAYS iteration) |
| Button "What's now?" | Button "What's now shows current schedule for chosen group" |
| No sync button | Added new buttton "Sync" that synchronize data with actual schedule in Google Sheet |

---

## Demonstration

<div style="display:flex;justify-content:center;align-items:center;min-height:300px;">

### 🎬 Video Demonstration of Version 2

<video controls width="100%" style="max-width: 800px;">
  <source src="video/video1.mp4" type="video/mp4">
</video>

</div>

---

<!-- _class: lead -->

## Links

<div style="display:flex; justify-content:space-around; margin-top:30px;">

<div style="text-align:center; flex:1;">

**📂 GitHub Repository**

`https://github.com/ZZInfaZV/schedule-bot`

![QR: GitHub](https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=https://github.com/ZZInfaZV/se-toolkit-hackathon)

</div>

<div style="text-align:center; flex:1;">

**🚀 Deployed Product**

`http://10.93.25.141:8080`

![QR: Live](https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=http://10.93.25.141:8080)

</div>

</div>
