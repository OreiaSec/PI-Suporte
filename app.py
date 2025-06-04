from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
import mysql.connector # Importa o conector MySQL
from werkzeug.security import generate_password_hash, check_password_hash # Para hashing de senhas

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_super_chave_secreta_e_complexa_aqui_12345') # Use uma chave mais robusta em produção!

# Configuração do Banco de Dados
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

# --- Funções de Conexão e Inicialização do Banco de Dados ---
def get_db_connection():
    """Estabelece uma conexão com o banco de dados."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

def init_db():
    """Cria as tabelas 'tecnicos' e 'historico_login' se elas não existirem."""
    print("DEBUG: init_db() sendo chamada...")
    conn = get_db_connection()
    if conn:
        print("DEBUG: Conexão com o banco de dados estabelecida em init_db().")
        cursor = conn.cursor()
        try:
            # Tabela para registrar técnicos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tecnicos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    senha_hash VARCHAR(255) NOT NULL
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """)
            conn.commit() # Confirma a transação DDL
            print("DEBUG: Comando CREATE TABLE IF NOT EXISTS tecnicos executado.")
            print("Tabela 'tecnicos' verificada/criada com sucesso.")

            # Tabela para histórico de logins (opcional, se você quiser registrar acessos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico_login (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tecnico_id INT NOT NULL,
                    data_hora_login DATETIME DEFAULT CURRENT_TIMESTAMP,
                    endereco_ip VARCHAR(45), -- Para IPv4 ou IPv6
                    status_login VARCHAR(10) DEFAULT 'SUCESSO', -- 'SUCESSO' ou 'FALHA'
                    FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE CASCADE
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """)
            conn.commit()
            print("DEBUG: Comando CREATE TABLE IF NOT EXISTS historico_login executado.")
            print("Tabela 'historico_login' verificada/criada com sucesso.")

        except mysql.connector.Error as err:
            print(f"ERRO CRÍTICO DB: Erro ao criar tabelas: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            print("DEBUG: Conexão do banco de dados fechada em init_db().")
    else:
        print("ERRO CRÍTICO DB: Não foi possível inicializar o banco de dados: conexão falhou.")

# --- Rotas do Aplicativo ---

@app.route('/')
def index():
    if 'user_name' in session:
        return redirect(url_for('dashboard_tecnico'))
    return render_template('index.html')

@app.route('/register_tecnico', methods=['POST']) # Rota para REGISTRO de técnico
def register_tecnico():
    nome_tecnico = request.form.get('nomeTecnico')
    email_corporativo = request.form.get('emailCorporativo')
    senha = request.form.get('senha')

    if not nome_tecnico or not email_corporativo or not senha:
        flash("Por favor, preencha todos os campos para cadastro!", "error")
        return jsonify({"success": False, "message": "Por favor, preencha todos os campos!"}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            hashed_password = generate_password_hash(senha) # Hash da senha para segurança

            cursor.execute("INSERT INTO tecnicos (nome, email, senha_hash) VALUES (%s, %s, %s)",
                           (nome_tecnico, email_corporativo, hashed_password))
            conn.commit() # Confirma a transação

            flash("Técnico cadastrado com sucesso! Agora você pode fazer login.", "message")
            return jsonify({"success": True, "message": "Técnico cadastrado com sucesso!"}), 200
        except mysql.connector.Error as err:
            if err.errno == 1062: # Erro de entrada duplicada (email UNIQUE)
                flash("E-mail já cadastrado. Tente fazer login ou use outro e-mail.", "error")
                return jsonify({"success": False, "message": "E-mail já cadastrado."}), 409 # Conflict
            else:
                flash(f"Erro ao cadastrar técnico: {err}", "error")
                return jsonify({"success": False, "message": f"Erro no servidor: {err}"}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        flash("Erro de conexão com o banco de dados.", "error")
        return jsonify({"success": False, "message": "Erro de conexão com o banco de dados."}), 500

@app.route('/login', methods=['POST']) # Rota para LOGIN
def login():
    email = request.form.get('emailCorporativo')
    senha = request.form.get('senha')

    if not email or not senha:
        flash("Por favor, preencha e-mail e senha para login.", "error")
        return jsonify({"success": False, "message": "Por favor, preencha e-mail e senha."}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True) # Retorna resultados como dicionários
        try:
            cursor.execute("SELECT id, nome, senha_hash FROM tecnicos WHERE email = %s", (email,))
            tecnico = cursor.fetchone()

            if tecnico and check_password_hash(tecnico['senha_hash'], senha):
                session['user_id'] = tecnico['id']
                session['user_name'] = tecnico['nome']
                flash(f"Bem-vindo, {tecnico['nome']}!", "message")

                # Opcional: Registrar login bem-sucedido no histórico
                try:
                    ip_address = request.remote_addr
                    cursor_log = conn.cursor()
                    cursor_log.execute(
                        "INSERT INTO historico_login (tecnico_id, endereco_ip, status_login) VALUES (%s, %s, %s)",
                        (tecnico['id'], ip_address, 'SUCESSO')
                    )
                    conn.commit()
                    cursor_log.close()
                except mysql.connector.Error as log_err:
                    print(f"Erro ao registrar histórico de login bem-sucedido: {log_err}")
                
                return jsonify({"success": True, "redirect": url_for('dashboard_tecnico')})
            else:
                # Opcional: Registrar login falho no histórico
                try:
                    ip_address = request.remote_addr
                    # Tenta obter o ID do técnico mesmo em caso de falha (se o email for válido, mas a senha não)
                    tecnico_id_for_log = tecnico['id'] if tecnico else None
                    cursor_log_fail = conn.cursor()
                    cursor_log_fail.execute(
                        "INSERT INTO historico_login (tecnico_id, endereco_ip, status_login) VALUES (%s, %s, %s)",
                        (tecnico_id_for_log, ip_address, 'FALHA')
                    )
                    conn.commit()
                    cursor_log_fail.close()
                except mysql.connector.Error as log_err:
                    print(f"Erro ao registrar histórico de login falho: {log_err}")

                flash("E-mail ou senha incorretos.", "error")
                return jsonify({"success": False, "message": "E-mail ou senha incorretos."}), 401 # Unauthorized
        except mysql.connector.Error as err:
            flash(f"Erro no servidor ao tentar login: {err}", "error")
            return jsonify({"success": False, "message": f"Erro no servidor: {err}"}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        flash("Erro de conexão com o banco de dados.", "error")
        return jsonify({"success": False, "message": "Erro de conexão com o banco de dados."}), 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Você foi desconectado.', 'message')
    return redirect(url_for('index')) # Redireciona para a página de login

# --- NOVA ROTA ADICIONADA: Dashboard do Técnico ---
@app.route('/dashboard_tecnico')
def dashboard_tecnico():
    # Verifica se o usuário está logado antes de exibir o dashboard
    if 'user_name' not in session:
        flash("Você precisa estar logado para acessar esta página.", "error")
        return redirect(url_for('index')) # Redireciona para o login se não estiver logado
    
    user_name = session.get('user_name', 'Usuário') # Pega o nome do usuário da sessão
    return render_template('dashboard_tecnico.html', user_name=user_name)

if __name__ == '__main__':
    # Inicializa o banco de dados e as tabelas 'tecnicos' e 'historico_login' antes de rodar o app
    init_db()
    app.run(debug=True) # Em produção, defina debug=False e use um servidor WSGI como Gunicorn
