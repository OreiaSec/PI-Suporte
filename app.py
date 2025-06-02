# app.py
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, session, render_template, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'e9f8d7c6b5a41234567890abcdefghijklmnopqrstuvwxyz') # Chave de exemplo, altere em produção!

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
    max_retries = 5
    retry_delay = 3
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
            if retry_count < max_retries:
                import time
                time.sleep(retry_delay)
            else:
                print("Máximo de tentativas de conexão excedido. Não foi possível conectar ao banco de dados.")
                return None
    return None

def init_database():
    """Cria a tabela de usuários se ela não existir e a tabela umbrella_retirada"""
    connection = None
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

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

            create_umbrella_table_query = """
            CREATE TABLE IF NOT EXISTS umbrella_retirada (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome_usuario VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                telefone VARCHAR(50) NOT NULL,
                codigo_guarda_chuva VARCHAR(6) NOT NULL,
                data_retirada DATE NOT NULL,
                hora_retirada TIME NOT NULL,
                timestamp_retirada DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_umbrella_table_query)
            print("Tabela 'umbrella_retirada' criada ou já existe.")

            connection.commit()

    except Error as e:
        print(f"Erro ao criar tabelas: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def validar_cpf(cpf):
    """Valida se o CPF tem 11 dígitos"""
    return re.match(r'^\d{11}$', cpf) is not None

def validar_email(email):
    """Valida formato do email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def inserir_usuario(nome, cpf, pais, email, telefone, senha):
    """Insere um novo usuário no banco de dados"""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return False, "Erro de conexão com o banco de dados!"

        cursor = connection.cursor()

        check_query = "SELECT id FROM users_from_bb WHERE cpf = %s OR email = %s"
        cursor.execute(check_query, (cpf, email))
        existing_user = cursor.fetchone()

        if existing_user:
            return False, "CPF ou email já cadastrados!"

        senha_hash = generate_password_hash(senha)

        insert_query = """
        INSERT INTO users_from_bb (nome, cpf, pais, email, telefone, senha)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(insert_query, (nome, cpf, pais, email, telefone, senha_hash))
        # connection.commit() # autocommit=True já cuida disso

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
            return False, "Erro de conexão com o banco de dados!", None, None, None

        cursor = connection.cursor(dictionary=True)

        query = "SELECT id, nome, email, telefone, senha FROM users_from_bb WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['senha'], senha):
            print(f"Login realizado: {user['nome']} - {user['email']}")
            return True, user['nome'], user['email'], user['telefone'], user['id']
        else:
            return False, "Email ou senha incorretos!", None, None, None

    except Error as e:
        print(f"Erro ao verificar login: {e}")
        return False, f"Erro no banco de dados: {str(e)}", None, None, None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


# --- HTML principal com CSS e JS embutidos ---
html_code = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Bubble SA - Cadastro e Login</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>

    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-image: url('https://static8.depositphotos.com/1020804/816/i/450/depositphotos_8166031-stock-photo-abstract-background-night-sky-after.jpg');
            background-size: cover;
            background-position: center;
            background-repeat: repeat;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .loading-screen, .container, .tela1, .tela2 {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(11, 12, 42, 0.9);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            transition: opacity 1s ease-in-out;
            z-index: 10;
        }
        .container, .tela1, .tela2 {
            background-color: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            box-shadow: 0px 0px 20px rgba(0, 0, 0, 0.3);
            width: 90%;
            max-width: 450px;
            border-radius: 20px;
            padding: 30px 20px;
            display: none; /* Controlado pelo JS */
        }
        .umbrella-img {
            width: auto;
            height: auto;
            max-width: 90%;
            max-height: 90%;
            transform: scale(0.85);
            margin-bottom: 10px;
            opacity: 0; /* Inicia oculto para a animação */
            animation: fadeIn 1.5s ease forwards,
                         float 3s ease-in-out infinite,
                         pulse 1s ease-in-out infinite;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.5); }
            to { opacity: 1; transform: scale(0.85); }
        }
        @keyframes float {
            0%, 100% { transform: translateY(0) scale(0.85); }
            50% { transform: translateY(-10px) scale(0.85); }
        }
        @keyframes pulse {
            0%, 100% { transform: translateY(0) scale(0.85); }
            50% { transform: translateY(0) scale(0.95); }
        }
        h2, p, label { color: white; }
        .input-group {
            position: relative;
            width: 100%;
            margin: 10px 0;
        }
        .input-group i {
            position: absolute;
            top: 50%;
            left: 12px;
            transform: translateY(-50%);
            color: #888;
            z-index: 2;
        }
        .input-group input, .input-group select {
            width: 100%;
            padding: 12px 12px 12px 36px;
            border: 1px solid #ccc;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .input-group input:focus, .input-group select:focus {
            border-color: #007BFF;
            background-color: #f4faff;
            outline: none;
            box-shadow: 0 0 5px rgba(0, 123, 255, 0.3);
        }
        .input-group input:invalid, .input-group select:invalid {
            border-color: #dc3545;
        }

        .tooltip {
            position: absolute;
            top: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background-color: #333;
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            white-space: nowrap;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s, visibility 0.3s;
            z-index: 1000;
            pointer-events: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }

        .tooltip::before {
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: transparent transparent #333 transparent;
        }

        .input-group input:focus:invalid + .tooltip,
        .input-group select:focus:invalid + .tooltip,
        .input-group input:focus:placeholder-shown + .tooltip {
            opacity: 1;
            visibility: visible;
        }

        .password-error {
            position: absolute;
            top: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background-color: #dc3545;
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s, visibility 0.3s;
            z-index: 1000;
            text-align: center;
            white-space: nowrap;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }

        .password-error::before {
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: transparent transparent #dc3545 transparent;
        }

        .password-error.show {
            opacity: 1;
            visibility: visible;
        }

        button {
            margin-top: 15px;
            padding: 12px 25px;
            border: none;
            background-color: #007BFF;
            color: white;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s ease;
            width: 100%;
            margin-bottom: 10px;
        }
        button:hover { background-color: #0056b3; }
        .flash-message {
            color: #28a745;
            font-weight: bold;
            margin-bottom: 10px;
            padding: 10px;
            background-color: rgba(40, 167, 69, 0.1);
            border-radius: 5px;
            border: 1px solid #28a745;
            text-align: center;
        }
        .flash-error {
            color: #dc3545;
            font-weight: bold;
            margin-bottom: 10px;
            padding: 10px;
            background-color: rgba(220, 53, 69, 0.1);
            border-radius: 5px;
            border: 1px solid #dc3545;
            text-align: center;
        }
    </style>

    <script>
        window.onload = function () {
            const flashMessages = document.querySelectorAll('.flash-message, .flash-error');
            let initialDelay = 2000;

            if (flashMessages.length > 0) {
                document.querySelector(".loading-screen").style.display = "none";
                document.querySelector(".container").style.display = "flex";
                flashMessages.forEach(msg => {
                    msg.style.display = 'block';
                    setTimeout(() => {
                        msg.style.opacity = '0';
                        msg.style.transition = 'opacity 1s ease-out';
                        setTimeout(() => msg.style.display = 'none', 1000);
                    }, 5000);
                });
            } else {
                setTimeout(() => {
                    document.querySelector(".loading-screen").style.opacity = 0;
                    setTimeout(() => {
                        document.querySelector(".loading-screen").style.display = "none";
                        document.querySelector(".container").style.display = "flex";
                    }, 1000);
                }, initialDelay);
            }
        };


        function irParaTela1() {
            let nome = document.getElementById("nome").value;
            let cpf = document.getElementById("cpf").value;
            let pais = document.getElementById("pais").value;

            if (nome === "" || cpf === "" || pais === "") {
                showEmptyFieldTooltips(['nome', 'cpf', 'pais']);
                return;
            }

            document.getElementById("hiddenNome").value = nome;
            document.getElementById("hiddenCpf").value = cpf;
            document.getElementById("hiddenPais").value = pais;

            document.querySelector(".container").style.display = "none";
            document.querySelector(".tela1").style.display = "flex";
        }

        function irParaTela2() {
            let email = document.getElementById("email").value;
            let telefone = document.getElementById("telefone").value;
            let senha = document.getElementById("senha").value;
            let confirmar = document.getElementById("confirmarSenha").value;

            if (email === "" || telefone === "" || senha === "" || confirmar === "") {
                showEmptyFieldTooltips(['email', 'telefone', 'senha', 'confirmarSenha']);
                return;
            }
            if (senha !== confirmar) {
                showPasswordError();
                return;
            }
            document.getElementById("formCadastro").submit();
        }

        function showEmptyFieldTooltips(fieldIds) {
            fieldIds.forEach(fieldId => {
                const field = document.getElementById(fieldId);
                const tooltip = field.parentNode.querySelector('.tooltip');
                if (field.value === "" && tooltip) {
                    tooltip.style.opacity = '1';
                    tooltip.style.visibility = 'visible';
                    setTimeout(() => {
                        tooltip.style.opacity = '0';
                        tooltip.style.visibility = 'hidden';
                    }, 3000);
                }
            });
        }

        function showPasswordError() {
            const errorDiv = document.querySelector('.password-error');
            errorDiv.classList.add('show');
            setTimeout(() => {
                errorDiv.classList.remove('show');
            }, 3000);
        }

        function irParaLogin() {
            document.querySelector(".container").style.display = "none";
            document.querySelector(".tela2").style.display = "flex";
        }

        function voltarParaCadastro() {
            document.querySelector(".tela2").style.display = "none";
            document.querySelector(".container").style.display = "flex";
        }

        document.addEventListener('DOMContentLoaded', function() {
            const inputs = document.querySelectorAll('input, select');
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    const tooltip = this.parentNode.querySelector('.tooltip');
                    if (tooltip && this.value !== '') {
                        tooltip.style.opacity = '0';
                        tooltip.style.visibility = 'hidden';
                    }
                });
            });
        });
    </script>
</head>
<body>

<div class="loading-screen">
    <img src="{{ url_for('static', filename='img/Bubble-SA-PNG.png') }}" alt="Logo Bubble SA" class="umbrella-img">
    <p style="color:white; font-weight:600; margin-top: 10px;">Conectando ao Render...</p>
</div>

<div class="container">
    <h2>Bem-vindo ao Bubble SA!</h2>
    <p>Preencha seus dados para cadastro:</p>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <form id="formCadastroParte1">
        <div class="input-group">
            <i class="fa fa-user"></i>
            <input type="text" name="nome" id="nome" placeholder="Nome completo" required>
            <div class="tooltip">Por favor, preencha seu nome completo</div>
        </div>

        <div class="input-group">
            <i class="fa fa-id-card"></i>
            <input type="text" name="cpf" id="cpf" placeholder="CPF (apenas números)" required pattern="[0-9]{11}" maxlength="11">
            <div class="tooltip">Digite um CPF válido (11 dígitos)</div>
        </div>

        <div class="input-group">
            <i class="fa fa-globe"></i>
            <select name="pais" id="pais" required>
                <option value="">Selecione seu país</option>
                <option value="Brasil">Brasil</option>
                <option value="Portugal">Portugal</option>
                <option value="Estados Unidos">Estados Unidos</option>
                <option value="Argentina">Argentina</option>
                <option value="Outro">Outro</option>
            </select>
            <div class="tooltip">Selecione seu país</div>
        </div>

        <button type="button" onclick="irParaTela1()">Próximo</button>
    </form>
    <button type="button" onclick="irParaLogin()">Já possui cadastro? Login</button>
</div>

<div class="tela1">
    <h2>Finalize seu cadastro</h2>

    <form id="formCadastro" method="POST" action="/cadastrar">
        <input type="hidden" name="nome" id="hiddenNome">
        <input type="hidden" name="cpf" id="hiddenCpf">
        <input type="hidden" name="pais" id="hiddenPais">

        <div class="input-group">
            <i class="fa fa-envelope"></i>
            <input type="email" name="email" id="email" placeholder="E-mail" required>
            <div class="tooltip">Digite um e-mail válido</div>
        </div>

        <div class="input-group">
            <i class="fa fa-phone"></i>
            <input type="text" name="telefone" id="telefone" placeholder="Telefone com DDD" required>
            <div class="tooltip">Digite seu telefone</div>
        </div>

        <div class="input-group">
            <i class="fa fa-lock"></i>
            <input type="password" name="senha" id="senha" placeholder="Criar senha (min. 6 caracteres)" required minlength="6">
            <div class="tooltip">A senha deve ter pelo menos 6 caracteres</div>
        </div>

        <div class="input-group">
            <i class="fa fa-lock"></i>
            <input type="password" id="confirmarSenha" placeholder="Confirmar senha" required>
            <div class="tooltip">Confirme sua senha</div>
            <div class="password-error">As senhas não correspondem!</div>
        </div>

        <button type="button" onclick="irParaTela2()">Finalizar Cadastro</button>
    </form>
</div>

<div class="tela2">
    <h2>Login</h2>

    <form method="POST" action="/login">
        <div class="input-group">
            <i class="fa fa-envelope"></i>
            <input type="email" name="email_login" placeholder="E-mail" required>
            <div class="tooltip">Digite seu e-mail</div>
        </div>

        <div class="input-group">
            <i class="fa fa-lock"></i>
            <input type="password" name="senha_login" placeholder="Senha" required>
            <div class="tooltip">Digite sua senha</div>
        </div>

        <button type="submit">Entrar</button>
        <button type="button" onclick="voltarParaCadastro()">Voltar para Cadastro</button>
    </form>
</div>

</body>
</html>
"""

