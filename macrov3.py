import tkinter as tk
from tkinter import messagebox, ttk, Toplevel, Text, Button
import keyboard
import pyperclip
import time
import json
import os

EXPANSIONS_FILE = "expansions.json"

if not os.path.exists(EXPANSIONS_FILE):
    with open(EXPANSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

with open(EXPANSIONS_FILE, "r", encoding="utf-8") as f:
    expansions = json.load(f)

current_typed = ""

def on_key_press(event):
    global current_typed
    if event.name in ["space", "enter"]:
        if current_typed.startswith("!") and current_typed in expansions:
            for _ in range(len(current_typed) + 1):
                keyboard.send("backspace")
            time.sleep(0.05)
            pyperclip.copy(expansions[current_typed])
            time.sleep(0.05)
            keyboard.press_and_release("ctrl+v")
        current_typed = ""
    elif event.name == "backspace":
        current_typed = current_typed[:-1] if current_typed else ""
    elif len(event.name) == 1:
        current_typed += event.name

def adicionar_macro_gui():
    def salvar_macro():
        shortcut = entrada_shortcut.get().strip()
        texto = entrada_texto.get("1.0", tk.END).strip()
        if not shortcut.startswith("!"):
            messagebox.showerror("Erro", "O atalho deve começar com '!'")
            return
        if shortcut in expansions:
            messagebox.showerror("Erro", f"O atalho '{shortcut}' já existe.")
            return
        expansions[shortcut] = texto
        with open(EXPANSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(expansions, f, ensure_ascii=False, indent=4)
        messagebox.showinfo("Sucesso", f"Macro '{shortcut}' adicionada com sucesso!")
        atualizar_lista()
        janela.destroy()

    janela = Toplevel(root)
    janela.title("Adicionar Macro")
    janela.geometry("400x500")

    container = ttk.Frame(janela, padding=10)
    container.pack(fill="both", expand=True)

    tk.Label(container, text="Atalho (começar com '!')").pack(anchor="w", pady=5)
    entrada_shortcut = tk.Entry(container, width=30)
    entrada_shortcut.pack(fill="x", pady=5)

    tk.Label(container, text="Texto da Macro").pack(anchor="w", pady=5)
    entrada_texto = Text(container, width=40, height=10)
    entrada_texto.pack(fill="both", expand=True, pady=5)

    btn_container = ttk.Frame(container)
    btn_container.pack(fill="x", pady=10)
    Button(btn_container, text="Salvar", command=salvar_macro).pack(side="right")

def remover_macro_gui():
    def confirmar_remocao():
        shortcut = entrada_shortcut.get().strip()
        if shortcut in expansions:
            del expansions[shortcut]
            with open(EXPANSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(expansions, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Sucesso", f"Macro '{shortcut}' removida com sucesso!")
            atualizar_lista()
        else:
            messagebox.showerror("Erro", f"Não existe macro '{shortcut}'.")
        janela.destroy()

    janela = Toplevel(root)
    janela.title("Remover Macro")
    janela.geometry("300x150")

    container = ttk.Frame(janela, padding=10)
    container.pack(fill="both", expand=True)

    tk.Label(container, text="Atalho para remover").pack(anchor="w", pady=5)
    entrada_shortcut = tk.Entry(container, width=30)
    entrada_shortcut.pack(fill="x", pady=5)

    btn_container = ttk.Frame(container)
    btn_container.pack(fill="x", pady=10)
    Button(btn_container, text="Remover", command=confirmar_remocao).pack(side="right")

def editar_macro_gui():
    def salvar_edicao():
        antigo_shortcut = entrada_atual_shortcut.get().strip()
        novo_shortcut = entrada_novo_shortcut.get().strip()
        novo_texto = entrada_texto.get("1.0", tk.END).strip()

        if not novo_shortcut.startswith("!"):
            messagebox.showerror("Erro", "O atalho deve começar com '!'")
            return

        if novo_shortcut in expansions and antigo_shortcut != novo_shortcut:
            messagebox.showerror("Erro", f"O atalho '{novo_shortcut}' já existe.")
            return

        if antigo_shortcut in expansions:
            del expansions[antigo_shortcut]
        expansions[novo_shortcut] = novo_texto

        with open(EXPANSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(expansions, f, ensure_ascii=False, indent=4)

        messagebox.showinfo("Sucesso", f"Macro '{antigo_shortcut}' editada com sucesso!")
        atualizar_lista()
        janela.destroy()

    selected_item = lista_macros.selection()
    if not selected_item:
        messagebox.showerror("Erro", "Nenhuma macro selecionada.")
        return

    item = lista_macros.item(selected_item)
    antigo_shortcut = item["values"][0]
    antigo_texto = expansions[antigo_shortcut]

    janela = Toplevel(root)
    janela.title("Editar Macro")
    janela.geometry("400x500")

    container = ttk.Frame(janela, padding=10)
    container.pack(fill="both", expand=True)

    tk.Label(container, text="Atalho Atual").pack(anchor="w", pady=5)
    entrada_atual_shortcut = tk.Entry(container, width=30)
    entrada_atual_shortcut.insert(0, antigo_shortcut)
    entrada_atual_shortcut.configure(state="readonly")
    entrada_atual_shortcut.pack(fill="x", pady=5)

    tk.Label(container, text="Novo Atalho (começar com '!')").pack(anchor="w", pady=5)
    entrada_novo_shortcut = tk.Entry(container, width=30)
    entrada_novo_shortcut.insert(0, antigo_shortcut)
    entrada_novo_shortcut.pack(fill="x", pady=5)

    tk.Label(container, text="Novo Texto da Macro").pack(anchor="w", pady=5)
    entrada_texto = Text(container, width=40, height=10)
    entrada_texto.insert("1.0", antigo_texto)
    entrada_texto.pack(fill="both", expand=True, pady=5)

    btn_container = ttk.Frame(container)
    btn_container.pack(fill="x", pady=10)
    Button(btn_container, text="Salvar", command=salvar_edicao).pack(side="right")

def atualizar_lista():
    lista_macros.delete(*lista_macros.get_children())
    for key, val in expansions.items():
        texto_curto = (val[:50] + "...") if len(val) > 50 else val
        lista_macros.insert("", "end", values=(key, texto_curto))

root = tk.Tk()
root.title("Gerenciador de Macros")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Label(frame, text="Macros disponíveis:").grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)

lista_macros = ttk.Treeview(frame, columns=("Atalho", "Texto"), show="headings", height=10)
lista_macros.heading("Atalho", text="Atalho")
lista_macros.heading("Texto", text="Texto")
lista_macros.column("Atalho", width=150)
lista_macros.column("Texto", width=300)
lista_macros.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E))

btn_adicionar = ttk.Button(frame, text="Adicionar Macro", command=adicionar_macro_gui)
btn_adicionar.grid(row=2, column=0, sticky=tk.W, pady=5)

btn_remover = ttk.Button(frame, text="Remover Macro", command=remover_macro_gui)
btn_remover.grid(row=2, column=1, sticky=tk.E, pady=5)

btn_editar = ttk.Button(frame, text="Editar Macro", command=editar_macro_gui)
btn_editar.grid(row=2, column=2, sticky=tk.E, pady=5)

atualizar_lista()

keyboard.on_press(on_key_press)

try:
    root.mainloop()
except KeyboardInterrupt:
    print("Saindo...")

keyboard.wait()
