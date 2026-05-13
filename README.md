# Simple Linux Wallpaper Engine GUI

A modern, universal GUI for [linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine).

**This fork’s repository:** [syskeyxi/simple-linux-wallpaperengine-gui-MULTI-MONITOR](https://github.com/syskeyxi/simple-linux-wallpaperengine-gui-MULTI-MONITOR)

I encountered various problems on GNOME and KDE. I recommend using Linux Wallpaper Engine on tiling window managers such as i3, hyprland, and bspwm. For KDE, I recommend trying this [plugin](https://github.com/catsout/wallpaper-engine-kde-plugin#build-and-install)

## About this fork

This repo is **forked from** [Maxnights/simple-linux-wallpaperengine-gui](https://github.com/Maxnights/simple-linux-wallpaperengine-gui) with a few changes added on top:

- **Multi-monitor support** — enable outputs in a table, **per-output wallpaper ID**, and **per-output scaling** (default, stretch, fit, fill) and **clamp / border modes** (clamp, border, repeat), passed through to the backend as documented for `linux-wallpaperengine`.
- **Wallpaper settings** section (**UNSTABLE**) — load `--list-properties` from the engine and edit values in a form instead of raw JSON where possible; save and apply per wallpaper ID.
- **FPS slider** — shows the current FPS value next to the slider so you are not guessing.
- **Library shortcut** — **Set wallpaper (all screens)** applies the selected library wallpaper ID to every **enabled** monitor row and applies.

**Testing:** I have **only tested this on KDE Plasma 6**. It might work on other desktops or display setups; I hope it does, but I have not verified them.

**Support:** I am **not offering support** for this project — I mostly made it for myself. Someone else might still find it useful; use it at your own risk.

## Screenshots
<img width="2560" height="1440" alt="Pasted image" src="https://github.com/user-attachments/assets/15c6dc78-f51b-4c1b-aeb1-f2bad88bc898" />
<img width="2560" height="1440" alt="Pasted image (2)" src="https://github.com/user-attachments/assets/d36990b8-641a-44fe-b4ff-ca582d9494da" />



## Installation (Arch Linux / Manjaro)

This fork ships a PKGBUILD under [`packaging/aur/PKGBUILD`](packaging/aur/PKGBUILD) (`pkgname`: **`simple-linux-wallpaperengine-gui-multi-monitor-git`**). It clones from [syskeyxi/simple-linux-wallpaperengine-gui-MULTI-MONITOR](https://github.com/syskeyxi/simple-linux-wallpaperengine-gui-MULTI-MONITOR).

After you publish that PKGBUILD to the AUR (or install it locally with `makepkg`), helpers such as:

```bash
yay -S simple-linux-wallpaperengine-gui-multi-monitor-git
```

will pull the backend (`linux-wallpaperengine`) via `depends` like the original package.

The original upstream package name was `simple-linux-wallpaperengine-gui-git` ([Maxnights](https://github.com/Maxnights/simple-linux-wallpaperengine-gui)); this fork uses a different name so it can coexist in packaging until you replace it deliberately.

## Installation (Nix)

Flake Install (Recommended)

Add to your flake inputs,
```nix
inputs = {
  simple-wallpaper-engine = {
    url = "github:syskeyxi/simple-linux-wallpaperengine-gui-MULTI-MONITOR";
    inputs = {
      nixpkgs.follows = "nixpkgs";
      home-manager.follows = "home-manager";
    };
  };
  # ...
}

```

Then in your home manager config, import the home manager module and enable the program.
```nix
{inputs, ...}: {
  imports = [inputs.simple-wallpaper-engine.homeManagerModules.default];
  # ...
  programs.simple-wallpaper-engine.enable = true;
}

```

Imperative Install

```bash
nix profile install github:syskeyxi/simple-linux-wallpaperengine-gui-MULTI-MONITOR
```


## 1. Prerequisites (The Backend)
This is just a GUI. You **must** install the core backend engine first. If you installed my GUI from AUR, then the main backend engine from Almamu(https://github.com/Almamu/linux-wallpaperengine) comes as a dependency. So you can skip this step.

### Arch / Manjaro
```bash
yay -S linux-wallpaperengine
```

### Debian / Ubuntu / Fedora (Build from Source)
Detailed instructions are [here](https://github.com/Almamu/linux-wallpaperengine#compiling), but essentially:
```bash
# Install build tools (Debian/Ubuntu)
sudo apt install build-essential cmake libx11-dev libxrandr-dev liblz4-dev

# Install build tools (Fedora)
sudo dnf install cmake gcc-c++ libX11-devel libXrandr-devel lz4-devel

# Clone & Build
git clone https://github.com/Almamu/linux-wallpaperengine.git
cd linux-wallpaperengine && mkdir build && cd build
cmake ..
make
sudo make install
```

## 2. Installation (The GUI)

This one-step script installs Python dependencies, and sets up the app.

```bash
git clone https://github.com/syskeyxi/simple-linux-wallpaperengine-gui-MULTI-MONITOR.git
cd simple-linux-wallpaperengine-gui-MULTI-MONITOR
chmod +x install.sh
./install.sh
```

## 3. Usage

Start the application:

```bash
./run_gui.sh
```


## Troubleshooting

**"linux-wallpaperengine not found"**
Ensure you completed Step 1. Run `linux-wallpaperengine --help` in a terminal to verify it's installed globally.

**Wallpapers not showing?**
Go to the **Library** tab and click **Scan Local Wallpapers**. The app searches standard paths including `~/.local/share/Steam`, `~/.var/app/com.valvesoftware.Steam`, and `~/snap/steam`.



