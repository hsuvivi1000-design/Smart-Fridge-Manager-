"""
主題 CSS 注入模組 — 支援淺色/深色模式切換
"""
import streamlit as st


def inject_theme_css(dark_mode=False):
    """根據模式注入對應的 CSS"""
    if dark_mode:
        bg = "#0E1117"; panel_bg = "#161B22"; text = "#E6EDF3"; sub_text = "#8B949E"
        chat_bg = "#1A1A2E"; user_bubble = "#2D4A3E"; asst_bubble = "#1E2A3A"
        input_bg = "#21262D"; border = "rgba(255,255,255,0.08)"
        inv_bg = "#161B22"; inv_item_bg = "rgba(255,255,255,0.04)"
    else:
        bg = "#FFFFFF"; panel_bg = "#F7F7F8"; text = "#333333"; sub_text = "#888888"
        chat_bg = "#FFFFFF"; user_bubble = "#E8D5B7"; asst_bubble = "#F0F0F0"
        input_bg = "#F5F5F5"; border = "rgba(0,0,0,0.08)"
        inv_bg = "#FAFAFA"; inv_item_bg = "rgba(0,0,0,0.02)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {bg}; color: {text}; }}
    footer, #MainMenu, header[data-testid="stHeader"] {{ visibility: hidden; }}
    [data-testid="stSidebar"] {{ display: none; }}
    [data-testid="stAppViewBlockContainer"] {{ padding-top: 1rem; }}

    .panel-header {{
        font-size: 1.1rem; font-weight: 700; padding: 12px 0 8px 0;
        border-bottom: 1px solid {border}; margin-bottom: 12px; color: {text};
    }}
    .inventory-item {{
        padding: 10px 14px; margin: 8px 0; border-radius: 6px;
        background: {inv_item_bg}; font-size: 0.92rem; color: {text};
    }}
    .item-category {{ font-size: 0.8rem; color: {sub_text}; }}

    .chat-area {{
        background: {chat_bg}; border-radius: 12px; padding: 16px;
        border: 1px solid {border};
    }}
    .chat-bubble {{
        padding: 12px 16px; border-radius: 14px; margin: 10px 0;
        max-width: 82%; font-size: 0.95rem; line-height: 1.6; color: {text};
    }}
    .assistant-bubble {{ background: {asst_bubble}; margin-right: auto; }}
    .user-bubble {{ background: {user_bubble}; margin-left: auto; text-align: right; }}

    .log-panel {{
        background: #1A1A2E; border-radius: 10px; padding: 16px;
        font-family: 'Consolas', 'Courier New', monospace; font-size: 0.78rem;
        color: #C9D1D9; min-height: 200px;
    }}
    .log-thought {{ color: #FFD600; }}
    .log-tool {{ color: #58A6FF; }}
    .log-memory {{ color: #56D364; }}
    .log-rag {{ color: #D2A8FF; }}
    .log-indent {{ color: #8B949E; padding-left: 16px; }}

    .divider {{ border: none; height: 1px; background: {border}; margin: 1rem 0; }}

    .stButton > button {{
        border-radius: 8px; font-weight: 500;
        transition: transform 0.15s ease;
    }}
    .stButton > button:hover {{ transform: translateY(-1px); }}
    </style>
    """, unsafe_allow_html=True)
