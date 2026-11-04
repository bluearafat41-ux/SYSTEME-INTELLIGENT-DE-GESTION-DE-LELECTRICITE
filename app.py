from flask import Flask, render_template_string, abort
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database" / "database.db"


# ============================================================
# CONNEXION SQLITE
# ============================================================

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


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
        return datetime.fromisoformat(
            str(date)
        ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(date)


def json_data(data):
    return json.dumps(
        data,
        ensure_ascii=False
    )


# ============================================================
# LAYOUT PRINCIPAL
# ============================================================

def page_template(title, content, active="home"):

    return f"""
<!DOCTYPE html>

<html lang="fr">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>{title} — Smart Energy Monitor</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

/* ============================================================
   RESET
============================================================ */

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{

    font-family:
        "Segoe UI",
        Arial,
        sans-serif;

    background:
        radial-gradient(
            circle at 85% 5%,
            rgba(22,163,74,0.09),
            transparent 25%
        ),

        radial-gradient(
            circle at 5% 90%,
            rgba(239,68,68,0.06),
            transparent 25%
        ),

        #f6faf7;

    color: #17221b;

    min-height: 100vh;
}}


/* ============================================================
   NAVIGATION
============================================================ */

.navbar {{

    width: calc(100% - 40px);

    margin: 20px auto;

    min-height: 72px;

    padding: 12px 20px;

    background: rgba(255,255,255,0.90);

    backdrop-filter: blur(18px);

    border: 1px solid #e1ebe4;

    border-radius: 23px;

    display: flex;

    align-items: center;

    justify-content: space-between;

    box-shadow:
        0 12px 40px rgba(20,40,25,0.07);

    position: sticky;

    top: 15px;

    z-index: 100;
}}


/* ============================================================
   LOGO
============================================================ */

.logo {{

    display: flex;

    align-items: center;

    gap: 11px;

    text-decoration: none;

    color: #17221b;

    font-weight: 850;

    font-size: 18px;
}}

.logo-icon {{

    width: 43px;

    height: 43px;

    border-radius: 14px;

    background: #16a34a;

    color: white;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 21px;

    box-shadow:
        0 8px 20px rgba(22,163,74,0.25);
}}

.logo span {{
    color: #16a34a;
}}


/* ============================================================
   MENU
============================================================ */

.menu {{

    display: flex;

    align-items: center;

    gap: 6px;

    flex-wrap: wrap;
}}

.menu a {{

    text-decoration: none;

    color: #68766d;

    font-size: 12px;

    font-weight: 700;

    padding: 10px 13px;

    border-radius: 12px;

    transition: 0.2s;
}}

.menu a:hover {{
    background: #edf8f0;
    color: #15803d;
}}

.menu a.active {{
    background: #17221b;
    color: white;
}}


/* ============================================================
   HORLOGE
============================================================ */

.clock-container {{

    display: flex;

    align-items: center;

    gap: 10px;

    padding: 9px 13px;

    background: #f0f8f2;

    border-radius: 15px;
}}

.live-dot {{

    width: 8px;

    height: 8px;

    background: #16a34a;

    border-radius: 50%;

    box-shadow:
        0 0 0 5px rgba(22,163,74,0.10);

    animation: pulse 2s infinite;
}}

@keyframes pulse {{

    0% {{
        opacity: 1;
    }}

    50% {{
        opacity: 0.4;
    }}

    100% {{
        opacity: 1;
    }}
}}

.clock {{
    font-weight: 850;
    font-size: 15px;
}}


/* ============================================================
   CONTAINER
============================================================ */

.container {{

    width: calc(100% - 40px);

    max-width: 1500px;

    margin: 25px auto 60px;
}}


/* ============================================================
   PAGE HEADER
============================================================ */

.page-header {{

    margin: 20px 0 25px;

}}

.page-header .tag {{

    display: inline-block;

    padding: 7px 11px;

    border-radius: 20px;

    background: #e8f7ed;

    color: #15803d;

    font-size: 10px;

    font-weight: 850;

    text-transform: uppercase;

    letter-spacing: 1px;

    margin-bottom: 10px;
}}

.page-header h1 {{

    font-size: clamp(30px, 4vw, 48px);

    letter-spacing: -2px;

    line-height: 1;
}}

.page-header h1 span {{
    color: #16a34a;
}}

.page-header p {{

    margin-top: 10px;

    color: #718078;

    font-size: 14px;

    line-height: 1.6;

    max-width: 700px;
}}


/* ============================================================
   HERO ACCUEIL
============================================================ */

.hero {{

    min-height: 340px;

    border-radius: 32px;

    padding: 40px;

    background:
        linear-gradient(
            120deg,
            #ffffff,
            #eff9f2
        );

    border: 1px solid #dfebe3;

    position: relative;

    overflow: hidden;

    box-shadow:
        0 25px 65px rgba(20,40,25,0.08);

    display: flex;

    align-items: center;
}}

.hero-content {{

    max-width: 680px;

    position: relative;

    z-index: 2;
}}

.hero-status {{

    display: inline-flex;

    align-items: center;

    gap: 8px;

    padding: 8px 13px;

    background: #e9f8ee;

    color: #15803d;

    border-radius: 20px;

    font-size: 11px;

    font-weight: 850;

    margin-bottom: 20px;
}}

.hero-status i {{

    width: 7px;

    height: 7px;

    background: #16a34a;

    border-radius: 50%;
}}

.hero h1 {{

    font-size: clamp(40px, 5vw, 72px);

    line-height: 0.95;

    letter-spacing: -4px;

    margin-bottom: 20px;
}}

.hero h1 span {{
    color: #16a34a;
}}

.hero p {{

    color: #637168;

    line-height: 1.7;

    font-size: 15px;

    max-width: 600px;
}}


/* ============================================================
   HERO CERCLES
============================================================ */

.hero-orbit {{

    position: absolute;

    width: 430px;

    height: 430px;

    border-radius: 50%;

    border: 1px solid rgba(22,163,74,0.14);

    right: -70px;

    top: -120px;
}}

.hero-orbit::before {{

    content: "";

    position: absolute;

    inset: 45px;

    border-radius: 50%;

    border: 1px dashed rgba(22,163,74,0.20);
}}

.hero-core {{

    position: absolute;

    right: 115px;

    top: 90px;

    width: 110px;

    height: 110px;

    border-radius: 32px;

    background: #16a34a;

    color: white;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 48px;

    transform: rotate(7deg);

    box-shadow:
        0 25px 50px rgba(22,163,74,0.25);
}}


/* ============================================================
   GRID PRINCIPAL
============================================================ */

.grid-4 {{

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 15px;

    margin-top: 18px;
}}

.grid-3 {{

    display: grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap: 18px;
}}

.grid-2 {{

    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 20px;
}}


/* ============================================================
   STAT CARDS
============================================================ */

.stat-card {{

    background: white;

    border: 1px solid #e1ebe4;

    border-radius: 22px;

    padding: 21px;

    box-shadow:
        0 10px 30px rgba(20,40,25,0.055);

    transition:
        transform 0.25s,
        box-shadow 0.25s;
}}

.stat-card:hover {{

    transform: translateY(-5px);

    box-shadow:
        0 18px 40px rgba(20,40,25,0.10);
}}

.stat-top {{

    display: flex;

    justify-content: space-between;

    align-items: center;

    margin-bottom: 15px;
}}

.stat-icon {{

    width: 42px;

    height: 42px;

    border-radius: 13px;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 19px;
}}

.green {{
    background: #e9f8ee;
    color: #15803d;
}}

.red {{
    background: #fff0f0;
    color: #dc2626;
}}

.orange {{
    background: #fff5e6;
    color: #d97706;
}}

.dark {{
    background: #eef1ef;
    color: #17221b;
}}

.stat-label {{

    font-size: 10px;

    text-transform: uppercase;

    color: #7a877f;

    font-weight: 800;

    letter-spacing: .5px;
}}

.stat-value {{

    font-size: 26px;

    font-weight: 900;

    letter-spacing: -1px;
}}


/* ============================================================
   SECTION
============================================================ */

.section-title {{

    margin: 34px 2px 16px;
}}

.section-title h2 {{
    font-size: 22px;
}}

.section-title p {{

    color: #78857d;

    font-size: 12px;

    margin-top: 4px;
}}


/* ============================================================
   CARTE INFO
============================================================ */

.info-panel {{

    background:
        linear-gradient(
            145deg,
            #102219,
            #173b27
        );

    color: white;

    border-radius: 28px;

    padding: 29px;

    position: relative;

    overflow: hidden;

    min-height: 470px;

    box-shadow:
        0 25px 55px rgba(16,34,25,0.20);
}}

.info-panel::after {{

    content: "";

    position: absolute;

    width: 230px;

    height: 230px;

    border: 1px solid rgba(255,255,255,0.07);

    border-radius: 50%;

    right: -100px;

    bottom: -100px;
}}

.info-panel .small-title {{

    color: #86efac;

    font-size: 10px;

    text-transform: uppercase;

    letter-spacing: 1.5px;

    font-weight: 850;

    margin-bottom: 12px;
}}

.info-panel h2 {{

    font-size: 27px;

    line-height: 1.15;

    margin-bottom: 12px;
}}

.info-panel > p {{

    color: #a9bcae;

    font-size: 13px;

    line-height: 1.7;

    margin-bottom: 27px;
}}

.step {{

    display: flex;

    gap: 13px;

    margin-bottom: 20px;

    position: relative;

    z-index: 2;
}}

.step-number {{

    width: 37px;

    height: 37px;

    flex-shrink: 0;

    border-radius: 11px;

    background: rgba(255,255,255,0.10);

    display: flex;

    align-items: center;

    justify-content: center;

    font-weight: 850;

    color: #86efac;
}}

.step h4 {{
    font-size: 13px;
    margin-bottom: 3px;
}}

.step p {{

    color: #9db0a3;

    font-size: 11px;

    line-height: 1.5;
}}


/* ============================================================
   ROOM CARDS
============================================================ */

.room-card {{

    background: white;

    border: 1px solid #e1ebe4;

    border-radius: 22px;

    padding: 20px;

    text-decoration: none;

    color: #17221b;

    display: block;

    transition:
        transform .25s,
        box-shadow .25s;
}}

.room-card:hover {{

    transform: translateY(-7px);

    box-shadow:
        0 20px 40px rgba(20,40,25,0.10);
}}

.room-top {{

    display: flex;

    align-items: center;

    justify-content: space-between;

    margin-bottom: 18px;
}}

.room-icon {{

    width: 45px;

    height: 45px;

    border-radius: 14px;

    background: #edf8f0;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 21px;
}}

.status-normal {{

    color: #15803d;

    background: #eaf8ee;

    padding: 6px 9px;

    border-radius: 20px;

    font-size: 9px;

    font-weight: 850;
}}

.room-card h3 {{

    font-size: 14px;

    margin-bottom: 5px;
}}

.room-card .location {{

    color: #89958d;

    font-size: 10px;
}}

.room-consumption {{

    border-top: 1px solid #edf1ee;

    margin-top: 17px;

    padding-top: 13px;
}}

.room-consumption small {{
    color: #8a968e;
    font-size: 10px;
}}

.room-consumption strong {{

    display: block;

    color: #15803d;

    font-size: 19px;

    margin-top: 3px;
}}


/* ============================================================
   GRAPHIQUE
============================================================ */

.chart-card {{

    background: white;

    border: 1px solid #e1ebe4;

    border-radius: 25px;

    padding: 25px;

    box-shadow:
        0 12px 35px rgba(20,40,25,0.055);

    min-height: 350px;
}}

.chart-card h3 {{
    font-size: 16px;
    margin-bottom: 5px;
}}

.chart-card p {{

    color: #849087;

    font-size: 11px;

    margin-bottom: 18px;
}}

.chart-container {{

    position: relative;

    height: 275px;
}}


/* ============================================================
   TABLEAU
============================================================ */

.table-card {{

    background: white;

    border: 1px solid #e1ebe4;

    border-radius: 24px;

    padding: 22px;

    overflow-x: auto;

    box-shadow:
        0 12px 35px rgba(20,40,25,0.05);
}}

table {{

    width: 100%;

    border-collapse: collapse;

    font-size: 12px;
}}

th {{

    text-align: left;

    color: #7a877f;

    font-size: 10px;

    text-transform: uppercase;

    padding: 13px;

    border-bottom: 1px solid #e8eee9;
}}

td {{

    padding: 14px 13px;

    border-bottom: 1px solid #f0f3f1;
}}

.badge {{

    display: inline-block;

    padding: 6px 9px;

    border-radius: 15px;

    font-size: 9px;

    font-weight: 850;
}}

.badge-red {{
    background: #fff0f0;
    color: #dc2626;
}}

.badge-green {{
    background: #eaf8ee;
    color: #15803d;
}}

.badge-orange {{
    background: #fff5e6;
    color: #d97706;
}}


/* ============================================================
   MODULES DU BAS
============================================================ */

.modules {{

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 14px;
}}

.module {{

    min-height: 105px;

    border-radius: 21px;

    padding: 19px;

    text-decoration: none;

    color: white;

    display: flex;

    align-items: center;

    gap: 13px;

    transition:
        transform .25s,
        box-shadow .25s;
}}

.module:hover {{

    transform: translateY(-6px);

    box-shadow:
        0 20px 35px rgba(20,40,25,0.13);
}}

.module-icon {{

    width: 45px;

    height: 45px;

    border-radius: 14px;

    background: rgba(255,255,255,0.18);

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 19px;

    flex-shrink: 0;
}}

.module h3 {{
    font-size: 13px;
}}

.module p {{

    margin-top: 4px;

    font-size: 10px;

    opacity: .8;

    line-height: 1.4;
}}

.module-analysis {{
    background: linear-gradient(135deg,#2563eb,#1d4ed8);
}}

.module-history {{
    background: linear-gradient(135deg,#7c3aed,#5b21b6);
}}

.module-alert {{
    background: linear-gradient(135deg,#ef4444,#b91c1c);
}}

.module-optimization {{
    background: linear-gradient(135deg,#16a34a,#15803d);
}}


/* ============================================================
   FOOTER
============================================================ */

footer {{

    width: calc(100% - 40px);

    max-width: 1500px;

    margin: 0 auto 30px;

    padding: 22px;

    text-align: center;

    color: #8a968e;

    font-size: 11px;
}}


/* ============================================================
   RESPONSIVE
============================================================ */

@media(max-width:1100px) {{

    .grid-4 {{
        grid-template-columns: repeat(2,1fr);
    }}

    .rooms {{
        grid-template-columns: repeat(2,1fr) !important;
    }}

    .modules {{
        grid-template-columns: repeat(2,1fr);
    }}

    .main-layout {{
        grid-template-columns: 1fr !important;
    }}
}}

@media(max-width:750px) {{

    .navbar {{
        width: calc(100% - 20px);
    }}

    .menu {{
        display: none;
    }}

    .container {{
        width: calc(100% - 20px);
    }}

    .grid-4,
    .grid-3,
    .grid-2 {{
        grid-template-columns: 1fr;
    }}

    .hero {{
        padding: 28px;
    }}

    .hero h1 {{
        font-size: 42px;
    }}

    .hero-orbit,
    .hero-core {{
        display: none;
    }}

    .rooms {{
        grid-template-columns: 1fr !important;
    }}

    .modules {{
        grid-template-columns: 1fr;
    }}

}}



/* BARRE DES COMMANDES */
.top-toolbar {{ display:flex; justify-content:flex-end; align-items:center; gap:10px; margin:18px 30px 0 292px; position:relative; z-index:90; }}
.toolbar-button {{ border:1px solid #dce9df; background:#fff; color:#173d2a; border-radius:12px; padding:10px 14px; font-weight:800; font-size:12px; cursor:pointer; transition:.2s; }}
.toolbar-button:hover {{ border-color:#238653; transform:translateY(-1px); }}
.translate-panel {{ display:none; background:#fff; border:1px solid #dce9df; border-radius:14px; padding:12px; box-shadow:0 12px 30px rgba(0,0,0,.12); }}
.translate-panel.open {{ display:block; }}
.goog-te-gadget {{ font-family:inherit !important; font-size:12px !important; }}
.goog-te-gadget .goog-te-combo {{ padding:7px; border:1px solid #dce9df; border-radius:8px; max-width:190px; }}
body.dark-mode {{ background:#080d0a !important; color:#e6f3e9 !important; }}
body.dark-mode .hero, body.dark-mode .stat-card, body.dark-mode .room-card, body.dark-mode .chart-card, body.dark-mode .table-card, body.dark-mode .floor-button, body.dark-mode .translate-panel {{ background:#111b15 !important; color:#e8f5ec !important; border-color:#244431 !important; box-shadow:0 12px 32px rgba(0,0,0,.25); }}
body.dark-mode .hero {{ background:linear-gradient(120deg,#101b14,#14291c) !important; }}
body.dark-mode .hero p, body.dark-mode .page-header p, body.dark-mode .section-title p, body.dark-mode .chart-card p, body.dark-mode .stat-label, body.dark-mode .room-card .location, body.dark-mode .room-consumption small {{ color:#9eb5a5 !important; }}
body.dark-mode .stat-value, body.dark-mode .chart-card h3, body.dark-mode .section-title h2, body.dark-mode .page-header h1, body.dark-mode .room-card h3 {{ color:#e8f5ec !important; }}
body.dark-mode th {{ color:#a9c2b1 !important; border-color:#294333 !important; }}
body.dark-mode td {{ border-color:#20372a !important; color:#dcebe1; }}
body.dark-mode .room-consumption {{ border-color:#263d2e !important; }}
body.dark-mode .floor-button {{ color:#e8f5ec !important; }}
body.dark-mode .floor-button:hover, body.dark-mode .floor-button.selected {{ background:#173d29 !important; border-color:#35a866 !important; }}
body.dark-mode .floor-badge {{ background:#214b32 !important; color:#baf2ce !important; }}
body.dark-mode .building-visual {{ background:linear-gradient(150deg,#071b10,#123d25) !important; }}
body.dark-mode .page-header .tag {{ background:#173d29 !important; color:#a8efbf !important; }}
body.dark-mode .stat-icon.green, body.dark-mode .room-icon {{ background:#183d28 !important; color:#9cebb5 !important; }}
body.dark-mode .toolbar-button {{ background:#14251a; color:#dff5e6; border-color:#2c5238; }}
body.dark-mode footer {{ color:#829b8b !important; }}
@media(max-width:900px) {{ .top-toolbar {{ margin:12px 12px 0; justify-content:flex-end; flex-wrap:wrap; }} }}

/* ============================================================
   NOUVELLE INTERFACE : SIDEBAR VERTICALE
============================================================ */
body {{ background: #f5f8f5; }}
.navbar {{
    position: fixed; left: 18px; top: 18px; bottom: 18px;
    width: 248px; height: auto; min-height: 0; margin: 0;
    padding: 22px 15px; border-radius: 24px;
    display: flex; flex-direction: column; align-items: stretch;
    justify-content: flex-start; gap: 28px; overflow-y: auto;
    background: #103d2b; border: 1px solid #174d37;
    box-shadow: 0 18px 45px rgba(16,61,43,.16);
}}
.navbar .logo {{ color: #fff; font-size: 16px; line-height: 1.35; }}
.navbar .logo span {{ color: #a7f3c2; }}
.logo-icon {{ background: #1c8a55; box-shadow: 0 8px 20px rgba(0,0,0,.18); flex-shrink: 0; }}
.menu {{ display: flex; flex-direction: column; align-items: stretch; gap: 7px; flex-wrap: nowrap; }}
.menu a {{ display: flex; align-items: center; gap: 12px; color: #d2e6d9; font-size: 13px; padding: 13px 14px; border-radius: 13px; }}
.menu a:hover {{ background: rgba(255,255,255,.10); color: #fff; transform: translateX(3px); }}
.menu a.active {{ background: #e5f8eb; color: #12472f; box-shadow: 0 5px 15px rgba(0,0,0,.08); }}
.clock-container {{ margin-top: auto; color: #fff; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.08); }}
.clock {{ color: #fff; }}
.container {{ width: auto; max-width: none; margin: 28px 30px 55px 292px; }}
footer {{ margin-left: 280px; padding: 20px; text-align: center; color: #738277; }}
.room-card, .stat-card, .chart-card, .table-card, .module {{ transition: transform .25s ease, box-shadow .25s ease; }}
.room-card:hover, .stat-card:hover, .module:hover {{ transform: translateY(-5px); box-shadow: 0 18px 36px rgba(16,61,43,.12); }}
.building-layout {{ display:grid; grid-template-columns:minmax(270px, .9fr) minmax(320px,1.1fr); gap:22px; align-items:stretch; }}
.building-visual {{ background:linear-gradient(150deg,#123f2d,#1d6946); color:white; border-radius:24px; padding:25px; box-shadow:0 15px 35px rgba(16,61,43,.15); }}
.building-visual h2 {{ margin-bottom:8px; }}
.building-svg {{ width:100%; max-height:420px; margin-top:12px; }}
.building-equipments {{ margin-top:12px; padding:10px 0 0 16px; border-top:1px solid #e6eee8; font-size:11px; }}
.building-equipments li {{ margin:5px 0; }}
.building-equipments small {{ color:#849087; }}
body.dark-mode .building-equipments {{ border-color:#294333 !important; }}
body.dark-mode .building-equipments small {{ color:#9eb5a5 !important; }}
.floor-list {{ display:grid; gap:10px; margin-top:18px; }}
.floor-button {{ display:flex; justify-content:space-between; align-items:center; gap:12px; width:100%; border:1px solid #dce9df; background:white; color:#163c2a; padding:16px 18px; border-radius:16px; text-decoration:none; font-weight:750; transition:.2s; }}
.floor-button:hover, .floor-button.selected {{ border-color:#238653; background:#eaf8ef; transform:translateX(3px); }}
.floor-badge {{ border-radius:10px; padding:6px 9px; background:#e0f4e7; color:#17633a; font-size:11px; }}
.history-controls {{ display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin:15px 0 8px; }}
.history-controls input[type=range] {{ flex:1; min-width:180px; accent-color:#167544; }}
.history-controls button {{ border:0; border-radius:10px; padding:9px 13px; background:#164c33; color:#fff; cursor:pointer; font-weight:700; }}
@media(max-width:900px) {{
 .navbar {{ position:relative; inset:auto; width:calc(100% - 24px); margin:12px; height:auto; padding:15px; gap:14px; }}
 .menu {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); }}
 .container {{ margin:20px 12px 40px; }} footer {{ margin-left:0; }}
 .building-layout {{ grid-template-columns:1fr; }}
}}
</style>

</head>


<body>


<!-- ========================================================
     NAVBAR
========================================================= -->

<nav class="navbar">
    <a href="/" class="logo">
        <div class="logo-icon">⚡</div>
        <span style="color:#fff">Smart <span>Energy</span><br>Monitor</span>
    </a>
    <div class="menu">
        <a href="/" class="{"active" if active == "home" else ""}"><span>▦</span> Accueil</a>
        <a href="/batiment" class="{"active" if active == "batiment" else ""}"><span>▤</span> Bâtiment</a>
        <a href="/historique" class="{"active" if active == "historique" else ""}"><span>⌁</span> Historique</a>
        <a href="/comparaisons" class="{"active" if active == "comparaisons" else ""}"><span>▥</span> Comparaisons</a>
        <a href="/alertes" class="{"active" if active == "alertes" else ""}"><span>♧</span> Alertes</a>
        <a href="/optimisations" class="{"active" if active == "optimisations" else ""}"><span>✳</span> Optimisations</a>
    </div>
    <div class="clock-container"><div class="live-dot"></div><div><div id="clock" class="clock">--:--:--</div><small style="color:#c5e6d1">Système en direct</small></div></div>
</nav>

<div class="top-toolbar">
  <button class="toolbar-button" id="themeToggle" type="button">◐ Mode sombre</button>
  <button class="toolbar-button" id="translateToggle" type="button">文 Traduire</button>
  <div class="translate-panel" id="translatePanel"><div id="google_translate_element"></div></div>
</div>

<!-- ========================================================
     CONTENU
========================================================= -->

<main class="container">

{content}

</main>


<footer>

    ⚡ Smart Energy Monitor
    — Système intelligent de gestion de l'électricité

</footer>


<script>

/* ==========================================================
   HORLOGE
========================================================== */

function updateClock() {{

    const now = new Date();

    const heures =
        String(now.getHours()).padStart(2,"0");

    const minutes =
        String(now.getMinutes()).padStart(2,"0");

    const secondes =
        String(now.getSeconds()).padStart(2,"0");

    document.getElementById("clock").textContent =
        heures + ":" + minutes + ":" + secondes;
}}

updateClock();
setInterval(updateClock,1000);

const themeToggle = document.getElementById("themeToggle");
function applyTheme(mode) {{
  document.body.classList.toggle("dark-mode", mode === "dark");
  if (themeToggle) themeToggle.textContent = mode === "dark" ? "☀ Mode clair" : "◐ Mode sombre";
  if (window.Chart) {{
    Chart.defaults.color = mode === "dark" ? "#d7e9dc" : "#66766b";
    Chart.defaults.borderColor = mode === "dark" ? "#294333" : "#e4ece6";
    Chart.defaults.plugins.legend.labels.color = mode === "dark" ? "#d7e9dc" : "#66766b";
    document.querySelectorAll("canvas").forEach(canvas => {{
      const chart = Chart.getChart(canvas);
      if (!chart) return;
      if (chart.options.scales) Object.values(chart.options.scales).forEach(axis => {{
        axis.ticks = axis.ticks || {{}};
        axis.ticks.color = mode === "dark" ? "#c4d8ca" : "#66766b";
        axis.grid = axis.grid || {{}};
        axis.grid.color = mode === "dark" ? "rgba(160,205,174,.13)" : "rgba(80,110,90,.10)";
      }});
      chart.update("none");
    }});
  }}
}}
let savedTheme = "light";
try {{ savedTheme = localStorage.getItem("energix-theme") || "light"; }} catch (e) {{}}
applyTheme(savedTheme);
if (themeToggle) themeToggle.addEventListener("click", () => {{
  const next = document.body.classList.contains("dark-mode") ? "light" : "dark";
  try {{ localStorage.setItem("energix-theme", next); }} catch (e) {{}}
  applyTheme(next);
}});

const translateToggle = document.getElementById("translateToggle");
const translatePanel = document.getElementById("translatePanel");
if (translateToggle && translatePanel) translateToggle.addEventListener("click", () => translatePanel.classList.toggle("open"));
function googleTranslateElementInit() {{
  if (window.google && google.translate) new google.translate.TranslateElement({{pageLanguage:"fr", includedLanguages:"en,ar,so,aa,fr,es,zh-CN,ja", autoDisplay:false}}, "google_translate_element");
}}
</script>
<script src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit" defer></script>


</body>

</html>
"""


# ============================================================
# ACCUEIL
# ============================================================

@app.route("/")
def home():

    db = get_db()
    cur = db.cursor()

    # --------------------------------------------------------
    # STATISTIQUES
    # --------------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM salles
    """)

    nombre_salles = cur.fetchone()["total"]

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM equipements
    """)

    nombre_equipements = cur.fetchone()["total"]

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM alertes
    """)

    nombre_alertes = cur.fetchone()["total"]

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM optimisations
    """)

    nombre_optimisations = cur.fetchone()["total"]

    cur.execute("""
        SELECT COALESCE(SUM(energie),0) AS total
        FROM consommations
    """)

    energie_totale = safe_float(
        cur.fetchone()["total"]
    )

    # --------------------------------------------------------
    # DERNIÈRE PUISSANCE
    # --------------------------------------------------------

    cur.execute("""
        SELECT SUM(puissance) AS puissance
        FROM consommations
        WHERE date_heure = (
            SELECT MAX(date_heure)
            FROM consommations
        )
    """)

    puissance_actuelle = safe_float(
        cur.fetchone()["puissance"]
    )

    # --------------------------------------------------------
    # SALLES
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            s.id,
            s.nom,
            s.description,
            s.localisation,
            COALESCE(SUM(c.energie),0) AS energie

        FROM salles s

        LEFT JOIN equipements e
            ON e.salle_id = s.id

        LEFT JOIN consommations c
            ON c.equipement_id = e.id

        GROUP BY
            s.id,
            s.nom,
            s.description,
            s.localisation

        ORDER BY s.id
    """)

    salles = cur.fetchall()

    # --------------------------------------------------------
    # DERNIÈRE MESURE
    # --------------------------------------------------------

    cur.execute("""
        SELECT MAX(date_heure) AS date
        FROM consommations
    """)

    derniere_mesure = cur.fetchone()["date"]

    cur.execute("""
        SELECT substr(date_heure, 12, 5) AS heure, COALESCE(SUM(energie), 0) AS energie
        FROM consommations
        WHERE date(date_heure) = date('now', 'localtime')
        GROUP BY substr(date_heure, 12, 5)
        ORDER BY heure ASC
    """)
    consommation_jour = cur.fetchall()
    labels_jour = [x["heure"] or "-" for x in consommation_jour]
    energies_jour = [safe_float(x["energie"]) for x in consommation_jour]

    db.close()

    # --------------------------------------------------------
    # ICÔNES DES SALLES
    # --------------------------------------------------------

    icones = {
        "Salle informatique": "💻",
        "Salle de cours": "📚",
        "Laboratoire": "🔬",
        "Bureau administratif": "🏢",
        "Salle de réunion": "👥"
    }

    # --------------------------------------------------------
    # CARTES SALLES
    # --------------------------------------------------------

    rooms_html = ""

    for salle in salles:

        nom = salle["nom"]

        icone = icones.get(
            nom,
            "🏢"
        )

        rooms_html += f"""

        <a class="room-card"
           href="/salle/{salle["id"]}">

            <div class="room-top">

                <div class="room-icon">
                    {icone}
                </div>

                <span class="status-normal">
                    ● SURVEILLÉE
                </span>

            </div>

            <h3>
                {nom}
            </h3>

            <div class="location">
                {salle["localisation"] or "Localisation non définie"}
            </div>

            <div class="room-consumption">

                <small>
                    Consommation enregistrée
                </small>

                <strong>
                    {safe_float(salle["energie"]):.2f} kWh
                </strong>

            </div>

        </a>
        """

    # --------------------------------------------------------
    # PAGE
    # --------------------------------------------------------

    content = f"""

