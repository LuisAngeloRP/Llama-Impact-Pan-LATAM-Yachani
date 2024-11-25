import pysqlite3
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import requests
import json
import os
from datetime import datetime
from typing import List, Dict

class AimlApiChat:
    def __init__(self, api_key: str, base_url: str = "https://api.aimlapi.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def create_completion(self, messages: List[Dict], tools: List[Dict] = None, **kwargs):
        """Crear una completion usando la API AI/ML"""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": kwargs.get("model", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "top_p": kwargs.get("top_p", 1),
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

def search_documents_tool():
    """Define la herramienta de búsqueda de documentos"""
    return {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Busca información en los documentos base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La consulta de búsqueda"
                    }
                },
                "required": ["query"]
            }
        }
    }

def main():
    st.title("💬 Chat Educativo")

    # Verificar configuración del agente
    if 'current_agent_config' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.warning("""
            ⚠️ No hay un asistente configurado.
            Por favor, configura tu asistente primero.
            """)
            if st.button("🤖 Configurar Asistente", use_container_width=True):
                st.switch_page("pages/2_🤖_agents.py")
        st.stop()

    config = st.session_state.current_agent_config
    agent_id = get_agent_id(config)

    # Inicializar el cliente de AI/ML API
    if 'aiml_client' not in st.session_state:
        st.session_state.aiml_client = AimlApiChat(
            api_key=st.secrets["AIML_API_KEY"]
        )

    # Layout principal
    chat_col, info_col = st.columns([3, 1])

    with info_col:
        # [Mantener el mismo código de la interfaz de usuario...]
        pass

    with chat_col:
        # Inicializar chat
        if "messages" not in st.session_state:
            st.session_state.messages = []
            welcome_message = {
                "role": "assistant",
                "content": f"""¡Hola! Soy {config['name']}, tu {config['role']}.
                Estoy aquí para ayudarte con los documentos que has seleccionado.
                Para obtener mejores resultados, por favor sé específico en tus preguntas.""",
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.messages.append(welcome_message)

        # Mostrar historial
        for message in st.session_state.messages:
            show_chat_message(message)

        # Input del usuario
        if prompt := st.chat_input("¿Qué deseas saber?"):
            user_message = {
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.messages.append(user_message)
            show_chat_message(user_message)

            with st.chat_message("assistant"):
                with st.spinner(f"💭 {config['name']} está pensando..."):
                    try:
                        # Preparar el contexto del sistema
                        system_message = {
                            "role": "system",
                            "content": f"""Actúa como {config['name']}, un {config['role']} con estilo {config['style'].lower()}.
                            
                            Instrucciones:
                            1. Usa la función search_documents para encontrar información relevante
                            2. Responde usando SOLO información de los documentos
                            3. Cita las fuentes usando [Documento]
                            4. Mantén un nivel de detalle {config['detail_level'].lower()}
                            5. Si no encuentras información, sugiere cómo reformular la pregunta
                            6. Mantén la coherencia con las respuestas anteriores"""
                        }

                        # Preparar los mensajes para la API
                        api_messages = [system_message]
                        
                        # Agregar historial reciente (últimos 5 mensajes)
                        recent_messages = st.session_state.messages[-5:]
                        for msg in recent_messages:
                            api_messages.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })

                        # Configurar la herramienta de búsqueda
                        tools = [search_documents_tool()]

                        # Llamar a la API
                        try:
                            response = st.session_state.aiml_client.create_completion(
                                messages=api_messages,
                                tools=tools,
                                temperature=config['temperature'],
                                max_tokens=config['max_tokens'],
                                model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
                            )

                            # Procesar la respuesta - versión simplificada para debug
                            st.write("Respuesta API:", response)  # Debug

                            # Extraer el contenido de la respuesta
                            if isinstance(response, dict):
                                response_content = response.get('content') or response.get('message', {}).get('content')
                                
                                if not response_content and 'choices' in response:
                                    first_choice = response['choices'][0]
                                    if isinstance(first_choice, dict):
                                        message = first_choice.get('message', {})
                                        response_content = message.get('content', '')

                                if response_content:
                                    assistant_message = {
                                        "role": "assistant",
                                        "content": response_content,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    
                                    st.markdown(response_content)
                                    st.session_state.messages.append(assistant_message)
                                    save_agent_history(agent_id, st.session_state.messages)
                                else:
                                    st.error("No se pudo extraer una respuesta válida de la API")
                                    st.write("Estructura de respuesta recibida:", response)
                            else:
                                st.error("Respuesta inesperada de la API")
                                st.write("Tipo de respuesta:", type(response))
                                st.write("Contenido:", response)

                        except Exception as e:
                            error_msg = f"❌ Error en la llamada a la API: {str(e)}"
                            st.error(error_msg)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": error_msg,
                                "timestamp": datetime.now().isoformat()
                            })

                        # Procesar la respuesta
                        if "choices" in response and response["choices"]:
                            choice = response["choices"][0]
                            if "tool_calls" in choice.get("message", {}):
                                # Procesar llamadas a funciones
                                for tool_call in choice["message"]["tool_calls"]:
                                    if tool_call["function"]["name"] == "search_documents":
                                        # Ejecutar búsqueda real en los documentos
                                        query = json.loads(tool_call["function"]["arguments"])["query"]
                                        results = []
                                        
                                        for vs in config['vectorstores']:
                                            docs = vs['retriever'].get_relevant_documents(query)
                                            for doc in docs:
                                                content = doc.page_content.strip()
                                                source = vs['title']
                                                if content not in [r.split(']:')[1].strip() for r in results]:
                                                    results.append(f"[{source}]: {content}")

                                        # Agregar resultados como mensaje del asistente
                                        api_messages.append({
                                            "role": "function",
                                            "name": "search_documents",
                                            "content": "\n\n".join(results[:config['context_window']])
                                        })

                                # Obtener respuesta final
                                final_response = st.session_state.aiml_client.create_completion(
                                    messages=api_messages,
                                    temperature=config['temperature'],
                                    max_tokens=config['max_tokens'],
                                    model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
                                )

                                response_content = final_response["choices"][0]["message"]["content"]
                            else:
                                response_content = choice["message"]["content"]

                            assistant_message = {
                                "role": "assistant",
                                "content": response_content,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            st.markdown(response_content)
                            st.session_state.messages.append(assistant_message)
                            
                            # Guardar historial automáticamente
                            save_agent_history(agent_id, st.session_state.messages)

                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg,
                            "timestamp": datetime.now().isoformat()
                        })

