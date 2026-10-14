from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

# Logical pixels; Qt handles display scaling. Shared by widgets and delegates.
CONTROL_HEIGHT = 40
URL_CONTROL_HEIGHT = 44
INLINE_HEIGHT = 32
CORNER_RADIUS = 8
FORM_MAX_WIDTH = 760
SIDEBAR_WIDTH = 176
SPACING = (4, 8, 12, 16, 24, 32)
SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL, SPACE_XXL = SPACING
TYPE_SIZE = {"body": 14, "label": 12, "detail": 12, "section": 16, "title": 24}
BUTTON_WEIGHT = {"primary": 600, "secondary": 500, "quiet": 400, "destructive": 400, "icon": 400}
_PALETTE = {
    "page_bg_top": "#ffffff", "page_bg_bottom": "#ffffff",
    "sidebar": "#f3f4f6", "text_primary": "#20252b", "text_muted": "#606873",
    "text_label": "#4b5563", "text_secondary": "#374151", "text_inverse": "#ffffff",
    "surface": "#f3f4f6", "surface_soft": "#f9fafb", "surface_soft_alt": "#e5e7eb",
    "surface_disabled": "#f3f4f6", "surface_selected": "#eff6ff",
    "surface_selected_strong": "#dbeafe", "border": "#8a94a3", "border_soft": "#e5e7eb",
    "border_strong": "#606873", "border_hover": "#606873",
    "accent": "#2563eb", "accent_hover": "#1d4ed8", "accent_pressed": "#1e40af",
    "action": "#2563eb", "action_hover": "#1d4ed8", "action_pressed": "#1e40af",
    "accent_text": "#1d4ed8", "accent_soft": "#eff6ff", "accent_border": "#2563eb",
    "button_text": "#374151", "button_hover_text": "#20252b", "button_disabled_text": "#7b8491",
    "field_text": "#20252b", "field_readonly_text": "#4b5563", "field_disabled_text": "#7b8491",
    "field_border": "#8a94a3", "field_disabled_border": "#d1d5db",
    "field_surface": "#ffffff", "field_surface_hover": "#f9fafb",
    "field_surface_focus": "#ffffff", "field_surface_readonly": "#f9fafb",
    "nav_text": "#4b5563", "nav_disabled": "#7b8491", "tab_text": "#4b5563",
    "scroll_handle": "#b7bdc6", "scroll_handle_hover": "#8a94a3",
    "destructive": "#b42318", "destructive_hover": "#912018",
    "destructive_bg": "#fff5f4", "destructive_bg_hover": "#fee4e2",
    "warning_bg": "#fffaeb", "warning_border": "#f5d78e", "warning_text": "#854d0e",
    "error_bg": "#fff5f4", "error_border": "#f4b4ae", "error_text": "#b42318",
    "success_bg": "#f0fdf4", "success_text": "#166534",
}


def control_height(sizing: str = "standard") -> int:
    return {"standard": CONTROL_HEIGHT, "url": URL_CONTROL_HEIGHT, "inline": INLINE_HEIGHT}[sizing]


