from __future__ import annotations


_PALETTE = {
    "page_bg_top": "#1b1b18",
    "page_bg_bottom": "#111210",
    "surface_glass": "rgba(48, 48, 43, 236)",
    "surface_glass_strong": "rgba(50, 50, 45, 248)",
    "surface_soft_glass": "rgba(38, 38, 35, 224)",
    "surface_soft_glass_strong": "rgba(38, 38, 35, 240)",
    "accent_wash": "rgba(36, 126, 97, 92)",
    "accent_wash_strong": "rgba(39, 147, 112, 146)",
    "scroll_handle": "#62625c",
    "scroll_handle_hover": "#7d7d75",
    "text_primary": "#f1eee7",
    "text_muted": "#b6b1a6",
    "text_label": "#c0baaf",
    "text_secondary": "#ded9cf",
    "text_inverse": "#f6f2ea",
    "surface": "#272724",
    "surface_soft": "#20201d",
    "surface_soft_alt": "#30302c",
    "surface_disabled": "#232320",
    "surface_selected": "#33332f",
    "surface_selected_strong": "#314d45",
    "border": "#505049",
    "border_strong": "#65655d",
    "border_soft": "#42423d",
    "border_hover": "#6d6d64",
    "accent": "#258161",
    "accent_hover": "#2d9571",
    "accent_pressed": "#1d6b51",
    "accent_soft": "#223a34",
    "accent_soft_hover": "#29463f",
    "accent_border": "#347c66",
    "accent_text": "#86d7b7",
    "field_text": "#f2ede5",
    "field_readonly_text": "#ddd7ca",
    "field_border": "#494943",
    "field_disabled_border": "#393934",
    "field_disabled_text": "#8c877f",
    "tab_text": "#b0aaa0",
    "nav_text": "#d8d2c8",
    "nav_disabled": "#6d6a62",
    "button_text": "#ece7de",
    "button_hover_text": "#ffffff",
    "button_disabled_text": "#7d7a72",
    "warning_bg": "#4a3c22",
    "warning_border": "#80663a",
    "warning_text": "#f3d08a",
    "error_bg": "#442421",
    "error_border": "#9f4b43",
    "error_text": "#ff7f72",
}


