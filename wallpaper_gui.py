#!/usr/bin/env python3

import sys
import os
import glob
import json
import subprocess
import shutil
import re
import pathlib
import logging
import argparse

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QCheckBox, QSlider, QComboBox,
                             QStackedWidget, QListWidget, QListWidgetItem, QSystemTrayIcon,
                             QMenu, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
                             QStyledItemDelegate, QStyle, QStyleOptionSlider, QFileDialog)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QObject, QTimer, QRect, QPropertyAnimation, QEasingCurve, QVariant, QUrl
from PyQt6.QtGui import QFont, QIcon, QPixmap, QImage, QAction, QColor, QPainter, QDesktopServices
from process_manager import WallpaperProcessManager

CONFIG_FILE = pathlib.Path(os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))) / "linux-wallpaperengine-gui" / "wpe_gui_config.json"
LOCALE_DIR = (pathlib.Path(__file__).parent / "locales").absolute()

MACOS_DARK = """
QMainWindow { background-color: #1E1E1E; }
QWidget { color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Helvetica, sans-serif; font-size: 13px; }
#NavContainer { background-color: #262626; border-bottom: 1px solid #3A3A3A; }
QListWidget#Sidebar { background-color: transparent; border: none; outline: none; font-size: 13px; font-weight: 500; }
QListWidget#Sidebar::item { height: 32px; padding: 0 15px; margin: 9px 5px; border-radius: 6px; color: #9A9A9A; }
QListWidget#Sidebar::item:selected { background-color: #3A3A3A; color: #FFFFFF; }
QListWidget#Sidebar::item:hover:!selected { background-color: #2F2F2F; color: #FFFFFF; }
QFrame.Card { background-color: #2D2D2D; border: 1px solid #3A3A3A; border-radius: 10px; }
QLabel.CardTitle { font-weight: 600; font-size: 15px; color: #FFFFFF; margin-bottom: 8px; }
QLineEdit, QComboBox { background-color: #000000; border: 1px solid #3A3A3A; border-radius: 6px; padding: 4px 8px; color: #FFFFFF; selection-background-color: #0A84FF; min-height: 22px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #0A84FF; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #1E1E1E; border: 1px solid #3A3A3A; selection-background-color: #0A84FF; selection-color: #FFFFFF; color: #FFFFFF; outline: none; }
QPushButton { background-color: #0A84FF; color: white; border: none; border-radius: 3px; padding: 6px 16px; font-weight: 650; font-size: 13px; min-height: 20px; }
QPushButton:hover { background-color: #03447b; }
QPushButton:pressed { background-color: #0062CC; }
QPushButton#SecondaryButton { background-color: #3A3A3A; border: 1px solid #3A3A3A; color: #FFFFFF; }
QPushButton#SecondaryButton:hover { background-color: #222222; }
QPushButton#DangerButton { background-color: #FF453A; }
QPushButton#DangerButton:hover { background-color: #D0342C; }
QCheckBox { spacing: 8px; color: #FFFFFF; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #666666; background: #2D2D2D; }
QCheckBox::indicator:checked { background: #0A84FF; border-color: #0A84FF; }
QSlider::groove:horizontal { border: 1px solid #3A3A3A; height: 5px; background: #3f7fcf; margin: 2px 0; border-radius: 2px; }
QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #5c5c5c; width: 18px; height: 18px; margin: -8px 0; border-radius: 9px; }
QListWidget#WallpaperGrid { background-color: transparent; border: none; outline: none; padding: 0px 0px 0px 0px; }
QListWidget#WallpaperGrid::item { background-color: #111111; border: 1px solid #3A3A3A; border-radius: 3px; margin: 15px; color: #FFFFFF; padding: 5px; }
QListWidget#WallpaperGrid::item:selected { background-color: #3A3A3A; border: 2px solid #0A84FF; color: #FFFFFF; }
QListWidget#WallpaperGrid::item:hover { background-color: #373737; border: 1px solid #4A4A4A; }
QScrollBar:vertical { border: none; background: transparent; width: 10px; margin: 0px; }
QScrollBar::handle:vertical { background: rgba(60, 150, 245, 0.75); min-height: 180px; border-radius: 5px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.2); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical { background: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QLabel#PreviewBox { background-color: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 16px; color: #666666; }
"""

class Worker(QObject):
    finished = pyqtSignal(object)
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    def run(self):
        result = self.func(*self.args, **self.kwargs)
        self.finished.emit(result)

class I18n:
    def __init__(self):
        self.locale_data = {}
        self.current_code = "en"
        self.available_languages = {
            "en": "English", "ru": "Русский", "de": "Deutsch",
            "uk": "Українська", "es": "Español", "fr": "Français"
        }
    def load(self, code):
        try:
            with open(os.path.join(LOCALE_DIR, f"{code}.json"), 'r', encoding='utf-8') as f:
                self.locale_data = json.load(f)
            self.current_code = code
            return True
        except: return False
    def get(self, key, **kwargs):
        text = self.locale_data.get(key, key)
        if kwargs: return text.format(**kwargs)
        return text

class WallpaperDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scales = {}
        self.current_scales = {}
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animations)
        self.timer.start(10)

    def update_animations(self):
        changed = False
        step = 0.02
        for index_ptr, target in self.scales.items():
            curr = self.current_scales.get(index_ptr, 1.0)
            if abs(curr - target) > 0.001:
                if curr < target:
                    self.current_scales[index_ptr] = min(curr + step, target)
                else:
                    self.current_scales[index_ptr] = max(curr - step, target)
                changed = True

        if changed and self.parent():
            self.parent().viewport().update()

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)


        idx_id = index.row()


        is_hovered = option.state & QStyle.StateFlag.State_MouseOver
        self.scales[idx_id] = 1.15 if is_hovered else 1.0


        scale = self.current_scales.get(idx_id, 1.0)

        if scale > 1.0:
            painter.translate(option.rect.center())
            painter.scale(scale, scale)
            painter.translate(-option.rect.center())


            if is_hovered:
                shadow_color = QColor(0, 0, 0, 0)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(shadow_color)
                painter.drawRoundedRect(option.rect.adjusted(2, 2, 2, 2), 5, 5)

        super().paint(painter, option, index)
        painter.restore()

class WallpaperChangeHandler(FileSystemEventHandler):
    def __init__(self, signal):
        self.signal = signal

    def on_any_event(self, event):
        if event.is_directory:
            return
        # Trigger update on file changes (creation, deletion, modification)
        self.signal.emit()

