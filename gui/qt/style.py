from __future__ import annotations


_PALETTE = {
    "page_bg_top": "#eef2f6",
    "page_bg_bottom": "#e4ebf2",
    "scroll_handle": "#b2beca",
    "scroll_handle_hover": "#8fa0ad",
    "text_primary": "#17222d",
    "text_muted": "#647383",
    "text_label": "#5b6b7b",
    "text_secondary": "#2d4051",
    "text_inverse": "#ffffff",
    "surface": "#ffffff",
    "surface_soft": "#f6f8fb",
    "surface_soft_alt": "#eef3f7",
    "surface_disabled": "#eef2f5",
    "surface_selected": "#e4efec",
    "surface_selected_strong": "#d6e6e2",
    "border": "#d3dde6",
    "border_strong": "#c2ced9",
    "border_soft": "#e0e7ee",
    "border_hover": "#90a6b8",
    "accent": "#1b6d63",
    "accent_hover": "#175d55",
    "accent_pressed": "#124b44",
    "accent_soft": "#e3efec",
    "accent_soft_hover": "#d9e8e4",
    "accent_border": "#9bbdb7",
    "accent_text": "#164f47",
    "field_text": "#223340",
    "field_readonly_text": "#375062",
    "field_border": "#c7d2dd",
    "field_disabled_border": "#d9e1e8",
    "field_disabled_text": "#8694a1",
    "tab_text": "#5d6f80",
    "nav_text": "#455969",
    "nav_disabled": "#9aa8b4",
    "button_text": "#2c4253",
    "button_hover_text": "#213847",
    "button_disabled_text": "#8a99a5",
    "warning_bg": "#fff4df",
    "warning_border": "#e6cd94",
    "warning_text": "#865f18",
    "error_bg": "#feeceb",
    "error_border": "#ebbbb7",
    "error_text": "#9a3c37",
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
        QWidget#downloadsPage, QWidget#panelPage {
            background: transparent;
            border: none;
        }
        QWidget#topBarShell {
            background: rgba(255, 255, 255, 238);
            border: 1px solid __border_soft__;
            border-radius: 16px;
        }
        QWidget#topBarBrand {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 __accent_soft__,
                stop: 1 __surface__
            );
            border: 1px solid __accent_border__;
            border-radius: 14px;
        }
        QWidget#topNavRail {
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 12px;
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
            background: __surface_soft__;
        }
        QMessageBox QLabel {
            color: __text_primary__;
            font-size: 14px;
        }
        QMessageBox QPushButton {
            min-width: 96px;
        }
        #titleLabel {
            font-size: 26px;
            font-weight: 800;
            color: __text_primary__;
        }
        #subtleLabel {
            color: __text_muted__;
            font-size: 11px;
            font-weight: 500;
        }
        QLabel#sectionFormLabel {
            color: __text_label__;
            font-size: 11px;
            font-weight: 600;
        }
        QLabel#outputFormLabel {
            color: __text_label__;
            font-size: 11px;
            font-weight: 600;
        }
        QLabel#saveBlockLabel {
            color: __text_label__;
            font-size: 11px;
            font-weight: 600;
        }
        #statusLine {
            color: __text_muted__;
            font-size: 11px;
        }
        QLabel#sectionStageHint {
            color: __accent_text__;
            font-size: 12px;
            font-weight: 600;
            padding: 7px 10px;
            background: __accent_soft__;
            border: 1px solid __accent_border__;
            border-radius: 11px;
        }
        QLabel#sectionHeaderTitle {
            color: __text_primary__;
            font-size: 17px;
            font-weight: 800;
        }
        QLabel#sectionMetaChip {
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 10px;
            color: __text_label__;
            font-size: 10px;
            font-weight: 800;
            padding: 3px 8px;
        }
        QLabel#panelHeaderTitle {
            color: __text_primary__;
            font-size: 20px;
            font-weight: 800;
        }
        QLabel#panelHeaderSubtitle {
            color: __text_muted__;
            font-size: 12px;
        }
        QLabel#cardHeaderTitle {
            color: __text_secondary__;
            font-size: 13px;
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
            padding: 15px 15px 13px 15px;
            background: __surface__;
            border: 1px solid __border__;
            border-radius: 18px;
        }
        QGroupBox#sourceSection {
            border: 1px solid __border_strong__;
        }
        QGroupBox#outputSection[stage="staged"], QGroupBox#runSection[stage="staged"] {
            background: rgba(255, 255, 255, 244);
            border: 1px solid __accent_border__;
        }
        QGroupBox#outputSection[stage="loading"], QGroupBox#runSection[stage="loading"] {
            background: rgba(255, 255, 255, 248);
            border: 1px solid __accent_border__;
        }
        QGroupBox#formatSection, QGroupBox#saveSection {
            margin-top: 0px;
            padding: 12px;
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 14px;
        }
        QGroupBox#outputSection[stage="ready"] QGroupBox#formatSection,
        QGroupBox#outputSection[stage="ready"] QGroupBox#saveSection {
            background: __surface_soft__;
            border: 1px solid __border__;
        }
        QGroupBox#formatSection[stage="staged"], QGroupBox#saveSection[stage="staged"] {
            background: __surface_soft__;
            border: 1px solid __border_soft__;
        }
        QGroupBox#formatSection[stage="loading"], QGroupBox#saveSection[stage="loading"] {
            background: __surface__;
            border: 1px solid __accent_border__;
        }
        QWidget#sourceHeroRow {
            background: __surface_soft__;
            border: 1px solid __field_border__;
            border-radius: 12px;
        }
        QFrame#sourcePreviewCard {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 __surface__,
                stop: 1 __surface_soft__
            );
            border: 1px solid __border_soft__;
            border-radius: 16px;
        }
        QFrame#sourcePreviewCard[stage="loading"] {
            background: __surface__;
            border: 1px solid __accent_border__;
        }
        QLabel#sourcePreviewBadge {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 __accent__,
                stop: 1 __accent_hover__
            );
            color: __text_inverse__;
            border-radius: 14px;
            font-size: 11px;
            font-weight: 800;
        }
        QLabel#sourcePreviewEyebrow {
            color: __accent_text__;
            font-size: 11px;
            font-weight: 800;
        }
        QLabel#sourcePreviewTitle {
            color: __text_primary__;
            font-size: 18px;
            font-weight: 800;
        }
        QLabel#sourcePreviewTitle[state="empty"] {
            color: __text_muted__;
        }
        QLabel#sourcePreviewPlaceholder {
            color: __text_secondary__;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#sourcePreviewSubtitle {
            color: __text_muted__;
            font-size: 12px;
        }
        QLabel#sourcePreviewDetailChip {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 10px;
            color: __text_secondary__;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 8px;
        }
        QLabel#sourceFeedbackLabel {
            border-radius: 11px;
            padding: 8px 10px;
            font-size: 12px;
            font-weight: 600;
            color: __text_secondary__;
            background: __surface_soft__;
            border: 1px solid __border_soft__;
        }
        QLabel#sourceFeedbackLabel[tone="loading"],
        QLabel#sourceFeedbackLabel[tone="success"] {
            color: __accent_text__;
            background: __accent_soft__;
            border: 1px solid __accent_border__;
        }
        QLabel#sourceFeedbackLabel[tone="warning"] {
            color: __warning_text__;
            background: __warning_bg__;
            border: 1px solid __warning_border__;
        }
        QLabel#sourceFeedbackLabel[tone="error"] {
            color: __error_text__;
            background: __error_bg__;
            border: 1px solid __error_border__;
        }
        QFrame#mixedUrlOverlay {
            background: rgba(23, 34, 45, 20);
            border: none;
        }
        QFrame#mixedUrlAlert {
            background: __surface__;
            border: 1px solid __border__;
            border-radius: 14px;
        }
        QLabel#mixedUrlAlertTitle {
            color: __text_primary__;
            font-weight: 700;
            background: transparent;
        }
        QFrame#panelCard {
            background: rgba(255, 255, 255, 240);
            border: 1px solid __border__;
            border-radius: 18px;
        }
        QFrame#panelFormCard, QFrame#panelEmptyCard {
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 16px;
        }
        QLabel#panelFormIntro {
            color: __text_muted__;
            font-size: 12px;
            font-weight: 600;
        }
        QLabel#panelEmptyBadge {
            background: __accent_soft__;
            border: 1px solid __accent_border__;
            border-radius: 14px;
            color: __accent_text__;
            font-size: 11px;
            font-weight: 800;
            padding: 5px 10px;
        }
        QLabel#panelEmptyTitle {
            color: __text_primary__;
            font-size: 18px;
            font-weight: 800;
        }
        QLabel#panelEmptyDescription {
            color: __text_muted__;
            font-size: 13px;
        }
        QLabel#panelEmptyHint {
            color: __text_secondary__;
            font-size: 12px;
            font-weight: 700;
        }
        QLabel#panelInlineMeta {
            color: __text_muted__;
            font-size: 12px;
            font-weight: 600;
        }
        QLabel#readySummaryLine {
            color: __text_muted__;
            font-size: 11px;
            font-weight: 600;
            padding: 6px 9px;
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 10px;
        }
        QFrame#metricsStrip {
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
        }
        QFrame#progressCard {
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 14px;
        }
        QFrame#progressCard[state="active"] {
            background: __surface__;
            border: 1px solid __accent_border__;
        }
        QLabel#metricInline, QLabel#metricInlineItem {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 9px;
            color: __text_secondary__;
            font-weight: 700;
            padding: 5px 8px;
        }
        QFrame#downloadResultCard[state="empty"] {
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 12px;
        }
        QFrame#downloadResultCard[state="ready"] {
            background: __surface__;
            border: 1px solid __accent_border__;
            border-radius: 12px;
        }
        QLabel#downloadResultTitle {
            color: __text_primary__;
            font-weight: 700;
        }
        QFrame#downloadResultCard[state="ready"] QLabel#downloadResultTitle {
            color: __accent_text__;
        }
        QLabel#downloadResultPath {
            color: __text_muted__;
            padding-right: 4px;
        }
        QFrame#downloadResultCard[state="ready"] QLabel#downloadResultPath {
            color: __text_secondary__;
        }
        QProgressBar {
            background: __surface_soft_alt__;
            border: 1px solid __border__;
            border-radius: 6px;
            padding: 1px;
            min-height: 13px;
            max-height: 13px;
        }
        QProgressBar::chunk {
            border-radius: 5px;
            margin: 0px;
            background: __accent__;
        }
        QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
            background: __surface__;
            border: 1px solid __field_border__;
            border-radius: 10px;
            padding: 5px 9px;
            color: __field_text__;
            min-height: 28px;
        }
        QComboBox {
            padding: 5px 9px;
            padding-right: 9px;
            selection-background-color: __surface_selected_strong__;
            selection-color: __field_text__;
        }
        QLineEdit:read-only {
            background: __surface_soft_alt__;
            color: __field_readonly_text__;
        }
        QLineEdit:disabled, QPlainTextEdit:disabled, QListWidget:disabled, QComboBox:disabled {
            background: __surface_soft__;
            border: 1px solid __field_disabled_border__;
            color: __text_muted__;
        }
        QLineEdit:hover, QPlainTextEdit:hover, QListWidget:hover, QComboBox:hover {
            border: 1px solid __border_hover__;
            background: __surface__;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QComboBox:focus {
            border: 1px solid __accent__;
            background: __surface__;
        }
        QPlainTextEdit#logsView {
            background: #15202b;
            border: 1px solid #223343;
            border-radius: 12px;
            color: #dce7f2;
            selection-background-color: #2a4f63;
            selection-color: #ffffff;
        }
        QListWidget#panelList {
            background: __surface__;
            border: 1px solid __field_border__;
            border-radius: 12px;
        }
        QComboBox::drop-down {
            width: 0px;
            border: none;
            background: transparent;
            subcontrol-position: top right;
            subcontrol-origin: padding;
        }
        QComboBox::down-arrow {
            image: none;
            width: 0px;
            height: 0px;
        }
        QComboBox:disabled {
            background: __surface_soft__;
            border: 1px solid __field_disabled_border__;
            color: __text_muted__;
        }
        QComboBox::drop-down:disabled {
            background: transparent;
            border: none;
        }
        QListView#nativeComboView {
            background: __surface__;
            border: 1px solid __field_border__;
            border-radius: 10px;
            padding: 4px;
            outline: 0;
            margin: 0px;
        }
        QListView#nativeComboView::item {
            min-height: 28px;
            padding: 5px 9px;
            border-radius: 7px;
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
            background: transparent;
            width: 10px;
            margin: 2px 0px 2px 0px;
            border: none;
        }
        QListView#nativeComboView QScrollBar::handle:vertical {
            background: __scroll_handle__;
            border-radius: 5px;
            min-height: 24px;
        }
        QListView#nativeComboView QScrollBar::handle:vertical:hover {
            background: __scroll_handle_hover__;
        }
        QListView#nativeComboView QScrollBar::sub-line:vertical,
        QListView#nativeComboView QScrollBar::add-line:vertical,
        QListView#nativeComboView QScrollBar::up-arrow:vertical,
        QListView#nativeComboView QScrollBar::down-arrow:vertical {
            height: 0px;
            width: 0px;
        }
        QListView#nativeComboView QScrollBar::add-page:vertical,
        QListView#nativeComboView QScrollBar::sub-page:vertical {
            background: transparent;
        }
        QPushButton {
            background: __surface__;
            color: __button_text__;
            border-radius: 10px;
            padding: 4px 12px;
            border: 1px solid __border__;
            min-height: 28px;
            font-weight: 650;
        }
        QPushButton:hover {
            background: __surface_soft__;
            border: 1px solid __border_hover__;
            color: __button_hover_text__;
        }
        QPushButton:pressed {
            background: __surface_selected__;
            border: 1px solid __accent_border__;
            color: __button_hover_text__;
        }
        QPushButton:disabled {
            background: __surface_soft__;
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
            font-weight: 650;
            padding: 4px 10px;
        }
        QPushButton#topNavButton:hover {
            background: __surface__;
            color: __button_hover_text__;
            border: 1px solid __border__;
        }
        QPushButton#topNavButton:checked {
            background: __surface__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
            font-weight: 650;
        }
        QPushButton#topNavButton:disabled {
            background: transparent;
            color: __nav_disabled__;
            border: 1px solid transparent;
        }
        QPushButton#primaryActionButton,
        QPushButton#analyzeUrlButton {
            background: __accent__;
            border: 1px solid __accent__;
            color: __text_inverse__;
            font-weight: 700;
            padding: 4px 14px;
            min-height: 32px;
        }
        QPushButton#primaryActionButton:hover,
        QPushButton#analyzeUrlButton:hover {
            background: __accent_hover__;
            border: 1px solid __accent_hover__;
        }
        QPushButton#primaryActionButton:pressed,
        QPushButton#analyzeUrlButton:pressed {
            background: __accent_pressed__;
            border: 1px solid __accent_pressed__;
        }
        QPushButton#primaryActionButton:disabled {
            background: #b4cbc6;
            color: #eff5f4;
            border: 1px solid #b4cbc6;
        }
        QPushButton#analyzeUrlButton[mode="ready"] {
            background: __surface__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
        }
        QPushButton#analyzeUrlButton[mode="ready"]:hover {
            background: __accent_soft__;
            border: 1px solid __accent_border__;
        }
        QPushButton#analyzeUrlButton[mode="loading"] {
            background: __accent_soft__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
        }
        QPushButton#analyzeUrlButton:disabled {
            background: __surface_disabled__;
            color: __button_disabled_text__;
            border: 1px solid __field_disabled_border__;
        }
        QPushButton#ghostButton {
            background: transparent;
            border: 1px solid __border__;
            border-radius: 10px;
            color: __button_text__;
            padding: 2px 10px;
            min-height: 28px;
        }
        QPushButton#ghostButton:hover {
            background: __surface_soft__;
            border: 1px solid __border_hover__;
            color: __button_hover_text__;
        }
        QPushButton#ghostButton:pressed {
            background: __surface_selected__;
            border: 1px solid __accent_border__;
        }
        QPushButton#ghostButton:disabled {
            background: transparent;
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
            border: 1px solid __field_border__;
        }
        QCheckBox::indicator {
            border-radius: 4px;
        }
        QRadioButton::indicator {
            border-radius: 8px;
        }
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {
            border: 1px solid __border_hover__;
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
            border: 1px solid __field_disabled_border__;
            background: __surface_disabled__;
        }
        QCheckBox::indicator:checked:disabled, QRadioButton::indicator:checked:disabled {
            background: #b7c8c4;
            border: 1px solid #aabbb7;
        }
        QListWidget::item {
            padding: 7px 9px;
            border-radius: 8px;
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
            background: __surface_soft__;
            color: __button_hover_text__;
        }
        QTabBar#topPanelTabs::tab:selected {
            background: __surface__;
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