# Mantener las funciones auxiliares existentes
def load_agent_history(agent_id: str) -> List[Dict]:
    """Carga el historial de conversaciones de un agente específico."""
    history_path = os.path.join("data", "chat_history", f"{agent_id}.json")
    if os.path.exists(history_path):
        with open(history_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_agent_history(agent_id: str, messages: List[Dict]):
    """Guarda el historial de conversaciones de un agente."""
    os.makedirs(os.path.join("data", "chat_history"), exist_ok=True)
    history_path = os.path.join("data", "chat_history", f"{agent_id}.json")
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def format_timestamp(timestamp: str) -> str:
    """Formatea un timestamp para mostrar."""
    dt = datetime.fromisoformat(timestamp)
    return dt.strftime("%d/%m/%Y %H:%M")

def show_chat_message(message: Dict, show_timestamp: bool = True):
    """Muestra un mensaje del chat con formato mejorado."""
    with st.chat_message(message["role"]):
        if show_timestamp and "timestamp" in message:
            st.caption(format_timestamp(message["timestamp"]))
        st.markdown(message["content"])

def get_agent_id(config: Dict) -> str:
    """Genera un ID único para el agente basado en su configuración."""
    return f"agent_{config['name']}_{datetime.now().strftime('%Y%m%d')}"

# Mantener los estilos CSS existentes
st.markdown("""
<style>
    /* Mensajes del chat */
    .stChatMessage {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        background-color: #f8f9fa;
    }
    
    /* Información del agente */
    .stSidebar .stMarkdown {
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    /* Timestamps */
    .stChatMessage small {
        color: #6c757d;
        font-size: 0.8em;
    }
    
    /* Contenedores */
    .stContainer {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Input del chat */
    .stChatInputContainer {
        padding: 1rem;
        background-color: white;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()