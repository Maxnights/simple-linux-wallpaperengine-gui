{ pkgs ? import <nixpkgs> { } }:

let
  pyEnv = pkgs.python3.withPackages (ps: with ps; [
    pyqt6
    pillow
    watchdog
    packaging
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pyEnv
    pkgs.linux-wallpaperengine
    pkgs.libxcb-cursor
    pkgs.libGL
    pkgs.libxkbcommon
    pkgs.wayland
  ];

  shellHook = ''
    # Expose system GPU drivers (mesa / nvidia) so Qt can find them at runtime
    export LD_LIBRARY_PATH="/run/opengl-driver/lib:${pkgs.libGL}/lib:${pkgs.wayland}/lib:${pkgs.libxkbcommon}/lib:$LD_LIBRARY_PATH"

    # Auto-detect display server
    if [ -n "$WAYLAND_DISPLAY" ]; then
      export QT_QPA_PLATFORM=wayland
    elif [ -n "$DISPLAY" ]; then
      export QT_QPA_PLATFORM=xcb
    fi

    echo "==> debug shell ready"
    echo "    python wallpaper_gui.py"
  '';
}
