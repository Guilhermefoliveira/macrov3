# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files # collect_data_files pode ser útil
import os
import sys # Necessário para sys.platform

# --- Configurações ---
app_name = 'MacroManager'
main_script = 'macrov3.py' # <<<< VERIFIQUE SE ESTE É O NOME CORRETO DO SEU SCRIPT PYTHON PRINCIPAL
icon_path = 'resources/icon.ico' # <<<< COLOQUE O CAMINHO CORRETO PARA SEU ÍCONE .ICO (ex: 'icon.ico' se estiver na raiz)
debug_build = False # MUDE PARA True PARA VER O CONSOLE AO TESTAR O .EXE (útil para erros)

# --- Coleta Automática de Dados e Binários ---
datas = []
binaries = []
hiddenimports = []

# Pacotes para os quais tentaremos coletar tudo
packages_to_collect_all = [
    'customtkinter',
    'PIL',
    'pystray',
    'keyboard',
    'pyperclip',
    'psutil',
    'screeninfo',
    'darkdetect'
]

print("INFO: Iniciando coleta de dependências...")
for package_name in packages_to_collect_all:
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name)
        datas.extend(pkg_datas)
        binaries.extend(pkg_binaries)
        hiddenimports.extend(pkg_hiddenimports)
        print(f"INFO: Coletado para {package_name}. Dados: {len(pkg_datas)}, Binários: {len(pkg_binaries)}, Imports Ocultos: {len(pkg_hiddenimports)}")
    except Exception as e:
        print(f"AVISO: Falha ao usar collect_all para {package_name}: {e}. Adicionando nome do pacote a hiddenimports.")
        if package_name not in hiddenimports:
            hiddenimports.append(package_name)

# --- Arquivos de Dados Específicos do Projeto ---
# Sintaxe: ('caminho/do/arquivo_ou_pasta_no_seu_PC', 'caminho_relativo_dentro_do_bundle')
project_datas_to_add = [
    ('expansions.json', '.'),  # Copia expansions.json para a raiz do bundle
    ('azure.tcl', '.'),        # Copia seu azure.tcl para a raiz do bundle
                               # (Assumindo que está no mesmo dir que o .spec)
    ('theme', 'theme')         # Copia a PASTA 'theme' INTEIRA e seu conteúdo recursivamente
                               # para uma pasta 'theme' dentro do bundle.
                               # (Assumindo que a pasta 'theme' está no mesmo dir que o .spec)
]

# Adicionar fontes se _desenhar_icone depender delas e não forem 100% padrão
# Exemplo: se 'arial.ttf' estiver na raiz do seu projeto:
# project_datas_to_add.append(('arial.ttf', '.'))
# Se estiver em uma subpasta 'fonts':
# project_datas_to_add.append(('fonts/arial.ttf', 'fonts'))

print("INFO: Adicionando arquivos de dados do projeto...")
for src_path, dest_folder_in_bundle in project_datas_to_add:
    if os.path.exists(src_path):
        datas.append((src_path, dest_folder_in_bundle))
        print(f"INFO: Adicionado aos dados: '{src_path}' -> '{dest_folder_in_bundle}'")
    else:
        print(f"AVISO CRÍTICO: Arquivo/Pasta de dados do projeto NÃO ENCONTRADO: '{src_path}'. O executável pode falhar!")

# --- Hidden Imports Adicionais ---
# Módulos que o PyInstaller pode ter dificuldade em encontrar.
additional_hiddenimports = [
    'PIL._tkinter_finder', # Importante para Pillow com Tkinter
    'ctypes.wintypes',
    # 'pystray._win32', # collect_all('pystray') geralmente pega isso, mas se não, adicione.
    'customtkinter.windows.widgets.ctk_scaling_tracker', # Muito importante para CTk
    # Adicionar outros se o executável reclamar de 'ModuleNotFound'
]
# Adicionar apenas se ainda não estiverem na lista (para evitar duplicatas de collect_all)
for imp in additional_hiddenimports:
    if imp not in hiddenimports:
        hiddenimports.append(imp)

