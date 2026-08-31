# Garagem Inteligente com ESP32

Projeto acadêmico de uma garagem automatizada controlada por uma aplicação web local. O sistema permite abrir, fechar e parar um portão usando um **ESP32**, com uma interface desenvolvida em **Python e Flask**.

## Demonstração

[Assistir ao vídeo do projeto no YouTube](https://www.youtube.com/shorts/G7s2tEDibgQ)

## Funcionalidades

- Controle de abertura, fechamento e parada do portão.
- Login de usuários.
- Perfis de administrador e usuário comum.
- Cadastro e gerenciamento de usuários.
- Histórico de comandos realizados.
- Configuração do endereço IP do ESP32.
- Interface responsiva para computador e celular.
- LEDs para indicar o estado do portão.

## Tecnologias utilizadas

- Python
- Flask
- SQLite
- HTML, CSS e JavaScript
- ESP32
- Arduino Framework
- Biblioteca ESP32Servo

## Componentes principais

- ESP32
- Servo motor
- LED verde e LED vermelho
- Resistores e cabos de conexão
- Protoboard e fonte de alimentação

## Como executar

1. Clone o repositório:

```bash
git clone https://github.com/andreyalmeidaa/garage-esp32-local.git
cd garage-esp32-local
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Defina uma chave para o Flask. No Windows PowerShell:

```powershell
$env:FLASK_SECRET_KEY="coloque-uma-chave-segura-aqui"
```

4. Execute a aplicação:

```bash
python app.py
```

5. Acesse `http://127.0.0.1:5000` no navegador.

Na primeira execução, o sistema cria o banco de dados e o usuário inicial:

- **Usuário:** `admin`
- **Senha:** `1234`

Altere essa senha após o primeiro acesso.

## Configuração do ESP32

Abra o arquivo `esp32/sketch_apr12a/sketch_apr12a.ino` na Arduino IDE, informe o nome e a senha da sua rede Wi-Fi, instale a biblioteca **ESP32Servo** e envie o código para a placa.

Depois, copie o IP exibido no Monitor Serial e informe-o na tela de configurações da aplicação.

## Observação

Este projeto foi desenvolvido para fins acadêmicos e para uso em rede local. Em uma instalação real, devem ser adicionados sensores de fim de curso, detecção de obstáculos e outros mecanismos de segurança.

## Autor

Desenvolvido por **Andrey Magalhães**.
