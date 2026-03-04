"""
Modern light theme for M2O — Options Strategy
Palette: blanc / gris très clair + accent bleu acier sobre.
"""

# ── Color tokens ───────────────────────────────────────────────────────────
BG_APP        = "#F5F6FA"   # fond principal (gris très clair)
BG_SURFACE    = "#FFFFFF"   # surface (panels, dock)
BG_RAISED     = "#FFFFFF"   # éléments surélevés (groupbox, cards)
BG_INPUT      = "#FFFFFF"   # champs de saisie
BG_HOVER      = "#EEF1F8"   # hover state
BG_SELECTED   = "#DDE6FB"   # sélection
BORDER        = "#DDE0E8"   # bordures générales
BORDER_FOCUS  = "#3D72F0"   # focus ring

TEXT_PRIMARY   = "#1A1D2E"  # texte principal
TEXT_SECONDARY = "#6B7080"  # texte secondaire / labels
TEXT_DISABLED  = "#B0B4C0"  # texte désactivé
TEXT_ACCENT    = "#2A5BD7"  # texte accentué (liens, titres section)

ACCENT        = "#3D72F0"   # bouton primaire
ACCENT_HOVER  = "#2A5BD7"
ACCENT_PRESS  = "#1A4AC4"
DANGER        = "#D94F4F"
DANGER_HOVER  = "#C03030"
SUCCESS       = "#2E9E72"
WARNING       = "#C88A20"

SCROLLBAR_BG   = "#F0F1F5"
SCROLLBAR_THUMB = "#C8CBD8"
SCROLLBAR_HOVER = "#A8ACBC"

TAB_BAR_BG    = "#ECEEF5"
TAB_ACTIVE_BG = "#FFFFFF"
TAB_INACTIVE  = "#ECEEF5"

RADIUS        = "6px"
RADIUS_SM     = "4px"
RADIUS_LG     = "8px"