<!-- HERO -->

<section class="hero">

    <div class="hero-content">

        <div class="hero-status">

            <i></i>

            Système opérationnel

        </div>

        <h1>
            Smart <span>Energy</span><br>
            Monitor
        </h1>

        <p>
            Une plateforme intelligente pour surveiller,
            analyser et optimiser la consommation électrique
            de chaque espace de votre établissement.
        </p>

    </div>


    <div class="hero-orbit"></div>

    <div class="hero-core">
        ⚡
    </div>

</section>


<!-- STATISTIQUES -->

<section class="grid-4">

    <div class="stat-card">

        <div class="stat-top">

            <div class="stat-icon green">
                ⚡
            </div>

        </div>

        <div class="stat-label">
            Énergie enregistrée
        </div>

        <div class="stat-value">
            {energie_totale:.2f}
            <small style="font-size:12px;">kWh</small>
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-top">

            <div class="stat-icon dark">
                📡
            </div>

        </div>

        <div class="stat-label">
            Équipements surveillés
        </div>

        <div class="stat-value">
            {nombre_equipements}
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-top">

            <div class="stat-icon red">
                🚨
            </div>

        </div>

        <div class="stat-label">
            Alertes enregistrées
        </div>

        <div class="stat-value">
            {nombre_alertes}
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-top">

            <div class="stat-icon green">
                🧠
            </div>

        </div>

        <div class="stat-label">
            Optimisations
        </div>

        <div class="stat-value">
            {nombre_optimisations}
        </div>

    </div>

