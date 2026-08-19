---
description: leadR script stage. Run /leadr-script to write the script with them (leadR writes the hook). Same as /leadr but goes straight to this stage. Use when the member says they want to script.
---

# /leadr-script

Exactly the same contract as `/leadr` (read that skill's rules: sign in, load context, save as you
go, report failures). The only difference: skip the menu and go straight to the **script** stage.

1. `leadr status`; if not signed in, run the sign-in steps from `/leadr` (email, six digit code).
2. `leadr me`; read their `context` fully (newest wins) and their recent work. If `onboarded` is
   false, run the onboarding stage first, then come back.
3. `leadr stage script` and follow the returned `instructions` as written. They are the current
   leadR method and they change often; the served version always wins over memory.
4. `leadr event script started` at the start, `leadr event script completed` at the end; save
   anything learned with `leadr context`, anything made with `leadr work` / `leadr setwork`,
   and `leadr progress script <work_id>` before the session ends.
5. Things will break sometimes. Check `troubleshooting` first; if it still fails, `leadr failure`
   with a stable fingerprint, and tell them plainly where they stand.

House rules that apply to everything you write for them: no em dashes or en dashes (commas, full
stops, colons), money in pounds, never post or publish anything without their explicit go.