def light_palette() -> QPalette:
    """Keep native popups, custom delegates and dialogs legible in either OS theme."""
    palette = QPalette()
    for role, key in {
        QPalette.ColorRole.Window: "page_bg_bottom", QPalette.ColorRole.Base: "page_bg_bottom",
        QPalette.ColorRole.AlternateBase: "surface_soft", QPalette.ColorRole.Button: "surface_soft",
        QPalette.ColorRole.WindowText: "text_primary", QPalette.ColorRole.Text: "text_primary",
        QPalette.ColorRole.ButtonText: "button_text", QPalette.ColorRole.PlaceholderText: "text_muted",
        QPalette.ColorRole.Highlight: "surface_selected_strong", QPalette.ColorRole.HighlightedText: "text_primary",
        QPalette.ColorRole.ToolTipBase: "text_primary", QPalette.ColorRole.ToolTipText: "text_inverse",
        QPalette.ColorRole.Link: "accent_text",
    }.items():
        palette.setColor(role, QColor(_PALETTE[key]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(_PALETTE["button_disabled_text"]))
    return palette


def button_colors(role: str, *, hover: bool = False) -> tuple[str, str, str]:
    if role == "primary":
        return (_PALETTE["action_hover" if hover else "action"],
                _PALETTE["action_hover" if hover else "action"], _PALETTE["text_inverse"])
    if role == "destructive":
        return (_PALETTE["destructive_bg_hover"] if hover else "transparent", "transparent",
                _PALETTE["destructive_hover" if hover else "destructive"])
    if role == "secondary":
        return (_PALETTE["surface"] if hover else "#ffffff", _PALETTE["border"], _PALETTE["button_text"])
    return (_PALETTE["surface"] if hover else "transparent", "transparent", _PALETTE["button_text"])


def build_stylesheet(combo_arrow_path: str) -> str:
    p = _PALETTE
    rules = []
    for role in BUTTON_WEIGHT:
        for state in ("", ":hover", ":pressed", ":disabled", ":focus"):
            bg, border, fg = button_colors(role, hover=state in {":hover", ":pressed"})
            if state == ":pressed":
                bg = p["action_pressed"] if role == "primary" else p["surface_soft_alt"]
            if state == ":disabled":
                bg, border, fg = p["surface_disabled"], p["field_disabled_border"], p["button_disabled_text"]
                if role in {"quiet", "destructive", "icon"}:
                    bg = border = "transparent"
            if state == ":focus":
                border = p["accent_pressed"] if role == "primary" else p["accent"]
            border_width = 2 if state == ":focus" else 1
            padding = "3px 11px" if state == ":focus" else "4px 12px"
            rules.append(f'QPushButton[uiRole="{role}"]{state} {{ background: {bg}; color: {fg}; '
                         f'border: {border_width}px solid {border}; border-radius: {CORNER_RADIUS}px; '
                         f'padding: {padding}; font-size: 14px; font-weight: {BUTTON_WEIGHT[role]}; }}')
    rules.append(f"""
        QWidget {{ color: {p['text_primary']}; font-size: 14px; }}
        QPushButton[iconOnly="true"] {{ padding: 4px; }}
        QPushButton[iconOnly="true"]:focus {{ padding: 3px; }}
        QMainWindow, QWidget#appRoot, QStackedWidget#panelStack {{ background: white; border: none; }}
        QLabel, QCheckBox, QRadioButton, QGroupBox {{ background: transparent; border: none; }}
        QWidget#downloadsPage, QWidget#panelPage, QWidget#contentColumn {{ background: white; border: none; }}
        QWidget#topBarShell {{ background: {p['sidebar']}; border: none; border-right: 1px solid {p['border_soft']}; }}
        QLabel#sidebarTitle {{ font-size: 15px; font-weight: 600; color: {p['text_primary']}; }}
        QPushButton#topNavButton, QPushButton#topIconButton {{ text-align: left; padding: 6px 10px;
            border: 1px solid transparent; border-radius: 8px; background: transparent; color: {p['nav_text']}; font-weight: 500; }}
        QPushButton#topNavButton:hover, QPushButton#topIconButton:hover {{ background: {p['surface_soft_alt']}; }}
        QPushButton#topNavButton:checked, QPushButton#topIconButton:checked {{ background: {p['surface_selected_strong']}; color: {p['accent_text']}; }}
        QPushButton#topNavButton:focus, QPushButton#topIconButton:focus {{ border-color: {p['accent']}; }}
        QLabel#pageTitle, QLabel#panelHeaderTitle {{ font-size: 24px; font-weight: 600; }}
        QLabel#sourceHint, QLabel#mediaSummaryDetail, QLabel#advancedSummary, QLabel#settingsAppVersion,
        QLabel#settingsEngineVersion, QLabel#updateDetailLabel, QLabel#analysisElapsed {{ color: {p['text_muted']}; font-size: 12px; }}
        QLabel#mediaSummaryTitle {{ font-size: 16px; font-weight: 600; }}
        QLabel#settingsRowTitle {{ font-size: 16px; font-weight: 600; }}
        QLabel#outputFormLabel, QLabel#sectionFormLabel, QLabel#saveBlockLabel {{ color: {p['text_label']}; font-size: 12px; font-weight: 500; }}
        QLineEdit, QComboBox {{ background: white; color: {p['field_text']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 4px 12px; selection-background-color: {p['surface_selected_strong']}; selection-color: {p['text_primary']}; }}
        QLineEdit:hover, QComboBox:hover {{ border-color: {p['border_hover']}; }}
        QLineEdit:focus, QComboBox:focus {{ border: 2px solid {p['accent']}; padding: 3px 11px; }}
        QLineEdit:disabled, QComboBox:disabled {{ background: {p['surface_disabled']}; color: {p['field_disabled_text']}; border-color: {p['field_disabled_border']}; }}
        QComboBox {{ padding-right: 32px; }}
        QComboBox:focus {{ padding-right: 31px; }}
        QComboBox::drop-down {{ width: 28px; border: none; }}
        QComboBox::down-arrow {{ image: url({combo_arrow_path}); width: 10px; height: 6px; }}
        QListView#nativeComboView, QComboBox QAbstractItemView {{ background: white; color: {p['text_primary']}; border: 1px solid {p['border']}; padding: 4px; outline: 0; selection-background-color: {p['surface_selected_strong']}; selection-color: {p['text_primary']}; }}
        QListView#nativeComboView::item {{ min-height: 32px; padding: 0px 8px; border-radius: 4px; }}
        QListView#nativeComboView::item:hover {{ background: {p['surface_selected']}; }}
        QWidget#contentModeSegment {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 8px; }}
        QFrame#contentModeSelection {{ background: {p['surface_selected_strong']}; border: none; border-radius: 6px; }}
        QPushButton#contentModeButton {{ background: transparent; color: {p['text_label']}; border: 1px solid transparent; border-radius: 6px; padding: 2px 10px; }}
        QPushButton#contentModeButton:checked {{ color: {p['accent_text']}; font-weight: 600; }}
        QPushButton#contentModeButton:focus {{ border-color: {p['accent']}; }}
        QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 4px 6px; color: {p['text_label']}; }}
        QToolButton:hover {{ background: {p['surface']}; }}
        QToolButton:focus {{ border-color: {p['accent']}; }}
        QCheckBox {{ spacing: 8px; }}
        QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {p['border']}; border-radius: 4px; background: white; }}
        QCheckBox::indicator:checked {{ background: {p['action']}; border-color: {p['action']}; image: url(__check__); }}
        QCheckBox:focus {{ outline: 1px solid {p['accent']}; }}
        QCheckBox::indicator:disabled {{ background: {p['surface_disabled']}; border-color: {p['field_disabled_border']}; }}
        QProgressBar {{ background: {p['surface_soft_alt']}; border: none; border-radius: 3px; min-height: 6px; max-height: 6px; }}
        QProgressBar::chunk {{ background: {p['accent']}; border-radius: 3px; }}
        QFrame#progressCard {{ background: white; border: none; border-top: 1px solid {p['border_soft']}; }}
        QLabel#metricInline, QLabel#metricInlineItem {{ font-size: 12px; color: {p['text_muted']}; }}
        QListWidget#panelList {{ background: white; border: none; outline: 0; }}
        QListWidget#panelList::item {{ border-bottom: 1px solid {p['border_soft']}; padding: 0; }}
        QListWidget#panelList::item:hover {{ background: {p['surface_soft']}; }}
        QListWidget#panelList::item:selected {{ background: {p['surface_selected']}; color: {p['text_primary']}; }}
        QListWidget#panelList::item:focus {{ border: 1px solid {p['accent']}; }}
        QPlainTextEdit {{ background: {p['surface_soft']}; color: {p['text_primary']}; border: 1px solid {p['border_soft']}; border-radius: 8px; padding: 8px; selection-background-color: {p['surface_selected_strong']}; selection-color: {p['text_primary']}; }}
        QFrame#sectionDivider {{ background: {p['border_soft']}; border: none; max-height: 1px; }}
        QWidget#feedbackRow {{ background: {p['surface_soft']}; border-radius: 8px; }}
        QWidget#feedbackRow[tone="error"] {{ background: {p['error_bg']}; }}
        QWidget#feedbackRow[tone="warning"] {{ background: {p['warning_bg']}; }}
        QWidget#feedbackRow[tone="success"] {{ background: {p['success_bg']}; }}
        QWidget#feedbackRow[tone="error"] QLabel#feedbackMessage {{ color: {p['error_text']}; }}
        QWidget#feedbackRow[tone="warning"] QLabel#feedbackMessage {{ color: {p['warning_text']}; }}
        QWidget#feedbackRow[tone="success"] QLabel#feedbackMessage {{ color: {p['success_text']}; }}
        QFrame#queueEmptySurface {{ background: transparent; border: none; }}
        QLabel#queueEmptyTitle, QLabel#panelEmptyTitle {{ font-size: 20px; font-weight: 600; }}
        QLabel#queueEmptyDescription, QLabel#panelEmptyDescription {{ color: {p['text_muted']}; }}
        QScrollArea#formScroll, QScrollArea#formScroll > QWidget > QWidget {{ background: white; border: none; }}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 0px; }}
        QScrollBar::handle:vertical {{ background: {p['scroll_handle']}; border-radius: 4px; min-height: 24px; }}
        QScrollBar::handle:vertical:hover {{ background: {p['scroll_handle_hover']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QToolTip {{ background: {p['text_primary']}; color: white; border: none; padding: 6px 8px; }}
        QMessageBox, QDialog {{ background: white; }}
        QMenu {{ background: white; color: {p['text_primary']}; border: 1px solid {p['border_soft']}; padding: 4px; }}
        QMenu::item {{ padding: 8px 20px; }}
        QMenu::item:selected {{ background: {p['surface_selected_strong']}; }}
        QWidget#mixedUrlOverlay {{ background: rgba(32, 37, 43, 36); }}
        QFrame#mixedUrlAlert {{ background: white; border: 1px solid {p['border']}; border-radius: 8px; }}
    """)
    from .icon_assets import style_asset_path
    from PySide6.QtCore import QSize
    return "\n".join(rules).replace("__check__", style_asset_path("check.svg", size=QSize(14, 14)))


def combo_popup_stylesheet(border_color: str | None = None) -> str:
    border = border_color or _PALETTE["border"]
    return (f"QFrame {{ background: white; border: 1px solid {border}; border-radius: 8px; }} "
            f"QListView {{ background: white; color: {_PALETTE['text_primary']}; border: none; }} "
            f"QListView::item:selected {{ background: {_PALETTE['surface_selected_strong']}; color: {_PALETTE['text_primary']}; }}")
