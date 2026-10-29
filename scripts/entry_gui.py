"""
Frozen entry point for the GUI build (PyInstaller / Nuitka).

Why a separate launcher: a packaging tool treats the file it is given as the
``__main__`` script, whose ``__file__`` sits at the bundle root.  ``app.py``
locates the built frontend as ``Path(__file__).parent / "frontend" / "dist"``,
so it has to be imported as part of the ``updater.gui`` package for that path -
and the matching ``--add-data`` destination - to stay correct in the bundle.

See https://pyinstaller.org/en/stable/runtime-information.html ("__file__" and
the package-mirroring rule for ``--add-data``).
"""

from updater.gui.app import main

if __name__ == "__main__":
    main()