</section>


<!-- EXPLICATION -->

<section class="section-title">

    <h2>
        Comment fonctionne Smart Energy Monitor ?
    </h2>

    <p>
        Le système transforme les données énergétiques
        en informations exploitables.
    </p>

</section>


<section class="grid-2">

    <div class="info-panel">

        <div class="small-title">
            Architecture intelligente
        </div>

        <h2>
            De la donnée<br>
            à la décision.
        </h2>

        <p>
            Chaque étape du système participe à la surveillance
            intelligente de l'énergie.
        </p>


        <div class="step">

            <div class="step-number">
                01
            </div>

            <div>

                <h4>
                    Simulation
                </h4>

                <p>
                    Les équipements produisent des données
                    énergétiques simulées.
                </p>

            </div>

        </div>


        <div class="step">

            <div class="step-number">
                02
            </div>

            <div>

                <h4>
                    Analyse
                </h4>

                <p>
                    Les consommations sont étudiées afin
                    d'identifier les comportements inhabituels.
                </p>

            </div>

        </div>


        <div class="step">

            <div class="step-number">
                03
            </div>

            <div>

                <h4>
                    Alertes
                </h4>

                <p>
                    Le système signale les situations
                    nécessitant une attention.
                </p>

            </div>

        </div>


        <div class="step">

            <div class="step-number">
                04
            </div>

            <div>

                <h4>
                    Optimisation
                </h4>

                <p>
                    Les données permettent de générer
                    des recommandations énergétiques.
                </p>

            </div>

        </div>

    </div>


    <div>

        <div class="chart-card">

            <h3>
                État actuel du système
            </h3>

            <p>
                Vue générale des principaux indicateurs.
            </p>

            <div class="chart-container">

                <canvas id="homeChart"></canvas>

            </div>

        </div>

    </div>

