#!/usr/bin/python3
# <xbar.title>Traggo</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Ihor Muliar</xbar.author>
# <xbar.author.github>IhorMuliar</xbar.author.github>
# <xbar.desc>Start/stop Traggo time tracking per project from the macOS menu bar.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
#
# Config: ~/.config/traggo-swiftbar/config.json  (see README)
# Auth:   a NoExpiry Traggo device token in the macOS Keychain
#         security add-generic-password -s traggo-swiftbar -a <user> -w <token> -T /usr/bin/security
# Actions (invoked by the menu items): traggo.30s.py start <project> | stop

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

CONFIG_PATH = os.path.expanduser("~/.config/traggo-swiftbar/config.json")
DEFAULTS = {
    "url": "https://traggo.example.com",
    "tag_key": "project",
    "projects": [],                 # always offered; server-known values are merged in
    "keychain_service": "traggo-swiftbar",
    "keychain_account": os.environ.get("USER", ""),
    "timeout": 5,
}
SELF = os.path.abspath(__file__)


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    cfg["url"] = cfg["url"].rstrip("/")
    return cfg


CFG = load_config()


def token():
    return subprocess.check_output(
        ["/usr/bin/security", "find-generic-password", "-s", CFG["keychain_service"],
         "-a", CFG["keychain_account"], "-w"], stderr=subprocess.DEVNULL).decode().strip()


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(CFG["url"] + "/graphql", data=body, headers={
        "Content-Type": "application/json", "Authorization": "traggo " + token()})
    with urllib.request.urlopen(req, timeout=CFG["timeout"]) as r:
        out = json.load(r)
    if out.get("errors"):
        raise RuntimeError(out["errors"][0]["message"])
    return out["data"]


def now_rfc3339():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt(td):
    m = int(td.total_seconds() // 60)
    return "%d:%02d" % divmod(m, 60)


def project_of(span):
    for t in span.get("tags") or []:
        if t["key"] == CFG["tag_key"]:
            return t["value"]
    return "?"


# ---------- actions ----------

def running():
    return gql("{ timers { id start tags { key value } } }")["timers"]


def stop_all():
    for t in running():
        gql("mutation($id:Int!,$end:Time!){ stopTimeSpan(id:$id,end:$end){ id } }",
            {"id": t["id"], "end": now_rfc3339()})


def start(project):
    stop_all()
    gql("mutation($s:Time!,$tags:[InputTimeSpanTag!]){ createTimeSpan(start:$s,tags:$tags,note:\"\"){ id } }",
        {"s": now_rfc3339(), "tags": [{"key": CFG["tag_key"], "value": project}]})


# ---------- menu ----------

def today_totals():
    local_midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    data = gql("query($f:Time!,$t:Time!){ timeSpans(fromInclusive:$f,toInclusive:$t,cursor:{pageSize:500}) "
               "{ timeSpans { start end tags { key value } } } }",
               {"f": local_midnight.isoformat(), "t": now_rfc3339()})  # isoformat -> RFC3339 "+02:00" offset
    totals = {}
    now = datetime.now(timezone.utc)
    for s in data["timeSpans"]["timeSpans"]:
        end = parse_time(s["end"]) if s.get("end") else now
        totals[project_of(s)] = totals.get(project_of(s), timedelta()) + (end - parse_time(s["start"]))
    return totals


def known_projects():
    vals = list(CFG["projects"])
    try:
        for v in gql('query($k:String!){ suggestTagValue(key:$k,query:"") }',
                     {"k": CFG["tag_key"]})["suggestTagValue"]:
            if v not in vals:
                vals.append(v)
    except Exception:
        pass
    return vals


def menu():
    act = 'bash="%s" terminal=false refresh=true' % SELF
    try:
        timers = running()
    except (urllib.error.URLError, OSError, RuntimeError, subprocess.CalledProcessError):
        print("⏱ ✕ | color=gray")
        print("---")
        print("Traggo unreachable | color=red")
        print("Is the VPN on? Is the Keychain token set? | size=11 color=gray")
        print("Open Traggo | href=%s" % CFG["url"])
        print("Refresh | refresh=true")
        return

    if timers:
        t = timers[0]
        proj, since = project_of(t), parse_time(t["start"])
        elapsed = datetime.now(timezone.utc) - since
        print("▶ %s %s" % (proj, fmt(elapsed)))
        print("---")
        print("Tracking %s since %s | color=green" % (proj, since.astimezone().strftime("%H:%M")))
        print("Stop | %s param1=stop sfimage=stop.circle" % act)
        current = proj
    else:
        print("⏱ | color=gray")
        print("---")
        print("Not tracking | color=gray")
        current = None

    print("---")
    for p in known_projects():
        if p == current:
            continue
        label = ("Switch to %s" if current else "Start %s") % p
        print("%s | %s param1=start param2=%s sfimage=play.circle" % (label, act, p))

    print("---")
    try:
        totals = today_totals()
        total = sum(totals.values(), timedelta())
        print("Today %s" % fmt(total))
        for p, d in sorted(totals.items(), key=lambda kv: -kv[1]):
            print("--%s  %s" % (p, fmt(d)))
    except Exception:
        print("Today: n/a | color=gray")

    print("---")
    print("Open Traggo | href=%s" % CFG["url"])
    print("Refresh | refresh=true")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "start" and len(args) > 1:
        start(args[1])
    elif args and args[0] == "stop":
        stop_all()
    else:
        menu()
