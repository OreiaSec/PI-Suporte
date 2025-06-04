from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash # Para hashing de senhas

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_super_chave_secreta_e_complexa_aqui_12345') # Use uma chave mais robusta em produção!

# Configuração do Banco de Dados
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'), # Adicione um valor padrão para desenvolvimento local
    'port': int(os.environ.get('DB_PORT', 3306)),
    'database': os.environ.get('DB_NAME', 'bubble_support_db'), # Adicione um valor padrão
    'user': os.environ.get('DB_USER', 'root'), # Adicione um valor padrão
    'password': os.environ.get('DB_PASSWORD', 'password'), # Adicione um valor padrão
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
    """Cria a tabela 'tecnicos' se ela não existir."""
    conn = get_db_connection()
    if conn:
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
            print("Tabela 'tecnicos' verificada/criada com sucesso.")

        except mysql.connector.Error as err:
            print(f"Erro ao criar tabela 'tecnicos': {err}")
        finally:
            cursor.close()
            conn.close()
    else:
        print("Não foi possível inicializar o banco de dados: conexão falhou.")

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
            # Hash da senha para segurança
            hashed_password = generate_password_hash(senha)

            # Insere o novo técnico no banco de dados
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
            cursor.close()
            conn.close()
    else:
        flash("Erro de conexão com o banco de dados.", "error")
        return jsonify({"success": False, "message": "Erro de conexão com o banco de dados."}), 500

@app.route('/login', methods=['POST']) # NOVA ROTA para LOGIN
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
                return jsonify({"success": True, "redirect": url_for('dashboard_tecnico')})
            else:
                flash("E-mail ou senha incorretos.", "error")
                return jsonify({"success": False, "message": "E-mail ou senha incorretos."}), 401 # Unauthorized
        except mysql.connector.Error as err:
            flash(f"Erro no servidor ao tentar login: {err}", "error")
            return jsonify({"success": False, "message": f"Erro no servidor: {err}"}), 500
        finally:
            cursor.close()
            conn.close()
    else:
        flash("Erro de conexão com o banco de dados.", "error")
        return jsonify({"success": False, "message": "Erro de conexão com o banco de dados."}), 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Você foi desconectado.', 'message')
    return redirect(url_for('index'))

@app.route('/dashboard_tecnico')
def dashboard_tecnico():
    if 'user_name' not in session:
        flash("Você precisa estar logado para acessar esta página.", "error")
        return redirect(url_for('index'))
    user_name = session.get('user_name', 'Usuário')
    return render_template('dashboard_tecnico.html', user_name=user_name)

# A rota '/search_users' e a lógica de banco de dados para usuários foram removidas
# Conforme sua instrução, a pesquisa de usuários no frontend continua sendo uma simulação (mock)

if __name__ == '__main__':
    # Inicializa o banco de dados e a tabela 'tecnicos' antes de rodar o app
    init_db()
    app.run(debug=True)
