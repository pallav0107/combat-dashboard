"""Publish a REDACTED combat_state.json to the public GitHub Pages dashboard, then git-push.
No keys, no account IDs — only equity/positions/regime/roster (all paper). Run from webdash/."""
import os, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys, requests
HERE = Path(__file__).parent
COMBAT = HERE.parent
sys.path.insert(0, str(COMBAT))
import combatants

def load_env(p):
    if Path(p).exists():
        for ln in open(p):
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.strip().split("=", 1); os.environ.setdefault(k, v)
load_env(COMBAT / ".env")
load_env(os.path.expanduser("~/missions/.openclaw_shared/secrets/.env"))  # GH_TOKEN

def alp(path):
    h = {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}
    return requests.get(os.environ["ALPACA_BASE_URL"] + path, headers=h, timeout=15).json()

a = alp("/v2/account"); eq = float(a["equity"]); cash = float(a["cash"]); le = float(a.get("last_equity", eq))
pos = alp("/v2/positions")
dep = json.loads((COMBAT/"state"/"deployment.json").read_text()) if (COMBAT/"state"/"deployment.json").exists() else {}
ep = json.loads((COMBAT/"state"/"exec_plan.json").read_text()) if (COMBAT/"state"/"exec_plan.json").exists() else {}

state = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "mode": ep.get("mode", "DRY_RUN"),
    "equity": eq, "cash": cash, "invested": eq - cash, "day_pl": eq - le,
    "notional": ep.get("notional", 50000),
    "regime": dep.get("regime") or ep.get("regime", "—"),
    "allocation": dep.get("deploy", {}),
    "positions": [{"symbol": p["symbol"], "value": float(p["market_value"]), "pl_pct": round(float(p["unrealized_plpc"])*100, 1)} for p in pos],
    "roster": [{"fighter": f, "style": combatants.DESCRIPTIONS[f], "best_regime": max(combatants.ROSTER[f], key=combatants.ROSTER[f].get)} for f in combatants.ROSTER],
}
(HERE/"combat_state.json").write_text(json.dumps(state, indent=2))
print("published combat_state.json | equity $%.0f | regime %s | %d positions" % (eq, state["regime"], len(state["positions"])))

# --- git commit + push (token from GH_TOKEN, never printed, not stored in config) ---
tok = os.environ.get("GH_TOKEN", "")
os.chdir(HERE)
subprocess.run(["git", "add", "combat_state.json", "index.html"], check=False)
subprocess.run(["git", "commit", "-m", "update " + state["updated"][:16]], check=False,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
if tok:
    r = subprocess.run(["git", "push", "https://x-access-token:%s@github.com/pallav0107/combat-dashboard.git" % tok, "HEAD:main"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print("git push:", "OK" if r.returncode == 0 else "FAILED (" + r.stderr.decode()[:80] + ")")
else:
    print("no GH_TOKEN — skipped push")
