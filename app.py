
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Bubble Support</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>

  <style>
    * {
      box-sizing: border-box;
    }

    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      margin: 0;
      padding: 0;
      background-image: url('https://static8.depositphotos.com/1020804/816/i/450/depositphotos_8166031-stock-photo-abstract-background-night-sky-after.jpg');
      background-size: cover;
      background-position: center;
      background-repeat: repeat;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
    }

    .loading-screen, .container {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(11, 12, 42, 0.9);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      transition: opacity 1s ease-in-out;
      z-index: 10;
    }

    .container {
      background-color: rgba(255, 255, 255, 0.2);
      backdrop-filter: blur(10px);
      box-shadow: 0px 0px 20px rgba(0, 0, 0, 0.3);
      width: 90%;
      max-width: 400px;
      border-radius: 20px;
      padding: 30px 20px;
      display: none;
    }

    /* CENTRALIZA O FORMULÁRIO DENTRO DO CONTAINER */
    form {
      width: 80%;
      margin: 0 auto;
    }

    .umbrella-img {
      width: auto;
      height: auto;
      max-width: 90%;
      max-height: 90%;
      transform: scale(0.85);
      margin-bottom: 20px;
      opacity: 0;
      animation: fadeIn 1.5s ease forwards,
                 float 3s ease-in-out infinite,
                 pulse 1s ease-in-out infinite;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: scale(0.5); }
      to { opacity: 1; transform: scale(0.85); }
    }

    @keyframes float {
      0%, 100% { transform: translateY(0) scale(0.85); }
      50% { transform: translateY(-10px) scale(0.85); }
    }

    @keyframes pulse {
      0%, 100% { transform: translateY(0) scale(0.85); }
      50% { transform: translateY(0) scale(0.95); }
    }

    h2 {
      color: white;
      margin-bottom: 15px;
      font-weight: 600;
    }

    .input-group {
      position: relative;
      width: 100%;
      margin: 12px 0;
    }

    .input-group i {
      position: absolute;
      top: 50%;
      left: 12px;
      transform: translateY(-50%);
      color: #888;
      font-size: 18px;
    }

    .input-group input {
      width: 100%;
      padding: 12px 12px 12px 40px;
      border: 1px solid #ccc;
      border-radius: 10px;
      font-size: 16px;
      transition: all 0.3s ease;
      background-color: rgba(255,255,255,0.8);
    }

    .input-group input:focus {
      border-color: #007BFF;
      background-color: #f4faff;
      outline: none;
      box-shadow: 0 0 5px rgba(0, 123, 255, 0.3);
    }

    button {
      margin-top: 20px;
      padding: 12px 25px;
      border: none;
      background-color: #007BFF;
      color: white;
      border-radius: 10px;
      cursor: pointer;
      font-size: 16px;
      transition: background-color 0.3s ease;
      width: 100%;
    }

    button:hover {
      background-color: #0056b3;
    }
  </style>

  <script>
    window.onload = function () {
      setTimeout(() => {
        document.querySelector(".loading-screen").style.opacity = 0;
        setTimeout(() => {
          document.querySelector(".loading-screen").style.display = "none";
          document.querySelector(".container").style.display = "flex";
        }, 1000);
      }, 3000);
    };

    function loginTecnico() {
      const email = document.getElementById("emailTecnico").value.trim();
      const cpf = document.getElementById("cpfTecnico").value.trim();
      const senha = document.getElementById("senhaTecnico").value.trim();

      if (!email || !cpf || !senha) {
        alert("Por favor, preencha todos os campos!");
        return;
      }

      // Aqui você pode adicionar validações extras ou chamadas para back-end

      alert("Login do técnico realizado com sucesso!");
    }
  </script>
</head>
<body>

  <!-- Tela de carregamento -->
  <div class="loading-screen">
    <img src="https://i.postimg.cc/26VcMNnf/Bubble-SA-PNG.png" alt="Logo Bubble SA" class="umbrella-img" />
    <p style="color:white; font-weight:600; margin-top: 10px;">Aguarde. Estamos preparando tudo.</p>
  </div>

  <!-- Container principal -->
  <div class="container">
    <h2>Bubble Support</h2>

    <form onsubmit="event.preventDefault(); loginTecnico();">
      <div class="input-group">
        <i class="fa fa-envelope"></i>
        <input type="email" id="emailTecnico" placeholder="E-mail" required />
      </div>

      <div class="input-group">
        <i class="fa fa-id-card"></i>
        <input type="text" id="cpfTecnico" placeholder="CPF" required />
      </div>

      <div class="input-group">
        <i class="fa fa-lock"></i>
        <input type="password" id="senhaTecnico" placeholder="Senha" required />
      </div>

      <button type="submit">Entrar</button>
    </form>
  </div>

</body>
</html>
