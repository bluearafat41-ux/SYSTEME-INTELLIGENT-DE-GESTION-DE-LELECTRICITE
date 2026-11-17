from flask import Flask, abort, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape as esc          # protège contre l'injection HTML
import secrets
import os
import re
import math
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SMART_ENERGY_SECRET",
    "smart-energy-monitor-local-dev-key-change-before-deployment")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

# ============================================================
# CONFIGURATION ET BASE DE DONNÉES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database" / "database.db"


def get_db():
    # timeout=20 : évite "database is locked" quand le simulateur écrit
    db = sqlite3.connect(DATABASE, timeout=20)
    db.row_factory = sqlite3.Row
    return db


def init_auth_db():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE, timeout=20) as db:
        db.execute("PRAGMA journal_mode=WAL")  # lecture + écriture simultanées
        db.execute("""
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                mot_de_passe TEXT NOT NULL,
                date_creation TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


init_auth_db()


def ecrire(sql, args=()):
    db = get_db()
    try:
        db.execute(sql, args)
        db.commit()
    finally:
        db.close()


def scalar(cur, sql, args=()):
    ligne = cur.execute(sql, args).fetchone()
    return ligne[0] if ligne and ligne[0] is not None else 0


# ============================================================
# ACCÈS : seules l'accueil, la connexion et l'inscription sont publiques
# ============================================================

PUBLIC_ENDPOINTS = {"home", "connexion", "inscription", "static"}


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def csrf_input():
    return f'<input type="hidden" name="csrf_token" value="{csrf_token()}">'


@app.before_request
def exiger_connexion():
    if request.endpoint is None or request.endpoint in PUBLIC_ENDPOINTS:
        return
    if not session.get("user_id"):
        return redirect(url_for("connexion", next=request.path, info=1))
    if request.method == "POST":
        envoye = request.form.get("csrf_token", "")
        if not secrets.compare_digest(envoye, session.get("csrf_token", "")):
            abort(400)


# ============================================================
# OUTILS
# ============================================================

def safe_float(value):
    if value is None:
        return 0
    return round(float(value), 4)


def format_date(date):
    if not date:
        return "-"
    try:
        return datetime.fromisoformat(str(date)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(date)


def json_data(data):
    # "</" échappé pour qu'une donnée ne puisse pas fermer la balise <script>
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def fill(tpl, **kw):
    """Remplace __CLE__ par la valeur (dans l'ordre des arguments)."""
    for k, v in kw.items():
        tpl = tpl.replace(f"__{k}__", str(v))
    return tpl


def stat(label, value, unit="", cls="", sub="", dec=0, sid=""):
    """Carte chiffre. Si value est un nombre, il est animé (compteur)."""
    if isinstance(value, (int, float)):
        idattr = f' id="{sid}"' if sid else ""
        v = f'<strong class="count" data-v="{value}" data-d="{dec}"{idattr}>0</strong>'
    else:
        v = f"<strong>{value}</strong>"
    u = f"<em>{unit}</em>" if unit else ""
    s = f'<span class="ss">{sub}</span>' if sub else ""
    return (f'<div class="stat rise {cls}"><small>{label}</small>'
            f'<div class="sv">{v}{u}</div>{s}</div>')


def header(tag, titre, texte):
    return (f'<div class="page-header rise"><div class="tag">{tag}</div>'
            f'<h1>{titre}</h1><p>{texte}</p></div>')


def badge_niveau(niveau):
    n = str(niveau or "INFO").upper()
    if n == "TRÈS ÉLEVÉ":
        return f'<span class="badge badge-red">{esc(n)}</span>'
    if n == "ÉLEVÉ":
        return f'<span class="badge badge-orange">{esc(n)}</span>'
    return f'<span class="badge badge-green">{esc(n)}</span>'


def live_stats(cur):
    return {
        "energie": safe_float(scalar(cur, "SELECT COALESCE(SUM(energie),0) FROM consommations")),
        "puissance": safe_float(scalar(cur, """
            SELECT COALESCE(SUM(puissance),0) FROM consommations
            WHERE date_heure = (SELECT MAX(date_heure) FROM consommations)""")),
        "alertes_actives": scalar(cur, "SELECT COUNT(*) FROM alertes WHERE UPPER(statut)='ACTIVE'"),
        "optim_attente": scalar(cur, "SELECT COUNT(*) FROM optimisations WHERE UPPER(statut)='EN ATTENTE'"),
        "derniere": format_date(scalar(cur, "SELECT MAX(date_heure) FROM consommations") or None),
    }


@app.route("/api/live")
def api_live():
    db = get_db()
    try:
        return jsonify(live_stats(db.cursor()))
    finally:
        db.close()


# ============================================================
# STYLE (chaîne simple : pas besoin de doubler les accolades)
# ============================================================

CSS = """
:root{--bg:#f2f8f7;--card:#fff;--ink:#153b37;--muted:#718985;--line:#dcebe8;--accent:#168b83;--accent2:#0f766e;--soft:#e4f5f2;--shadow:0 13px 34px rgba(18,82,75,.08)}
body.dark{--bg:#071311;--card:#10201e;--ink:#e2f4ef;--muted:#a0bdb6;--line:#24433e;--accent2:#5fd0bc;--soft:#153b36;--shadow:0 13px 34px rgba(0,0,0,.35)}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:"Segoe UI",Arial,sans-serif;color:var(--ink);min-height:100vh;
 background:radial-gradient(circle at 82% 8%,rgba(22,139,131,.11),transparent 27%),radial-gradient(circle at 12% 86%,rgba(72,175,154,.08),transparent 25%),var(--bg)}
a{color:var(--accent2)}
/* ---- sidebar ---- */
.navbar{position:fixed;left:18px;top:18px;bottom:18px;width:248px;padding:22px 15px;border-radius:24px;display:flex;flex-direction:column;gap:28px;overflow-y:auto;background:linear-gradient(165deg,#103d3a,#0d514b 55%,#12645a);box-shadow:0 22px 60px rgba(11,67,62,.22);z-index:100}
.logo{display:flex;align-items:center;gap:11px;text-decoration:none;color:#fff;font-weight:850;font-size:16px;line-height:1.35}
.logo b{color:#9ce6d8}
.logo-icon{width:43px;height:43px;border-radius:14px;background:linear-gradient(135deg,#39b8a5,#168b83);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:900;flex-shrink:0}
.menu{display:flex;flex-direction:column;gap:7px}
.menu a{display:flex;align-items:center;gap:12px;text-decoration:none;color:#d1e9e4;font-size:13px;font-weight:700;padding:11px 12px;border-radius:13px;transition:.2s}
.menu a:hover{background:rgba(143,232,214,.13);color:#fff;transform:translateX(3px)}
.menu a.active{background:linear-gradient(110deg,#e5fbf5,#c9f2e8);color:#0e5149}
.nav-mark{width:30px;height:30px;flex:0 0 30px;display:inline-flex;align-items:center;justify-content:center;border-radius:9px;font-size:9px;font-weight:900;color:#a8ded3;background:rgba(255,255,255,.09)}
.menu a.active .nav-mark{color:#0f766e;background:rgba(22,139,131,.12)}
.clock-container{margin-top:auto;display:flex;align-items:center;gap:10px;padding:10px 13px;border-radius:15px;background:rgba(255,255,255,.10);color:#fff}
.clock{font-weight:850;font-size:15px;color:#fff}
.live-dot{width:8px;height:8px;background:#70e3b7;border-radius:50%;box-shadow:0 0 0 5px rgba(112,227,183,.15);animation:pulse 2s infinite}
@keyframes pulse{50%{opacity:.4}}
.container{margin:28px 30px 40px 292px}
footer{margin-left:280px;padding:20px;text-align:center;color:var(--muted);font-size:11px}
/* ---- barre du haut ---- */
.top-toolbar{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:24px;padding:15px 18px;background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}
.toolbar-left{display:flex;flex-direction:column;gap:3px}.toolbar-left strong{font-size:18px}
.toolbar-kicker{font-size:9px;letter-spacing:1.5px;color:var(--accent);font-weight:900}
.toolbar-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.toolbar-button{border:1px solid var(--line);background:var(--soft);color:var(--accent2);padding:10px 13px;border-radius:11px;font-weight:800;font-size:12px;text-decoration:none;cursor:pointer;font-family:inherit}
.signup-link{background:linear-gradient(135deg,#168b83,#26a997);color:#fff;border-color:transparent}
.logout-link{color:#c24141}
.translate-hidden{display:none!important}
/* ---- titres ---- */
.page-header{margin:6px 0 24px}
.tag{display:inline-block;padding:7px 11px;border-radius:20px;background:var(--soft);color:var(--accent2);font-size:10px;font-weight:850;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px}
.page-header h1{font-size:clamp(28px,4vw,44px);letter-spacing:-1.5px;line-height:1.05}
.page-header p{margin-top:10px;color:var(--muted);font-size:14px;line-height:1.6;max-width:720px}
.section-title{margin:34px 2px 16px}.section-title h2{font-size:22px}.section-title p{color:var(--muted);font-size:12px;margin-top:4px}
/* ---- grilles ---- */
.grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:16px 0}
/* ---- cartes ---- */
.card,.chart-card,.table-card,.stat,.feat,.room-card{background:var(--card);border:1px solid var(--line);border-radius:22px;box-shadow:var(--shadow)}
.card,.chart-card{padding:24px}.table-card{padding:20px;overflow-x:auto}
.card h3,.chart-card h3{font-size:17px}.card>p,.chart-card>p{color:var(--muted);font-size:12px;margin:4px 0 16px;line-height:1.6}
.chart-container{position:relative;height:275px}
.stat{position:relative;overflow:hidden;padding:18px;transition:transform .25s,box-shadow .25s}
.stat:hover,.feat:hover,.room-card:hover,.floor-button:hover{transform:translateY(-7px);box-shadow:0 22px 44px rgba(14,95,85,.16)}
.stat::after{content:"";position:absolute;left:-60%;top:0;width:40%;height:100%;background:linear-gradient(100deg,transparent,rgba(22,139,131,.13),transparent);animation:shine 4.5s infinite}
@keyframes shine{to{left:130%}}
.stat small{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.6px;font-weight:800;color:var(--muted)}
.sv{display:flex;align-items:baseline;gap:6px;margin-top:6px}.sv strong{font-size:28px;letter-spacing:-1px}.sv em{font-style:normal;font-size:12px;color:var(--muted)}
.ss{display:block;margin-top:6px;font-size:11px;color:var(--muted)}
.stat.warn strong{color:#d97706}.stat.bad strong{color:#dc2626}.stat.ok strong{color:var(--accent2)}
/* ---- animations ---- */
.rise{opacity:0;transform:translateY(20px);animation:rise .8s cubic-bezier(.2,.8,.2,1) forwards;animation-delay:var(--d,0s)}
@keyframes rise{to{opacity:1;transform:none}}
.grid-4>*:nth-child(2),.grid-3>*:nth-child(2){--d:.1s}.grid-4>*:nth-child(3),.grid-3>*:nth-child(3){--d:.2s}.grid-4>*:nth-child(4){--d:.3s}
.feats>*:nth-child(2){--d:.1s}.feats>*:nth-child(3){--d:.2s}.feats>*:nth-child(4){--d:.3s}.feats>*:nth-child(5){--d:.4s}.feats>*:nth-child(6){--d:.5s}
@keyframes bob{50%{transform:translateY(-8px) rotate(4deg)}}
/* ---- hero ---- */
.hero{position:relative;overflow:hidden;border-radius:28px;padding:34px;display:flex;align-items:center;justify-content:space-between;gap:20px;color:#eafbf7;background:linear-gradient(120deg,#0d4a45,#14796d,#1c9a86,#0d4a45);background-size:300% 300%;animation:bgmove 12s ease infinite;box-shadow:0 24px 60px rgba(14,95,85,.22)}
@keyframes bgmove{0%,100%{background-position:0 50%}50%{background-position:100% 50%}}
.hero h1{font-size:clamp(28px,3.6vw,46px);letter-spacing:-1.5px;line-height:1.05;margin:14px 0 10px;color:#fff}
.hero p{max-width:620px;color:#cdeee6;font-size:14px;line-height:1.65}
.hero .g{color:#9af0d0}
.pill{display:inline-flex;align-items:center;gap:8px;padding:7px 12px;border-radius:20px;background:rgba(255,255,255,.13);font-size:11px;font-weight:800}
.pill i{width:8px;height:8px;border-radius:50%;background:#70e3b7;animation:ping 1.8s infinite}
@keyframes ping{0%{box-shadow:0 0 0 0 rgba(112,227,183,.7)}100%{box-shadow:0 0 0 12px rgba(112,227,183,0)}}
.orbs{position:relative;width:150px;height:150px;flex-shrink:0}
.orbs span{position:absolute;inset:0;border-radius:50%;border:1.5px solid rgba(255,255,255,.35);animation:orb 3.6s ease-out infinite}
.orbs span:nth-child(2){animation-delay:1.2s}.orbs span:nth-child(3){animation-delay:2.4s}
@keyframes orb{0%{transform:scale(.35);opacity:.9}100%{transform:scale(1.15);opacity:0}}
.orbs b{position:absolute;inset:38px;border-radius:26px;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:20px;animation:bob 3s ease-in-out infinite}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.hbtn{display:inline-block;padding:12px 20px;border-radius:13px;font-weight:850;text-decoration:none;font-size:13px;transition:transform .2s}
.hbtn:hover{transform:translateY(-3px)}.hbtn.primary{background:#fff;color:#0f766e}.hbtn.ghost{border:1px solid rgba(255,255,255,.55);color:#fff}
/* ---- pipeline ---- */
.main2{display:grid;grid-template-columns:1.6fr 1fr;gap:16px;margin-top:6px}
.track{position:relative;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding-top:6px}
.line{position:absolute;left:12%;right:12%;top:34px;height:3px;border-radius:3px;background:var(--line)}
.line i{position:absolute;top:-3px;left:0;width:9px;height:9px;border-radius:50%;background:#16a89a;box-shadow:0 0 12px #16a89a;animation:run 4s linear infinite}
.line i:nth-child(2){animation-delay:-1.3s}.line i:nth-child(3){animation-delay:-2.6s}
@keyframes run{0%{left:0;opacity:0}10%,90%{opacity:1}100%{left:100%;opacity:0}}
.node{position:relative;text-align:center;z-index:1}
.ico{width:56px;height:56px;margin:0 auto 10px;border-radius:18px;display:flex;align-items:center;justify-content:center;font-weight:900;color:var(--accent2);background:var(--soft);border:2px solid var(--line);animation:glow 6s infinite;animation-delay:var(--d)}
@keyframes glow{0%,20%,100%{transform:scale(1);background:var(--soft);color:var(--accent2)}6%,14%{transform:scale(1.18);background:#16a89a;color:#fff;box-shadow:0 0 0 8px rgba(22,168,154,.15)}}
.node h4{font-size:13px}.node span{display:block;margin-top:3px;font-size:11px;color:var(--muted)}
/* ---- jauges ---- */
.gauge{margin:12px 0}.gauge div.t{display:flex;justify-content:space-between;font-size:12px;font-weight:700;margin-bottom:5px}
.bar{height:10px;border-radius:10px;background:var(--line);overflow:hidden}
.bar i{display:block;height:100%;width:0;border-radius:10px;animation:fillbar 2s ease-out forwards,breathe 3s ease-in-out 2s infinite}
@keyframes fillbar{to{width:var(--w)}}@keyframes breathe{50%{filter:brightness(1.25)}}
/* ---- fonctionnalités ---- */
.feats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.feat{display:block;padding:20px;text-decoration:none;color:var(--ink);transition:transform .25s,box-shadow .25s;animation:rise .8s forwards,floaty 6s ease-in-out infinite;animation-delay:var(--d,0s),var(--d,0s);opacity:0}
@keyframes floaty{50%{translate:0 -4px}}
.feat .fi{width:46px;height:46px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:900;color:#fff;background:linear-gradient(135deg,#168b83,#39b8a5);margin-bottom:14px;animation:bob 4s ease-in-out infinite}
.feat h3{font-size:15px;margin-bottom:6px}.feat p{font-size:12px;color:var(--muted);line-height:1.6}
/* ---- tableaux ---- */
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;color:var(--muted);font-size:10px;text-transform:uppercase;padding:12px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:13px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:hover td{background:var(--soft)}
.badge{display:inline-block;padding:6px 9px;border-radius:15px;font-size:9px;font-weight:850;white-space:nowrap}
.badge-red{background:#fff0f0;color:#dc2626}.badge-green{background:#eaf8ee;color:#15803d}.badge-orange{background:#fff5e6;color:#d97706}
body.dark .badge-red{background:#3a1717}body.dark .badge-green{background:#123221}body.dark .badge-orange{background:#3a2a10}
.btn{border:0;border-radius:10px;padding:8px 12px;font-weight:800;font-size:12px;cursor:pointer;background:linear-gradient(135deg,#168b83,#26a997);color:#fff;text-decoration:none;display:inline-block;font-family:inherit;transition:transform .2s}
.btn:hover{transform:translateY(-2px)}.btn.light{background:var(--soft);color:var(--accent2)}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 16px}
.tabs a{padding:9px 14px;border-radius:11px;font-size:12px;font-weight:800;text-decoration:none;background:var(--soft);color:var(--accent2)}
.tabs a.on{background:var(--accent);color:#fff}
.notice{padding:12px 16px;border-radius:12px;background:var(--soft);color:var(--accent2);font-weight:700;font-size:13px;margin-bottom:16px}
.pager{display:flex;justify-content:center;align-items:center;gap:14px;margin-top:16px;font-size:12px}
small.mut{color:var(--muted)}
/* ---- bâtiment ---- */
.building-layout{display:grid;grid-template-columns:minmax(270px,.9fr) minmax(320px,1.1fr);gap:22px;align-items:start}
.building-visual{background:linear-gradient(145deg,#103f3b,#16786d);color:#fff;border-radius:24px;padding:25px;box-shadow:var(--shadow)}
.building-3d{width:100%;height:390px;border-radius:18px;overflow:hidden;background:#0f3f3a;cursor:grab;margin-top:14px}
.building-3d canvas{display:block;width:100%;height:100%}
.three-loading{padding:35px;color:#d1ead9}.three-help{font-size:11px;color:#c7e8d1;margin:10px 0 14px}
.fb3d{width:100%;height:100%}.fb3d rect{fill:#b9e5c7;stroke:#17643e;stroke-width:2;transition:.2s;cursor:pointer}.fb3d rect.sel,.fb3d a:hover rect{fill:#38d9b0}.fb3d text{fill:#0e3d2c;font-weight:800;font-size:15px;pointer-events:none}
.floor-list{display:grid;gap:10px;margin-top:18px}
.floor-button{display:flex;justify-content:space-between;align-items:center;gap:12px;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:16px 18px;border-radius:16px;text-decoration:none;font-weight:750;transition:.2s}
.floor-button.selected{border-color:#38a99a;background:var(--soft)}
.floor-badge{border-radius:10px;padding:6px 9px;background:var(--soft);color:var(--accent2);font-size:11px}
.room-card{display:block;padding:20px;text-decoration:none;color:var(--ink);transition:transform .25s,box-shadow .25s}
.room-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.room-icon{width:45px;height:45px;border-radius:14px;background:var(--soft);color:var(--accent2);display:flex;align-items:center;justify-content:center}
.status-normal{color:var(--accent2);background:var(--soft);padding:6px 9px;border-radius:20px;font-size:9px;font-weight:850}
.room-card h3{font-size:14px;margin-bottom:5px}.location{color:var(--muted);font-size:10px}
.room-consumption{border-top:1px solid var(--line);margin-top:15px;padding-top:12px}.room-consumption small{color:var(--muted);font-size:10px}.room-consumption strong{display:block;color:var(--accent2);font-size:19px;margin-top:3px}
/* ---- comptes ---- */
.auth-wrap{max-width:520px;margin:20px auto;background:var(--card);border:1px solid var(--line);border-radius:24px;padding:30px;box-shadow:var(--shadow)}
.auth-wrap .page-header{margin-top:0}
.auth-form{display:grid;gap:14px}.auth-form label{font-size:12px;font-weight:800}
.auth-form input,select{width:100%;padding:13px;border:1px solid var(--line);border-radius:11px;margin-top:6px;font:inherit;background:var(--card);color:var(--ink)}
.auth-form button{border:0;background:linear-gradient(135deg,#168b83,#26a997);color:#fff;padding:14px;border-radius:12px;font-weight:900;cursor:pointer}
.auth-message{padding:12px;border-radius:10px;background:#fff4e5;color:#86520b;margin:12px 0;font-size:13px}
.language-select{width:auto;margin:0}
/* ---- carte flottante ---- */
.floating-insight{position:fixed;right:26px;bottom:24px;z-index:80;width:250px;padding:15px 17px 12px;border-radius:19px;color:#eafbf7;background:linear-gradient(145deg,rgba(13,66,61,.96),rgba(17,112,100,.94));box-shadow:0 20px 55px rgba(10,70,64,.24);animation:floaty2 5.5s ease-in-out infinite}
@keyframes floaty2{50%{transform:translateY(-7px)}}
.fi-head{display:flex;align-items:center;gap:8px;color:#a9e8dc;font-size:8px;font-weight:900;letter-spacing:1.3px}
.fi-dot{width:7px;height:7px;border-radius:50%;background:#70e3b7}
.floating-insight>strong{display:block;margin-top:11px;font-size:14px;color:#fff}
.floating-insight p{margin-top:5px;color:#c1e4dc;font-size:10px;line-height:1.55}
.fi-clock{display:block;margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,.13);font-size:10px;color:#fff}
/* ---- responsive ---- */
@media(max-width:1100px){.grid-4,.feats{grid-template-columns:repeat(2,1fr)}.main2,.building-layout{grid-template-columns:1fr}.grid-3{grid-template-columns:1fr 1fr}}
@media(max-width:900px){.navbar{position:relative;inset:auto;width:calc(100% - 24px);margin:12px;padding:15px;gap:14px}.menu{display:grid;grid-template-columns:repeat(2,1fr)}.container{margin:20px 12px 40px}footer{margin-left:0}.hero .orbs{display:none}.floating-insight{display:none}}
@media(max-width:650px){.grid-2,.grid-3,.grid-4,.feats,.track{grid-template-columns:1fr}.line{display:none}.top-toolbar{flex-direction:column;align-items:flex-start}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}.rise,.feat{opacity:1;transform:none}.bar i{width:var(--w)}}
/* ============================================================
   AJOUT : diagrammes explicatifs animés (classes préfixées dg-)
   ============================================================ */
.dg-card{margin:18px 0}
.dg-flow{display:grid;grid-template-columns:minmax(0,1fr) 46px minmax(0,1fr) 46px minmax(0,1fr) 46px minmax(0,1fr);align-items:stretch;gap:10px;margin-top:8px}
.dg-step{position:relative;background:var(--soft);border:1px solid var(--line);border-radius:18px;padding:20px 14px 16px;text-align:center;transition:transform .25s;animation:dgstep 8s ease-in-out infinite;animation-delay:var(--d,0s)}
.dg-step:hover{transform:translateY(-6px)}
@keyframes dgstep{0%,28%,100%{border-color:var(--line);box-shadow:0 0 0 0 rgba(22,168,154,0)}4%,22%{border-color:#16a89a;box-shadow:0 0 0 6px rgba(22,168,154,.14)}}
.dg-num{position:absolute;top:10px;left:13px;font-size:10px;font-weight:900;color:var(--accent2);opacity:.75}
.dg-ico{width:64px;height:64px;margin:4px auto 12px;border-radius:20px;background:var(--card);border:2px solid var(--line);display:flex;align-items:center;justify-content:center;color:var(--accent2)}
.dg-ico svg{width:34px;height:34px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;overflow:visible}
.dg-step h4{font-size:13px;margin-bottom:6px}
.dg-step p{font-size:11px;color:var(--muted);line-height:1.55}
.dg-tag{display:inline-block;margin-top:10px;padding:5px 9px;border-radius:14px;font-size:9px;font-weight:850;background:var(--card);color:var(--accent2);border:1px solid var(--line)}
.dg-arrow{position:relative;width:100%;align-self:center;height:3px;background:var(--line);border-radius:3px}
.dg-arrow::after{content:"";position:absolute;right:-2px;top:-4px;border-left:9px solid var(--line);border-top:5.5px solid transparent;border-bottom:5.5px solid transparent}
.dg-arrow i{position:absolute;top:-3px;left:0;width:9px;height:9px;border-radius:50%;background:#16a89a;box-shadow:0 0 10px #16a89a;animation:dgrun 2.4s linear infinite;animation-delay:var(--d,0s)}
@keyframes dgrun{0%{left:0;opacity:0}15%,85%{opacity:1}100%{left:calc(100% - 9px);opacity:0}}
@keyframes dgrunv{0%{top:0;opacity:0}15%,85%{opacity:1}100%{top:calc(100% - 9px);opacity:0}}
.dg-foot{display:flex;align-items:center;gap:10px;margin-top:16px;padding:11px 14px;border-radius:12px;background:var(--soft);color:var(--accent2);font-size:12px;font-weight:700;line-height:1.5}
.dg-foot i{flex:0 0 8px;width:8px;height:8px;border-radius:50%;background:#16a89a;animation:ping 1.8s infinite}
/* animations des icônes : une animation différente par carte */
.dg-ring{transform-box:fill-box;transform-origin:center;animation:dgring 2.2s ease-out infinite}
.dg-ring.r2{animation-delay:1.1s}
@keyframes dgring{0%{transform:scale(.3);opacity:.9}100%{transform:scale(1.7);opacity:0}}
.dg-scanline{animation:dgscan 2.4s ease-in-out infinite alternate}
@keyframes dgscan{from{transform:translateY(0)}to{transform:translateY(11px)}}
.dg-bell{transform-origin:12px 3px;animation:dgbell 2s ease-in-out infinite}
@keyframes dgbell{0%,50%,100%{transform:rotate(0)}10%{transform:rotate(14deg)}20%{transform:rotate(-12deg)}30%{transform:rotate(8deg)}40%{transform:rotate(-5deg)}}
.dg-blink{animation:dgblink 1.2s steps(2,start) infinite}
@keyframes dgblink{to{visibility:hidden}}
.dg-flicker{animation:dgflick 1.6s infinite}
@keyframes dgflick{0%,100%{opacity:1}45%{opacity:.3}50%{opacity:1}70%{opacity:.5}}
.dg-bar{fill:currentColor;stroke:none;transform-box:fill-box;transform-origin:50% 100%;animation:dgbar 2s ease-in-out infinite}
.dg-bar.b2{animation-delay:.3s}.dg-bar.b3{animation-delay:.6s}
@keyframes dgbar{0%,100%{transform:scaleY(.45)}50%{transform:scaleY(1)}}
.dg-glowing{fill:currentColor;fill-opacity:.1;animation:dgglow 2s ease-in-out infinite}
@keyframes dgglow{50%{fill-opacity:.55}}
.dg-draw{stroke-dasharray:22;stroke-dashoffset:22;animation:dgdraw 2.4s ease-in-out infinite}
@keyframes dgdraw{0%{stroke-dashoffset:22}40%,80%{stroke-dashoffset:0}100%{stroke-dashoffset:22}}
.dg-bob{animation:dgbob 2s ease-in-out infinite}
@keyframes dgbob{50%{transform:translateY(-2.5px)}}
.dg-needle{transform-origin:12px 17px;animation:dgneedle 2.4s ease-in-out infinite alternate}
@keyframes dgneedle{from{transform:rotate(-55deg)}to{transform:rotate(55deg)}}
.dg-drop{fill:currentColor;stroke:none;animation:dgdrop 1.8s ease-in infinite}
@keyframes dgdrop{0%{transform:translateY(0);opacity:0}20%{opacity:1}100%{transform:translateY(8px);opacity:0}}
/* diagrammes : adaptation aux petits écrans (étapes empilées, flèches verticales) */
@media(max-width:1180px){
.dg-flow{grid-template-columns:1fr;gap:6px}
.dg-step{display:grid;grid-template-columns:64px minmax(0,1fr);gap:0 16px;align-items:center;text-align:left;padding:16px}
.dg-ico{margin:0}
.dg-num{top:8px;left:auto;right:14px}
.dg-arrow{width:3px;height:30px;justify-self:center}
.dg-arrow::after{right:auto;left:-4px;top:auto;bottom:-2px;border-left:5.5px solid transparent;border-right:5.5px solid transparent;border-top:9px solid var(--line);border-bottom:0}
.dg-arrow i{left:-3px;top:0;animation-name:dgrunv}
}
@media(max-width:650px){.dg-step{grid-template-columns:52px minmax(0,1fr);gap:0 12px}.dg-ico{width:52px;height:52px}.dg-ico svg{width:28px;height:28px}}
"""

LAYOUT = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ — Smart Energy Monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>__CSS__</style>
</head>
<body>
<nav class="navbar">
  <a href="/" class="logo"><div class="logo-icon">SE</div><span>Smart <b>Energy</b><br>Monitor</span></a>
  <div class="menu">__MENU__</div>
  <div class="clock-container"><div class="live-dot"></div><div><div id="clock" class="clock">--:--:--</div><small style="color:#c5e6d1">Système en direct</small></div></div>
</nav>
<main class="container">
  <div class="top-toolbar">
    <div class="toolbar-left"><span class="toolbar-kicker">ESPACE DE GESTION</span><strong>__TITLE__</strong></div>
    <div class="toolbar-actions">
      <button class="toolbar-button" id="themeToggle" type="button">Mode sombre</button>
      <select class="toolbar-button language-select" id="languageSelect" aria-label="Langue"><option value="fr">FR</option><option value="en">EN</option><option value="ar">AR</option><option value="so">SO</option><option value="es">ES</option><option value="zh-CN">中文</option></select>
      __AUTH__
    </div>
  </div>
  <div id="google_translate_element" class="translate-hidden"></div>
  <aside class="floating-insight">
    <div class="fi-head"><span class="fi-dot"></span><span>SUIVI ÉNERGÉTIQUE · LIVE</span></div>
    <strong>__TITLE__</strong><p>__NOTE__</p><span class="fi-clock" id="floatingClock">--:--</span>
  </aside>
  __CONTENT__
</main>
<footer>Smart Energy Monitor — Système intelligent de gestion de l'électricité</footer>
<script>
var PAL=["#168b83","#26a997","#5fd0bc","#0f766e","#7cc8d8","#f59e0b","#6366f1","#ef4444"];
function tick(){var n=new Date(),h=String(n.getHours()).padStart(2,"0"),m=String(n.getMinutes()).padStart(2,"0"),s=String(n.getSeconds()).padStart(2,"0");
 var c=document.getElementById("clock");if(c)c.textContent=h+":"+m+":"+s;var f=document.getElementById("floatingClock");if(f)f.textContent=h+":"+m}
tick();setInterval(tick,1000);

/* compteurs animés */
function animate(el,to,dec,dur){var from=parseFloat(el.textContent)||0,t0=performance.now();
 (function step(t){var p=Math.min((t-t0)/dur,1),e=1-Math.pow(1-p,3);el.textContent=(from+(to-from)*e).toFixed(dec);if(p<1)requestAnimationFrame(step)})(t0)}
window.setCount=function(id,v,d){var e=document.getElementById(id);if(e)animate(e,v,d||0,800)};
document.querySelectorAll(".count").forEach(function(e){animate(e,parseFloat(e.dataset.v)||0,parseInt(e.dataset.d)||0,1200)});

/* thème */
(function(){
 var body=document.body,toggle=document.getElementById("themeToggle"),mode="light";
 try{mode=localStorage.getItem("sem-theme")||"light"}catch(e){}
 function apply(v){body.classList.toggle("dark",v==="dark");if(toggle)toggle.textContent=v==="dark"?"Mode clair":"Mode sombre";
  try{localStorage.setItem("sem-theme",v)}catch(e){}
  if(window.Chart){Chart.defaults.color=v==="dark"?"#d7e9dc":"#66766b";Chart.defaults.borderColor=v==="dark"?"#294943":"#e4ece6";
   document.querySelectorAll("canvas").forEach(function(c){var ch=Chart.getChart(c);if(ch)ch.update()})}}
 apply(mode);if(toggle)toggle.addEventListener("click",function(){apply(body.classList.contains("dark")?"light":"dark")});
 var lang=document.getElementById("languageSelect");
 if(lang)lang.addEventListener("change",function(){var v=lang.value;(function w(){var c=document.querySelector(".goog-te-combo");if(c){c.value=v;c.dispatchEvent(new Event("change"))}else setTimeout(w,400)})()});
})();
function googleTranslateElementInit(){if(window.google&&google.translate){new google.translate.TranslateElement({pageLanguage:"fr",includedLanguages:"en,ar,so,es,zh-CN",autoDisplay:false},"google_translate_element")}}
</script>
<script src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit" defer></script>
</body>
</html>
"""

PAGE_NOTES = {
    "home": "Indicateurs globaux et état général de la plateforme.",
    "batiment": "Vue des étages, des salles et de leur consommation.",
    "historique": "Suivi chronologique des mesures enregistrées.",
    "comparaisons": "Comparaison des consommations par salle et équipement.",
    "alertes": "Anomalies énergétiques détectées et à traiter.",
    "optimisations": "Recommandations associées aux alertes détectées.",
}

MENU = [
    ("home", "/", "01", "Accueil"),
    ("batiment", "/batiment", "02", "Bâtiment"),
    ("historique", "/historique", "03", "Historique"),
    ("comparaisons", "/comparaisons", "04", "Comparaisons"),
    ("alertes", "/alertes", "05", "Alertes"),
    ("optimisations", "/optimisations", "06", "Optimisations"),
]


def page_template(title, content, active="home"):
    connecte = bool(session.get("user_id"))
    menu = ""
    for key, href, mark, label in MENU:
        if not connecte and key != "home":
            continue
        cls = "active" if key == active else ""
        menu += f'<a href="{href}" class="{cls}"><span class="nav-mark">{mark}</span> {label}</a>'
    if connecte:
        auth = ('<a class="toolbar-button" href="/compte">Mon compte</a>'
                '<a class="toolbar-button logout-link" href="/deconnexion">Déconnexion</a>')
    else:
        auth = ('<a class="toolbar-button" href="/connexion">Connexion</a>'
                '<a class="toolbar-button signup-link" href="/inscription">Inscription</a>')
    return fill(LAYOUT, TITLE=esc(title), CSS=CSS, MENU=menu, AUTH=auth,
                NOTE=PAGE_NOTES.get(active, "Espace de gestion Smart Energy Monitor."),
                CONTENT=content)


# ============================================================
# AJOUT : DIAGRAMMES EXPLICATIFS ANIMÉS (alertes, optimisations, salle)
# ============================================================

# Icônes SVG (viewBox 24x24). Chaque classe dg-* porte sa propre animation (voir CSS).
DG_ICONS = {
    "radar": ('<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" opacity=".35"/>'
              '<circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/>'
              '<circle class="dg-ring" cx="12" cy="12" r="6"/>'
              '<circle class="dg-ring r2" cx="12" cy="12" r="6"/></svg>'),
    "scan": ('<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="3"/>'
             '<path d="M7 17v-3M12 17V10M17 17v-5"/>'
             '<line class="dg-scanline" x1="5" y1="6" x2="19" y2="6" stroke-width="2.2"/></svg>'),
    "bell": ('<svg viewBox="0 0 24 24"><g class="dg-bell"><path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15z"/>'
             '<path d="M10 20.5a2 2 0 0 0 4 0"/></g></svg>'),
    "screen": ('<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/>'
               '<path d="M8 20h8M12 16v4"/><path class="dg-blink" d="M7 10h6" stroke-width="2.4"/></svg>'),
    "bolt": ('<svg viewBox="0 0 24 24"><path class="dg-flicker" d="M13 2 5 14h6l-1 8 8-12h-6z"/></svg>'),
    "chart": ('<svg viewBox="0 0 24 24"><path d="M4 20h16"/>'
              '<rect class="dg-bar b1" x="6" y="11" width="3" height="9" rx="1"/>'
              '<rect class="dg-bar b2" x="10.5" y="5" width="3" height="15" rx="1"/>'
              '<rect class="dg-bar b3" x="15" y="8" width="3" height="12" rx="1"/></svg>'),
    "bulb": ('<svg viewBox="0 0 24 24"><path d="M9 18h6M10 21h4"/>'
             '<path class="dg-glowing" d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/></svg>'),
    "check": ('<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/>'
              '<path class="dg-draw" d="M7.5 12.5l3 3 6-6.5"/></svg>'),
    "plug": ('<svg viewBox="0 0 24 24"><g class="dg-bob"><path d="M9 3v4M15 3v4"/>'
             '<path d="M6 7h12v4a6 6 0 0 1-12 0z"/><path d="M12 17v4"/></g></svg>'),
    "gauge": ('<svg viewBox="0 0 24 24"><path d="M4 17a8 8 0 0 1 16 0"/>'
              '<line class="dg-needle" x1="12" y1="17" x2="12" y2="8" stroke-width="2.2"/>'
              '<circle cx="12" cy="17" r="1.6" fill="currentColor" stroke="none"/></svg>'),
    "database": ('<svg viewBox="0 0 24 24"><ellipse cx="12" cy="6" rx="7" ry="3"/>'
                 '<path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>'
                 '<circle class="dg-drop" cx="12" cy="1" r="1.3"/></svg>'),
}


def diagramme_html(did, titre, texte, etapes, pied=""):
    """Diagramme en 4 étapes reliées par des flèches animées.
    etapes = [(icone, titre, description, étiquette), ...]"""
    out = (f'<div class="card dg-card rise" id="{did}"><h3>{titre}</h3><p>{texte}</p>'
           '<div class="dg-flow">')
    for i, (icone, nom, desc, tag) in enumerate(etapes):
        if i:
            out += f'<div class="dg-arrow" style="--d:{(i - 1) * 0.6:.1f}s"><i></i></div>'
        out += (f'<div class="dg-step" style="--d:{i * 2}s"><span class="dg-num">0{i + 1}</span>'
                f'<div class="dg-ico">{DG_ICONS[icone]}</div>'
                f'<div class="dg-body"><h4>{nom}</h4><p>{desc}</p><span class="dg-tag">{tag}</span></div></div>')
    out += '</div>'
    if pied:
        out += f'<div class="dg-foot"><i></i><span>{pied}</span></div>'
    return out + '</div>'


def diagramme_alertes():
    return diagramme_html(
        "dgAlertes", "Fonctionnement du système d'alertes",
        "Le parcours complet d'une anomalie, de la mesure de l'équipement jusqu'à l'alerte visible dans l'interface.",
        [("radar", "Détection d'une anomalie",
          "Une mesure de puissance est enregistrée toutes les 2 minutes pour chaque équipement.",
          "Mesure en continu"),
         ("scan", "Analyse",
          "Toutes les 10 minutes, les mesures récentes sont comparées à la puissance normale de l'équipement.",
          "Seuil : 120 %"),
         ("bell", "Création de l'alerte",
          "Si le seuil est dépassé, une alerte est enregistrée : ÉLEVÉ au-delà de 120 %, TRÈS ÉLEVÉ à partir de 180 %.",
          "Statut : ACTIVE"),
         ("screen", "Affichage dans l'interface",
          "L'alerte apparaît dans la liste et dans les compteurs. Le bouton « Traiter » la passe en TRAITÉE.",
          "Page Alertes")],
        "Le cycle est continu : une nouvelle alerte peut être créée si l'anomalie revient après traitement.")


def diagramme_optimisations():
    return diagramme_html(
        "dgOptimisations", "Processus d'optimisation",
        "Comment une consommation excessive devient une recommandation concrète, puis une action suivie.",
        [("bolt", "Détection d'une consommation excessive",
          "Une alerte signale qu'un équipement dépasse sa puissance normale (plus de 120 %).",
          "Source : alerte"),
         ("chart", "Analyse",
          "Le système identifie le type d'équipement concerné (climatiseur, éclairage…) et la gravité de l'alerte.",
          "Équipement + gravité"),
         ("bulb", "Proposition d'optimisation",
          "Un conseil adapté est créé avec un gain estimé : 10 % pour une alerte ÉLEVÉE, 20 % pour une alerte TRÈS ÉLEVÉE.",
          "Statut : EN ATTENTE"),
         ("check", "Application et suivi",
          "Une fois l'action réalisée, « Appliquer » passe la recommandation en APPLIQUÉE pour suivre l'avancement.",
          "Statut : APPLIQUÉE")],
        "Chaque recommandation reste liée à l'alerte d'origine, ce qui permet de suivre son avancement.")


def diagramme_salle(nb_equipements=0):
    return diagramme_html(
        "dgSalle", "Consommation électrique et suivi de la salle",
        "Comment les équipements de cette salle consomment de l'électricité et comment le système en assure le suivi.",
        [("plug", "Équipements de la salle",
          f"{int(nb_equipements)} équipement(s) branché(s) dans cette salle, chacun avec sa puissance normale en kW.",
          "Puissance (kW)"),
         ("gauge", "Mesure",
          "Toutes les 2 minutes, la puissance de chaque équipement est mesurée. L'énergie est la puissance multipliée par la durée.",
          "Énergie (kWh)"),
         ("database", "Enregistrement",
          "Chaque mesure est enregistrée avec sa date, son équipement et sa salle, puis regroupée pour les graphiques.",
          "Historique"),
         ("chart", "Suivi par le système",
          "Les mesures sont comparées au seuil de 120 % : un dépassement déclenche une alerte, puis une recommandation.",
          "Alertes + optimisations")],
        "Les graphiques ci-dessus et le tableau ci-dessous sont alimentés par ces mêmes mesures.")


# ============================================================
# BLOCS RÉUTILISABLES DE L'ACCUEIL
# ============================================================

FEATURES = [
    ("3D", "/batiment", "Bâtiment 3D",
     "Explorez votre établissement en trois dimensions, étage par étage, et accédez aux salles."),
    ("HIS", "/historique", "Historique",
     "Toutes les mesures enregistrées, regroupées par minute, heure ou jour pour rester rapide."),
    ("VS", "/comparaisons", "Comparaisons",
     "Comparez la consommation des salles et des équipements pour repérer les plus gourmands."),
    ("ALT", "/alertes", "Alertes",
     "Les surconsommations sont détectées automatiquement. Vous les traitez d'un clic."),
    ("OPT", "/optimisations", "Optimisations",
     "Chaque alerte génère un conseil concret avec un gain estimé que vous pouvez appliquer."),
    ("SIM", "/historique", "Simulation en continu",
     "Une mesure toutes les 2 minutes sur chaque équipement, avec des anomalies simulées."),
]


def features_html(liens=True):
    out = '<div class="feats">'
    for mark, href, titre, texte in FEATURES:
        cible = href if liens else "/connexion"
        out += (f'<a class="feat" href="{cible}"><div class="fi">{mark}</div>'
                f'<h3>{titre}</h3><p>{texte}</p></a>')
    return out + "</div>"


def gauge_html():
    return """<div class="card rise"><h3>Comment une alerte se déclenche</h3>
<p>Chaque équipement a une puissance normale. Au-delà de 120 % de cette valeur, une alerte est créée.</p>
<div class="gauge"><div class="t"><span>Puissance normale</span><span>100 %</span></div><div class="bar"><i style="--w:55%;background:#16a89a"></i></div></div>
<div class="gauge"><div class="t"><span>Seuil d'anomalie</span><span>120 %</span></div><div class="bar"><i style="--w:66%;background:#f59e0b"></i></div></div>
<div class="gauge"><div class="t"><span>Niveau ÉLEVÉ</span><span>&gt; 120 %</span></div><div class="bar"><i style="--w:80%;background:#f97316"></i></div></div>
<div class="gauge"><div class="t"><span>Niveau TRÈS ÉLEVÉ</span><span>≥ 180 %</span></div><div class="bar"><i style="--w:100%;background:#dc2626"></i></div></div></div>"""


def pipeline_html(n_mesures="—", n_alertes="—", n_opt="—"):
    return f"""<div class="card rise"><h3>De la donnée à la décision</h3>
<p>Le système transforme chaque mesure en action concrète, en continu.</p>
<div class="track"><div class="line"><i></i><i></i><i></i></div>
<div class="node" style="--d:0s"><div class="ico">01</div><h4>Simulation</h4><span>{n_mesures} mesures</span></div>
<div class="node" style="--d:1.5s"><div class="ico">02</div><h4>Analyse</h4><span>toutes les 10 min</span></div>
<div class="node" style="--d:3s"><div class="ico">03</div><h4>Alertes</h4><span>{n_alertes} détectées</span></div>
<div class="node" style="--d:4.5s"><div class="ico">04</div><h4>Optimisation</h4><span>{n_opt} conseils</span></div></div></div>"""


# ============================================================
# ACCUEIL
# ============================================================

HOME_JS = """
<script>
new Chart(document.getElementById("hoursChart"),{type:"line",
 data:{labels:__L1__,datasets:[{label:"Énergie (kWh)",data:__V1__,borderColor:"#168b83",backgroundColor:"rgba(22,139,131,.15)",fill:true,tension:.35,pointRadius:2}]},
 options:{responsive:true,maintainAspectRatio:false,scales:{y:{beginAtZero:true}}}});
new Chart(document.getElementById("typeChart"),{type:"doughnut",
 data:{labels:__L2__,datasets:[{data:__V2__,backgroundColor:PAL}]},
 options:{responsive:true,maintainAspectRatio:false,cutout:"60%",plugins:{legend:{position:"bottom"}}}});
function refresh(){fetch("/api/live").then(function(r){return r.json()}).then(function(d){
 setCount("liveEnergie",d.energie,2);setCount("livePuissance",d.puissance,3);
 setCount("liveAlertes",d.alertes_actives,0);setCount("liveOptim",d.optim_attente,0);
 var l=document.getElementById("liveDate");if(l)l.textContent=d.derniere}).catch(function(){})}
setInterval(refresh,10000);
</script>
"""


@app.route("/")
def home():
    # ---------- visiteur non connecté : page de bienvenue ----------
    if not session.get("user_id"):
        content = (
            '<section class="hero rise"><div>'
            '<span class="pill"><i></i>Bienvenue dans le système</span>'
            '<h1>Smart <span class="g">Energy</span> Monitor</h1>'
            '<p>Surveillez, analysez et optimisez la consommation électrique de votre établissement. '
            '<b>Veuillez vous connecter</b> pour accéder au tableau de bord, aux alertes et aux optimisations.</p>'
            '<div class="actions"><a class="hbtn primary" href="/connexion">Se connecter</a>'
            '<a class="hbtn ghost" href="/inscription">Créer un compte</a></div></div>'
            '<div class="orbs"><span></span><span></span><span></span><b>SE</b></div></section>'
            '<div class="section-title"><h2>Ce que fait le système</h2>'
            '<p>Six modules, accessibles après connexion.</p></div>'
            + features_html(liens=False) +
            '<div class="section-title"><h2>Comment ça fonctionne</h2></div>'
            '<div class="main2">' + pipeline_html() + gauge_html() + '</div>'
        )
        return page_template("Bienvenue", content, "home")

    # ---------- utilisateur connecté : tableau de bord ----------
    db = get_db()
    cur = db.cursor()
    live = live_stats(cur)
    n_mesures = scalar(cur, "SELECT COUNT(*) FROM consommations")
    n_alertes = scalar(cur, "SELECT COUNT(*) FROM alertes")
    n_opt = scalar(cur, "SELECT COUNT(*) FROM optimisations")
    n_equip = scalar(cur, "SELECT COUNT(*) FROM equipements")
    n_salles = scalar(cur, "SELECT COUNT(*) FROM salles")

    cur.execute("""
        SELECT substr(date_heure,1,13) AS h, SUM(energie) AS e
        FROM consommations GROUP BY h ORDER BY h DESC LIMIT 24""")
    heures = list(reversed(cur.fetchall()))
    cur.execute("""
        SELECT e.nom, COALESCE(SUM(c.energie),0) AS energie
        FROM equipements e LEFT JOIN consommations c ON c.equipement_id = e.id
        GROUP BY e.nom ORDER BY energie DESC""")
    types = cur.fetchall()
    db.close()

    nom = esc(session.get("user_name", ""))
    stats = (
        '<section class="grid-4">'
        + stat("Énergie enregistrée", live["energie"], "kWh", "ok", "Total depuis le début", 2, "liveEnergie")
        + stat("Puissance actuelle", live["puissance"], "kW", "", "Dernière mesure", 3, "livePuissance")
        + stat("Alertes actives", live["alertes_actives"], "", "bad" if live["alertes_actives"] else "ok",
               f"{n_alertes} au total", 0, "liveAlertes")
        + stat("Optimisations en attente", live["optim_attente"], "", "warn",
               f"{n_opt} au total", 0, "liveOptim")
        + '</section>'
    )
    content = (
        f'<section class="hero rise"><div><span class="pill"><i></i>Système opérationnel</span>'
        f'<h1>Bonjour <span class="g">{nom}</span>, bienvenue.</h1>'
        f'<p>{n_salles} salles et {n_equip} équipements surveillés en direct. '
        f'Dernière mesure : <b id="liveDate">{live["derniere"]}</b>.</p>'
        f'<div class="actions"><a class="hbtn primary" href="/alertes">Voir les alertes</a>'
        f'<a class="hbtn ghost" href="/batiment">Explorer le bâtiment</a></div></div>'
        f'<div class="orbs"><span></span><span></span><span></span><b>SE</b></div></section>'
        + stats +
        '<div class="main2">' + pipeline_html(n_mesures, n_alertes, n_opt) + gauge_html() + '</div>'
        '<div class="section-title"><h2>Consommation en direct</h2>'
        '<p>Mise à jour automatique des compteurs toutes les 10 secondes.</p></div>'
        '<div class="grid-2">'
        '<div class="chart-card rise"><h3>Dernières 24 heures</h3><p>Énergie (kWh) regroupée par heure.</p>'
        '<div class="chart-container"><canvas id="hoursChart"></canvas></div></div>'
        '<div class="chart-card rise"><h3>Répartition par type d\'équipement</h3><p>Part de chaque type dans l\'énergie totale.</p>'
        '<div class="chart-container"><canvas id="typeChart"></canvas></div></div></div>'
        '<div class="section-title"><h2>Modules</h2><p>Cliquez pour accéder directement à une fonction.</p></div>'
        + features_html()
        + fill(HOME_JS,
               L1=json_data([x["h"][5:] + "h" for x in heures]),
               V1=json_data([safe_float(x["e"]) for x in heures]),
               L2=json_data([x["nom"] for x in types]),
               V2=json_data([safe_float(x["energie"]) for x in types]))
    )
    return page_template("Accueil", content, "home")


# ============================================================
# PAGE D'UNE SALLE
# ============================================================

ROOM_JS = """<script>
new Chart(document.getElementById("roomLine"),{type:"line",
 data:{labels:__L__,datasets:[{label:"Énergie (kWh)",data:__E__,borderColor:"#168b83",backgroundColor:"rgba(22,139,131,.15)",fill:true,tension:.35}]},
 options:{responsive:true,maintainAspectRatio:false,scales:{x:{ticks:{maxTicksLimit:12}}}}});
new Chart(document.getElementById("roomPie"),{type:"doughnut",
 data:{labels:__EL__,datasets:[{data:__EV__,backgroundColor:PAL}]},
 options:{responsive:true,maintainAspectRatio:false,cutout:"58%",plugins:{legend:{position:"bottom"}}}});
</script>"""


@app.route("/salle/<int:salle_id>")
def salle(salle_id):
    db = get_db()
    cur = db.cursor()
    s = cur.execute("SELECT * FROM salles WHERE id = ?", (salle_id,)).fetchone()
    if not s:
        db.close()
        abort(404)

    cur.execute("""
        SELECT e.id, e.nom, e.type, e.etat,
               COALESCE(SUM(c.energie),0) AS energie, COALESCE(AVG(c.puissance),0) AS puissance
        FROM equipements e LEFT JOIN consommations c ON c.equipement_id = e.id
        WHERE e.salle_id = ? GROUP BY e.id, e.nom, e.type, e.etat ORDER BY e.id""", (salle_id,))
    equipements = cur.fetchall()
    stats = cur.execute("""
        SELECT COALESCE(SUM(c.energie),0) AS energie, COALESCE(AVG(c.puissance),0) AS puissance
        FROM consommations c JOIN equipements e ON e.id = c.equipement_id
        WHERE e.salle_id = ?""", (salle_id,)).fetchone()
    cur.execute("""
        SELECT c.date_heure, SUM(c.energie) AS energie
        FROM consommations c JOIN equipements e ON e.id = c.equipement_id
        WHERE e.salle_id = ? GROUP BY c.date_heure ORDER BY c.date_heure DESC LIMIT 30""", (salle_id,))
    hist = list(reversed(cur.fetchall()))
    db.close()

    rows = "".join(
        f'<tr><td><strong>{esc(e["nom"])}</strong></td><td>{esc(e["type"] or "-")}</td>'
        f'<td>{esc(e["etat"] or "-")}</td><td>{safe_float(e["puissance"]):.3f} kW</td>'
        f'<td>{safe_float(e["energie"]):.3f} kWh</td></tr>' for e in equipements)

    content = (
        header("Salle surveillée", esc(s["nom"]),
               esc(s["description"] or "Analyse détaillée de la consommation énergétique."))
        + '<div class="grid-4">'
        + stat("Énergie", safe_float(stats["energie"]), "kWh", "ok", "", 2)
        + stat("Puissance moyenne", safe_float(stats["puissance"]), "kW", "", "", 3)
        + stat("Équipements", len(equipements))
        + stat("Localisation", esc(s["localisation"] or "-"))
        + '</div>'
        '<div class="grid-2"><div class="chart-card"><h3>Évolution de la consommation</h3>'
        '<p>30 dernières mesures.</p><div class="chart-container"><canvas id="roomLine"></canvas></div></div>'
        '<div class="chart-card"><h3>Consommation par équipement</h3><p>Répartition de l\'énergie.</p>'
        '<div class="chart-container"><canvas id="roomPie"></canvas></div></div></div>'
        + diagramme_salle(len(equipements)) +
        '<div class="section-title"><h2>Équipements</h2></div>'
        '<div class="table-card"><table><thead><tr><th>Équipement</th><th>Type</th><th>État</th>'
        f'<th>Puissance moyenne</th><th>Énergie</th></tr></thead><tbody>{rows}</tbody></table></div>'
        + fill(ROOM_JS,
               L=json_data([str(x["date_heure"])[11:16] for x in hist]),
               E=json_data([safe_float(x["energie"]) for x in hist]),
               EL=json_data([x["nom"] for x in equipements]),
               EV=json_data([safe_float(x["energie"]) for x in equipements]))
    )
    return page_template(s["nom"], content, "batiment")


# ============================================================
# BÂTIMENT 3D (three r128 + 3 CDN de secours + plan 2D si WebGL échoue)
# ============================================================

BUILDING_JS = """<script>
(function(){
var host=document.getElementById("building3d"),SEL=__SEL__;
if(!host)return;
var NAMES=["","Rez-de-chaussée","1er étage","2e étage","3e étage"];
var SRC=["https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
 "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js",
 "https://unpkg.com/three@0.128.0/build/three.min.js"];

function fallback(){
 var h='<svg viewBox="0 0 300 330" class="fb3d">';
 for(var i=4;i>=1;i--){var y=15+(4-i)*78;
  h+='<a href="/batiment/'+i+'"><rect x="40" y="'+y+'" width="220" height="68" rx="10" class="'+(i===SEL?"sel":"")+'"/><text x="150" y="'+(y+40)+'" text-anchor="middle">'+NAMES[i]+'</text></a>';}
 host.innerHTML=h+"</svg>";
}

function init(){
 var W=Math.max(host.clientWidth,300),H=390;
 var renderer=new THREE.WebGLRenderer({antialias:true});
 renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));renderer.setSize(W,H);
 host.innerHTML="";host.appendChild(renderer.domElement);
 var scene=new THREE.Scene();scene.background=new THREE.Color(0x0f3f3a);
 var camera=new THREE.PerspectiveCamera(42,W/H,.1,100);camera.position.set(8,6,10);
 scene.add(new THREE.AmbientLight(0xffffff,.8));
 var dl=new THREE.DirectionalLight(0xffffff,.9);dl.position.set(5,9,6);scene.add(dl);
 var building=new THREE.Group();scene.add(building);
 var floors=[];
 for(var i=0;i<4;i++){
  var col=(i+1===SEL)?0x38d9b0:0xb9e5c7;
  var f=new THREE.Mesh(new THREE.BoxGeometry(4.2,.85,3.2),new THREE.MeshStandardMaterial({color:col,roughness:.6}));
  f.position.y=i*1.05+.55;f.userData.floor=i+1;building.add(f);floors.push(f);
  var slab=new THREE.Mesh(new THREE.BoxGeometry(4.35,.12,3.35),new THREE.MeshStandardMaterial({color:0x17643e}));
  slab.position.y=i*1.05+.08;building.add(slab);
  for(var w=0;w<3;w++){
   var win=new THREE.Mesh(new THREE.BoxGeometry(.65,.42,.04),new THREE.MeshStandardMaterial({color:0x238653}));
   win.position.set(-1.35+w*1.35,i*1.05+.58,1.62);building.add(win);}
 }
 var roof=new THREE.Mesh(new THREE.ConeGeometry(2.8,1.3,4),new THREE.MeshStandardMaterial({color:0x17643e}));
 roof.rotation.y=Math.PI/4;roof.position.y=4.9;building.add(roof);
 var ground=new THREE.Mesh(new THREE.BoxGeometry(7,.15,5.5),new THREE.MeshStandardMaterial({color:0x28563c}));
 ground.position.y=-.08;scene.add(ground);

 var drag=false,moved=0,lx=0,ly=0,rotY=-.5,rotX=.1;
 host.addEventListener("pointerdown",function(e){drag=true;moved=0;lx=e.clientX;ly=e.clientY});
 window.addEventListener("pointerup",function(){drag=false});
 host.addEventListener("pointermove",function(e){if(!drag)return;
  moved+=Math.abs(e.clientX-lx)+Math.abs(e.clientY-ly);
  rotY+=(e.clientX-lx)*.008;rotX=Math.max(-.4,Math.min(.4,rotX+(e.clientY-ly)*.004));lx=e.clientX;ly=e.clientY});
 host.addEventListener("wheel",function(e){e.preventDefault();camera.position.multiplyScalar(e.deltaY>0?1.08:.92);camera.position.clampLength(7,20)},{passive:false});
 var ray=new THREE.Raycaster(),mouse=new THREE.Vector2();
 host.addEventListener("click",function(e){
  if(moved>6)return;
  var r=host.getBoundingClientRect();
  mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;
  ray.setFromCamera(mouse,camera);var hit=ray.intersectObjects(floors);
  if(hit.length)window.location.href="/batiment/"+hit[0].object.userData.floor;});
 (function loop(){requestAnimationFrame(loop);
  if(!drag)rotY+=.004;
  building.rotation.y=rotY;building.rotation.x=rotX;camera.lookAt(0,2,0);renderer.render(scene,camera)})();
 window.addEventListener("resize",function(){var w=Math.max(host.clientWidth,300);camera.aspect=w/H;camera.updateProjectionMatrix();renderer.setSize(w,H)});
}

function load(i){
 if(window.THREE){try{init()}catch(e){fallback()}return}
 if(i>=SRC.length){fallback();return}
 var s=document.createElement("script");s.src=SRC[i];
 s.onload=function(){try{init()}catch(e){fallback()}};
 s.onerror=function(){load(i+1)};
 document.head.appendChild(s);
}
load(0);
})();
</script>"""


@app.route("/batiment")
@app.route("/batiment/<int:etage>")
def batiment(etage=0):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.id, s.nom, s.description, s.localisation,
               COUNT(DISTINCT e.id) AS nb_equipements, COALESCE(SUM(c.energie),0) AS energie
        FROM salles s
        LEFT JOIN equipements e ON e.salle_id = s.id
        LEFT JOIN consommations c ON c.equipement_id = e.id
        GROUP BY s.id, s.nom, s.description, s.localisation ORDER BY s.id""")
    toutes = cur.fetchall()
    db.close()

    etage = max(0, min(4, etage))
    noms = {1: "Rez-de-chaussée", 2: "1er étage", 3: "2e étage", 4: "3e étage"}
    # Les salles sont réparties sur les étages sans modifier la base.
    salles_etage = toutes if etage == 0 else [s for i, s in enumerate(toutes) if i % 4 == etage - 1]

    if not salles_etage:
        salles_html = '<div class="card"><h3>Aucune salle à cet étage</h3><p>Choisissez un autre étage.</p></div>'
    else:
        salles_html = '<div class="grid-2">'
        for s in salles_etage:
            salles_html += (
                f'<a class="room-card" href="/salle/{s["id"]}"><div class="room-top"><div class="room-icon">'
                '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">'
                '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 7h2m2 0h2M9 11h2m2 0h2M9 15h2m2 0h2M10 21v-3h4v3"/></svg>'
                '</div><span class="status-normal">SURVEILLÉE</span></div>'
                f'<h3>{esc(s["nom"])}</h3><div class="location">{esc(s["localisation"] or noms.get(etage, ""))}</div>'
                f'<div class="room-consumption"><small>Consommation enregistrée</small>'
                f'<strong>{safe_float(s["energie"]):.3f} kWh</strong></div>'
                f'<small class="mut">{s["nb_equipements"]} équipement(s)</small></a>')
        salles_html += '</div>'

    floors = (f'<a class="floor-button{" selected" if etage == 0 else ""}" href="/batiment">'
              f'<span>Toutes les salles</span><span class="floor-badge">{len(toutes)}</span></a>')
    for n, nom in noms.items():
        sel = " selected" if n == etage else ""
        floors += (f'<a class="floor-button{sel}" href="/batiment/{n}"><span>{nom}</span>'
                   f'<span class="floor-badge">Étage {n}</span></a>')
    label = "Tous les étages" if etage == 0 else noms[etage]

    content = (
        header("GESTION DES ESPACES", "Bâtiment intelligent",
               "Explorez le bâtiment en 3D et consultez les salles, équipements et consommations.")
        + '<div class="building-layout"><section class="building-visual">'
        '<div style="font-size:11px;letter-spacing:2px;color:#b9e9c9;font-weight:800">SMART ENERGY MONITOR</div>'
        '<h2 style="margin-top:6px">Votre établissement</h2>'
        '<div id="building3d" class="building-3d"><div class="three-loading">Chargement du bâtiment 3D…</div></div>'
        '<div class="three-help">Glissez pour tourner · Molette pour zoomer · Cliquez sur un étage</div>'
        '</section><section><div class="section-title" style="margin-top:0"><h2>Choisir un étage</h2></div>'
        f'<div class="floor-list">{floors}</div>'
        f'<div class="section-title"><h2>{label}</h2><p>{len(salles_etage)} salle(s) trouvée(s)</p></div>'
        f'{salles_html}</section></div>'
        + fill(BUILDING_JS, SEL=etage)
    )
    return page_template("Bâtiment", content, "batiment")