QSS = f"""
/* ===== GLOBAL =========================================================== */
QWidget {{
    background-color: {BG_APP};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    border: none;
    outline: none;
}}

QMainWindow {{
    background-color: {BG_APP};
}}

/* ===== DOCK ============================================================= */
QDockWidget {{
    background-color: {BG_SURFACE};
    border: none;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background-color: {BG_RAISED};
    color: {TEXT_SECONDARY};
    text-align: left;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border-bottom: 1px solid {BORDER};
}}
QDockWidget::close-button,
QDockWidget::float-button {{
    background: transparent;
    border: none;
    padding: 2px;
}}

/* ===== SCROLL AREA ====================================================== */
QScrollArea {{
    background-color: {BG_SURFACE};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {BG_SURFACE};
}}
QScrollBar:vertical {{
    background: {SCROLLBAR_BG};
    width: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {SCROLLBAR_THUMB};
    border-radius: 3px;
    min-height: px;
}}
QScrollBar::handle:vertical:hover {{
    background: {SCROLLBAR_HOVER};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
    height: 0;
}}
QScrollBar:horizontal {{
    background: {SCROLLBAR_BG};
    height: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {SCROLLBAR_THUMB};
    border-radius: 3px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {SCROLLBAR_HOVER};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
    width: 0;
}}

/* ===== GROUP BOX ======================================================== */
QGroupBox {{
    background-color: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: {RADIUS};
    margin-top: 18px;
    padding: 8px 6px 6px 6px;
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_ACCENT};
    letter-spacing: 0.06em;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 2px;
    padding: 0 4px;
    color: {TEXT_ACCENT};
    background-color: {BG_RAISED};
}}

/* ===== TABS ============================================================= */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: {RADIUS};
    background-color: {BG_SURFACE};
    top: -1px;
}}
QTabBar {{
    background-color: {TAB_BAR_BG};
}}
QTabBar::tab {{
    background-color: {TAB_INACTIVE};
    color: {TEXT_SECONDARY};
    padding: 11px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 15px;
    font-weight: 500;
    min-width: 110px;
}}
QTabBar::tab:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}
QTabBar::tab:selected {{
    background-color: {TAB_ACTIVE_BG};
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT};
    font-weight: 600;
}}
QTabBar::tab:first {{
    border-top-left-radius: {RADIUS_SM};
}}

/* ===== INPUTS =========================================================== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    color: {TEXT_PRIMARY};
    padding: 4px 8px;
    selection-background-color: {BG_SELECTED};
    selection-color: {TEXT_PRIMARY};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {BORDER_FOCUS};
}}
QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {BG_RAISED};
    color: {TEXT_DISABLED};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    color: {TEXT_PRIMARY};
    padding: 3px 4px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {BORDER_FOCUS};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {BG_HOVER};
    border: none;
    width: 16px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {BG_SELECTED};
}}

QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    color: {TEXT_PRIMARY};
    padding: 4px 8px;
    min-width: 60px;
}}
QComboBox:focus {{
    border-color: {BORDER_FOCUS};
}}
QComboBox:hover {{
    border-color: {SCROLLBAR_HOVER};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_SECONDARY};
    margin-right: 4px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    color: {TEXT_PRIMARY};
    selection-background-color: {BG_SELECTED};
    selection-color: {TEXT_PRIMARY};
    outline: none;
    padding: 2px;
}}
QComboBox QAbstractItemView::item {{
    padding: 5px 10px;
    border-radius: {RADIUS_SM};
}}

/* ===== BUTTONS ========================================================== */
QPushButton {{
    background-color: {BG_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    min-height: 26px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {SCROLLBAR_HOVER};
}}
QPushButton:pressed {{
    background-color: {BG_SELECTED};
}}
QPushButton:disabled {{
    background-color: {BG_RAISED};
    color: {TEXT_DISABLED};
    border-color: {BORDER};
}}

/* Primary (run) button — use setProperty("accent", "true") */
QPushButton[accent="true"] {{
    background-color: {ACCENT};
    color: white;
    border: none;
    font-weight: 600;
}}
QPushButton[accent="true"]:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton[accent="true"]:pressed {{
    background-color: {ACCENT_PRESS};
}}
QPushButton[accent="true"]:disabled {{
    background-color: {BG_HOVER};
    color: {TEXT_DISABLED};
}}

/* Danger button — use setProperty("danger", "true") */
QPushButton[danger="true"] {{
    background-color: transparent;
    color: {DANGER};
    border: 1px solid {DANGER};
}}
QPushButton[danger="true"]:hover {{
    background-color: {DANGER};
    color: white;
}}

/* ===== CHECKBOX ========================================================= */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:hover {{
    border-color: {BORDER_FOCUS};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    image: none;
}}
QCheckBox::indicator:checked:hover {{
    background-color: {ACCENT_HOVER};
}}

/* ===== SLIDER =========================================================== */
QSlider::groove:horizontal {{
    background: {BORDER};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT_HOVER};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    height: 4px;
    border-radius: 2px;
}}

/* ===== LABELS =========================================================== */
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QLabel[class="section-title"] {{
    color: {TEXT_ACCENT};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}
QLabel[class="metric"] {{
    color: {TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 600;
}}
QLabel[class="metric-label"] {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}
QLabel[class="status"] {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    padding: 4px 0;
}}

/* ===== TABLE ============================================================ */
QTableWidget, QTableView {{
    background-color: {BG_SURFACE};
    gridline-color: {BORDER};
    alternate-background-color: {BG_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    selection-background-color: {BG_SELECTED};
    selection-color: {TEXT_PRIMARY};
}}
QTableWidget::item, QTableView::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {BG_SELECTED};
    color: {TEXT_PRIMARY};
}}
QHeaderView::section {{
    background-color: {BG_RAISED};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    padding: 5px 8px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
QHeaderView::section:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

/* ===== FORM LAYOUT ====================================================== */
QFormLayout > QLabel {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}

/* ===== TOOLTIP ========================================================== */
QToolTip {{
    background-color: {BG_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    padding: 4px 8px;
    font-size: 11px;
}}

/* ===== STATUS BAR ======================================================= */
QStatusBar {{
    background-color: {BG_APP};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER};
    font-size: 11px;
}}

/* ===== PROGRESS BAR ===================================================== */
QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    color: transparent;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: {RADIUS_SM};
}}

/* ===== SPLITTER ========================================================= */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ===== MENU ============================================================= */
QMenuBar {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER};
}}
QMenuBar::item:selected {{
    background-color: {BG_HOVER};
    border-radius: {RADIUS_SM};
}}
QMenu {{
    background-color: {BG_RAISED};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px 6px 10px;
    border-radius: {RADIUS_SM};
}}
QMenu::item:selected {{
    background-color: {BG_SELECTED};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}
"""


def apply(app) -> None:
    """Apply the theme stylesheet to a QApplication instance."""
    app.setStyleSheet(QSS)
