"""Neon-purple theme. Single source of truth for colors + the global stylesheet."""
from __future__ import annotations

# ── Color tokens (futuristic neon purple) ───────────────────────────────
BG_BASE      = "#0a0612"   # app background (deep purple-black)
BG_CANVAS    = "#070410"   # deepest — title bar / footer
BG_PANEL     = "#120a22"   # elevated panels
BG_CARD      = "#191033"   # cards
BG_HOVER     = "#231546"
BORDER       = "#2c1a4d"
BORDER_SOFT  = "#1d1138"

ACCENT       = "#a855f7"   # primary neon purple
ACCENT_BRIGHT= "#c77dff"   # hover / active
ACCENT_GLOW  = "#7b2cbf"
ACCENT_DEEP  = "#5a189a"
CYAN         = "#22d3ee"   # secondary accent (SPL / links)

TEXT         = "#ece6f8"
TEXT_DIM     = "#a191c9"
TEXT_MUTED   = "#5f4d86"

# step-kind colors
K_THOUGHT    = "#a191c9"
K_SPL        = CYAN
K_RESULT     = "#7ef0c0"
K_DRIFT      = "#ff9e00"
K_HEAL       = "#c77dff"
K_CORRELATE  = "#8ab4ff"
K_CONCLUSION = "#e0aaff"
K_ACTION     = "#7ef0c0"
K_ERROR      = "#ff4d6d"


QSS = f"""
* {{ outline: 0; }}
QWidget {{
    background: transparent;
    color: {TEXT};
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}
QWidget#root {{ background: {BG_BASE}; border: 1px solid {BORDER}; border-radius: 14px; }}

/* Title bar */
QFrame#titleBar {{ background: {BG_CANVAS}; border-top-left-radius: 14px; border-top-right-radius: 14px;
                   border-bottom: 1px solid {BORDER_SOFT}; }}
QLabel#brand {{ color: {ACCENT_BRIGHT}; font-size: 16px; font-weight: 800; letter-spacing: 2px; }}
QLabel#brandSub {{ color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px; }}

/* Top-bar elements */
QLineEdit#search {{ background: {BG_PANEL}; border: 1px solid {BORDER_SOFT}; border-radius: 19px;
                    padding: 8px 16px; color: {TEXT}; }}
QLineEdit#search:focus {{ border: 1px solid {ACCENT}; }}
QPushButton#iconBtn {{ background: transparent; border: none; border-radius: 9px; }}
QPushButton#iconBtn:hover {{ background: {BG_HOVER}; }}

/* Filter pills */
QPushButton#pill {{ background: {BG_PANEL}; color: {TEXT_DIM}; border: 1px solid {BORDER_SOFT};
                    border-radius: 15px; padding: 7px 16px; font-weight: 700; font-size: 12px; }}
QPushButton#pill:hover {{ color: {TEXT}; border-color: {ACCENT_DEEP}; }}
QPushButton#pill:checked {{ background: {ACCENT_DEEP}; color: white; border-color: {ACCENT_BRIGHT}; }}

/* Link-style button (Add to Case) */
QPushButton#linkBtn {{ background: transparent; color: {TEXT_DIM}; border: none; font-size: 12px;
                       font-weight: 600; padding: 4px; }}
QPushButton#linkBtn:hover {{ color: {ACCENT_BRIGHT}; }}
QPushButton#winBtn, QPushButton#winClose {{ background: transparent; border: none;
                      color: {TEXT_DIM}; font-size: 15px; border-radius: 8px;
                      min-width: 38px; max-width: 38px; min-height: 30px; }}
QPushButton#winBtn:hover {{ background: {BG_HOVER}; color: {TEXT}; }}
QPushButton#winClose:hover {{ background: #ff4d6d; color: white; }}

/* Sidebar */
QFrame#sidebar {{ background: {BG_CANVAS}; border-right: 1px solid {BORDER_SOFT};
                  border-bottom-left-radius: 14px; }}
QPushButton#navBtn {{ background: transparent; border: none; color: {TEXT_DIM};
                      text-align: left; padding: 12px 18px; border-radius: 10px;
                      font-size: 13px; font-weight: 600; letter-spacing: 0.5px; }}
QPushButton#navBtn:hover {{ background: {BG_HOVER}; color: {TEXT}; }}
QPushButton#navBtn:checked {{ background: {ACCENT_DEEP}; color: white;
                              border-left: 3px solid {ACCENT_BRIGHT}; }}

/* Cards / panels */
QFrame#card {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#panel {{ background: {BG_PANEL}; border: 1px solid {BORDER_SOFT}; border-radius: 12px; }}
QLabel#h1 {{ font-size: 22px; font-weight: 800; color: {TEXT}; }}
QLabel#h2 {{ font-size: 15px; font-weight: 700; color: {ACCENT_BRIGHT}; letter-spacing: 0.5px; }}
QLabel#dim {{ color: {TEXT_DIM}; }}
QLabel#muted {{ color: {TEXT_MUTED}; font-size: 12px; }}

/* Buttons */
QPushButton#primary {{ background: {ACCENT}; color: white; border: none; border-radius: 10px;
                       padding: 11px 22px; font-weight: 700; letter-spacing: 0.5px; }}
QPushButton#primary:hover {{ background: {ACCENT_BRIGHT}; }}
QPushButton#primary:disabled {{ background: {BORDER}; color: {TEXT_MUTED}; }}
QPushButton#ghost {{ background: transparent; color: {ACCENT_BRIGHT}; border: 1px solid {ACCENT_DEEP};
                     border-radius: 10px; padding: 10px 20px; font-weight: 700; }}
QPushButton#ghost:hover {{ background: {BG_HOVER}; }}
QPushButton#approve {{ background: #1f7a4d; color: white; border: none; border-radius: 10px;
                       padding: 11px 22px; font-weight: 700; }}
QPushButton#approve:hover {{ background: #29a065; }}
QPushButton#reject {{ background: transparent; color: #ff708a; border: 1px solid #5e2030;
                      border-radius: 10px; padding: 11px 22px; font-weight: 700; }}
QPushButton#reject:hover {{ background: #2a121a; }}

/* Console step stream */
QScrollArea {{ border: none; background: transparent; }}
QFrame#step {{ background: {BG_CARD}; border: 1px solid {BORDER_SOFT}; border-radius: 10px;
               border-left: 3px solid {ACCENT}; }}
QLabel#stepKind {{ font-weight: 800; font-size: 11px; letter-spacing: 1.5px; }}
QLabel#stepBody {{ color: {TEXT_DIM}; font-size: 13px; }}
QLabel#spl {{ font-family: "Cascadia Code", "Consolas", monospace; color: {CYAN};
             background: {BG_CANVAS}; border: 1px solid {BORDER_SOFT}; border-radius: 8px;
             padding: 10px; font-size: 12px; }}

/* Inputs */
QLineEdit {{ background: {BG_CANVAS}; border: 1px solid {BORDER}; border-radius: 8px;
             padding: 9px 12px; color: {TEXT}; selection-background-color: {ACCENT_DEEP}; }}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}

/* Tables */
QTableWidget {{ background: {BG_PANEL}; border: 1px solid {BORDER_SOFT}; border-radius: 10px;
                gridline-color: {BORDER_SOFT}; }}
QHeaderView::section {{ background: {BG_CANVAS}; color: {TEXT_DIM}; border: none;
                        padding: 8px; font-weight: 700; }}
QTableWidget::item {{ padding: 6px; }}
QTableWidget::item:selected {{ background: {ACCENT_DEEP}; color: white; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT_DEEP}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""
