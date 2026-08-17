# leadR skills

The Claude Code plugin for members of the leadR community. Two commands to install, then `/leadr`
picks up wherever you left off.

## Install

In Claude Code:

```
/plugin marketplace add mitchellali123/leadr-skills
```

```
/plugin install leadr@leadr
```

Then:

```
/leadr
```

First run asks for your email and sends you a six digit code. After that it remembers you on this
machine.

## What it does

`/leadr` asks what you are working on and walks you through it: finding an idea, writing the
script, getting ready to record, editing, thumbnails and posting, then turning one video into a
week of content. You can start at any stage. Wrote your script somewhere else? Start at recording.
Only want a LinkedIn post? Go straight there.

Your brand, tone, scripts and what has worked live with leadR, so each session knows what you did
last time and gets faster as you go.

## What is in this repo, and what is not

**In here:** a router. It knows how to ask leadR what to do and how to save your work. That is all.

**Not in here:** the actual method. The scripting formula, the edit process, the quality bar, the
layouts, the recording rules. Those are served from leadR when you run a stage, which means:

- You always have the current version. When we improve something, your next run has it. There is
  nothing to download and no versions to keep track of.
- New stages appear in your menu on their own, with no action from you.

## Your files stay on your machine

Footage, Daydream projects and exports never leave your computer. The only things that travel to
leadR are text: your context, your scripts, and reports of what broke so we can fix it for
everybody.

## The security model, briefly

An email address is a claim, not proof. Signing in emails you a code, and only that code produces a
session. Everything you can then read or write is scoped to you at the database, not by code we
wrote, so there is no route by which one member reads another's work.

The `supabase_anon_key` in `scripts/config.json` is public by design. It names the project and
grants nothing: the anonymous role can read nothing at all. Your data is protected by your login.

## Something broken?

Tell `/leadr` and it will try the known fixes, then report it so we can fix it properly. Anything
else: ask in the community.

## Development

Test locally without installing:

```bash
claude --plugin-dir ./plugins/leadr
```

Validate before pushing:

```bash
claude plugin validate ./plugins/leadr
```

Publishing an update: push to this repo, and members pick it up with
`/plugin marketplace update`. Only structural changes need that. Content changes (instructions,
troubleshooting, new stages) are served at runtime and need no release at all.
