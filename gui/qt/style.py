from __future__ import annotations


_PALETTE = {
    "page_bg_top": "#f6fcf9",
    "page_bg_bottom": "#e4f4ef",
    "scroll_handle": "#97cfc2",
    "scroll_handle_hover": "#79bdae",
    "text_primary": "#173d3a",
    "text_muted": "#68847e",
    "text_label": "#6d8a84",
    "text_secondary": "#406561",
    "text_inverse": "#ffffff",
    "surface": "#ffffff",
    "surface_soft": "#f4fbf8",
    "surface_soft_alt": "#eff8f4",
    "surface_disabled": "#edf5f2",
    "surface_selected": "#ddf2eb",
    "surface_selected_strong": "#d1eee5",
    "border": "#d1e6de",
    "border_strong": "#bbdacf",
    "border_soft": "#d9ebe5",
    "border_hover": "#8fc7ba",
    "accent": "#0f9e8b",
    "accent_hover": "#0d8c7b",
    "accent_pressed": "#0a7769",
    "accent_soft": "#d8f0e9",
    "accent_soft_hover": "#caeae2",
    "accent_border": "#99d0c3",
    "accent_text": "#0f5b51",
    "field_text": "#204743",
    "field_readonly_text": "#2b5953",
    "field_border": "#bfdad1",
    "field_disabled_border": "#d6e6e0",
    "field_disabled_text": "#91a7a1",
    "tab_text": "#50716b",
    "nav_text": "#5b7973",
    "nav_disabled": "#9aafa9",
    "button_text": "#2a5d57",
    "button_hover_text": "#1f534d",
    "button_disabled_text": "#95aaa4",
}