class LibraryWatcher(QObject):
    # Signal to notify the app that the library needs refreshing (debounced)
    library_changed = pyqtSignal()
    # Internal signal from worker thread
    _raw_change = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.observer = Observer()
        self.handler = WallpaperChangeHandler(self._raw_change)
        self.watched_paths = set()

        # Debounce timer
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(2000)  # Wait 2 seconds after last event
        self.timer.timeout.connect(self.library_changed.emit)

        self._raw_change.connect(self.on_raw_change)

    def on_raw_change(self):
        # Restart timer to debounce
        self.timer.start()

    def update_watches(self, directories):
        # efficiently update watches
        new_paths = set(directories)
        if new_paths == self.watched_paths:
            return

        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

        self.observer = Observer()
        self.watched_paths = new_paths

        for d in directories:
            if os.path.isdir(d):
                try:
                    self.observer.schedule(self.handler, d, recursive=True)
                except Exception as e:
                    print(f"Failed to watch {d}: {e}")

        try:
            self.observer.start()
        except Exception as e:
            print(f"Failed to start observer: {e}")

    def stop(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()


class ClickableSlider(QSlider):

    def mousePressEvent(self, signal):

        if signal.button() == Qt.MouseButton.LeftButton:
            offset = 5
            value = QStyle.sliderValueFromPosition(self.minimum() - offset, self.maximum() + offset,
                                                   signal.pos().x(), self.width())
            self.setValue(value)

        super().mousePressEvent(signal)

class WallpaperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.i18n = I18n()
        self.translatable_labels = []
        self.properties_data = {}
        self.load_config_data()
        self.i18n.load(self.config.get("current_language", "en"))
        self._ = self.i18n.get
        self.setWindowTitle(f"{self._('app_title')} [build: multi-monitor-1]")
        self.setMinimumSize(920, 960)
        self.resize(920, 980)
        # screen_name -> {"id": str, "title": str}
        self.monitor_assignments = {}
        self.monitor_row_widgets = {}
        self.selected_wallpaper_meta = None  # {"id", "title", "path", ...}
        self.setup_ui()
        self.apply_theme()
        self.apply_config_ui()
        self.setup_tray()
        self.start_scan()
        self.stack.setCurrentIndex(1)
        self.nav_bar.setCurrentRow(1)
        self.rebuild_monitor_panel()
        self.update_texts()

        # Setup file watcher for auto-refresh
        self.watcher = LibraryWatcher()
        self.watcher.library_changed.connect(self.on_library_changed_auto)

        QTimer.singleShot(500, self.restore_last_wallpaper)

        self.wallpaper_proc_manager = WallpaperProcessManager()
        self.wallpaper_watchdog = QTimer()
        self.wallpaper_watchdog.setInterval(1000)
        self.wallpaper_watchdog.timeout.connect(self.check_wallpaper_process)
        self.wallpaper_watchdog.start()

    def on_library_changed_auto(self):
        # Trigger a scan if one isn't already running
        if self.btn_scan.isEnabled():
            self.start_scan()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.nav_container = QFrame()
        self.nav_container.setObjectName("NavContainer")
        self.nav_container.setFixedHeight(50)
        nav_layout = QHBoxLayout(self.nav_container)
        nav_layout.setContentsMargins(245, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.nav_bar = QListWidget()
        self.nav_bar.setObjectName("Sidebar")
        self.nav_bar.setFlow(QListWidget.Flow.LeftToRight)
        self.nav_bar.setFixedWidth(600)
        self.nav_bar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_bar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_bar.addItems(["Control", "Library"])
        for i in range(self.nav_bar.count()):
            item = self.nav_bar.item(i)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(QSize(200, 32))

        self.nav_bar.currentRowChanged.connect(self.switch_page)

        nav_layout.addStretch()
        nav_layout.addWidget(self.nav_bar)
        nav_layout.addStretch()
        nav_layout.addSpacing(250)

        main_layout.addWidget(self.nav_container)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        self.page_control = QWidget()
        self.setup_control_page()
        self.stack.addWidget(self.page_control)
        self.page_library = QWidget()
        self.setup_library_page()
        self.stack.addWidget(self.page_library)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        self.status_bar.hide()

    def setup_control_page(self):
        layout = QVBoxLayout(self.page_control)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        card_main = self.create_card(layout, "main_controls_frame")
        self.wp_id_input = QLineEdit()
        self.wp_id_input.setPlaceholderText("Select a wallpaper in Library, or paste an ID/path")
        self.wp_id_input.textChanged.connect(self.on_wallpaper_id_changed)
        self.lbl_selected_title = QLabel("")
        self.lbl_selected_title.setStyleSheet("color: #A5A5A5; font-size: 12px;")
        self.lbl_selected_title.setWordWrap(True)
        self.add_form_row(card_main, "wallpaper_id_path_label", self.wp_id_input)
        card_main.layout().addWidget(self.lbl_selected_title)

        # Multi-monitor assignment panel (replaces free-text screen field)
        card_monitors = self.create_card(layout, "monitors_frame")
        self.monitor_hint = QLabel()
        self.monitor_hint.setWordWrap(True)
        self.monitor_hint.setStyleSheet("color: #A5A5A5; font-size: 12px;")
        card_monitors.layout().addWidget(self.monitor_hint)

        self.monitor_rows_host = QWidget()
        self.monitor_rows_layout = QVBoxLayout(self.monitor_rows_host)
        self.monitor_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.monitor_rows_layout.setSpacing(8)
        card_monitors.layout().addWidget(self.monitor_rows_host)

        mon_btn_row = QHBoxLayout()
        self.btn_refresh_screens = QPushButton("refresh_screens_button")
        self.btn_refresh_screens.setObjectName("SecondaryButton")
        self.btn_refresh_screens.clicked.connect(self.rebuild_monitor_panel)
        self.btn_assign_all = QPushButton("assign_all_monitors_button")
        self.btn_assign_all.setObjectName("SecondaryButton")
        self.btn_assign_all.clicked.connect(self.assign_selected_to_all_monitors)
        self.btn_clear_all = QPushButton("clear_all_monitors_button")
        self.btn_clear_all.setObjectName("SecondaryButton")
        self.btn_clear_all.clicked.connect(self.clear_all_monitor_assignments)
        mon_btn_row.addWidget(self.btn_refresh_screens)
        mon_btn_row.addWidget(self.btn_assign_all)
        mon_btn_row.addWidget(self.btn_clear_all)
        mon_btn_row.addStretch()
        card_monitors.layout().addLayout(mon_btn_row)

        # Primary target for library "Set on Target" / windowed mode (synced with Library tab combo)
        self.screen_combo = QComboBox()
        self.screen_combo.setEditable(False)
        self.screen_combo.currentIndexChanged.connect(self._on_primary_target_changed)
        self.add_form_row(card_monitors, "primary_target_label", self.screen_combo)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(20)
        layout.addLayout(h_layout)
        card_audio = self.create_card(h_layout, "audio_frame")
        self.chk_silent = QCheckBox("silent_checkbox")
        self.chk_silent.clicked.connect(self.run_wallpaper)
        self.slider_volume = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(15)
        self.slider_volume.sliderReleased.connect(self.run_wallpaper)
        self.chk_no_automute = QCheckBox("no_automute_checkbox")
        self.chk_no_automute.clicked.connect(self.run_wallpaper)
        self.chk_no_proc = QCheckBox("no_audio_processing_checkbox")
        self.chk_no_proc.clicked.connect(self.run_wallpaper)
        l = card_audio.layout()
        l.addWidget(self.chk_silent)
        l.addWidget(self.create_label("volume_label"))
        l.addWidget(self.slider_volume)
        l.addWidget(self.chk_no_automute)
        l.addWidget(self.chk_no_proc)
        card_perf = self.create_card(h_layout, "perf_frame")
        self.slider_fps = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider_fps.setRange(10, 144)
        self.slider_fps.setValue(30)
        self.slider_fps.sliderReleased.connect(self.run_wallpaper)
        self.chk_mouse = QCheckBox("disable_mouse_checkbox")
        self.chk_mouse.clicked.connect(self.run_wallpaper)
        self.chk_parallax = QCheckBox("disable_parallax_checkbox")
        self.chk_parallax.clicked.connect(self.run_wallpaper)
        self.chk_fs_pause = QCheckBox("no_fullscreen_pause_checkbox")
        self.chk_fs_pause.clicked.connect(self.run_wallpaper)
        l = card_perf.layout()
        l.addWidget(self.create_label("fps_label"))
        l.addWidget(self.slider_fps)
        l.addWidget(self.chk_mouse)
        l.addWidget(self.chk_parallax)
        l.addWidget(self.chk_fs_pause)
        card_adv = self.create_card(layout, "adv_frame")
        self.combo_scaling = QComboBox()
        self.combo_scaling.addItems(['default', 'stretch', 'fit', 'fill'])
        if "scale" in self.config:
            self.combo_scaling.setCurrentText(self.config["scale"])
        self.combo_scaling.currentTextChanged.connect(self.run_wallpaper)
        self.combo_clamp = QComboBox()
        self.combo_clamp.addItems(['clamp', 'border', 'repeat'])
        if "clamp" in self.config:
            self.combo_clamp.setCurrentText(self.config["clamp"])
        self.combo_clamp.currentTextChanged.connect(self.run_wallpaper)
        self.chk_windowed_mode = QCheckBox("windowed_mode_checkbox")
        self.chk_windowed_mode.clicked.connect(self.run_wallpaper)
        self.input_custom_args = QLineEdit()
        self.input_custom_args.setPlaceholderText("--window 0x0x1280x720")

        self.combo_lang = QComboBox()
        self.combo_lang.currentTextChanged.connect(self.change_lang)

        self.add_form_row(card_adv, "language_label", self.combo_lang)
        self.add_form_row(card_adv, "scaling_label", self.combo_scaling)
        self.add_form_row(card_adv, "clamp_label", self.combo_clamp)
        card_adv.layout().addWidget(self.chk_windowed_mode)

        self.lbl_kwin_hint = QLabel("kwin_hint")
        self.lbl_kwin_hint.setWordWrap(True)
        self.lbl_kwin_hint.setStyleSheet("color: #888; font-size: 11px; margin-left: 24px; margin-bottom: 8px;")
        self.lbl_kwin_hint.setVisible(False)
        self.chk_windowed_mode.toggled.connect(self.lbl_kwin_hint.setVisible)
        card_adv.layout().addWidget(self.lbl_kwin_hint)

        props_controls = QHBoxLayout()
        props_controls.setSpacing(10)
        props_controls.setContentsMargins(0, 0, 0, 0)
        self.properties_type = QLabel()
        self.properties_type.setMinimumWidth(120)
        self.properties_type.setStyleSheet("color: #A5A5A5;")
        self.properties_combo = QComboBox()
        self.properties_combo.setEditable(False)
        self.properties_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.properties_combo.setMinimumWidth(280)
        self.properties_combo.addItem(self._("properties_select_placeholder"), None)
        self.properties_combo.currentIndexChanged.connect(self.on_property_selected)
        self.properties_value = QLineEdit()
        self.properties_value.setPlaceholderText(self._("property_value_placeholder"))
        self.properties_value.editingFinished.connect(self.apply_property_value)
        self.properties_value.setMinimumWidth(240)
        self.properties_value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_load_props = QPushButton("load_properties_button")
        self.btn_load_props.clicked.connect(self.load_properties)
        self.btn_apply_prop = QPushButton("apply_property_button")
        self.btn_apply_prop.clicked.connect(self.apply_property_value)
        for btn in (self.btn_load_props, self.btn_apply_prop):
            btn.setMinimumWidth(120)
            btn.setMinimumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        props_header = QHBoxLayout()
        props_label = self.create_label("set_property_label")
        props_header.addWidget(props_label)
        props_header.addStretch()
        props_header.addWidget(self.btn_load_props)
        props_header.addWidget(self.btn_apply_prop)
        card_adv.layout().addLayout(props_header)

        props_controls.addWidget(self.properties_combo)
        props_controls.addWidget(self.properties_type)
        props_controls.addWidget(self.properties_value, 1)
        card_adv.layout().addLayout(props_controls)
        self.add_form_row(card_adv, "Custom Arguments", self.input_custom_args)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        layout.addLayout(btn_layout)
        self.btn_set = QPushButton("set_wallpaper_button")
        self.btn_set.clicked.connect(self.run_wallpaper)
        self.btn_set.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set.setMinimumHeight(32)
        self.btn_show_log = QPushButton("show_log_button")
        self.btn_show_log.setObjectName("SecondaryButton")
        self.btn_show_log.clicked.connect(self.show_log_file)
        self.btn_show_log.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show_log.setMinimumHeight(32)
        self.btn_stop = QPushButton("stop_button")
        self.btn_stop.setObjectName("DangerButton")
        self.btn_stop.clicked.connect(self.stop_wallpapers)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setMinimumHeight(32)
        btn_layout.addWidget(self.btn_set)
        btn_layout.addWidget(self.btn_show_log)
        btn_layout.addWidget(self.btn_stop)
        layout.addStretch()

    def setup_library_page(self):
        layout = QVBoxLayout(self.page_library)
        layout.setContentsMargins(12, 24, 0, 0)
        layout.setSpacing(0)
        push_buttons_layout = QHBoxLayout()
        push_buttons_layout.setContentsMargins(165, 0, 0, 0)
        push_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header = QHBoxLayout()
        self.btn_scan = QPushButton("scan_local_wallpapers_button")
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_scan.setFixedSize(160, 200)
        self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        push_buttons_layout.addWidget(self.btn_scan)
        push_buttons_layout.addSpacing(25)

        # Target monitor + Set on Target (same primary target as Control tab)
        set_target_col = QWidget()
        set_target_col.setFixedWidth(180)
        set_target_layout = QVBoxLayout(set_target_col)
        set_target_layout.setContentsMargins(0, 0, 0, 0)
        set_target_layout.setSpacing(8)
        set_target_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lbl_library_target = QLabel(self._("primary_target_label"))
        self.lbl_library_target.setWordWrap(True)
        self.lbl_library_target.setStyleSheet("color: #A5A5A5; font-size: 12px;")
        set_target_layout.addWidget(self.lbl_library_target)
        self.library_screen_combo = QComboBox()
        self.library_screen_combo.setEditable(False)
        self.library_screen_combo.setMinimumHeight(28)
        self.library_screen_combo.currentIndexChanged.connect(self._on_library_target_changed)
        set_target_layout.addWidget(self.library_screen_combo)
        self.btn_set_library = QPushButton("set_on_target_button")
        self.btn_set_library.clicked.connect(self.assign_selected_to_primary_and_apply)
        self.btn_set_library.setMinimumHeight(48)
        self.btn_set_library.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_set_library.setObjectName("PrimaryButton")
        self.btn_set_library.setCursor(Qt.CursorShape.PointingHandCursor)
        set_target_layout.addWidget(self.btn_set_library)
        set_target_layout.addStretch()
        push_buttons_layout.addWidget(set_target_col)
        push_buttons_layout.addSpacing(25)

        self.btn_apply_all_library = QPushButton("apply_all_monitors_button")
        self.btn_apply_all_library.clicked.connect(self.apply_all_monitors_from_library)
        self.btn_apply_all_library.setFixedSize(160, 200)
        self.btn_apply_all_library.setObjectName("SecondaryButton")
        self.btn_apply_all_library.setCursor(Qt.CursorShape.PointingHandCursor)
        push_buttons_layout.addWidget(self.btn_apply_all_library)
        self.btn_select_folder = QPushButton("select_folder_button")
        self.btn_select_folder.clicked.connect(self.manual_scan)
        self.btn_select_folder.setFixedSize(160, 200)
        self.btn_select_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        push_buttons_layout.addSpacing(25)
        push_buttons_layout.addWidget(self.btn_select_folder)
        layout.addLayout(push_buttons_layout)
        layout.addLayout(header)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self._("search_placeholder"))
        self.search_input.textChanged.connect(self.filter_wallpapers)
        self.search_input.setFixedWidth(350)
        self.sorting_type = QComboBox()
        self.sorting_type.addItems(["Name", "Subscription Date"])
        self.sorting_type.setFixedWidth(150)
        self.sorting_type.setStyleSheet("text-align: left;")
        self.sort_reversed_state = False
        self.sorting_type.currentTextChanged.connect(self.on_sort_change)
        self.btn_reverse_sorted = QPushButton("↑")
        self.btn_reverse_sorted.setFixedSize(50, 50)
        self.btn_reverse_sorted.setStyleSheet("background-color: None; font-size: 22px;")
        self.btn_reverse_sorted.clicked.connect(self.reverse_sorted)
        search_layout = QHBoxLayout()
        search_layout.setSpacing(0)
        search_layout.setContentsMargins(64,10,0,0)
        search_layout.addWidget(self.search_input)
        search_layout.addSpacing(183)
        search_layout.addWidget(self.btn_reverse_sorted)
        search_layout.addWidget(self.sorting_type)
        search_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(search_layout)

        self.list_wallpapers = QListWidget()
        self.list_wallpapers.setMovement(QListWidget.Movement.Static)
        self.list_wallpapers.setObjectName("WallpaperGrid")
        self.list_wallpapers.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_wallpapers.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_wallpapers.setGridSize(QSize(190, 250))
        self.list_wallpapers.setSpacing(100)
        self.list_wallpapers.setWordWrap(True)
        self.list_wallpapers.setIconSize(QSize(150, 170))
        self.list_wallpapers.setItemDelegate(WallpaperDelegate(self.list_wallpapers))
        self.list_wallpapers.setMouseTracking(True)
        self.list_wallpapers.itemClicked.connect(self.on_wallpaper_selected)
        self.list_wallpapers.itemDoubleClicked.connect(self.assign_selected_to_primary_and_apply)
        self.list_wallpapers.setItemAlignment(Qt.AlignmentFlag.AlignCenter)
        wallpapers_layout = QVBoxLayout()
        wallpapers_layout.addWidget(self.list_wallpapers)
        wallpapers_layout.setContentsMargins(50,0,0,0)
        layout.addLayout(wallpapers_layout)

    def create_label(self, text_key):
        lbl = QLabel(self._(text_key))
        self.translatable_labels.append((lbl, text_key))
        return lbl

    def create_card(self, parent_layout, title_key):
        frame = QFrame()
        frame.setProperty("class", "Card")
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(12)
        lbl = self.create_label(title_key)
        lbl.setProperty("class", "CardTitle")
        vbox.addWidget(lbl)
        parent_layout.addWidget(frame)
        return frame

    def add_form_row(self, card, label_key, widget):
        h = QHBoxLayout()
        l = self.create_label(label_key)
        h.addWidget(l)
        h.addWidget(widget)
        card.layout().addLayout(h)

    def apply_theme(self):
        self.setStyleSheet(MACOS_DARK)

    def update_texts(self):
        items = ["control_tab", "local_library_tab"]
        for i, key in enumerate(items):
            self.nav_bar.item(i).setText(self._(key))

        for widget, key in self.translatable_labels:
            widget.setText(self._(key))

        self.combo_lang.blockSignals(True)
        self.combo_lang.clear()
        for code, name in self.i18n.available_languages.items():
            self.combo_lang.addItem(name, code)
        self.combo_lang.setCurrentText(self.i18n.available_languages.get(self.i18n.current_code, "English"))
        self.combo_lang.blockSignals(False)
        self.btn_set.setText(self._("apply_all_monitors_button"))
        self.btn_set_library.setText(self._("set_on_target_button"))
        if hasattr(self, "btn_apply_all_library"):
            self.btn_apply_all_library.setText(self._("apply_all_monitors_button"))
        if hasattr(self, "lbl_library_target"):
            self.lbl_library_target.setText(self._("primary_target_label"))
        self.btn_stop.setText(self._("stop_button"))
        self.btn_show_log.setText(self._("show_log_button"))
        self.btn_scan.setText(self._("scan_local_wallpapers_button"))
        self.btn_select_folder.setText(self._("select_folder_button"))
        self.chk_silent.setText(self._("silent_checkbox"))
        self.chk_no_automute.setText(self._("no_automute_checkbox"))
        self.chk_no_proc.setText(self._("no_audio_processing_checkbox"))
        self.chk_mouse.setText(self._("disable_mouse_checkbox"))
        self.chk_parallax.setText(self._("disable_parallax_checkbox"))
        self.chk_fs_pause.setText(self._("no_fullscreen_pause_checkbox"))
        self.chk_windowed_mode.setText(self._("windowed_mode_checkbox"))
        self.lbl_kwin_hint.setText(self._("kwin_hint"))
        self.btn_load_props.setText(self._("load_properties_button"))
        self.btn_apply_prop.setText(self._("apply_property_button"))
        self.properties_combo.setItemText(0, self._("properties_select_placeholder"))
        self.properties_value.setPlaceholderText(self._("property_value_placeholder"))
        self.search_input.setPlaceholderText(self._("search_placeholder"))
        if hasattr(self, "btn_refresh_screens"):
            self.btn_refresh_screens.setText(self._("refresh_screens_button"))
            self.btn_assign_all.setText(self._("assign_all_monitors_button"))
            self.btn_clear_all.setText(self._("clear_all_monitors_button"))
            self.monitor_hint.setText(self._("monitors_hint"))
        self.refresh_monitor_row_labels()

    def switch_page(self, row):
        self.stack.setCurrentIndex(row)

    def change_lang(self, text):
        code = self.combo_lang.currentData()
        if self.i18n.load(code):
            self.update_texts()
            self.config["current_language"] = code
            self.save_config()

    def start_scan(self):
        self.status_bar.showMessage(self._("status_searching_local"))
        self.btn_scan.setEnabled(False)
        self.search_input.clear()
        self.thread = QThread()
        self.worker = Worker(self.scan_logic)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.scan_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def manual_scan(self):
        directory = QFileDialog.getExistingDirectory(self, self._("select_folder_button"))
        if directory:
            self.status_bar.showMessage(self._("status_searching_local"))
            self.btn_scan.setEnabled(False)
            self.search_input.clear()
            self.thread = QThread()
            self.worker = Worker(self.scan_logic, manual_dir=directory)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.scan_finished)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()

    def get_steam_workshop_dirs(self):
        workshop_dirs = set()
        base_paths = [
            os.path.expanduser("~/.local/share/Steam"),
            os.path.expanduser("~/.steam/steam"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.local/share/Steam"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.data/Steam"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.steam/steam"),
        ]

        # Library folders from VDF
        lib_configs = [
            os.path.expanduser("~/.local/share/Steam/steamapps/libraryfolders.vdf"),
            os.path.expanduser("~/.steam/steam/steamapps/libraryfolders.vdf"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/libraryfolders.vdf")
        ]

        for cfg in lib_configs:
            if os.path.isfile(cfg):
                try:
                    with open(cfg, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Simple regex to find paths in VDF
                        paths = re.findall(r'"path"\s+"([^"]+)"', content)
                        for p in paths:
                            if os.path.isdir(p):
                                base_paths.append(p)
                except: pass

        # Deduplicate
        base_paths = list(set(base_paths))

        # Add Snap paths
        base_paths.extend(glob.glob(os.path.expanduser("~/snap/steam/*/.local/share/Steam")))
        base_paths.extend(glob.glob(os.path.expanduser("~/snap/steam/*/.steam/steam")))

        for base in base_paths:
            if not os.path.exists(base): continue

            # Standard workshop path for Wallpaper Engine (ID: 431960)
            p_workshop = os.path.join(base, "steamapps/workshop/content/431960")
            if os.path.isdir(p_workshop):
                workshop_dirs.add(p_workshop)

            # Default assets
            p_presets = os.path.join(base, "steamapps/common/wallpaper_engine/assets/presets")
            if os.path.isdir(p_presets):
                workshop_dirs.add(p_presets)

        # Fallback deep scan if nothing found
        if not workshop_dirs:
            try:
                # Limit search to home directory to avoid scanning whole system
                search_roots = [os.path.expanduser("~")]
                cmd = ["find"] + search_roots + ["-maxdepth", "6", "-type", "d", "-name", "431960"]
                result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if os.path.isdir(line):
                            workshop_dirs.add(line)
            except Exception as e:
                logging.error(f"Deep scan error: {e}")

        return workshop_dirs

    def scan_logic(self, manual_dir=None):
        workshop_dirs = self.get_steam_workshop_dirs()
        is_append = manual_dir is not None
        if manual_dir:
            workshop_dirs.add(manual_dir)

        wallpapers = []
        seen = set()

        for w_dir in workshop_dirs:
            try:
                proj_self = os.path.join(w_dir, "project.json")
                if os.path.isfile(proj_self):
                    try:
                        with open(proj_self, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            item_id = os.path.basename(w_dir)
                            wallpapers.append({
                                "title": data.get("title", "Untitled"),
                                "id": item_id,
                                "path": w_dir,
                                "preview": data.get("preview")
                            })
                            seen.add(item_id)
                    except: pass
                for item_id in os.listdir(w_dir):
                    if item_id in seen: continue
                    path = os.path.join(w_dir, item_id)
                    proj = os.path.join(path, "project.json")
                    if os.path.isfile(proj):
                        try:
                            with open(proj, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                wallpapers.append({
                                    "title": data.get("title", "Untitled"),
                                    "id": item_id,
                                    "path": path,
                                    "preview": data.get("preview")
                                })
                                seen.add(item_id)
                        except: pass
            except: pass

        return wallpapers, is_append, list(workshop_dirs)

    def scan_finished(self, result):
        wallpapers, is_append, scanned_dirs = result
        if hasattr(self, 'watcher'):
            self.watcher.update_watches(scanned_dirs)

        if not is_append:
            self.list_wallpapers.clear()
        existing_ids = set()
        for i in range(self.list_wallpapers.count()):
            data = self.list_wallpapers.item(i).data(Qt.ItemDataRole.UserRole)
            if data: existing_ids.add(data["id"])
        new_count = 0
        self.sort_wallpapers(wallpapers)
        for w in wallpapers:
            if w["id"] in existing_ids: continue
            item = QListWidgetItem(w["title"])
            item.setSizeHint(QSize(200, 240))
            item_font = QFont()
            item_font.setPointSize(10)
            item_font.setWeight(700)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignCenter)
            item.setFont(item_font)
            item.setData(Qt.ItemDataRole.UserRole, w)

            if w.get("preview"):
                path = os.path.join(w["path"], w["preview"])
                if os.path.isfile(path):
                    pixmap = QPixmap(path)

                    icon_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)


                    rect = QRect(0, 0, 200, 200)
                    rect.moveCenter(icon_pixmap.rect().center())
                    icon_pixmap = icon_pixmap.copy(rect)

                    item.setIcon(QIcon(icon_pixmap))

            self.list_wallpapers.addItem(item)
            existing_ids.add(w["id"])
            new_count += 1
        self.btn_scan.setEnabled(True)
        if is_append:
            self.status_bar.showMessage(f"Added {new_count} new wallpapers.")
        else:
            self.status_bar.showMessage(self._("status_local_wallpapers_found").format(count=self.list_wallpapers.count()))

    def on_wallpaper_selected(self, item):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        self.selected_wallpaper_meta = data
        self.wp_id_input.blockSignals(True)
        self.wp_id_input.setText(str(data.get("id", "")))
        self.wp_id_input.blockSignals(False)
        title = data.get("title") or data.get("id") or ""
        self.lbl_selected_title.setText(self._("selected_wallpaper_label").format(title=title, id=data.get("id", "")))
        self.on_wallpaper_id_changed()
        self.status_bar.showMessage(self._("status_selected_wallpaper_id").format(id=data.get("id", "")))

    def get_current_wallpaper_selection(self):
        """Return {id, title} from the ID field / library selection."""
        wp_id = self.wp_id_input.text().strip()
        if not wp_id:
            return None
        title = wp_id
        if self.selected_wallpaper_meta and str(self.selected_wallpaper_meta.get("id")) == wp_id:
            title = self.selected_wallpaper_meta.get("title") or wp_id
        else:
            # Try to resolve title from library list
            for i in range(self.list_wallpapers.count()):
                item = self.list_wallpapers.item(i)
                data = item.data(Qt.ItemDataRole.UserRole) or {}
                if str(data.get("id")) == wp_id:
                    title = data.get("title") or wp_id
                    break
        return {"id": wp_id, "title": title}

    def _primary_target_combos(self):
        """Control + Library target combos that must stay in sync."""
        combos = []
        if hasattr(self, "screen_combo"):
            combos.append(self.screen_combo)
        if hasattr(self, "library_screen_combo"):
            combos.append(self.library_screen_combo)
        return combos

    def get_primary_target_screen(self):
        if hasattr(self, "screen_combo") and self.screen_combo.count():
            return self.screen_combo.currentText().strip()
        if hasattr(self, "library_screen_combo") and self.library_screen_combo.count():
            return self.library_screen_combo.currentText().strip()
        return ""

    def set_primary_target_screen(self, screen_name):
        """Set the primary target on every synced combo."""
        if not screen_name:
            return
        for combo in self._primary_target_combos():
            idx = combo.findText(screen_name)
            if idx < 0:
                continue
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def _on_primary_target_changed(self, *_args):
        if not hasattr(self, "screen_combo"):
            return
        self.set_primary_target_screen(self.screen_combo.currentText().strip())

    def _on_library_target_changed(self, *_args):
        if not hasattr(self, "library_screen_combo"):
            return
        self.set_primary_target_screen(self.library_screen_combo.currentText().strip())

    def _populate_primary_target_combos(self, prev_primary=""):
        """Refill Control/Library target combos from self.screens."""
        if not prev_primary:
            prev_primary = self.get_primary_target_screen()
        for combo in self._primary_target_combos():
            combo.blockSignals(True)
            combo.clear()
            for s in self.screens:
                combo.addItem(s["name"], s)
            if prev_primary:
                idx = combo.findText(prev_primary)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def rebuild_monitor_panel(self):
        """Detect screens and rebuild per-monitor assignment rows."""
        # Preserve existing assignments across rebuild
        previous = dict(self.monitor_assignments)

        # Clear rows
        while self.monitor_rows_layout.count():
            item = self.monitor_rows_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.monitor_row_widgets.clear()

        self.screens = self.detect_screens()
        self._populate_primary_target_combos()

        # Drop assignments for disconnected screens; keep the rest
        valid_names = {s["name"] for s in self.screens}
        self.monitor_assignments = {
            name: info for name, info in previous.items() if name in valid_names
        }

        for s in self.screens:
            self._add_monitor_row(s)

        self.refresh_monitor_row_labels()
        self.status_bar.showMessage(
            self._("status_screens_detected").format(count=len(self.screens))
        )

    def _add_monitor_row(self, screen):
        name = screen["name"]
        row = QFrame()
        row.setProperty("class", "Card")
        row.setStyleSheet(
            "QFrame { background-color: #222222; border: 1px solid #3A3A3A; border-radius: 8px; }"
        )
        h = QHBoxLayout(row)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)

        info = QVBoxLayout()
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("font-weight: 600; font-size: 14px;")
        res = f"{screen.get('w', '?')}×{screen.get('h', '?')}  @ {screen.get('x', '0')},{screen.get('y', '0')}"
        lbl_res = QLabel(res)
        lbl_res.setStyleSheet("color: #888888; font-size: 11px;")
        info.addWidget(lbl_name)
        info.addWidget(lbl_res)
        h.addLayout(info, 1)

        lbl_wp = QLabel(self._("monitor_unassigned"))
        lbl_wp.setWordWrap(True)
        lbl_wp.setMinimumWidth(220)
        lbl_wp.setStyleSheet("color: #CCCCCC;")
        h.addWidget(lbl_wp, 2)

        btn_assign = QPushButton(self._("assign_monitor_button"))
        btn_assign.setMinimumHeight(30)
        btn_assign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_assign.clicked.connect(lambda _=False, n=name: self.assign_selected_to_monitor(n, apply=False))

        btn_apply_one = QPushButton(self._("assign_and_apply_button"))
        btn_apply_one.setMinimumHeight(30)
        btn_apply_one.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply_one.clicked.connect(lambda _=False, n=name: self.assign_selected_to_monitor(n, apply=True))

        btn_clear = QPushButton(self._("clear_monitor_button"))
        btn_clear.setObjectName("SecondaryButton")
        btn_clear.setMinimumHeight(30)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(lambda _=False, n=name: self.clear_monitor_assignment(n))

        h.addWidget(btn_assign)
        h.addWidget(btn_apply_one)
        h.addWidget(btn_clear)

        self.monitor_rows_layout.addWidget(row)
        self.monitor_row_widgets[name] = {
            "row": row,
            "label": lbl_wp,
            "btn_assign": btn_assign,
            "btn_apply": btn_apply_one,
            "btn_clear": btn_clear,
            "screen": screen,
        }

    def refresh_monitor_row_labels(self):
        if not hasattr(self, "monitor_row_widgets"):
            return
        for name, widgets in self.monitor_row_widgets.items():
            info = self.monitor_assignments.get(name)
            if info and info.get("id"):
                title = info.get("title") or info["id"]
                widgets["label"].setText(
                    self._("monitor_assigned").format(title=title, id=info["id"])
                )
                widgets["label"].setStyleSheet("color: #FFFFFF;")
            else:
                widgets["label"].setText(self._("monitor_unassigned"))
                widgets["label"].setStyleSheet("color: #888888;")
            # refresh button captions on language change
            widgets["btn_assign"].setText(self._("assign_monitor_button"))
            widgets["btn_apply"].setText(self._("assign_and_apply_button"))
            widgets["btn_clear"].setText(self._("clear_monitor_button"))

    def assign_selected_to_monitor(self, screen_name, apply=False):
        selection = self.get_current_wallpaper_selection()
        if not selection:
            self.status_bar.showMessage(self._("status_error_empty_id"))
            return
        self.monitor_assignments[screen_name] = selection
        # Keep primary target combos in sync with last assign target
        self.set_primary_target_screen(screen_name)
        self.refresh_monitor_row_labels()
        self.save_config()
        self.status_bar.showMessage(
            self._("status_assigned_to_monitor").format(
                title=selection["title"], screen=screen_name
            )
        )
        if apply:
            self.run_wallpaper()

    def assign_selected_to_all_monitors(self):
        selection = self.get_current_wallpaper_selection()
        if not selection:
            self.status_bar.showMessage(self._("status_error_empty_id"))
            return
        if not self.screens:
            self.rebuild_monitor_panel()
        if not self.screens:
            self.status_bar.showMessage(self._("status_error_screen_not_selected"))
            return
        for s in self.screens:
            self.monitor_assignments[s["name"]] = selection
        self.refresh_monitor_row_labels()
        self.save_config()
        self.status_bar.showMessage(
            self._("status_assigned_to_all").format(title=selection["title"])
        )

    def clear_monitor_assignment(self, screen_name):
        self.monitor_assignments.pop(screen_name, None)
        self.refresh_monitor_row_labels()
        self.save_config()

    def clear_all_monitor_assignments(self):
        self.monitor_assignments.clear()
        self.refresh_monitor_row_labels()
        self.save_config()

    def _sync_library_selection_to_id(self):
        """Ensure library list selection is reflected in the wallpaper ID field."""
        item = self.list_wallpapers.currentItem()
        if item is not None:
            self.on_wallpaper_selected(item)

    def assign_selected_to_primary_and_apply(self, *_args):
        """Library 'Set on target' / double-click: assign to primary monitor, keep others, apply all."""
        self._sync_library_selection_to_id()
        screen = self.get_primary_target_screen()
        if not screen:
            self.status_bar.showMessage(self._("status_error_screen_not_selected"))
            return
        self.assign_selected_to_monitor(screen, apply=True)

    def apply_all_monitors_from_library(self, *_args):
        """Library 'Apply All Monitors': launch wallpapers for every assigned (or all) screens.

        If per-monitor assignments already exist, apply those.
        Otherwise assign the currently selected wallpaper to every detected
        monitor and apply — so the Library button does useful work without a
        prior trip to the Control tab.
        """
        self._sync_library_selection_to_id()
        active = [
            (name, info) for name, info in self.monitor_assignments.items()
            if info and info.get("id")
        ]
        if not active:
            selection = self.get_current_wallpaper_selection()
            if not selection:
                self.status_bar.showMessage(self._("status_error_empty_id"))
                return
            if not self.screens:
                self.rebuild_monitor_panel()
            if not self.screens:
                self.status_bar.showMessage(self._("status_error_screen_not_selected"))
                return
            for s in self.screens:
                self.monitor_assignments[s["name"]] = selection
            self.refresh_monitor_row_labels()
            self.save_config()
        self.run_wallpaper()

    def filter_wallpapers(self, text):
        query = text.lower()

        if query:
            self.watcher.timer.stop()

        else:
            self.watcher.timer.start()

        for i in range(self.list_wallpapers.count()):
            item = self.list_wallpapers.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            title = item.text().lower()
            wp_id = str(data.get("id", "")).lower()
            item.setHidden(query not in title and query not in wp_id)
    
    def on_sort_change(self):
        try:
            # Save sorting type to config
            self.config["sorting_type"] = self.sorting_type.currentText()
            self.save_config()

            if self.list_wallpapers:
                wallpapers = self.list_wallpapers

            if wallpapers:
                self.thread = QThread()
                self.worker = Worker(self.sort_wallpapers, wallpapers)
                self.worker.moveToThread(self.thread)
                self.thread.started.connect(self.worker.run)
                self.worker.finished.connect(self.thread.quit)
                self.thread.finished.connect(self.worker.deleteLater)
                self.watcher.library_changed.emit()
                self.thread.start()

        except FileNotFoundError:
            return 0

        except Exception as e:
            print(f"Error of type {e}")
            return 0


    def sort_wallpapers(self, wallpapers):
        try:

            if self.sorting_type.currentText() == "Name":
                if not self.sort_reversed_state:
                    wallpapers.sort(key=lambda x: x["title"].lower())
                else:
                    wallpapers.sort(key=lambda x: x["title"].lower(), reverse=True)

            elif self.sorting_type.currentText() == "Subscription Date":
                if not self.sort_reversed_state:
                    # By default needs to be reversed to get the latest subscriptions
                    wallpapers.sort(key=lambda x: pathlib.Path(x["path"]).stat().st_ctime, reverse=True)
                else:
                    wallpapers.sort(key=lambda x: pathlib.Path(x["path"]).stat().st_ctime, reverse=False)
        except FileNotFoundError:
            return 0

        except Exception as e:
            print(f"Error of type {e}")
            return 0

    def reverse_sorted(self):
        if not self.sort_reversed_state:
            self.sort_reversed_state = True
            self.btn_reverse_sorted.setText("↓")
        else:
            self.btn_reverse_sorted.setText("↑")
            self.sort_reversed_state = False

        self.config["reversed"] = self.sort_reversed_state
        self.save_config()
        self.watcher.library_changed.emit()

    def on_property_selected(self):
        data = self.properties_combo.currentData()
        if not isinstance(data, dict):
            self.properties_type.setText("")
            self.properties_value.blockSignals(True)
            self.properties_value.clear()
            self.properties_value.blockSignals(False)
            return
        name = data.get("name", "")
        stored = self.properties_data.get(name, data)
        self.properties_type.setText(stored.get("type", ""))
        self.properties_value.blockSignals(True)
        self.properties_value.setText(stored.get("value", ""))
        self.properties_value.blockSignals(False)

    def apply_property_value(self):
        data = self.properties_combo.currentData()
        if not isinstance(data, dict):
            return
        value = self.properties_value.text().strip()
        data["value"] = value
        name = data.get("name", "")
        if name:
            self.properties_data[name] = data
        idx = self.properties_combo.currentIndex()
        self.properties_combo.setItemData(idx, data)
        self.run_wallpaper()

    def populate_properties_combo(self, props_dict):
        self.properties_combo.blockSignals(True)
        self.properties_combo.clear()
        self.properties_combo.addItem(self._("properties_select_placeholder"), None)
        self.properties_data = {}
        for name, data in props_dict.items():
            item = {
                "name": name,
                "value": data.get("value", ""),
                "sep": data.get("sep", "="),
                "type": data.get("type", ""),
            }
            self.properties_data[name] = item
            self.properties_combo.addItem(name, item)
        self.properties_combo.setCurrentIndex(0)
        self.properties_combo.blockSignals(False)
        self.on_property_selected()

    def normalize_property_value(self, value):
        if "," in value:
            value = re.sub(r"\s*,\s*", ",", value)
        return value

    def parse_properties_output(self, output):
        props = []

        text = output.strip()
        if text:
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = None

            if parsed is None:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        parsed = json.loads(text[start:end + 1])
                    except Exception:
                        parsed = None

            if isinstance(parsed, dict):
                for name, value in parsed.items():
                    props.append((str(name), str(value), "=", ""))
                return props
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("property") or item.get("key")
                        if name is None:
                            continue
                        value = item.get("value", "")
                        props.append((str(name), str(value), "=", ""))
                    elif isinstance(item, str):
                        props.append((item, "", "=", ""))
                if props:
                    return props

        lines = output.splitlines()
        current_name = None
        current_type = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("_") or " - " in stripped:
                parts = stripped.split(" - ", 1)
                if parts:
                    current_name = parts[0].strip()
                    current_type = parts[1].strip() if len(parts) > 1 else ""
                continue
            if stripped.startswith("Value:"):
                if current_name:
                    value = stripped.split("Value:", 1)[1].strip()
                    props.append((current_name, value, "=", current_type))
                    current_name = None
                    current_type = ""
                continue

        if props:
            return props

        for line in lines:
            line = line.strip()
            if not line:
                continue
            lower = line.lower()
            if lower.startswith("properties") or line.startswith("#"):
                continue
            if lower.startswith("running with") or lower.startswith("particle "):
                continue
            if lower.startswith("found user setting with script value"):
                continue
            if "=" in line:
                name, value = line.split("=", 1)
                sep = "="
            elif ":" in line:
                name, value = line.split(":", 1)
                sep = ":"
            else:
                parts = line.split(None, 1)
                name = parts[0]
                value = parts[1] if len(parts) > 1 else ""
                sep = "="
            name = name.strip()
            value = value.strip()
            if name:
                props.append((name, value, sep, ""))
        return props

    def list_properties_logic(self, wallpaper_id):
        cmd = ["linux-wallpaperengine", "-l", wallpaper_id]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.terminate()
            stdout, stderr = proc.communicate(timeout=2)
        returncode = proc.returncode if proc.returncode is not None else 0
        combined = (stdout or "")
        if stderr:
            combined = (combined + "\n" + stderr).strip()
        return returncode, combined, stderr or "", timed_out, wallpaper_id

    def load_properties(self):
        wallpaper_id = self.wp_id_input.text().strip()
        if not wallpaper_id:
            self.status_bar.showMessage(self._("status_error_empty_id"))
            return
        if not shutil.which("linux-wallpaperengine"):
            self.status_bar.showMessage("Error: linux-wallpaperengine not found")
            return
        self.status_bar.showMessage(self._("status_loading_properties"))
        self.btn_load_props.setEnabled(False)
        self.props_thread = QThread()
        self.props_worker = Worker(self.list_properties_logic, wallpaper_id)
        self.props_worker.moveToThread(self.props_thread)
        self.props_thread.started.connect(self.props_worker.run)
        self.props_worker.finished.connect(self.load_properties_finished)
        self.props_worker.finished.connect(self.props_thread.quit)
        self.props_worker.finished.connect(self.props_worker.deleteLater)
        self.props_thread.finished.connect(self.props_thread.deleteLater)
        self.props_thread.start()

    def load_properties_finished(self, result):
        returncode, stdout, stderr, timed_out, wallpaper_id = result
        self.btn_load_props.setEnabled(True)
        if returncode != 0 and not timed_out:
            msg = stderr.strip() or "Unknown error"
            self.status_bar.showMessage(self._("status_properties_load_failed").format(error=msg))
            return
        props = self.parse_properties_output(stdout)
        stored = self.config.get("properties_by_wallpaper", {}).get(wallpaper_id, {})
        merged = {}
        for name, value, sep, prop_type in props:
            data = {"name": name, "value": value, "sep": sep, "type": prop_type}
            if name in stored:
                data["value"] = stored[name].get("value", value)
            merged[name] = data
        self.populate_properties_combo(merged)
        if props:
            if timed_out:
                self.status_bar.showMessage(self._("status_properties_loaded_timeout").format(count=len(props)))
            else:
                self.status_bar.showMessage(self._("status_properties_loaded").format(count=len(props)))
        else:
            if timed_out:
                self.status_bar.showMessage(self._("status_properties_none_timeout"))
            else:
                self.status_bar.showMessage(self._("status_properties_none"))

    def kill_external_wallpapers(self):
        self.wallpaper_proc_manager.kill_external("linux-wallpaperengine")

    def _append_global_wallpaper_flags(self, cmd):
        """Shared audio/perf/property flags for the backend process."""
        if self.chk_silent.isChecked():
            cmd.append('--silent')
        elif self.slider_volume.value() != 15:
            cmd.extend(['--volume', str(self.slider_volume.value())])
        if self.chk_no_automute.isChecked():
            cmd.append('--noautomute')
        if self.chk_no_proc.isChecked():
            cmd.append('--no-audio-processing')
        if self.slider_fps.value() != 30:
            cmd.extend(['--fps', str(self.slider_fps.value())])
        if self.chk_mouse.isChecked():
            cmd.append('--disable-mouse')
        if self.chk_parallax.isChecked():
            cmd.append('--disable-parallax')
        if self.chk_fs_pause.isChecked():
            cmd.append('--no-fullscreen-pause')
        if hasattr(self, "properties_data"):
            for name, data in self.properties_data.items():
                value = self.normalize_property_value(str(data.get("value", "")))
                sep = data.get("sep", "=")
                cmd.extend(['--set-property', f"{name}{sep}{value}"])
        custom_args = self.input_custom_args.text()
        if custom_args:
            for arg in custom_args.split():
                cmd.append(arg)

    def run_wallpaper(self, *_args):
        if not shutil.which("linux-wallpaperengine"):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error",
                "The backend 'linux-wallpaperengine' was not found in your PATH.\n\n"
                "Please install it first. See README.md for instructions.")
            self.status_bar.showMessage("Error: linux-wallpaperengine not found")
            return

        scale = self.combo_scaling.currentText()
        clamp = self.combo_clamp.currentText()
        self.config["scale"] = scale
        self.config["clamp"] = clamp

        cmd = ['linux-wallpaperengine']
        self._append_global_wallpaper_flags(cmd)

        if self.chk_windowed_mode.isChecked():
            # Windowed preview uses the currently selected wallpaper only
            selection = self.get_current_wallpaper_selection()
            if not selection:
                self.status_bar.showMessage(self._("status_error_empty_id"))
                return
            screen_name = self.get_primary_target_screen()
            geom = "0x0x1920x1080"
            found = next((s for s in self.screens if s["name"] == screen_name), None)
            if found:
                geom = f"{found['x']}x{found['y']}x{found['w']}x{found['h']}"
            if scale != 'default':
                cmd.extend(['--scaling', scale])
            if clamp != 'clamp':
                cmd.extend(['--clamp', clamp])
            cmd.extend(['--window', geom, '--bg', selection["id"]])
        else:
            # Build one process with per-monitor --screen-root / --bg pairs
            active = [
                (name, info) for name, info in self.monitor_assignments.items()
                if info and info.get("id")
            ]
            # Fallback: if nothing assigned yet, put selected wallpaper on every screen
            if not active:
                selection = self.get_current_wallpaper_selection()
                if not self.screens:
                    self.rebuild_monitor_panel()
                if selection and self.screens:
                    for s in self.screens:
                        self.monitor_assignments[s["name"]] = selection
                    self.refresh_monitor_row_labels()
                    active = [(s["name"], selection) for s in self.screens]
                else:
                    self.status_bar.showMessage(self._("status_error_no_assignments"))
                    return

            # Stable order: match detect_screens left-to-right
            order = {s["name"]: i for i, s in enumerate(self.screens)}
            active.sort(key=lambda pair: order.get(pair[0], 999))

            for screen_name, info in active:
                # Per-output scaling/clamp (backend applies to previous screen-root)
                if scale != 'default':
                    cmd.extend(['--scaling', scale])
                if clamp != 'clamp':
                    cmd.extend(['--clamp', clamp])
                cmd.extend(['--screen-root', screen_name, '--bg', str(info["id"])])

        self.stop_wallpapers()
        try:
            self.wallpaper_proc_manager.start(cmd)
            assigned = len([1 for v in self.monitor_assignments.values() if v and v.get("id")])
            self.status_bar.showMessage(
                self._("status_multi_launched").format(count=assigned)
            )
            self.save_config()
        except Exception as e:
            logging.error("Couldn't run with error %s", e)
            self.status_bar.showMessage(f"Error: {e}")

    def show_log_file(self):
        log_path = self.wallpaper_proc_manager.log_path()
        if not log_path.exists():
            self.status_bar.showMessage("Log file not found.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path)))

    def stop_wallpapers(self):
        stopped_internal = False
        if self.wallpaper_proc_manager.is_running():
            try:
                stopped_internal = self.wallpaper_proc_manager.stop(timeout=1)
            except Exception as e:
                logging.error("Couldn't stop internal wallpaper process: %s", e)

        # Fallback: If we didn't stop a child process (e.g. GUI restarted),
        # ensure we clean up any orphaned linux-wallpaperengine processes.
        # This restores the "force stop" capability users expect.
        if not stopped_internal:
            self.kill_external_wallpapers()
            self.status_bar.showMessage(self._("status_all_stopped"))
        else:
            self.status_bar.showMessage(self._("status_all_stopped"))

    def check_wallpaper_process(self):
        result = self.wallpaper_proc_manager.check()
        if result is None:
            return
        if result["expected"]:
            return
        returncode = result["returncode"]
        if returncode == 0:
            msg = "Wallpaper process exited."
        else:
            msg = f"Wallpaper process crashed (code {returncode})."
        if result["log_path"]:
            msg = f"{msg} Log: {result['log_path']}"
        self.status_bar.showMessage(msg)
        if hasattr(self, "tray") and self.tray.isVisible():
            self.tray.showMessage("Wallpaper Engine", msg)

    def restore_last_wallpaper(self):
        c = self.config.get("last_wallpaper", {})
        # Library Settings first so list is sorted consistently
        self.sorting_type.setCurrentText(self.config.get("sorting_type", "Name"))
        self.sort_reversed_state = self.config.get("reversed", False)
        self.btn_reverse_sorted.setText("↓" if self.sort_reversed_state else "↑")

        # Multi-monitor assignments (new format)
        stored = self.config.get("monitor_assignments") or {}
        if stored:
            self.monitor_assignments = {}
            for name, info in stored.items():
                if isinstance(info, dict) and info.get("id"):
                    self.monitor_assignments[name] = {
                        "id": str(info["id"]),
                        "title": info.get("title") or str(info["id"]),
                    }
                elif isinstance(info, str) and info:
                    self.monitor_assignments[name] = {"id": info, "title": info}
            self.refresh_monitor_row_labels()

        if not c and not stored:
            return

        if c:
            self.wp_id_input.setText(c.get("background_id", ""))
            screen = c.get("screen", "")
            if screen:
                self.set_primary_target_screen(screen)
            self.chk_silent.setChecked(c.get("silent", False))
            self.slider_volume.setValue(c.get("volume", 15))
            self.chk_no_automute.setChecked(c.get("noautomute", False))
            self.chk_no_proc.setChecked(c.get("no-audio-processing", False))
            self.slider_fps.setValue(c.get("fps", 30))
            self.chk_mouse.setChecked(c.get("disable-mouse", False))
            self.chk_parallax.setChecked(c.get("disable-parallax", False))
            self.chk_fs_pause.setChecked(c.get("no-fullscreen-pause", False))
            self.input_custom_args.setText(c.get("custom_args", ""))
            self.chk_windowed_mode.setChecked(c.get("windowed_mode", False))

            # Migrate legacy single-screen config into assignments if needed
            if not stored and c.get("background_id") and c.get("screen"):
                self.monitor_assignments[c["screen"]] = {
                    "id": c["background_id"],
                    "title": c.get("background_title") or c["background_id"],
                }
                self.refresh_monitor_row_labels()

        # Auto-apply restored multi-monitor layout
        if any(v.get("id") for v in self.monitor_assignments.values()):
            self.run_wallpaper()

    def detect_screens(self):
        screens = []
        # Prefer hyprctl on Hyprland (accurate connector names under Wayland)
        try:
            res = subprocess.run(
                ['hyprctl', 'monitors', '-j'],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                for m in data:
                    screens.append({
                        "name": m.get("name"),
                        "w": str(m.get("width", "?")),
                        "h": str(m.get("height", "?")),
                        "x": str(m.get("x", 0)),
                        "y": str(m.get("y", 0)),
                    })
                screens = [s for s in screens if s.get("name")]
                if screens:
                    screens.sort(key=lambda s: (int(s.get("x") or 0), int(s.get("y") or 0)))
                    return screens
        except Exception as e:
            logging.debug("hyprctl screen detection failed: %s", e)

        # xrandr (X11 / XWayland)
        try:
            res = subprocess.run(['xrandr', '--query'], capture_output=True, text=True, timeout=3)
            pattern = re.compile(
                r'^(\S+)\s+connected(?:\s+primary)?\s+(\d+)x(\d+)\+(\d+)\+(\d+)'
            )
            for line in res.stdout.splitlines():
                match = pattern.match(line)
                if match:
                    name, w, h, x, y = match.groups()
                    screens.append({"name": name, "w": w, "h": h, "x": x, "y": y})
        except Exception as e:
            logging.error("Screen detection error: %s", e)

        # Qt screens as last resort (names may be generic)
        if not screens:
            try:
                app = QApplication.instance()
                if app:
                    for i, qs in enumerate(app.screens()):
                        g = qs.geometry()
                        name = qs.name() or f"Screen-{i}"
                        screens.append({
                            "name": name,
                            "w": str(g.width()),
                            "h": str(g.height()),
                            "x": str(g.x()),
                            "y": str(g.y()),
                        })
            except Exception as e:
                logging.error("Qt screen detection error: %s", e)

        if not screens:
            screens = [{"name": "eDP-1", "w": "1920", "h": "1080", "x": "0", "y": "0"}]

        screens.sort(key=lambda s: (int(s.get("x") or 0), int(s.get("y") or 0)))
        return screens

    def load_config_data(self):
        self.config = {}

        # Ensure config directory exists
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create config directory: {e}")

        # Migration: Check for old config in current working directory
        old_config_path = pathlib.Path(__file__).parent / "wpe_gui_config.json"
        if old_config_path.exists() and not CONFIG_FILE.exists():
            logging.info(f"Migrating config from {old_config_path} to {CONFIG_FILE}")
            try:
                shutil.move(str(old_config_path), str(CONFIG_FILE))
            except Exception as e:
                logging.error(f"Migration failed: {e}")

        if os.path.exists(CONFIG_FILE):
            logging.info("Attempting to read config from: %s", CONFIG_FILE)
            try:
                with open(CONFIG_FILE, 'r') as f: self.config = json.load(f)
            except Exception as e:
                logging.info("Failed to open config with error %s", e)
        if "properties_by_wallpaper" not in self.config:
            self.config["properties_by_wallpaper"] = {}

    def apply_config_ui(self):
        pass

    def on_wallpaper_id_changed(self):
        wallpaper_id = self.wp_id_input.text().strip()
        stored = self.config.get("properties_by_wallpaper", {}).get(wallpaper_id, {})
        self.populate_properties_combo(stored)

    def save_config(self):
        selection = self.get_current_wallpaper_selection()
        self.config["last_wallpaper"] = {
            "background_id": self.wp_id_input.text(),
            "background_title": (selection or {}).get("title", ""),
            "screen": self.get_primary_target_screen(),
            "silent": self.chk_silent.isChecked(),
            "volume": self.slider_volume.value(),
            "noautomute": self.chk_no_automute.isChecked(),
            "no-audio-processing": self.chk_no_proc.isChecked(),
            "fps": self.slider_fps.value(),
            "disable-mouse": self.chk_mouse.isChecked(),
            "disable-parallax": self.chk_parallax.isChecked(),
            "no-fullscreen-pause": self.chk_fs_pause.isChecked(),
            "custom_args": self.input_custom_args.text(),
            "windowed_mode": self.chk_windowed_mode.isChecked(),
        }
        # Persist per-monitor assignments for dual/multi-monitor restore
        self.config["monitor_assignments"] = {
            name: {"id": info.get("id", ""), "title": info.get("title", "")}
            for name, info in self.monitor_assignments.items()
            if info and info.get("id")
        }
        wallpaper_id = self.wp_id_input.text().strip()
        if wallpaper_id:
            props_out = {}
            for name, data in self.properties_data.items():
                props_out[name] = {
                    "value": str(data.get("value", "")),
                    "sep": data.get("sep", "="),
                    "type": data.get("type", ""),
                }
            self.config.setdefault("properties_by_wallpaper", {})[wallpaper_id] = props_out
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w') as f: json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error("Couldn't save config with error %s", e)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(QApplication.instance())
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#007AFF"))
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        from PyQt6.QtGui import QPainter, QBrush
        painter = QPainter(img)
        painter.setBrush(QBrush(QColor("#007AFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 64, 64)
        painter.end()
        self.tray.setIcon(QIcon(QPixmap.fromImage(img)))

        self.tray_menu = QMenu()
        a_show = QAction(self._("show_window_tray_menu"), self)
        a_show.triggered.connect(self.show)
        a_exit = QAction(self._("exit_tray_menu"), self)
        a_exit.triggered.connect(self.quit_app)
        self.tray_menu.addAction(a_show)
        self.tray_menu.addAction(a_exit)

        self.tray.setContextMenu(self.tray_menu)
        self.tray.show()

    def closeEvent(self, event):
        if self.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            self.quit_app()

    def quit_app(self):
        logging.info("Exiting application...")
        self.stop_wallpapers()
        if hasattr(self, 'watcher'):
            self.watcher.stop()

        # Force kill any remaining backend processes to ensure clean exit
        self.kill_external_wallpapers()

        QApplication.quit()

if __name__ == "__main__":
    logging.basicConfig(format='[%(asctime)s] [%(levelname)s]:  %(message)s')
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    window = WallpaperApp()
    parser = argparse.ArgumentParser(description="A simple gui for linux-wallpaperengine")
    parser.add_argument("--background", action="store_true", help="Start the GUI minimized to the tray")
    args = parser.parse_args()
    if not args.background:
        window.show()
    sys.exit(app.exec())
