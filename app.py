import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, session, render_template, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_super_segura_aqui')

# Configurações do banco de dados MySQL - usando variáveis de ambiente para segurança
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'database': os.environ.get('DB_NAME'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True,
    'connection_timeout': 60,
    'raise_on_warnings': True
}

def get_db_connection():
    """Estabelece conexão com o banco de dados MySQL com retry"""
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                print("Conexão MySQL estabelecida com sucesso!")
                return connection
        except Error as e:
            retry_count += 1
            print(f"Tentativa {retry_count}/{max_retries} - Erro ao conectar com MySQL: {e}")
            if retry_count >= max_retries:
                print("Máximo de tentativas de conexão excedido")
                return None
    return None

def init_database():
    """Cria as tabelas de usuários, retirada e devolução se não existirem.
       Assume que qualquer ALTER TABLE necessário para colunas como user_id e ativo já foi feito manualmente."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # 1. Criar tabela users_from_bb (se não existir)
            create_users_table_query = """
            CREATE TABLE IF NOT EXISTS users_from_bb (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                cpf VARCHAR(11) UNIQUE NOT NULL,
                pais VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                telefone VARCHAR(20) NOT NULL,
                senha VARCHAR(255) NOT NULL,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_cpf (cpf)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_users_table_query)
            print("Tabela 'users_from_bb' criada ou já existe.")

            # 2. Criar tabela umbrella_retirada (se não existir, com as colunas finais esperadas e FK)
            create_umbrella_retirada_table_query = """
            CREATE TABLE IF NOT EXISTS umbrella_retirada (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                nome_usuario VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                telefone VARCHAR(50) NOT NULL,
                codigo_guarda_chuva VARCHAR(6) NOT NULL,
                data_retirada DATE NOT NULL,
                hora_retirada TIME NOT NULL,
                timestamp_retirada DATETIME DEFAULT CURRENT_TIMESTAMP,
                ativo BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users_from_bb(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_umbrella_retirada_table_query)
            print("Tabela 'umbrella_retirada' criada ou já existe (com colunas user_id, ativo e FK).")

            # 3. Criar tabela umbrella_devolucao (se não existir)
            create_umbrella_devolucao_table_query = """
            CREATE TABLE IF NOT EXISTS umbrella_devolucao (
                id INT AUTO_INCREMENT PRIMARY KEY,
                retirada_id INT NOT NULL,
                data_devolucao DATE NOT NULL,
                hora_devolucao TIME NOT NULL,
                cpf_usuario VARCHAR(11) NOT NULL,
                timestamp_devolucao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (retirada_id) REFERENCES umbrella_retirada(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_umbrella_devolucao_table_query)
            print("Tabela 'umbrella_devolucao' criada ou já existe.")

            connection.commit()

    except Error as e:
        print(f"Erro geral ao criar/atualizar tabelas: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

def validar_cpf(cpf):
    """Valida se o CPF tem 11 dígitos"""
    return re.match(r'^\d{11}$', cpf) is not None

def validar_email(email):
    """Valida formato do email"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def inserir_usuario(nome, cpf, pais, email, telefone, senha):
    """Insere um novo usuário no banco de dados"""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return False, "Erro de conexão com o banco de dados!"

        cursor = connection.cursor()

        # Verificar se CPF ou email já existem
        check_query = "SELECT id FROM users_from_bb WHERE cpf = %s OR email = %s"
        cursor.execute(check_query, (cpf, email))
        existing_user = cursor.fetchone()

        if existing_user:
            return False, "CPF ou email já cadastrados!"

        # Hash da senha para segurança
        senha_hash = generate_password_hash(senha)

        # Inserir novo usuário
        insert_query = """
        INSERT INTO users_from_bb (nome, cpf, pais, email, telefone, senha)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (nome, cpf, pais, email, telefone, senha_hash))
        connection.commit()

        print(f"Usuário cadastrado: {nome} - {email}")
        return True, "Usuário cadastrado com sucesso!"

    except Error as e:
        print(f"Erro ao inserir usuário: {e}")
        return False, f"Erro no banco de dados: {str(e)}"
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def verificar_login(email, senha):
    """Verifica as credenciais de login e retorna dados do usuário"""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return False, "Erro de conexão com o banco de dados!", None, None, None, None
        
        cursor = connection.cursor(dictionary=True)

        # Selecionar nome, email, telefone, CPF e ID
        query = "SELECT id, nome, email, telefone, cpf, senha FROM users_from_bb WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['senha'], senha):
            print(f"Login realizado: {user['nome']} - {user['email']}")
            # Retorna sucesso, nome, email, telefone, CPF e ID
            return True, user['nome'], user['email'], user['telefone'], user['cpf'], user['id']
        else:
            return False, "Email ou senha incorretos!", None, None, None, None

    except Error as e:
        print(f"Erro ao verificar login: {e}")
        return False, f"Erro no banco de dados: {str(e)}", None, None, None, None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Código HTML da tela de login (mantido o que você gostou)
html_code_for_index_page = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Bubble Support - Login Técnico</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
    <style>
        /* Variáveis CSS */
        :root {
            --primary-color: #007BFF;
            --main-bg-image: url('https://static8.depositphotos.com/1020804/816/i/450/depositphotos_8166031-stock-photo-abstract-background-night-sky-after.jpg');
        }

        /* Estilos base do corpo, adaptados para a tela de login */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-image: var(--main-bg-image);
            background-size: cover;
            background-position: center;
            background-repeat: repeat;
            display: flex;
            justify-content: center; /* Centraliza horizontalmente */
            align-items: center; /* Centraliza verticalmente */
            min-height: 100vh; /* Garante que ocupe a altura total da viewport */
            color: #333;
            overflow: hidden; /* Evita rolagem desnecessária no body principal */
        }

        /* Container principal do formulário */
        .container {
            background-color: rgba(255, 255, 255, 0.95); /* Fundo semi-transparente */
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            text-align: center;
            width: 100%;
            max-width: 450px; /* Largura máxima para o formulário */
            box-sizing: border-box; /* Inclui padding e borda na largura */
            position: relative; /* Para posicionamento das mensagens flash */
            animation: fadeIn 0.8s ease-out;
            max-height: 90vh; /* Limita a altura do container */
            overflow-y: auto; /* Permite rolagem vertical se o conteúdo for muito grande */
            padding-right: 20px; /* Adiciona padding para barra de rolagem */
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .container h2 {
            color: var(--primary-color);
            margin-bottom: 25px;
            font-size: 2.2em;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .container p {
            color: #555;
            margin-bottom: 30px;
            font-size: 1.1em;
        }

        /* Tabs de Login/Cadastro */
        .tabs {
            display: flex;
            margin-bottom: 30px;
            border-bottom: 2px solid #e0e0e0;
        }

        .tab-button {
            flex: 1;
            padding: 15px 0;
            cursor: pointer;
            font-size: 1.1em;
            font-weight: bold;
            color: #777;
            border: none;
            background-color: transparent;
            transition: color 0.3s ease, border-color 0.3s ease;
            position: relative;
        }

        .tab-button.active {
            color: var(--primary-color);
            border-bottom: 3px solid var(--primary-color);
        }

        .tab-button:hover:not(.active) {
            color: #444;
        }

        /* Estilos dos campos de formulário */
        .input-group {
            position: relative;
            margin-bottom: 25px;
            text-align: left; /* Alinha labels e ícones à esquerda */
        }

        .input-group i {
            position: absolute;
            left: 15px;
            /* AJUSTE PARA O ALINHAMENTO VERTICAL DOS ÍCONES */
            top: 50%; /* Mantém o ícone centralizado verticalmente */
            transform: translateY(-50%); /* Ajusta a posição exata baseada na sua própria altura */
            line-height: 1; /* Garante que a altura da linha não afete o alinhamento */
            /* FIM DO AJUSTE */
            color: #888;
            font-size: 1.1em;
        }

        .input-group label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-size: 0.95em;
            font-weight: bold;
        }

        .input-group input,
        .input-group select { /* Adicionado 'select' aqui para aplicar o mesmo estilo */
            width: calc(100% - 60px); /* Ajusta largura para acomodar padding e ícone */
            padding: 14px 15px 14px 40px; /* Mantido 40px para alinhar texto ao ícone */
            border: 1px solid #ccc;
            border-radius: 8px;
            font-size: 1em;
            color: #333;
            background-color: #f8f8f8;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
            box-sizing: border-box; /* Garante que padding e borda não aumentem a largura total */
            height: 44px; /* Altura fixa para inputs e selects para ajudar no alinhamento dos ícones */
        }

        .input-group input:focus,
        .input-group select:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 8px rgba(0, 123, 255, 0.2);
            outline: none;
        }

        /* Botões */
        .btn-submit {
            width: 100%;
            padding: 15px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.3s ease, transform 0.2s ease, box-shadow 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 123, 255, 0.2);
            margin-top: 20px;
        }

        .btn-submit:hover {
            background-color: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 7px 20px rgba(0, 123, 255, 0.3);
        }

        .form-footer {
            margin-top: 25px;
            font-size: 0.95em;
            color: #777;
        }

        .form-footer a {
            color: var(--primary-color);
            text-decoration: none;
            font-weight: bold;
            transition: color 0.3s ease;
        }

        .form-footer a:hover {
            color: #0056b3;
        }

        /* Flash Messages */
        .flash-messages-container {
            width: 100%;
            max-width: 450px; /* Alinha com a largura do container principal */
            margin-bottom: 20px;
            position: absolute; /* Posiciona absolutamente dentro do container */
            top: -70px; /* Ajuste conforme necessário para ficar acima do container */
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            text-align: center;
        }

        .flash-message, .flash-error {
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center; /* Centraliza o conteúdo da mensagem */
            gap: 10px;
            opacity: 1; /* Começa visível */
            transition: opacity 0.5s ease-out, transform 0.5s ease-out; /* Transição para fade out */
        }
        .flash-message.hide, .flash-error.hide {
            opacity: 0;
            transform: translateY(-20px); /* Move para cima enquanto some */
        }

        .flash-message {
            background-color: rgba(40, 167, 69, 0.1);
            border: 1px solid #28a745;
            color: #28a745;
        }
        .flash-error {
            background-color: rgba(220, 53, 69, 0.1);
            border: 1px solid #dc3545;
            color: #dc3545;
        }
        .flash-message i, .flash-error i {
            font-size: 1.2em;
        }
    </style>