# ============================================================
# HISTORIQUE (rapide : agrégation SQL + tableau paginé)
# ============================================================

# pas : (nb de caractères de date_heure conservés, fenêtre affichée sur le graphique)
PAS = {
    "minute": (16, timedelta(hours=4)),
    "heure": (13, timedelta(days=3)),
    "jour": (10, timedelta(days=60)),
}
PAR_PAGE = 50

HIST_JS = """<script>
new Chart(document.getElementById("historyChart"),{type:"line",
 data:{labels:__L__,datasets:[{label:"Énergie (kWh)",data:__E__,borderColor:"#168b83",backgroundColor:"rgba(22,139,131,.15)",fill:true,tension:.3,pointRadius:2}]},
 options:{responsive:true,maintainAspectRatio:false,scales:{x:{ticks:{maxTicksLimit:14}},y:{beginAtZero:true}}}});
</script>"""


@app.route("/historique")
def historique():
    pas = request.args.get("pas", "heure")
    if pas not in PAS:
        pas = "heure"
    n, fenetre = PAS[pas]
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    db = get_db()
    cur = db.cursor()
    total, premiere, derniere, energie, pmax = cur.execute("""
        SELECT COUNT(*), MIN(date_heure), MAX(date_heure), COALESCE(SUM(energie),0), COALESCE(MAX(puissance),0)
        FROM consommations""").fetchone()

    # fenêtre calculée depuis la dernière mesure : utilise l'index sur date_heure
    cutoff = ""
    try:
        cutoff = (datetime.strptime(str(derniere)[:19], "%Y-%m-%d %H:%M:%S") - fenetre).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    cur.execute(f"""
        SELECT substr(date_heure,1,{n}) AS t, SUM(energie) AS e
        FROM consommations WHERE date_heure >= ? GROUP BY t ORDER BY t""", (cutoff,))
    serie = cur.fetchall()

    pages = max(1, math.ceil(total / PAR_PAGE))
    page = min(page, pages)
    cur.execute("""
        SELECT c.date_heure, s.nom AS salle, e.nom AS equipement, c.puissance, c.energie
        FROM consommations c JOIN equipements e ON e.id = c.equipement_id
        JOIN salles s ON s.id = e.salle_id
        ORDER BY c.date_heure DESC, c.id DESC LIMIT ? OFFSET ?""", (PAR_PAGE, (page - 1) * PAR_PAGE))
    lignes = cur.fetchall()
    db.close()

    rows = "".join(
        f'<tr><td>{format_date(x["date_heure"])}</td><td>{esc(x["salle"])}</td><td>{esc(x["equipement"])}</td>'
        f'<td>{safe_float(x["puissance"]):.3f} kW</td><td>{safe_float(x["energie"]):.4f} kWh</td></tr>'
        for x in lignes)

    tabs = '<div class="tabs">'
    for cle, nom in (("minute", "Par minute (4 h)"), ("heure", "Par heure (3 jours)"), ("jour", "Par jour (60 jours)")):
        tabs += f'<a class="{"on" if cle == pas else ""}" href="/historique?pas={cle}">{nom}</a>'
    tabs += '</div>'

    prec = f'<a class="btn light" href="/historique?pas={pas}&page={page - 1}">← Précédent</a>' if page > 1 else ""
    suiv = f'<a class="btn light" href="/historique?pas={pas}&page={page + 1}">Suivant →</a>' if page < pages else ""

    content = (
        header("Données énergétiques", "Historique",
               "Consultez les mesures enregistrées et observez leur évolution. Les données sont regroupées pour un affichage instantané.")
        + '<div class="grid-4">'
        + stat("Mesures enregistrées", total)
        + stat("Énergie totale", safe_float(energie), "kWh", "ok", "", 2)
        + stat("Puissance maximale", safe_float(pmax), "kW", "warn", "", 3)
        + stat("Première mesure", format_date(premiere), "", "", f"Dernière : {format_date(derniere)}")
        + '</div>'
        '<div class="chart-card"><h3>Évolution de l\'énergie</h3><p>Somme de l\'énergie de tous les équipements par période.</p>'
        + tabs + '<div class="chart-container"><canvas id="historyChart"></canvas></div></div>'
        '<div class="section-title"><h2>Mesures détaillées</h2>'
        f'<p>Les plus récentes d\'abord · page {page} sur {pages}</p></div>'
        '<div class="table-card"><table><thead><tr><th>Date</th><th>Salle</th><th>Équipement</th>'
        f'<th>Puissance</th><th>Énergie</th></tr></thead><tbody>{rows}</tbody></table>'
        f'<div class="pager">{prec}<span>Page {page} / {pages}</span>{suiv}</div></div>'
        + fill(HIST_JS,
               L=json_data([x["t"][5:] for x in serie]),
               E=json_data([safe_float(x["e"]) for x in serie]))
    )
    return page_template("Historique", content, "historique")


