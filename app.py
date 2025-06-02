from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro_usuario', methods=['POST']) # Novo endpoint para cadastro
def cadastro_usuario():
    nome_completo = request.form.get('nomeCompleto')
    cpf_cadastro = request.form.get('cpfCadastro')
    pais = request.form.get('pais')

    if not nome_completo or not cpf_cadastro or not pais:
        return jsonify({"success": False, "message": "Por favor, preencha todos os campos!"}), 400

    # --- Sua lógica de cadastro em Python iria aqui ---
    # Por exemplo: salvar no banco de dados, verificar CPF, etc.
    print(f"Tentando cadastrar: Nome={nome_completo}, CPF={cpf_cadastro}, País={pais}")
    # ---------------------------------------------------

    return jsonify({"success": True, "message": "Cadastro realizado com sucesso!"}), 200

if __name__ == '__main__':
    app.run(debug=True)
