from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    # Isso renderiza o seu arquivo HTML (index.html)
    return render_template('index.html')

@app.route('/cadastro_tecnico', methods=['POST']) # O endpoint agora é para cadastro de técnico
def cadastro_tecnico():
    # Coletando os dados dos novos campos do formulário
    nome_tecnico = request.form.get('nomeTecnico')
    email_corporativo = request.form.get('emailCorporativo')
    senha = request.form.get('senha')

    # Verificação básica se todos os campos foram preenchidos
    if not nome_tecnico or not email_corporativo or not senha:
        return jsonify({"success": False, "message": "Por favor, preencha todos os campos!"}), 400

    # --- Sua lógica de cadastro em Python viria aqui ---
    # Por exemplo:
    # 1. Salvar esses dados em um banco de dados (Nome, E-mail, Senha Criptografada)
    # 2. Criptografar a senha antes de salvar por segurança (MUITO IMPORTANTE!)
    # 3. Realizar validações adicionais (ex: formato do e-mail, força da senha)

    print(f"Tentando cadastrar técnico: Nome={nome_tecnico}, E-mail={email_corporativo}, Senha={'*'*len(senha)}")
    # Atenção: Eu mascarei a senha no print por segurança. NUNCA imprima senhas em logs.
    # ---------------------------------------------------

    return jsonify({"success": True, "message": "Cadastro de técnico realizado com sucesso!"}), 200

if __name__ == '__main__':
    # Roda o aplicativo Flask em modo de depuração (debug=True)
    # útil para desenvolvimento, pois ele reinicia o servidor automaticamente
    # quando você faz alterações no código.
    app.run(debug=True)
