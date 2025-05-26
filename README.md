# Macro Manager - Gerenciador de Macros Avançado

Um aplicativo de desktop para Windows que permite criar, gerenciar e utilizar macros de texto para aumentar sua produtividade. Possui uma interface gráfica moderna construída com CustomTkinter, integração com a bandeja do sistema e diversas funcionalidades para facilitar o seu dia a dia.

![Placeholder para Screenshot do MacroManager](placeholder.png)

## Funcionalidades Principais

* **Criação e Gerenciamento de Macros:** Adicione, edite e remova macros de texto facilmente através de uma interface gráfica intuitiva.
* **Atalho Global:** Ative o menu de sugestão de macros rapidamente com o atalho `CTRL + ESPAÇO`.
* **Menu de Sugestão Inteligente:**
    * Filtre macros digitando parte do atalho.
    * Navegue pelas sugestões usando as teclas de seta.
    * Aplique a macro selecionada com `Enter`, `Tab`, `Espaço` ou clicando diretamente sobre ela.
* **Aplicação Automática:** A macro selecionada é automaticamente colada na aplicação ativa após o atalho digitado ser apagado.
* **Persistência de Dados:** Suas macros são salvas localmente em um arquivo `expansions.json` na pasta de dados do usuário (ex: `%APPDATA%/MacroManagerV3`).
* **Integração com a Bandeja do Sistema (System Tray):**
    * Minimize o aplicativo para a bandeja para mantê-lo rodando discretamente.
    * Restaure a janela ou saia do aplicativo pelo menu da bandeja.
    * Ícone personalizado na bandeja.
* **Notificações:** Receba notificações visuais ao aplicar uma macro.
* **Tema Escuro:** Interface agradável com suporte a tema escuro (via CustomTkinter e tema Azure Tcl).
* **Portabilidade:** Pode ser buildado como um executável para rodar em outras máquinas Windows sem necessidade de instalação do Python.

## Tecnologias Utilizadas

* **Python 3.x**
* **CustomTkinter:** Para a interface gráfica moderna.
* **Tkinter (ttk):** Usado para alguns widgets como o Treeview.
* **Keyboard:** Para detecção de hotkeys globais e simulação de entrada de teclado.
* **Pyperclip:** Para interações com a área de transferência (copiar/colar).
* **Pystray:** Para criar e gerenciar o ícone na bandeja do sistema.
* **Pillow (PIL):** Para manipulação de imagens (criação do ícone da bandeja).
* **psutil:** Para gerenciamento de processos (usado no cleanup).
* **screeninfo:** Para obter informações dos monitores e posicionar o popup.
* **JSON:** Para armazenamento das macros.

## Pré-requisitos

Para executar o script diretamente (ambiente de desenvolvimento):

* Python 3.9 ou superior.
* `pip` (gerenciador de pacotes Python).

## Configuração do Ambiente de Desenvolvimento

1.  **Clone o repositório (se estiver no GitHub):**
    ```bash
    git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
    cd seu-repositorio
    ```

2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    Crie um arquivo `requirements.txt` com o seguinte conteúdo:
    ```txt
    customtkinter
    keyboard
    pyperclip
    pystray
    Pillow
    psutil
    screeninfo
    ```
    E então instale:
    ```bash
    pip install -r requirements.txt
    ```

## Como Usar

1.  **Executando o Aplicativo:**
    * No ambiente de desenvolvimento: `python macrov3.py` (ou o nome do seu script principal).
    * Se tiver buildado um executável: execute o arquivo `.exe` gerado.

2.  **Gerenciando Macros:**
    * A janela principal exibirá a lista de macros existentes.
    * Use os botões "Adicionar Macro", "Remover Selecionada" e "Editar Selecionada" para gerenciar suas macros.
    * Os atalhos de macro devem começar com `/` (ex: `/saudacao`).

