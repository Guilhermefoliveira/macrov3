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
