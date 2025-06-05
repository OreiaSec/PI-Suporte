from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_super_chave_secreta_e_complexa_aqui_12345')

# Início da Configuração da Base de Dados
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

# Início da conexão com o banco de dados
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar à base de dados: {err}")
        flash("Erro interno no servidor ao conectar à base de dados.", "error")
        return None

# Início das Rotas da Aplicação
@app.route('/')
def index():
    if 'user_name' in session:
        return redirect(url_for('dashboard_tecnico'))
    return render_template('index.html')

@app.route('/cadastro_tecnico', methods=['POST'])
def cadastro_tecnico():
    nome_tecnico = request.form.get('nomeTecnico')
    email_corporativo = request.form.get('emailCorporativo')
    senha = request.form.get('senha')

    if not nome_tecnico or not email_corporativo or not senha:
        flash("Por favor, preencha todos os campos!", "error")
        return jsonify({"success": False, "message": "Por favor, preencha todos os campos!"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"success": False, "message": "Não foi possível conectar à base de dados."}), 500

    cursor = conn.cursor(buffered=True)
    
    try:
        cursor.execute("SELECT id_tecnico FROM tecnicos WHERE email_corporativo = %s", (email_corporativo,))
        if cursor.fetchone():
            flash("Este e-mail já está registado. Por favor, use outro ou faça autenticação.", "error")
            return jsonify({"success": False, "message": "Este e-mail já está registado."}), 409

        hashed_senha = generate_password_hash(senha)

        insert_query = "INSERT INTO tecnicos (nome_tecnico, email_corporativo, senha_hash) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (nome_tecnico, email_corporativo, hashed_senha))
        conn.commit()

        session['user_id'] = cursor.lastrowid
        session['user_name'] = nome_tecnico
        
        flash("Registo e Autenticação realizados com sucesso!", "message")
        return jsonify({"success": True, "redirect": url_for('dashboard_tecnico')})

    except mysql.connector.Error as err:
        flash(f"Erro ao processar o registo: {err}", "error")
        conn.rollback()
        return jsonify({"success": False, "message": f"Erro interno ao registar o técnico: {err}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Você foi desconectado.', 'message')
    return redirect(url_for('index'))

# Rota para o Dashboard do Técnico
@app.route('/dashboard_tecnico')
def dashboard_tecnico():
    if 'user_name' not in session:
        flash("Você precisa estar autenticado para aceder a esta página.", "error")
        return redirect(url_for('index'))
    
    user_name = session.get('user_name', 'Utilizador')

    conn = get_db_connection()
    users = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, nome_usuario, email, telefone, codigo_guarda_chuva, data_retirada, hora_retirada, timestamp_retirada, ativo FROM umbrella_retirada")
            raw_users = cursor.fetchall()
            
            for user in raw_users:
                user_copy = dict(user) 
                if isinstance(user_copy.get('data_retirada'), date):
                    user_copy['data_retirada'] = user_copy['data_retirada'].isoformat()
                if isinstance(user_copy.get('hora_retirada'), timedelta):
                    total_seconds = int(user_copy['hora_retirada'].total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    user_copy['hora_retirada'] = f"{hours:02}:{minutes:02}:{seconds:02}"
                if isinstance(user_copy.get('timestamp_retirada'), datetime):
                    user_copy['timestamp_retirada'] = user_copy['timestamp_retirada'].isoformat()
                users.append(user_copy)
            
            flash("Dados de utilizadores carregados com sucesso!", "message")
        except mysql.connector.Error as err:
            flash(f"Erro ao carregar utilizadores da base de dados: {err}", "error")
            print(f"Erro SQL ao carregar utilizadores: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('dashboard_tecnico.html', user_name=user_name, initial_users=users)

# Rota API para pesquisa de utilizadores (AJAX)
@app.route('/api/search_users', methods=['POST'])
def api_search_users():
    if 'user_name' not in session:
        return jsonify({"success": False, "message": "Não autorizado."}), 401
    
    data = request.get_json()
    nome = data.get('nomeUsuario', '').strip()
    email = data.get('emailUsuario', '').strip()

    conn = get_db_connection()
    if conn is None:
        return jsonify({"success": False, "message": "Não foi possível conectar à base de dados."}), 500

    cursor = conn.cursor(dictionary=True)
    formatted_users = []
    try:
        query = "SELECT id, nome_usuario, email, telefone, codigo_guarda_chuva, data_retirada, hora_retirada, timestamp_retirada, ativo FROM umbrella_retirada WHERE 1=1"
        params = []

        if nome:
            query += " AND LOWER(nome_usuario) LIKE LOWER(%s)"
            params.append(f"%{nome}%")
        if email:
            query += " AND LOWER(email) LIKE LOWER(%s)"
            params.append(f"%{email}%")

        cursor.execute(query, params)
        raw_users = cursor.fetchall()

        for user in raw_users:
            user_copy = dict(user) 
            if isinstance(user_copy.get('data_retirada'), date):
                user_copy['data_retirada'] = user_copy['data_retirada'].isoformat()
            if isinstance(user_copy.get('hora_retirada'), timedelta):
                total_seconds = int(user_copy['hora_retirada'].total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                user_copy['hora_retirada'] = f"{hours:02}:{minutes:02}:{seconds:02}"
            if isinstance(user_copy.get('timestamp_retirada'), datetime):
                user_copy['timestamp_retirada'] = user_copy['timestamp_retirada'].isoformat()
            formatted_users.append(user_copy)
            
        return jsonify({"success": True, "users": formatted_users})

    except mysql.connector.Error as err:
        print(f"Erro SQL na pesquisa de utilizadores: {err}")
        return jsonify({"success": False, "message": f"Erro interno ao pesquisar utilizadores: {err}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    app.run(debug=True)
