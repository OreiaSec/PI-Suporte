from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
import mysql.connector # Importa a biblioteca do MySQL
from werkzeug.security import generate_password_hash, check_password_hash # Para hashing de palavras-passe

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_super_chave_secreta_e_complexa_aqui_12345')

# Configuração da Base de Dados
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
    """Cria e retorna uma nova conexão com a base de dados."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar à base de dados: {err}")
        # Em um ambiente de produção, você pode querer registar isso e não retornar a falha diretamente ao utilizador
        flash("Erro interno no servidor ao conectar à base de dados.", "error")
        return None

@app.route('/')
def index():
    # Se o utilizador já estiver autenticado (ou seja, 'user_name' na sessão),
    # redireciona diretamente para o dashboard, evitando que ele veja a tela de autenticação novamente.
    if 'user_name' in session:
        return redirect(url_for('dashboard_tecnico'))
    
    # Renderiza a tela de autenticação/registo se não estiver autenticado
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

    cursor = conn.cursor(buffered=True) # buffered=True é útil para evitar "Unread result found"
    
    try:
        # 1. Verificar se o e-mail já existe
        cursor.execute("SELECT id_tecnico FROM tecnicos WHERE email_corporativo = %s", (email_corporativo,))
        if cursor.fetchone():
            flash("Este e-mail já está registado. Por favor, use outro ou faça autenticação.", "error")
            return jsonify({"success": False, "message": "Este e-mail já está registado."}), 409 # Conflict

        # 2. Hash da palavra-passe antes de armazenar
        hashed_senha = generate_password_hash(senha)

        # 3. Inserir novo técnico
        insert_query = "INSERT INTO tecnicos (nome_tecnico, email_corporativo, senha_hash) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (nome_tecnico, email_corporativo, hashed_senha))
        conn.commit() # Garante que a transação seja efetivada

        # Lógica de autenticação após registo bem-sucedido
        session['user_id'] = cursor.lastrowid # Pega o ID gerado para o novo técnico
        session['user_name'] = nome_tecnico
        
        flash("Registo e Autenticação realizados com sucesso!", "message")
        return jsonify({"success": True, "redirect": url_for('dashboard_tecnico')})

    except mysql.connector.Error as err:
        flash(f"Erro ao processar o registo: {err}", "error")
        conn.rollback() # Desfaz a transação em caso de erro
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

# --- ROTA PARA O DASHBOARD DO TÉCNICO (CARREGA TODOS OS UTILIZADORES INICIALMENTE) ---
@app.route('/dashboard_tecnico')
def dashboard_tecnico():
    # Verifica se o utilizador está autenticado antes de exibir o dashboard
    if 'user_name' not in session:
        flash("Você precisa estar autenticado para aceder a esta página.", "error")
        return redirect(url_for('index'))
    
    user_name = session.get('user_name', 'Utilizador')

    # Carrega todos os utilizadores da tabela umbrella_retirada para exibição inicial
    conn = get_db_connection()
    users = []
    if conn:
        cursor = conn.cursor(dictionary=True) # Retorna resultados como dicionários
        try:
            # Seleciona as colunas conforme a imagem fornecida
            cursor.execute("SELECT id, nome_usuario, email, telefone, codigo_guarda_chuva, data_retirada, hora_retirada, timestamp_retirada, ativo FROM umbrella_retirada")
            users = cursor.fetchall()
            flash("Dados atualizados com sucesso!", "message")
        except mysql.connector.Error as err:
            flash(f"Erro ao carregar utilizadores da base de dados: {err}", "error")
            print(f"Erro SQL ao carregar utilizadores: {err}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('dashboard_tecnico.html', user_name=user_name, initial_users=users)

# --- NOVA ROTA API PARA PESQUISA DE UTILIZADORES (AJAX) ---
@app.route('/api/search_users', methods=['POST'])
def api_search_users():
    # Verifica se o utilizador está autenticado para aceder à API de busca
    if 'user_name' not in session:
        return jsonify({"success": False, "message": "Não autorizado."}), 401
    
    # Pega os dados da requisição POST
    data = request.get_json()
    nome = data.get('nomeUsuario', '').strip()
    cpf = data.get('cpfUsuario', '').strip() # CPF é mantido no frontend, mas não é usado na query SQL para umbrella_retirada
    email = data.get('emailUsuario', '').strip()

    conn = get_db_connection()
    if conn is None:
        return jsonify({"success": False, "message": "Não foi possível conectar à base de dados."}), 500

    cursor = conn.cursor(dictionary=True) # Retorna resultados como dicionários
    users = []
    try:
        # A query agora considera as colunas reais da tabela e remove o CPF da busca SQL
        query = "SELECT id, nome_usuario, email, telefone, codigo_guarda_chuva, data_retirada, hora_retirada, timestamp_retirada, ativo FROM umbrella_retirada WHERE 1=1"
        params = []

        if nome:
            query += " AND nome_usuario LIKE %s"
            params.append(f"%{nome}%")
        if email: # Usar a coluna 'email' da tabela
            query += " AND email LIKE %s"
            params.append(f"%{email}%")
        # O campo 'cpf' não existe na tabela 'umbrella_retirada', portanto, não será usado na filtragem SQL.

        cursor.execute(query, params)
        users = cursor.fetchall()
        
        return jsonify({"success": True, "users": users})

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
