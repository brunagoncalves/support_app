from typing import Dict
from typing import List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# Modelo para representar um usuário


class User(BaseModel):
    id: int
    name: str
    email: str

# Modelo para criar um novo usuário. (ID será gerado automaticamente).


class UserCreate(BaseModel):
    name: str
    email: str


# Banco de dados simulado
fake_users_db: Dict[int, User] = {}
next_user_id = 1

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat App com Usuários</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .user-section { background: #f0f0f0; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
            .chat-section { background: #fff; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            input, button { padding: 8px; margin: 5px; }
            #messages { list-style-type: none; padding: 0; max-height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
            #messages li { padding: 5px; border-bottom: 1px solid #eee; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Chat App com Sistema de Usuários</h1>
            
            <!-- Seção para criar/selecionar usuário -->
            <div class="user-section">
                <h2>Gerenciar Usuário</h2>
                
                <!-- Criar novo usuário -->
                <div>
                    <h3>Criar Novo Usuário</h3>
                    <input type="text" id="userName" placeholder="Nome do usuário" />
                    <input type="email" id="userEmail" placeholder="Email do usuário" />
                    <button onclick="createUser()">Criar Usuário</button>
                </div>
                
                <!-- Listar usuários existentes -->
                <div>
                    <h3>Usuários Existentes</h3>
                    <button onclick="loadUsers()">Carregar Usuários</button>
                    <select id="userSelect">
                        <option value="">Selecione um usuário</option>
                    </select>
                    <button onclick="selectUser()">Usar Este Usuário</button>
                </div>
                
                <div id="currentUser" style="margin-top: 10px; font-weight: bold;"></div>
            </div>
            
            <!-- Seção de Chat -->
            <div class="chat-section">
                <h2>Chat</h2>
                <div id="chatStatus">Selecione um usuário para começar a conversar</div>
                
                <form id="messageForm" onsubmit="sendMessage(event)" style="display: none;">
                    <input type="text" id="messageText" placeholder="Digite sua mensagem..." autocomplete="off"/>
                    <button type="submit">Enviar</button>
                </form>
                
                <ul id='messages'></ul>
            </div>
        </div>

        <script>
            let ws = null;
            let currentUserId = null;
            let currentUserName = null;

            async function createUser() {
                const name = document.getElementById('userName').value;
                const email = document.getElementById('userEmail').value;
                
                if (!name || !email) {
                    alert('Por favor, preencha nome e email');
                    return;
                }
                
                try {
                    const response = await fetch('/users', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ name: name, email: email })
                    });
                    
                    if (response.ok) {
                        const user = await response.json();
                        alert(`Usuário criado com sucesso! ID: ${user.id}`);
                        document.getElementById('userName').value = '';
                        document.getElementById('userEmail').value = '';
                        loadUsers(); // Recarrega a lista de usuários
                    } else {
                        const error = await response.json();
                        alert('Erro ao criar usuário: ' + error.detail);
                    }
                } catch (error) {
                    alert('Erro ao criar usuário: ' + error.message);
                }
            }
            
            async function loadUsers() {
                try {
                    const response = await fetch('/users');
                    const users = await response.json();
                    
                    const select = document.getElementById('userSelect');
                    select.innerHTML = '<option value="">Selecione um usuário</option>';
                    
                    users.forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.id;
                        option.textContent = `${user.name} (${user.email})`;
                        select.appendChild(option);
                    });
                } catch (error) {
                    alert('Erro ao carregar usuários: ' + error.message);
                }
            }
            
            function selectUser() {
                const select = document.getElementById('userSelect');
                const userId = select.value;
                
                if (!userId) {
                    alert('Por favor, selecione um usuário');
                    return;
                }
                
                currentUserId = userId;
                currentUserName = select.options[select.selectedIndex].textContent.split(' (')[0];
                
                document.getElementById('currentUser').textContent = `Usuário atual: ${currentUserName} (ID: ${userId})`;
                document.getElementById('chatStatus').textContent = 'Conectando ao chat...';
                document.getElementById('messageForm').style.display = 'block';
                
                connectToChat();
            }
            
            function connectToChat() {
                if (ws) {
                    ws.close();
                }
                
                ws = new WebSocket(`ws://localhost:8000/ws/${currentUserId}`);
                
                ws.onopen = function() {
                    document.getElementById('chatStatus').textContent = 'Conectado ao chat!';
                };
                
                ws.onmessage = function(event) {
                    const messages = document.getElementById('messages');
                    const message = document.createElement('li');
                    const content = document.createTextNode(event.data);
                    message.appendChild(content);
                    messages.appendChild(message);
                    messages.scrollTop = messages.scrollHeight;
                };
                
                ws.onclose = function() {
                    document.getElementById('chatStatus').textContent = 'Desconectado do chat';
                };
                
                ws.onerror = function(error) {
                    document.getElementById('chatStatus').textContent = 'Erro na conexão';
                    console.error('WebSocket error:', error);
                };
            }
            
            function sendMessage(event) {
                event.preventDefault();
                
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    alert('Não conectado ao chat');
                    return;
                }
                
                const input = document.getElementById("messageText");
                const message = input.value.trim();
                
                if (message) {
                    ws.send(message);
                    input.value = '';
                }
            }
            
            window.onload = function() {
                loadUsers();
            };
        </script>
    </body>
</html>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    from typing import Optional

    async def broadcast(self, message: str, exclude_user_id: Optional[int] = None):
        for user_id, connection in self.active_connections.items():
            if exclude_user_id is None or user_id != exclude_user_id:
                try:
                    await connection.send_text(message)
                except:
                    pass


manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.post("/users", response_model=User)
async def create_user(user: UserCreate):
    global next_user_id

    # Verifica se já existe usuário com o mesmo nome ou email
    for existing_user in fake_users_db.values():
        if existing_user.name == user.name:
            raise HTTPException(status_code=400, detail="Nome de usuário já está em uso")
        if existing_user.email == user.email:
            raise HTTPException(status_code=400, detail="Email já está em uso")

    # Cria novo usuário
    new_user = User(
        id=next_user_id,
        name=user.name,
        email=user.email
    )

    fake_users_db[next_user_id] = new_user
    next_user_id += 1

    return new_user


@app.get("/users", response_model=List[User])
async def get_users():
    return list(fake_users_db.values())


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    if user_id not in fake_users_db:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return fake_users_db[user_id]


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    if user_id not in fake_users_db:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    del fake_users_db[user_id]
    return {"detail": "Usuário deletado com sucesso"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    if user_id not in fake_users_db:
        await manager.send_personal_message("Usuário não encontrado", user_id)
        return

    user = fake_users_db[user_id]
    await manager.connect(user_id, websocket)

    # Envia mensagem de boas-vindas
    await manager.send_personal_message(f"Bem-vindo ao chat, {user.name}!", user_id)

    try:
        while True:
            data = await websocket.receive_text()

            # Envia a confirmação de recebimento para o próprio usuário
            await manager.send_personal_message(f"Você: {data}", user_id)

            # Envia a mensagem para todos os outros usuários conectados
            await manager.broadcast(f"{user.name}: {data}", exclude_user_id=user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await manager.broadcast(f"{user.name} saiu do chat!", exclude_user_id=user_id)


@app.get("/stats")
async def get_stats():
    return {
        "total_users": len(fake_users_db),
        "online_users": len(manager.active_connections),
        "users_online": [fake_users_db[user_id].name for user_id in manager.active_connections.keys()]
    }
