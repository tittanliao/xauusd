---
name: Feedback & Preferences
description: 用戶對工作方式的偏好與回饋
type: feedback
originSessionId: 50c1ae8c-8816-4a68-a11d-86ce07776023
---
## 繁體中文溝通
**Why:** 用戶慣用繁體中文。
**How to apply:** 所有回覆和說明預設用繁體中文。

## 記憶存放在專案 .claude/memory/ 資料夾
**Why:** 用戶希望記憶跟著 git 走，不同電腦 git pull 後就有一樣的記憶。
**How to apply:** 記憶檔寫在 `.claude/memory/`（系統路徑 symlink 指向此處）。新電腦需依 CLAUDE.md 說明設定 Junction/symlink。

## 每次改動後必須執行的三步流程
**Why:** 用戶明確要求（2026-05-04）「後續改動請記得更新 claude.md 與 .claude 然後幫我 commit and push」。
**How to apply:** 完成任何功能改動後，不等用戶提醒，主動：
1. 更新 `CLAUDE.md`（若目錄結構或設計有變）
2. 更新 `.claude/memory/`（project_context.md 或其他相關 memory）
3. `git add` → `git commit` → `git push`
所有三步合在一個 commit 一起推上去。