</section>


<section class="chart-card" style="margin:22px 0">
    <h3>Consommation du jour</h3>
    <p>Énergie mesurée aujourd’hui, regroupée par heure à partir de la base SQLite.</p>
    <div class="chart-container"><canvas id="dailyEnergyChart"></canvas></div>
</section>
<script>
new Chart(document.getElementById("dailyEnergyChart"), {{
 type:"line", data:{{labels:{json_data(labels_jour)},datasets:[{{label:"Énergie (kWh)",data:{json_data(energies_jour)},borderColor:"#167544",backgroundColor:"rgba(22,117,68,.12)",fill:true,tension:.35,pointRadius:3}}]}},
 options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:true}}}},scales:{{y:{{beginAtZero:true}}}}}}
}});
</script>

<!-- SALLES -->

<section class="section-title">

    <h2>
        🏢 Espaces surveillés
    </h2>

    <p>
        Sélectionnez une salle pour accéder à son analyse détaillée.
    </p>

</section>


<div class="rooms"
     style="
        display:grid;
        grid-template-columns:repeat(5,1fr);
        gap:14px;
     ">

    {rooms_html}

</div>


<!-- DERNIÈRE ACTIVITÉ -->

<section class="section-title">

    <h2>
        📡 Activité du système
    </h2>

