from flask import Flask, render_template_string, abort, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SMART_ENERGY_SECRET", "smart-energy-monitor-local-dev-key-change-before-deployment")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

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


def init_auth_db():
    """Crée uniquement la table des comptes, sans modifier les tables énergétiques."""
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE) as db:
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

    page_notes = {
        "home": "Indicateurs globaux et état général de la plateforme.",
        "batiment": "Vue des espaces enregistrés et de leur consommation.",
        "historique": "Suivi chronologique des mesures enregistrées.",
        "comparaisons": "Comparaison des consommations par espace et équipement.",
        "alertes": "Anomalies énergétiques enregistrées dans la base.",
        "optimisations": "Recommandations associées aux alertes détectées.",
    }
    floating_note = page_notes.get(active, "Espace de gestion Smart Energy Monitor.")

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

/* BATIMENT 3D */
.building-3d{{width:100%;height:390px;border-radius:18px;overflow:hidden;background:#123f2d;cursor:grab}}.building-3d:active{{cursor:grabbing}}.building-3d canvas{{display:block;width:100%;height:100%}}.three-loading{{padding:35px;color:#d1ead9}}.three-help{{font-size:11px;color:#c7e8d1;margin-top:10px}}
/* BARRE D'OUTILS ET COMPTES */
.top-toolbar{{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:0 0 24px;padding:15px 18px;background:rgba(255,255,255,.92);border:1px solid #e1ebe4;border-radius:18px;box-shadow:0 8px 25px rgba(20,40,25,.05)}}
.toolbar-left{{display:flex;flex-direction:column;gap:3px}}.toolbar-left strong{{font-size:18px}}.toolbar-kicker{{font-size:9px;letter-spacing:1.5px;color:#21814b;font-weight:900}}
.toolbar-actions{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}.toolbar-button{{border:1px solid #dce9df;background:#f7fbf8;color:#16452e;padding:10px 13px;border-radius:11px;font-weight:800;font-size:12px;text-decoration:none;cursor:pointer;font-family:inherit}}.signup-link{{background:#168449;color:white;border-color:#168449}}.logout-link{{color:#a33;background:#fff8f8;border-color:#f1dada}}.language-select{{min-width:66px}}
.translate-hidden{{display:none!important}}
.auth-wrap{{max-width:520px;margin:35px auto;background:white;border:1px solid #e1ebe4;border-radius:24px;padding:30px;box-shadow:0 15px 40px rgba(20,40,25,.07)}}.auth-wrap h1{{margin-bottom:8px}}.auth-wrap p{{color:#718078;margin-bottom:22px}}.auth-form{{display:grid;gap:14px}}.auth-form label{{font-size:12px;font-weight:800;color:#315640}}.auth-form input{{width:100%;padding:13px;border:1px solid #dce9df;border-radius:11px;margin-top:6px;font:inherit}}.auth-form button{{border:0;background:#168449;color:white;padding:14px;border-radius:12px;font-weight:900;cursor:pointer}}.auth-message{{padding:12px;border-radius:10px;background:#fff4e5;color:#86520b;margin:12px 0;font-size:13px}}
/* THEME NOIR + VERT : couvre toutes les pages et tableaux */
body.dark-mode{{background:#070b08!important;color:#e7f4ea!important}}
body.dark-mode .container,body.dark-mode main{{color:#e7f4ea}}
body.dark-mode .top-toolbar,body.dark-mode .hero,body.dark-mode .stat-card,body.dark-mode .room-card,body.dark-mode .chart-card,body.dark-mode .table-card,body.dark-mode .floor-button,body.dark-mode .auth-wrap,body.dark-mode .info-panel,body.dark-mode .module,body.dark-mode .translate-panel{{background:#101a13!important;color:#e7f4ea!important;border-color:#244631!important}}
body.dark-mode .hero{{background:linear-gradient(120deg,#0c1710,#14271b)!important}}
body.dark-mode h1,body.dark-mode h2,body.dark-mode h3,body.dark-mode h4,body.dark-mode .stat-value,body.dark-mode .room-card h3,body.dark-mode .chart-card h3,body.dark-mode .section-title h2,body.dark-mode .toolbar-left strong{{color:#e7f4ea!important}}
body.dark-mode p,body.dark-mode small,body.dark-mode .page-header p,body.dark-mode .section-title p,body.dark-mode .stat-label,body.dark-mode .room-card .location,body.dark-mode .chart-card p{{color:#a9c4b1!important}}
body.dark-mode td,body.dark-mode th{{color:#dcebe0!important;border-color:#294333!important}}
body.dark-mode input,body.dark-mode select{{background:#0b130e!important;color:#e7f4ea!important;border-color:#31543c!important}}
body.dark-mode .toolbar-button{{background:#14251a;color:#dff5e6;border-color:#31543c}}
body.dark-mode .signup-link{{background:#168449!important;color:white!important}}
body.dark-mode .room-consumption{{border-color:#294333!important}}
body.dark-mode .floor-button:hover,body.dark-mode .floor-button.selected{{background:#173d29!important;border-color:#35a866!important}}
body.dark-mode .building-visual{{background:linear-gradient(150deg,#071b10,#123d25)!important}}
@media(max-width:800px){{.top-toolbar{{align-items:flex-start;flex-direction:column}}.toolbar-actions{{width:100%}}.toolbar-button{{flex:1;text-align:center}}.auth-wrap{{padding:22px}}}}



/* ============================================================
   DESIGN SYSTEM VERT-BLEU + CARTES FLOTTANTES
============================================================ */
:root {{
  --sem-accent: #168b83;
  --sem-accent-strong: #0f766e;
  --sem-accent-soft: #e4f5f2;
  --sem-ink: #153b37;
  --sem-muted: #718985;
  --sem-line: #dcebe8;
  --sem-surface: #ffffff;
  --sem-bg: #f2f8f7;
}}
body {{
  background:
    radial-gradient(circle at 82% 8%, rgba(22,139,131,.11), transparent 27%),
    radial-gradient(circle at 12% 86%, rgba(72,175,154,.08), transparent 25%),
    var(--sem-bg) !important;
  color: var(--sem-ink);
}}
.navbar {{
  background: linear-gradient(165deg, #103d3a 0%, #0d514b 55%, #12645a 100%) !important;
  border: 1px solid rgba(120,220,202,.18) !important;
  box-shadow: 0 22px 60px rgba(11,67,62,.22) !important;
}}
.logo-icon {{
  background: linear-gradient(135deg, #39b8a5, #168b83) !important;
  color: #fff !important;
  letter-spacing: -1px;
  font-size: 13px !important;
  font-weight: 950;
}}
.navbar .logo span {{ color: #9ce6d8 !important; }}
.menu a {{ color: #d1e9e4 !important; }}
.menu a:hover {{ background: rgba(143,232,214,.13) !important; color: #fff !important; }}
.menu a.active {{ background: linear-gradient(110deg,#e5fbf5,#c9f2e8) !important; color: #0e5149 !important; }}
.nav-mark {{
  width: 30px; height: 30px; flex: 0 0 30px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 9px; font-size: 9px; letter-spacing: .5px;
  font-weight: 900; color: #a8ded3; background: rgba(255,255,255,.09);
}}
.menu a.active .nav-mark {{ color: #0f766e; background: rgba(22,139,131,.12); }}
.clock-container {{ background: rgba(255,255,255,.10) !important; border: 1px solid rgba(255,255,255,.10); }}
.container {{ padding-bottom: 80px; }}
.top-toolbar {{
  background: rgba(255,255,255,.78) !important;
  border-color: var(--sem-line) !important;
  backdrop-filter: blur(18px);
  box-shadow: 0 12px 34px rgba(17,74,68,.07) !important;
}}
.toolbar-kicker, .page-header h1 span {{ color: var(--sem-accent) !important; }}
.toolbar-button {{ border-color: #d3e8e3 !important; color: #14534c !important; background: #f7fcfb !important; }}
.signup-link, .auth-form button {{ background: linear-gradient(135deg,#168b83,#26a997) !important; color: #fff !important; border-color: transparent !important; }}
.hero {{
  background: linear-gradient(118deg,#ffffff 0%,#e8f7f4 58%,#d9f1eb 100%) !important;
  border-color: #d7ebe6 !important;
  box-shadow: 0 26px 70px rgba(14,95,85,.10) !important;
}}
.hero h1 span {{ color: var(--sem-accent) !important; }}
.hero-status, .page-header .tag {{ background: var(--sem-accent-soft) !important; color: var(--sem-accent-strong) !important; }}
.hero-core {{ background: linear-gradient(145deg,#28a995,#0f766e) !important; }}
.stat-card, .room-card, .chart-card, .table-card, .module, .floor-button, .auth-wrap {{
  border-color: var(--sem-line) !important;
  box-shadow: 0 13px 34px rgba(18,82,75,.065) !important;
}}
.stat-card, .room-card, .chart-card, .table-card, .module, .floor-button {{
  animation: sem-card-drift 7s ease-in-out infinite;
  will-change: transform;
}}
.stat-card:nth-child(2n), .room-card:nth-child(2n), .module:nth-child(2n) {{ animation-delay: -2.8s; }}
.stat-card:nth-child(3n), .room-card:nth-child(3n) {{ animation-delay: -4.6s; }}
.stat-card:hover, .room-card:hover, .chart-card:hover, .table-card:hover, .module:hover, .floor-button:hover {{
  transform: translateY(-9px) scale(1.012) !important;
  box-shadow: 0 25px 48px rgba(14,95,85,.15) !important;
  border-color: rgba(22,139,131,.35) !important;
}}
.room-icon, .stat-icon.green {{ background: #e2f5f1 !important; color: #11796f !important; }}
.room-consumption strong, .status-normal {{ color: #11796f !important; }}
.status-normal {{ background: #e3f6f1 !important; }}
.building-visual {{ background: linear-gradient(145deg,#103f3b,#16786d) !important; }}
.floor-button:hover, .floor-button.selected {{ border-color: #38a99a !important; background: #e5f6f2 !important; }}

@keyframes sem-card-drift {{
  0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-4px); }}
}}

/* Carte d'information flottante partagée par toutes les pages */
.floating-insight {{
  position: fixed; right: 26px; bottom: 24px; z-index: 80;
  width: 258px; padding: 16px 17px 13px;
  border: 1px solid rgba(255,255,255,.72); border-radius: 19px;
  color: #eafbf7;
  background: linear-gradient(145deg,rgba(13,66,61,.96),rgba(17,112,100,.94));
  box-shadow: 0 20px 55px rgba(10,70,64,.24), inset 0 1px 0 rgba(255,255,255,.14);
  backdrop-filter: blur(18px);
  animation: sem-float 5.5s ease-in-out infinite;
  transition: transform .3s ease, box-shadow .3s ease;
}}
.floating-insight:hover {{ transform: translateY(-10px) rotate(-.4deg) scale(1.025); box-shadow: 0 28px 65px rgba(10,70,64,.32); }}
.floating-insight-head, .floating-insight-foot {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
.floating-insight-head {{ color:#a9e8dc; font-size:8px; font-weight:900; letter-spacing:1.35px; }}
.floating-live-dot {{ width:7px; height:7px; border-radius:50%; background:#70e3b7; box-shadow:0 0 0 5px rgba(112,227,183,.13); margin-right:1px; }}
.floating-pulse {{ margin-left:auto; padding:4px 6px; border-radius:6px; background:rgba(112,227,183,.15); color:#9af0d0; font-size:8px; letter-spacing:.8px; }}
.floating-insight > strong {{ display:block; margin-top:13px; color:#fff; font-size:14px; letter-spacing:-.2px; }}
.floating-insight p {{ margin-top:5px; color:#c1e4dc; font-size:10px; line-height:1.55; }}
.floating-insight-foot {{ border-top:1px solid rgba(255,255,255,.13); margin-top:12px; padding-top:9px; color:#9bcfc4; font-size:7px; font-weight:800; letter-spacing:1px; }}
.floating-clock {{ color:#fff; font-size:10px; font-variant-numeric:tabular-nums; letter-spacing:.5px; }}
@keyframes sem-float {{ 0%,100% {{ transform:translateY(0); }} 50% {{ transform:translateY(-7px); }} }}

/* Mode sombre complet : surfaces, textes, formulaires, tableaux et composants bâtiment */
body.dark-mode {{
  --sem-bg: #071311; --sem-surface: #10201e; --sem-ink: #e2f4ef;
  --sem-muted: #a0bdb6; --sem-line: #24433e; --sem-accent-soft: #153b36;
  background: radial-gradient(circle at 80% 5%,rgba(24,139,126,.13),transparent 28%),#071311 !important;
  color: #e2f4ef !important;
}}
body.dark-mode .top-toolbar, body.dark-mode .hero, body.dark-mode .stat-card,
body.dark-mode .room-card, body.dark-mode .chart-card, body.dark-mode .table-card,
body.dark-mode .module, body.dark-mode .floor-button, body.dark-mode .auth-wrap,
body.dark-mode .panel, body.dark-mode .comparison-card {{
  background: #10201e !important; color: #e2f4ef !important; border-color: #24433e !important;
}}
body.dark-mode .hero {{ background:linear-gradient(120deg,#0d211e,#12312c) !important; }}
body.dark-mode h1, body.dark-mode h2, body.dark-mode h3, body.dark-mode h4,
body.dark-mode .stat-value, body.dark-mode .room-card h3, body.dark-mode .toolbar-left strong,
body.dark-mode .section-title h2 {{ color:#e8f7f2 !important; }}
body.dark-mode p, body.dark-mode small, body.dark-mode .page-header p,
body.dark-mode .section-title p, body.dark-mode .stat-label,
body.dark-mode .room-card .location, body.dark-mode .chart-card p {{ color:#a8c5bd !important; }}
body.dark-mode td, body.dark-mode th {{ color:#d8eee7 !important; border-color:#294943 !important; }}
body.dark-mode input, body.dark-mode select, body.dark-mode textarea {{
  background:#0a1916 !important; color:#e2f4ef !important; border-color:#31574f !important;
}}
body.dark-mode .toolbar-button {{ background:#142a26 !important; color:#dff5ed !important; border-color:#31574f !important; }}
body.dark-mode .room-consumption {{ border-color:#294943 !important; }}
body.dark-mode .floor-button:hover, body.dark-mode .floor-button.selected {{ background:#173c35 !important; border-color:#3ba994 !important; }}
body.dark-mode .building-visual {{ background:linear-gradient(145deg,#09201c,#10473e) !important; }}
body.dark-mode .floating-insight {{ background:linear-gradient(145deg,rgba(5,25,23,.97),rgba(10,65,58,.97)); border-color:#31574f; }}
body.dark-mode .auth-form label {{ color:#c6e4db !important; }}
body.dark-mode footer {{ color:#91aaa2 !important; }}

@media(max-width:900px) {{
  .floating-insight {{ right:14px; bottom:14px; width:220px; }}
  .container {{ padding-bottom:120px; }}
}}
@media(max-width:600px) {{
  .floating-insight {{ width:calc(100% - 28px); right:14px; bottom:12px; padding:12px 14px; }}
  .floating-insight p {{ max-width:90%; }}
  .container {{ padding-bottom:145px; }}
}}
@media(prefers-reduced-motion:reduce) {{
  .floating-insight, .stat-card, .room-card, .chart-card, .table-card, .module, .floor-button {{ animation:none !important; transition:none !important; }}
}}

</style>

</head>


<body>


<!-- ========================================================
     NAVBAR
========================================================= -->

<nav class="navbar">
    <a href="/" class="logo">
        <div class="logo-icon">SE</div>
        <span style="color:#fff">Smart <span>Energy</span><br>Monitor</span>
    </a>
    <div class="menu">
        <a href="/" class="{"active" if active == "home" else ""}"><span class="nav-mark">01</span> Accueil</a>
        <a href="/batiment" class="{"active" if active == "batiment" else ""}"><span class="nav-mark">02</span> Bâtiment</a>
        <a href="/historique" class="{"active" if active == "historique" else ""}"><span class="nav-mark">03</span> Historique</a>
        <a href="/comparaisons" class="{"active" if active == "comparaisons" else ""}"><span class="nav-mark">04</span> Comparaisons</a>
        <a href="/alertes" class="{"active" if active == "alertes" else ""}"><span class="nav-mark">05</span> Alertes</a>
        <a href="/optimisations" class="{"active" if active == "optimisations" else ""}"><span class="nav-mark">06</span> Optimisations</a>
    </div>
    <div class="clock-container"><div class="live-dot"></div><div><div id="clock" class="clock">--:--:--</div><small style="color:#c5e6d1">Système en direct</small></div></div>
</nav>


<!-- ========================================================
     CONTENU
========================================================= -->

<main class="container">
<div class="top-toolbar">
  <div class="toolbar-left"><span class="toolbar-kicker">ESPACE DE GESTION</span><strong>{title}</strong></div>
  <div class="toolbar-actions">
    <button class="toolbar-button" id="themeToggle" type="button">Mode sombre</button>
    <select class="toolbar-button language-select" id="languageSelect" aria-label="Choisir la langue"><option value="fr">FR</option><option value="en">EN</option><option value="ar">AR</option><option value="so">SO</option><option value="es">ES</option><option value="zh-CN">中文</option></select>
    {f'<a class="toolbar-button account-link" href="/compte">Mon compte</a><a class="toolbar-button logout-link" href="/deconnexion">Déconnexion</a>' if session.get('user_id') else '<a class="toolbar-button account-link" href="/connexion">Login</a><a class="toolbar-button signup-link" href="/inscription">Sign up</a>'}
  </div>
</div>
<div id="google_translate_element" class="translate-hidden"></div>
<aside class="floating-insight" aria-label="Carte de suivi de la page">
  <div class="floating-insight-head"><span class="floating-live-dot"></span><span>SUIVI ÉNERGÉTIQUE</span><span class="floating-pulse">LIVE</span></div>
  <strong>{title}</strong>
  <p>{floating_note}</p>
  <div class="floating-insight-foot"><span>SMART ENERGY MONITOR</span><span class="floating-clock" id="floatingClock">--:--</span></div>
</aside>
{content}

</main>


<footer>

    Smart Energy Monitor
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

    const clock = document.getElementById("clock");
    if (clock) clock.textContent = heures + ":" + minutes + ":" + secondes;
    const floatingClock = document.getElementById("floatingClock");
    if (floatingClock) floatingClock.textContent = heures + ":" + minutes;
}}

updateClock();

setInterval(updateClock,1000);

</script>



<script>
(function(){{
 const body=document.body, toggle=document.getElementById('themeToggle');
 let mode='light'; try{{mode=localStorage.getItem('energix-theme')||'light'}}catch(e){{}}
 function applyTheme(value){{body.classList.toggle('dark-mode',value==='dark');if(toggle)toggle.textContent=value==='dark'?'Mode clair':'Mode sombre';try{{localStorage.setItem('energix-theme',value)}}catch(e){{}} if(window.Chart){{Chart.defaults.color=value==='dark'?'#d7e9dc':'#66766b';Chart.defaults.borderColor=value==='dark'?'#294333':'#e4ece6';Chart.defaults.plugins.legend.labels.color=Chart.defaults.color;document.querySelectorAll('canvas').forEach(c=>{{const ch=Chart.getChart(c);if(ch){{Object.values(ch.options.scales||{{}}).forEach(a=>{{if(a.ticks)a.ticks.color=Chart.defaults.color;if(a.grid)a.grid.color=Chart.defaults.borderColor}});ch.update()}}}})}}}}
 applyTheme(mode);if(toggle)toggle.addEventListener('click',()=>applyTheme(body.classList.contains('dark-mode')?'light':'dark'));
 const lang=document.getElementById('languageSelect');if(lang)lang.addEventListener('change',()=>{{const value=lang.value;if(value==='fr'){{const frame=document.querySelector('.goog-te-combo');if(frame){{frame.value='fr';frame.dispatchEvent(new Event('change'))}}return}}const wait=()=>{{const combo=document.querySelector('.goog-te-combo');if(combo){{combo.value=value;combo.dispatchEvent(new Event('change'))}}else{{setTimeout(wait,400)}}}};wait()}});
}})();
function googleTranslateElementInit(){{if(window.google&&google.translate){{new google.translate.TranslateElement({{pageLanguage:'fr',includedLanguages:'en,ar,so,es,zh-CN',autoDisplay:false}},'google_translate_element')}}}}
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
        "Salle informatique": "INFO",
        "Salle de cours": "COURS",
        "Laboratoire": "LAB",
        "Bureau administratif": "BUREAU",
        "Salle de réunion": "ÉQUIPE"
    }

    # --------------------------------------------------------
    # CARTES SALLES
    # --------------------------------------------------------

    rooms_html = ""

    for salle in salles:

        nom = salle["nom"]

        icone = icones.get(
            nom,
            "BUREAU"
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
        SE
    </div>

</section>


<!-- STATISTIQUES -->

<section class="grid-4">

    <div class="stat-card">

        <div class="stat-top">

            <div class="stat-icon green">
                SE
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
                SYSTÈME
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
                ALERTE
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
                ANALYSE
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
        BUREAU Espaces surveillés
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
        SYSTÈME Activité du système
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
            HISTORIQUE
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
            DONNÉES
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
            ALERTE
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
            ANALYSE
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
        DONNÉES Analyse de la salle
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
        ÉQUIPEMENTS Équipements
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
    db.close()

    etage = max(0, min(4, etage))
    noms_etages = {1: "Rez-de-chaussée", 2: "1er étage", 3: "2e étage", 4: "3e étage"}
    # Les salles déjà présentes dans la base sont réparties sans modifier la base.
    salles_etage = toutes_salles if etage == 0 else [s for i, s in enumerate(toutes_salles) if i % 4 == etage - 1]
    if not salles_etage:
        salles_html = '<div class="info-panel"><h3>Aucune salle enregistrée à cet étage</h3><p>Ajoutez les salles dans votre base de données pour les afficher ici. Aucune donnée n’a été créée ou modifiée automatiquement.</p></div>'
    else:
        salles_html = '<div class="grid-2">'
        for salle in salles_etage:
            salles_html += f"""<a class="room-card" href="/salle/{salle["id"]}">
              <div class="room-top"><div class="room-icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 7h2m2 0h2M9 11h2m2 0h2M9 15h2m2 0h2M10 21v-3h4v3"/></svg></div><span class="status-normal">SURVEILLÉE</span></div>
              <h3>{salle["nom"]}</h3><div class="location">{salle["localisation"] or noms_etages.get(etage, "Étage non précisé")}</div>
              <div class="room-consumption"><small>Consommation enregistrée</small><strong>{safe_float(salle["energie"]):.3f} kWh</strong></div>
              <small style="color:#718078">{salle["nb_equipements"]} équipement(s)</small></a>"""
        salles_html += '</div>'

    floors = '<a class="floor-button" href="/batiment"><span>▦ Toutes les salles</span><span class="floor-badge">' + str(len(toutes_salles)) + '</span></a>'
    for numero, nom in noms_etages.items():
        selected = ' selected' if numero == etage else ''
        floors += f'<a class="floor-button{selected}" href="/batiment/{numero}"><span><span class="floor-mark" style="color:#21814b;margin-right:10px">NIVEAU</span>{nom}</span><span class="floor-badge">Étage {numero}</span></a>'

    building_svg = """<div id="building3d" class="building-3d" aria-label="Bâtiment interactif en trois dimensions"><div class="three-loading">Chargement du bâtiment 3D…</div></div>
    <div class="three-help">Glissez pour tourner · Molette pour zoomer · Cliquez sur un étage</div>
    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
    <script>
    (function(){
      const host=document.getElementById('building3d'); if(!host)return;if(!window.THREE){host.innerHTML="<div class=\"three-loading\">Le moteur 3D n’a pas pu être chargé. Vérifiez votre connexion Internet puis rechargez la page.</div>";return;}
      host.innerHTML=''; const scene=new THREE.Scene();scene.background=new THREE.Color(0x123f2d);
      const camera=new THREE.PerspectiveCamera(42,host.clientWidth/390,.1,100);camera.position.set(8,7,10);camera.lookAt(0,2,0);
      const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(host.clientWidth,390);renderer.shadowMap.enabled=true;host.appendChild(renderer.domElement);
      scene.add(new THREE.AmbientLight(0xffffff,.75));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(5,9,6);scene.add(light);
      const building=new THREE.Group();scene.add(building);
      const mat=new THREE.MeshStandardMaterial({color:0xb9e5c7,roughness:.55});const edge=new THREE.MeshStandardMaterial({color:0x17643e,roughness:.45});
      const floorMeshes=[];
      for(let i=0;i<4;i++){const floor=new THREE.Mesh(new THREE.BoxGeometry(4.2,.85,3.2),new THREE.MeshStandardMaterial({color:0xb9e5c7,roughness:.6}));floor.position.y=i*1.05+.55;floor.userData.floor=i+1;building.add(floor);floorMeshes.push(floor);
        const slab=new THREE.Mesh(new THREE.BoxGeometry(4.35,.12,3.35),edge);slab.position.y=i*1.05+.08;building.add(slab);
        for(let w=0;w<3;w++){const win=new THREE.Mesh(new THREE.BoxGeometry(.65,.42,.035),new THREE.MeshStandardMaterial({color:0x238653,metalness:.15,roughness:.25,emissive:0x092a18}));win.position.set(-1.35+w*1.35,i*1.05+.58,1.62);building.add(win)}
      }
      const roof=new THREE.Mesh(new THREE.ConeGeometry(2.8,1.3,4),new THREE.MeshStandardMaterial({color:0x17643e}));roof.rotation.y=Math.PI/4;roof.position.y=4.9;building.add(roof);
      const ground=new THREE.Mesh(new THREE.BoxGeometry(7,.15,5.5),new THREE.MeshStandardMaterial({color:0x28563c}));ground.position.y=-.08;scene.add(ground);
      let dragging=false,lastX=0,lastY=0,rotY=-.45,rotX=-.15;host.addEventListener('pointerdown',e=>{dragging=true;lastX=e.clientX;lastY=e.clientY;host.setPointerCapture(e.pointerId)});host.addEventListener('pointerup',()=>dragging=false);host.addEventListener('pointermove',e=>{if(!dragging)return;rotY+=(e.clientX-lastX)*.008;rotX+=(e.clientY-lastY)*.004;rotX=Math.max(-.5,Math.min(.35,rotX));lastX=e.clientX;lastY=e.clientY});host.addEventListener('wheel',e=>{camera.position.multiplyScalar(e.deltaY>0?1.08:.92);camera.position.clampLength(7,20);},{passive:true});
      const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();host.addEventListener('click',e=>{const r=host.getBoundingClientRect();mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;ray.setFromCamera(mouse,camera);const hit=ray.intersectObjects(floorMeshes);if(hit.length){const f=hit[0].object.userData.floor;window.location.href='/batiment/'+f}});
      function animate(){requestAnimationFrame(animate);building.rotation.y=rotY;building.rotation.x=rotX;renderer.render(scene,camera)}animate();window.addEventListener('resize',()=>{camera.aspect=host.clientWidth/390;camera.updateProjectionMatrix();renderer.setSize(host.clientWidth,390)});
    })();
    </script>"""
    etage_label = 'Tous les étages' if etage == 0 else noms_etages[etage]
    content = f"""<div class="page-header"><div class="tag">GESTION DES ESPACES</div><h1>Bâtiment <span style="color:#21814b">intelligent</span></h1><p>Explorez le bâtiment en 3D et consultez les salles, équipements et consommations enregistrés.</p></div>
    <div class="building-layout"><section class="building-visual"><div style="font-size:11px;letter-spacing:2px;color:#b9e9c9;font-weight:800">SMART ENERGY MONITOR</div><h2>Votre établissement</h2><p style="color:#d1ead9;line-height:1.6">Sélectionnez un étage pour afficher les salles correspondantes.</p>{building_svg}<div style="display:flex;justify-content:space-between;border-top:1px solid #ffffff30;padding-top:16px"><span style="color:#d1ead9">Étages disponibles</span><strong>04</strong></div></section>
    <section><div class="section-title"><h2>Choisir un étage</h2><p>Navigation par niveau</p></div><div class="floor-list">{floors}</div><div class="section-title" style="margin-top:25px"><h2>{etage_label}</h2><p>{len(salles_etage)} salle(s) trouvée(s) dans la base</p></div>{salles_html}</section></div>"""
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
            ALERTE
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
            ANALYSE
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
            SE
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
            SYSTÈME
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
# AUTHENTIFICATION ET ESPACE UTILISATEUR
# ============================================================

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
                with sqlite3.connect(DATABASE) as db:
                    cur = db.execute("INSERT INTO utilisateurs(nom,email,mot_de_passe) VALUES(?,?,?)", (nom,email,generate_password_hash(password)))
                    user_id = cur.lastrowid
                session.clear(); session["user_id"] = user_id; session["user_name"] = nom; session["user_email"] = email
                return redirect(url_for("compte"))
            except sqlite3.IntegrityError:
                message = "Cette adresse e-mail possède déjà un compte."
    content = f"""<section class="auth-wrap"><div class="page-header"><div class="tag">NOUVEAU COMPTE</div><h1>Créer un compte</h1><p>Rejoignez votre espace Smart Energy Monitor.</p></div>{f'<div class="auth-message">{message}</div>' if message else ''}<form class="auth-form" method="post"><label>Nom complet<input name="nom" autocomplete="name" required></label><label>Adresse e-mail<input name="email" type="email" autocomplete="email" required></label><label>Mot de passe<input name="mot_de_passe" type="password" minlength="8" autocomplete="new-password" required></label><label>Confirmer le mot de passe<input name="confirmation" type="password" minlength="8" autocomplete="new-password" required></label><button type="submit">Créer mon compte</button></form><p style="margin-top:18px">Déjà inscrit ? <a href="/connexion">Se connecter</a></p></section>"""
    return page_template("Inscription", content, "home")


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    message = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("mot_de_passe", "")
        with sqlite3.connect(DATABASE) as db:
            db.row_factory = sqlite3.Row
            user = db.execute("SELECT * FROM utilisateurs WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["mot_de_passe"], password):
            session.clear(); session["user_id"] = user["id"]; session["user_name"] = user["nom"]; session["user_email"] = user["email"]
            return redirect(url_for("compte"))
        message = "Adresse e-mail ou mot de passe incorrect."
    content = f"""<section class="auth-wrap"><div class="page-header"><div class="tag">ESPACE SÉCURISÉ</div><h1>Connexion</h1><p>Connectez-vous à votre compte.</p></div>{f'<div class="auth-message">{message}</div>' if message else ''}<form class="auth-form" method="post"><label>Adresse e-mail<input name="email" type="email" autocomplete="email" required></label><label>Mot de passe<input name="mot_de_passe" type="password" autocomplete="current-password" required></label><button type="submit">Se connecter</button></form><p style="margin-top:18px">Pas encore de compte ? <a href="/inscription">Créer un compte</a></p></section>"""
    return page_template("Connexion", content, "home")


@app.route("/compte")
def compte():
    if not session.get("user_id"):
        return redirect(url_for("connexion"))
    content = f"""<div class="page-header"><div class="tag">ESPACE PERSONNEL</div><h1>Mon compte</h1><p>Informations de votre profil utilisateur.</p></div><div class="grid-2"><div class="stat-card"><div class="stat-label">Nom</div><div class="stat-value">{session.get('user_name','Utilisateur')}</div></div><div class="stat-card"><div class="stat-label">Adresse e-mail</div><div style="font-weight:800;margin-top:10px">{session.get('user_email','')}</div></div></div><div style="margin-top:22px"><a class="toolbar-button logout-link" href="/deconnexion">Déconnexion</a></div>"""
    return page_template("Mon compte", content, "home")


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect(url_for("home"))


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
            font-size:22px;
            font-weight:900;
            letter-spacing:3px;
            margin-bottom:20px;
            color:#168b83;
        ">
            SMART ENERGY
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
        host="0.0.0.0",
        port=5000
    )

