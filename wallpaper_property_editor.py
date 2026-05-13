# SPDX-License-Identifier: GPL-3.0-or-later
"""Parse linux-wallpaperengine --list-properties output and build Qt editors."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSlider,
    QComboBox,
    QPushButton,
    QFrame,
    QColorDialog,
    QSizePolicy,
    QStyle,
    QStyleOptionSlider,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


_PROP_HEADER = re.compile(r"^([a-zA-Z0-9_]+)\s+-\s+(.+)$")
_COMBO_LINE = re.compile(r"^(.+?)\s*->\s*(.+)$")


def _parse_num(s: str) -> Optional[float]:
    s = s.strip()
    if not s:
        return None
    try:
        if "." in s:
            return float(s)
        return float(int(s))
    except ValueError:
        return None


def parse_color_line_to_qcolor(line: str) -> Optional[QColor]:
    """Parse color from 'R: … G: … B: …' or 'r,g,b[,a]' float lists into QColor."""
    line = (line or "").strip()
    if not line:
        return None
    parts = [p.strip() for p in line.split(",") if p.strip()]
    if len(parts) >= 3:
        try:
            rf, gf, bf = float(parts[0]), float(parts[1]), float(parts[2])
            af = float(parts[3]) if len(parts) > 3 else 1.0
            return QColor.fromRgbF(rf, gf, bf, af)
        except (ValueError, TypeError):
            pass
    try:
        r = re.search(r"R:\s*([0-9.+-eE]+)", line, re.I)
        g = re.search(r"G:\s*([0-9.+-eE]+)", line, re.I)
        b = re.search(r"B:\s*([0-9.+-eE]+)", line, re.I)
        a = re.search(r"A:\s*([0-9.+-eE]+)", line, re.I)
        if not (r and g and b):
            return None
        rf, gf, bf = float(r.group(1)), float(g.group(1)), float(b.group(1))
        af = float(a.group(1)) if a else 1.0
        return QColor.fromRgbF(rf, gf, bf, af)
    except (ValueError, TypeError):
        return None


def color_ui_value_to_engine_vec3(s: str, _prop_type: str = "") -> str:
    """
    linux-wallpaperengine expects vec3 colors as comma-separated floats, e.g.
    schemecolor=0.15,0.23,0.40 — not the human-readable 'R: … G: …' line from --list-properties.
    """
    s = (s or "").strip()
    if not s:
        return s
    if re.search(r"R:\s*[\d.+-eE]", s, re.I) and re.search(r"G:\s*[\d.+-eE]", s, re.I) and re.search(
        r"B:\s*[\d.+-eE]", s, re.I
    ):
        r = re.search(r"R:\s*([0-9.+-eE]+)", s, re.I)
        g = re.search(r"G:\s*([0-9.+-eE]+)", s, re.I)
        b = re.search(r"B:\s*([0-9.+-eE]+)", s, re.I)
        if r and g and b:
            return f"{r.group(1)},{g.group(1)},{b.group(1)}"
        return s
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) >= 3 and all(_parse_num(p) is not None for p in parts[:3]):
        return f"{parts[0]},{parts[1]},{parts[2]}"
    return s


def engine_vec3_csv_to_color_display(s: str) -> str:
    """Show stored engine vec3 as R/G/B/A line for the editor label."""
    s = (s or "").strip()
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) >= 3:
        try:
            r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
            a = float(parts[3]) if len(parts) > 3 else 1.0
            return f"R: {r:.5f} G: {g:.5f} B: {b:.5f} A: {a:.5f}"
        except (ValueError, TypeError):
            pass
    return s


def parse_properties_enriched(text: str) -> List[Dict[str, Any]]:
    """Parse human-readable --list-properties blocks into property definitions."""
    lines = text.splitlines()
    blocks: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    in_combo = False

    def flush():
        nonlocal cur
        if cur:
            cur.pop("_in_combo_options", None)
            blocks.append(cur)
            cur = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        m = _PROP_HEADER.match(stripped)
        if m:
            flush()
            name, typ = m.group(1), m.group(2).strip().lower()
            cur = {
                "name": name,
                "type": typ,
                "value": "",
                "description": "",
                "min": None,
                "max": None,
                "step": None,
                "options": [],
            }
            in_combo = False
            continue

        if cur is None:
            continue

        if stripped.startswith("Description:"):
            in_combo = False
            cur["description"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Value:"):
            in_combo = False
            cur["value"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Minimum value:"):
            in_combo = False
            cur["min"] = _parse_num(stripped.split(":", 1)[1])
        elif stripped.startswith("Maximum value:"):
            in_combo = False
            cur["max"] = _parse_num(stripped.split(":", 1)[1])
        elif stripped.startswith("Step:"):
            in_combo = False
            cur["step"] = _parse_num(stripped.split(":", 1)[1])
        elif "ossible values" in stripped or stripped.startswith("Possible values"):
            in_combo = True
            cur["_in_combo_options"] = True
        elif in_combo and "->" in stripped:
            cm = _COMBO_LINE.match(stripped)
            if cm:
                label, val = cm.group(1).strip(), cm.group(2).strip()
                cur["options"].append((label, val))
        elif stripped.startswith("R:") and "G:" in stripped and "B:" in stripped:
            in_combo = False
            cur["color_line"] = stripped
            if not cur.get("value"):
                cur["value"] = stripped

    flush()
    return blocks


def merge_stored_into_blocks(
    blocks: List[Dict[str, Any]],
    stored: Dict[str, Any],
) -> List[Dict[str, Any]]:
    out = []
    for b in blocks:
        nb = dict(b)
        name = nb["name"]
        if name in stored and isinstance(stored[name], dict):
            v = stored[name].get("value")
            if v is not None and str(v).strip() != "":
                nb["value"] = str(v)
        out.append(nb)
    return out


class ClickableSliderCopy(QSlider):
    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            pos = ev.pos().x()
            span = max(1, self.width() - 12)
            v = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), pos, span
            )
            self.setValue(v)
        super().mousePressEvent(ev)


class WallpaperPropsEditor(QWidget):
    """One card per property with a control suited to its type."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(12)
        self._fields: Dict[str, QWidget] = {}
        self._types: Dict[str, str] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._placeholder = QLabel()
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet("color: #888;")
        self._root.addWidget(self._placeholder)
        self._rows_widget = QWidget()
        self._rows = QVBoxLayout(self._rows_widget)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(10)
        self._root.addWidget(self._rows_widget)
        self._root.addStretch()

    def clear(self, message: str = ""):
        while self._rows.count():
            item = self._rows.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._fields.clear()
        self._types.clear()
        self._meta.clear()
        self._placeholder.setText(message)
        self._placeholder.setVisible(bool(message))

    def build_from_blocks(self, blocks: List[Dict[str, Any]]):
        self.clear("")
        self._placeholder.setVisible(False)
        if not blocks:
            return

        for b in blocks:
            name = b["name"]
            typ = (b.get("type") or "").lower()
            self._types[name] = typ
            self._meta[name] = dict(b)

            card = QFrame()
            card.setProperty("class", "Card")
            card.setStyleSheet(
                "QFrame { background-color: #252525; border: 1px solid #3A3A3A; border-radius: 8px; }"
            )
            cv = QVBoxLayout(card)
            cv.setContentsMargins(12, 10, 12, 10)
            cv.setSpacing(6)

            title = QLabel(f"<b>{name}</b> <span style='color:#666;'>({typ})</span>")
            title.setTextFormat(Qt.TextFormat.RichText)
            cv.addWidget(title)
            desc = (b.get("description") or "").strip()
            if desc:
                dl = QLabel(desc)
                dl.setWordWrap(True)
                dl.setStyleSheet("color: #A5A5A5; font-size: 11px;")
                cv.addWidget(dl)

            val = str(b.get("value", ""))

            if typ == "boolean":
                cb = QCheckBox()
                cb.setChecked(val not in ("", "0", "false", "False", "no"))
                cb.toggled.connect(lambda *_: self.changed.emit())
                self._fields[name] = cb
                cv.addWidget(cb)
            elif typ == "slider":
                mn = b.get("min")
                mx = b.get("max")
                if mn is None:
                    mn = 0.0
                if mx is None:
                    mx = 100.0
                use_float = any(
                    isinstance(x, float) and abs(x - int(x)) > 1e-9
                    for x in (mn, mx)
                    if isinstance(x, (int, float))
                )
                nv = _parse_num(val)
                if nv is None:
                    nv = float(mn)
                rng = float(mx) - float(mn)
                if rng <= 0:
                    rng = 1.0

                steps = 1000
                slider = ClickableSliderCopy(Qt.Orientation.Horizontal)
                slider.setRange(0, steps)
                pos = int((float(nv) - float(mn)) / rng * steps)
                slider.setValue(max(0, min(steps, pos)))

                lab = QLabel()
                lab.setMinimumWidth(56)
                lab.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                def mk_upd(sli, label, vmin, vmax, nsteps, is_float):
                    def upd(_v):
                        t = sli.value() / float(nsteps)
                        raw = float(vmin) + t * (float(vmax) - float(vmin))
                        if is_float:
                            label.setText(f"{raw:.4g}".rstrip("0").rstrip("."))
                        else:
                            label.setText(str(int(round(raw))))

                    return upd

                upd = mk_upd(slider, lab, mn, mx, steps, use_float)
                slider.valueChanged.connect(upd)
                slider.sliderReleased.connect(lambda: self.changed.emit())
                upd(slider.value())

                row = QWidget()
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                rl.addWidget(slider, 1)
                rl.addWidget(lab)
                self._fields[name] = slider
                self._meta[name]["_slider_label"] = lab
                self._meta[name]["_slider_min"] = mn
                self._meta[name]["_slider_max"] = mx
                self._meta[name]["_slider_steps"] = steps
                self._meta[name]["_slider_float"] = use_float
                cv.addWidget(row)
            elif typ == "combolist" and b.get("options"):
                combo = QComboBox()
                for lbl, opt_val in b["options"]:
                    combo.addItem(lbl, opt_val)
                idx = combo.findData(val)
                if idx < 0:
                    combo.insertItem(0, val or "—", val)
                    combo.setCurrentIndex(0)
                else:
                    combo.setCurrentIndex(idx)
                combo.currentIndexChanged.connect(lambda *_: self.changed.emit())
                self._fields[name] = combo
                cv.addWidget(combo)
            elif "color" in typ:
                row = QWidget()
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                btn = QPushButton("…")
                btn.setFixedWidth(36)
                disp = engine_vec3_csv_to_color_display(val) if val else ""
                lab = QLabel(disp or val or "")
                lab.setWordWrap(True)
                lab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

                def make_pick(la=lab):
                    def on_click():
                        qc = parse_color_line_to_qcolor(la.text()) or QColor(64, 64, 128, 255)
                        q = QColorDialog.getColor(initial=qc, parent=self)
                        if q.isValid():
                            r, g, b, a = q.redF(), q.greenF(), q.blueF(), q.alphaF()
                            la.setText(f"R: {r:.5f} G: {g:.5f} B: {b:.5f} A: {a:.5f}")
                            self.changed.emit()

                    return on_click

                btn.clicked.connect(make_pick())
                rl.addWidget(btn)
                rl.addWidget(lab, 1)
                self._fields[name] = lab
                cv.addWidget(row)
            else:
                le = QLineEdit(val)
                le.textChanged.connect(lambda *_: self.changed.emit())
                self._fields[name] = le
                cv.addWidget(le)

            self._rows.addWidget(card)

    def collect_values(self) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        for name, widget in self._fields.items():
            typ = self._types.get(name, "")
            meta = self._meta.get(name, {})
            val = ""
            sep = "="

            if typ == "boolean" and isinstance(widget, QCheckBox):
                val = "1" if widget.isChecked() else "0"
            elif typ == "slider" and isinstance(widget, ClickableSliderCopy):
                mn = float(meta.get("_slider_min", 0))
                mx = float(meta.get("_slider_max", 100))
                steps = int(meta.get("_slider_steps", 1000))
                use_float = bool(meta.get("_slider_float"))
                t = widget.value() / float(steps)
                raw = mn + t * (mx - mn)
                if use_float:
                    val = f"{raw:.6f}".rstrip("0").rstrip(".")
                else:
                    val = str(int(round(raw)))
            elif typ == "combolist" and isinstance(widget, QComboBox):
                d = widget.currentData()
                val = str(d) if d is not None else widget.currentText()
            elif "color" in typ and isinstance(widget, QLabel):
                val = color_ui_value_to_engine_vec3(widget.text(), typ)
            elif isinstance(widget, QLabel):
                val = widget.text().strip()
            elif isinstance(widget, QLineEdit):
                val = widget.text().strip()

            out[name] = {"value": val, "sep": sep, "type": typ}
        return out
