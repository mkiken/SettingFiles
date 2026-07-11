---
description: >
  Activate fact-based response mode that prioritizes factual accuracy, source citations,
  and explicit certainty levels. Use this when the user asks to verify external facts,
  statistics, specifications, or current events, or requests evidence-backed answers
  with sources. Not for codebase investigation, refactoring, or implementation requests.
  Trigger keywords: "ファクトチェック", "事実ベースで", "ソースは？", "根拠は？",
  "fact check", "cite sources", "how certain are you", "is this accurate", "verify this".
allowed-tools: Bash(/bin/cat:*)
---

## Fact-Based Response Mode

Apply the following protocol for this conversation.

!`/bin/cat ~/.claude/common/fact_based_core.md`

### Scope

If `$ARGUMENTS` is provided, apply this protocol to answer that topic or question immediately.

If `$ARGUMENTS` is empty, activate this mode for all subsequent responses involving factual claims, statistics, technical specifications, or source-dependent information.
