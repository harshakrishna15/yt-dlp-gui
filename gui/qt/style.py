from __future__ import annotations


def build_stylesheet(combo_arrow_path: str) -> str:
    style_sheet = """
        QMainWindow, QWidget#appRoot {
            background: #f1ede5;
        }
        QWidget {
            color: #26384f;
            font-size: 13px;
        }
        QLabel, QCheckBox, QRadioButton {
            background: transparent;
        }
        #titleLabel {
            font-size: 32px;
            font-weight: 700;
            color: #4f7fda;
        }
        #subtleLabel {
            color: #6f839e;
        }
        #statusLine {
            color: #5a7394;
        }
        QGroupBox {
            border: 1px solid #d4ccbe;
            border-top: 1px solid #e4ddcf;
            border-bottom: 1px solid #c8bfaf;
            border-radius: 12px;
            margin-top: 18px;
            padding-top: 14px;
            padding-bottom: 8px;
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f9f6ef,
                stop: 1 #f3eee5
            );
            font-weight: 700;
            color: #27425f;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            top: -1px;
            padding: 0 5px;
            color: #24415f;
            background: #f1ede5;
            border-radius: 6px;
        }
        QGroupBox#sourceSection, QGroupBox#outputSection, QGroupBox#runSection {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8f4ec,
                stop: 1 #f1ece3
            );
        }
        QGroupBox#formatSection, QGroupBox#saveSection {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #fcf9f3,
                stop: 1 #f6f1e8
            );
            border: 1px solid #d8cfbf;
            border-top: 1px solid #e7dfd1;
            border-bottom: 1px solid #cac0af;
        }
        QGroupBox#sourceSection::title, QGroupBox#outputSection::title, QGroupBox#runSection::title {
            background: #f2ede5;
        }
        QGroupBox#formatSection::title, QGroupBox#saveSection::title {
            background: #f8f4ec;
        }
        QFrame#metricsStrip {
            background: #f4efe6;
            border: 1px solid #d6cdbe;
            border-radius: 10px;
            padding: 8px 10px;
        }
        QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
            background: #fcfaf6;
            border: 1px solid #c9c0b3;
            border-top: 1px solid #d8d0c3;
            border-bottom: 1px solid #bbb2a5;
            border-radius: 10px;
            padding: 7px 10px;
            min-height: 38px;
        }
        QComboBox {
            padding: 7px 12px;
            padding-right: 38px;
            selection-background-color: #d7e3f8;
            selection-color: #26384f;
        }
        QLineEdit:read-only {
            background: #fcfaf6;
            color: #41556f;
        }
        QLineEdit:hover, QPlainTextEdit:hover, QListWidget:hover, QComboBox:hover {
            border: 1px solid #a4b3ce;
            border-bottom: 1px solid #91a3c3;
            background: #fefcf9;
        }
        QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QComboBox:focus {
            border: 1px solid #7f9dcf;
            border-bottom: 1px solid #6c89b8;
            background: #ffffff;
        }
        QComboBox::drop-down {
            width: 30px;
            border: none;
            border-left: 1px solid #d6cdbd;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8f4eb,
                stop: 1 #f0ebdf
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
            background: #ece8e0;
            border: 1px solid #d7d2c8;
            color: #9ea5b1;
        }
        QComboBox::drop-down:disabled {
            background: #e4dfd6;
            border-left: 1px solid #d1ccbf;
        }
        QListView#nativeComboView {
            background: #fcfaf6;
            border: 1px solid #cec6b9;
            border-radius: 10px;
            padding: 4px;
            outline: 0;
            margin: 0px;
        }
        QListView#nativeComboView::item {
            min-height: 28px;
            padding: 5px 9px;
            border-radius: 8px;
            color: #26384f;
        }
        QListView#nativeComboView::item:hover {
            background: #e8effb;
            color: #20344f;
        }
        QListView#nativeComboView::item:selected {
            background: #d7e3f8;
            color: #1f3556;
        }
        QPushButton {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f3f7ff,
                stop: 1 #dfe8f8
            );
            color: #2c4569;
            border-radius: 10px;
            padding: 5px 14px;
            border: 1px solid #b9c7de;
            border-top: 1px solid #cbd8eb;
            border-bottom: 1px solid #9db0cf;
            min-height: 38px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: qlineargradient(
                x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8fbff,
                stop: 1 #e8f0ff
            );
            border: 1px solid #a8b8d3;
            border-bottom: 1px solid #8fa4c8;
        }
        QPushButton:pressed {
            background: #d8e4fb;
            border: 1px solid #8ea4c8;
            border-top: 1px solid #8398ba;
            border-bottom: 1px solid #9aafd2;
        }
        QPushButton:disabled {
            background: #ece8e0;
            color: #9ea5b1;
            border: 1px solid #d7d2c8;
        }
        QPushButton:checked {
            background: #426db8;
            border: 1px solid #365890;
            color: #ffffff;
        }
        QCheckBox {
            color: #526b89;
            spacing: 8px;
        }
        QRadioButton {
            color: #26384f;
            spacing: 8px;
        }
        QCheckBox:hover, QRadioButton:hover {
            color: #2f4f7f;
        }
        QCheckBox:disabled, QRadioButton:disabled {
            color: #93a2b6;
        }
        QCheckBox::indicator, QRadioButton::indicator {
            width: 16px;
            height: 16px;
            background: #fcfaf6;
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
            background: #426db8;
            border: 1px solid #365890;
        }
        QCheckBox::indicator:pressed, QRadioButton::indicator:pressed {
            background: #2f568f;
            border: 1px solid #2a4b7b;
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
            background: #e8edf6;
        }
        QListWidget::item:selected {
            background: #d8e4f7;
            color: #243d5c;
        }
        QListView#topPanelSelectorView {
            background: #fcfaf6;
            border: 1px solid #cec6b9;
            border-radius: 10px;
            outline: 0;
            margin: 0px;
            padding: 0px;
            selection-background-color: #dbe5f7;
            selection-color: #26384f;
        }
        QListView#topPanelSelectorView::item {
            min-height: 26px;
            padding: 4px 10px;
            border-radius: 8px;
        }
        QListView#topPanelSelectorView::item:hover {
            background: #dbe5f7;
            color: #26384f;
        }
        QListView#topPanelSelectorView::item:selected {
            background: #cddcf4;
            color: #26384f;
        }
    """
    return style_sheet.replace("__combo_arrow_icon__", combo_arrow_path)
