{
  pkgs ? import <nixpkgs> {system = "x86_64-linux";},
  lib,
  makeWrapper,
  copyDesktopItems,
}:
pkgs.stdenv.mkDerivation rec {
  name = "simple-wallpaper-engine";
  src = ./../..;

  nativeBuildInputs = [makeWrapper copyDesktopItems];

  propagatedBuildInputs = with pkgs; [
    (python3.withPackages (pythonPackages:
      with pythonPackages; [
        pyqt6
        pillow
        packaging
        watchdog
      ]))
    linux-wallpaperengine
    libxcb-cursor
  ];

  installPhase = ''
    mkdir -p $out/bin
    cp -r ./locales $out/bin
    install -Dm755 ./wallpaper_gui.py $out/bin/simple-wallpaper-engine
    install -Dm644 ./process_manager.py $out/bin/process_manager.py
    wrapProgram $out/bin/simple-wallpaper-engine \
      --prefix PATH : ${lib.makeBinPath propagatedBuildInputs}
    mkdir -p $out/share/applications
    install -Dm644 ./simple-wallpaper-engine.desktop $out/share/applications/simple-wallpaper-engine.desktop
    install -Dm644 ./simple-wallpaper-engine-autostart.desktop $out/share/applications/simple-wallpaper-engine-autostart.desktop
  '';

  meta = {
    description = "Simple Linux Wallpaper Engine GUI";
    homepage = "https://github.com/syskeyxi/simple-linux-wallpaperengine-gui-MULTI-MONITOR";
    license = lib.licenses.gpl3;
    platforms = ["x86_64-linux"];
    mainProgram = "simple-wallpaper-engine";
    desktopFileName = "simple-wallpaper-engine.desktop";
  };
}
