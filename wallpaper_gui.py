import sys
import os
import glob
import json
import subprocess
import shutil
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QCheckBox, QSlider, QComboBox, 
                             QStackedWidget, QListWidget, QListWidgetItem, QSystemTrayIcon, 
                             QMenu, QFrame, QSizePolicy, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QImage, QAction, QColor

CONFIG_FILE = "wpe_gui_config.json"
LOCALE_DIR = "locales"

MACOS_DARK = """
QMainWindow { background-color: #1E1E1E; }
QWidget { color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Helvetica, sans-serif; font-size: 13px; }
QListWidget#Sidebar { background-color: #262626; border: none; outline: none; font-size: 13px; font-weight: 500; }
QListWidget#Sidebar::item { height: 32px; padding-left: 10px; margin: 2px 10px; border-radius: 6px; color: #9A9A9A; }
QListWidget#Sidebar::item:selected { background-color: #3A3A3A; color: #FFFFFF; }
QListWidget#Sidebar::item:hover:!selected { background-color: #2F2F2F; color: #FFFFFF; }
QFrame.Card { background-color: #2D2D2D; border: 1px solid #3A3A3A; border-radius: 10px; }
QLabel.CardTitle { font-weight: 600; font-size: 15px; color: #FFFFFF; margin-bottom: 8px; }
QLineEdit, QComboBox { background-color: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 6px; padding: 4px 8px; color: #FFFFFF; selection-background-color: #0A84FF; min-height: 22px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #0A84FF; }
QComboBox::drop-down { border: none; }
QPushButton { background-color: #0A84FF; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-weight: 500; font-size: 13px; min-height: 20px; }
QPushButton:hover { background-color: #007AFF; }
QPushButton:pressed { background-color: #0062CC; }
QPushButton#SecondaryButton { background-color: #3A3A3A; border: 1px solid #3A3A3A; color: #FFFFFF; }
QPushButton#SecondaryButton:hover { background-color: #454545; }
QPushButton#DangerButton { background-color: #FF453A; }
QPushButton#DangerButton:hover { background-color: #D0342C; }
QCheckBox { spacing: 8px; color: #FFFFFF; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #666666; background: #2D2D2D; }
QCheckBox::indicator:checked { background: #0A84FF; border-color: #0A84FF; }
QSlider::groove:horizontal { border: 1px solid #3A3A3A; height: 4px; background: #3A3A3A; margin: 2px 0; border-radius: 2px; }
QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #5c5c5c; width: 18px; height: 18px; margin: -8px 0; border-radius: 9px; }
QListWidget#WallpaperList { background-color: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 8px; outline: none; }
QListWidget#WallpaperList::item { padding: 8px; border-bottom: 1px solid #2D2D2D; color: #FFFFFF; }
QListWidget#WallpaperList::item:selected { background-color: #0A84FF; color: white; border-radius: 4px; }
QLabel#PreviewBox { background-color: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 16px; color: #666666; }
"""