# ============================================================
# COMPARAISONS
# ============================================================

COMP_JS = """<script>
new Chart(document.getElementById("roomsChart"),{type:"bar",
 data:{labels:__RL__,datasets:[{label:"Énergie (kWh)",data:__RV__,backgroundColor:PAL}]},
 options:{responsive:true,maintainAspectRatio:false,indexAxis:"y",plugins:{legend:{display:false}}}});
new Chart(document.getElementById("equipChart"),{type:"doughnut",
 data:{labels:__EL__,datasets:[{data:__EV__,backgroundColor:PAL}]},
 options:{responsive:true,maintainAspectRatio:false,cutout:"58%",plugins:{legend:{position:"bottom"}}}});
</script>"""


@app.route("/comparaisons")
def comparaisons():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.nom, COALESCE(SUM(c.energie),0) AS energie, COALESCE(AVG(c.puissance),0) AS puissance
        FROM salles s LEFT JOIN equipements e ON e.salle_id = s.id
        LEFT JOIN consommations c ON c.equipement_id = e.id
        GROUP BY s.id, s.nom ORDER BY energie DESC""")
    salles = cur.fetchall()
    cur.execute("""
        SELECT e.nom, COALESCE(SUM(c.energie),0) AS energie
        FROM equipements e LEFT JOIN consommations c ON c.equipement_id = e.id
        GROUP BY e.nom ORDER BY energie DESC""")
    equips = cur.fetchall()
    db.close()

    rows = "".join(
        f'<tr><td><strong>{esc(x["nom"])}</strong></td><td>{safe_float(x["energie"]):.3f} kWh</td>'
        f'<td>{safe_float(x["puissance"]):.3f} kW</td></tr>' for x in salles)
    top = salles[0]["nom"] if salles and safe_float(salles[0]["energie"]) > 0 else "-"

    content = (
        header("Analyse comparative", "Comparaisons",
               "Comparez les consommations enregistrées entre les salles et les équipements.")
        + '<div class="grid-3">'
        + stat("Salle la plus consommatrice", esc(top))
        + stat("Salles comparées", len(salles))
        + stat("Types d'équipements", len(equips))
        + '</div><div class="grid-2" style="margin-top:18px">'
        '<div class="chart-card"><h3>Consommation par salle</h3><p>Énergie enregistrée (kWh).</p>'
        '<div class="chart-container"><canvas id="roomsChart"></canvas></div></div>'
        '<div class="chart-card"><h3>Consommation par équipement</h3><p>Contribution de chaque type.</p>'
        '<div class="chart-container"><canvas id="equipChart"></canvas></div></div></div>'
        '<div class="section-title"><h2>Tableau comparatif</h2></div>'
        '<div class="table-card"><table><thead><tr><th>Salle</th><th>Énergie</th><th>Puissance moyenne</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        + fill(COMP_JS,
               RL=json_data([x["nom"] for x in salles]), RV=json_data([safe_float(x["energie"]) for x in salles]),
               EL=json_data([x["nom"] for x in equips]), EV=json_data([safe_float(x["energie"]) for x in equips]))
    )
    return page_template("Comparaisons", content, "comparaisons")


# ============================================================
# ALERTES (avec bouton Traiter)
# ============================================================

RE_MESURE = re.compile(r"Puissance mesurée : ([\d.]+) kW ; seuil de détection : ([\d.]+) kW")

ALERT_JS = """<script>
new Chart(document.getElementById("nivChart"),{type:"doughnut",
 data:{labels:__NL__,datasets:[{data:__NV__,backgroundColor:["#f97316","#dc2626","#16a34a","#6366f1"]}]},
 options:{responsive:true,maintainAspectRatio:false,cutout:"58%",plugins:{legend:{position:"bottom"}}}});