</section>


<div class="grid-3">

    <div class="stat-card">

        <div class="stat-label">
            Puissance dernière mesure
        </div>

        <div class="stat-value">
            {puissance_actuelle:.3f}
            <small style="font-size:12px;">kW</small>
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-label">
            Salles surveillées
        </div>

        <div class="stat-value">
            {nombre_salles}
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-label">
            Dernière mesure
        </div>

        <div style="
            margin-top:8px;
            font-size:14px;
            font-weight:800;
        ">
            {format_date(derniere_mesure)}
        </div>

    </div>

</div>


<!-- MODULES -->

<section class="section-title">

    <h2>
        Modules
    </h2>

    <p>
        Accédez directement aux différentes fonctions du système.
    </p>

</section>


<div class="modules">

    <a href="/historique"
       class="module module-history">

        <div class="module-icon">
            📜
        </div>

        <div>

            <h3>
                Historique
            </h3>

            <p>
                Explorer les données énergétiques.
            </p>

        </div>

    </a>


    <a href="/comparaisons"
       class="module module-analysis">

        <div class="module-icon">
            📊
        </div>

        <div>

            <h3>
                Comparaisons
            </h3>

            <p>
                Comparer les performances des salles.
            </p>

        </div>

    </a>


    <a href="/alertes"
       class="module module-alert">

        <div class="module-icon">
            🚨
        </div>

        <div>

            <h3>
                Alertes
            </h3>

            <p>
                Consulter les anomalies détectées.
            </p>

        </div>

    </a>


    <a href="/optimisations"
       class="module module-optimization">

        <div class="module-icon">
            🧠
        </div>

        <div>

            <h3>
                Optimisations
            </h3>

            <p>
                Découvrir les recommandations.
            </p>

        </div>

    </a>

</div>


<script>

new Chart(

    document.getElementById("homeChart"),

    {{

        type: "doughnut",

        data: {{

            labels: [
                "Salles",
                "Équipements",
                "Alertes",
                "Optimisations"
            ],

            datasets: [{{

                data: [
                    {nombre_salles},
                    {nombre_equipements},
                    {nombre_alertes},
                    {nombre_optimisations}
                ]

            }}]

        }},

        options: {{

            responsive: true,

            maintainAspectRatio: false,

            cutout: "68%",

            plugins: {{

                legend: {{

                    position: "bottom"

                }}

            }}

        }}

    }}

);

</script>

"""

    return page_template(
        "Accueil",
        content,
        "home"
    )


# ============================================================
# PAGE D'UNE SALLE
# ============================================================

@app.route("/salle/<int:salle_id>")
def salle(salle_id):

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT *
        FROM salles
        WHERE id = ?
    """, (salle_id,))

    salle_data = cur.fetchone()

    if not salle_data:
        db.close()
        abort(404)

    # --------------------------------------------------------
    # ÉQUIPEMENTS
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            e.id,
            e.nom,
            e.type,
            e.etat,
            COALESCE(SUM(c.energie),0) AS energie,
            COALESCE(AVG(c.puissance),0) AS puissance

        FROM equipements e

        LEFT JOIN consommations c
            ON c.equipement_id = e.id

        WHERE e.salle_id = ?

        GROUP BY
            e.id,
            e.nom,
            e.type,
            e.etat

        ORDER BY e.id
    """, (salle_id,))

    equipements = cur.fetchall()

    # --------------------------------------------------------
    # CONSOMMATION TOTALE
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            COALESCE(SUM(c.energie),0) AS energie,
            COALESCE(AVG(c.puissance),0) AS puissance
        FROM consommations c

        JOIN equipements e
            ON e.id = c.equipement_id

        WHERE e.salle_id = ?
    """, (salle_id,))

    stats = cur.fetchone()

    # --------------------------------------------------------
    # HISTORIQUE PAR MESURE
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            c.date_heure,
            SUM(c.energie) AS energie,
            SUM(c.puissance) AS puissance

        FROM consommations c

        JOIN equipements e
            ON e.id = c.equipement_id

        WHERE e.salle_id = ?

        GROUP BY c.date_heure

        ORDER BY c.date_heure DESC

        LIMIT 30
    """, (salle_id,))

    historique = list(
        reversed(cur.fetchall())
    )

    db.close()

    labels = [
        str(x["date_heure"])[11:16]
        for x in historique
    ]

    energie = [
        safe_float(x["energie"])
        for x in historique
    ]

    equip_labels = [
        x["nom"]
        for x in equipements
    ]

    equip_values = [
        safe_float(x["energie"])
        for x in equipements
    ]

    equip_html = ""

    for equipement in equipements:

        equip_html += f"""

        <tr>

            <td>
                <strong>
                    {equipement["nom"]}
                </strong>
            </td>

            <td>
                {equipement["type"] or "-"}
            </td>

            <td>
                {equipement["etat"] or "-"}
            </td>

            <td>
                {safe_float(equipement["puissance"]):.3f} kW
            </td>

            <td>
                {safe_float(equipement["energie"]):.3f} kWh
            </td>

        </tr>

        """

    content = f"""

