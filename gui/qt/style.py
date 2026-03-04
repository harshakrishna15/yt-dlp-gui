from __future__ import annotations


def build_stylesheet(combo_arrow_path: str) -> str:
    style_sheet = """
        QMainWindow, QWidget#appRoot {
            background: #eef6f3;
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
            background: #9fcfc5;
            border-radius: 5px;
            min-height: 24px;
        }
        QScrollBar::handle:vertical:hover {
            background: #86bfb2;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: transparent;
        }
        QWidget {
            color: #1b2f46;
            font-size: 13px;
        }
        QLabel, QCheckBox, QRadioButton {
            background: transparent;
        }
        QMessageBox {
            background: #eef6f3;
        }
        QMessageBox QLabel {
            color: #1b2f46;
            font-size: 14px;
        }
        QMessageBox QPushButton {
            min-width: 96px;
        }
        #titleLabel {
            font-size: 34px;
            font-weight: 700;
            color: #0D9F8A;
        }
        #subtleLabel {
            color: #415a77;
        }
        QLabel#sectionFormLabel {
            color: #233f5e;
            font-size: 12px;
            font-weight: 600;
        }
        QLabel#outputFormLabel {
            color: #223f5d;
            font-size: 12px;
            font-weight: 650;
        }
        QLabel#saveBlockLabel {
            color: #254361;
            font-size: 12px;
            font-weight: 650;
        }
        #statusLine {
            color: #435d7b;
        }
        QGroupBox {
            border: none;
            border-radius: 0px;
            margin-top: 12px;
            padding-top: 8px;
            padding-bottom: 0px;
            background: transparent;
            font-weight: 650;
            color: #122d48;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 0px;
            top: -2px;
            padding: 0 2px;
            color: #122d48;
            background: transparent;
        }
        QGroupBox#sourceSection, QGroupBox#outputSection, QGroupBox#runSection {
            margin-top: 14px;
            padding-top: 10px;
            background: transparent;
            border: none;
        }
        QGroupBox#formatSection, QGroupBox#saveSection {
            margin-top: 8px;
            padding-top: 8px;
            padding-bottom: 2px;
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        QGroupBox#sourceSection::title, QGroupBox#outputSection::title, QGroupBox#runSection::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 0px;
            top: -2px;
            padding: 0 2px;
            font-size: 16px;
            font-weight: 750;
            color: #0f2942;
            background: transparent;
        }
        QGroupBox#formatSection::title, QGroupBox#saveSection::title {
            font-size: 13px;
            font-weight: 650;
            color: #405f80;
            background: transparent;
        }
        QFrame#sectionDivider {
            background: #cadfd8;
            border: none;
        }
        QFrame#mixedUrlAlert {
            background: #ffffff;
            border: 1px solid #d6e0ec;
            border-radius: 10px;
        }
        QFrame#mixedUrlOverlay {
            background: transparent;
            border: none;
        }
        QLabel#mixedUrlAlertTitle {
            color: #1e3651;
            font-weight: 700;
            background: transparent;
        }
        QLabel#readySummaryLine {
            color: #334d69;
            font-size: 12px;
            font-weight: 600;
            padding: 1px 2px 0 2px;
        }
        QFrame#metricsStrip {
            background: transparent;
            border: none;
            border-radius: 0px;
            padding: 0px;
        }
        QLabel#metricInline {
            color: #1f3650;
            font-weight: 700;
        }
        QLabel#metricInlineItem {
            color: #2c4866;
            font-weight: 600;
        }
        QFrame#downloadResultCard[state="info"] {
            background: #f7fafd;
            border: 1px solid #c7ddd7;
            border-radius: 10px;
            padding: 4px 0px;
        }
        QFrame#downloadResultCard[state="latest"] {
            background: #ecf8f0;
            border: 1px solid #c4dccd;
            border-radius: 10px;
            padding: 4px 0px;
        }
        QLabel#downloadResultTitle {
            font-weight: 700;
        }
        QFrame#downloadResultCard[state="info"] QLabel#downloadResultTitle {
            color: #213a56;
        }
        QFrame#downloadResultCard[state="latest"] QLabel#downloadResultTitle {
            color: #21533b;
        }
        QLabel#downloadResultPath {
            color: #264360;
            padding-right: 4px;
        }
        QProgressBar {
            background: #e4f3ee;
            border: 1px solid #bdd9d2;
            border-radius: 5px;
            padding: 1px;
            min-height: 12px;
            max-height: 12px;
        }
        QProgressBar::chunk {
            border-radius: 4px;
            margin: 0px;
            background: #0D9F8A;
        }
        QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
            background: #ffffff;
            border: 1px solid #bccce0;
            border-radius: 8px;
            padding: 4px 8px;
            color: #1d3650;
            min-height: 28px;
        }
        QComboBox {
            padding: 5px 9px;
            padding-right: 34px;
            selection-background-color: #d9efe9;
            selection-color: #1d3650;
        }
        QLineEdit:read-only {
            background: #f6f9fd;
            color: #2f4a66;
        }
        QLineEdit:disabled, QPlainTextEdit:disabled, QListWidget:disabled, QComboBox:disabled {
            background: #edf1f6;
            border: 1px solid #d3dce8;
            color: #95a4b8;
        }
        QLineEdit:hover, QPlainTextEdit:hover, QListWidget:hover, QComboBox:hover {
            border: 1px solid #90bfb6;
            background: #ffffff;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QComboBox:focus {
            border: 1px solid #2f9d8f;
            background: #ffffff;
        }
        QComboBox::drop-down {
            width: 30px;
            border: none;
            border-left: 1px solid #c6ddd7;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
            background: #f6f9fd;
            subcontrol-position: top right;
            subcontrol-origin: padding;
        }
        QComboBox::down-arrow {
            image: url("__combo_arrow_icon__");
            width: 10px;
            height: 6px;
        }
        QComboBox:disabled {
            background: #edf1f6;
            border: 1px solid #d3dce8;
            color: #95a4b8;
        }
        QComboBox::drop-down:disabled {
            background: #e7f2ee;
            border-left: 1px solid #c5dbd5;
        }
        QListView#nativeComboView {
            background: #ffffff;
            border: 1px solid #bdd9d2;
            border-radius: 8px;
            padding: 4px;
            outline: 0;
            margin: 0px;
        }
        QListView#nativeComboView::item {
            min-height: 28px;
            padding: 5px 9px;
            border-radius: 6px;
            color: #1d3650;
        }
        QListView#nativeComboView::item:hover {
            background: #eaf5f1;
            color: #1f3550;
        }
        QListView#nativeComboView::item:selected {
            background: #d7eee8;
            color: #1d3654;
        }
        QListView#nativeComboView QScrollBar:vertical {
            background: #f0f8f5;
            width: 19px;
            margin: 0px;
            border: none;
            border-left: 1px solid #c4ddd7;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
        }
        QListView#nativeComboView QScrollBar::handle:vertical {
            background: #b8d9d2;
            min-height: 20px;
            margin: 2px;
            border-radius: 6px;
        }
        QListView#nativeComboView QScrollBar::handle:vertical:hover {
            background: #9fcac0;
        }
        QListView#nativeComboView QScrollBar::sub-line:vertical,
        QListView#nativeComboView QScrollBar::add-line:vertical {
            height: 18px;
            background: #e7f2ee;
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
            background: #dcece7;
        }
        QListView#nativeComboView QScrollBar::sub-line:vertical:disabled,
        QListView#nativeComboView QScrollBar::add-line:vertical:disabled {
            background: #edf7f4;
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
            background: #f0f8f5;
            color: #1d6457;
            border-radius: 8px;
            padding: 3px 10px;
            border: 1px solid #aed4cc;
            min-height: 28px;
            font-weight: 650;
        }
        QPushButton:hover {
            background: #e7f4ef;
            border: 1px solid #91c1b8;
            color: #1b5d51;
        }
        QPushButton:pressed {
            background: #e2f1ec;
            border: 1px solid #84b8ad;
            color: #1a574c;
        }
        QPushButton:disabled {
            background: #eff2f7;
            color: #9aa8ba;
            border: 1px solid #d6deea;
        }
        QPushButton:checked {
            background: #d9efe9;
            border: 1px solid #9ecfc5;
            color: #16594d;
        }
        QPushButton#primaryActionButton {
            background: #0D9F8A;
            border: 1px solid #0D9F8A;
            color: #ffffff;
            font-weight: 700;
            padding: 4px 14px;
            min-height: 32px;
        }
        QPushButton#primaryActionButton:hover {
            background: #0B8C7A;
            border: 1px solid #0B8C7A;
        }
        QPushButton#primaryActionButton:pressed {
            background: #097968;
            border: 1px solid #097968;
        }
        QPushButton#primaryActionButton:disabled {
            background: #b4d9d1;
            color: #e4f3ee;
            border: 1px solid #b4d9d1;
        }
        QPushButton#ghostButton {
            background: #ffffff;
            border: 1px solid #b6d8d1;
            border-radius: 8px;
            color: #1f7568;
            padding: 2px 10px;
            min-height: 28px;
        }
        QPushButton#ghostButton:hover {
            background: #ebf7f3;
            border: 1px solid #94c5bb;
            color: #1d6d61;
        }
        QPushButton#ghostButton:pressed {
            background: #e5f4ef;
            border: 1px solid #87bcb1;
        }
        QPushButton#ghostButton:disabled {
            background: #eff2f7;
            color: #9aa8ba;
            border: 1px solid #d6deea;
        }
        QCheckBox {
            color: #2b5c53;
            spacing: 8px;
        }
        QRadioButton {
            color: #1e5048;
            spacing: 8px;
        }
        QCheckBox:hover, QRadioButton:hover {
            color: #25675e;
        }
        QCheckBox:disabled, QRadioButton:disabled {
            color: #95a3b7;
        }
        QCheckBox::indicator, QRadioButton::indicator {
            width: 16px;
            height: 16px;
            background: #ffffff;
            border: 1px solid #9fbfb8;
        }
        QCheckBox::indicator {
            border-radius: 4px;
        }
        QRadioButton::indicator {
            border-radius: 8px;
        }
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {
            border: 1px solid #86b8ae;
            background: #f5fbf9;
        }
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background: #0D9F8A;
            border: 1px solid #0D9F8A;
        }
        QCheckBox::indicator:pressed, QRadioButton::indicator:pressed {
            background: #0A836F;
            border: 1px solid #0A836F;
        }
        QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
            border: 1px solid #b4c9c4;
            background: #e7f2ee;
        }
        QCheckBox::indicator:checked:disabled, QRadioButton::indicator:checked:disabled {
            background: #bfd5cf;
            border: 1px solid #a9c2bc;
        }
        QListWidget::item {
            padding: 4px 8px;
            border-radius: 6px;
        }
        QListWidget::item:hover {
            background: #e7f4ef;
        }
        QListWidget::item:selected {
            background: #d9efe9;
            color: #1c5b50;
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
            background: #e8f5f0;
            color: #203149;
        }
        QTabBar#topPanelTabs::tab:selected {
            background: #eaf5f1;
            color: #1f3550;
            border: 1px solid #b8d8d1;
            border-bottom: 2px solid #0D9F8A;
            font-weight: 700;
        }
        QTabBar#topPanelTabs::tab:focus {
            border: 1px solid #84bfb3;
            border-bottom: 2px solid #0D9F8A;
        }
        QTabBar#topPanelTabs QToolButton {
            border-radius: 8px;
            padding: 0 6px;
            min-height: 28px;
        }
    """
    return style_sheet.replace("__combo_arrow_icon__", combo_arrow_path)
