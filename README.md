# Gerenciador de Macros

Este é um aplicativo em Python para gerenciar macros que substituem atalhos (prefixados por `!`) por textos definidos pelo usuário. Ideal para facilitar e automatizar tarefas repetitivas.

## Funcionalidades

- **Adicionar macros**: Permite criar atalhos personalizados que são expandidos para textos maiores.
- **Remover macros**: Exclui atalhos que não são mais necessários.
- **Visualizar macros disponíveis**: Exibe uma lista de todas as macros criadas.

## Tecnologias Utilizadas

- Python
- Bibliotecas:
  - `tkinter`: Para a interface gráfica.
  - `keyboard`: Para captura de teclas.
  - `pyperclip`: Para copiar e colar textos.
  - `json`: Para salvar e carregar as macros criadas.

## Como Funciona

1. **Atalhos**: Todos os atalhos devem começar com `!`. Quando digitado um atalho definido, ele será automaticamente substituído pelo texto correspondente.
2. **Interface gráfica**: O programa oferece uma interface simples para gerenciar as macros.
3. **Armazenamento**: As macros são salvas em um arquivo `expansions.json`, garantindo a persistência dos dados.

## Como Usar

### Pré-requisitos

- Python 3.6 ou superior.
- As bibliotecas necessárias podem ser instaladas com o seguinte comando:
  ```bash
  pip install keyboard pyperclip
## Executar o Programa

1. Baixe ou clone este repositório.
2. Execute o script principal:
   ```bash
   python nome_do_script.py

## Funcionalidades

### Adicionar Macro

1. Clique no botão **Adicionar Macro**.
2. Preencha os campos:
   - **Atalho**: Deve começar com `!`.
   - **Texto da Macro**: Texto que será inserido quando o atalho for digitado.
3. Clique em **Salvar**.

### Remover Macro

1. Clique no botão **Remover Macro**.
2. Informe o atalho (começando com `!`) que deseja remover.
3. Clique em **Remover**.

### Substituição Automática

1. Digite o atalho em qualquer editor de texto ou campo.
2. Ao pressionar **espaço** ou **enter**, o atalho será substituído pelo texto correspondente.

## Exemplo

- **Adicionando a Macro**:
  - **Atalho**: `!email`
  - **Texto da Macro**: `meuemail@exemplo.com`
- Ao digitar `!email` e pressionar espaço, o texto será automaticamente expandido para `meuemail@exemplo.com`.

## Estrutura do Projeto

```bash
├── expansions.json    # Arquivo de armazenamento das macros
├── script.py          # Código principal do aplicativo

Licença
Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para mais informações.
