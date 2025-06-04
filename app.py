from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_super_chave_secreta_e_complexa_aqui_12345') 

@app.route('/')
def index():
    # Se o usuário já estiver logado (ou seja, 'user_name' na sessão),
    # redireciona diretamente para o dashboard, evitando que ele veja a tela de login novamente.
    if 'user_name' in session:
        return redirect(url_for('dashboard_tecnico'))
    
    # Renderiza a tela de login/cadastro se não estiver logado
    return render_template('index.html')

@app.route('/cadastro_tecnico', methods=['POST']) 
def cadastro_tecnico():
    nome_tecnico = request.form.get('nomeTecnico')
    email_corporativo = request.form.get('emailCorporativo')
    senha = request.form.get('senha')

    if not nome_tecnico or not email_corporativo or not senha:
        flash("Por favor, preencha todos os campos!", "error")
        return jsonify({"success": False, "message": "Por favor, preencha todos os campos!"}), 400

    # --- Sua lógica de cadastro/autenticação viria aqui ---
    # Por exemplo:
    # 1. Verificar credenciais no banco de dados
    # 2. Se as credenciais estiverem corretas:
    session['user_id'] = 'algum_id_unico_do_usuario' 
    session['user_name'] = nome_tecnico # Assume que o nome do técnico é o nome para exibir
    
    flash("Login realizado com sucesso!", "message")
    # Redireciona para uma URL para evitar problemas com recarga de formulário POST
    return jsonify({"success": True, "redirect": url_for('dashboard_tecnico')}) # Retorna a URL para redirecionar no JS
    # ---------------------------------------------------

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
    app.run(debug=True)
