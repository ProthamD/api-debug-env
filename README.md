cd "D:\Meta Hackathon\api_debug_env"

@"
---
title: API Debug Env
emoji: 🔧
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# API Debug Environment

An OpenEnv environment where AI agents learn to debug broken HTTP API requests.
"@ | Out-File -FilePath "README.md" -Encoding utf8

git add README.md
git commit -m "Add HF Space README"
git push origin master:main