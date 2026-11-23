"""
Abre o painel do Robô de Vagas. É o ponto de entrada do .exe (ver robo-vagas.spec).

O perfil e o banco ficam numa pasta do usuário (no Windows: %APPDATA%\\RoboVagas),
porque a pasta do .exe é temporária e some ao fechar.
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

PASTA_APP = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
PORTA = 8765
os.environ.setdefault("ROBO_VAGAS_PASTA", str(Path(os.environ.get("APPDATA") or Path.home()) / "RoboVagas"))

if __name__ == "__main__":
    from streamlit.web import cli

    print("Abrindo o Robô de Vagas no navegador... Deixe esta janela aberta enquanto usa.")
    # headless evita a pergunta de e-mail do Streamlit; o navegador é aberto aqui
    threading.Timer(4, webbrowser.open, [f"http://localhost:{PORTA}"]).start()
    sys.argv = ["streamlit", "run", str(PASTA_APP / "painel.py"),
                "--global.developmentMode=false", "--server.headless=true",
                f"--server.port={PORTA}", "--browser.gatherUsageStats=false"]
    sys.exit(cli.main())
