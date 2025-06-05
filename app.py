from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
import mysql.connector # Importa a biblioteca do MySQL
from werkzeug.security import generate_password_hash, check_password_hash # Para hashing de senhas

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_super_chave_secreta_e_complexa_aqui_12345')

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

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        # Em um ambiente de produção, você pode querer logar isso e não retornar a falha diretamente ao usuário
        flash("Erro interno no servidor ao conectar ao banco de dados.", "error")
        return None

@app.route('/') [cite: 1]
def index(): [cite: 1]
    # Se o usuário já estiver logado (ou seja, 'user_name' na sessão),
    # redireciona diretamente para o dashboard, evitando que ele veja a tela de login novamente.
    if 'user_name' in session: [cite: 2]
        return redirect(url_for('dashboard_tecnico')) [cite: 2]
    
    # Renderiza a tela de login/cadastro se não estiver logado
    return render_template('index.html') [cite: 205]

@app.route('/cadastro_tecnico', methods=['POST']) [cite: 2]
def cadastro_tecnico(): [cite: 2]
    nome_tecnico = request.form.get('nomeTecnico')
    email_corporativo = request.form.get('emailCorporativo')
    senha = request.form.get('senha')

    if not nome_tecnico or not email_corporativo or not senha: [cite: 2]
        flash("Por favor, preencha todos os campos!", "error") [cite: 2]
        return jsonify({"success": False, "message": "Por favor, preencha todos os campos!"}), 400 [cite: 2]

    conn = get_db_connection()
    if conn is None:
        return jsonify({"success": False, "message": "Não foi possível conectar ao banco de dados."}), 500

    cursor = conn.cursor(buffered=True) # buffered=True é útil para evitar "Unread result found"
    
    try:
        # 1. Verificar se o e-mail já existe
        cursor.execute("SELECT id_tecnico FROM tecnicos WHERE email_corporativo = %s", (email_corporativo,))
        if cursor.fetchone():
            flash("Este e-mail já está cadastrado. Por favor, use outro ou faça login.", "error")
            return jsonify({"success": False, "message": "Este e-mail já está cadastrado."}), 409 # Conflict

        # 2. Hash da senha antes de armazenar
        hashed_senha = generate_password_hash(senha)

        # 3. Inserir novo técnico
        insert_query = "INSERT INTO tecnicos (nome_tecnico, email_corporativo, senha_hash) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (nome_tecnico, email_corporativo, hashed_senha))
        conn.commit() # Garante que a transação seja efetivada

        # Lógica de login após cadastro bem-sucedido
        session['user_id'] = cursor.lastrowid # Pega o ID gerado para o novo técnico
        session['user_name'] = nome_tecnico
        
        flash("Cadastro e Login realizados com sucesso!", "message")
        return jsonify({"success": True, "redirect": url_for('dashboard_tecnico')})

    except mysql.connector.Error as err:
        flash(f"Erro ao processar o cadastro: {err}", "error")
        conn.rollback() # Desfaz a transação em caso de erro
        return jsonify({"success": False, "message": f"Erro interno ao cadastrar o técnico: {err}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/logout') [cite: 4]
def logout(): [cite: 4]
    session.pop('user_id', None) [cite: 5]
    session.pop('user_name', None) [cite: 5]
    flash('Você foi desconectado.', 'message') [cite: 5]
    return redirect(url_for('index')) [cite: 5]

# --- NOVA ROTA ADICIONADA: Dashboard do Técnico ---
@app.route('/dashboard_tecnico') [cite: 4]
def dashboard_tecnico(): [cite: 4]
    # Verifica se o usuário está logado antes de exibir o dashboard
    if 'user_name' not in session: [cite: 4]
        flash("Você precisa estar logado para acessar esta página.", "error") [cite: 5]
        return redirect(url_for('index')) [cite: 5]
    
    user_name = session.get('user_name', 'Usuário') [cite: 5]
    return render_template('dashboard_tecnico.html', user_name=user_name) [cite: 5]

if __name__ == '__main__': [cite: 5]
    app.run(debug=True) [cite: 5]
