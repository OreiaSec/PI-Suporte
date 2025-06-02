# app.py
from flask import Flask, render_template, request, jsonify, url_for
import os

app = Flask(__name__)

# --- CONFIGURAÇÃO PARA AMBIENTE DE PRODUÇÃO (Render, por exemplo) ---
# O Render define a porta através da variável de ambiente 'PORT'
# Se 'PORT' não estiver definida (ex: rodando localmente), usa 5000 como padrão.
PORT = int(os.environ.get('PORT', 5000))

# Rota para a página de login (GET request)
@app.route('/')
def login_page():
    return render_template('login.html')

# Rota para processar o login (POST request)
@app.route('/login', methods=['POST'])
def handle_login():
    email = request.form.get('emailTecnico')
    cpf = request.form.get('cpfTecnico')
    senha = request.form.get('senhaTecnico')

    # --- LÓGICA DE VERIFICAÇÃO DE LOGIN NO BACKEND ---
    # ESTE É UM EXEMPLO SIMPLES E INSEGURO.
    # Em uma aplicação real, você faria:
    # 1. Consulta em banco de dados para buscar o usuário pelo email/CPF.
    # 2. Verificação da senha usando um algoritmo de hash seguro (ex: bcrypt).
    # 3. Geração de um token de sessão ou cookie para manter o usuário logado.

    if email == "tecnico@bubble.com" and cpf == "123.456.789-00" and senha == "senha123":
        # Credenciais válidas
        return jsonify({"success": True, "message": "Login realizado com sucesso! Bem-vindo(a)!"})
    else:
        # Credenciais inválidas
        return jsonify({"success": False, "message": "E-mail, CPF ou Senha inválidos. Tente novamente."})

# Garante que o Flask seja executado quando você rodar o arquivo diretamente
if __name__ == '__main__':
    # Quando rodando localmente, 'debug=True' é útil para recarregar o servidor
    # automaticamente em mudanças e ver erros detalhados.
    # Em produção (no Render, por exemplo), 'debug' deve ser 'False'.
    app.run(debug=True, port=PORT)

