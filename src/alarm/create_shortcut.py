"""Script pour créer les raccourcis Windows"""
import os
import sys


def _ensure_ico(assets_dir: str) -> str:
    """Convert logo.jpeg → icon.ico if needed, return path to .ico."""
    ico_path = os.path.join(assets_dir, "icon.ico")
    if os.path.exists(ico_path):
        return ico_path
    jpeg_path = os.path.join(assets_dir, "logo.jpeg")
    if not os.path.exists(jpeg_path):
        return ""
    try:
        from PIL import Image
        img = Image.open(jpeg_path).convert("RGBA")
        img = img.resize((256, 256), Image.LANCZOS)
        img.save(ico_path, format="ICO", sizes=[(256, 256), (48, 48), (32, 32), (16, 16)])
        print(f"    [OK] icon.ico généré depuis logo.jpeg")
    except Exception as e:
        print(f"    [!] Impossible de convertir logo.jpeg → ico : {e}")
        return ""
    return ico_path


def create_shortcuts():
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("    [!] winshell/pywin32 non installé")
        return False

    # Remonter à la racine du projet (src/alarm/create_shortcut.py → racine)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(script_dir)
    project_dir = os.path.dirname(src_dir)

    # Trouver pythonw.exe
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable

    main_script = os.path.join(src_dir, "app.py")
    assets_dir = os.path.join(project_dir, "assets")
    icon_path = _ensure_ico(assets_dir)

    print(f"    Project: {project_dir}")
    print(f"    Main: {main_script} (exists: {os.path.exists(main_script)})")
    print(f"    Icon: {icon_path} (exists: {os.path.exists(icon_path)})")

    try:
        shell = Dispatch("WScript.Shell")

        # Raccourci Bureau
        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, "M2O.lnk")
        print(f"    Desktop: {shortcut_path}")

        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = pythonw
        shortcut.Arguments = f'"{main_script}"'
        shortcut.WorkingDirectory = project_dir
        shortcut.Description = "M2O — Option Strategy"
        if icon_path and os.path.exists(icon_path):
            shortcut.IconLocation = f"{icon_path},0"
        shortcut.save()
        print("    [OK] Raccourci Bureau créé")

        # Raccourci Menu Démarrer
        start_menu = winshell.start_menu()
        shortcut_path2 = os.path.join(start_menu, "Programs", "M2O.lnk")
        shortcut2 = shell.CreateShortCut(shortcut_path2)
        shortcut2.Targetpath = pythonw
        shortcut2.Arguments = f'"{main_script}"'
        shortcut2.WorkingDirectory = project_dir
        shortcut2.Description = "M2O — Option Strategy"
        if icon_path and os.path.exists(icon_path):
            shortcut2.IconLocation = f"{icon_path},0"
        shortcut2.save()
        print("    [OK] Raccourci Menu Démarrer créé")

        return True
    except Exception as e:
        print(f"    [!] Erreur: {e}")
        return False

if __name__ == "__main__":
    create_shortcuts()