@app.route('/')
def index():
    if 'user_name' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(html_code)

@app.route('/health')
def health_check():
    """Health check endpoint para o Render"""
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            return jsonify({"status": "healthy", "database": "connected"}), 200
        else:
            return jsonify({"status": "unhealthy", "database": "disconnected", "reason": "Failed to connect to DB"}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    nome = request.form.get('nome', '').strip()
    cpf = request.form.get('cpf', '').strip()
    pais = request.form.get('pais', '').strip()
    email = request.form.get('email', '').strip().lower()
    telefone = request.form.get('telefone', '').strip()
    senha = request.form.get('senha', '')

    if not all([nome, cpf, pais, email, telefone, senha]):
        flash('Todos os campos são obrigatórios para o cadastro!', 'error')
        return redirect(url_for('index'))

    if not validar_cpf(cpf):
        flash('CPF deve conter exatamente 11 dígitos!', 'error')
        return redirect(url_for('index'))

    if not validar_email(email):
        flash('Por favor, digite um email válido!', 'error')
        return redirect(url_for('index'))

    if len(senha) < 6:
        flash('A senha deve ter pelo menos 6 caracteres!', 'error')
        return redirect(url_for('index'))

    sucesso, mensagem = inserir_usuario(nome, cpf, pais, email, telefone, senha)

    if sucesso:
        flash(mensagem + " Agora você pode fazer login.", 'message')
    else:
        flash(mensagem, 'error')

    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email_login', '').strip().lower()
    senha = request.form.get('senha_login', '')

    if not email or not senha:
        flash('Email e senha são obrigatórios para o login!', 'error')
        return redirect(url_for('index'))

    sucesso, user_name, user_email, user_phone, user_id = verificar_login(email, senha)

    if sucesso:
        session['user_id'] = user_id
        session['user_name'] = user_name
        session['email'] = user_email
        session['phone'] = user_phone
        flash(f'Bem-vindo de volta, {user_name}!', 'message')
        return redirect(url_for('dashboard'))
    else:
        flash(user_name, 'error')

    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_name' in session:
        return render_template('user_dashboard.html', user_name=session['user_name'])
    else:
        flash('Você precisa fazer login para acessar esta página.', 'error')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('email', None)
    session.pop('phone', None)
    flash('Você foi desconectado.', 'message')
    return redirect(url_for('index'))

@app.route('/registrar_retirada', methods=['POST'])
def registrar_retirada():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Não autenticado. Faça login para registrar a retirada.'}), 401
        
    data = request.get_json()
    codigo_guarda_chuva = data.get('codigo', '').strip()

    if not codigo_guarda_chuva or len(codigo_guarda_chuva) != 6:
        return jsonify({'status': 'error', 'message': 'Código do guarda-chuva inválido. Deve ter 6 caracteres.'}), 400

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
        INSERT INTO umbrella_retirada (nome_usuario, email, telefone, codigo_guarda_chuva, data_retirada, hora_retirada)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (nome_usuario, email, telefone, codigo_guarda_chuva, data_retirada, hora_retirada)
        
        cursor.execute(insert_query, values)

        print(f"Retirada registrada: Usuário '{nome_usuario}', Código: '{codigo_guarda_chuva}'")
        return jsonify({'status': 'success', 'message': 'Retirada registrada com sucesso!'})

    except Error as e:
        print(f"Erro ao inserir retirada no MySQL: {e}")
        if connection and not connection.autocommit:
             connection.rollback()
        return jsonify({'status': 'error', 'message': f'Erro no servidor ao registrar retirada: {str(e)}'}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

with app.app_context():
    init_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
