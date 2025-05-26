import tkinter as tk
from tkinter import messagebox, Toplevel
from tkinter import ttk
import tkinter.font as tkfont
import keyboard
import pyperclip
import time
import json
import os
import shutil
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw, ImageFont
import sys
import atexit
import customtkinter as ctk
from customtkinter import CTkFont
import threading
import psutil
from typing import Dict, Optional, Any
from collections import defaultdict
from screeninfo import get_monitors
from ctypes import windll, c_int, c_uint, byref, sizeof, c_void_p
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[
        logging.FileHandler('macro_manager.log', mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def get_user_data_dir(app_name="MacroManagerV3"):
    if sys.platform == "win32":
        path = os.path.join(os.getenv('APPDATA', os.path.expanduser('~')), app_name)
    elif sys.platform == "darwin":
        path = os.path.join(os.path.expanduser('~/Library/Application Support'), app_name)
    else:
        config_home = os.getenv('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
        path = os.path.join(config_home, app_name)
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.info(f"User data directory created/ensured at: {path}")
    except OSError as e:
        logger.error(f"Could not create user data directory {path}: {e}. Falling back to CWD.")
        path = os.path.join(os.getcwd(), app_name)
        try:
            if not os.path.exists(path):
                 os.makedirs(path, exist_ok=True)
            logger.info(f"Using fallback user data directory at: {path}")
        except Exception as e_fallback_create:
            logger.critical(f"Failed to create even fallback CWD data directory {path}: {e_fallback_create}")
            path = os.getcwd()
    return path

def is_admin():
    if os.name == 'nt':
        try:
            return windll.shell32.IsUserAnAdmin() != 0
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
    return True

class WindowsAPI:
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_SYSTEMBACKDROP_TYPE = 38

    @staticmethod
    def apply_window_style(root: tk.Tk) -> None:
        if os.name != 'nt': return
        try:
            version = sys.getwindowsversion()
            use_mica = version.major >= 10 and version.build >= 22523
            set_window_attribute = windll.dwmapi.DwmSetWindowAttribute
            hwnd = c_void_p(root.winfo_id())
            # Usar 1 para modo claro, 2 para modo escuro (se o sistema estiver em modo escuro)
            # Ou sempre 2 se o tema do app for sempre escuro.
            # CustomTkinter lida com a aparência do app, isso é mais para a barra de título nativa.
            current_ctk_mode = ctk.get_appearance_mode()
            value_dark_mode = c_int(2 if current_ctk_mode == "Dark" else 1) # 0 = off, 1 = on (light), 2 = on (dark) - requer app awareness

            # Para forçar o modo escuro na barra de título se o tema do app for escuro:
            if current_ctk_mode == "Dark":
                 value_dark_mode = c_int(2) # DWMWA_USE_IMMERSIVE_DARK_MODE = 20, value 2 = Force Dark
            else:
                 value_dark_mode = c_int(0) # Default (ou 1 se quiser forçar light)

            set_window_attribute(hwnd, WindowsAPI.DWMWA_USE_IMMERSIVE_DARK_MODE, byref(value_dark_mode), sizeof(value_dark_mode))

            if use_mica: # Mica/Acrylic effects
                # 2 para Mica (default), 3 para Acrylic, 4 para Mica Tabbed
                # Estes valores podem variar e o efeito depende da versão do Windows 11
                value_backdrop = c_int(2) # DWMSBT_MAINWINDOW ou DWMSBT_AUTO
                if current_ctk_mode == "Dark":
                    value_backdrop = c_int(2) # Tentar Mica normal
                else:
                    value_backdrop = c_int(3) # Tentar Acrylic para tema claro (ou Mica normal)

                # Para maior compatibilidade, pode ser melhor usar 0 (desabilitado) ou 1 (automático)
                # ou um valor como 4 (DWMSBT_TABBEDWINDOW) que é mais sutil.
                # value_backdrop = c_int(4)
                set_window_attribute(hwnd, WindowsAPI.DWMWA_SYSTEMBACKDROP_TYPE, byref(value_backdrop), sizeof(value_backdrop))
        except Exception as e: logger.error(f"Error applying Windows API window style: {e}")


def configurar_tema(root: tk.Tk) -> None:
    try: logger.info("Tk scaling call has been commented out/skipped in configurar_tema.")
    except Exception as e: logger.warning(f"Could not set Tk scaling (or call was already commented out): {e}")

    if hasattr(sys, '_MEIPASS'): base_path = sys._MEIPASS
    else: base_path = os.path.dirname(os.path.abspath(__file__))
    theme_package_name = 'azure'
    possible_theme_package_base_paths = [ base_path, os.path.join(base_path, 'libs'), os.path.dirname(base_path) ]
    tcl_auto_path_to_add = None
    for p_path in possible_theme_package_base_paths:
        if os.path.isdir(os.path.join(p_path, 'theme')) and os.path.exists(os.path.join(p_path, 'theme', 'pkgIndex.tcl')):
            tcl_auto_path_to_add = p_path; logger.info(f"Found Azure theme structure with 'theme' folder in: {tcl_auto_path_to_add}"); break
        if os.path.basename(p_path) == 'theme' and os.path.exists(os.path.join(p_path, 'pkgIndex.tcl')):
            tcl_auto_path_to_add = os.path.dirname(p_path); logger.info(f"Found Azure theme structure where base_path pointed into 'theme'. Auto_path set to parent: {tcl_auto_path_to_add}"); break
        if os.path.exists(os.path.join(p_path, f'{theme_package_name}.tcl')) and os.path.isdir(os.path.join(p_path, 'theme')) and os.path.exists(os.path.join(p_path, 'theme', 'pkgIndex.tcl')):
            tcl_auto_path_to_add = p_path; logger.info(f"Found {theme_package_name}.tcl and 'theme' subfolder in: {tcl_auto_path_to_add}"); break
    if not tcl_auto_path_to_add: tcl_auto_path_to_add = base_path; logger.warning(f"Could not definitively locate Azure theme structure. Defaulting Tcl auto_path to: {tcl_auto_path_to_add}")
    logger.info(f"Adding to Tcl auto_path: {tcl_auto_path_to_add}")
    try: root.tk.call('lappend', 'auto_path', tcl_auto_path_to_add)
    except tk.TclError as e:
        logger.error(f"Failed to lappend to Tcl auto_path: {e}"); ctk.set_default_color_theme("blue"); logger.info("Falling back to default CustomTkinter theme as Tcl auto_path configuration failed.")
        default_font_tuple = ('Segoe UI', 10); root.option_add('*Font', default_font_tuple); style = ttk.Style(root)
        style.configure('Treeview', rowheight=28, font=default_font_tuple); style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        if os.name == 'nt': WindowsAPI.apply_window_style(root); return
    try:
        logger.info(f"Attempting to 'package require {theme_package_name}'")
        root.tk.call('package', 'require', theme_package_name)
        root.tk.call('set_theme', ctk.get_appearance_mode().lower())
        logger.info(f"{theme_package_name.capitalize()} Tcl theme loaded and set to {ctk.get_appearance_mode().lower()}.")
    except tk.TclError as e:
        logger.error(f"Failed to load or set {theme_package_name.capitalize()} Tcl theme: {e}. Using default CustomTkinter theme.")
        ctk.set_default_color_theme("blue")
    style = ttk.Style(root); default_font_tuple = ('Segoe UI', 10); bold_font_tuple = ('Segoe UI', 10, 'bold')
    root.option_add('*Font', default_font_tuple)
    style.configure('Treeview', rowheight=28, font=default_font_tuple, borderwidth=0, relief="flat")
    style.configure('Treeview.Heading', font=bold_font_tuple, padding=(5, 5))
    style.configure('TButton', padding=6, font=default_font_tuple); style.configure('TLabel', padding=4, font=default_font_tuple)
    try:
        appearance_mode = ctk.get_appearance_mode()
        idx = 1 if appearance_mode == "Dark" else 0

        # Correção para ctk.ThemeManager.THEME_DATA (para CTk < 5.x) ou ctk.ThemeManager.get_theme() (para CTk >= 5.x)
        theme_data = {}
        if hasattr(ctk.ThemeManager, 'get_theme') and callable(ctk.ThemeManager.get_theme):
            theme_name_or_path = ctk.ThemeManager.get_currently_used_theme()
            if isinstance(theme_name_or_path, str) and os.path.exists(theme_name_or_path): # Se for um path para JSON
                with open(theme_name_or_path, 'r') as f:
                    theme_data = json.load(f)
            else: # Se for um nome de tema embutido
                theme_data = ctk.ThemeManager.get_theme(theme_name_or_path)
        elif hasattr(ctk.ThemeManager, 'THEME_DATA'): # Para versões mais antigas
            theme_data = ctk.ThemeManager.THEME_DATA

        bg_color_tuple = theme_data.get("CTkFrame", {}).get("fg_color", ("#DBDBDB", "#2B2B2B"))
        text_color_tuple = theme_data.get("CTkLabel", {}).get("text_color", ("#101010", "#DCE4EE"))

        final_bg_color = bg_color_tuple[idx] if isinstance(bg_color_tuple, (list, tuple)) and len(bg_color_tuple) > idx else bg_color_tuple
        final_text_color = text_color_tuple[idx] if isinstance(text_color_tuple, (list, tuple)) and len(text_color_tuple) > idx else text_color_tuple

        style.configure('TScrollbar', troughcolor=final_bg_color, bordercolor=final_bg_color, arrowcolor=final_text_color, background=final_bg_color)
    except Exception as e_style: logger.warning(f"Could not apply CTk-based styles to TScrollbar: {e_style}.")
    root.attributes('-alpha', 1.0); root.overrideredirect(False)
    if os.name == 'nt': WindowsAPI.apply_window_style(root)


class MacroManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._load_lock = threading.Lock()
        self._expansion_cache = defaultdict(str)
        self.expansions: Dict[str, str] = {}
        self.current_typed: str = ""
        self.keyboard_listener_hook: Optional[Any] = None
        self.tray_icon: Optional[Any] = None
        self.suggestion_ui_callback: Optional[callable] = None
        self.suggestion_popup_active: bool = False
        self.suggestion_hotkey_hook: Optional[Any] = None
        self.is_running: bool = True
        self.is_applying_macro_flag: bool = False
        self.last_hotkey_press_time: float = 0.0

        app_data_dir_name = "MacroManagerV3"

        if hasattr(sys, '_MEIPASS'):
            self.bundled_expansions_file = os.path.join(sys._MEIPASS, "expansions.json")
            user_data_path = get_user_data_dir(app_data_dir_name)
            self.expansions_file = os.path.join(user_data_path, "expansions.json")
            logger.info(f"Modo Buildado: Usando expansions.json em: {self.expansions_file}")
            if not os.path.exists(self.bundled_expansions_file):
                logger.warning(f"Arquivo de expansões padrão (bundle) NÃO ENCONTRADO em: {self.bundled_expansions_file}")
                self.bundled_expansions_file = None
            else:
                logger.info(f"Arquivo de expansões padrão (bundle) encontrado em: {self.bundled_expansions_file}")
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            self.expansions_file = os.path.join(self.base_path, "expansions.json")
            self.bundled_expansions_file = self.expansions_file
            logger.info(f"Modo Desenvolvimento: Usando expansions.json em: {self.expansions_file}")

        self._ensure_expansions_file()
        self.load_expansions()

    def _ensure_expansions_file(self) -> None:
        try:
            exp_dir = os.path.dirname(self.expansions_file)
            if not os.path.exists(exp_dir):
                try:
                    os.makedirs(exp_dir, exist_ok=True)
                    logger.info(f"Diretório de dados do usuário criado: {exp_dir}")
                except OSError as e:
                    logger.error(f"Não foi possível criar o diretório de dados do usuário {exp_dir}: {e}")

            if not os.path.exists(self.expansions_file):
                logger.info(f"Arquivo de expansões do usuário não encontrado em {self.expansions_file}.")
                copied_from_bundle = False
                if self.bundled_expansions_file and os.path.exists(self.bundled_expansions_file) and \
                   os.path.abspath(self.bundled_expansions_file) != os.path.abspath(self.expansions_file):
                    try:
                        os.makedirs(os.path.dirname(self.expansions_file), exist_ok=True)
                        shutil.copy2(self.bundled_expansions_file, self.expansions_file)
                        logger.info(f"Copiado expansions.json do bundle para {self.expansions_file}")
                        copied_from_bundle = True
                    except Exception as e_copy:
                        logger.error(f"Falha ao copiar expansions.json do bundle: {e_copy}. Criando um novo vazio.")

                if not copied_from_bundle:
                    logger.info(f"Criando novo expansions.json vazio em {self.expansions_file}")
                    os.makedirs(os.path.dirname(self.expansions_file), exist_ok=True)
                    with open(self.expansions_file, "w", encoding="utf-8") as f:
                        json.dump({}, f, ensure_ascii=False, indent=4)

            with open(self.expansions_file, "r+", encoding="utf-8") as f:
                try:
                    json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"JSON inválido em {self.expansions_file}. Resetando para arquivo vazio.")
                    f.seek(0)
                    f.truncate()
                    json.dump({}, f, ensure_ascii=False, indent=4)

        except Exception as e:
            logger.critical(f"Erro crítico ao garantir o arquivo de expansões do usuário {self.expansions_file}: {e}", exc_info=True)
            try:
                emergency_fallback_path = os.path.join(os.getcwd(), "macros_emergency.json")
                logger.warning(f"TENTATIVA DE EMERGÊNCIA: Usando fallback de expansões em: {emergency_fallback_path}")
                self.expansions_file = emergency_fallback_path
                if not os.path.exists(self.expansions_file):
                    with open(self.expansions_file, "w", encoding="utf-8") as f:
                        json.dump({}, f, ensure_ascii=False, indent=4)
            except Exception as e_critical_fallback:
                logger.error(f"FALHA TOTAL ao criar qualquer arquivo de expansões: {e_critical_fallback}")


    def load_expansions(self) -> None:
        with self._load_lock:
            try:
                with open(self.expansions_file, "r", encoding="utf-8") as f:
                    self.expansions = json.load(f)
                    self._expansion_cache.clear()
                    self._expansion_cache.update(self.expansions)
                logger.info(f"Successfully loaded {len(self.expansions)} macros from {self.expansions_file}")
            except FileNotFoundError:
                logger.error(f"Expansions file {self.expansions_file} não encontrado em load_expansions. Tentando _ensure_expansions_file e recarregar.")
                self._ensure_expansions_file()
                try:
                    with open(self.expansions_file, "r", encoding="utf-8") as f_retry:
                        self.expansions = json.load(f_retry)
                        self._expansion_cache.clear()
                        self._expansion_cache.update(self.expansions)
                    logger.info(f"Successfully loaded {len(self.expansions)} macros from {self.expansions_file} após recriação.")
                except Exception as e_retry_load:
                    logger.error(f"Falha ao carregar expansões mesmo após _ensure_expansions_file: {e_retry_load}")
                    self.expansions = {}
                    self._expansion_cache.clear()
            except json.JSONDecodeError:
                logger.error(f"JSONDecodeError em load_expansions para {self.expansions_file}. Resetando.")
                self.expansions = {}
                self._expansion_cache.clear()
            except Exception as e:
                logger.error(f"Falha ao carregar expansões de {self.expansions_file}: {e}", exc_info=True)
                self.expansions = {}
                self._expansion_cache.clear()

    def save_expansions(self) -> None:
        with self._load_lock:
            try:
                exp_dir = os.path.dirname(self.expansions_file)
                if not os.path.exists(exp_dir):
                    try:
                        os.makedirs(exp_dir, exist_ok=True)
                    except OSError as e:
                        logger.error(f"Não foi possível criar diretório {exp_dir} para salvar expansões: {e}. Salvamento pode falhar.")
                        return

                with open(self.expansions_file, "w", encoding="utf-8") as f:
                    json.dump(self.expansions, f, ensure_ascii=False, indent=4)
                self._expansion_cache.clear()
                self._expansion_cache.update(self.expansions)
                logger.info(f"Successfully saved {len(self.expansions)} macros to {self.expansions_file}")
            except Exception as e:
                logger.error(f"Falha ao salvar expansões em {self.expansions_file}: {e}")

    def register_suggestion_ui_callback(self, callback: callable) -> None:
        self.suggestion_ui_callback = callback

    def _trigger_suggestion_ui(self, command: str, data: Optional[Any] = None) -> None:
        if self.suggestion_ui_callback:
            self.suggestion_ui_callback(command, data)

    def try_apply_macro(self, macro_key_to_apply: str, typed_length_to_delete: int) -> bool:
        if macro_key_to_apply in self._expansion_cache:
            logger.info(f"Applying macro '{macro_key_to_apply}', deleting {typed_length_to_delete} chars.")
            logger.debug(f"try_apply_macro: current_typed before action: '{self.current_typed}' for macro '{macro_key_to_apply}'")

            self.is_applying_macro_flag = True
            macro_text = self._expansion_cache[macro_key_to_apply]

            if self.suggestion_popup_active:
                logger.debug("try_apply_macro: Hiding suggestion popup BEFORE sending keys.")
                self._trigger_suggestion_ui("hide")
                # VALOR CRÍTICO PARA AJUSTE:
                sleep_duration_for_focus_return = 0.7 # <<<<<< VALOR AUMENTADO PARA TESTE DE FOCO
                logger.debug(f"try_apply_macro: Pausing for {sleep_duration_for_focus_return}s for focus to return...")
                time.sleep(sleep_duration_for_focus_return)
                logger.debug("try_apply_macro: Paused after hide, attempting key operations.")
            else:
                time.sleep(0.05)


            try:
                logger.debug(f"Sending {typed_length_to_delete} backspaces.")
                for _ in range(typed_length_to_delete):
                    keyboard.send("backspace")
                time.sleep(0.05) # Pequena pausa após backspaces

                # Salvar conteúdo atual da área de transferência
                original_clipboard_content = pyperclip.paste()
                logger.debug("Original clipboard content saved.")

                # Copiar texto da macro para a área de transferência
                pyperclip.copy(macro_text)
                logger.debug(f"Macro text '{macro_text[:30]}...' copied to clipboard.")
                time.sleep(0.05) # Pausa para garantir que a cópia foi processada

                # Colar (Ctrl+V ou Cmd+V)
                if sys.platform == "darwin": # macOS
                    keyboard.send("command+v")
                    logger.debug("Sent command+v (macOS).")
                else: # Windows/Linux
                    keyboard.send("ctrl+v")
                    logger.debug("Sent ctrl+v.")
                time.sleep(0.05) # Pausa após colar

                # Restaurar conteúdo original da área de transferência
                pyperclip.copy(original_clipboard_content)
                logger.debug("Original clipboard content restored.")

                self.show_notification(f"Macro '{macro_key_to_apply}' aplicada")
            except Exception as e:
                logger.error(f"Error during macro application keyboard events: {e}", exc_info=True)
            finally:
                self.is_applying_macro_flag = False
                self.current_typed = ""
                if self.suggestion_popup_active:
                     logger.debug("try_apply_macro finally: suggestion_popup_active is still true, ensuring hide (callback will set it to false).")
                     self._trigger_suggestion_ui("hide")

                logger.debug(f"try_apply_macro: Cleanup done. current_typed='{self.current_typed}', is_applying_macro_flag={self.is_applying_macro_flag}, popup_active={self.suggestion_popup_active}")
            return True

        logger.warning(f"Macro key '{macro_key_to_apply}' not found in cache for application.")
        return False


    def on_key_press(self, event: keyboard.KeyboardEvent) -> None:
        if self.is_applying_macro_flag:
            logger.debug(f"on_key_press: Ignored (is_applying_macro_flag). Key: {event.name}")
            return

        HOTKEY_IGNORE_WINDOW = 0.25
        keys_to_ignore_post_hotkey = ['ctrl', 'left ctrl', 'right ctrl', 'space', 'alt', 'left alt', 'right alt', 'shift', 'left shift', 'right shift']
        if time.time() - self.last_hotkey_press_time < HOTKEY_IGNORE_WINDOW and \
           event.name in keys_to_ignore_post_hotkey:
            logger.debug(f"on_key_press: Ignored (hotkey component filter). Key: '{event.name}', TimeDiff: {time.time() - self.last_hotkey_press_time:.3f}s")
            return

        if not self.is_running or event.name is None:
            return

        try:
            logger.debug(f"on_key_press: START - key='{event.name}', current_typed='{self.current_typed}', popup_active={self.suggestion_popup_active}")

            if self.suggestion_popup_active:
                if event.name in ["ctrl", "alt", "shift", "left ctrl", "right ctrl", "left alt", "right alt", "left shift", "right shift", "caps lock", "cmd", "option", "windows"]:
                    logger.debug(f"on_key_press: Ignored modifier key '{event.name}' while popup active.")
                    return

                logger.debug(f"Popup active, processing key: {event.name}")
                if event.name == "esc": # Correção: 'esc' é o nome canônico para Escape
                    self._trigger_suggestion_ui("hide")
                    return
                if event.name in ["up", "down"]:
                    self._trigger_suggestion_ui("navigate", event.name)
                    return
                if event.name in ["space", "enter", "tab"]:
                    logger.debug(f"on_key_press: Popup selection key '{event.name}', current_typed to be sent: '{self.current_typed}'")
                    self._trigger_suggestion_ui("select_or_close", self.current_typed)
                    return
                elif event.name == "backspace":
                    if self.current_typed:
                        self.current_typed = self.current_typed[:-1]
                        logger.debug(f"on_key_press: Backspace, current_typed now: '{self.current_typed}'")
                        if not self.current_typed.startswith('/'):
                            self._trigger_suggestion_ui("hide")
                            logger.debug("on_key_press: Backspace, hiding popup (current_typed no longer starts with /)")
                        else:
                            filtered_macros = [m for m in self.expansions.keys() if m.startswith(self.current_typed)]
                            if not filtered_macros and self.current_typed == "/":
                                logger.debug("on_key_press: Backspace, current_typed is '/', updating with empty list.")
                                self._trigger_suggestion_ui("update", {"macros": [], "filter": self.current_typed})
                            elif not filtered_macros :
                                logger.debug(f"on_key_press: Backspace, no macros for '{self.current_typed}'. Hiding.")
                                self._trigger_suggestion_ui("hide")
                            else:
                                self._trigger_suggestion_ui("update", {"macros": filtered_macros, "filter": self.current_typed})
                    else:
                        logger.debug("on_key_press: Backspace with empty current_typed in active popup. Hiding.")
                        self._trigger_suggestion_ui("hide")
                    return
                elif len(event.name) == 1 and event.name.isprintable():
                    self.current_typed += event.name
                    logger.debug(f"on_key_press: Printable char, current_typed now: '{self.current_typed}'")
                    filtered_macros = [m for m in self.expansions.keys() if m.startswith(self.current_typed)]
                    if not filtered_macros:
                         logger.debug(f"on_key_press: No macros match '{self.current_typed}'. Hiding popup.")
                         self._trigger_suggestion_ui("hide")
                    else:
                        self._trigger_suggestion_ui("update", {"macros": filtered_macros, "filter": self.current_typed})
                    return
                logger.debug(f"on_key_press: Ignored unhandled key '{event.name}' while popup active.")
                return

            if self.current_typed.startswith("/"):
                if event.name in ["space", "enter", "tab"]:
                    if self.current_typed in self._expansion_cache:
                        logger.info(f"Direct expansion: '{self.current_typed}' by '{event.name}'")
                        self.try_apply_macro(self.current_typed, len(self.current_typed) + 1)
                    else:
                        logger.debug(f"Direct expansion: '{self.current_typed}' not a macro. Clearing.")
                        self.current_typed = ""
                elif event.name == "backspace":
                    self.current_typed = self.current_typed[:-1]
                    logger.debug(f"Direct: Backspace, current_typed: '{self.current_typed}'")
                elif len(event.name) == 1 and event.name.isprintable():
                    self.current_typed += event.name
                    logger.debug(f"Direct: Printable, current_typed: '{self.current_typed}'")
                elif event.name not in keys_to_ignore_post_hotkey + ["caps lock", "esc", "cmd", "option", "windows"]:
                    logger.debug(f"Direct: Non-handled key '{event.name}' with '{self.current_typed}'. Clearing.")
                    self.current_typed = ""
            elif event.name == "/":
                self.current_typed = "/"
                logger.debug(f"Direct: Slash typed, current_typed set to: '{self.current_typed}'")

            logger.debug(f"on_key_press: END - current_typed='{self.current_typed}'")
        except Exception as e:
            logger.error(f"Error processing key in on_key_press: {e}", exc_info=True)
            self.current_typed = ""


    def activate_suggestion_mode(self) -> None:
        self.last_hotkey_press_time = time.time()

        if self.is_applying_macro_flag:
            logger.info("activate_suggestion_mode: Macro application in progress, ignoring hotkey.")
            return

        logger.info("--- activate_suggestion_mode CALLED ---")
        if not self.is_running:
            logger.warning("activate_suggestion_mode: self.is_running is False, returning.")
            return

        if self.suggestion_popup_active:
            logger.info("Hotkey (ctrl+space) pressed while popup active. Hiding popup.")
            self._trigger_suggestion_ui("hide")
        else:
            logger.info("Hotkey (ctrl+space) pressed. Activating suggestion mode. Current typed before reset: '%s'", self.current_typed)
            self.current_typed = "/"
            logger.info(f"activate_suggestion_mode: current_typed SET TO: '{self.current_typed}'")
            self._trigger_suggestion_ui("show", {"macros": list(self.expansions.keys()), "filter": self.current_typed})


    def start_listener(self) -> None:
        logger.info("Attempting to start listeners...")
        if not self.is_running:
            logger.warning("start_listener called but manager is not running.")
            return

        if self.suggestion_hotkey_hook is None:
            try:
                self.suggestion_hotkey_hook = keyboard.add_hotkey(
                    'ctrl+space',
                    self.activate_suggestion_mode,
                    suppress=True,
                    timeout=0.1,
                    trigger_on_release=False
                )
                logger.info(f"Suggestion hotkey 'ctrl+space' registered. Remover function: {self.suggestion_hotkey_hook}")
            except Exception as e:
                logger.error(f"Failed to register suggestion hotkey 'ctrl+space': {e}", exc_info=True)
                self.suggestion_hotkey_hook = None
        else:
            logger.info("Suggestion hotkey 'ctrl+space' already registered.")

        if self.keyboard_listener_hook is None:
            try:
                self.keyboard_listener_hook = keyboard.on_press(self.on_key_press, suppress=False)
                logger.info(f"Keyboard on_press listener registered. Remover function: {self.keyboard_listener_hook}")
            except Exception as e:
                logger.error(f"Failed to register on_press listener: {e}", exc_info=True)
                self.keyboard_listener_hook = None
        else:
            logger.info("Keyboard on_press listener already registered.")


    def stop_listener(self) -> None:
        logger.info("Attempting to stop listeners...")
        if self.keyboard_listener_hook:
            try:
                if callable(self.keyboard_listener_hook): self.keyboard_listener_hook()
                else: keyboard.unhook(self.on_key_press)
                logger.info("Keyboard on_press listener unhooked.")
            except (KeyError, Exception) as e:
                logger.info(f"Could not unhook on_press listener (may already be unhooked or issue with unhooking by callback object): {e}")
                try:
                    keyboard.unhook_all()
                    logger.info("Called keyboard.unhook_all() as a fallback.")
                except Exception as e_all:
                    logger.error(f"Error during keyboard.unhook_all(): {e_all}")
            finally:
                self.keyboard_listener_hook = None

        if self.suggestion_hotkey_hook:
            try:
                if callable(self.suggestion_hotkey_hook):
                    self.suggestion_hotkey_hook()
                    logger.info("Suggestion hotkey 'ctrl+space' removed by stored removal function.")
                else:
                    keyboard.remove_hotkey('ctrl+space')
                    logger.info("Suggestion hotkey 'ctrl+space' removed by string (fallback).")
            except (KeyError, Exception) as e:
                logger.info(f"Could not remove hotkey 'ctrl+space' (may already be removed or other issue): {e}")
                try:
                    keyboard.remove_all_hotkeys()
                    logger.info("Called keyboard.remove_all_hotkeys() as a fallback.")
                except Exception as e_all_hk:
                    logger.error(f"Error during keyboard.remove_all_hotkeys(): {e_all_hk}")
            finally:
                self.suggestion_hotkey_hook = None


    def cleanup(self) -> None:
        with self._lock:
            if not self.is_running:
                logger.info("Cleanup: Manager already stopped or cleanup in progress.")
                return

            logger.info("Cleanup: Stopping manager and listeners...")
            self.is_running = False
            self.stop_listener()

            try:
                current_process = psutil.Process(os.getpid())
                children = current_process.children(recursive=True)
                if children:
                    logger.info(f"Cleanup: Terminating {len(children)} child process(es).")
                    for child in children:
                        try:
                            logger.debug(f"Cleanup: Terminating child PID {child.pid} - {child.name()}")
                            child.terminate()
                        except psutil.NoSuchProcess:
                            logger.warning(f"Cleanup: Child process {child.pid} already terminated.")
                        except Exception as e_child:
                            logger.error(f"Cleanup: Error terminating child process {child.pid}: {e_child}")
                else:
                    logger.info("Cleanup: No child processes to terminate.")
            except Exception as e_psutil:
                logger.error(f"Cleanup: Error during psutil process cleanup: {e_psutil}", exc_info=True)

            logger.info("Cleanup: Manager cleanup process finished.")


    def show_notification(self, message: str) -> None:
        if self.tray_icon and hasattr(self.tray_icon, 'HAS_NOTIFICATION') and self.tray_icon.HAS_NOTIFICATION:
            try:
                self.tray_icon.notify(message, "Macro Manager")
                logger.debug(f"Tray notification sent: {message}")
            except Exception as e:
                logger.error(f"Error sending tray notification: {e}")
        else:
            logger.debug(f"Tray icon not available or no notification support, for message: {message}")

class MacroSuggestionPopup(ctk.CTkToplevel):
    def __init__(self, master, all_macros_dict: Dict[str, str], manager_ref: MacroManager, on_close_callback: callable):
        super().__init__(master)
        logger.debug(f"MacroSuggestionPopup __init__ called. Master: {master}, Macros count: {len(all_macros_dict)}")
        self.all_macros_dict = all_macros_dict
        self.manager_ref = manager_ref
        self.on_close_callback = on_close_callback

        self.overrideredirect(True)
        self.attributes("-topmost", True)

        self.BORDER_COLOR = ("#808080", "#383838")
        self.BG_COLOR = ("#F9F9F9", "#2B2B2B")
        self.ITEM_FG_COLOR = ("#FFFFFF", "#333333")
        self.ITEM_HOVER_COLOR = ("#E0E0E0", "#4A4A4A")
        try:
            theme_data = ctk.ThemeManager.get_theme(ctk.ThemeManager.get_currently_used_theme()) if hasattr(ctk.ThemeManager, 'get_theme') else {}
            self.ITEM_SELECTED_COLOR = theme_data.get("CTkButton", {}).get("fg_color", ("#1F6AA5", "#1F6AA5"))
            self.ITEM_TEXT_COLOR = theme_data.get("CTkLabel", {}).get("text_color", ("#101010", "#DCE4EE"))
            self.ITEM_SELECTED_TEXT_COLOR = theme_data.get("CTkButton", {}).get("text_color", ("#FFFFFF", "#FFFFFF"))
            current_appearance = ctk.get_appearance_mode()
            idx = 1 if current_appearance == "Dark" else 0
            if isinstance(self.ITEM_SELECTED_COLOR, (list, tuple)) and len(self.ITEM_SELECTED_COLOR) > idx: self.ITEM_SELECTED_COLOR = self.ITEM_SELECTED_COLOR[idx]
            if isinstance(self.ITEM_TEXT_COLOR, (list, tuple)) and len(self.ITEM_TEXT_COLOR) > idx: self.ITEM_TEXT_COLOR = self.ITEM_TEXT_COLOR[idx]
            if isinstance(self.ITEM_SELECTED_TEXT_COLOR, (list, tuple)) and len(self.ITEM_SELECTED_TEXT_COLOR) > idx: self.ITEM_SELECTED_TEXT_COLOR = self.ITEM_SELECTED_TEXT_COLOR[idx]
        except Exception as e:
            logger.warning(f"Could not get theme colors for popup items from CTk ThemeManager, using fallbacks: {e}")
            appearance_mode = ctk.get_appearance_mode() # Ensure we have it
            self.ITEM_SELECTED_COLOR = "#1F6AA5"
            self.ITEM_TEXT_COLOR = "#DCE4EE" if appearance_mode == "Dark" else "#101010"
            self.ITEM_SELECTED_TEXT_COLOR = "#FFFFFF"

        self.configure(fg_color=self.BG_COLOR)
        self.outer_frame = ctk.CTkFrame(self, fg_color=self.BORDER_COLOR, corner_radius=7)
        self.outer_frame.pack(expand=True, fill="both", padx=1, pady=1)
        self.inner_frame = ctk.CTkFrame(self.outer_frame, fg_color=self.BG_COLOR, corner_radius=6)
        self.inner_frame.pack(expand=True, fill="both", padx=1, pady=1)
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.inner_frame, fg_color="transparent",
            scrollbar_button_color=self.ITEM_HOVER_COLOR,
            scrollbar_button_hover_color=self.ITEM_SELECTED_COLOR, corner_radius=5
        )
        self.scrollable_frame.pack(expand=True, fill="both", padx=3, pady=3)
        self.list_item_widgets: list[ctk.CTkButton] = []
        self.current_selection_index: int = -1
        self.item_font = CTkFont("Segoe UI", 11)
        self.bind("<Escape>", lambda e: self.close_popup())
        self.withdraw()
        logger.debug("MacroSuggestionPopup __init__ finished.")

    def _clear_items(self):
        for widget in self.list_item_widgets: widget.destroy()
        self.list_item_widgets = []
        self.current_selection_index = -1

    def _highlight_item(self, index: int, select: bool):
        if 0 <= index < len(self.list_item_widgets):
            item_button = self.list_item_widgets[index]
            if select: item_button.configure(fg_color=self.ITEM_SELECTED_COLOR, text_color=self.ITEM_SELECTED_TEXT_COLOR)
            else: item_button.configure(fg_color=self.ITEM_FG_COLOR, text_color=self.ITEM_TEXT_COLOR)

    def _on_item_enter(self, event, item_button: ctk.CTkButton):
        try:
            index = self.list_item_widgets.index(item_button)
            if index != self.current_selection_index:
                item_button.configure(fg_color=self.ITEM_HOVER_COLOR)
        except ValueError: logger.warning(f"Item not found in list_item_widgets during _on_item_enter: {item_button}")

    def _on_item_leave(self, event, item_button: ctk.CTkButton):
        try:
            index = self.list_item_widgets.index(item_button)
            if index != self.current_selection_index:
                item_button.configure(fg_color=self.ITEM_FG_COLOR)
        except ValueError: logger.warning(f"Item not found in list_item_widgets during _on_item_leave: {item_button}")

    def _scroll_to_item(self, index: int):
        if not self.list_item_widgets or not (0 <= index < len(self.list_item_widgets)): return
        self.scrollable_frame.update_idletasks()
        target_widget = self.list_item_widgets[index]
        try:
            widget_y_rel = target_widget.winfo_y(); widget_h = target_widget.winfo_height()
            viewport_h = self.scrollable_frame._parent_canvas.winfo_height()
            self.scrollable_frame._parent_canvas.update_idletasks()
            bbox_all = self.scrollable_frame._parent_canvas.bbox("all")
            if not bbox_all: return
            content_h = bbox_all[3] - bbox_all[1]
            if content_h <= viewport_h: return
            if content_h <= 0: return
            viewport_top_y = self.scrollable_frame._parent_canvas.canvasy(0)
            viewport_bottom_y = viewport_top_y + viewport_h
            widget_top_y = widget_y_rel; widget_bottom_y = widget_y_rel + widget_h
            new_scroll_fraction = -1.0
            if widget_top_y < viewport_top_y: new_scroll_fraction = widget_top_y / content_h
            elif widget_bottom_y > viewport_bottom_y: new_scroll_fraction = (widget_bottom_y - viewport_h) / content_h
            if new_scroll_fraction != -1.0:
                new_scroll_fraction = max(0.0, min(new_scroll_fraction, 1.0))
                self.scrollable_frame._parent_canvas.yview_moveto(new_scroll_fraction)
                self.scrollable_frame.update_idletasks()
        except Exception as e: logger.error(f"Error in _scroll_to_item: {e}", exc_info=True)

    def _navigate(self, direction: int):
        if not self.list_item_widgets: return
        new_index = self.current_selection_index + direction
        num_items = len(self.list_item_widgets)
        if self.current_selection_index != -1 and 0 <= self.current_selection_index < num_items:
            self._highlight_item(self.current_selection_index, False)
        if 0 <= new_index < num_items: self.current_selection_index = new_index
        elif new_index < 0: self.current_selection_index = num_items - 1
        elif new_index >= num_items: self.current_selection_index = 0
        if 0 <= self.current_selection_index < num_items:
            self._highlight_item(self.current_selection_index, True)
            self._scroll_to_item(self.current_selection_index)
            if self.list_item_widgets[self.current_selection_index].winfo_exists():
                 self.list_item_widgets[self.current_selection_index].focus_set()
        else: self.current_selection_index = -1

    def update_suggestions(self, filter_text: str) -> None:
        self._clear_items()
        logger.info(f"update_suggestions (com CTkButton) chamado com filtro: '{filter_text}'")
        if not self.manager_ref.suggestion_popup_active:
            if self.winfo_viewable(): self.withdraw(); return
        if not filter_text.startswith("/"): self.close_popup(); return
        if filter_text == "/": display_macros_keys = sorted(self.all_macros_dict.keys())
        else: display_macros_keys = sorted([k for k in self.all_macros_dict.keys() if k.startswith(filter_text)])
        logger.debug(f"Encontradas {len(display_macros_keys)} macros para o filtro '{filter_text}'.")
        MAX_ITEMS_DISPLAY = 7; item_pady_outer = 1; button_height = 30
        try:
            for i, key in enumerate(display_macros_keys):
                preview_full = self.all_macros_dict.get(key, ""); preview_oneline = preview_full.split('\n')[0]
                preview_char_limit = 40; preview_short = (preview_oneline[:preview_char_limit] + "...") if len(preview_oneline) > preview_char_limit else preview_oneline
                button_text = f"{key}  \u2192  {preview_short}"
                item_button = ctk.CTkButton(
                    self.scrollable_frame, text=button_text, font=self.item_font,
                    fg_color=self.ITEM_FG_COLOR, hover_color=self.ITEM_HOVER_COLOR,
                    text_color=self.ITEM_TEXT_COLOR, anchor="w", height=button_height,
                    corner_radius=4, border_spacing=8,
                    command=lambda k=key, idx=i: self._trigger_select_action_from_click(k, idx)
                )
                item_button._macro_key = key
                item_button.bind("<Enter>", lambda e, btn=item_button: self._on_item_enter(e, btn))
                item_button.bind("<Leave>", lambda e, btn=item_button: self._on_item_leave(e, btn))
                item_button.pack(fill="x", expand=True, padx=3, pady=item_pady_outer)
                self.list_item_widgets.append(item_button)
            self.scrollable_frame.update_idletasks()
            if self.list_item_widgets:
                self.current_selection_index = 0; self._highlight_item(0, True)
                if not self.winfo_viewable(): logger.info("Tornando o popup de sugestões visível (deiconify)."); self.deiconify()
                else: logger.info("Popup de sugestões já estava visível (lift).")
                self.lift(); self.scrollable_frame.focus_set()
                visible_items = min(len(self.list_item_widgets), MAX_ITEMS_DISPLAY)
                actual_item_height_in_scroll = button_height + (item_pady_outer * 2)
                popup_content_height = visible_items * actual_item_height_in_scroll
                outer_f_pady = 1; inner_f_pady = 1; scroll_f_pady = 3
                total_vertical_padding = (outer_f_pady*2)+(inner_f_pady*2)+(scroll_f_pady*2)
                popup_total_height = min(max(popup_content_height + total_vertical_padding + 10, 80), 450)
                popup_width = 480
                current_geom = self.geometry()
                try:
                    current_pos_parts = current_geom.split('+')
                    if len(current_pos_parts) == 3:
                         current_pos = "+" + current_pos_parts[1] + "+" + current_pos_parts[2]
                         self.geometry(f"{popup_width}x{int(popup_total_height)}{current_pos}")
                    else: self.geometry(f"{popup_width}x{int(popup_total_height)}")
                except IndexError: self.geometry(f"{popup_width}x{int(popup_total_height)}")
                logger.info(f"Geometria do popup definida para: {self.geometry()}")
                self._scroll_to_item(self.current_selection_index)
            else:
                if self.winfo_viewable(): self.withdraw()
        except Exception as e:
            logger.critical(f"ERRO CRÍTICO DENTRO DO UPDATE_SUGGESTIONS: {e}", exc_info=True)
            if self.winfo_viewable(): self.withdraw()
            if self.on_close_callback: self.on_close_callback()

    def _trigger_select_action_from_click(self, macro_key: str, clicked_index: int):
        logger.debug(f"_trigger_select_action_from_click: Key='{macro_key}', Index='{clicked_index}'")
        if self.current_selection_index != -1 and \
           0 <= self.current_selection_index < len(self.list_item_widgets) and \
           self.current_selection_index != clicked_index:
            self._highlight_item(self.current_selection_index, False)
        self.current_selection_index = clicked_index
        self._highlight_item(self.current_selection_index, True)
        self.after(50, self._apply_selected_macro)

    def _trigger_select_action_from_keyboard(self):
        logger.debug(f"_trigger_select_action_from_keyboard: Current index: {self.current_selection_index}")
        if 0 <= self.current_selection_index < len(self.list_item_widgets):
            self._apply_selected_macro()
        else:
            logger.debug("_trigger_select_action_from_keyboard: Nenhum item selecionado ou índice inválido. Fechando popup.")
            self.close_popup()

    def _apply_selected_macro(self):
        if not (0 <= self.current_selection_index < len(self.list_item_widgets)):
            logger.warning("_apply_selected_macro: Índice de seleção inválido.")
            self.close_popup(); return
        selected_button = self.list_item_widgets[self.current_selection_index]
        if hasattr(selected_button, "_macro_key"):
            selected_key_to_apply = selected_button._macro_key
            if selected_key_to_apply in self.all_macros_dict:
                chars_to_delete = len(self.manager_ref.current_typed)
                logger.debug(f"_apply_selected_macro: Aplicando. Key='{selected_key_to_apply}', manager.current_typed='{self.manager_ref.current_typed}', chars_to_delete={chars_to_delete}")
                self.manager_ref.try_apply_macro(selected_key_to_apply, chars_to_delete)
            else: logger.warning(f"Chave '{selected_key_to_apply}' não encontrada para _apply_selected_macro.")
        else: logger.error(f"Botão no índice {self.current_selection_index} não possui _macro_key.")
        self.close_popup()

    def on_select_action(self, event=None) -> bool:
        logger.debug(f"on_select_action (event handler for keyboard). Current index: {self.current_selection_index}")
        self._trigger_select_action_from_keyboard(); return True

    def close_popup(self, event=None) -> None:
        popup_was_viewable = self.winfo_viewable()
        if popup_was_viewable: logger.debug("Closing suggestion popup (withdraw)."); self.withdraw()
        if popup_was_viewable and self.on_close_callback and self.manager_ref.suggestion_popup_active:
            logger.debug("close_popup: Calling on_close_callback (was viewable and manager active)."); self.on_close_callback()
        elif not popup_was_viewable and self.on_close_callback and self.manager_ref.suggestion_popup_active:
            logger.debug("close_popup: Popup not viewable but manager thought active. Calling callback."); self.on_close_callback()

    def handle_external_key(self, key_name: str) -> None:
        logger.debug(f"Popup handling external key: {key_name}")
        if not self.winfo_viewable(): logger.debug(f"Popup not viewable, ignoring key: {key_name}"); return
        if key_name == "up": self._navigate(-1)
        elif key_name == "down": self._navigate(1)
        elif key_name in ["enter", "tab", "space"]: self.on_select_action()

    def is_active(self) -> bool: return self.winfo_viewable()

class MacroGUI:
    def __init__(self, root: ctk.CTk, manager: MacroManager) -> None:
        self.root = root; self.manager = manager; self.bandeja_ativa = False
        self.tray_icon_object: Optional[Icon] = None; self.tray_thread: Optional[threading.Thread] = None
        self.suggestion_popup: Optional[MacroSuggestionPopup] = None
        configurar_tema(self.root); self._setup_window(); self._create_widgets(); self._setup_events()
        self.manager.register_suggestion_ui_callback(lambda cmd, data: self.root.after(0, self._process_suggestion_request, cmd, data))
        self.atualizar_lista()

    def _setup_window(self) -> None:
        self.root.title("Macro Manager"); self.root.geometry("800x600"); self.root.minsize(600, 400)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing_main_window_X_button)

    def _create_widgets(self) -> None:
        self.root.grid_columnconfigure(0, weight=1); self.root.grid_rowconfigure(0, weight=1)
        self.main_frame = ctk.CTkFrame(self.root); self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1); self.main_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.main_frame, text="Macros Disponíveis:", font=CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=5, pady=(5,10))
        self._create_macro_list(); self._create_buttons()

    def _create_macro_list(self) -> None:
        tree_container_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent"); tree_container_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        tree_container_frame.grid_columnconfigure(0, weight=1); tree_container_frame.grid_rowconfigure(0, weight=1)
        self.lista_macros = ttk.Treeview(tree_container_frame, columns=("Atalho", "Texto"), show="headings")
        self.lista_macros.heading("Atalho", text="Atalho"); self.lista_macros.heading("Texto", text="Texto da Macro")
        self.lista_macros.column("Atalho", width=200, minwidth=150, stretch=tk.NO); self.lista_macros.column("Texto", width=500, minwidth=300)
        self.lista_macros.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tree_container_frame, orient="vertical", command=self.lista_macros.yview); scrollbar.grid(row=0, column=1, sticky="ns")
        self.lista_macros.configure(yscrollcommand=scrollbar.set)

    def _create_buttons(self) -> None:
        button_frame = ctk.CTkFrame(self.main_frame); button_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(10,5))
        button_frame.grid_columnconfigure((0,1,2), weight=1)
        ctk.CTkButton(button_frame, text="Adicionar Macro", command=self.adicionar_macro_gui).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(button_frame, text="Remover Selecionada", command=self.remover_macro_gui).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(button_frame, text="Editar Selecionada", command=self.editar_macro_gui).grid(row=0, column=2, padx=5, pady=5)

    def _setup_events(self) -> None: self.root.protocol("WM_DELETE_WINDOW", self.on_closing_main_window_X_button)

    def atualizar_lista(self) -> None:
        try:
            for i in self.lista_macros.get_children(): self.lista_macros.delete(i)
            for key, val in sorted(self.manager.expansions.items()):
                primeira_linha_val = val.split('\n')[0]
                texto_curto = (primeira_linha_val[:60] + "...") if len(primeira_linha_val) > 60 else primeira_linha_val
                self.lista_macros.insert("", "end", values=(key, texto_curto))
            logger.info(f"Updated macro list with {len(self.manager.expansions)} items")
        except Exception as e: logger.error(f"Error updating macro list: {e}", exc_info=True)

    def _center_toplevel(self, win, w, h):
        self.root.update_idletasks(); px,py,pw,ph = self.root.winfo_x(),self.root.winfo_y(),self.root.winfo_width(),self.root.winfo_height()
        x,y = (px+(pw//2)-(w//2), py+(ph//2)-(h//2)) if pw>100 and ph>100 else ((self.root.winfo_screenwidth()//2)-(w//2), (self.root.winfo_screenheight()//2)-(h//2))
        win.geometry(f"{w}x{h}+{x}+{y}")

    def adicionar_macro_gui(self):
        janela_adicionar = ctk.CTkToplevel(self.root); janela_adicionar.title("Adicionar Nova Macro"); janela_adicionar.attributes("-topmost", True)
        janela_adicionar.transient(self.root); janela_adicionar.grab_set(); self._center_toplevel(janela_adicionar, 450, 550)
        container = ctk.CTkFrame(janela_adicionar); container.pack(fill="both", expand=True, padx=15, pady=15); container.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(container, text="Atalho (ex: /saudacao):", font=CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=(0,2))
        entrada_shortcut = ctk.CTkEntry(container, width=400); entrada_shortcut.grid(row=1, column=0, sticky="ew", pady=(0,10))
        ctk.CTkLabel(container, text="Texto da Macro:", font=CTkFont(size=12)).grid(row=2, column=0, sticky="w", pady=(0,2))
        entrada_texto = ctk.CTkTextbox(container, height=300, width=400, wrap="word"); entrada_texto.grid(row=3, column=0, sticky="nsew", pady=(0,15)); container.grid_rowconfigure(3, weight=1)
        def salvar():
            s,t = entrada_shortcut.get().strip(), entrada_texto.get("1.0", "end-1c").strip()
            if not s.startswith("/") or len(s)<2 or not t or s in self.manager.expansions: messagebox.showerror("Erro", "Verifique o atalho (deve começar com '/', ser único, e não vazio) e o texto (não pode ser vazio).", parent=janela_adicionar); return
            self.manager.expansions[s] = t; self.manager.save_expansions(); self.atualizar_lista()
            if self.suggestion_popup and self.suggestion_popup.is_active(): self.suggestion_popup.all_macros_dict=self.manager.expansions.copy(); self.suggestion_popup.update_suggestions(self.manager.current_typed or "/")
            janela_adicionar.destroy()
        ctk.CTkButton(container, text="Salvar Macro", command=salvar).grid(row=4, column=0, pady=(10,0)); entrada_shortcut.focus_set(); janela_adicionar.bind("<Escape>", lambda e: janela_adicionar.destroy())

    def remover_macro_gui(self):
        sel = self.lista_macros.selection()
        if not sel: messagebox.showwarning("Nenhuma Seleção", "Selecione uma macro para remover.", parent=self.root); return
        val = self.lista_macros.item(sel[0], "values")
        if not val: messagebox.showerror("Erro Interno", "Não foi possível obter dados da macro.", parent=self.root); return
        s_rem = val[0]
        if messagebox.askyesno("Confirmar Remoção", f"Remover '{s_rem}'?", icon='warning', parent=self.root):
            if s_rem in self.manager.expansions: del self.manager.expansions[s_rem]; self.manager.save_expansions(); self.atualizar_lista()
            if self.suggestion_popup and self.suggestion_popup.is_active(): self.suggestion_popup.all_macros_dict=self.manager.expansions.copy(); self.suggestion_popup.update_suggestions(self.manager.current_typed or "/")
            else: messagebox.showerror("Erro", f"Macro '{s_rem}' não encontrada.", parent=self.root); self.atualizar_lista()

    def editar_macro_gui(self):
        sel = self.lista_macros.selection()
        if not sel: messagebox.showwarning("Nenhuma Seleção", "Selecione uma macro para editar.", parent=self.root); return
        val = self.lista_macros.item(sel[0], "values")
        if not val: messagebox.showerror("Erro Interno", "Não foi possível obter dados da macro.", parent=self.root); return
        old_s, old_t = val[0], self.manager.expansions.get(val[0], "")
        win_edit = ctk.CTkToplevel(self.root); win_edit.title(f"Editar: {old_s}"); win_edit.attributes("-topmost",True); win_edit.transient(self.root); win_edit.grab_set(); self._center_toplevel(win_edit, 450,550)
        container=ctk.CTkFrame(win_edit); container.pack(fill="both",expand=True,padx=15,pady=15); container.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(container,text=f"Editando: {old_s}",font=CTkFont(size=12,weight="bold")).grid(row=0,column=0,sticky="w",pady=(0,5))
        ctk.CTkLabel(container,text="Novo Atalho:",font=CTkFont(size=12)).grid(row=1,column=0,sticky="w",pady=(0,2))
        entry_new_s=ctk.CTkEntry(container,width=400); entry_new_s.insert(0,old_s); entry_new_s.grid(row=2,column=0,sticky="ew",pady=(0,10))
        ctk.CTkLabel(container,text="Novo Texto:",font=CTkFont(size=12)).grid(row=3,column=0,sticky="w",pady=(0,2))
        entry_new_t=ctk.CTkTextbox(container,height=300,width=400,wrap="word"); entry_new_t.insert("1.0",old_t); entry_new_t.grid(row=4,column=0,sticky="nsew",pady=(0,15)); container.grid_rowconfigure(4,weight=1)
        def confirm_edit():
            new_s,new_t = entry_new_s.get().strip(), entry_new_t.get("1.0","end-1c").strip()
            if not new_s.startswith("/") or len(new_s)<2 or not new_t or (old_s!=new_s and new_s in self.manager.expansions): messagebox.showerror("Erro", "Verifique o atalho e o texto.",parent=win_edit); return
            if old_s in self.manager.expansions: del self.manager.expansions[old_s]
            self.manager.expansions[new_s]=new_t; self.manager.save_expansions(); self.atualizar_lista()
            if self.suggestion_popup and self.suggestion_popup.is_active(): self.suggestion_popup.all_macros_dict=self.manager.expansions.copy(); self.suggestion_popup.update_suggestions(self.manager.current_typed or "/")
            win_edit.destroy()
        ctk.CTkButton(container,text="Salvar",command=confirm_edit).grid(row=5,column=0,pady=(10,0)); entry_new_s.focus_set(); win_edit.bind("<Escape>",lambda e:win_edit.destroy())

    def hide_to_tray(self) -> None:
        if not self.bandeja_ativa:
            logger.info("Escondendo janela para a bandeja do sistema.")
            self.bandeja_ativa = True
            self.root.withdraw()
            if self.tray_thread is None or not self.tray_thread.is_alive():
                def run_tray_thread():
                    logger.debug("Thread da bandeja iniciada.")
                    self.tray_icon_object = self.criar_icone_bandeja()
                    if self.manager: self.manager.tray_icon = self.tray_icon_object
                    if self.tray_icon_object:
                        try: self.tray_icon_object.run()
                        except Exception as e_tray_run: logger.error(f"Erro ao rodar ícone da bandeja: {e_tray_run}", exc_info=True)
                    else: logger.error("Falha ao criar o objeto do ícone da bandeja.")
                    logger.debug("Thread da bandeja finalizada.")
                    self.tray_icon_object = None
                    if self.manager: self.manager.tray_icon = None
                    self.bandeja_ativa = False
                self.tray_thread = threading.Thread(target=run_tray_thread, name="TrayIconThread", daemon=True); self.tray_thread.start()
        else: logger.info("Tentativa de esconder para a bandeja, mas já está no modo bandeja ou thread ativa.")

    def criar_icone_bandeja(self):
        def restaurar(i,it): # i é o objeto Icon
            logger.info("Tray menu: 'Restaurar' clicked.")
            if i: i.stop()
            else: logger.warning("Tray menu 'Restaurar': icon object was None at callback.")
            logger.debug("Tray menu 'Restaurar': icon.stop() called (if icon existed).")
            self.root.after(0,self._restaurar_janela_callback)
            logger.debug("Tray menu 'Restaurar': _restaurar_janela_callback scheduled.")

        def sair(i,it): # i é o objeto Icon
            # Esta função 'sair' original não será usada nesta etapa de teste.
            # Mantida aqui para referência, mas o menu abaixo a substitui.
            pass

        def callback_teste_sair(icon_param, item_param):
            logger.critical("--- CALLBACK DE TESTE DO MENU DA BANDEJA ACIONADO ---")
            if icon_param: icon_param.stop()
            self.root.after(50, self._perform_full_shutdown)
        menu = (MenuItem("Sair de Teste", callback_teste_sair),)
        try: img=self._desenhar_icone(); return Icon("MacroMan",img,"Gerenciador de Macros",menu) if img else None
        except Exception as e: logger.error(f"Failed to create tray icon: {e}",exc_info=True); return None

    def _restaurar_janela_callback(self):
        logger.debug("Executing _restaurar_janela_callback.")
        if self.tray_thread and self.tray_thread.is_alive(): self.tray_thread.join(timeout=0.5)
        self.tray_thread=None; self.tray_icon_object=None
        if self.manager: self.manager.tray_icon=None
        self.bandeja_ativa=False
        self.root.after(10,self.root.deiconify); self.root.lift(); self.root.attributes('-topmost',1); self.root.focus_force(); self.root.after(100,lambda: self.root.attributes('-topmost',0))

    def _desenhar_icone(self):
        s=64;i=Image.new("RGBA",(s,s),(0,0,0,0));d=ImageDraw.Draw(i)
        try:
            d.ellipse((4,4,s-4,s-4),fill=(0,120,215,255));fs=38;fnt=None
            try:
                fps=["arial.ttf","verdana.ttf","tahoma.ttf","calibri.ttf"]
                if hasattr(sys,'_MEIPASS'): pass
                for fp in fps:
                    try: fnt=ImageFont.truetype(fp,fs);logger.debug(f"Font {fp} for tray.");break
                    except IOError: continue
                if not fnt: raise IOError("No suitable font.")
            except IOError: logger.warning(f"Fonts not found, PIL default.");fnt=ImageFont.load_default()
            except Exception as e:logger.error(f"Font load error: {e}");d.rectangle((s//4,s//4,3*s//4,3*s//4),fill=(255,255,255,255));return i
            txt="M"
            if hasattr(d,'textbbox'): bb=d.textbbox((0,0),txt,font=fnt,anchor="lt");tw,th,txo,tyo=bb[2]-bb[0],bb[3]-bb[1],bb[0],bb[1]
            elif hasattr(d,'textsize'): tw,th=d.textsize(txt,font=fnt);txo,tyo=0,0
            else: tw,th=fs*0.6,fs;txo,tyo=0,0
            x,y=(s-tw)/2-txo,(s-th)/2-tyo;d.text((x,y),txt,fill=(255,255,255,255),font=fnt);return i
        except Exception as e:
            logger.error(f"Icon draw error: {e}",exc_info=True);d.rectangle((0,0,s,s),fill=(200,0,0,200))
            try:
                ef=ImageFont.load_default()
                if hasattr(d,'textbbox'): ebb=d.textbbox((0,0),"!",font=ef,anchor="lt");etw,eth,etxo,etyo=ebb[2]-ebb[0],ebb[3]-ebb[1],ebb[0],ebb[1]; d.text(((s-etw)/2-etxo,(s-eth)/2-etyo),"!",fill=(255,255,255,255),font=ef)
                elif hasattr(d,'textsize'): etw,eth=d.textsize("!",font=ef);d.text(((s-etw)//2,(s-eth)//2),"!",fill=(255,255,255,255),font=ef)
                else: d.text((s//3,s//3),"!",fill=(255,255,255,255))
            except:pass
            return i

    def _gui_cleanup(self) -> None:
        logger.info("MacroGUI _gui_cleanup initiated.")
        if self.tray_icon_object:
            logger.debug("Stopping tray icon object (self.tray_icon_object.stop()).")
            self.tray_icon_object.stop()
            self.tray_icon_object=None
        if self.tray_thread and self.tray_thread.is_alive():
            logger.debug(f"Joining tray thread ({self.tray_thread.name})...")
            self.tray_thread.join(timeout=1.0)
            if self.tray_thread.is_alive():
                logger.warning(f"TrayIconThread ({self.tray_thread.name}) did NOT terminate after join with timeout.")
            else:
                logger.info(f"TrayIconThread ({self.tray_thread.name}) terminated successfully.")
            self.tray_thread = None
        else:
            logger.info("Tray thread already stopped or was not running/None at _gui_cleanup.")
        self.bandeja_ativa = False
        logger.info("MacroGUI _gui_cleanup finished.")

    def on_closing_main_window_X_button(self, event=None) -> None:
        logger.info("Main window 'X' button clicked. Hiding to system tray.")
        self.hide_to_tray()

    def _perform_full_shutdown(self) -> None:
        logger.info("--- Initiating full application shutdown sequence ---")
        shutdown_successful = True

        # 1. Parar lógica de negócio e listeners de input do manager
        # É importante fazer isso antes de tentar destruir a GUI ou parar o tray,
        # pois podem tentar interagir com o manager ou a GUI.
        try:
            if hasattr(self, 'manager') and self.manager and \
               hasattr(self.manager, 'is_running') and self.manager.is_running:
                logger.info("Full shutdown: Calling manager.cleanup()")
                self.manager.cleanup() # Isso define is_running=False e para os listeners
            else:
                logger.info("Full shutdown: Manager cleanup skipped (manager not available, not running, or already cleaned up).")
        except Exception as e:
            logger.error(f"Full shutdown: Error during manager.cleanup(): {e}", exc_info=True)
            shutdown_successful = False

        # 2. Limpar a GUI e o ícone da bandeja
        # _gui_cleanup para o ícone da bandeja e join no thread.
        try:
            logger.info("Full shutdown: Calling _gui_cleanup()")
            self._gui_cleanup() # Stops tray icon, joins tray thread
        except Exception as e:
            logger.error(f"Full shutdown: Error during _gui_cleanup(): {e}", exc_info=True)
            shutdown_successful = False

        # 3. Destruir a janela principal do Tkinter
        # Isso deve fazer o root.mainloop() retornar se ainda estiver ativo.
        try:
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                logger.info("Full shutdown: Attempting to destroy Tkinter root window.")
                self.root.destroy()
                logger.info("Full shutdown: Tkinter root window destroy() called.")
            else:
                logger.info("Full shutdown: Tkinter root window destruction skipped (root not available or already destroyed).")
        except tk.TclError as e:
                logger.warning(f"Full shutdown: TclError during root.destroy(): {e}. Window might already be destroyed.")
                # Potentially not a critical failure for shutdown itself if window is already gone.
        except Exception as e_destroy_root: # Renomeado para evitar conflito com 'e' anterior se estivesse no mesmo escopo
            logger.error(f"Full shutdown: Unexpected error during root.destroy(): {e_destroy_root}", exc_info=True)
            shutdown_successful = False # A failure here could be problematic

        if shutdown_successful:
            logger.info("--- Full application shutdown sequence substantially complete. Attempting sys.exit(0). ---")
        else:
            logger.warning("--- Full application shutdown sequence encountered errors. Attempting sys.exit(0) anyway. ---")

        sys.exit(0) # Força a saída do interpretador Python.
        # Se o processo ainda travar após isso, é provável que seja devido a threads/recursos não Python
        # ou um problema com o próprio sys.exit() neste ambiente/contexto.
        logger.critical("--- sys.exit(0) foi chamado, mas a execução continuou. Isso indica um problema profundo. ---") # Não deve ser alcançado

    def _ensure_suggestion_popup(self) -> MacroSuggestionPopup:
        logger.debug(f"Entering _ensure_suggestion_popup. Popup exists: {self.suggestion_popup is not None and self.suggestion_popup.winfo_exists()}")
        if not self.suggestion_popup or not self.suggestion_popup.winfo_exists():
            logger.info("Creating new MacroSuggestionPopup instance.")
            self.suggestion_popup = MacroSuggestionPopup(self.root, self.manager.expansions.copy(), self.manager, self._on_suggestion_popup_closed)
        else:
             logger.debug("Reusing existing MacroSuggestionPopup instance.")
             self.suggestion_popup.all_macros_dict = self.manager.expansions.copy()
        logger.debug("Exiting _ensure_suggestion_popup.")
        return self.suggestion_popup

    def _on_suggestion_popup_closed(self) -> None:
        manager_active = self.manager.suggestion_popup_active
        logger.debug(f"Popup closed callback. manager.current_typed: '{self.manager.current_typed}', is_applying: {self.manager.is_applying_macro_flag}, manager_popup_active: {manager_active}")
        if manager_active and not self.manager.is_applying_macro_flag: self.manager.current_typed = ""
        self.manager.suggestion_popup_active = False
        logger.debug(f"Popup closed. manager.current_typed: '{self.manager.current_typed}', popup_active: {self.manager.suggestion_popup_active}")

    def _process_suggestion_request(self, command: str, data: Optional[Any]) -> None:
        logger.debug(f"GUI _process_suggestion_request: command='{command}', data='{data}'")
        if command == "show" and not self.manager.expansions: logger.warning("SHOW: No expansions loaded.")
        if command=="show" and self.manager.suggestion_popup_active and self.suggestion_popup and self.suggestion_popup.is_active():
            filter_val = data.get("filter",self.manager.current_typed) if isinstance(data,dict) else self.manager.current_typed
            logger.warning(f"SHOW: Popup already active. Updating filter: '{filter_val}'.");popup=self._ensure_suggestion_popup();popup.update_suggestions(filter_val or "/");return
        popup=self._ensure_suggestion_popup()
        if command=="show":
            self.manager.suggestion_popup_active=True
            mx,my=self.root.winfo_pointerx(),self.root.winfo_pointery();tx,ty=mx,my+25
            pwg,pmhg=480,450;am=None
            try:
                mons=get_monitors()
                for m in mons:
                    if m.x<=mx<m.x+m.width and m.y<=my<m.y+m.height:am=m;break
                if not am and mons:am=mons[0]
            except Exception as e:logger.error(f"Monitor info error: {e}",exc_info=True)
            if am:
                mox,moy,mow,moh=am.x,am.y,am.width,am.height
                if ty+pmhg>moy+moh-10:ty=my-pmhg-30
                ty=max(moy+5,ty);tx=max(mox+5,min(tx,mox+mow-pwg-5))
            else:
                sw,sh=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
                if ty+pmhg>sh-10:ty=my-pmhg-30
                ty=max(0,ty);tx=max(0,min(tx,sw-pwg-10))
            logger.debug(f"Positioning popup: +{int(tx)}+{int(ty)}");popup.geometry(f"+{int(tx)}+{int(ty)}")
            filter_val_show=data.get("filter",self.manager.current_typed) if isinstance(data,dict) else self.manager.current_typed
            popup.update_suggestions(filter_val_show or "/")
        elif command=="update":
            if popup.is_active() and data and "filter" in data:popup.update_suggestions(data["filter"])
            elif not popup.is_active() and self.manager.suggestion_popup_active:logger.warning("Update: popup not active, manager thought so. Syncing.");self._on_suggestion_popup_closed()
        elif command=="hide":
            if popup.is_active():popup.close_popup()
            elif self.manager.suggestion_popup_active:logger.debug("Hide: popup not visible, manager thought so. Syncing.");self._on_suggestion_popup_closed()
        elif command=="navigate":
            if popup.is_active():popup.handle_external_key(data)
        elif command=="select_or_close":
            if popup.is_active():logger.debug(f"select_or_close: manager.current_typed='{data}'");popup.handle_external_key("enter")
            else: logger.debug("select_or_close: popup not active. Syncing.");
            if self.manager.suggestion_popup_active:self._on_suggestion_popup_closed()

def main():
    logger.info(f"Application starting... Running as admin: {is_admin()}")
    app_instance = None
    try:
        if os.name == 'nt':
            try:
                windll.shcore.SetProcessDpiAwareness(2)
                logger.info("Set DPI awareness to Per-Monitor v2.")
            except (AttributeError, OSError):
                try:
                    windll.user32.SetProcessDPIAware()
                    logger.info("Set DPI awareness to System Aware.")
                except (AttributeError, OSError):
                    logger.warning("Could not set DPI awareness. GUI might appear blurry on high-DPI screens.")
            except Exception as e_dpi:
                 logger.error(f"An unexpected error occurred while setting DPI awareness: {e_dpi}")

        manager = MacroManager()
        root = ctk.CTk()
        app_instance = MacroGUI(root, manager)

        atexit.register(app_instance._perform_full_shutdown)

        manager.start_listener()

        logger.info("Starting Tkinter mainloop...")
        root.mainloop()
        logger.info("Tkinter mainloop finished.")

    except SystemExit as e:
        logger.info(f"App exited via SystemExit (code: {e.code}). Atexit hooks should run.")
    except KeyboardInterrupt:
        logger.info("App interrupted by user (KeyboardInterrupt). Atexit hooks should run.")
    except Exception as e_main:
        logger.critical(f"Unhandled critical exception in main function: {e_main}", exc_info=True)
    finally:
        logger.info("Main function's 'finally' block reached. Normal exit or post-exception.")
        if app_instance and hasattr(app_instance, 'manager') and app_instance.manager and \
           hasattr(app_instance.manager, 'is_running') and app_instance.manager.is_running:
             logger.warning("Main finally: Manager 'is_running' is still true.")
        elif app_instance and hasattr(app_instance, 'manager') and app_instance.manager and \
             hasattr(app_instance.manager, 'is_running') and not app_instance.manager.is_running:
             logger.info("Main finally: Manager 'is_running' is false, indicating cleanup likely occurred.")


if __name__ == "__main__":
    main()
    logger.info("Application __main__ block finished.")
