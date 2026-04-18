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
QCheckBox::indicator:checked { background: #0A84FF; border-color: #0A84FF; image: url(CHECKMARK_PATH); }
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
        self.setWindowTitle(f"{self._('app_title')} [build: props-ui-1]")
        self.setFixedSize(900, 900)
        self.setup_ui()
        self.apply_theme()
        self.apply_config_ui()
        self.setup_tray()
        self.start_scan()
        self.stack.setCurrentIndex(1)
        self.nav_bar.setCurrentRow(1)
        self.screens = self.detect_screens()
        for s in self.screens:
            self.screen_combo.addItem(s["name"], s)
        self.update_texts()

        # Setup file watcher for auto-refresh
        self.watcher = LibraryWatcher()
        self.watcher.library_changed.connect(self.on_library_changed_auto)

        QTimer.singleShot(500, self.restore_last_wallpaper)

        self.wallpaper_proc_manager = WallpaperProcessManager()
        # Per-screen process managers and wallpaper assignments (for multi-screen support)
        self.screen_proc_managers = {}   # screen_name -> WallpaperProcessManager
        self.screen_assignments = {}     # screen_name -> background_id
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
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        card_main = self.create_card(layout, "main_controls_frame")
        self.wp_id_input = QLineEdit()
        self.wp_id_input.textChanged.connect(self.on_wallpaper_id_changed)
        self.screen_combo = QComboBox()
        self.screen_combo.setEditable(True)
        self.add_form_row(card_main, "wallpaper_id_path_label", self.wp_id_input)
        self.add_form_row(card_main, "screen_label", self.screen_combo)
        self.chk_keep_others = QCheckBox("keep_others_checkbox")
        self.chk_keep_others.setChecked(True)
        card_main.layout().addWidget(self.chk_keep_others)
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
        push_buttons_layout.setContentsMargins(0, 0, 0, 0)
        push_buttons_layout.setSpacing(25)
        push_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        header = QHBoxLayout()
        self.btn_scan = QPushButton("scan_local_wallpapers_button")
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_scan.setFixedSize(160, 200)
        self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        push_buttons_layout.addWidget(self.btn_scan)
        self.btn_set_library = QPushButton("set_wallpaper_button")
        self.btn_set_library.clicked.connect(self.run_wallpaper)
        self.btn_set_library.setFixedSize(160, 200)
        self.btn_set_library.setObjectName("PrimaryButton")
        self.btn_set_library.setCursor(Qt.CursorShape.PointingHandCursor)
        push_buttons_layout.addWidget(self.btn_set_library)
        self.btn_select_folder = QPushButton("select_folder_button")
        self.btn_select_folder.clicked.connect(self.manual_scan)
        self.btn_select_folder.setFixedSize(160, 200)
        self.btn_select_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        push_buttons_layout.addWidget(self.btn_select_folder)
        self.btn_stop_library = QPushButton("remove_wallpaper_button")
        self.btn_stop_library.setObjectName("DangerButton")
        self.btn_stop_library.clicked.connect(self.stop_screen_wallpaper)
        self.btn_stop_library.setFixedSize(160, 200)
        self.btn_stop_library.setCursor(Qt.CursorShape.PointingHandCursor)
        push_buttons_layout.addWidget(self.btn_stop_library)
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
        self.list_wallpapers.itemDoubleClicked.connect(self.run_wallpaper)
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
        import pathlib
        checkmark = pathlib.Path(__file__).parent / "checkmark.svg"
        self.setStyleSheet(MACOS_DARK.replace("CHECKMARK_PATH", str(checkmark)))

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
        self.btn_set.setText(self._("set_wallpaper_button"))
        self.btn_set_library.setText(self._("set_wallpaper_button"))
        self.btn_stop.setText(self._("stop_button"))
        self.btn_stop_library.setText(self._("remove_wallpaper_button"))
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
        self.chk_keep_others.setText(self._("keep_others_checkbox"))
        self.lbl_kwin_hint.setText(self._("kwin_hint"))
        self.btn_load_props.setText(self._("load_properties_button"))
        self.btn_apply_prop.setText(self._("apply_property_button"))
        self.properties_combo.setItemText(0, self._("properties_select_placeholder"))
        self.properties_value.setPlaceholderText(self._("property_value_placeholder"))
        self.search_input.setPlaceholderText(self._("search_placeholder"))

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
        data = item.data(Qt.ItemDataRole.UserRole)
        self.wp_id_input.setText(data["id"])

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

    def run_wallpaper(self):
        if not shutil.which("linux-wallpaperengine"):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error",
                "The backend 'linux-wallpaperengine' was not found in your PATH.\n\n"
                "Please install it first. See README.md for instructions.")
            self.status_bar.showMessage("Error: linux-wallpaperengine not found")
            return

        cmd = ['linux-wallpaperengine']
        screen_name = self.screen_combo.currentText()

        if self.chk_windowed_mode.isChecked():
            geom = "0x0x1920x1080"
            found = next((s for s in self.screens if s["name"] == screen_name), None)
            if found:
                geom = f"{found['x']}x{found['y']}x{found['w']}x{found['h']}"
            cmd.extend(['--window', geom])
        else:
            cmd.extend(['--screen-root', screen_name])

        cmd.extend(['--bg', self.wp_id_input.text()])
        if self.chk_silent.isChecked(): cmd.append('--silent')
        elif self.slider_volume.value() != 15: cmd.extend(['--volume', str(self.slider_volume.value())])
        if self.chk_no_automute.isChecked(): cmd.append('--noautomute')
        if self.chk_no_proc.isChecked(): cmd.append('--no-audio-processing')
        if self.slider_fps.value() != 30: cmd.extend(['--fps', str(self.slider_fps.value())])
        if self.chk_mouse.isChecked(): cmd.append('--disable-mouse')
        if self.chk_parallax.isChecked(): cmd.append('--disable-parallax')
        if self.chk_fs_pause.isChecked(): cmd.append('--no-fullscreen-pause')
        scale = self.combo_scaling.currentText()
        self.config["scale"] = scale
        if scale != 'default': cmd.extend(['--scaling', scale])
        clamp = self.combo_clamp.currentText()
        self.config["clamp"] = clamp
        if clamp != 'clamp': cmd.extend(['--clamp', clamp])
        if hasattr(self, "properties_data"):
            for name, data in self.properties_data.items():
                value = self.normalize_property_value(str(data.get("value", "")))
                sep = data.get("sep", "=")
                cmd.extend(['--set-property', f"{name}{sep}{value}"])
        custom_args = self.input_custom_args.text()
        if custom_args:
             for arg in custom_args.split(): cmd.append(arg)

        if self.chk_keep_others.isChecked():
            # Stop only the process running on the selected screen, leave others alone.
            old_mgr = self.screen_proc_managers.get(screen_name)
            if old_mgr and old_mgr.is_running():
                try:
                    old_mgr.stop(timeout=1)
                except Exception as e:
                    logging.error("Couldn't stop per-screen process for %s: %s", screen_name, e)
            try:
                mgr = WallpaperProcessManager()
                mgr.start(cmd)
                self.screen_proc_managers[screen_name] = mgr
                self.screen_assignments[screen_name] = self.wp_id_input.text()
                self.status_bar.showMessage(self._("status_command_launched"))
                self.save_config()
            except Exception as e:
                logging.error("Couldn't run with error %s", e)
                self.status_bar.showMessage(f"Error: {e}")
        else:
            # Legacy path: kill everything, then start fresh on the selected screen.
            self.stop_wallpapers()
            self.screen_assignments = {screen_name: self.wp_id_input.text()}
            try:
                self.wallpaper_proc_manager.start(cmd)
                self.status_bar.showMessage(self._("status_command_launched"))
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

        # Stop all per-screen managers (multi-screen mode).
        for screen_name, mgr in list(self.screen_proc_managers.items()):
            if mgr.is_running():
                try:
                    mgr.stop(timeout=1)
                    stopped_internal = True
                except Exception as e:
                    logging.error("Couldn't stop per-screen process for %s: %s", screen_name, e)
        self.screen_proc_managers.clear()
        self.screen_assignments.clear()

        # Also stop the legacy single process manager.
        if self.wallpaper_proc_manager.is_running():
            try:
                stopped_internal = self.wallpaper_proc_manager.stop(timeout=1) or stopped_internal
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

    def stop_screen_wallpaper(self):
        """Stop the wallpaper only for the currently selected screen, leaving others untouched."""
        screen_name = self.screen_combo.currentText()
        mgr = self.screen_proc_managers.pop(screen_name, None)
        if mgr and mgr.is_running():
            try:
                mgr.stop(timeout=1)
            except Exception as e:
                logging.error("Couldn't stop wallpaper on %s: %s", screen_name, e)
        self.screen_assignments.pop(screen_name, None)
        # Also stop the legacy single manager in case it was the one running for this screen.
        if self.wallpaper_proc_manager.is_running():
            try:
                self.wallpaper_proc_manager.stop(timeout=1)
            except Exception as e:
                logging.error("Couldn't stop legacy wallpaper: %s", e)
        self.status_bar.showMessage(self._("status_all_stopped"))
        self.save_config()

    def check_wallpaper_process(self):
        result = self.wallpaper_proc_manager.check()
        if result is not None and not result["expected"]:
            returncode = result["returncode"]
            msg = "Wallpaper process exited." if returncode == 0 else f"Wallpaper process crashed (code {returncode})."
            if result["log_path"]:
                msg = f"{msg} Log: {result['log_path']}"
            self.status_bar.showMessage(msg)
            if hasattr(self, "tray") and self.tray.isVisible():
                self.tray.showMessage("Wallpaper Engine", msg)

        # Check per-screen managers.
        for screen_name in list(self.screen_proc_managers.keys()):
            mgr = self.screen_proc_managers.get(screen_name)
            if mgr is None:
                continue
            result = mgr.check()
            if result is None:
                continue
            if result["expected"]:
                self.screen_proc_managers.pop(screen_name, None)
                self.screen_assignments.pop(screen_name, None)
                continue
            returncode = result["returncode"]
            msg = f"Wallpaper on {screen_name} exited." if returncode == 0 else f"Wallpaper on {screen_name} crashed (code {returncode})."
            if result["log_path"]:
                msg = f"{msg} Log: {result['log_path']}"
            self.status_bar.showMessage(msg)
            if hasattr(self, "tray") and self.tray.isVisible():
                self.tray.showMessage("Wallpaper Engine", msg)
            self.screen_proc_managers.pop(screen_name, None)
            self.screen_assignments.pop(screen_name, None)

    def restore_last_wallpaper(self):
        c = self.config.get("last_wallpaper", {})
        if not c: return
        keep_others = c.get("keep_others", True)
        self.chk_keep_others.setChecked(keep_others)
        self.wp_id_input.setText(c.get("background_id", ""))
        self.screen_combo.setCurrentText(c.get("screen", ""))
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
        # Kill any orphaned processes from a previous crash before starting new ones.
        self.kill_external_wallpapers()
        self.run_wallpaper()
        # Restore wallpapers on other screens saved from the previous session.
        if keep_others:
            saved_assignments = self.config.get("screen_assignments", {})
            primary_screen = c.get("screen", "")
            for screen_name, bg_id in saved_assignments.items():
                if screen_name == primary_screen:
                    continue
                if not bg_id:
                    continue
                self._launch_screen(screen_name, bg_id)
        # Library Settings
        self.sorting_type.setCurrentText(self.config.get("sorting_type", "name"))
        self.sort_reversed_state = self.config.get("reversed", False)
        self.btn_reverse_sorted.setText("↑") if self.sort_reversed_state == False else self.btn_reverse_sorted.setText("↓")
        self.watcher.library_changed.emit()

    def _launch_screen(self, screen_name, bg_id):
        """Start linux-wallpaperengine on a specific screen with the given wallpaper ID,
        using current audio/perf settings. Does not affect other running screens."""
        if not bg_id:
            return
        old_mgr = self.screen_proc_managers.get(screen_name)
        if old_mgr and old_mgr.is_running():
            try:
                old_mgr.stop(timeout=1)
            except Exception as e:
                logging.error("Couldn't stop per-screen process for %s: %s", screen_name, e)
        cmd = ['linux-wallpaperengine']
        if self.chk_windowed_mode.isChecked():
            geom = "0x0x1920x1080"
            found = next((s for s in self.screens if s["name"] == screen_name), None)
            if found:
                geom = f"{found['x']}x{found['y']}x{found['w']}x{found['h']}"
            cmd.extend(['--window', geom])
        else:
            cmd.extend(['--screen-root', screen_name])
        cmd.extend(['--bg', bg_id])
        if self.chk_silent.isChecked(): cmd.append('--silent')
        elif self.slider_volume.value() != 15: cmd.extend(['--volume', str(self.slider_volume.value())])
        if self.chk_no_automute.isChecked(): cmd.append('--noautomute')
        if self.chk_no_proc.isChecked(): cmd.append('--no-audio-processing')
        if self.slider_fps.value() != 30: cmd.extend(['--fps', str(self.slider_fps.value())])
        if self.chk_mouse.isChecked(): cmd.append('--disable-mouse')
        if self.chk_parallax.isChecked(): cmd.append('--disable-parallax')
        if self.chk_fs_pause.isChecked(): cmd.append('--no-fullscreen-pause')
        scale = self.combo_scaling.currentText()
        if scale != 'default': cmd.extend(['--scaling', scale])
        clamp = self.combo_clamp.currentText()
        if clamp != 'clamp': cmd.extend(['--clamp', clamp])
        try:
            mgr = WallpaperProcessManager()
            mgr.start(cmd)
            self.screen_proc_managers[screen_name] = mgr
            self.screen_assignments[screen_name] = bg_id
        except Exception as e:
            logging.error("Couldn't launch wallpaper on %s: %s", screen_name, e)

    def detect_screens(self):
        screens = []
        try:
            res = subprocess.run(['xrandr', '--query'], capture_output=True, text=True)


            pattern = re.compile(r'^(\S+)\s+connected\s+(?:primary\s+)?(\d+)x(\d+)\+(\d+)\+(\d+)')

            for line in res.stdout.splitlines():
                match = pattern.match(line)
                if match:
                    name, w, h, x, y = match.groups()
                    screens.append({
                        "name": name,
                        "w": w, "h": h, "x": x, "y": y
                    })
        except Exception as e:
            logging.error(f"Screen detection error: {e}")

        if not screens:
            screens = [{"name": "eDP-1", "w": "1920", "h": "1080", "x": "0", "y": "0"}]

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
        self.config["last_wallpaper"] = {
            "background_id": self.wp_id_input.text(),
            "screen": self.screen_combo.currentText(),
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
            "keep_others": self.chk_keep_others.isChecked(),
        }
        # Persist per-screen assignments so they can be restored on next launch.
        self.config["screen_assignments"] = dict(self.screen_assignments)
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
