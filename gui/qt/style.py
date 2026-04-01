from __future__ import annotations


_PALETTE = {
    "page_bg_top": "#111514",
    "page_bg_bottom": "#0d1110",
    "surface_glass": "#1c211f",
    "surface_glass_strong": "#202624",
    "surface_soft_glass": "#171c1b",
    "surface_soft_glass_strong": "#191f1d",
    "accent_wash": "rgba(45, 143, 112, 72)",
    "accent_wash_strong": "rgba(45, 143, 112, 116)",
    "scroll_handle": "#5b625f",
    "scroll_handle_hover": "#727a76",
    "text_primary": "#edf2ef",
    "text_muted": "#aab2ae",
    "text_label": "#bcc4c0",
    "text_secondary": "#d6ddd9",
    "text_inverse": "#f6fbf8",
    "surface": "#1f2422",
    "surface_soft": "#171c1b",
    "surface_soft_alt": "#252b28",
    "surface_disabled": "#1b201f",
    "surface_selected": "#2a302d",
    "surface_selected_strong": "#24453b",
    "border": "#48504c",
    "border_strong": "#5f6864",
    "border_soft": "#353d39",
    "border_hover": "#6a736f",
    "accent": "#2d8f70",
    "accent_hover": "#38a27f",
    "accent_pressed": "#226d55",
    "accent_soft": "#18342d",
    "accent_soft_hover": "#1f443a",
    "accent_border": "#418e75",
    "accent_text": "#8bdcbe",
    "accent_toast_bg": "#183a31",
    "field_text": "#eef3ef",
    "field_readonly_text": "#dbe2de",
    "field_surface": "#202725",
    "field_surface_hover": "#262d2a",
    "field_surface_focus": "#2b332f",
    "field_surface_readonly": "#1b201f",
    "field_border": "#424a46",
    "field_disabled_border": "#303734",
    "field_disabled_text": "#858d89",
    "tab_text": "#a5ada9",
    "nav_text": "#d5dcd8",
    "nav_disabled": "#686f6c",
    "button_text": "#e7ece9",
    "button_hover_text": "#ffffff",
    "button_disabled_text": "#737b77",
    "warning_bg": "#473621",
    "warning_border": "#89653f",
    "warning_text": "#f1cb8a",
    "error_bg": "#412320",
    "error_border": "#a4564d",
    "error_text": "#ff897d",
}

_INPUT_RADIUS = "22px"