MACOS_LIGHT = """
QMainWindow { background-color: #F5F5F7; }
QWidget { color: #000000; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Helvetica, sans-serif; font-size: 13px; }
QListWidget#Sidebar { background-color: #EBEDF0; border: none; outline: none; font-size: 13px; font-weight: 500; }
QListWidget#Sidebar::item { height: 32px; padding-left: 10px; margin: 2px 10px; border-radius: 6px; color: #555555; }
QListWidget#Sidebar::item:selected { background-color: #FFFFFF; color: #000000; border: 1px solid #E5E5E5; }
QListWidget#Sidebar::item:hover:!selected { background-color: #E0E0E0; color: #000000; }
QFrame.Card { background-color: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 10px; }
QLabel.CardTitle { font-weight: 600; font-size: 15px; color: #000000; margin-bottom: 8px; }
QLineEdit, QComboBox { background-color: #FFFFFF; border: 1px solid #D1D1D6; border-radius: 6px; padding: 4px 8px; color: #000000; selection-background-color: #007AFF; min-height: 22px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #007AFF; }
QComboBox::drop-down { border: none; }
QPushButton { background-color: #007AFF; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-weight: 500; font-size: 13px; min-height: 20px; }
QPushButton:hover { background-color: #0062CC; }
QPushButton:pressed { background-color: #0051A8; }
QPushButton#SecondaryButton { background-color: #FFFFFF; border: 1px solid #D1D1D6; color: #000000; }
QPushButton#SecondaryButton:hover { background-color: #F2F2F7; }
QPushButton#DangerButton { background-color: #FF3B30; }
QPushButton#DangerButton:hover { background-color: #D70015; }
QCheckBox { spacing: 8px; color: #000000; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #D1D1D6; background: #FFFFFF; }
QCheckBox::indicator:checked { background: #007AFF; border-color: #007AFF; }
QSlider::groove:horizontal { border: 1px solid #D1D1D6; height: 4px; background: #D1D1D6; margin: 2px 0; border-radius: 2px; }
QSlider::handle:horizontal { background: #FFFFFF; border: 1px solid #D1D1D6; width: 18px; height: 18px; margin: -8px 0; border-radius: 9px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
QListWidget#WallpaperList { background-color: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 8px; outline: none; }
QListWidget#WallpaperList::item { padding: 8px; border-bottom: 1px solid #F2F2F7; color: #000000; }
QListWidget#WallpaperList::item:selected { background-color: #007AFF; color: white; border-radius: 4px; }
QLabel#PreviewBox { background-color: #F2F2F7; border: 1px solid #E5E5E5; border-radius: 16px; color: #999999; }
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

class WallpaperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.i18n = I18n()
        self.load_config_data()
        self.i18n.load(self.config.get("current_language", "en"))
        self._ = self.i18n.get
        self.setWindowTitle(self._("app_title"))
        self.setFixedSize(1050, 750)
        self.setup_ui()
        self.apply_theme()
        self.apply_config_ui()
        self.setup_tray()
        self.screens = self.detect_screens()
        for s in self.screens:
            self.screen_combo.addItem(s["name"], s)
        if self.config.get("auto_restore", False):
            QTimer.singleShot(1000, self.restore_last_wallpaper)
        self.update_texts()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar.addItems(["Control", "Library", "Settings"])
        self.sidebar.currentRowChanged.connect(self.switch_page)
        main_layout.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        self.page_control = QWidget()
        self.setup_control_page()
        self.stack.addWidget(self.page_control)
        self.page_library = QWidget()
        self.setup_library_page()
        self.stack.addWidget(self.page_library)
        self.page_settings = QWidget()
        self.setup_settings_page()
        self.stack.addWidget(self.page_settings)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        self.status_bar.hide()

    def setup_control_page(self):
        layout = QVBoxLayout(self.page_control)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        card_main = self.create_card(layout, "main_controls_frame")
        self.wp_id_input = QLineEdit()
        self.screen_combo = QComboBox()
        self.screen_combo.setEditable(True)
        self.add_form_row(card_main, "wallpaper_id_path_label", self.wp_id_input)
        self.add_form_row(card_main, "screen_label", self.screen_combo)
        h_layout = QHBoxLayout()
        h_layout.setSpacing(20)
        layout.addLayout(h_layout)
        card_audio = self.create_card(h_layout, "audio_frame")
        self.chk_silent = QCheckBox("silent_checkbox")
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(15)
        self.chk_no_automute = QCheckBox("no_automute_checkbox")
        self.chk_no_proc = QCheckBox("no_audio_processing_checkbox")
        l = card_audio.layout()
        l.addWidget(self.chk_silent)
        l.addWidget(QLabel("volume_label"))
        l.addWidget(self.slider_volume)
        l.addWidget(self.chk_no_automute)
        l.addWidget(self.chk_no_proc)
        card_perf = self.create_card(h_layout, "perf_frame")
        self.slider_fps = QSlider(Qt.Orientation.Horizontal)
        self.slider_fps.setRange(10, 144)
        self.slider_fps.setValue(30)
        self.chk_mouse = QCheckBox("disable_mouse_checkbox")
        self.chk_parallax = QCheckBox("disable_parallax_checkbox")
        self.chk_fs_pause = QCheckBox("no_fullscreen_pause_checkbox")
        l = card_perf.layout()
        l.addWidget(QLabel("fps_label"))
        l.addWidget(self.slider_fps)
        l.addWidget(self.chk_mouse)
        l.addWidget(self.chk_parallax)
        l.addWidget(self.chk_fs_pause)
        card_adv = self.create_card(layout, "adv_frame")
        self.combo_scaling = QComboBox()
        self.combo_scaling.addItems(['default', 'stretch', 'fit', 'fill'])
        self.combo_clamp = QComboBox()
        self.combo_clamp.addItems(['clamp', 'border', 'repeat'])
        self.chk_windowed_mode = QCheckBox("windowed_mode_checkbox")
        self.input_props = QLineEdit()
        self.input_custom_args = QLineEdit()
        self.input_custom_args.setPlaceholderText("--window 0x0x1280x720")
        self.add_form_row(card_adv, "scaling_label", self.combo_scaling)
        self.add_form_row(card_adv, "clamp_label", self.combo_clamp)
        card_adv.layout().addWidget(self.chk_windowed_mode)
        
        self.lbl_kwin_hint = QLabel("kwin_hint")
        self.lbl_kwin_hint.setWordWrap(True)
        self.lbl_kwin_hint.setStyleSheet("color: #888; font-size: 11px; margin-left: 24px; margin-bottom: 8px;")
        self.lbl_kwin_hint.setVisible(False)
        self.chk_windowed_mode.toggled.connect(self.lbl_kwin_hint.setVisible)
        card_adv.layout().addWidget(self.lbl_kwin_hint)

        self.add_form_row(card_adv, "set_property_label", self.input_props)
        self.add_form_row(card_adv, "Custom Arguments", self.input_custom_args)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        layout.addLayout(btn_layout)
        self.btn_set = QPushButton("set_wallpaper_button")
        self.btn_set.clicked.connect(self.run_wallpaper)
        self.btn_set.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set.setMinimumHeight(32)
        self.btn_stop = QPushButton("stop_button")
        self.btn_stop.setObjectName("DangerButton")
        self.btn_stop.clicked.connect(self.stop_wallpapers)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setMinimumHeight(32)
        self.btn_restore = QPushButton("restore_last_button")
        self.btn_restore.setObjectName("SecondaryButton")
        self.btn_restore.clicked.connect(self.restore_last_wallpaper)
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.setMinimumHeight(32)
        btn_layout.addWidget(self.btn_set)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_restore)
        layout.addStretch()

    def setup_library_page(self):
        layout = QVBoxLayout(self.page_library)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        self.btn_scan = QPushButton("scan_local_wallpapers_button")
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_scan.setMinimumHeight(32)
        self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.btn_scan)
        splitter = QHBoxLayout()
        splitter.setSpacing(16)
        layout.addLayout(splitter, 1)
        self.list_wallpapers = QListWidget()
        self.list_wallpapers.setObjectName("WallpaperList")
        self.list_wallpapers.itemClicked.connect(self.on_wallpaper_selected)
        splitter.addWidget(self.list_wallpapers, 1)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        self.btn_set_library = QPushButton("set_wallpaper_button")
        self.btn_set_library.clicked.connect(self.run_wallpaper)
        self.btn_set_library.setMinimumHeight(32)
        self.btn_set_library.setCursor(Qt.CursorShape.PointingHandCursor)
        right_layout.addWidget(self.btn_set_library)
        self.lbl_preview = QLabel("Preview")
        self.lbl_preview.setObjectName("PreviewBox")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setFixedSize(480, 360)
        right_layout.addWidget(self.lbl_preview, 1, Qt.AlignmentFlag.AlignCenter)
        splitter.addWidget(right_container, 1)

    def setup_settings_page(self):
        layout = QVBoxLayout(self.page_settings)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        card = self.create_card(layout, "settings_tab")
        self.combo_lang = QComboBox()
        self.combo_lang.currentTextChanged.connect(self.change_lang)
        self.add_form_row(card, "language_label", self.combo_lang)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Dark", "Light"])
        self.combo_theme.currentTextChanged.connect(self.change_theme)
        row_theme = QHBoxLayout()
        lbl_theme = QLabel("Theme")
        row_theme.addWidget(lbl_theme)
        row_theme.addWidget(self.combo_theme)
        card.layout().addLayout(row_theme)
        self.chk_auto_restore = QCheckBox("auto_restore_checkbox")
        self.chk_auto_restore.clicked.connect(self.save_config)
        self.chk_stop_exit = QCheckBox("stop_on_exit_checkbox")
        self.chk_stop_exit.clicked.connect(self.save_config)
        card.layout().addWidget(self.chk_auto_restore)
        card.layout().addWidget(self.chk_stop_exit)
        layout.addStretch()

    def create_card(self, parent_layout, title_key):
        frame = QFrame()
        frame.setProperty("class", "Card")
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(12)
        lbl = QLabel(title_key)
        lbl.setProperty("class", "CardTitle")
        vbox.addWidget(lbl)
        parent_layout.addWidget(frame)
        return frame

    def add_form_row(self, card, label_key, widget):
        h = QHBoxLayout()
        l = QLabel(label_key)
        h.addWidget(l)
        h.addWidget(widget)
        card.layout().addLayout(h)

    def apply_theme(self):
        theme = self.config.get("theme", "Dark")
        if theme == "Dark":
            self.setStyleSheet(MACOS_DARK)
        else:
            self.setStyleSheet(MACOS_LIGHT)

    def update_texts(self):
        items = ["control_tab", "local_library_tab", "settings_tab"]
        for i, key in enumerate(items):
            self.sidebar.item(i).setText(self._(key))
        self.combo_lang.blockSignals(True)
        self.combo_lang.clear()
        for code, name in self.i18n.available_languages.items():
            self.combo_lang.addItem(name, code)
        self.combo_lang.setCurrentText(self.i18n.available_languages.get(self.i18n.current_code, "English"))
        self.combo_lang.blockSignals(False)
        self.combo_theme.blockSignals(True)
        self.combo_theme.setCurrentText(self.config.get("theme", "Dark"))
        self.combo_theme.blockSignals(False)
        self.btn_set.setText(self._("set_wallpaper_button"))
        self.btn_set_library.setText(self._("set_wallpaper_button"))
        self.btn_stop.setText(self._("stop_button"))
        self.btn_restore.setText(self._("restore_last_button"))
        self.btn_scan.setText(self._("scan_local_wallpapers_button"))
        self.chk_silent.setText(self._("silent_checkbox"))
        self.chk_no_automute.setText(self._("no_automute_checkbox"))
        self.chk_no_proc.setText(self._("no_audio_processing_checkbox"))
        self.chk_mouse.setText(self._("disable_mouse_checkbox"))
        self.chk_parallax.setText(self._("disable_parallax_checkbox"))
        self.chk_fs_pause.setText(self._("no_fullscreen_pause_checkbox"))
        self.chk_windowed_mode.setText(self._("windowed_mode_checkbox"))
        self.lbl_kwin_hint.setText(self._("kwin_hint"))
        self.chk_auto_restore.setText(self._("auto_restore_checkbox"))
        self.chk_stop_exit.setText(self._("stop_on_exit_checkbox"))

    def switch_page(self, row):
        self.stack.setCurrentIndex(row)

    def change_lang(self, text):
        code = self.combo_lang.currentData()
        if self.i18n.load(code):
            self.update_texts()
            self.config["current_language"] = code
            self.save_config()

    def change_theme(self, text):
        self.config["theme"] = text
        self.apply_theme()
        self.save_config()

    def start_scan(self):
        self.status_bar.showMessage(self._("status_searching_local"))
        self.btn_scan.setEnabled(False)
        self.thread = QThread()
        self.worker = Worker(self.scan_logic)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.scan_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def scan_logic(self):
        workshop_dirs = set()
        
        # 1. Standard expected paths
        base_paths = [
            os.path.expanduser("~/.local/share/Steam"),
            os.path.expanduser("~/.steam/steam"),
            # Common Flatpak paths
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.local/share/Steam"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.data/Steam"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.steam/steam"),
        ]
        
        # Dynamic Snap paths
        base_paths.extend(glob.glob(os.path.expanduser("~/snap/steam/*/.local/share/Steam")))
        base_paths.extend(glob.glob(os.path.expanduser("~/snap/steam/*/.steam/steam")))
        base_paths.extend(glob.glob(os.path.expanduser("~/snap/steam/*/.steam/root")))

        for base in base_paths:
            if not os.path.exists(base): continue
            
            # Check for Workshop Content (431960)
            p_workshop = os.path.join(base, "steamapps/workshop/content/431960")
            if os.path.isdir(p_workshop):
                workshop_dirs.add(p_workshop)
            
            # Check for Default Presets (wallpaper_engine/assets/presets)
            p_presets = os.path.join(base, "steamapps/common/wallpaper_engine/assets/presets")
            if os.path.isdir(p_presets):
                workshop_dirs.add(p_presets)

        # 2. Global search fallback (limited depth to avoid long scans)
        if not workshop_dirs:
            try:
                # Find "431960" directory in common locations if quick check failed
                search_roots = [os.path.expanduser("~")]
                cmd = ["find"] + search_roots + ["-maxdepth", "6", "-type", "d", "-name", "431960"]
                result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if os.path.isdir(line):
                            workshop_dirs.add(line)
            except Exception as e:
                print(f"Deep scan error: {e}")

        wallpapers = []
        seen = set()
        
        for w_dir in workshop_dirs:
            try:
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
            
        return wallpapers

    def scan_finished(self, wallpapers):
        self.list_wallpapers.clear()
        wallpapers.sort(key=lambda x: x["title"].lower())
        for w in wallpapers:
            item = QListWidgetItem(w["title"])
            item.setData(Qt.ItemDataRole.UserRole, w)
            self.list_wallpapers.addItem(item)
        self.btn_scan.setEnabled(True)
        self.status_bar.showMessage(self._("status_local_wallpapers_found").format(count=len(wallpapers)))

    def on_wallpaper_selected(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        self.wp_id_input.setText(data["id"])
        
        self.lbl_preview.setGraphicsEffect(None)
        
        if data.get("preview"):
            path = os.path.join(data["path"], data["preview"])
            if os.path.isfile(path):
                pixmap = QPixmap(path)
                scaled = pixmap.scaled(QSize(480, 360), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.lbl_preview.setPixmap(scaled)
                self.lbl_preview.setFixedSize(scaled.size())
                
                try:
                    img = scaled.toImage()
                    small = img.scaled(1, 1, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    avg_color = small.pixelColor(0, 0)
                    
                    effect = QGraphicsDropShadowEffect()
                    effect.setBlurRadius(120)
                    effect.setColor(avg_color)
                    effect.setOffset(0, 0)
                    self.lbl_preview.setGraphicsEffect(effect)
                except: pass
            else:
                self.lbl_preview.setFixedSize(480, 360)
                self.lbl_preview.setText(self._("preview_file_not_found"))
        else:
            self.lbl_preview.setFixedSize(480, 360)
            self.lbl_preview.setText(self._("preview_not_specified"))

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
        if scale != 'default': cmd.extend(['--scaling', scale])
        clamp = self.combo_clamp.currentText()
        if clamp != 'clamp': cmd.extend(['--clamp', clamp])
        props = self.input_props.text()
        if props:
             for prop in props.split(): cmd.extend(['--set-property', prop])
        custom_args = self.input_custom_args.text()
        if custom_args:
             for arg in custom_args.split(): cmd.append(arg)
        self.stop_wallpapers()
        try:
            subprocess.Popen(cmd)
            self.status_bar.showMessage(self._("status_command_launched"))
            self.save_config()
        except Exception as e:
            self.status_bar.showMessage(f"Error: {e}")

    def stop_wallpapers(self):
        try:
            subprocess.run(['pkill', '-f', 'linux-wallpaperengine'], stderr=subprocess.DEVNULL)
            self.status_bar.showMessage(self._("status_all_stopped"))
        except Exception as e:
            self.status_bar.showMessage(f"Error stopping: {e}")

    def restore_last_wallpaper(self):
        c = self.config.get("last_wallpaper", {})
        if not c: return
        self.wp_id_input.setText(c.get("background_id", ""))
        self.screen_combo.setCurrentText(c.get("screen", ""))
        self.chk_silent.setChecked(c.get("silent", False))
        self.slider_volume.setValue(c.get("volume", 15))
        self.input_custom_args.setText(c.get("custom_args", ""))
        self.chk_windowed_mode.setChecked(c.get("windowed_mode", False))
        self.run_wallpaper()

    def detect_screens(self):
        screens = []
        try:
            res = subprocess.run(['xrandr', '--query'], capture_output=True, text=True)
            # Regex to match: Name connected [primary] WxH+X+Y ...
            # Group 1: Name, Group 2: W, Group 3: H, Group 4: X, Group 5: Y
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
            print(f"Screen detection error: {e}")
            
        if not screens:
            screens = [{"name": "eDP-1", "w": "1920", "h": "1080", "x": "0", "y": "0"}]
            
        return screens

    def load_config_data(self):
        self.config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: self.config = json.load(f)
            except: pass
    
    def apply_config_ui(self):
        self.chk_auto_restore.setChecked(self.config.get("auto_restore", False))
        self.chk_stop_exit.setChecked(self.config.get("stop_on_exit", False))

    def save_config(self):
        self.config["auto_restore"] = self.chk_auto_restore.isChecked()
        self.config["stop_on_exit"] = self.chk_stop_exit.isChecked()
        self.config["last_wallpaper"] = {
            "background_id": self.wp_id_input.text(),
            "screen": self.screen_combo.currentText(),
            "silent": self.chk_silent.isChecked(),
            "volume": self.slider_volume.value(),
            "custom_args": self.input_custom_args.text(),
            "windowed_mode": self.chk_windowed_mode.isChecked()
        }
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config, f, indent=4)

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
        if self.chk_stop_exit.isChecked():
            self.stop_wallpapers()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    window = WallpaperApp()
    window.show()
    sys.exit(app.exec())