new Chart(document.getElementById("eqChart"),{type:"bar",
 data:{labels:__EL__,datasets:[{label:"Alertes",data:__EV__,backgroundColor:PAL}]},
 options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{precision:0}}}}});
</script>"""


@app.route("/alertes")
def alertes():
    statut = request.args.get("statut", "toutes")
    if statut not in ("ACTIVE", "TRAITEE", "toutes"):
        statut = "toutes"

    db = get_db()
    cur = db.cursor()
    total, actives, traitees, critiques = cur.execute("""
        SELECT COUNT(*),
               COALESCE(SUM(UPPER(statut)='ACTIVE'),0),
               COALESCE(SUM(UPPER(statut)='TRAITEE'),0),
               COALESCE(SUM(niveau='TRÈS ÉLEVÉ'),0)
        FROM alertes""").fetchone()

    where, args = ("", ())
    if statut != "toutes":
        where, args = "WHERE UPPER(a.statut) = ?", (statut,)
    cur.execute(f"""
        SELECT a.id, a.type, a.message, a.niveau, a.date_heure, a.statut,
               s.nom AS salle, e.nom AS equipement
        FROM alertes a LEFT JOIN salles s ON s.id = a.salle_id
        LEFT JOIN equipements e ON e.id = a.equipement_id
        {where} ORDER BY a.date_heure DESC, a.id DESC LIMIT 200""", args)
    lignes = cur.fetchall()
    niveaux = cur.execute("SELECT niveau, COUNT(*) AS n FROM alertes GROUP BY niveau").fetchall()
    par_equip = cur.execute("""
        SELECT COALESCE(e.nom,'Inconnu') AS nom, COUNT(*) AS n FROM alertes a
        LEFT JOIN equipements e ON e.id = a.equipement_id
        GROUP BY e.nom ORDER BY n DESC LIMIT 8""").fetchall()
    db.close()

    rows = ""
    for a in lignes:
        m = RE_MESURE.search(a["message"] or "")
        if m and float(m.group(2)) > 0:
            p, sv = float(m.group(1)), float(m.group(2))
            mesure = (f'{p:.3f} kW<br><small class="mut">seuil {sv:.3f} kW · '
                      f'+{(p / sv - 1) * 100:.0f} %</small>')
        else:
            mesure = "-"
        if str(a["statut"] or "").upper() == "ACTIVE":
            action = ('<form method="post" action="/alertes/%d/traiter">%s'
                      '<input type="hidden" name="statut" value="%s">'
                      '<button class="btn" type="submit">Traiter</button></form>'
                      % (a["id"], csrf_input(), statut))
            etat = '<span class="badge badge-red">ACTIVE</span>'
        else:
            action = '<small class="mut">Aucune action</small>'
            etat = '<span class="badge badge-green">TRAITÉE</span>'
        rows += (f'<tr><td>#{a["id"]}</td><td>{format_date(a["date_heure"])}</td><td>{esc(a["salle"] or "-")}</td>'
                 f'<td>{esc(a["equipement"] or "-")}</td><td>{badge_niveau(a["niveau"])}</td><td>{mesure}</td>'
                 f'<td style="min-width:220px">{esc(a["message"] or "-")}</td><td>{etat}</td><td>{action}</td></tr>')
    if not rows:
        rows = '<tr><td colspan="9" style="text-align:center;padding:30px">Aucune alerte pour ce filtre.</td></tr>'

    ok = '<div class="notice">Alerte(s) traitée(s) avec succès.</div>' if request.args.get("ok") else ""
    tabs = '<div class="tabs">'
    for cle, nom in (("toutes", "Toutes"), ("ACTIVE", "Actives"), ("TRAITEE", "Traitées")):
        tabs += f'<a class="{"on" if cle == statut else ""}" href="/alertes?statut={cle}">{nom}</a>'
    tabs += '</div>'
    tout = ""
    if actives:
        tout = (f'<form method="post" action="/alertes/traiter-tout" style="margin-bottom:14px">{csrf_input()}'
                f'<button class="btn" type="submit">Traiter les {actives} alerte(s) active(s)</button></form>')

    content = (
        header("Surveillance", "Alertes",
               "Les surconsommations détectées par le système sont centralisées ici. Traitez-les une fois la situation vérifiée.")
        + ok + '<div class="grid-4">'
        + stat("Alertes au total", total)
        + stat("À traiter", actives, "", "bad" if actives else "ok", "Statut ACTIVE")
        + stat("Traitées", traitees, "", "ok")
        + stat("Très élevées", critiques, "", "warn", "Puissance ≥ 180 % de la normale")
        + '</div><div class="grid-3" style="margin-bottom:18px">'
        '<div class="card rise"><h3>Comment ça marche</h3><p>Toutes les 10 minutes, les mesures récentes sont comparées à la puissance normale de chaque équipement. '
        'Au-delà de 120 %, une alerte est créée.</p></div>'
        '<div class="card rise"><h3>Que signifie « Traiter » ?</h3><p>Vous confirmez avoir vérifié l\'équipement. L\'alerte passe en TRAITÉE, '
        'et une nouvelle alerte pourra être créée si l\'anomalie revient.</p></div>'
        '<div class="card rise"><h3>Niveaux de gravité</h3><p><span class="badge badge-orange">ÉLEVÉ</span> dépasse le seuil de 120 %.<br><br>'
        '<span class="badge badge-red">TRÈS ÉLEVÉ</span> atteint 180 % de la puissance normale.</p></div></div>'
        '<div class="grid-2"><div class="chart-card"><h3>Répartition par niveau</h3><p>Gravité des alertes enregistrées.</p>'
        '<div class="chart-container"><canvas id="nivChart"></canvas></div></div>'
        '<div class="chart-card"><h3>Équipements les plus concernés</h3><p>Nombre d\'alertes par type d\'équipement.</p>'
        '<div class="chart-container"><canvas id="eqChart"></canvas></div></div></div>'
        + diagramme_alertes() +
        '<div class="section-title"><h2>Liste des alertes</h2><p>200 plus récentes maximum.</p></div>'
        + tabs + tout +
        '<div class="table-card"><table><thead><tr><th>N°</th><th>Date</th><th>Salle</th><th>Équipement</th><th>Niveau</th>'
        f'<th>Mesure</th><th>Message</th><th>Statut</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div>'
        + fill(ALERT_JS,
               NL=json_data([x["niveau"] for x in niveaux]), NV=json_data([x["n"] for x in niveaux]),
               EL=json_data([x["nom"] for x in par_equip]), EV=json_data([x["n"] for x in par_equip]))
    )
    return page_template("Alertes", content, "alertes")


@app.route("/alertes/<int:alerte_id>/traiter", methods=["POST"])
def traiter_alerte(alerte_id):
    ecrire("UPDATE alertes SET statut='TRAITEE' WHERE id=? AND UPPER(statut)='ACTIVE'", (alerte_id,))
    statut = request.form.get("statut", "toutes")
    return redirect(url_for("alertes", statut=statut, ok=1))


@app.route("/alertes/traiter-tout", methods=["POST"])
def traiter_toutes():
    ecrire("UPDATE alertes SET statut='TRAITEE' WHERE UPPER(statut)='ACTIVE'")
    return redirect(url_for("alertes", ok=1))


# ============================================================
# OPTIMISATIONS (avec bouton Appliquer)
# ============================================================

OPT_JS = """<script>
new Chart(document.getElementById("optChart"),{type:"bar",
 data:{labels:__L__,datasets:[{label:"Recommandations",data:__V__,backgroundColor:PAL}]},
 options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{precision:0}}}}});