def build_stylesheet(combo_arrow_path: str) -> str:
    style_sheet = """
        QMainWindow, QWidget#appRoot {
            background: __page_bg_bottom__;
        }
        QStackedWidget#panelStack {
            background: __page_bg_bottom__;
            border: none;
        }
        QWidget#downloadsPage, QWidget#panelPage {
            background: transparent;
            border: none;
        }
        QWidget#topBarShell {
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
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
            font-size: 14px;
            font-family: "Avenir Next";
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
            padding: 0px 0px 1px 2px;
            background: transparent;
            border: none;
        }
        QLabel#sectionHeaderTitle {
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            color: __text_primary__;
            font-size: 18px;
            font-weight: 800;
        }
        QLabel#sectionMetaChip {
            background: transparent;
            border: none;
            color: __text_muted__;
            font-size: 10px;
            font-weight: 800;
            padding: 0px;
        }
        QLabel#panelHeaderTitle {
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            color: __text_primary__;
            font-size: 20px;
            font-weight: 800;
        }
        QLabel#cardHeaderTitle {
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            color: __text_label__;
            font-size: 15px;
            font-weight: 800;
            letter-spacing: 0.8px;
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
        QGroupBox#sourceSection {
            background: transparent;
            border: none;
            padding: 0px;
        }
        QWidget#outputSection {
            margin-top: 0px;
            padding: 0px;
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QGroupBox#runSection {
            margin-top: 0px;
            padding: 0px;
            background: transparent;
            border: none;
        }
        QWidget#outputSection[stage="staged"] {
            background: transparent;
            border: none;
        }
        QWidget#outputSection[stage="loading"] {
            background: transparent;
            border: none;
        }
        QGroupBox#formatSection {
            margin-top: 0px;
            padding: 0px;
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
        }
        QWidget#saveSection {
            background: transparent;
            border: none;
        }
        QWidget#outputCardBlock {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QWidget#outputSection[stage="ready"] QGroupBox#formatSection {
            background: __surface__;
        }
        QGroupBox#formatSection[stage="staged"] {
            background: __surface__;
        }
        QGroupBox#formatSection[stage="loading"] {
            background: __surface__;
        }
        QWidget#commandBar {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QWidget#commandBar QFrame#urlInputShell {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QWidget#commandBar QFrame#urlInputShell[state="hover"] {
            background: transparent;
            border: none;
        }
        QWidget#commandBar QFrame#urlInputShell[state="focus"] {
            background: transparent;
            border: none;
        }
        QWidget#commandBar QLineEdit#urlInputField {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
            padding: 8px 16px;
            color: __field_text__;
            font-size: 16px;
            selection-background-color: __accent_wash_strong__;
            selection-color: __text_primary__;
        }
        QWidget#commandBar QLineEdit#urlInputField:disabled {
            color: __field_disabled_text__;
        }
        QWidget#commandBar QPushButton {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            font-size: 14px;
            font-weight: 700;
            padding: 8px 16px;
        }
        QWidget#commandBar QPushButton:hover {
            background: __surface__;
            border: 1px solid __border_hover__;
        }
        QWidget#commandBar QPushButton:pressed {
            background: __surface_selected__;
            border: 1px solid __accent_border__;
        }
        QWidget#commandBar QPushButton#analyzeUrlButton {
            background: __accent__;
            color: __text_inverse__;
            border: 1px solid __accent__;
            font-weight: 700;
            padding: 8px 16px;
            min-height: 0px;
            border-radius: 18px;
        }
        QWidget#commandBar QPushButton#analyzeUrlButton:hover {
            background: __accent_hover__;
            border: 1px solid __accent_hover__;
        }
        QWidget#commandBar QPushButton#analyzeUrlButton:pressed {
            background: __accent_pressed__;
            border: 1px solid __accent_pressed__;
        }
        QWidget#commandBar QPushButton#analyzeUrlButton[mode="ready"] {
            background: __surface_glass_strong__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
        }
        QWidget#commandBar QPushButton#analyzeUrlButton[mode="ready"]:hover {
            background: __surface__;
            border: 1px solid __accent__;
        }
        QWidget#commandBar QPushButton#analyzeUrlButton[mode="loading"] {
            background: __accent_soft__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
        }
        QWidget#commandBar QPushButton#analyzeUrlButton:disabled {
            background: __surface_disabled__;
            color: __button_disabled_text__;
            border: 1px solid __field_disabled_border__;
        }
        QFrame#sourceContentPanel {
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 24px;
        }
        QFrame#sectionDivider {
            background: __border_soft__;
            border: none;
            border-radius: 0px;
        }
        QWidget#workspaceTabBar {
            background: transparent;
            border: none;
        }
        QWidget#topNavRail {
            background: __surface_soft_glass__;
            border: 1px solid __border_soft__;
            border-radius: 22px;
        }
        QFrame#workspaceTabUnderline {
            background: __accent__;
            border: none;
            border-radius: 0px;
        }
        QFrame#topNavSelection {
            background: __surface_selected_strong__;
            border: 1px solid __accent_border__;
            border-radius: 18px;
        }
        QPushButton#workspaceTabButton {
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            border-radius: 0px;
            color: __text_muted__;
            font-size: 16px;
            font-weight: 700;
            padding: 3px 0px 8px 0px;
        }
        QPushButton#workspaceTabButton:hover {
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            color: __text_secondary__;
        }
        QPushButton#workspaceTabButton:checked {
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            color: __accent__;
        }
        QLabel#workspaceEmptyLabel {
            color: __text_muted__;
            font-size: 13px;
            font-weight: 600;
            padding: 2px 0px 2px 0px;
        }
        QFrame#sourcePreviewCard {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 16px;
        }
        QFrame#sourcePreviewCard[stage="loading"] {
            background: __surface__;
        }
        QLabel#sourcePreviewBadge {
            background: __accent_soft__;
            color: __text_inverse__;
            border: none;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 800;
        }
        QLabel#sourcePreviewEyebrow {
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            color: __accent_text__;
            font-size: 11px;
            font-weight: 800;
        }
        QLabel#sourcePreviewTitle {
            color: __text_primary__;
            font-size: 16px;
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
            background: transparent;
            border: none;
            border-radius: 0px;
            color: __text_secondary__;
            font-size: 10px;
            font-weight: 700;
            padding: 0px 7px 0px 0px;
        }
        QFrame#mixedUrlOverlay {
            background: rgba(23, 34, 45, 20);
            border: none;
        }
        QFrame#mixedUrlAlert {
            background: __surface_glass_strong__;
            border: none;
            border-radius: 18px;
        }
        QLabel#mixedUrlAlertTitle {
            color: __text_primary__;
            font-weight: 700;
            background: transparent;
        }
        QFrame#sourceToastCard {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
        }
        QFrame#sourceToastCard[tone="success"] {
            background: __accent_toast_bg__;
            border: 1px solid __accent_border__;
        }
        QFrame#sourceToastCard[tone="warning"] {
            background: __warning_bg__;
            border: 1px solid __warning_border__;
        }
        QFrame#sourceToastCard[tone="error"] {
            background: __error_bg__;
            border: 1px solid __error_border__;
        }
        QLabel#sourceToastTitle {
            color: __text_muted__;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.8px;
        }
        QLabel#sourceToastMessage {
            color: __text_primary__;
            font-size: 13px;
            font-weight: 700;
        }
        QPushButton#sourceToastDismissButton {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 12px;
            color: __text_muted__;
            font-family: "Avenir Next";
            font-size: 18px;
            font-weight: 500;
            padding: 0px;
        }
        QPushButton#sourceToastDismissButton:hover {
            background: rgba(255, 255, 255, 40);
            border: 1px solid rgba(255, 255, 255, 34);
        }
        QPushButton#sourceToastDismissButton:pressed {
            background: rgba(15, 33, 45, 36);
            border: 1px solid rgba(15, 33, 45, 30);
        }
        QFrame#sourceToastCard[tone="success"] QLabel#sourceToastTitle {
            color: __accent_text__;
        }
        QFrame#sourceToastCard[tone="success"] QLabel#sourceToastMessage {
            color: __text_inverse__;
        }
        QFrame#sourceToastCard[tone="success"] QPushButton#sourceToastDismissButton {
            color: __accent_text__;
        }
        QFrame#sourceToastCard[tone="warning"] QLabel#sourceToastTitle,
        QFrame#sourceToastCard[tone="warning"] QLabel#sourceToastMessage {
            color: __warning_text__;
        }
        QFrame#sourceToastCard[tone="warning"] QPushButton#sourceToastDismissButton {
            color: __warning_text__;
        }
        QFrame#sourceToastCard[tone="error"] QLabel#sourceToastTitle,
        QFrame#sourceToastCard[tone="error"] QLabel#sourceToastMessage {
            color: __error_text__;
        }
        QFrame#sourceToastCard[tone="error"] QPushButton#sourceToastDismissButton {
            color: __error_text__;
        }
        QFrame#panelCard {
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 24px;
        }
        QFrame#panelFormCard {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QFrame#panelEmptyCard {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 24px;
        }
        QLabel#panelFormIntro {
            color: __text_muted__;
            font-size: 12px;
            font-weight: 600;
        }
        QFrame#settingsRowCard, QFrame#settingsAppCard {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QLabel#settingsRowTitle {
            color: __text_primary__;
            font-size: 16px;
            font-weight: 800;
        }
        QLabel#settingsRowDescription {
            color: __text_muted__;
            font-size: 12px;
            font-weight: 600;
            line-height: 1.35em;
        }
        QLabel#settingsAppName {
            color: __text_primary__;
            font-size: 18px;
            font-weight: 800;
        }
        QLabel#settingsAppVersion {
            color: __text_muted__;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#panelEmptyBadge {
            background: __accent_soft__;
            border: none;
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
        QFrame#queueEmptyPlaceholder {
            background: transparent;
            border: none;
        }
        QLabel#queueEmptyIcon {
            background: __surface_soft_alt__;
            color: __text_inverse__;
            border: none;
            border-radius: 18px;
            font-size: 28px;
            font-weight: 800;
        }
        QLabel#queueEmptyTitle {
            color: __text_primary__;
            font-size: 18px;
            font-weight: 800;
        }
        QLabel#queueEmptyDescription {
            color: __text_muted__;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#panelInlineMeta {
            color: __text_muted__;
            font-size: 12px;
            font-weight: 600;
        }
        QLabel#readySummaryLine {
            color: __text_secondary__;
            font-size: 14px;
            font-weight: 700;
            padding: 1px 0px 3px 0px;
            min-height: 20px;
            background: transparent;
            border: none;
        }
        QLabel#readySummaryLine[compact="true"] {
            font-size: 13px;
            min-height: 18px;
            padding: 0px 0px 2px 0px;
        }
        QFrame#metricsStrip {
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
        }
        QFrame#progressCard {
            background: __surface_soft_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 16px;
        }
        QFrame#progressCard[state="active"] {
            border: 1px solid __accent_border__;
        }
        QGroupBox#runSection[embedded="true"] {
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }
        QFrame#runActivityCard {
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 24px;
        }
        QFrame#runActionCard {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QLabel#metricInline, QLabel#metricInlineItem {
            background: transparent;
            border: none;
            border-radius: 0px;
            color: __text_secondary__;
            font-weight: 700;
            padding: 0px 0px 3px 0px;
            min-height: 20px;
        }
        QLabel#metricInline[compact="true"], QLabel#metricInlineItem[compact="true"] {
            font-size: 10px;
            padding: 0px 0px 2px 0px;
            min-height: 18px;
        }
        QProgressBar {
            background: __surface_soft_alt__;
            border: 1px solid __border_soft__;
            border-radius: 5px;
            padding: 0px;
            min-height: 10px;
            max-height: 10px;
        }
        QProgressBar::chunk {
            border-radius: 5px;
            margin: 0px;
            background: __accent__;
        }
        QProgressBar#workspaceSummaryProgress {
            background: __surface_soft_alt__;
            border: none;
            min-height: 4px;
            max-height: 4px;
            border-radius: 2px;
        }
        QProgressBar#workspaceSummaryProgress::chunk {
            border-radius: 2px;
        }
        QLineEdit {
            background: __field_surface__;
            border: 1px solid __field_border__;
            border-radius: __input_radius__;
            color: __field_text__;
            selection-background-color: __accent_wash_strong__;
            selection-color: __text_primary__;
        }
        QComboBox {
            background: __field_surface__;
            border: 1px solid __border_soft__;
            border-radius: 16px;
            color: __field_text__;
            selection-background-color: __surface_selected_strong__;
            selection-color: __field_text__;
            padding: 7px 16px;
            padding-right: 46px;
            font-weight: 600;
        }
        QPlainTextEdit, QListWidget {
            background: __surface__;
            border: 1px solid __field_border__;
            border-radius: 18px;
            color: __field_text__;
        }
        QLineEdit {
            padding: 8px 16px;
        }
        QPlainTextEdit, QListWidget {
            padding: 8px 12px;
        }
        QWidget#outputCardBlock QLabel#outputFormLabel,
        QWidget#outputCardBlock QLabel#saveBlockLabel {
            padding: 0px 2px 1px 0px;
        }
        QLineEdit:read-only {
            background: __field_surface_readonly__;
            border: 1px solid __border_soft__;
            color: __field_readonly_text__;
        }
        QLineEdit:disabled, QPlainTextEdit:disabled, QListWidget:disabled, QComboBox:disabled {
            background: __surface_soft__;
            border: 1px solid __field_disabled_border__;
            color: __text_muted__;
        }
        QLineEdit:hover, QPlainTextEdit:hover, QListWidget:hover {
            border: 1px solid __border_hover__;
            background: __field_surface_hover__;
        }
        QComboBox:hover {
            border: 1px solid __border_hover__;
            background: __field_surface_hover__;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus {
            border: 1px solid __accent_border__;
            background: __field_surface_focus__;
        }
        QComboBox:focus {
            border: 1px solid __accent_border__;
            background: __field_surface_focus__;
        }
        QWidget#commandBar QLineEdit#urlInputField:hover,
        QWidget#commandBar QLineEdit#urlInputField:focus {
            border: 1px solid __accent_border__;
            background: __field_surface_focus__;
        }
        QGroupBox#formatSection QWidget#outputCardBlock QLineEdit {
            background: __field_surface__;
            border: 1px solid __border_soft__;
            border-radius: 16px;
        }
        QGroupBox#formatSection QWidget#outputCardBlock QLineEdit:hover {
            background: __field_surface_hover__;
        }
        QGroupBox#formatSection QWidget#outputCardBlock QLineEdit:focus {
            background: __field_surface_focus__;
            border: 1px solid __accent_border__;
        }
        QWidget#logsContentPage {
            background: transparent;
            border: none;
        }
        QFrame#logsConsoleCard {
            background: __surface_soft_alt__;
            border: 1px solid __border_soft__;
            border-radius: 24px;
        }
        QPlainTextEdit#logsView,
        QPlainTextEdit#logsView:hover,
        QPlainTextEdit#logsView:focus {
            background: transparent;
            border: none;
            border-radius: 20px;
            color: __text_secondary__;
            selection-background-color: __accent_wash_strong__;
            selection-color: __text_inverse__;
            font-size: 13px;
            padding: 18px 18px;
        }
        QListWidget#panelList {
            background: __surface_glass_strong__;
            border: none;
            border-radius: 18px;
        }
        QListWidget#workspaceList {
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
        }
        QListWidget#workspaceList::item {
            min-height: 82px;
            padding: 0px;
            border: none;
            background: transparent;
        }
        QListWidget#workspaceList::item:selected {
            background: transparent;
            color: __text_primary__;
            border-radius: 0px;
        }
        QFrame#workspaceSummaryCard {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
        }
        QFrame#workspaceSummaryCard[tone="active"] {
            background: __surface_selected__;
            border-color: __accent_border__;
        }
        QLabel#workspaceSummaryBadge {
            background: __surface_soft_alt__;
            color: __text_primary__;
            border-radius: 14px;
            font-size: 12px;
            font-weight: 800;
        }
        QFrame#workspaceSummaryCard[tone="active"] QLabel#workspaceSummaryBadge {
            background: __accent_wash_strong__;
            color: __text_inverse__;
        }
        QLabel#workspaceSummaryTitle {
            color: __text_primary__;
            font-size: 17px;
            font-weight: 800;
        }
        QLabel#workspaceSummaryMeta {
            color: __text_muted__;
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#workspaceSummaryStatus {
            background: __surface_soft_alt__;
            border: 1px solid __border_soft__;
            border-radius: 13px;
            color: __text_secondary__;
            font-size: 12px;
            font-weight: 700;
            padding: 6px 12px;
        }
        QFrame#workspaceSummaryCard[tone="active"] QLabel#workspaceSummaryStatus {
            background: __accent_wash__;
            border-color: __accent_border__;
            color: __accent_text__;
        }
        QComboBox::drop-down {
            width: 32px;
            border: none;
            background: transparent;
            subcontrol-position: center right;
            subcontrol-origin: padding;
        }
        QComboBox::down-arrow {
            image: url("__combo_arrow_icon__");
            width: 14px;
            height: 14px;
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
            border: 1px solid __border_soft__;
            border-radius: 20px;
            padding: 6px;
            outline: 0;
            margin: 0px;
        }
        QListView#nativeComboView::item {
            background: transparent;
            min-height: 30px;
            padding: 7px 12px;
            border-radius: 12px;
            color: __field_text__;
            font-weight: 600;
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
            border-radius: 16px;
            padding: 5px 14px;
            border: 1px solid __border_soft__;
            font-weight: 700;
        }
        QPushButton:hover {
            background: __surface_glass_strong__;
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
            background: __accent_wash_strong__;
            border: 1px solid __accent_border__;
            color: __accent_text__;
        }
        QPushButton#topNavButton {
            background: transparent;
            color: __nav_text__;
            border: none;
            border-radius: 18px;
            font-weight: 700;
            min-width: 112px;
            padding: 8px 14px;
            text-align: center;
        }
        QPushButton#topNavButton:hover {
            background: transparent;
            color: __button_hover_text__;
            border: none;
        }
        QPushButton#topNavButton:checked {
            background: transparent;
            color: __accent_text__;
            border: none;
            font-weight: 700;
        }
        QPushButton#topNavButton:disabled {
            background: transparent;
            color: __nav_disabled__;
            border: none;
        }
        QPushButton#topIconButton {
            background: __surface_soft_glass__;
            color: __nav_text__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
            padding: 0px;
            min-width: 40px;
            min-height: 40px;
        }
        QPushButton#topIconButton:hover {
            background: __surface_selected__;
            color: __button_hover_text__;
            border: 1px solid __border_hover__;
        }
        QPushButton#topIconButton:checked {
            background: __surface_selected_strong__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
        }
        QPushButton#topIconButton:disabled {
            background: __surface__;
            color: __nav_disabled__;
            border: 1px solid __field_disabled_border__;
        }
        QPushButton#primaryActionButton,
        QPushButton#analyzeUrlButton {
            background: __accent__;
            border: 1px solid __accent__;
            color: __text_inverse__;
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            font-size: 15px;
            font-weight: 700;
            padding: 12px 20px;
            min-height: 46px;
        }
        QPushButton#primaryActionButton[compact="true"] {
            font-size: 14px;
            padding: 9px 16px;
            min-height: 40px;
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
            background: #2e5348;
            color: #88a79f;
            border: 1px solid #2e5348;
        }
        QPushButton#analyzeUrlButton[mode="ready"] {
            background: __surface_glass_strong__;
            color: __accent_text__;
            border: 1px solid __accent_border__;
        }
        QPushButton#analyzeUrlButton[mode="ready"]:hover {
            background: __accent_soft__;
            border: 1px solid __accent__;
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
        QWidget#commandBar QPushButton,
        QWidget#commandBar QPushButton#analyzeUrlButton {
            font-family: "Avenir Next";
            font-size: 14px;
            font-weight: 700;
        }
        QPushButton#ghostButton {
            background: transparent;
            border: 1px solid __border_soft__;
            border-radius: 16px;
            color: __button_text__;
            padding: 5px 12px;
        }
        QPushButton#ghostButton:hover {
            background: __surface_glass_strong__;
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
        QPushButton#secondaryActionButton {
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            color: __text_secondary__;
            font-size: 15px;
            font-weight: 700;
            min-height: 44px;
            padding: 10px 18px;
        }
        QPushButton#secondaryActionButton[compact="true"] {
            font-size: 14px;
            padding: 8px 16px;
            min-height: 38px;
        }
        QPushButton#secondaryActionButton:hover {
            background: __surface_selected__;
        }
        QPushButton#secondaryActionButton:disabled {
            color: __button_disabled_text__;
        }
        QPushButton#dangerActionButton {
            background: transparent;
            border: 1px solid __border_soft__;
            border-radius: 12px;
            color: __text_secondary__;
            font-size: 15px;
            font-weight: 700;
            min-height: 44px;
            padding: 10px 18px;
        }
        QPushButton#dangerActionButton[pill="true"] {
            border-radius: 20px;
        }
        QPushButton#dangerActionButton[compact="true"] {
            font-size: 14px;
            padding: 8px 16px;
            min-height: 38px;
        }
        QPushButton#dangerActionButton:hover {
            background: __surface_glass_strong__;
            border: 1px solid __border_hover__;
            color: __button_hover_text__;
        }
        QPushButton#dangerActionButton:pressed {
            background: __surface_selected__;
            border: 1px solid __border_hover__;
            color: __button_hover_text__;
        }
        QPushButton#dangerActionButton:disabled {
            background: transparent;
            color: __button_disabled_text__;
            border: 1px solid __field_disabled_border__;
        }
        QPushButton#compactButton {
            padding: 6px 14px;
        }
        QCheckBox {
            color: __button_text__;
            spacing: 10px;
        }
        QRadioButton {
            color: __button_hover_text__;
            spacing: 10px;
            font-size: 14px;
            font-weight: 600;
        }
        QWidget#contentModeSegment {
            background: __surface_soft_glass__;
            border: 1px solid __border_soft__;
            border-radius: 14px;
        }
        QFrame#contentModeSelection {
            background: __accent__;
            border: 1px solid __accent_border__;
            border-radius: 10px;
        }
        QRadioButton#contentModeButton, QPushButton#contentModeButton {
            background: transparent;
            border: none;
            border-radius: 10px;
            color: __nav_text__;
            font-size: 14px;
            font-weight: 700;
            spacing: 0px;
            padding: 0px 13px;
            text-align: center;
        }
        QRadioButton#contentModeButton::indicator {
            width: 0px;
            height: 0px;
            border: none;
            background: transparent;
        }
        QRadioButton#contentModeButton:hover, QPushButton#contentModeButton:hover {
            color: __button_hover_text__;
        }
        QRadioButton#contentModeButton:checked, QPushButton#contentModeButton:checked {
            color: __text_inverse__;
        }
        QRadioButton#contentModeButton:disabled, QPushButton#contentModeButton:disabled {
            color: __field_disabled_text__;
        }
        QRadioButton#contentModeButton:checked:disabled, QPushButton#contentModeButton:checked:disabled {
            color: rgba(246, 242, 234, 180);
        }
        QCheckBox:hover, QRadioButton:hover {
            color: __accent_text__;
        }
        QCheckBox:disabled, QRadioButton:disabled {
            color: __field_disabled_text__;
        }
        QCheckBox::indicator, QRadioButton::indicator {
            width: 18px;
            height: 18px;
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
            background: __surface_glass_strong__;
            color: __accent_text__;
            border: 1px solid transparent;
            border-bottom: 2px solid __accent__;
            font-weight: 700;
        }
        QTabBar#topPanelTabs::tab:focus {
            border: 1px solid transparent;
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
    tokens["input_radius"] = _INPUT_RADIUS
    for key, value in tokens.items():
        style_sheet = style_sheet.replace(f"__{key}__", value)
    return style_sheet
