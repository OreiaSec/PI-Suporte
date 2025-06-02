from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    # Isso renderizará seu arquivo HTML da pasta 'templates'
    return render_template('index.html')

@app.route('/login_tecnico', methods=['POST'])
def login_tecnico():
    email = request.form.get('emailTecnico')
    cpf = request.form.get('cpfTecnico')
    senha = request.form.get('senhaTecnico')

    # Validação básica no lado do servidor
    if not email or not cpf or not senha:
        return jsonify({"success": False, "message": "Por favor, preencha todos os campos!"}), 400

    # --- Sua lógica de login em Python entraria aqui ---
    # Para demonstração, apenas imprimiremos e retornaremos uma mensagem de sucesso
    print(f"Tentando login para: Email={email}, CPF={cpf}, Senha={'*' * len(senha)}")
    # Em uma aplicação real, você verificaria isso em um banco de dados
    # Por exemplo:
    # if email == "test@example.com" and cpf == "123.456.789-00" and senha == "password123":
    #     return jsonify({"success": True, "message": "Login do técnico realizado com sucesso!"}), 200
    # else:
    #     return jsonify({"success": False, "message": "Credenciais inválidas."}), 401
    # -----------------------------------------------

    return jsonify({"success": True, "message": "Login do técnico realizado com sucesso!"}), 200

if __name__ == '__main__':
    app.run(debug=True) # debug=True permite recarregamento automático e mensagens de erro úteis
