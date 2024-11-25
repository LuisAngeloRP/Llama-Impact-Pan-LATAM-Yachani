import os
import streamlit as st
from datetime import datetime
from utils.document_manager import DocumentManager

# Cargar variables de entorno
AIML_API_KEY = st.secrets["AIML_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Configuración de la página
st.set_page_config(
    page_title="Yachani - Biblioteca Educativa",
    page_icon="📚",
    layout="wide"
)

# Inicializar el gestor de documentos
doc_manager = DocumentManager()

st.title("📚 Yachani")
st.markdown("""
### Democratizando la educación a través del conocimiento compartido

Yachani es una plataforma educativa que pone al alcance de todos recursos educativos 
de calidad mediante tecnología avanzada de procesamiento de lenguaje natural.
""")

# Sección de Páginas Disponibles
st.markdown("## 🧭 Guía de Navegación")

# Usar columnas para una mejor presentación
col1, col2 = st.columns(2)

with col1:
    with st.container():
        st.markdown("""
        ### 📚 Catálogo
        En esta página encontrarás:
        - Biblioteca completa de documentos
        - Filtros por categoría, nivel y tipo
        - Sistema de búsqueda avanzada
        - Vista previa de documentos
        - Selección de materiales para tu asistente
        
        ### 🤖 Gestión de Asistentes
        Aquí podrás:
        - Crear asistentes personalizados
        - Configurar el estilo de enseñanza
        - Seleccionar documentos base
        - Administrar asistentes existentes
        - Ajustar parámetros avanzados
        """)

with col2:
    with st.container():
        st.markdown("""
        ### 💬 Chat Educativo
        Esta página te permite:
        - Interactuar con tu asistente
        - Hacer preguntas sobre los documentos
        - Obtener explicaciones detalladas
        - Guardar conversaciones importantes
        - Acceder a historiales de chat
        
        ### 📤 Subir Documentos
        En esta sección puedes:
        - Cargar nuevos documentos
        - Procesar automáticamente el contenido
        - Categorizar materiales
        - Añadir metadatos educativos
        - Verificar el estado del procesamiento
        """)

# Sección de Estadísticas
st.markdown("## 📊 Estadísticas de la Biblioteca")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Documentos", doc_manager.get_total_documents())

with col2:
    st.metric("Categorías", len(doc_manager.get_categories()))

with col3:
    st.metric("Documentos Nuevos (Hoy)", 
              doc_manager.get_new_documents_count(datetime.now()))

# Mostrar flujo de trabajo recomendado
st.markdown("""
## 🚀 ¿Cómo Empezar?

1. **Explorar el Catálogo**
   - Ve a 📚 Catálogo
   - Navega por los documentos disponibles
   - Selecciona los materiales que te interesan

2. **Crear tu Asistente**
   - Dirígete a 🤖 Gestión de Asistentes
   - Crea un nuevo asistente personalizado
   - Configura sus parámetros según tus necesidades

3. **Comenzar a Aprender**
   - Abre 💬 Chat Educativo
   - Interactúa con tu asistente
   - Haz preguntas sobre el material

4. **Contribuir (Opcional)**
   - Usa 📤 Subir Documentos
   - Comparte materiales educativos
   - Ayuda a crecer la biblioteca
""")

# Mostrar categorías populares
st.markdown("## 🏷️ Categorías Destacadas")
categories = doc_manager.get_popular_categories()
cols = st.columns(4)
for idx, (category, count) in enumerate(categories.items()):
    with cols[idx % 4]:
        st.button(
            f"{category} ({count} docs)",
            key=f"cat_{category}",
            use_container_width=True
        )

# Información adicional en el sidebar
with st.sidebar:
    st.success("Explora nuestras páginas para descubrir más.")
    
    # Estado del sistema
    st.markdown("### 🔧 Estado del Sistema")
    st.markdown("""
    - ✅ API Conectada
    - ✅ Base de Datos Activa
    - ✅ Procesamiento Disponible
    """)
    
    # Ayuda rápida
    with st.expander("❓ Ayuda Rápida"):
        st.markdown("""
        - Para dudas técnicas, consulta la documentación
        - Para problemas con documentos, contacta al administrador
        - Para sugerencias, usa el formulario de feedback
        """)

if __name__ == "__main__":
    pass