---
name: Feedback & Preferences
description: 用戶對工作方式的偏好與回饋
type: feedback
---

## 繁體中文溝通
**Why:** 用戶慣用繁體中文。
**How to apply:** 所有回覆和說明預設用繁體中文。

## 記憶存放在專案 .claude/memory/ 資料夾
**Why:** 用戶希望記憶跟著 git 走，不同電腦 git pull 後就有一樣的記憶。
**How to apply:** 記憶檔寫在 `/Users/tittan/program/github/xauusd/.claude/memory/`（系統路徑 symlink 指向此處）。新電腦需執行：
```bash
rm -rf ~/.claude/projects/-Users-tittan-program-github-xauusd/memory
ln -s /path/to/xauusd/.claude/memory ~/.claude/projects/-Users-tittan-program-github-xauusd/memory
```
