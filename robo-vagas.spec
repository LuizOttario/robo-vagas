# Gera o executável:  pyinstaller robo-vagas.spec
# Sai em dist/RoboVagas.exe (no Windows) ou dist/RoboVagas (no Linux).
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

sys.path.insert(0, SPECPATH)  # sem isso o collect_submodules não acha o pacote vagas
datas = [("painel.py", "."), ("config.exemplo.toml", ".")]
binaries = []
# O painel é rodado pelo Streamlit como script, então o PyInstaller não enxerga os imports dele sozinho
hiddenimports = collect_submodules("vagas")
for pacote in ["streamlit", "plotly", "pypdf", "selenium"]:
    d, b, h = collect_all(pacote)
    datas += d
    binaries += b
    hiddenimports += h
datas += copy_metadata("streamlit")

a = Analysis(["iniciar.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="RoboVagas", console=True)
