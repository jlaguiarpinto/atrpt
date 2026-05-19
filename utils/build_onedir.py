# atrpt\utils\build_onedir.py
# Uso:
#   python build_onedir.py secretaria
#   python build_onedir.py ponto
#   python build_onedir.py pessoas
#   python build_onedir.py aprovisionamento

import shutil
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

ROOT = Path(__file__).parent.parent  # assume na raiz do projeto
SPEC_DIR = ROOT / "spec"
MODULOS = {
    "aprovisionamento": {
        "spec": SPEC_DIR/"onedir_aprovisionamento.spec",
        "deploy": Path(r"G:\deploy\Aprovisionamento"),
    },
    "pessoas": {
        "spec": SPEC_DIR/"onedir_pessoas.spec",
        "deploy": Path(r"G:\deploy\Pessoas"),
    },
    "ponto": {
        "spec": SPEC_DIR/"onedir_ponto.spec",
        "deploy": Path(r"G:\deploy\Ponto"),
    },
    "secretaria": {
        "spec": SPEC_DIR/"onedir_secretaria.spec",
        "deploy": Path(r"G:\deploy\Secretaria"),
    },
    "fornecedores": {
        "spec": SPEC_DIR/"onedir_fornecedores.spec",
        "deploy": Path(r"G:\deploy\Fornecedores"),
    },
    "correio": {
        "spec": SPEC_DIR/"onedir_correio.spec",
        "deploy": Path(r"G:\deploy\Correio"),
    },
}

# ─────────────────────────────────────────────
# BUILD
# ─────────────────────────────────────────────

def run_pyinstaller(spec: str):
    modulo = Path(spec).stem.replace("onedir_", "")
    print(f"\n▶ A compilar {spec}...\n")

    # limpar build anterior
    build_dir = ROOT / "build" / modulo
    dist_dir = ROOT / "dist" / modulo

    for d in (build_dir, dist_dir):
        if d.exists():
            shutil.rmtree(d)

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec)],
        cwd=ROOT,
    )

    if result.returncode != 0:
        print("\n✖ PyInstaller falhou.")
        sys.exit(1)

    print("\n✔ Build concluído.")

# ─────────────────────────────────────────────
# DEPLOY
# ─────────────────────────────────────────────

def deploy_onedir(modulo: str, deploy_dir: Path):
    origem = ROOT / "dist" / modulo

    if not origem.exists():
        print(f"\n✖ Pasta não encontrada: {origem}")
        sys.exit(1)

    destino = deploy_dir / modulo

    print(f"\n▶ Deploy:")
    print(f"   origem : {origem}")
    print(f"   destino: {destino}")

    # remover destino antigo
    if destino.exists():
        shutil.rmtree(destino)

    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(origem, destino)

    print(f"\n✔ Deploy concluído.")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("\nUso: python build_onedir.py <modulo>")
        print(f"Módulos: {', '.join(MODULOS.keys())}")
        sys.exit(1)

    modulo = sys.argv[1]

    if modulo not in MODULOS:
        print(f"\n✖ Módulo inválido: {modulo}")
        print(f"Módulos disponíveis: {', '.join(MODULOS.keys())}")
        sys.exit(1)

    cfg = MODULOS[modulo]

    run_pyinstaller(cfg["spec"])
    deploy_onedir(modulo, cfg["deploy"])