def build_stylesheet(combo_arrow_path: str) -> str:
    style_sheet = """
        QMainWindow, QWidget#appRoot {
            background: __page_bg_bottom__;
        }
        QWidget#downloadsPage, QWidget#panelPage {
            background: transparent;
            border: none;
        }
        QWidget#topBarShell {
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 0px;
            border-left: none;
            border-right: none;
            border-top: none;
            padding: 0px;
        }
        QWidget#topBarBrand {
            background: transparent;
            border-radius: 0px;
        }
        QWidget#topNavRail {
            background: transparent;
            border: none;
            border-radius: 0px;
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
        #titleLabel {
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            font-size: 28px;
            font-weight: 800;
            color: __text_primary__;
        }
        #subtleLabel {
            color: __text_muted__;
            font-size: 11px;
            font-weight: 600;
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
        QLabel#panelHeaderSubtitle {
            color: __text_muted__;
            font-size: 12px;
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
        QGroupBox#outputSection {
            margin-top: 0px;
            padding: 0px;
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 24px;
        }
        QGroupBox#runSection {
            margin-top: 0px;
            padding: 0px;
            background: transparent;
            border: none;
        }
        QGroupBox#outputSection[stage="staged"] {
            background: __surface_glass_strong__;
        }
        QGroupBox#outputSection[stage="loading"] {
            background: __surface_glass_strong__;
        }
        QGroupBox#formatSection, QGroupBox#saveSection {
            margin-top: 0px;
            padding: 0px;
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 20px;
        }
        QGroupBox#outputSection[stage="ready"] QGroupBox#formatSection,
        QGroupBox#outputSection[stage="ready"] QGroupBox#saveSection {
            background: __surface__;
        }
        QGroupBox#formatSection[stage="staged"], QGroupBox#saveSection[stage="staged"] {
            background: __surface__;
        }
        QGroupBox#formatSection[stage="loading"], QGroupBox#saveSection[stage="loading"] {
            background: __surface__;
        }
        QWidget#commandBar {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QWidget#commandBar QLineEdit {
            background: __surface__;
            border: 1px solid __field_border__;
            border-radius: 18px;
            padding: 8px 14px;
            color: __field_text__;
            font-size: 16px;
        }
        QWidget#commandBar QLineEdit:hover,
        QWidget#commandBar QLineEdit:focus {
            background: __surface__;
        }
        QWidget#commandBar QPushButton {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            font-size: 14px;
            font-weight: 700;
            padding: 8px 18px;
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
            border-bottom: 3px solid __border_soft__;
            color: __text_secondary__;
        }
        QPushButton#workspaceTabButton:checked {
            background: transparent;
            border: none;
            border-bottom: 3px solid __accent__;
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
            border-radius: 18px;
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
            font-size: 12px;
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
            font-size: 14px;
            font-weight: 700;
        }
        QLabel#sourcePreviewSubtitle {
            color: __text_muted__;
            font-size: 13px;
        }
        QLabel#sourcePreviewDetailChip {
            background: transparent;
            border: none;
            border-radius: 0px;
            color: __text_secondary__;
            font-size: 11px;
            font-weight: 700;
            padding: 0px 7px 0px 0px;
        }
        QLabel#sourceFeedbackLabel {
            border-radius: 18px;
            padding: 11px 14px;
            font-size: 13px;
            font-weight: 700;
            color: __text_muted__;
            background: transparent;
            border: none;
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
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
        }
        QFrame#sourceToastCard[tone="success"] {
            background: __accent_wash_strong__;
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
            font-size: 11px;
            font-weight: 700;
        }
        QLabel#sourceToastMessage {
            color: __text_primary__;
            font-size: 13px;
            font-weight: 700;
        }
        QFrame#sourceToastCard[tone="success"] QLabel#sourceToastTitle,
        QFrame#sourceToastCard[tone="success"] QLabel#sourceToastMessage {
            color: __accent_text__;
        }
        QFrame#sourceToastCard[tone="warning"] QLabel#sourceToastTitle,
        QFrame#sourceToastCard[tone="warning"] QLabel#sourceToastMessage {
            color: __warning_text__;
        }
        QFrame#sourceToastCard[tone="error"] QLabel#sourceToastTitle,
        QFrame#sourceToastCard[tone="error"] QLabel#sourceToastMessage {
            color: __error_text__;
        }
        QFrame#panelCard {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QFrame#panelFormCard {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QFrame#panelEmptyCard {
            background: __surface_soft_glass_strong__;
            border: none;
            border-radius: 18px;
        }
        QLabel#panelFormIntro {
            color: __text_muted__;
            font-size: 12px;
            font-weight: 600;
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
        QLabel#panelInlineMeta {
            color: __text_muted__;
            font-size: 12px;
            font-weight: 600;
        }
        QLabel#readySummaryLine {
            color: __text_secondary__;
            font-size: 14px;
            font-weight: 700;
            padding: 1px 0px 0px 0px;
            background: transparent;
            border: none;
        }
        QLabel#runSectionLabel {
            color: __text_label__;
            font-size: 15px;
            font-weight: 800;
            letter-spacing: 0.9px;
        }
        QFrame#metricsStrip {
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
        }
        QFrame#progressCard {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QFrame#progressCard[state="active"] {
            background: transparent;
        }
        QFrame#runActivityCard, QFrame#runActionCard {
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 24px;
        }
        QFrame#sessionMetricCard {
            background: __surface__;
            border: 1px solid __border_soft__;
            border-radius: 16px;
        }
        QLabel#sessionMetricValue {
            color: __text_primary__;
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            font-size: 24px;
            font-weight: 800;
        }
        QLabel#sessionMetricLabel {
            color: __text_muted__;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#metricInline, QLabel#metricInlineItem {
            background: transparent;
            border: none;
            border-radius: 0px;
            color: __text_secondary__;
            font-weight: 700;
            padding: 0px;
        }
        QFrame#downloadResultCard[state="empty"] {
            background: __surface_soft_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 16px;
        }
        QFrame#downloadResultCard[state="ready"] {
            background: __accent_wash__;
            border: 1px solid __accent_border__;
            border-radius: 16px;
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
        QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
            background: __surface__;
            border: 1px solid __field_border__;
            border-radius: 16px;
            padding: 8px 12px;
            color: __field_text__;
            min-height: 34px;
        }
        QComboBox {
            padding: 7px 12px;
            padding-right: 9px;
            selection-background-color: __surface_selected_strong__;
            selection-color: __field_text__;
        }
        QLineEdit:read-only {
            background: __surface_soft__;
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
            border: none;
            border-radius: 16px;
            color: #dce7f2;
            selection-background-color: #2a4f63;
            selection-color: #ffffff;
        }
        QListWidget#panelList {
            background: __surface_glass_strong__;
            border: none;
            border-radius: 16px;
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
            background: __surface_glass_strong__;
            border: 1px solid __border_soft__;
            border-radius: 14px;
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
            border-radius: 16px;
            padding: 7px 14px;
            border: 1px solid __border_soft__;
            min-height: 34px;
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
            border-bottom: 3px solid transparent;
            border-radius: 0px;
            font-weight: 700;
            padding: 6px 12px 10px 12px;
        }
        QPushButton#topNavButton:hover {
            background: transparent;
            color: __button_hover_text__;
            border: none;
            border-bottom: 3px solid __border_soft__;
        }
        QPushButton#topNavButton:checked {
            background: transparent;
            color: __accent__;
            border: none;
            border-bottom: 3px solid __accent__;
            font-weight: 700;
        }
        QPushButton#topNavButton:disabled {
            background: transparent;
            color: __nav_disabled__;
            border: none;
            border-bottom: 3px solid transparent;
        }
        QPushButton#primaryActionButton,
        QPushButton#analyzeUrlButton {
            background: __accent__;
            border: 1px solid __accent__;
            color: __text_inverse__;
            font-family: "Arial Rounded MT Bold", "Avenir Next";
            font-size: 15px;
            font-weight: 700;
            padding: 10px 18px;
            min-height: 42px;
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
        QPushButton#ghostButton {
            background: transparent;
            border: 1px solid __border_soft__;
            border-radius: 16px;
            color: __button_text__;
            padding: 6px 12px;
            min-height: 30px;
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
            min-height: 40px;
        }
        QPushButton#secondaryActionButton:hover {
            background: __surface_selected__;
        }
        QPushButton#dangerActionButton {
            background: transparent;
            border: 1px solid __error_border__;
            color: __error_text__;
            font-size: 15px;
            font-weight: 700;
            min-height: 40px;
        }
        QPushButton#dangerActionButton:hover {
            background: rgba(159, 75, 67, 28);
            border: 1px solid __error_border__;
            color: __error_text__;
        }
        QPushButton#compactButton {
            padding: 5px 10px;
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
            background: __surface_soft__;
            border: 1px solid __border_soft__;
            border-radius: 18px;
            padding: 4px;
        }
        QRadioButton#contentModeButton {
            background: transparent;
            border: none;
            border-radius: 14px;
            color: __text_muted__;
            font-size: 15px;
            font-weight: 700;
            spacing: 0px;
            padding: 8px 14px;
        }
        QRadioButton#contentModeButton::indicator {
            width: 0px;
            height: 0px;
            border: none;
            background: transparent;
        }
        QRadioButton#contentModeButton:hover {
            color: __text_secondary__;
        }
        QRadioButton#contentModeButton:checked {
            background: __accent__;
            color: __text_inverse__;
        }
        QRadioButton#contentModeButton:disabled {
            color: __field_disabled_text__;
        }
        QRadioButton#contentModeButton:checked:disabled {
            background: #2e5348;
            color: #88a79f;
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
    for key, value in tokens.items():
        style_sheet = style_sheet.replace(f"__{key}__", value)
    return style_sheet
