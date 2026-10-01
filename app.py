import json, re, sqlite3, threading
from datetime import datetime, timedelta
from html import escape as e

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from google import genai
from google.genai import types

st.set_page_config(page_title="Cart Pool", page_icon="🛒", layout="centered")

# =====================================================================
# STYLES
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, .stMarkdown, .stButton button, input, label, p { font-family: 'Plus Jakarta Sans', sans-serif !important; }
.stApp { background: #F7F5EF; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 720px; }
h1, h2, h3 { font-weight: 800 !important; letter-spacing: -0.02em; color: #1B2A21; }

.brand { font-size: 26px; font-weight: 800; letter-spacing: -0.03em; color: #1B2A21; }
.brand span { color: #1F7A4D; }

.hero { background: linear-gradient(135deg, #1F7A4D 0%, #2E9E66 100%); color: #fff; border-radius: 24px; padding: 30px 28px; margin: 8px 0 22px; }
.hero h1 { color: #fff !important; font-size: 30px; margin: 0 0 6px; line-height: 1.15; }
.hero p { color: #E3F4EA; margin: 0; font-size: 16px; }
.stats { display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap; }
.stat { background: rgba(255,255,255,.14); border-radius: 14px; padding: 10px 16px; min-width: 110px; }
.stat b { display: block; font-size: 22px; color: #fff; }
.stat small { color: #D2EEDD; font-size: 12px; }

[class*="st-key-card"] { background: #fff; border: 1px solid #E7E3D8; border-radius: 20px; padding: 20px 20px 14px; box-shadow: 0 2px 12px rgba(27,42,33,.05); transition: transform .15s ease, box-shadow .15s ease; }
[class*="st-key-card"]:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(27,42,33,.09); }

.store { font-size: 19px; font-weight: 800; color: #1B2A21; margin-bottom: 4px; }
.meta { color: #6B766D; font-size: 14px; margin-top: 2px; }
.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.between { display: flex; justify-content: space-between; align-items: center; margin: 14px 0 8px; }
.muted { color: #6B766D; font-size: 13px; }

.pill { border-radius: 99px; padding: 5px 12px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.pill-open { background: #E3F4EA; color: #1F7A4D; }
.pill-full { background: #EFEDE7; color: #6B766D; }

.avatars { display: flex; align-items: center; }
.avatar { width: 34px; height: 34px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 12px; border: 2.5px solid #fff; margin-right: -9px; }

.bar { height: 8px; background: #EEF2EC; border-radius: 99px; overflow: hidden; margin-bottom: 12px; }
.bar > div { height: 100%; background: linear-gradient(90deg, #2E9E66, #1F7A4D); border-radius: 99px; }

.section { font-size: 18px; font-weight: 800; margin: 26px 0 10px; color: #1B2A21; }
.item-name { font-weight: 700; font-size: 16px; }
.price { font-weight: 800; color: #1F7A4D; font-size: 16px; }

.receipt { background: #fff; border: 1.5px dashed #CFC8B6; border-radius: 18px; padding: 20px 22px; font-family: 'JetBrains Mono', monospace; font-size: 14px; }
.rhead { text-align: center; font-weight: 600; letter-spacing: .12em; color: #6B766D; font-size: 12px; padding-bottom: 12px; border-bottom: 1.5px dashed #CFC8B6; margin-bottom: 8px; }
.rrow { display: flex; justify-content: space-between; align-items: center; padding: 9px 0; border-bottom: 1px dotted #E2DDCF; gap: 10px; }
.rtotal { display: flex; justify-content: space-between; padding-top: 12px; font-weight: 600; font-size: 15px; }
.tag { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 11px; font-weight: 700; border-radius: 99px; padding: 3px 9px; margin-left: 6px; }
.tag-ok { background: #E3F4EA; color: #1F7A4D; }
.tag-wait { background: #FDF0E1; color: #B4621B; }
.tag-host { background: #E8ECFB; color: #4453B5; }

.stButton button, .stFormSubmitButton button { border-radius: 12px; font-weight: 700; padding: .55rem 1.1rem; }
button[kind="primary"], button[kind="primaryFormSubmit"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: #1F7A4D !important; border-color: #1F7A4D !important; color: #fff !important; }
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover { background: #18663F !important; }
.stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input { border-radius: 12px !important; }
[data-testid="stForm"] { background: #fff; border: 1px solid #E7E3D8; border-radius: 20px; padding: 22px; }
</style>
""", unsafe_allow_html=True)

def html(s):
    st.markdown("".join(line.strip() for line in s.splitlines()), unsafe_allow_html=True)

# =====================================================================
# DATABASE
# =====================================================================
@st.cache_resource
def get_db():
    con = sqlite3.connect("cartpool.db", check_same_thread=False)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, store TEXT, area TEXT, meet TEXT,
                                    when_ts TEXT, spots INTEGER, host TEXT);
    CREATE TABLE IF NOT EXISTS members(run_id INTEGER, name TEXT, paid INTEGER DEFAULT 0,
                                       PRIMARY KEY(run_id, name));
    CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY, run_id INTEGER, name TEXT, price REAL);
    CREATE TABLE IF NOT EXISTS shares(item_id INTEGER, name TEXT, count INTEGER,
                                      PRIMARY KEY(item_id, name));
    """)
    return con, threading.Lock()

db, lock = get_db()

def q(sql, args=()):
    with lock:
        return db.execute(sql, args).fetchall()

def execute(sql, args=()):
    with lock, db:
        return db.execute(sql, args).lastrowid

# =====================================================================
# HELPERS
# =====================================================================
gbp = lambda n: f"£{n:,.2f}"
fmt = lambda w: datetime.fromisoformat(w).strftime("%a %d %b · %H:%M")
PALETTE = ["#1F7A4D", "#E07A3F", "#5B6CD9", "#C24E7A", "#2A9D8F", "#B8860B"]
initials = lambda n: "".join(p[0] for p in n.split()[:2]).upper() or "?"

def avatars(names):
    shown = "".join(
        f'<span class="avatar" title="{e(n)}" style="background:{PALETTE[sum(map(ord, n)) % len(PALETTE)]}">{e(initials(n))}</span>'
        for n in names[:6])
    extra = f'<span class="muted" style="margin-left:16px">+{len(names) - 6}</span>' if len(names) > 6 else ""
    return f'<div class="avatars">{shown}{extra}</div>'

def spots_pill(left):
    if left > 0:
        return f'<span class="pill pill-open">{left} spot{"s" if left != 1 else ""} left</span>'
    return '<span class="pill pill-full">Full</span>'

def progress(joined, spots):
    pct = min(100, round(joined / max(spots, 1) * 100))
    return f'<div class="bar"><div style="width:{pct}%"></div></div>'

def go(view, rid=None):
    st.session_state.view, st.session_state.rid = view, rid
    st.rerun()

# ---------- Gemini receipt scanner ----------
PROMPT = """Read this shop receipt. Return ONLY a JSON array, like:
[{"name": "Basmati rice 10kg", "price": 15.99}]
Include every purchased item with its final price in GBP after any line discounts.
Exclude subtotals, totals, VAT, payment, card, change and loyalty lines.
Use clear, readable item names (expand abbreviations where obvious)."""

# Tries each model in order, so the app keeps working if Google renames one
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash"]

def scan_receipt(file):
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    img.thumbnail((1600, 1600))

    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    models = [st.secrets.get("GEMINI_MODEL")] + MODELS
    text, last_err = None, None
    for model in filter(None, models):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=[img, PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
            )
            text = resp.text or ""
            break
        except Exception as ex:
            last_err = ex
    if text is None:
        raise last_err

    match = re.search(r"\[.*\]", text, re.S)
    items = json.loads(match.group(0)) if match else []
    return pd.DataFrame(
        [{"Item": str(i.get("name", "")).strip(), "Price £": round(float(i.get("price", 0)), 2)}
         for i in items if i.get("name")],
        columns=["Item", "Price £"],
    )

# =====================================================================
# NAME GATE
# =====================================================================
if "me" not in st.session_state:
    html('<div class="brand">🛒 Cart<span>Pool</span></div>')
    html("""<div class="hero"><h1>Grocery runs,<br>together.</h1>
    <p>Join other London students on bulk shopping trips. Buy big, split fair, save money.</p></div>""")
    with st.form("login"):
        name = st.text_input("What should we call you?", placeholder="e.g. Fatima")
        if st.form_submit_button("Get started →", type="primary", use_container_width=True) and name.strip():
            st.session_state.me = name.strip()
            st.session_state.view = "feed"
            st.rerun()
    st.stop()

me = st.session_state.me

# =====================================================================
# TOP BAR
# =====================================================================
c1, c2 = st.columns([3, 1], vertical_alignment="center")
c1.markdown('<div class="brand">🛒 Cart<span>Pool</span></div>', unsafe_allow_html=True)
with c2.popover(f"👤 {me}", use_container_width=True):
    if st.button("Switch user", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# =====================================================================
# FEED
# =====================================================================
def feed():
    cutoff = (datetime.now() - timedelta(hours=12)).isoformat()
    n_runs = q("SELECT COUNT(*) FROM runs WHERE when_ts > ?", (cutoff,))[0][0]
    n_people = q("SELECT COUNT(*) FROM members m JOIN runs r ON r.id = m.run_id WHERE r.when_ts > ?", (cutoff,))[0][0]
    n_split = q("SELECT COALESCE(SUM(price), 0) FROM items")[0][0]

    html(f"""<div class="hero"><h1>Buy in bulk.<br>Split the bill.</h1>
    <p>Find a grocery run near you, or start your own.</p>
    <div class="stats">
      <div class="stat"><b>{n_runs}</b><small>open runs</small></div>
      <div class="stat"><b>{n_people}</b><small>students going</small></div>
      <div class="stat"><b>{gbp(n_split)}</b><small>split so far</small></div>
    </div></div>""")

    c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
    area = c1.text_input("Filter by area", placeholder="🔍  Stratford, Croydon, Greenwich…")
    if c2.button("+ Post a run", type="primary", use_container_width=True):
        go("new")

    rows = q("""SELECT id, store, area, meet, when_ts, spots, host FROM runs
                WHERE when_ts > ? AND area LIKE ? ORDER BY when_ts""", (cutoff, f"%{area}%"))
    if not rows:
        html('<p class="muted" style="text-align:center;padding:30px 0">No runs yet. Be the first to post one 🛒</p>')

    for rid, store, ar, meet, when, spots, host in rows:
        names = [r[0] for r in q("SELECT name FROM members WHERE run_id = ?", (rid,))]
        joined = len(names) - 1
        with st.container(key=f"card_{rid}"):
            html(f"""<div class="top"><div>
              <div class="store">{e(store)}</div>
              <div class="meta">📅 {fmt(when)} &nbsp;·&nbsp; 📍 {e(ar)}</div>
              <div class="meta">🤝 Meet at {e(meet)} · hosted by {e(host)}</div>
            </div>{spots_pill(spots - joined)}</div>
            <div class="between">{avatars(names)}<span class="muted">{joined}/{spots} joined</span></div>
            {progress(joined, spots)}""")
            if st.button("View run →", key=f"open{rid}", use_container_width=True):
                go("run", rid)

# =====================================================================
# CREATE RUN
# =====================================================================
def new_run():
    if st.button("← Back"):
        go("feed")
    st.markdown("## Post a grocery run")
    with st.form("new"):
        store = st.text_input("Store", placeholder="Costco Croydon")
        c1, c2 = st.columns(2)
        area = c1.text_input("Area", placeholder="Croydon")
        meet = c2.text_input("Meeting point", placeholder="East Croydon station")
        c3, c4, c5 = st.columns(3)
        d = c3.date_input("Date")
        t = c4.time_input("Time")
        spots = c5.number_input("Spots for others", 1, 10, 3)
        ok = st.form_submit_button("Post run", type="primary", use_container_width=True)
    if ok:
        if not store.strip() or not area.strip():
            st.error("Fill in the store and area.")
            return
        when = datetime.combine(d, t).isoformat()
        rid = execute("INSERT INTO runs(store, area, meet, when_ts, spots, host) VALUES (?,?,?,?,?,?)",
                      (store.strip(), area.strip(), meet.strip(), when, int(spots), me))
        execute("INSERT INTO members VALUES (?,?,1)", (rid, me))
        go("run", rid)

# =====================================================================
# RUN PAGE
# =====================================================================
def run_page():
    rid = st.session_state.rid
    if st.button("← All runs"):
        go("feed")
    live_run(rid)

    host = q("SELECT host FROM runs WHERE id = ?", (rid,))
    if not host or host[0][0] != me:
        return

    # ---- Scan receipt (host only) ----
    html('<div class="section">📸 Scan the receipt</div>')
    with st.container(key="card_scan"):
        src = st.radio("Source", ["Upload photo", "Use camera"], horizontal=True,
                       label_visibility="collapsed")
        photo = (st.camera_input("Take a photo of the receipt") if src == "Use camera"
                 else st.file_uploader("Upload a receipt photo", type=["jpg", "jpeg", "png", "webp"]))

        if photo and st.button("✨ Read receipt", type="primary", use_container_width=True):
            with st.spinner("Reading your receipt…"):
                try:
                    st.session_state[f"scan{rid}"] = scan_receipt(photo)
                except Exception as ex:
                    st.error(f"Couldn't read that receipt: {ex}")

        scanned = st.session_state.get(f"scan{rid}")
        if scanned is not None:
            if scanned.empty:
                st.warning("No items found. Try a flatter, well-lit photo, or add items manually below.")
            else:
                st.caption("Check the items and fix anything before adding.")
                edited = st.data_editor(
                    scanned, num_rows="dynamic", use_container_width=True, key=f"ed{rid}",
                    column_config={"Price £": st.column_config.NumberColumn(format="£%.2f", min_value=0.0)},
                )
                valid = edited.dropna()
                valid = valid[(valid["Item"].astype(str).str.strip() != "") & (valid["Price £"] > 0)]
                c1, c2 = st.columns(2)
                if c1.button(f"Add {len(valid)} items · {gbp(valid['Price £'].sum())}",
                             type="primary", use_container_width=True):
                    for _, row in valid.iterrows():
                        execute("INSERT INTO items(run_id, name, price) VALUES (?,?,?)",
                                (rid, str(row["Item"]).strip(), float(row["Price £"])))
                    del st.session_state[f"scan{rid}"]
                    st.rerun()
                if c2.button("Discard", use_container_width=True):
                    del st.session_state[f"scan{rid}"]
                    st.rerun()

    # ---- Manual add (backup) ----
    html('<div class="section" style="font-size:15px">Or add an item manually</div>')
    with st.form("add_item", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("Item", placeholder="10kg basmati rice")
        price = c2.number_input("Price £", min_value=0.0, step=0.5, format="%.2f")
        if st.form_submit_button("Add item", type="primary", use_container_width=True) and name.strip() and price > 0:
            execute("INSERT INTO items(run_id, name, price) VALUES (?,?,?)", (rid, name.strip(), price))
            st.rerun()

@st.fragment(run_every="3s")
def live_run(rid):
    r = q("SELECT store, area, meet, when_ts, spots, host FROM runs WHERE id = ?", (rid,))
    if not r:
        st.error("Run not found.")
        return
    store, area, meet, when, spots, host = r[0]
    members = dict(q("SELECT name, paid FROM members WHERE run_id = ?", (rid,)))
    names = list(members)
    is_host, is_member = me == host, me in members
    joined = len(members) - 1
    left = spots - joined

    # ---- Header card ----
    with st.container(key="card_header"):
        html(f"""<div class="top"><div>
          <div class="store" style="font-size:24px">{e(store)}</div>
          <div class="meta">📅 {fmt(when)} &nbsp;·&nbsp; 📍 {e(area)}</div>
          <div class="meta">🤝 Meet at {e(meet)}</div>
        </div>{spots_pill(left)}</div>
        <div class="between">{avatars(names)}<span class="muted">{", ".join(e(n) + (" (host)" if n == host else "") for n in names)}</span></div>
        {progress(joined, spots)}""")
        if not is_member and left > 0 and st.button("Join this run", type="primary", use_container_width=True):
            execute("INSERT OR IGNORE INTO members VALUES (?,?,0)", (rid, me))
            st.rerun(scope="fragment")
        if is_member and not is_host and st.button("Leave run", use_container_width=True):
            execute("DELETE FROM members WHERE run_id = ? AND name = ?", (rid, me))
            execute("DELETE FROM shares WHERE name = ? AND item_id IN (SELECT id FROM items WHERE run_id = ?)", (me, rid))
            st.rerun(scope="fragment")

    # ---- Basket ----
    html('<div class="section">🧺 Basket</div>')
    items = q("SELECT id, name, price FROM items WHERE run_id = ?", (rid,))
    shares = {}
    for iid, n, c in q("""SELECT s.item_id, s.name, s.count FROM shares s
                          JOIN items i ON i.id = s.item_id WHERE i.run_id = ?""", (rid,)):
        shares.setdefault(iid, {})[n] = c
    if not items:
        html('<p class="muted">After shopping, the host scans the receipt or adds items below.</p>')
    for iid, name, price in items:
        sh = shares.get(iid, {})
        who = ", ".join(f"{e(n)} ×{c}" for n, c in sh.items() if c > 0) or "Nobody yet"
        with st.container(key=f"card_item_{iid}"):
            html(f"""<div class="top"><div class="item-name">{e(name)}</div><div class="price">{gbp(price)}</div></div>
            <div class="meta" style="margin-bottom:8px">Split: {who}</div>""")
            if is_member:
                mine = sh.get(me, 0)
                new = st.number_input("Your shares", min_value=0, max_value=50, value=mine, step=1, key=f"sh{iid}")
                if new != mine:
                    execute("""INSERT INTO shares VALUES (?,?,?)
                               ON CONFLICT(item_id, name) DO UPDATE SET count = excluded.count""",
                            (iid, me, int(new)))
                    st.rerun(scope="fragment")

    # ---- Split maths: each item's price divided by total shares ----
    owe = {n: 0.0 for n in members}
    total = unassigned = 0.0
    for iid, name, price in items:
        total += price
        sh = {n: c for n, c in shares.get(iid, {}).items() if c > 0 and n in owe}
        count = sum(sh.values())
        if not count:
            unassigned += price
            continue
        for n, c in sh.items():
            owe[n] += price * c / count
    back = sum(v for n, v in owe.items() if n != host)

    # ---- Receipt ----
    html('<div class="section">🧾 Who owes what</div>')
    rows = ""
    for n, paid in members.items():
        if n == host:
            tag, amount = '<span class="tag tag-host">Paid at till</span>', f"+{gbp(back)}"
        else:
            tag = '<span class="tag tag-ok">Paid</span>' if paid else '<span class="tag tag-wait">Pending</span>'
            amount = gbp(owe[n])
        rows += f'<div class="rrow"><span>{e(n)}{tag}</span><span>{amount}</span></div>'
    note = f'<div class="muted" style="padding-top:8px">{gbp(unassigned)} not claimed yet</div>' if unassigned else ""
    html(f"""<div class="receipt"><div class="rhead">CART POOL · SPLIT</div>{rows}
    <div class="rtotal"><span>Basket total</span><span>{gbp(total)}</span></div>{note}</div>""")

    # ---- Confirm payments (host only) ----
    unpaid = [n for n, p in members.items() if n != host and not p]
    if is_host and unpaid:
        html('<div class="section" style="font-size:15px">Confirm payments</div>')
        cols = st.columns(min(len(unpaid), 3))
        for i, n in enumerate(unpaid):
            if cols[i % len(cols)].button(f"✓ {n} paid", key=f"paid{n}", use_container_width=True):
                execute("UPDATE members SET paid = 1 WHERE run_id = ? AND name = ?", (rid, n))
                st.rerun(scope="fragment")

# =====================================================================
# ROUTER
# =====================================================================
view = st.session_state.get("view", "feed")
if view == "new":
    new_run()
elif view == "run" and st.session_state.get("rid"):
    run_page()
else:
    feed()