<div class="page-header">

    <div class="tag">
        Salle surveillée
    </div>

    <h1>
        {salle_data["nom"]}
    </h1>

    <p>
        {salle_data["description"] or
         "Analyse détaillée de la consommation énergétique."}
    </p>

</div>


<div class="grid-4">

    <div class="stat-card">

        <div class="stat-label">
            Énergie
        </div>

        <div class="stat-value">
            {safe_float(stats["energie"]):.2f}
            <small style="font-size:12px;">kWh</small>
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-label">
            Puissance moyenne
        </div>

        <div class="stat-value">
            {safe_float(stats["puissance"]):.3f}
            <small style="font-size:12px;">kW</small>
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-label">
            Équipements
        </div>

        <div class="stat-value">
            {len(equipements)}
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-label">
            Localisation
        </div>

        <div style="
            margin-top:10px;
            font-size:13px;
            font-weight:800;
        ">
            {salle_data["localisation"] or "-"}
        </div>

    </div>

</div>


<section class="section-title">

    <h2>
        📊 Analyse de la salle
    </h2>

    <p>
        Évolution de la consommation et répartition
        entre les équipements.
    </p>

</section>


<div class="grid-2">

    <div class="chart-card">

        <h3>
            Évolution de la consommation
        </h3>

        <p>
            Mesures enregistrées dans la base.
        </p>

        <div class="chart-container">

            <canvas id="roomLine"></canvas>

        </div>

    </div>


    <div class="chart-card">

        <h3>
            Consommation par équipement
        </h3>

        <p>
            Répartition de l'énergie enregistrée.
        </p>

        <div class="chart-container">

            <canvas id="roomPie"></canvas>

        </div>

    </div>

</div>


<section class="section-title">

    <h2>
        🔌 Équipements
    </h2>

</section>


<div class="table-card">

<table>

<thead>

<tr>

    <th>Équipement</th>
    <th>Type</th>
    <th>État</th>
    <th>Puissance moyenne</th>
    <th>Énergie</th>

</tr>

</thead>

<tbody>

{equip_html}

</tbody>

</table>

</div>


<script>

const roomLabels =
    {json_data(labels)};

const roomEnergy =
    {json_data(energie)};

const equipLabels =
    {json_data(equip_labels)};

const equipValues =
    {json_data(equip_values)};


new Chart(

    document.getElementById("roomLine"),

    {{

        type: "line",

        data: {{

            labels: roomLabels,

            datasets: [{{

                label: "Énergie (kWh)",

                data: roomEnergy,

                tension: 0.35,

                fill: true

            }}]

        }},

        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{ intersect: false, mode: "index" }},
            scales: {{ x: {{ ticks: {{ maxTicksLimit: 12 }} }} }}
        }}

    }}

);


new Chart(

    document.getElementById("roomPie"),

    {{

        type: "doughnut",

        data: {{

            labels: equipLabels,

            datasets: [{{

                data: equipValues

            }}]

        }},

        options: {{

            responsive: true,

            maintainAspectRatio: false,

            cutout: "58%",

            plugins: {{

                legend: {{

                    position: "bottom"

                }}

            }}

        }}

    }}

);

</script>

"""

    return page_template(
        salle_data["nom"],
        content,
        "home"
    )


# ============================================================
# BÂTIMENT : ÉTAGES ET SALLES
# ============================================================

@app.route("/batiment")
@app.route("/batiment/<int:etage>")
def batiment(etage=0):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.id, s.nom, s.description, s.localisation,
               COUNT(DISTINCT e.id) AS nb_equipements,
               COALESCE(SUM(c.energie), 0) AS energie
        FROM salles s
        LEFT JOIN equipements e ON e.salle_id = s.id
        LEFT JOIN consommations c ON c.equipement_id = e.id
        GROUP BY s.id, s.nom, s.description, s.localisation
        ORDER BY s.id
    """)
    toutes_salles = cur.fetchall()
    # Liste réelle des équipements associés à chaque salle.
    cur.execute("SELECT salle_id, nom, type, etat FROM equipements ORDER BY salle_id, id")
    equipements_par_salle = {}
    for eq in cur.fetchall():
        equipements_par_salle.setdefault(eq["salle_id"], []).append(eq)

    db.close()

    noms_etages = {1: "Rez-de-chaussée", 2: "1er étage", 3: "2e étage", 4: "3e étage"}
    import re
    def niveau_depuis_localisation(localisation):
        texte = (localisation or "").lower()
        if re.search(r"rez[- ]?de[- ]?chaussée|\brdc\b", texte): return 1
        if re.search(r"1er|premier|étage 1|etage 1", texte): return 2
        if re.search(r"2e|2ème|deuxième|étage 2|etage 2", texte): return 3
        if re.search(r"3e|3ème|troisième|étage 3|etage 3", texte): return 4
        return None
    if etage in noms_etages:
        salles_etage = [s for s in toutes_salles if niveau_depuis_localisation(s["localisation"]) == etage]
        titre_etage = noms_etages[etage]
    else:
        salles_etage = toutes_salles
        titre_etage = "Toutes les salles"
    if not salles_etage:
        salles_html = '<div class="info-panel"><h3>Aucune salle enregistrée à cet étage</h3><p>Ajoutez les salles dans votre base de données pour les afficher ici. Aucune donnée n’a été créée ou modifiée automatiquement.</p></div>'
    else:
        salles_html = '<div class="grid-2">'
        for salle in salles_etage:
            equipements_html = "".join(
                f"<li>{eq['nom']} <small>{eq['type'] or 'Type non précisé'} · {eq['etat'] or 'État non précisé'}</small></li>"
                for eq in equipements_par_salle.get(salle["id"], [])
            ) or "<li>Aucun équipement enregistré</li>"
            salles_html += f"""<a class="room-card" href="/salle/{salle["id"]}">
              <div class="room-top"><div class="room-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 7h2m2 0h2M9 11h2m2 0h2M9 15h2m2 0h2M10 21v-3h4v3"/></svg></div><span class="status-normal">SURVEILLÉE</span></div>
              <h3>{salle["nom"]}</h3><div class="location">{salle["localisation"] or "Localisation non renseignée"}</div>
              <div class="room-consumption"><small>Consommation enregistrée</small><strong>{safe_float(salle["energie"]):.3f} kWh</strong></div>
              <small style="color:#718078">{salle["nb_equipements"]} équipement(s)</small>
              <ul class="building-equipments">{equipements_html}</ul></a>"""
        salles_html += '</div>'

    floors = f'<a class="floor-button{" selected" if etage == 0 else ""}" href="/batiment"><span>▦ Toutes les salles</span><span class="floor-badge">{len(toutes_salles)}</span></a>'
    for numero, nom in noms_etages.items():
        selected = ' selected' if numero == etage else ''
        count = sum(1 for s in toutes_salles if niveau_depuis_localisation(s["localisation"]) == numero)
        floors += f'<a class="floor-button{selected}" href="/batiment/{numero}"><span><span style="color:#21814b;margin-right:10px">▦</span>{nom}</span><span class="floor-badge">{count} salle(s)</span></a>'

    building_svg = """<svg class="building-svg" viewBox="0 0 320 360" role="img" aria-label="Illustration du bâtiment à quatre niveaux">
      <defs><linearGradient id="facade" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f4fff7"/><stop offset="1" stop-color="#b8e4c7"/></linearGradient></defs>
      <path d="M45 83 L160 24 L275 83" fill="none" stroke="#c9f5d8" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="52" y="80" width="216" height="245" rx="7" fill="url(#facade)" stroke="#8bc9a0" stroke-width="3"/>
      <rect x="140" y="270" width="40" height="55" rx="3" fill="#19563a"/>
      <g fill="#1f8050" stroke="#17643e" stroke-width="2"><rect x="73" y="99" width="42" height="31" rx="3"/><rect x="137" y="99" width="42" height="31" rx="3"/><rect x="201" y="99" width="42" height="31" rx="3"/><rect x="73" y="157" width="42" height="31" rx="3"/><rect x="137" y="157" width="42" height="31" rx="3"/><rect x="201" y="157" width="42" height="31" rx="3"/><rect x="73" y="215" width="42" height="31" rx="3"/><rect x="137" y="215" width="42" height="31" rx="3"/></g>
      <g fill="#d9f8e4"><path d="M77 103h34v22H77zM141 103h34v22h-34zM205 103h34v22h-34zM77 161h34v22H77zM141 161h34v22h-34zM205 161h34v22h-34zM77 219h34v22H77zM141 219h34v22h-34z"/></g>
      <path d="M35 325h250" stroke="#c9f5d8" stroke-width="6" stroke-linecap="round"/><circle cx="260" cy="47" r="17" fill="#b5edc8"/><path d="M260 36v22M249 47h22" stroke="#19563a" stroke-width="3" stroke-linecap="round"/>
    </svg>"""
    content = f"""<div class="page-header"><div class="tag">GESTION DES ESPACES</div><h1>Bâtiment <span style="color:#21814b">intelligent</span></h1><p>Explorez les niveaux et consultez les salles, équipements et consommations enregistrés.</p></div>
    <div class="building-layout"><section class="building-visual"><div style="font-size:11px;letter-spacing:2px;color:#b9e9c9;font-weight:800">SMART ENERGY MONITOR</div><h2>Votre établissement</h2><p style="color:#d1ead9;line-height:1.6">Consultez les salles, leur localisation, leurs équipements et leurs consommations enregistrées.</p>{building_svg}<div style="display:flex;justify-content:space-between;border-top:1px solid #ffffff30;padding-top:16px"><span style="color:#d1ead9">Salles enregistrées</span><strong>{len(toutes_salles)}</strong></div></section>
    <section><div class="section-title"><h2>Choisir un étage</h2><p>Navigation par niveau</p></div><div class="floor-list">{floors}</div><div class="section-title" style="margin-top:25px"><h2>{titre_etage}</h2><p>{len(salles_etage)} salle(s) affichée(s)</p></div>{salles_html}</section></div>"""
    return page_template("Bâtiment", content, "batiment")


