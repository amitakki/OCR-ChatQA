import streamlit as st
from sidebar import display_sidebar
from chat_interface import display_chat_interface
from api_utils import check_health, get_health_info
import time

# Page configuration
st.set_page_config(
    page_title="OCR-Enhanced RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better UI
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .status-indicator {
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: bold;
    }
    
    .status-healthy {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .status-unhealthy {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    .feature-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e1e4e8;
        border-radius: 8px;
        background: #fafbfc;
    }
    
    .sidebar .stSelectbox > div > div {
        background-color: #f0f2f6;
    }
    
    .stProgress > div > div > div > div {
        background-color: #667eea;
    }
</style>
""",
    unsafe_allow_html=True,
)


def display_header():
    """Display main application header"""
    st.markdown(
        """
    <div class="main-header">
        <h1>🤖 OCR-Enhanced RAG Chatbot</h1>
        <p>Intelligent document processing with OCR capabilities</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def display_system_status():
    """Display system health status"""
    with st.expander("🔧 System Status", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            if check_health():
                st.markdown(
                    """
                <div class="status-indicator status-healthy">
                    ✅ System Online
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                <div class="status-indicator status-unhealthy">
                    ❌ System Offline
                </div>
                """,
                    unsafe_allow_html=True,
                )

        with col2:
            health_info = get_health_info()
            if health_info:
                if health_info.get("ocr_enabled", False):
                    st.markdown(
                        """
                    <div class="status-indicator status-healthy">
                        🔍 OCR Available
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        """
                    <div class="status-indicator status-unhealthy">
                        ❌ OCR Unavailable
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

        # Display detailed health information
        if health_info:
            st.subheader("🔍 System Details")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**📄 Supported Formats:**")
                for fmt in health_info.get("supported_formats", []):
                    st.write(f"• {fmt}")

            with col2:
                st.markdown("**🚀 Available Features:**")
                for feature in health_info.get("features", []):
                    st.write(f"• {feature}")


def display_features_overview():
    """Display features overview"""
    st.subheader("🌟 Key Features")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
        <div class="feature-card">
            <h4>🔍 OCR Processing</h4>
            <p>Automatically extracts text from scanned PDFs and image-based documents</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div class="feature-card">
            <h4>🤖 RAG Chat</h4>
            <p>Chat with your documents using advanced retrieval-augmented generation</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        <div class="feature-card">
            <h4>📊 Status Tracking</h4>
            <p>Real-time monitoring of document processing and system health</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def display_usage_metrics():
    """Display usage metrics and statistics"""
    if "documents" in st.session_state and st.session_state.documents:
        documents = st.session_state.documents

        # Calculate statistics
        total_docs = len(documents)
        completed = len(
            [d for d in documents if d.get("processing_status") == "completed"]
        )
        processing = len(
            [d for d in documents if d.get("processing_status") == "processing"]
        )
        failed = len([d for d in documents if d.get("processing_status") == "failed"])
        pending = len([d for d in documents if d.get("processing_status") == "pending"])

        st.subheader("📊 Usage Statistics")

        # Metrics row
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>📄</h3>
                <h2>{total_docs}</h2>
                <p>Total Documents</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>✅</h3>
                <h2>{completed}</h2>
                <p>Completed</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>⏳</h3>
                <h2>{processing}</h2>
                <p>Processing</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col4:
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>⏸️</h3>
                <h2>{pending}</h2>
                <p>Pending</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col5:
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>❌</h3>
                <h2>{failed}</h2>
                <p>Failed</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Processing methods breakdown
        if completed > 0:
            st.subheader("🔧 Processing Methods")
            methods = {}
            for doc in documents:
                if doc.get("processing_status") == "completed":
                    method = doc.get("processing_method", "unknown")
                    methods[method] = methods.get(method, 0) + 1

            if methods:
                method_cols = st.columns(len(methods))
                for i, (method, count) in enumerate(methods.items()):
                    with method_cols[i]:
                        method_display = {
                            "standard": "📄 Standard Text",
                            "pure_ocr": "🔍 Pure OCR",
                            "ocr": "🔍 OCR Enhanced",
                            "unknown": "❓ Unknown",
                        }.get(method, f"🔧 {method}")

                        st.metric(method_display, count)


def initialize_session_state():
    """Initialize session state variables"""
    # Chat-related state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "session_id" not in st.session_state:
        st.session_state.session_id = None

    # UI state
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True

    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False

    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()

    # Document management state
    if "documents" not in st.session_state:
        st.session_state.documents = []

    if "selected_doc_for_stats" not in st.session_state:
        st.session_state.selected_doc_for_stats = None


def display_welcome_message():
    """Display welcome message for new users"""
    if st.session_state.show_welcome and not st.session_state.messages:
        st.info(
            """
        👋 **Welcome to the OCR-Enhanced RAG Chatbot!**
        
        To get started:
        1. 📤 Upload documents using the sidebar (supports text and scanned PDFs)
        2. ⏳ Wait for processing to complete (watch the status indicators)
        3. 💬 Start chatting with your documents!
        
        💡 **Tip**: The system automatically detects scanned PDFs and uses OCR to extract text.
        """
        )

        if st.button("🚀 Got it, let's start!"):
            st.session_state.show_welcome = False
            st.rerun()


def display_auto_refresh_controls():
    """Display auto-refresh controls"""
    with st.expander("⚙️ Advanced Settings", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            auto_refresh = st.checkbox(
                "🔄 Auto-refresh document status",
                value=st.session_state.auto_refresh,
                help="Automatically refresh document status every 10 seconds",
            )
            st.session_state.auto_refresh = auto_refresh

        with col2:
            if st.button("🔄 Manual Refresh"):
                st.session_state.last_refresh = time.time()
                st.rerun()

        # Auto-refresh logic
        if st.session_state.auto_refresh:
            current_time = time.time()
            if current_time - st.session_state.last_refresh > 10:  # 10 seconds
                st.session_state.last_refresh = current_time
                st.rerun()


def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()

    # Display header
    display_header()

    # Display system status
    display_system_status()

    # Create main layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Main chat interface
        st.subheader("💬 Chat Interface")

        # Welcome message
        display_welcome_message()

        # Chat interface container
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        display_chat_interface()
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Features overview (only show if no documents)
        if (
            not st.session_state.get("documents")
            or len(st.session_state.documents) == 0
        ):
            display_features_overview()
        else:
            # Show usage metrics if documents exist
            display_usage_metrics()

    # Display sidebar
    display_sidebar()

    # Auto-refresh controls
    display_auto_refresh_controls()

    # Footer
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; color: #666; padding: 1rem;">
        🤖 OCR-Enhanced RAG Chatbot | Built with Streamlit, FastAPI, and LangChain
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