new Chart(document.getElementById("statChart"),{type:"doughnut",
 data:{labels:["En attente","Appliquées"],datasets:[{data:__S__,backgroundColor:["#f59e0b","#16a34a"]}]},
 options:{responsive:true,maintainAspectRatio:false,cutout:"60%",plugins:{legend:{position:"bottom"}}}});
</script>"""


@app.route("/optimisations")
def optimisations():
    db = get_db()
    cur = db.cursor()
    total, attente, appliquees, gain_moy = cur.execute("""
        SELECT COUNT(*),
               COALESCE(SUM(UPPER(statut)='EN ATTENTE'),0),
               COALESCE(SUM(UPPER(statut)='APPLIQUEE'),0),
               COALESCE(AVG(gain_estime),0)
        FROM optimisations""").fetchone()
    cur.execute("""
        SELECT o.id, o.alerte_id, o.titre, o.description, o.gain_estime, o.date_heure, o.statut,
               s.nom AS salle, e.nom AS equipement
        FROM optimisations o LEFT JOIN salles s ON s.id = o.salle_id
        LEFT JOIN equipements e ON e.id = o.equipement_id
        ORDER BY o.date_heure DESC, o.id DESC LIMIT 100""")
    lignes = cur.fetchall()
    par_equip = cur.execute("""
        SELECT COALESCE(e.nom,'Inconnu') AS nom, COUNT(*) AS n FROM optimisations o
        LEFT JOIN equipements e ON e.id = o.equipement_id
        GROUP BY e.nom ORDER BY n DESC LIMIT 8""").fetchall()
    db.close()

    rows = ""
    for o in lignes:
        conseil = (o["description"] or "-").split("Action recommandée :")[-1].strip()
        if str(o["statut"] or "").upper() == "EN ATTENTE":
            etat = '<span class="badge badge-orange">EN ATTENTE</span>'
            action = ('<form method="post" action="/optimisations/%d/appliquer">%s'
                      '<button class="btn" type="submit">Appliquer</button></form>' % (o["id"], csrf_input()))
        else:
            etat = '<span class="badge badge-green">APPLIQUÉE</span>'
            action = '<small class="mut">Aucune action</small>'
        lien = f'<br><small class="mut">Liée à l\'alerte #{o["alerte_id"]}</small>' if o["alerte_id"] else ""
        rows += (f'<tr><td>{format_date(o["date_heure"])}</td><td><strong>{esc(o["titre"] or "-")}</strong>{lien}</td>'
                 f'<td>{esc(o["salle"] or "-")}</td><td>{esc(o["equipement"] or "-")}</td>'
                 f'<td style="min-width:240px">{esc(conseil)}</td>'
                 f'<td><strong style="color:#15803d">-{safe_float(o["gain_estime"]):.0f} %</strong></td>'
                 f'<td>{etat}</td><td>{action}</td></tr>')
    if not rows:
        rows = '<tr><td colspan="8" style="text-align:center;padding:30px">Aucune recommandation pour le moment.</td></tr>'

    ok = '<div class="notice">Recommandation marquée comme appliquée.</div>' if request.args.get("ok") else ""
    content = (
        header("Intelligence énergétique", "Optimisations",
               "Chaque alerte détectée produit une recommandation concrète. Marquez-la comme appliquée une fois l'action réalisée.")
        + ok + '<div class="grid-4">'
        + stat("Recommandations", total)
        + stat("En attente", attente, "", "warn")
        + stat("Appliquées", appliquees, "", "ok")
        + stat("Gain moyen estimé", safe_float(gain_moy), "%", "ok", "Estimation indicative", 1)
        + '</div><div class="grid-3" style="margin-bottom:18px">'
        '<div class="card rise"><h3>D\'où viennent ces conseils ?</h3><p>Pour chaque alerte, le système associe un conseil adapté au type d\'équipement concerné (climatiseur, éclairage, etc.).</p></div>'
        '<div class="card rise"><h3>Que signifie le gain ?</h3><p>C\'est un potentiel d\'économie estimé : 10 % pour une alerte ÉLEVÉE, 20 % pour une alerte TRÈS ÉLEVÉE. '
        'Ce n\'est pas une économie mesurée après intervention.</p></div>'
        '<div class="card rise"><h3>Que fait « Appliquer » ?</h3><p>Vous indiquez que l\'action a été réalisée. La recommandation passe en APPLIQUÉE pour suivre votre avancement.</p></div></div>'
        '<div class="grid-2"><div class="chart-card"><h3>Recommandations par équipement</h3><p>Équipements qui génèrent le plus de conseils.</p>'
        '<div class="chart-container"><canvas id="optChart"></canvas></div></div>'
        '<div class="chart-card"><h3>Avancement</h3><p>Recommandations en attente et appliquées.</p>'
        '<div class="chart-container"><canvas id="statChart"></canvas></div></div></div>'
        + diagramme_optimisations() +
        '<div class="section-title"><h2>Recommandations</h2><p>100 plus récentes maximum.</p></div>'
        '<div class="table-card"><table><thead><tr><th>Date</th><th>Recommandation</th><th>Salle</th><th>Équipement</th>'
        f'<th>Action conseillée</th><th>Gain estimé</th><th>Statut</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div>'
        + fill(OPT_JS,
               L=json_data([x["nom"] for x in par_equip]), V=json_data([x["n"] for x in par_equip]),
               S=json_data([attente, appliquees]))
    )
    return page_template("Optimisations", content, "optimisations")


@app.route("/optimisations/<int:opt_id>/appliquer", methods=["POST"])
def appliquer_optimisation(opt_id):
    ecrire("UPDATE optimisations SET statut='APPLIQUEE' WHERE id=? AND UPPER(statut)='EN ATTENTE'", (opt_id,))
    return redirect(url_for("optimisations", ok=1))


# ============================================================
# AUTHENTIFICATION
# ============================================================

def next_sur(valeur):
    return valeur if valeur.startswith("/") and not valeur.startswith("//") else ""


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    message = ""
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("mot_de_passe", "")
        confirm = request.form.get("confirmation", "")
        if not nom or not email or not password:
            message = "Tous les champs sont obligatoires."
        elif len(password) < 8:
            message = "Le mot de passe doit contenir au moins 8 caractères."
        elif password != confirm:
            message = "Les deux mots de passe ne correspondent pas."
        else:
            try:
                with sqlite3.connect(DATABASE, timeout=20) as db:
                    cur = db.execute("INSERT INTO utilisateurs(nom,email,mot_de_passe) VALUES(?,?,?)",
                                     (nom, email, generate_password_hash(password)))
                    user_id = cur.lastrowid
                session.clear()
                session.permanent = True
                session["user_id"], session["user_name"], session["user_email"] = user_id, nom, email
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                message = "Cette adresse e-mail possède déjà un compte."
    msg = f'<div class="auth-message">{esc(message)}</div>' if message else ""
    content = (
        '<section class="auth-wrap"><div class="page-header"><div class="tag">NOUVEAU COMPTE</div>'
        '<h1>Créer un compte</h1><p>Rejoignez votre espace Smart Energy Monitor.</p></div>' + msg +
        '<form class="auth-form" method="post">'
        '<label>Nom complet<input name="nom" autocomplete="name" required></label>'
        '<label>Adresse e-mail<input name="email" type="email" autocomplete="email" required></label>'
        '<label>Mot de passe<input name="mot_de_passe" type="password" minlength="8" autocomplete="new-password" required></label>'
        '<label>Confirmer le mot de passe<input name="confirmation" type="password" minlength="8" autocomplete="new-password" required></label>'
        '<button type="submit">Créer mon compte</button></form>'
        '<p style="margin-top:18px">Déjà inscrit ? <a href="/connexion">Se connecter</a></p></section>')
    return page_template("Inscription", content, "home")


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    message = ""
    if request.args.get("info"):
        message = "Veuillez vous connecter pour accéder à cette page."
    suite = next_sur(request.values.get("next", ""))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("mot_de_passe", "")
        with sqlite3.connect(DATABASE, timeout=20) as db:
            db.row_factory = sqlite3.Row
            user = db.execute("SELECT * FROM utilisateurs WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["mot_de_passe"], password):
            session.clear()
            session.permanent = True
            session["user_id"], session["user_name"], session["user_email"] = user["id"], user["nom"], user["email"]
            return redirect(suite or url_for("home"))
        message = "Adresse e-mail ou mot de passe incorrect."
    msg = f'<div class="auth-message">{esc(message)}</div>' if message else ""
    content = (
        '<section class="auth-wrap"><div class="page-header"><div class="tag">ESPACE SÉCURISÉ</div>'
        '<h1>Connexion</h1><p>Connectez-vous à votre compte.</p></div>' + msg +
        '<form class="auth-form" method="post">'
        f'<input type="hidden" name="next" value="{esc(suite)}">'
        '<label>Adresse e-mail<input name="email" type="email" autocomplete="email" required></label>'
        '<label>Mot de passe<input name="mot_de_passe" type="password" autocomplete="current-password" required></label>'
        '<button type="submit">Se connecter</button></form>'
        '<p style="margin-top:18px">Pas encore de compte ? <a href="/inscription">Créer un compte</a></p></section>')
    return page_template("Connexion", content, "home")


@app.route("/compte")
def compte():
    content = (
        header("ESPACE PERSONNEL", "Mon compte", "Informations de votre profil utilisateur.")
        + '<div class="grid-2">'
        + stat("Nom", esc(session.get("user_name", "Utilisateur")))
        + stat("Adresse e-mail", esc(session.get("user_email", "")))
        + '</div><div style="margin-top:22px"><a class="toolbar-button logout-link" href="/deconnexion">Déconnexion</a></div>')
    return page_template("Mon compte", content, "home")


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect(url_for("home"))


# ============================================================
# ERREURS
# ============================================================

@app.errorhandler(404)
def page_not_found(error):
    content = (
        '<div style="min-height:420px;display:flex;align-items:center;justify-content:center;text-align:center"><div>'
        '<div style="font-size:22px;font-weight:900;letter-spacing:3px;margin-bottom:20px;color:#168b83">SMART ENERGY</div>'
        '<h1 style="font-size:50px;margin-bottom:10px">404</h1>'
        '<p style="color:#718985;margin-bottom:25px">Cette page n\'existe pas.</p>'
        '<a class="btn" href="/">Retour à l\'accueil</a></div></div>')
    return page_template("Page introuvable", content, "home"), 404


@app.errorhandler(400)
def requete_invalide(error):
    content = ('<div class="card"><h3>Requête invalide</h3><p>Votre session a expiré. '
               'Rechargez la page puis recommencez.</p><a class="btn" href="/">Retour à l\'accueil</a></div>')
    return page_template("Requête invalide", content, "home"), 400


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":
    # use_reloader=False : évite de lancer deux fois l'app quand le lanceur la démarre
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5000)