def build_stylesheet(combo_arrow_path: str) -> str:
    style_sheet = """
        QMainWindow, QWidget#appRoot {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 __page_bg_top__,
                stop: 1 __page_bg_bottom__
            );
        }
        QScrollArea#downloadsScrollArea {
            background: transparent;
            border: none;
        }
        QScrollArea#downloadsScrollArea > QWidget > QWidget {
            background: transparent;
        }
        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 2px 0px 2px 0px;
        }
        QScrollBar::handle:vertical {
            background: __scroll_handle__;
            border-radius: 5px;
            min-height: 24px;
        }
        QScrollBar::handle:vertical:hover {
            background: __scroll_handle_hover__;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: transparent;
        }
        QWidget {
            color: __text_primary__;
            font-size: 13px;
        }
        QLabel, QCheckBox, QRadioButton {
            background: transparent;
        }
        QMessageBox {
            background: __page_bg_bottom__;
        }
        QMessageBox QLabel {
            color: __text_primary__;
            font-size: 14px;
        }
        QMessageBox QPushButton {
            min-width: 96px;
        }
        #titleLabel {
            font-size: 40px;
            font-weight: 800;
            color: __accent_text__;
        }
        #subtleLabel {
            color: __text_muted__;
            font-size: 11px;
            font-weight: 500;
        }
        QLabel#sectionFormLabel {
            color: __text_label__;
            font-size: 11px;
            font-weight: 500;
        }
        QLabel#outputFormLabel {
            color: __text_label__;
            font-size: 11px;
            font-weight: 500;
        }
        QLabel#saveBlockLabel {
            color: __text_label__;
            font-size: 11px;
            font-weight: 500;
        }
        QLabel#previewValue {
            background: __surface_soft_alt__;
            border: 1px solid __field_border__;
            border-radius: 8px;
            color: __field_readonly_text__;
            padding: 4px 8px;
        }
        #statusLine {
            color: __text_muted__;
            font-size: 11px;
        }
        QLabel#sectionHeaderTitle {
            color: __text_primary__;
            font-size: 18px;
            font-weight: 800;
        }
        QLabel#cardHeaderTitle {
            color: __text_secondary__;
            font-size: 14px;
            font-weight: 700;
        }
        QGroupBox {
            border: none;
            border-radius: 0px;
            margin-top: 0px;
            padding-top: 0px;
            padding-bottom: 0px;
            background: transparent;
            font-weight: 650;
            color: __text_primary__;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 0px;
            top: -2px;
            padding: 0 2px;
            color: __text_primary__;
            background: transparent;
        }
        QGroupBox#sourceSection, QGroupBox#outputSection, QGroupBox#runSection {
            margin-top: 0px;
            padding: 14px 14px 12px 14px;
            background: __surface__;
            border: 1px solid __border__;
            border-radius: 16px;
        }
        QGroupBox#formatSection, QGroupBox#saveSection {
            margin-top: 0px;
            padding: 11px 12px 8px 12px;
            padding-bottom: 4px;
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 12px;
        }
        QFrame#mixedUrlAlert {
            background: __surface__;
            border: 1px solid __border__;
            border-radius: 10px;
        }
        QFrame#mixedUrlOverlay {
            background: transparent;
            border: none;
        }
        QLabel#mixedUrlAlertTitle {
            color: __text_primary__;
            font-weight: 700;
            background: transparent;
        }
        QLabel#readySummaryLine {
            color: __text_muted__;
            font-size: 11px;
            font-weight: 500;
            padding: 0 1px;
        }
        QFrame#metricsStrip {
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
        }
        QLabel#metricInline {
            color: __text_primary__;
            font-weight: 700;
        }
        QLabel#metricInlineItem {
            color: __text_secondary__;
            font-weight: 600;
        }
        QFrame#downloadResultCard[state="info"] {
            background: __surface_soft__;
            border: 1px solid __border__;
            border-radius: 10px;
            padding: 4px 0px;
        }
        QFrame#downloadResultCard[state="latest"] {
            background: __accent_soft__;
            border: 1px solid __accent_border__;
            border-radius: 10px;
            padding: 4px 0px;
        }
        QLabel#downloadResultTitle {
            font-weight: 700;
        }
        QFrame#downloadResultCard[state="info"] QLabel#downloadResultTitle {
            color: __text_primary__;
        }
        QFrame#downloadResultCard[state="latest"] QLabel#downloadResultTitle {
            color: __accent_text__;
        }
        QLabel#downloadResultPath {
            color: __text_secondary__;
            padding-right: 4px;
        }
        QProgressBar {
            background: #dff1eb;
            border: 1px solid __border_strong__;
            border-radius: 5px;
            padding: 1px;
            min-height: 12px;
            max-height: 12px;
        }
        QProgressBar::chunk {
            border-radius: 4px;
            margin: 0px;
            background: __accent__;
        }
        QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
            background: __surface__;
            border: 1px solid __field_border__;
            border-radius: 8px;
            padding: 4px 8px;
            color: __field_text__;
            min-height: 28px;
        }
        QComboBox {
            padding: 5px 9px;
            padding-right: 34px;
            selection-background-color: __surface_selected_strong__;
            selection-color: __field_text__;
        }
        QLineEdit:read-only {
            background: __surface_soft_alt__;
            color: __field_readonly_text__;
        }
        QLineEdit:disabled, QPlainTextEdit:disabled, QListWidget:disabled, QComboBox:disabled {
            background: __surface_disabled__;
            border: 1px solid __field_disabled_border__;
            color: __field_disabled_text__;
        }
        QLineEdit:hover, QPlainTextEdit:hover, QListWidget:hover, QComboBox:hover {
            border: 1px solid __border_hover__;
            background: __surface__;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QComboBox:focus {
            border: 1px solid __accent__;
            background: __surface__;
        }
        QComboBox::drop-down {
            width: 30px;
            border: none;
            border-left: 1px solid __border_soft__;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
            background: __surface_soft_alt__;
            subcontrol-position: top right;
            subcontrol-origin: padding;
        }
        QComboBox::down-arrow {
            image: url("__combo_arrow_icon__");
            width: 10px;
            height: 6px;
        }
        QComboBox:disabled {
            background: __surface_disabled__;
            border: 1px solid __field_disabled_border__;
            color: __field_disabled_text__;
        }
        QComboBox::drop-down:disabled {
            background: __surface_soft__;
            border-left: 1px solid __border_soft__;
        }
        QListView#nativeComboView {
            background: __surface__;
            border: 1px solid __field_border__;
            border-radius: 8px;
            padding: 4px;
            outline: 0;
            margin: 0px;
        }
        QListView#nativeComboView::item {
            min-height: 28px;
            padding: 5px 9px;
            border-radius: 6px;
            color: __field_text__;
        }
        QListView#nativeComboView::item:hover {
            background: __surface_soft_alt__;
            color: __text_primary__;
        }
        QListView#nativeComboView::item:selected {
            background: __surface_selected_strong__;
            color: __accent_text__;
        }
        QListView#nativeComboView QScrollBar:vertical {
            background: __surface_soft_alt__;
            width: 19px;
            margin: 0px;
            border: none;
            border-left: 1px solid __border_soft__;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
        }
        QListView#nativeComboView QScrollBar::handle:vertical {
            background: #b2d8cf;
            min-height: 20px;
            margin: 2px;
            border-radius: 6px;
        }
        QListView#nativeComboView QScrollBar::handle:vertical:hover {
            background: #93c5b8;
        }
        QListView#nativeComboView QScrollBar::sub-line:vertical,
        QListView#nativeComboView QScrollBar::add-line:vertical {
            height: 18px;
            background: #e5f3ee;
            border: none;
        }
        QListView#nativeComboView QScrollBar::sub-line:vertical {
            border-top-right-radius: 8px;
        }
        QListView#nativeComboView QScrollBar::add-line:vertical {
            border-bottom-right-radius: 8px;
        }
        QListView#nativeComboView QScrollBar::sub-line:vertical:hover,
        QListView#nativeComboView QScrollBar::add-line:vertical:hover {
            background: #d7ebe4;
        }
        QListView#nativeComboView QScrollBar::sub-line:vertical:disabled,
        QListView#nativeComboView QScrollBar::add-line:vertical:disabled {
            background: #eef7f4;
        }
        QListView#nativeComboView QScrollBar::up-arrow:vertical,
        QListView#nativeComboView QScrollBar::down-arrow:vertical {
            width: 9px;
            height: 6px;
        }
        QListView#nativeComboView QScrollBar::add-page:vertical,
        QListView#nativeComboView QScrollBar::sub-page:vertical {
            background: transparent;
        }
        QPushButton {
            background: __surface_soft__;
            color: __button_text__;
            border-radius: 8px;
            padding: 3px 10px;
            border: 1px solid __border__;
            min-height: 28px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: __surface_soft_alt__;
            border: 1px solid __accent_border__;
            color: __button_hover_text__;
        }
        QPushButton:pressed {
            background: #def0ea;
            border: 1px solid #89beb0;
            color: __button_hover_text__;
        }
        QPushButton:disabled {
            background: __surface_disabled__;
            color: __button_disabled_text__;
            border: 1px solid __field_disabled_border__;
        }
        QPushButton:checked {
            background: __surface_selected_strong__;
            border: 1px solid __accent_border__;
            color: __accent_text__;
        }
        QPushButton#topNavButton {
            background: transparent;
            color: __nav_text__;
            border: 1px solid transparent;
            font-weight: 550;
            padding: 3px 10px;
        }
        QPushButton#topNavButton:hover {
            background: __surface_soft__;
            color: __button_hover_text__;
            border: 1px solid __border_soft__;
        }
        QPushButton#topNavButton:checked {
            background: __surface_selected__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
            font-weight: 650;
        }
        QPushButton#topNavButton:disabled {
            background: transparent;
            color: __nav_disabled__;
            border: 1px solid transparent;
        }
        QPushButton#primaryActionButton {
            background: __accent__;
            border: 1px solid __accent__;
            color: __text_inverse__;
            font-weight: 700;
            padding: 4px 14px;
            min-height: 32px;
        }
        QPushButton#primaryActionButton:hover {
            background: __accent_hover__;
            border: 1px solid __accent_hover__;
        }
        QPushButton#primaryActionButton:pressed {
            background: __accent_pressed__;
            border: 1px solid __accent_pressed__;
        }
        QPushButton#primaryActionButton:disabled {
            background: #a7d2c8;
            color: #e8f6f1;
            border: 1px solid #a7d2c8;
        }
        QPushButton#ghostButton {
            background: __surface__;
            border: 1px solid __accent_border__;
            border-radius: 8px;
            color: __accent_text__;
            padding: 2px 10px;
            min-height: 28px;
        }
        QPushButton#ghostButton:hover {
            background: __surface_soft_alt__;
            border: 1px solid __border_hover__;
            color: __accent_text__;
        }
        QPushButton#ghostButton:pressed {
            background: __accent_soft__;
            border: 1px solid __accent_border__;
        }
        QPushButton#ghostButton:disabled {
            background: __surface_disabled__;
            color: __button_disabled_text__;
            border: 1px solid __field_disabled_border__;
        }
        QCheckBox {
            color: __button_text__;
            spacing: 8px;
        }
        QRadioButton {
            color: __button_hover_text__;
            spacing: 8px;
        }
        QCheckBox:hover, QRadioButton:hover {
            color: __accent_text__;
        }
        QCheckBox:disabled, QRadioButton:disabled {
            color: __field_disabled_text__;
        }
        QCheckBox::indicator, QRadioButton::indicator {
            width: 16px;
            height: 16px;
            background: __surface__;
            border: 1px solid #98c1b6;
        }
        QCheckBox::indicator {
            border-radius: 4px;
        }
        QRadioButton::indicator {
            border-radius: 8px;
        }
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {
            border: 1px solid #7fb4a7;
            background: __surface_soft_alt__;
        }
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background: __accent__;
            border: 1px solid __accent__;
        }
        QCheckBox::indicator:pressed, QRadioButton::indicator:pressed {
            background: __accent_pressed__;
            border: 1px solid __accent_pressed__;
        }
        QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
            border: 1px solid #b8d1cb;
            background: #e5f2ee;
        }
        QCheckBox::indicator:checked:disabled, QRadioButton::indicator:checked:disabled {
            background: #b9d4cc;
            border: 1px solid #a0c0b7;
        }
        QListWidget::item {
            padding: 4px 8px;
            border-radius: 6px;
        }
        QListWidget::item:hover {
            background: __surface_soft_alt__;
        }
        QListWidget::item:selected {
            background: __surface_selected_strong__;
            color: __accent_text__;
        }
        QTabBar#topPanelTabs {
            background: transparent;
        }
        QTabBar#topPanelTabs::tab {
            min-height: 40px;
            margin-right: 4px;
            padding: 0 16px;
            border: 1px solid transparent;
            border-bottom: 2px solid transparent;
            border-radius: 10px;
            background: transparent;
            color: __tab_text__;
            font-weight: 600;
        }
        QTabBar#topPanelTabs::tab:hover {
            background: __surface_soft_alt__;
            color: __button_hover_text__;
        }
        QTabBar#topPanelTabs::tab:selected {
            background: __surface_selected__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
            border-bottom: 2px solid __accent__;
            font-weight: 700;
        }
        QTabBar#topPanelTabs::tab:focus {
            border: 1px solid __border_hover__;
            border-bottom: 2px solid __accent__;
        }
        QTabBar#topPanelTabs QToolButton {
            border-radius: 8px;
            padding: 0 6px;
            min-height: 28px;
        }
    """
    tokens = dict(_PALETTE)
    tokens["combo_arrow_icon"] = combo_arrow_path
    for key, value in tokens.items():
        style_sheet = style_sheet.replace(f"__{key}__", value)
    return style_sheet