3.  **Usando Macros:**
    * Em qualquer campo de texto de outra aplicação, pressione `CTRL + ESPAÇO`.
    * O menu de sugestão de macros aparecerá próximo ao cursor do mouse.
    * Comece a digitar o atalho da macro (ex: `/sa`) para filtrar a lista.
    * Use as **teclas de seta para cima/baixo** para navegar na lista filtrada.
    * Pressione **Enter**, **Tab** ou **Espaço** para aplicar a macro selecionada.
    * Alternativamente, **clique com o botão esquerdo do mouse** diretamente sobre a macro desejada no menu para aplicá-la.
    * O texto do atalho que você digitou será apagado e o conteúdo da macro será colado.

4.  **Bandeja do Sistema:**
    * Clicar no botão "X" (fechar) da janela principal minimizará o aplicativo para a bandeja do sistema.
    * Clique com o botão direito no ícone da bandeja para "Restaurar" a janela ou "Sair" do aplicativo.
    * Um duplo clique (ou clique esquerdo, dependendo da configuração) no ícone da bandeja também deve restaurar a janela.

## Geração do Executável (Build)

Este projeto utiliza o PyInstaller para criar um executável para Windows.

1.  **Instale o PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Certifique-se de que os arquivos de dados estão presentes:**
    * `expansions.json` (pode ser um arquivo inicial vazio ou com macros padrão).
    * `azure.tcl` (seu arquivo Tcl que carrega o tema).
    * A pasta `theme/` completa do tema Azure Tcl.
    * (Opcional) `resources/icon.ico` ou `icon.ico` para o ícone do executável.
    Todos esses arquivos devem estar no mesmo diretório que o seu script principal (`macrov3.py`) e o arquivo `.spec` durante o processo de build.

3.  **Use o arquivo `.spec` fornecido (ou ajustado):**
    O arquivo `macrov3.spec` (ou o nome que você deu) já está configurado para incluir as dependências e arquivos de dados necessários.

4.  **Execute o PyInstaller com o arquivo `.spec`:**
    Abra o terminal no diretório do projeto e execute:
    ```bash
    pyinstaller macrov3.spec
    ```

5.  **Resultado:**
    * O PyInstaller criará as pastas `build/` e `dist/`.
    * Dentro de `dist/MacroManager/` (ou o nome definido em `app_name` no seu `.spec`), você encontrará o `MacroManager.exe` e todos os arquivos de suporte.
    * Para distribuir o aplicativo, copie toda a pasta `dist/MacroManager/`.

    * **Para um único arquivo `.exe` (opcional):**
        ```bash
        pyinstaller --onefile macrov3.spec
        ```
        Isso criará `dist/MacroManager.exe`. Este método pode ter um tempo de inicialização um pouco maior.

## Estrutura de Arquivos Esperada (para Desenvolvimento e Build)
```
SeuProjeto/
├── macrov3.py        (ou o nome do seu script principal)
├── macrov3.spec      (arquivo de especificação do PyInstaller)
├── expansions.json   (arquivo inicial de macros)
├── azure.tcl         (arquivo Tcl para carregar o tema Azure)
├── theme/            (pasta completa do tema Azure Tcl)
│   ├── pkgIndex.tcl
│   ├── azuredark.tcl
│   ├── azurelight.tcl
│   └── azure/
│       └── (widgets, imagens .png, etc.)
├── resources/        (opcional, para ícones)
│   └── icon.ico
└── README.md
 ```

## Possíveis Melhorias Futuras

* Opção para importar/exportar macros.
* Configuração de hotkey personalizável pelo usuário.
* Suporte a mais temas visuais ou personalização de cores.
* Pré-visualização completa da macro no menu de sugestão (talvez em um tooltip).
* Busca mais avançada nas macros (não apenas pelo início do atalho).
* Suporte a macros com múltiplas linhas de forma mais robusta na edição/criação.

## Como Contribuir

Contribuições são bem-vindas! Se você tiver ideias para melhorias, encontrar bugs ou quiser adicionar novas funcionalidades:

1.  Faça um Fork do projeto.
2.  Crie uma Branch para sua feature (`git checkout -b feature/MinhaFeature`).
3.  Faça commit de suas mudanças (`git commit -m 'Adiciona MinhaFeature'`).
4.  Faça Push para a Branch (`git push origin feature/MinhaFeature`).
5.  Abra um Pull Request.

## Licença
