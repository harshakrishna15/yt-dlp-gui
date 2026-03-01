from __future__ import annotations


def build_stylesheet(combo_arrow_path: str) -> str:
    style_sheet = """
        QMainWindow, QWidget#appRoot {
            background: #f5f4ef;
        }
        QWidget {
            color: #22324a;
            font-size: 13px;
        }
        QLabel, QCheckBox, QRadioButton {
            background: transparent;
        }
        QMessageBox {
            background: #f5f4ef;
        }
        QMessageBox QLabel {
            color: #22324a;
            font-size: 14px;
        }
        QMessageBox QPushButton {
            min-width: 96px;
        }
        #titleLabel {
            font-size: 34px;
            font-weight: 700;
            color: #2f6fb5;
        }
        #subtleLabel {
            color: #5d748f;
        }
        QLabel#saveBlockLabel {
            color: #5a6f88;
            font-size: 12px;
            font-weight: 600;
        }
        #statusLine {
            color: #5d748f;
        }
        QGroupBox {
            border: 1px solid #d8d3c7;
            border-top: 1px solid #e4dfd4;
            border-bottom: 1px solid #cdc8bc;
            border-radius: 14px;
            margin-top: 18px;
            padding-top: 12px;
            padding-bottom: 8px;
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #fcfbf8,
                stop: 1 #f7f5ef
            );
            font-weight: 700;
            color: #1f3550;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 13px;
            top: -1px;
            padding: 0 6px;
            color: #1f3550;
            background: #f5f4ef;
            border-radius: 6px;
        }
        QGroupBox#sourceSection, QGroupBox#outputSection, QGroupBox#runSection {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #fcfaf5,
                stop: 1 #f6f3ec
            );
        }
        QGroupBox#formatSection, QGroupBox#saveSection {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #ffffff,
                stop: 1 #faf8f3
            );
            border: 1px solid #dbd4c7;
            border-top: 1px solid #e9e2d6;
            border-bottom: 1px solid #cec7ba;
        }
        QGroupBox#sourceSection::title, QGroupBox#outputSection::title, QGroupBox#runSection::title {
            background: #f6f3ec;
        }
        QGroupBox#formatSection::title, QGroupBox#saveSection::title {
            background: #fbf8f1;
        }
        QFrame#mixedUrlAlert {
            background: #f7f3ea;
            border: 1px solid #ddd4c6;
            border-radius: 12px;
        }
        QFrame#mixedUrlOverlay {
            background: transparent;
            border: none;
        }
        QLabel#mixedUrlAlertTitle {
            color: #1f3550;
            font-weight: 700;
            background: transparent;
        }
        QLabel#sourceHelperHint {
            color: #6b8097;
            font-size: 12px;
        }
        QLabel#sourceFeedback {
            border: 1px solid #d3dee9;
            border-radius: 10px;
            padding: 7px 10px;
            color: #355170;
            background: #edf3f8;
        }
        QLabel#sourceFeedback[tone="neutral"] {
            border: 1px solid #d3dee9;
            color: #355170;
            background: #edf3f8;
        }
        QLabel#sourceFeedback[tone="loading"] {
            border: 1px solid #cad9ea;
            color: #2e5680;
            background: #e8f1fb;
        }
        QLabel#sourceFeedback[tone="success"] {
            border: 1px solid #bddccc;
            color: #22553b;
            background: #e6f5ec;
        }
        QLabel#sourceFeedback[tone="warning"] {
            border: 1px solid #e1cf9e;
            color: #6e5320;
            background: #faf2dd;
        }
        QLabel#sourceFeedback[tone="error"] {
            border: 1px solid #e2b6b6;
            color: #7a2d2d;
            background: #faeaea;
        }
        QFrame#metricsStrip {
            background: #f1f5fa;
            border: 1px solid #d2ddea;
            border-radius: 12px;
            padding: 5px 8px;
        }
        QLabel#metricInline {
            color: #2a4360;
            font-weight: 700;
        }
        QLabel#metricInlineItem {
            color: #355170;
            font-weight: 600;
        }
        QFrame#downloadResultCard {
            background: #e8f5ec;
            border: 1px solid #bfd9c9;
            border-radius: 12px;
            padding: 2px 0px;
        }
        QLabel#downloadResultTitle {
            color: #21523a;
            font-weight: 700;
        }
        QLabel#downloadResultPath {
            color: #2f4f6e;
            padding-right: 4px;
        }
        QProgressBar {
            background: #e6edf5;
            border: 1px solid #c5d2e1;
            border-radius: 7px;
            min-height: 12px;
            max-height: 12px;
        }
        QProgressBar::chunk {
            border-radius: 6px;
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 #5f8fca,
                stop: 1 #2f6fb5
            );
        }
        QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
            background: #fefdfa;
            border: 1px solid #ccc7bd;
            border-top: 1px solid #dad4cb;
            border-bottom: 1px solid #bdb8af;
            border-radius: 10px;
            padding: 4px 8px;
            min-height: 27px;
        }
        QComboBox {
            padding: 5px 10px;
            padding-right: 34px;
            selection-background-color: #dce9f9;
            selection-color: #22324a;
        }
        QLineEdit:read-only {
            background: #fcfbf8;
            color: #41556c;
        }
        QLineEdit:hover, QPlainTextEdit:hover, QListWidget:hover, QComboBox:hover {
            border: 1px solid #a9bbd4;
            border-bottom: 1px solid #96abc8;
            background: #ffffff;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QComboBox:focus {
            border: 1px solid #7ea2d5;
            border-bottom: 1px solid #6b8fc2;
            background: #ffffff;
        }
        QComboBox::drop-down {
            width: 30px;
            border: none;
            border-left: 1px solid #d5cec1;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #faf7f1,
                stop: 1 #f2eee5
            );
            subcontrol-position: top right;
            subcontrol-origin: padding;
        }
        QComboBox::down-arrow {
            image: url("__combo_arrow_icon__");
            width: 10px;
            height: 6px;
        }
        QComboBox:disabled {
            background: #ece9e1;
            border: 1px solid #d6d1c7;
            color: #9ea5b1;
        }
        QComboBox::drop-down:disabled {
            background: #e6e1d8;
            border-left: 1px solid #d2ccc0;
        }
        QListView#nativeComboView {
            background: #fefdfa;
            border: 1px solid #d1c9bc;
            border-radius: 10px;
            padding: 4px;
            outline: 0;
            margin: 0px;
        }
        QListView#nativeComboView::item {
            min-height: 28px;
            padding: 5px 9px;
            border-radius: 8px;
            color: #22324a;
        }
        QListView#nativeComboView::item:hover {
            background: #eaf1fb;
            color: #20374f;
        }
        QListView#nativeComboView::item:selected {
            background: #dce9f9;
            color: #1f3556;
        }
        QPushButton {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8fbff,
                stop: 1 #e7eef9
            );
            color: #2b4568;
            border-radius: 10px;
            padding: 3px 11px;
            border: 1px solid #bdcade;
            border-top: 1px solid #cfdbec;
            border-bottom: 1px solid #a2b5d1;
            min-height: 27px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #fbfdff,
                stop: 1 #edf3ff
            );
            border: 1px solid #acbdd6;
            border-bottom: 1px solid #93a8ca;
        }
        QPushButton:pressed {
            background: #dbe7fb;
            border: 1px solid #90a7ca;
            border-top: 1px solid #8499bb;
            border-bottom: 1px solid #9fb3d4;
        }
        QPushButton:disabled {
            background: #ece9e1;
            color: #9ea5b1;
            border: 1px solid #d5d0c6;
        }
        QPushButton:checked {
            background: #2f6fb5;
            border: 1px solid #295d95;
            color: #ffffff;
        }
        QPushButton#primaryActionButton {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #4f86cc,
                stop: 1 #2f6fb5
            );
            border: 1px solid #295d95;
            border-top: 1px solid #3873b5;
            border-bottom: 1px solid #224c7a;
            color: #ffffff;
            font-weight: 700;
        }
        QPushButton#primaryActionButton:hover {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #5a91d5,
                stop: 1 #3477bf
            );
            border: 1px solid #2f669f;
            border-bottom: 1px solid #265488;
        }
        QPushButton#primaryActionButton:pressed {
            background: #2a649f;
            border: 1px solid #255589;
            border-top: 1px solid #214c79;
            border-bottom: 1px solid #2a639d;
        }
        QPushButton#primaryActionButton:disabled {
            background: #c9d8ec;
            color: #f2f6fb;
            border: 1px solid #bccbdf;
        }
        QPushButton#ghostButton {
            background: #f4f8fe;
            border: 1px solid #c3d2e4;
            color: #2f6fb5;
            padding: 2px 10px;
            min-height: 27px;
        }
        QPushButton#ghostButton:hover {
            background: #eaf2fd;
            border: 1px solid #a9bfdc;
            color: #275f9b;
        }
        QPushButton#ghostButton:pressed {
            background: #deebfd;
            border: 1px solid #96b1d6;
        }
        QPushButton#ghostButton:disabled {
            background: #eff2f7;
            color: #9aa8ba;
            border: 1px solid #d6deea;
        }
        QCheckBox {
            color: #4f6886;
            spacing: 8px;
        }
        QRadioButton {
            color: #22324a;
            spacing: 8px;
        }
        QCheckBox:hover, QRadioButton:hover {
            color: #2e4e7d;
        }
        QCheckBox:disabled, QRadioButton:disabled {
            color: #93a2b6;
        }
        QCheckBox::indicator, QRadioButton::indicator {
            width: 16px;
            height: 16px;
            background: #fefdfa;
            border: 1px solid #aab8cd;
        }
        QCheckBox::indicator {
            border-radius: 4px;
        }
        QRadioButton::indicator {
            border-radius: 8px;
        }
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {
            border: 1px solid #8fa4c8;
            background: #fefcf9;
        }
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background: #2f6fb5;
            border: 1px solid #295d95;
        }
        QCheckBox::indicator:pressed, QRadioButton::indicator:pressed {
            background: #285a92;
            border: 1px solid #244f7f;
        }
        QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
            border: 1px solid #bac2ce;
            background: #e6eaf1;
        }
        QCheckBox::indicator:checked:disabled, QRadioButton::indicator:checked:disabled {
            background: #c8d0de;
            border: 1px solid #b3bdcb;
        }
        QListWidget::item {
            padding: 4px 8px;
            border-radius: 8px;
        }
        QListWidget::item:hover {
            background: #e9eef7;
        }
        QListWidget::item:selected {
            background: #dce9f8;
            color: #24405f;
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
            color: #4f6886;
            font-weight: 600;
        }
        QTabBar#topPanelTabs::tab:hover {
            background: #e9eff8;
            color: #22324a;
        }
        QTabBar#topPanelTabs::tab:selected {
            background: #edf3fb;
            color: #1f3550;
            border: 1px solid #c8d6ea;
            border-bottom: 2px solid #2f6fb5;
            font-weight: 700;
        }
        QTabBar#topPanelTabs::tab:focus {
            border: 1px solid #8aa9d3;
            border-bottom: 2px solid #2f6fb5;
        }
        QTabBar#topPanelTabs QToolButton {
            border-radius: 8px;
            padding: 0 6px;
            min-height: 28px;
        }
    """
    return style_sheet.replace("__combo_arrow_icon__", combo_arrow_path)
