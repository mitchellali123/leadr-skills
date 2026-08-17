#!/usr/bin/env python3
"""
leadr_api.py: all the plumbing between a member's machine and the leadR brain.

Standard library only, so nothing to install. Python 3.8+.

This file is deliberately DUMB. It moves data and holds no method: no scripting formula, no edit
process, no quality bar. All of that is served from the `stages` table at runtime, gated on the
member's own token. This repo is public, so anything in it is public.

Auth is Supabase Auth. An email is a CLAIM, never proof: the member enters an email, Supabase
emails a six digit code, and only exchanging that code produces a session. Row level security then
scopes every read and write to that member. There is no server of ours in the middle.

Commands
    status                                  are we signed in, and as who
    signin  <email>                         send a six digit code to that mailbox
    verify  <email> <code>                  exchange the code for a session, stored locally
    signout                                 forget the session on this machine
    me                                      context + progress + the stage menu, as JSON
    stage   <key>                           that stage's instructions, as JSON
    context <dimension> <value> [topic]     append one piece of context, newest wins
    work    <kind> <title> [format]         start a piece of work, prints its id
    setwork <id> <status>                   move a piece of work along
    progress <stage_key> [work_id]          record where they are
    event   <stage_key> <action>            behaviour log: started / completed / abandoned
    failure <stage_key> <step> <error> <attempted> <fingerprint>
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.path.expanduser("~/.leadr/session.json")


def _config():
    """URL and anon key. The anon key is PUBLIC by design: it identifies the project, it does not
    grant anything. Every table is behind row level security, and `anon` itself can read nothing."""
    cfg_path = os.path.join(HERE, "config.json")
    cfg = {}
    if os.path.exists(cfg_path):
        cfg = json.load(open(cfg_path))
    url = os.environ.get("LEADR_SUPABASE_URL") or cfg.get("supabase_url", "")
    key = os.environ.get("LEADR_SUPABASE_ANON_KEY") or cfg.get("supabase_anon_key", "")
    if not url or key.startswith("PASTE_"):
        die("This copy of the plugin is not configured yet. Ask leadR for the current "
            "config.json, or set LEADR_SUPABASE_URL and LEADR_SUPABASE_ANON_KEY.")
    return url.rstrip("/"), key


def die(msg, code=1):
    print(json.dumps({"ok": False, "error": msg}, indent=2))
    sys.exit(code)


def out(obj):
    print(json.dumps(obj, indent=2, default=str))


# ── HTTP ──────────────────────────────────────────────────────────────────────
def _request(method, url, headers=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        try:
            detail = json.loads(detail).get("msg") or json.loads(detail).get("message") or detail
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"cannot reach leadR ({e.reason}). Check the internet connection.")


# ── Session ───────────────────────────────────────────────────────────────────
def _save_session(tok):
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    tok["saved_at"] = int(time.time())
    with open(SESSION_PATH, "w") as f:
        json.dump(tok, f, indent=2)
    os.chmod(SESSION_PATH, 0o600)          # tokens are secrets, keep them off other accounts


def _load_session():
    if not os.path.exists(SESSION_PATH):
        return None
    try:
        return json.load(open(SESSION_PATH))
    except Exception:
        return None


def _access_token():
    """A valid access token, refreshing silently if it has expired."""
    s = _load_session()
    if not s:
        die("not signed in. Run: signin <your email>")
    if s.get("expires_at", 0) - 60 > time.time():
        return s["access_token"]
    url, key = _config()
    try:
        tok = _request("POST", f"{url}/auth/v1/token?grant_type=refresh_token",
                       {"apikey": key}, {"refresh_token": s["refresh_token"]})
    except RuntimeError:
        die("the session has expired. Run: signin <your email>")
    if not tok.get("access_token"):
        die("the session has expired. Run: signin <your email>")
    _save_session(tok)
    return tok["access_token"]


def _auth_headers():
    url, key = _config()
    return {"apikey": key, "Authorization": "Bearer " + _access_token()}


def _rest(method, path, body=None, prefer=None):
    url, _ = _config()
    h = _auth_headers()
    if prefer:
        h["Prefer"] = prefer
    return _request(method, f"{url}/rest/v1/{path}", h, body)


# ── Commands ──────────────────────────────────────────────────────────────────
def cmd_status():
    # Report an unconfigured plugin here rather than letting the member discover it at signin:
    # this is the router's first call, so it is the cheapest place to catch it.
    cfg_path = os.path.join(HERE, "config.json")
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
    key = os.environ.get("LEADR_SUPABASE_ANON_KEY") or cfg.get("supabase_anon_key", "")
    url = os.environ.get("LEADR_SUPABASE_URL") or cfg.get("supabase_url", "")
    if not url or not key or key.startswith("PASTE_"):
        return out({"ok": False, "configured": False, "signed_in": False,
                    "error": "This copy of the plugin is not configured. Ask leadR for the "
                             "current config.json, or set LEADR_SUPABASE_URL and "
                             "LEADR_SUPABASE_ANON_KEY."})
    s = _load_session()
    if not s:
        return out({"ok": True, "configured": True, "signed_in": False})
    try:
        rows = _rest("GET", "members?select=id,email,created_at,status")
    except RuntimeError as e:
        return out({"ok": False, "signed_in": False, "error": str(e)})
    if not rows:
        return out({"ok": False, "signed_in": False,
                    "error": "signed in but no member record. Tell leadR."})
    out({"ok": True, "signed_in": True, "member": rows[0]})


def cmd_signin(email):
    url, key = _config()
    _request("POST", f"{url}/auth/v1/otp", {"apikey": key},
             {"email": email.strip().lower(), "create_user": True})
    # Deliberately never says whether that email is known to us: that would leak the member list.
    out({"ok": True, "sent": True,
         "message": "If we can reach that address, a six digit code is on its way. "
                    "It expires shortly. Then run: verify <email> <code>"})


def cmd_verify(email, code):
    url, key = _config()
    tok = _request("POST", f"{url}/auth/v1/verify", {"apikey": key},
                   {"email": email.strip().lower(), "token": code.strip(), "type": "email"})
    if not tok.get("access_token"):
        die("that code did not work. Codes expire quickly, so request a fresh one with signin.")
    _save_session(tok)
    rows = _rest("GET", "members?select=id,email")
    out({"ok": True, "signed_in": True, "member": rows[0] if rows else None})


def cmd_signout():
    if os.path.exists(SESSION_PATH):
        os.remove(SESSION_PATH)
    out({"ok": True, "signed_in": False})


def cmd_me():
    """Everything /leadr needs to open a session: who they are, what we know, where they got to,
    and the menu. One call, so the router is not chatty."""
    members = _rest("GET", "members?select=id,email,created_at")
    if not members:
        die("no member record for this session. Tell leadR.")
    m = members[0]
    context = _rest("GET", "member_context_current?select=dimension,topic,value,created_at")
    progress = _rest("GET", "member_progress?select=current_stage,current_work,updated_at")
    stages = _rest("GET", "stages?select=key,label,section,sort&order=sort")
    work = _rest("GET", "member_work?select=id,kind,format,title,status,created_at"
                        "&order=created_at.desc&limit=10")
    out({"ok": True, "member": m, "context": context, "progress": progress[0] if progress else None,
         "recent_work": work, "stages": stages, "onboarded": len(context) > 0})


def cmd_stage(key):
    rows = _rest("GET", f"stages?key=eq.{key}&select=key,label,section,instructions,"
                        "troubleshooting,doc_url")
    if not rows:
        die(f"no stage called {key!r}. Run `me` for the current menu.")
    out({"ok": True, "stage": rows[0]})


def _member_id():
    rows = _rest("GET", "members?select=id")
    if not rows:
        die("no member record for this session.")
    return rows[0]["id"]


def cmd_context(dimension, value, topic=None):
    _rest("POST", "member_context", [{"member_id": _member_id(), "dimension": dimension,
                                      "topic": topic, "value": value, "source": "session"}])
    out({"ok": True, "saved": {"dimension": dimension, "topic": topic}})


def cmd_work(kind, title, fmt=None):
    r = _rest("POST", "member_work", [{"member_id": _member_id(), "kind": kind,
                                       "title": title, "format": fmt}],
              prefer="return=representation")
    out({"ok": True, "work": r[0] if r else None})


def cmd_setwork(work_id, status):
    _rest("PATCH", f"member_work?id=eq.{work_id}", {"status": status})
    out({"ok": True, "work_id": work_id, "status": status})


def cmd_progress(stage_key, work_id=None):
    row = {"member_id": _member_id(), "current_stage": stage_key}
    if work_id:
        row["current_work"] = int(work_id)
    _rest("POST", "member_progress", [row], prefer="resolution=merge-duplicates")
    out({"ok": True, "progress": row})


def cmd_event(stage_key, action):
    _rest("POST", "member_events", [{"member_id": _member_id(), "stage_key": stage_key,
                                     "action": action}])
    out({"ok": True})


def cmd_failure(stage_key, step, error, attempted, fingerprint):
    _rest("POST", "member_failures", [{"member_id": _member_id(), "stage_key": stage_key,
                                       "step": step, "error": error[:2000],
                                       "attempted": attempted[:2000], "resolved": False,
                                       "fingerprint": fingerprint}])
    out({"ok": True, "reported": fingerprint})


COMMANDS = {
    "status": (cmd_status, 0), "signin": (cmd_signin, 1), "verify": (cmd_verify, 2),
    "signout": (cmd_signout, 0), "me": (cmd_me, 0), "stage": (cmd_stage, 1),
    "context": (cmd_context, 2), "work": (cmd_work, 2), "setwork": (cmd_setwork, 2),
    "progress": (cmd_progress, 1), "event": (cmd_event, 2), "failure": (cmd_failure, 5),
}


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    name = argv[1]
    if name not in COMMANDS:
        die(f"unknown command {name!r}. Run --help.")
    fn, need = COMMANDS[name]
    args = argv[2:]
    if len(args) < need:
        die(f"{name} needs {need} argument(s), got {len(args)}. Run --help.")
    try:
        fn(*args)
    except RuntimeError as e:
        die(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
