from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash # Adicionado redirect, url_for, session, flash
import os # Importado para usar variáveis de ambiente ou para gerar secret key

app = Flask(__name__)
# Configurando a SECRET_KEY. É CRUCIAL que esta chave seja COMPLEXA e SECRETA!
# Em produção, você deve usar uma variável de ambiente para isso.
# Exemplo para desenvolvimento (NÃO USE EM PRODUÇÃO):
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_super_chave_secreta_e_complexa_aqui_12345') # Use uma chave mais robusta

@app.route('/')
def index():
    # Para o propósito de demonstrar o logout e o user_name na sessão,
    # vamos definir um usuário de exemplo na sessão ao acessar a página inicial.
    # Em um app real, isso viria de um processo de login.
    if 'user_name' not in session:
        session['user_name'] = 'Convidado' # Ou qualquer valor padrão
        # Se você tiver um sistema de login, aqui você carregaria o nome do usuário logado.

    # Isso renderiza o seu arquivo HTML (index.html)
    # Passamos user_name para o template para que ele possa ser exibido no header.
    return render_template('index.html', user_name=session.get('user_name', 'Usuário'))

@app.route('/cadastro_tecnico', methods=['POST']) # O endpoint agora é para cadastro de técnico
def cadastro_tecnico():
    # Coletando os dados dos novos campos do formulário
    nome_tecnico = request.form.get('nomeTecnico')
    email_corporativo = request.form.get('emailCorporativo')
    senha = request.form.get('senha')

    # Verificação básica se todos os campos foram preenchidos
    if not nome_tecnico or not email_corporativo or not senha:
        flash("Por favor, preencha todos os campos!", "error") # Usa flash para erro
        return jsonify({"success": False, "message": "Por favor, preencha todos os campos!"}), 400

    # --- Sua lógica de cadastro em Python viria aqui ---
    # Por exemplo:
    # 1. Salvar esses dados em um banco de dados (Nome, E-mail, Senha Criptografada)
    # 2. Criptografar a senha antes de salvar por segurança (MUITO IMPORTANTE!)
    # 3. Realizar validações adicionais (ex: formato do e-mail, força da senha)

    print(f"Tentando cadastrar técnico: Nome={nome_tecnico}, E-mail={email_corporativo}, Senha={'*'*len(senha)}")
    # Atenção: Eu mascarei a senha no print por segurança. NUNCA imprima senhas em logs.
    # ---------------------------------------------------

    # Simulação de login após cadastro bem-sucedido
    session['user_id'] = 'algum_id_unico_do_usuario' # Em um app real, seria o ID do banco de dados
    session['user_name'] = nome_tecnico # Define o nome do usuário na sessão

    flash("Login realizado com sucesso!", "message") # Usa flash para sucesso
    return jsonify({"success": True, "message": "Login realizado com sucesso!"}), 200

# --- NOVA ROTA ADICIONADA: /logout ---
@app.route('/logout')
def logout():
    session.pop('user_id', None) # Remove o ID do usuário da sessão
    session.pop('user_name', None) # Remove o nome do usuário da sessão
    flash('Você foi desconectado.', 'message') # Mensagem de sucesso ao desconectar
    return redirect(url_for('index')) # Redireciona para a página inicial

# --- NOVA ROTA ADICIONADA: /registrar_retirada ---
@app.route('/registrar_retirada', methods=['POST'])
def registrar_retirada():
    data = request.get_json()
    codigo_retirada = data.get('codigo')

    if not codigo_retirada:
        return jsonify({"status": "error", "message": "Código de retirada não fornecido."}), 400

    # Aqui você adicionaria a lógica para registrar a retirada do guarda-chuva
    # Por exemplo:
    # - Validar o código (se existe, se está ativo, etc.)
    # - Registrar no banco de dados que o guarda-chuva foi retirado
    # - Associar a retirada a um usuário (se estiver logado)

    print(f"Código de retirada recebido: {codigo_retirada}")
    
    # Simulação de sucesso
    flash(f"Retirada do guarda-chuva com código {codigo_retirada} registrada com sucesso!", "message")
    return jsonify({"status": "success", "message": "Retirada registrada com sucesso!"}), 200


if __name__ == '__main__':
    # Roda o aplicativo Flask em modo de depuração (debug=True)
    # útil para desenvolvimento, pois ele reinicia o servidor automaticamente
    # quando você faz alterações no código.
    app.run(debug=True)