# ============================================================
# HISTORIQUE
# ============================================================

@app.route("/historique")
def historique():

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT
            c.date_heure,
            s.nom AS salle,
            e.nom AS equipement,
            c.puissance,
            c.energie

        FROM consommations c

        JOIN equipements e
            ON e.id = c.equipement_id

        JOIN salles s
            ON s.id = e.salle_id

        ORDER BY c.date_heure ASC
    """)

    donnees = cur.fetchall()

    db.close()

    labels = [
        format_date(x["date_heure"])
        for x in donnees
    ]

    energies = [
        safe_float(x["energie"])
        for x in donnees
    ]

    rows = ""

    for x in donnees:

        rows += f"""

        <tr>

            <td>
                {format_date(x["date_heure"])}
            </td>

            <td>
                {x["salle"]}
            </td>

            <td>
                {x["equipement"]}
            </td>

            <td>
                {safe_float(x["puissance"]):.3f} kW
            </td>

            <td>
                {safe_float(x["energie"]):.4f} kWh
            </td>

        </tr>

        """

    content = f"""

<div class="page-header">

    <div class="tag">
        Données énergétiques
    </div>

    <h1>
        Historique
    </h1>

    <p>
        Consultez les mesures enregistrées par le système
        et observez leur évolution.
    </p>

</div>


<div class="chart-card">

    <h3>
        Évolution des mesures
    </h3>

    <p>
        Toutes les mesures enregistrées dans SQLite, de la première à la plus récente.
    </p>
    <div class="history-controls">
        <button type="button" id="historyPrev">← Précédent</button>
        <input type="range" id="historyRange" min="0" max="0" value="0" aria-label="Parcourir l’historique">
        <button type="button" id="historyNext">Suivant →</button>
        <span id="historyPosition" style="font-size:12px;color:#66766b">Toutes les mesures</span>
    </div>
    <div class="chart-container">
        <canvas id="historyChart"></canvas>
    </div>

</div>


<section class="section-title">

    <h2>
        Dernières mesures
    </h2>

</section>


<div class="table-card">

<table>

<thead>

<tr>

    <th>Date</th>
    <th>Salle</th>
    <th>Équipement</th>
    <th>Puissance</th>
    <th>Énergie</th>

</tr>

</thead>

<tbody>

{rows}

</tbody>

</table>

</div>


<script>

new Chart(

    document.getElementById("historyChart"),

    {{

        type: "line",

        data: {{

            labels:
                {json_data(labels)},

            datasets: [{{

                label: "Énergie (kWh)",

                data:
                    {json_data(energies)},

                tension: 0.3

            }}]

        }},

        options: {{

            responsive: true,

            maintainAspectRatio: false

        }}

    }}

);

const historyChart = Chart.getChart(document.getElementById("historyChart"));
const historyRange = document.getElementById("historyRange");
const historyPosition = document.getElementById("historyPosition");
const historyWindow = 60;
const historyCount = historyChart.data.labels.length;
historyRange.max = Math.max(0, historyCount - historyWindow);
function showHistoryWindow(start) {{
    const maxStart = Math.max(0, historyCount - historyWindow);
    const from = Math.max(0, Math.min(maxStart, Number(start)));
    const to = Math.min(historyCount, from + historyWindow);
    historyChart.data.labels = {json_data(labels)}.slice(from, to);
    historyChart.data.datasets[0].data = {json_data(energies)}.slice(from, to);
    historyChart.update("none");
    historyRange.value = from;
    historyPosition.textContent = historyCount ? `Mesures ${{from + 1}} à ${{to}} sur ${{historyCount}}` : "Aucune mesure";
}}
historyRange.addEventListener("input", () => showHistoryWindow(historyRange.value));
document.getElementById("historyPrev").addEventListener("click", () => showHistoryWindow(Number(historyRange.value) - historyWindow));
document.getElementById("historyNext").addEventListener("click", () => showHistoryWindow(Number(historyRange.value) + historyWindow));
showHistoryWindow(0);

</script>

"""

    return page_template(
        "Historique",
        content,
        "historique"
    )


# ============================================================
# COMPARAISONS
# ============================================================

@app.route("/comparaisons")
def comparaisons():

    db = get_db()
    cur = db.cursor()

    # --------------------------------------------------------
    # SALLES
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            s.nom,
            COALESCE(SUM(c.energie),0) AS energie,
            COALESCE(AVG(c.puissance),0) AS puissance

        FROM salles s

        LEFT JOIN equipements e
            ON e.salle_id = s.id

        LEFT JOIN consommations c
            ON c.equipement_id = e.id

        GROUP BY s.id, s.nom

        ORDER BY energie DESC
    """)

    salles = cur.fetchall()

    # --------------------------------------------------------
    # TYPES D'ÉQUIPEMENTS
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            e.nom,
            COALESCE(SUM(c.energie),0) AS energie

        FROM equipements e

        LEFT JOIN consommations c
            ON c.equipement_id = e.id

        GROUP BY e.nom

        ORDER BY energie DESC
    """)

    equipements = cur.fetchall()

    db.close()

    room_labels = [
        x["nom"]
        for x in salles
    ]

    room_values = [
        safe_float(x["energie"])
        for x in salles
    ]

    equip_labels = [
        x["nom"]
        for x in equipements
    ]

    equip_values = [
        safe_float(x["energie"])
        for x in equipements
    ]

    rows = ""

    for x in salles:

        rows += f"""

        <tr>

            <td>
                <strong>
                    {x["nom"]}
                </strong>
            </td>

            <td>
                {safe_float(x["energie"]):.3f} kWh
            </td>

            <td>
                {safe_float(x["puissance"]):.3f} kW
            </td>

        </tr>

        """

    content = f"""