# Remover duplicatas de hiddenimports, se houver
hiddenimports = list(set(hiddenimports))
print(f"INFO: Imports ocultos finais: {hiddenimports}")


# --- Configuração da Análise ---
a = Analysis(
    [main_script],
    pathex=[], # PyInstaller geralmente encontra o diretório do script automaticamente
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[], # Diretórios para seus próprios hooks do PyInstaller (geralmente não necessário)
    hooksconfig={},
    runtime_hooks=[], # Scripts para rodar antes da sua aplicação (geralmente não necessário)
    excludes=[], # Bibliotecas para excluir explicitamente (use com cuidado)
    win_no_prefer_redirects=False,
    win_private_assemblies=False, # Não incluir manifestos lado-a-lado privados (geralmente False)
    cipher=None, # Para criptografar o bytecode (opcional, pode ser detectado por antivírus)
    noarchive=False # False para criar um arquivo de archive dentro do .exe ou da pasta
)

# --- Criação do PYZ (Python Zipped Archive) ---
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# --- Configuração do Executável ---
final_console_setting = True if debug_build else False

final_icon_path = None
if os.path.exists(icon_path):
    final_icon_path = icon_path
elif os.path.exists('icon.ico'): # Tenta 'icon.ico' na raiz se o path configurado falhar
    final_icon_path = 'icon.ico'

if final_icon_path:
    print(f"INFO: Usando ícone para o executável: {final_icon_path}")
else:
    print("AVISO: Ícone do executável não encontrado. Usando ícone padrão do PyInstaller.")

exe_options = {
    'name': app_name,
    'debug': debug_build,
    'bootloader_ignore_signals': False,
    'strip': False, # True para remover símbolos, pode reduzir tamanho mas dificulta debug
    'upx': True,    # True para usar UPX (precisa estar instalado e no PATH)
    'upx_exclude': [],
    'runtime_tmpdir': None, # PyInstaller decide onde extrair (para --onefile)
    'console': final_console_setting,
    'disable_windowed_traceback': False,
    'target_arch': None, # None para auto-detectar (ex: 'x86_64')
    'codesign_identity': None,
    'entitlements_file': None,
    'icon': final_icon_path
}

# Para informações de versão no Windows (opcional)
# version_file_path = 'file_version_info.txt' # Você precisa criar este arquivo
# if os.path.exists(version_file_path):
#     exe_options['version'] = version_file_path

# Modo Diretório (Padrão e Recomendado para Início)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries, # Incluir binários coletados
    a.zipfiles, # Incluir arquivos zipados (PYZ)
    a.datas,    # Incluir dados coletados
    **exe_options # Passar as opções como keyword arguments
)

# Modo Arquivo Único (Alternativa - descomente a seção COLLECT abaixo e comente o EXE acima)
# Lembre-se que é mais fácil controlar onefile/onedir pela linha de comando.
# Para forçar onefile via spec, a estrutura é um pouco diferente, geralmente envolvendo
# um COLLECT que empacota o EXE.
# Para buildar como --onefile, o mais simples é usar o comando: pyinstaller --onefile macrov3.spec

# Se quiser controlar o --onefile explicitamente no .spec, você faria algo como:
# _exe_obj = EXE(pyz, a.scripts, [], name=app_name, ... outras_opcoes_sem_datas_e_binaries ...)
# coll = COLLECT(
#     _exe_obj,
#     a.binaries,
#     a.datas,
#     a.zipfiles, # Adicionado
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name=app_name # Nome da pasta (se onedir) ou do exe (se onefile é implicitamente ativado por não ter exe separado)
# )
# Para simplificar, vamos manter o EXE acima (onedir por padrão) e você usa a flag --onefile
# na linha de comando se desejar.