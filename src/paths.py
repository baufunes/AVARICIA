"""
Resuelve rutas de archivos de forma que funcionen tanto corriendo el
proyecto normalmente (python main.py / python gui.py) como empaquetado
como app nativa con PyInstaller.

Por qué hace falta esto: cuando PyInstaller empaqueta la app, "desde dónde
se ejecuta" deja de ser la carpeta del proyecto — así que rutas relativas
como "data/historical_matches.csv" se rompen si no las resolvemos bien.

Mantenemos los datos (caché, historial, gráficos generados) en una carpeta
al lado del .app (no adentro), para que sean fáciles de encontrar y editar
sin tener que abrir el paquete de la app.
"""
import os
import sys


def is_frozen() -> bool:
    """True si estamos corriendo como app empaquetada con PyInstaller."""
    return getattr(sys, "frozen", False)


def _project_root() -> str:
    """Raíz del proyecto en modo desarrollo (dos niveles arriba de este archivo)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _app_bundle_folder() -> str:
    """
    Carpeta que CONTIENE el .app (por ejemplo, tu Desktop o dist/), en modo
    empaquetado. sys.executable en una app de Mac vive en
    AppName.app/Contents/MacOS/AppName, así que subimos 3 niveles.
    """
    return os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "..", ".."))


def base_dir() -> str:
    """Carpeta base para buscar/guardar data/, outputs/ y .env."""
    return _app_bundle_folder() if is_frozen() else _project_root()


def path(*relative_parts) -> str:
    """Arma una ruta absoluta a partir de la carpeta base del proyecto/app."""
    full_path = os.path.join(base_dir(), *relative_parts)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    return full_path