</head>
<body>

<div class="container">
    {# Container para mensagens de flash #}
    <div class="flash-messages-container" id="flashMessagesContainer">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-{{ category }}">
                        {% if category == 'message' %}
                            <i class="fas fa-check-circle"></i>
                        {% else %}
                            <i class="fas fa-exclamation-triangle"></i>
                        {% endif %}
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
    </div>

    <h2>Bem-vindo ao Bubble SA!</h2>
    <p>Aceda à sua conta ou crie um novo registo de técnico.</p>

    <div class="tabs">
        <button class="tab-button active" id="loginTab">Autenticação</button>
        <button class="tab-button" id="cadastroTab">Registo</button>
    </div>

    {# Formulário de Login #}
    <form id="loginForm" class="form-content">
        <div class="input-group">
            <i class="fas fa-envelope"></i>
            <label for="loginEmail">E-mail Corporativo:</label>
            <input type="email" id="loginEmail" name="email_login" placeholder="seu.email@empresa.com" required>
        </div>
        <div class="input-group">
            <i class="fas fa-lock"></i>
            <label for="loginSenha">Palavra-passe:</label>
            <input type="password" id="loginSenha" name="senha_login" placeholder="********" required>
        </div>
        <button type="submit" class="btn-submit">Autenticar</button>
        <div class="form-footer">
            <a href="#">Esqueceu a palavra-passe?</a>
        </div>
    </form>

    {# Formulário de Cadastro (Inicialmente escondido) #}
    <form id="cadastroTecnicoForm" class="form-content" style="display: none;">
        <div class="input-group">
            <i class="fas fa-user"></i>
            <label for="nomeTecnico">Nome Completo:</label>
            <input type="text" id="nomeTecnico" name="nome" placeholder="Seu Nome Completo" required>
        </div>
        <div class="input-group">
            <i class="fas fa-id-card"></i> {# Novo ícone para CPF #}
            <label for="cpfCadastro">CPF (apenas números):</label>
            <input type="text" id="cpfCadastro" name="cpf" placeholder="Apenas 11 dígitos" required pattern="[0-9]{11}" maxlength="11">
        </div>
        <div class="input-group">
            <i class="fas fa-globe"></i> {# Novo ícone para País #}
            <label for="paisCadastro">País:</label>
            <select name="pais" id="paisCadastro" required>
                <option value="">Selecione seu país</option>
                <option value="Brasil">Brasil</option>
                <option value="Portugal">Portugal</option>
                <option value="Estados Unidos">Estados Unidos</option>
                <option value="Argentina">Argentina</option>
                <option value="Outro">Outro</option>
            </select>
        </div>
        <div class="input-group">
            <i class="fas fa-phone"></i> {# Novo ícone para Telefone #}
            <label for="telefoneCadastro">Telefone:</label>
            <input type="text" id="telefoneCadastro" name="telefone" placeholder="Com DDD" required>
        </div>
        <div class="input-group">
            <i class="fas fa-envelope"></i>
            <label for="emailCorporativo">E-mail Corporativo:</label>
            <input type="email" id="emailCorporativo" name="email" placeholder="seu.email@empresa.com" required>
        </div>
        <div class="input-group">
            <i class="fas fa-lock"></i>
            <label for="senha">Criar Palavra-passe:</label>
            <input type="password" id="senha" name="senha" placeholder="********" required>
        </div>
        <button type="submit" class="btn-submit">Registar</button>
    </form>
</div>

<script>
    const loginTab = document.getElementById('loginTab');
    const cadastroTab = document.getElementById('cadastroTab');
    const loginForm = document.getElementById('loginForm');
    const cadastroTecnicoForm = document.getElementById('cadastroTecnicoForm');
    const flashMessagesContainer = document.getElementById('flashMessagesContainer');

    loginTab.addEventListener('click', () => {
        loginTab.classList.add('active');
        cadastroTab.classList.remove('active');
        loginForm.style.display = 'block';
        cadastroTecnicoForm.style.display = 'none';
        // Limpar mensagens de flash ao trocar de aba
        if (flashMessagesContainer) flashMessagesContainer.innerHTML = ''; 
    });

    cadastroTab.addEventListener('click', () => {
        cadastroTab.classList.add('active');
        loginTab.classList.remove('active');
        loginForm.style.display = 'none';
        cadastroTecnicoForm.style.display = 'block';
        // Limpar mensagens de flash ao trocar de aba
        if (flashMessagesContainer) flashMessagesContainer.innerHTML = '';
    });

    // Função para exibir mensagem de flash (simulada, pois o Flask já faz isso)
    function showFlashMessage(message, category) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flash-${category}`;
        messageDiv.innerHTML = `
            <i class="fas fa-${category === 'message' ? 'check-circle' : 'exclamation-triangle'}"></i>
            ${message}
        `;
        if (flashMessagesContainer) {
            flashMessagesContainer.appendChild(messageDiv);
            setTimeout(() => {
                messageDiv.classList.add('hide');
                messageDiv.addEventListener('transitionend', () => {
                    messageDiv.remove();
                });
            }, 5000);
        }
    }

    // Lógica de envio de formulário para login (AJAX)
    loginForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(loginForm);
        const data = Object.fromEntries(formData.entries());

        fetch('/login', { // Rota de login
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(data).toString(),
        })
        .then(response => {
            // Se a resposta não for OK (e.g., 400, 401), lê como JSON para pegar a mensagem de erro
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(result => {
            if (result.success && result.redirect) {
                window.location.href = result.redirect;
            } else {
                // Se o Flask retornar success: false, a mensagem de erro já virá no flash.
                // Mas aqui podemos adicionar um log para depuração.
                console.error("Erro no login:", result.message);
                showFlashMessage(result.message || "Erro no login.", "error"); // Exibir mensagem de erro
            }
        })
        .catch(error => {
            console.error('Erro na requisição ou no servidor:', error);
            showFlashMessage(error.message || "Requisição falhou. Tente novamente.", "error"); // Exibir erro de requisição
        });
    });

    // Lógica de envio de formulário para cadastro (AJAX)
    cadastroTecnicoForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(cadastroTecnicoForm);
        const data = Object.fromEntries(formData.entries());

        fetch('/cadastrar', { // Rota de cadastro
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(data).toString(),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(result => {
            if (result.success && result.redirect) {
                window.location.href = result.redirect; // Redireciona para a nova tela
            } else {
                console.error("Erro no cadastro:", result.message);
                showFlashMessage(result.message || "Erro no cadastro.", "error"); // Exibir mensagem de erro
            }
        })
        .catch(error => {
            console.error('Erro na requisição ou no servidor:', error);
            showFlashMessage(error.message || "Requisição falhou. Tente novamente.", "error"); // Exibir erro de requisição
        });
    });

    // Faz as mensagens de flash sumirem automaticamente
    document.addEventListener('DOMContentLoaded', function() {
        if (flashMessagesContainer) {
            const messages = flashMessagesContainer.querySelectorAll('.flash-message, .flash-error');
            messages.forEach(messageDiv => {
                setTimeout(() => {
                    messageDiv.classList.add('hide');
                    messageDiv.addEventListener('transitionend', () => {
                        messageDiv.remove();
                    });
                }, 5000);
            });
        }
    });
</script>

</body>
</html>
"""

@app.route('/')
def index():
    # Verifica se o usuário já está logado
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(html_code_for_index_page)

@app.route('/health')
def health_check():
    """Health check endpoint para o Render"""
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            return {"status": "healthy", "database": "connected"}, 200
        else:
            return {"status": "unhealthy", "database": "disconnected"}, 503
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    nome = request.form.get('nome', '').strip()
    cpf = request.form.get('cpf', '').strip()
    pais = request.form.get('pais', '').strip()
    email = request.form.get('email', '').strip().lower()
    telefone = request.form.get('telefone', '').strip()
    senha = request.form.get('senha', '')

    # Validações
    if not all([nome, cpf, pais, email, telefone, senha]):
        flash('Todos os campos são obrigatórios!', 'error')
        return jsonify({"success": False, "message": "Todos os campos são obrigatórios!"})

    if not validar_cpf(cpf):
        flash('CPF deve conter exatamente 11 dígitos!', 'error')
        return jsonify({"success": False, "message": "CPF deve conter exatamente 11 dígitos!"})

    if not validar_email(email):
        flash('Por favor, digite um email válido!', 'error')
        return jsonify({"success": False, "message": "Por favor, digite um email válido!"})

    if len(senha) < 6:
        flash('A senha deve ter pelo menos 6 caracteres!', 'error')
        return jsonify({"success": False, "message": "A senha deve ter pelo menos 6 caracteres!"})

    # Inserir no banco de dados
    sucesso, mensagem = inserir_usuario(nome, cpf, pais, email, telefone, senha)

    if sucesso:
        flash(mensagem, 'message')
        return jsonify({"success": True, "message": mensagem, "redirect": url_for('index')}) 
    else:
        flash(mensagem, 'error')
        return jsonify({"success": False, "message": mensagem})

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email_login', '').strip().lower()
    senha = request.form.get('senha_login', '')

    if not email or not senha:
        flash('Email e senha são obrigatórios!', 'error')
        return jsonify({"success": False, "message": "Email e senha são obrigatórios!"})

    sucesso, user_name, user_email, user_phone, user_cpf, user_id = verificar_login(email, senha)
    
    if sucesso:
        session['user_id'] = user_id
        session['user_name'] = user_name
        session['email'] = user_email
        session['phone'] = user_phone
        session['cpf'] = user_cpf # Salva o CPF na sessão
        flash(f'Bem-vindo de volta, {user_name}!', 'message')
        return jsonify({"success": True, "message": f'Bem-vindo de volta, {user_name}!', "redirect": url_for('dashboard')})
    else:
        flash(user_name, 'error') # user_name aqui conterá a mensagem de erro
        return jsonify({"success": False, "message": user_name})

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        has_umbrella = check_user_has_umbrella(user_id) # Verifica se o usuário tem guarda-chuva retirado
        # Renderiza 'user_dashboard.html' e passa a variável has_umbrella
        return render_template('user_dashboard.html', user_name=session['user_name'], has_umbrella=has_umbrella)
    else:
        flash('Você precisa fazer login para acessar esta página.', 'error')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('email', None)
    session.pop('phone', None)
    session.pop('cpf', None) # Remove CPF da sessão
    flash('Você foi desconectado.', 'message')
    return redirect(url_for('index'))

# --- Funções Auxiliares para Guarda-Chuva ---

def check_user_has_umbrella(user_id):
    """Verifica se o usuário tem um guarda-chuva ativo (não devolvido)"""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            print("Erro de conexão ao verificar guarda-chuva do usuário.")
            return False # Assume que não tem se não consegue conectar
        
        cursor = connection.cursor(dictionary=True)
        # Verifica se há alguma retirada ativa para o user_id
        query = "SELECT id FROM umbrella_retirada WHERE user_id = %s AND ativo = TRUE ORDER BY timestamp_retirada DESC LIMIT 1"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        return result is not None
    except Error as e:
        print(f"Erro ao verificar guarda-chuva ativo para user_id {user_id}: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# --- ROTA PARA REGISTRAR RETIRADA DE GUARDA-CHUVA ---
@app.route('/registrar_retirada', methods=['POST'])
def registrar_retirada():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Não autenticado. Faça login para registrar a retirada.'}), 401
    
    user_id = session['user_id']
    
    # Primeiro, verifica se o usuário já tem um guarda-chuva ativo
    if check_user_has_umbrella(user_id):
        return jsonify({'status': 'error', 'message': 'Você já tem um guarda-chuva retirado. Por favor, devolva-o antes de retirar outro.'}), 400

    data = request.get_json()
    codigo_guarda_chuva = data.get('codigo')

    if not codigo_guarda_chuva:
        return jsonify({'status': 'error', 'message': 'Código do guarda-chuva não fornecido.'}), 400

    nome_usuario = session.get('user_name')
    email = session.get('email')
    telefone = session.get('phone')

    if not all([nome_usuario, email, telefone]):
        return jsonify({'status': 'error', 'message': 'Dados do usuário (nome, email, telefone) não encontrados na sessão. Por favor, faça login novamente.'}), 400

    data_retirada = datetime.now().strftime('%Y-%m-%d')
    hora_retirada = datetime.now().strftime('%H:%M:%S')

    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'status': 'error', 'message': 'Erro de conexão com o banco de dados.'}), 500
        
        cursor = connection.cursor()
        
        insert_query = """
        INSERT INTO umbrella_retirada (user_id, nome_usuario, email, telefone, codigo_guarda_chuva, data_retirada, hora_retirada, ativo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        """
        values = (user_id, nome_usuario, email, telefone, codigo_guarda_chuva, data_retirada, hora_retirada)
        
        cursor.execute(insert_query, values)
        connection.commit()

        print(f"Retirada registrada: Usuário '{nome_usuario}', Código: '{codigo_guarda_chuva}'")
        return jsonify({'status': 'success', 'message': 'Retirada registrada com sucesso!', 'action': 'retirada'})

    except Error as e:
        print(f"Erro ao inserir retirada no MySQL: {e}")
        if connection:
            connection.rollback()
        return jsonify({'status': 'error', 'message': f'Erro no servidor ao registrar retirada: {str(e)}'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# --- ROTA PARA REGISTRAR DEVOLUÇÃO DE GUARDA-CHUVA ---
@app.route('/registrar_devolucao', methods=['POST'])
def registrar_devolucao():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Não autenticado. Faça login para registrar a devolução.'}), 401
    
    user_id = session['user_id']
    user_cpf = session.get('cpf') # Pega o CPF da sessão para registrar na devolução

    if not user_cpf:
        return jsonify({'status': 'error', 'message': 'CPF do usuário não encontrado na sessão.'}), 400

    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'status': 'error', 'message': 'Erro de conexão com o banco de dados.'}), 500
        
        cursor = connection.cursor(dictionary=True)

        # 1. Encontrar a última retirada ativa do usuário
        # Use user_id para filtrar e garantir que a retirada pertence ao usuário logado
        query_ultima_retirada = "SELECT id, codigo_guarda_chuva FROM umbrella_retirada WHERE user_id = %s AND ativo = TRUE ORDER BY timestamp_retirada DESC LIMIT 1"
        cursor.execute(query_ultima_retirada, (user_id,))
        ultima_retirada = cursor.fetchone()

        if not ultima_retirada:
            return jsonify({'status': 'error', 'message': 'Nenhum guarda-chuva ativo para este usuário. Não há o que devolver.'}), 400
        
        # CORREÇÃO: Troca 'ultima_retima' por 'ultima_retirada'
        retirada_id = ultima_retirada['id'] 
        codigo_guarda_chuva = ultima_retirada['codigo_guarda_chuva']

        # 2. Registrar a devolução
        data_devolucao = datetime.now().strftime('%Y-%m-%d')
        hora_devolucao = datetime.now().strftime('%H:%M:%S')

        insert_devolucao_query = """
        INSERT INTO umbrella_devolucao (retirada_id, data_devolucao, hora_devolucao, cpf_usuario)
        VALUES (%s, %s, %s, %s)
        """
        values_devolucao = (retirada_id, data_devolucao, hora_devolucao, user_cpf)
        cursor.execute(insert_devolucao_query, values_devolucao)

        # 3. Atualizar o status 'ativo' da retirada para FALSE
        update_retirada_query = "UPDATE umbrella_retirada SET ativo = FALSE WHERE id = %s"
        cursor.execute(update_retirada_query, (retirada_id,))
        
        connection.commit()

        print(f"Devolução registrada: Usuário ID '{user_id}', Retirada ID: '{retirada_id}', Código: '{codigo_guarda_chuva}'")
        return jsonify({'status': 'success', 'message': 'Guarda-chuva devolvido com sucesso!', 'action': 'devolucao', 'codigo_devolvido': codigo_guarda_chuva})

    except Error as e:
        print(f"Erro ao registrar devolução no MySQL: {e}")
        if connection:
            connection.rollback()
        return jsonify({'status': 'error', 'message': f'Erro no servidor ao registrar devolução: {str(e)}'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# Rota para verificar o status do guarda-chuva do cliente
@app.route('/check_umbrella_status', methods=['GET'])
def check_umbrella_status():
    if 'user_id' not in session:
        # Se não estiver autenticado, não pode ter guarda-chuva ativo.
        # Retorna 401 para o frontend lidar com redirecionamento para login
        return jsonify({'status': 'error', 'message': 'Não autenticado.'}), 401
    
    user_id = session['user_id']
    has_umbrella = check_user_has_umbrella(user_id)
    return jsonify({'status': 'success', 'has_umbrella': has_umbrella})


with app.app_context():
    init_database() # Garante que as tabelas são criadas ao iniciar a aplicação

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