<div class="page-header">

    <div class="tag">
        Analyse comparative
    </div>

    <h1>
        Comparaisons
    </h1>

    <p>
        Comparez les consommations enregistrées entre
        les différents espaces et équipements.
    </p>

</div>


<div class="grid-2">

    <div class="chart-card">

        <h3>
            Consommation par salle
        </h3>

        <p>
            Comparaison de l'énergie enregistrée.
        </p>

        <div class="chart-container">

            <canvas id="roomsChart"></canvas>

        </div>

    </div>


    <div class="chart-card">

        <h3>
            Consommation par équipement
        </h3>

        <p>
            Contribution des équipements.
        </p>

        <div class="chart-container">

            <canvas id="equipChart"></canvas>

        </div>

    </div>

</div>


<section class="section-title">

    <h2>
        Tableau comparatif
    </h2>

</section>


<div class="table-card">

<table>

<thead>

<tr>

    <th>Salle</th>
    <th>Énergie</th>
    <th>Puissance moyenne</th>

</tr>

</thead>

<tbody>

{rows}

</tbody>

</table>

</div>


<script>

new Chart(

    document.getElementById("roomsChart"),

    {{

        type: "bar",

        data: {{

            labels:
                {json_data(room_labels)},

            datasets: [{{

                label: "Énergie (kWh)",

                data:
                    {json_data(room_values)}

            }}]

        }},

        options: {{

            responsive: true,

            maintainAspectRatio: false,

            indexAxis: "y"

        }}

    }}

);


new Chart(

    document.getElementById("equipChart"),

    {{

        type: "doughnut",

        data: {{

            labels:
                {json_data(equip_labels)},

            datasets: [{{

                data:
                    {json_data(equip_values)}

            }}]

        }},

        options: {{

            responsive: true,

            maintainAspectRatio: false,

            cutout: "58%",

            plugins: {{

                legend: {{

                    position: "bottom"

                }}

            }}

        }}

    }}

);

</script>

"""

    return page_template(
        "Comparaisons",
        content,
        "comparaisons"
    )


# ============================================================
# ALERTES
# ============================================================

@app.route("/alertes")
def alertes():

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT
            a.*,
            s.nom AS salle,
            e.nom AS equipement

        FROM alertes a

        LEFT JOIN salles s
            ON s.id = a.salle_id

        LEFT JOIN equipements e
            ON e.id = a.equipement_id

        ORDER BY a.date_heure DESC

        LIMIT 100
    """)

    alertes_data = cur.fetchall()

    db.close()

    rows = ""

    for alerte in alertes_data:

        niveau = str(
            alerte["niveau"] or "INFO"
        ).upper()

        if niveau in ["CRITIQUE", "HIGH", "HAUTE"]:
            classe = "badge-red"

        elif niveau in ["MOYEN", "MEDIUM"]:
            classe = "badge-orange"

        else:
            classe = "badge-green"

        rows += f"""

        <tr>

            <td>
                {format_date(alerte["date_heure"])}
            </td>

            <td>
                {alerte["salle"] or "-"}
            </td>

            <td>
                {alerte["equipement"] or "-"}
            </td>

            <td>
                <span class="badge {classe}">
                    {niveau}
                </span>
            </td>

            <td>
                {alerte["type"] or "-"}
            </td>

            <td>
                {alerte["message"] or "-"}
            </td>

            <td>
                {alerte["statut"] or "-"}
            </td>

        </tr>

        """

    content = f"""

<div class="page-header">

    <div class="tag">
        Surveillance
    </div>

    <h1>
        Alertes
    </h1>

    <p>
        Les événements détectés par le système
        sont centralisés ici.
    </p>

</div>


<div class="stat-card"
     style="margin-bottom:20px;">

    <div class="stat-top">

        <div class="stat-icon red">
            🚨
        </div>

    </div>

    <div class="stat-label">
        Alertes enregistrées
    </div>

    <div class="stat-value">
        {len(alertes_data)}
    </div>

</div>


<div class="table-card">

<table>

<thead>

<tr>

    <th>Date</th>
    <th>Salle</th>
    <th>Équipement</th>
    <th>Niveau</th>
    <th>Type</th>
    <th>Message</th>
    <th>Statut</th>

</tr>

</thead>

<tbody>

{rows}

</tbody>

</table>

</div>

"""

    return page_template(
        "Alertes",
        content,
        "alertes"
    )


# ============================================================
# OPTIMISATIONS
# ============================================================

@app.route("/optimisations")
def optimisations():

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT
            o.*,
            s.nom AS salle,
            e.nom AS equipement

        FROM optimisations o

        LEFT JOIN salles s
            ON s.id = o.salle_id

        LEFT JOIN equipements e
            ON e.id = o.equipement_id

        ORDER BY o.date_heure DESC

        LIMIT 100
    """)

    optimisations_data = cur.fetchall()

    db.close()

    gain_total = sum(
        safe_float(x["gain_estime"])
        for x in optimisations_data
    )

    rows = ""

    for optimisation in optimisations_data:

        statut = str(
            optimisation["statut"] or "-"
        ).upper()

        rows += f"""

        <tr>

            <td>
                {format_date(optimisation["date_heure"])}
            </td>

            <td>
                <strong>
                    {optimisation["titre"] or "-"}
                </strong>
            </td>

            <td>
                {optimisation["salle"] or "-"}
            </td>

            <td>
                {optimisation["equipement"] or "-"}
            </td>

            <td>
                {optimisation["description"] or "-"}
            </td>

            <td>
                <strong style="color:#15803d;">
                    {safe_float(optimisation["gain_estime"]):.2f}
                </strong>
            </td>

            <td>
                <span class="badge badge-green">
                    {statut}
                </span>
            </td>

        </tr>

        """

    content = f"""

<div class="page-header">

    <div class="tag">
        Intelligence énergétique
    </div>

    <h1>
        Optimisations
    </h1>

    <p>
        Les recommandations produites à partir de
        l'analyse des consommations.
    </p>

</div>


<div class="grid-3">

    <div class="stat-card">

        <div class="stat-icon green">
            🧠
        </div>

        <div class="stat-label">
            Recommandations
        </div>

        <div class="stat-value">
            {len(optimisations_data)}
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-icon green">
            ⚡
        </div>

        <div class="stat-label">
            Gain estimé cumulé
        </div>

        <div class="stat-value">
            {gain_total:.2f}
        </div>

    </div>


    <div class="stat-card">

        <div class="stat-icon dark">
            📡
        </div>

        <div class="stat-label">
            Source
        </div>

        <div style="
            margin-top:10px;
            font-size:13px;
            font-weight:800;
        ">
            Analyse énergétique
        </div>

    </div>

</div>


<section class="section-title">

    <h2>
        Recommandations
    </h2>

</section>


<div class="table-card">

<table>

<thead>

<tr>

    <th>Date</th>
    <th>Recommandation</th>
    <th>Salle</th>
    <th>Équipement</th>
    <th>Description</th>
    <th>Gain</th>
    <th>Statut</th>

</tr>

</thead>

<tbody>

{rows}

</tbody>

</table>

</div>

"""

    return page_template(
        "Optimisations",
        content,
        "optimisations"
    )


# ============================================================
# ERREUR 404
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    content = """

<div style="
    min-height:500px;
    display:flex;
    align-items:center;
    justify-content:center;
    text-align:center;
">

    <div>

        <div style="
            font-size:80px;
            margin-bottom:20px;
        ">
            ⚡
        </div>

        <h1 style="
            font-size:50px;
            margin-bottom:10px;
        ">
            404
        </h1>

        <p style="
            color:#718078;
            margin-bottom:25px;
        ">
            Cette page n'existe pas.
        </p>

        <a href="/"
           style="
                display:inline-block;
                padding:12px 20px;
                border-radius:14px;
                background:#16a34a;
                color:white;
                text-decoration:none;
                font-weight:800;
           ">
            Retour à l'accueil
        </a>

    </div>

</div>

"""

    return page_template(
        "Page introuvable",
        content,
        "home"
    ), 404


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )

