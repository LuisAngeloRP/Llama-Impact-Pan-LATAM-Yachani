import pysqlite3
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import requests
import json
import os
from datetime import datetime
from typing import List, Dict
import base64
import fitz  # PyMuPDF

# Configuración de la página
st.set_page_config(
    page_title="Vista Documento + Chat",
    page_icon="📑",
    layout="wide"
)

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

def get_recent_history(messages: List[Dict], max_messages: int = 5) -> str:
    """Obtiene el historial reciente de mensajes formateado."""
    recent_messages = messages[-max_messages:] if messages else []
    formatted_history = []
    for msg in recent_messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        formatted_history.append(f"{role}: {msg['content']}")
    return "\n".join(formatted_history)

def display_pdf(pdf_path: str):
    """Muestra un PDF en el iframe."""
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def extract_pdf_content(pdf_path: str) -> List[Dict]:
    """
    Extrae el contenido del PDF página por página.
    """
    pages_content = []
    
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            content = page.get_text("text").strip()
            preview = content[:100] + "..." if len(content) > 100 else content
            
            pages_content.append({
                'page_num': page_num + 1,
                'content': content,
                'preview': preview
            })
        return pages_content
    except Exception as e:
        st.error(f"Error al extraer contenido del PDF: {str(e)}")
        return []

def display_content_viewer(pdf_path: str):
    """Muestra el contenido del PDF con navegación mejorada."""
    if not pdf_path or not os.path.exists(pdf_path):
        st.error("El archivo no se encuentra disponible.")
        st.markdown(f"Ruta esperada: {pdf_path}")
        return

    # Extraer contenido del PDF si no está en caché
    cache_key = f"pdf_content_{pdf_path}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = extract_pdf_content(pdf_path)
    
    pages_content = st.session_state[cache_key]
    
    if not pages_content:
        st.error("No se pudo extraer el contenido del documento.")
        return

    # Inicializar página actual
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0

    # Selector de estilo de navegación
    nav_style = st.radio(
        "Estilo de navegación",
        options=["Flechas", "Índice horizontal"],
        horizontal=True
    )

    # Contenedor para el contenido
    content_container = st.container()
    
    if nav_style == "Flechas":
        with content_container:
            st.markdown(f"""
            <div class="content-box">
                <div class="page-header">
                    <h4>Página {st.session_state.current_page + 1} de {len(pages_content)}</h4>
                </div>
                <div class="page-content">
                    {pages_content[st.session_state.current_page]['content'].replace('\n', '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("← Anterior", disabled=st.session_state.current_page <= 0):
                st.session_state.current_page -= 1
                st.rerun()
        
        with col2:
            progress = (st.session_state.current_page + 1) / len(pages_content)
            st.progress(progress)
        
        with col3:
            if st.button("Siguiente →", disabled=st.session_state.current_page >= len(pages_content) - 1):
                st.session_state.current_page += 1
                st.rerun()
    
    else:  # Índice horizontal
        st.markdown("""
        <div class="page-index">
            <div class="index-scroll">
        """, unsafe_allow_html=True)
        
        cols = st.columns(min(10, len(pages_content)))
        for idx, col in enumerate(cols):
            with col:
                page_num = idx + 1
                if st.button(
                    f"{page_num}",
                    key=f"page_{page_num}",
                    disabled=st.session_state.current_page == idx,
                    use_container_width=True
                ):
                    st.session_state.current_page = idx
                    st.rerun()
        
        st.markdown("</div></div>", unsafe_allow_html=True)
        
        with content_container:
            st.markdown(f"""
            <div class="content-box">
                <div class="page-header">
                    <h4>Página {st.session_state.current_page + 1} de {len(pages_content)}</h4>
                </div>
                <div class="page-content">
                    {pages_content[st.session_state.current_page]['content'].replace('\n', '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)

def get_document_info(vectorstores: List[Dict]) -> List[Dict]:
    """Extrae información de los vectorstores para el selector."""
    agent_name = vectorstores[0]['title']
    docs_info = []
    
    agent_dir = os.path.join('data/processed_docs', agent_name)
    
    if os.path.exists(agent_dir):
        pdf_files = [f for f in os.listdir(agent_dir) if f.endswith('.pdf')]
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(agent_dir, pdf_file)
            docs_info.append({
                'title': os.path.splitext(pdf_file)[0],
                'path': pdf_path,
                'agent_name': agent_name
            })
    
    return docs_info

def main():
    st.title("📑 Vista Documento + Chat")

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
    doc_col, chat_col = st.columns([1.2, 0.8])

    # Columna del documento
    with doc_col:
        st.markdown("### 📄 Material de Estudio")
        try:
            docs_info = get_document_info(config['vectorstores'])
            if docs_info:
                st.markdown(f"**🤖 Agente:** {docs_info[0]['agent_name']}")
                selected_doc = st.selectbox(
                    "Seleccionar documento",
                    options=docs_info,
                    format_func=lambda x: x['title']
                )
                
                if selected_doc and os.path.exists(selected_doc['path']):
                    display_content_viewer(selected_doc['path'])
                else:
                    st.error("Archivo no encontrado")
            else:
                st.warning("No se encontraron documentos PDF.")
        except Exception as e:
            st.error(f"Error al cargar documentos: {str(e)}")

    # Columna del chat
    with chat_col:
        st.markdown("### 💬 Asistente IA")
        
        with st.expander("ℹ️ Información del Asistente"):
            st.markdown(f"""
            **{config['name']}**
            - 🎭 Rol: {config['role']}
            - 💬 Estilo: {config['style']}
            - 📝 Nivel: {config['detail_level']}
            """)

        chat_container = st.container()
        with chat_container:
            if "messages" not in st.session_state:
                st.session_state.messages = []
                welcome_message = {
                    "role": "assistant",
                    "content": f"""¡Hola! Soy {config['name']}, tu {config['role']}.
                    Estoy aquí para ayudarte con el material que estás revisando.
                    Puedes preguntarme cualquier cosa sobre el documento.""",
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.messages.append(welcome_message)

            for message in st.session_state.messages:
                show_chat_message(message)

        if prompt := st.chat_input("¿Qué deseas saber sobre el material?"):
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
                            1. Usa la función search_documents para buscar información relevante
                            2. Responde usando SOLO información de los documentos
                            3. Cita las fuentes usando [Documento]
                            4. Mantén un nivel de detalle {config['detail_level'].lower()}
                            5. Si no encuentras información, sugiere cómo reformular la pregunta
                            """
                        }

                        # Preparar mensajes para la API
                        api_messages = [system_message]
                        recent_messages = st.session_state.messages[-5:]
                        for msg in recent_messages:
                            api_messages.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })

                        # Primera llamada a la API para obtener la búsqueda
                        response = st.session_state.aiml_client.create_completion(
                            messages=api_messages,
                            tools=[search_documents_tool()],
                            temperature=config['temperature'],
                            max_tokens=config['max_tokens'],
                            model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
                        )

                        st.write("Debug - Respuesta API inicial:", response)  # Debug

                        # Procesar la respuesta y las llamadas a funciones
                        if "choices" in response and response["choices"]:
                            choice = response["choices"][0].get("message", {})
                            
                            # Si hay llamadas a funciones
                            if "tool_calls" in choice:
                                for tool_call in choice["tool_calls"]:
                                    if tool_call["function"]["name"] == "search_documents":
                                        # Ejecutar búsqueda
                                        query = json.loads(tool_call["function"]["arguments"])["query"]
                                        results = []
                                        
                                        for vs in config['vectorstores']:
                                            docs = vs['retriever'].get_relevant_documents(query)
                                            for doc in docs:
                                                content = doc.page_content.strip()
                                                source = vs['title']
                                                if content not in [r.split(']:')[1].strip() for r in results]:
                                                    results.append(f"[{source}]: {content}")

                                        # Agregar resultados de búsqueda como mensaje de función
                                        search_results = "\n\n".join(results[:config['context_window']])
                                        api_messages.append({
                                            "role": "function",
                                            "name": "search_documents",
                                            "content": search_results if results else "No se encontró información relevante."
                                        })
                                
                                # Segunda llamada a la API para obtener la respuesta final
                                final_response = st.session_state.aiml_client.create_completion(
                                    messages=api_messages,
                                    temperature=config['temperature'],
                                    max_tokens=config['max_tokens'],
                                    model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
                                )
                                
                                st.write("Debug - Respuesta API final:", final_response)  # Debug
                                
                                if "choices" in final_response and final_response["choices"]:
                                    response_content = final_response["choices"][0].get("message", {}).get("content", "")
                                else:
                                    response_content = "Lo siento, no pude procesar la información adecuadamente."
                            else:
                                # Si no hay llamadas a funciones, usar la respuesta directa
                                response_content = choice.get("content", "")

                            if not response_content:
                                response_content = "Lo siento, no pude generar una respuesta apropiada."

                            # Mostrar y guardar la respuesta
                            assistant_message = {
                                "role": "assistant",
                                "content": response_content,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            st.markdown(response_content)
                            st.session_state.messages.append(assistant_message)
                            save_agent_history(agent_id, st.session_state.messages)
                        else:
                            st.error("No se recibió una respuesta válida de la API")
                            st.write("Respuesta completa:", response)

                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg,
                            "timestamp": datetime.now().isoformat()
                        })

# Estilos CSS
st.markdown("""
<style>
    /* Contenedor principal */
    .content-box {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        min-height: 500px;
    }

    /* Encabezado de página */
    .page-header {
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
    }

    /* Contenido de página */
    .page-content {
        font-size: 1rem;
        line-height: 1.6;
        text-align: justify;
        padding: 1rem;
        white-space: pre-wrap;
    }

    /* Navegación con flechas */
    .stButton button {
        width: 100%;
        padding: 0.5rem;
    }

    /* Índice horizontal */
    .page-index {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        overflow-x: auto;
        white-space: nowrap;
    }

    .index-scroll {
        display: flex;
        gap: 0.5rem;
        padding: 0.5rem;
    }

    /* Botones del índice */
    .page-index button {
        min-width: 40px;
        height: 40px;
        padding: 0.25rem;
        border-radius: 5px;
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        cursor: pointer;
    }

    .page-index button:hover {
        background-color: #e9ecef;
    }

    .page-index button:disabled {
        background-color: #1f77b4;
        color: white;
        border: none;
    }

    /* Barra de progreso */
    .stProgress {
        margin-top: 0.5rem;
    }

    /* Contenedor del documento */
    .doc-viewer {
        height: calc(100vh - 200px);
        overflow-y: auto;
        padding: 1rem;
    }

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