"""CSS injection helpers for the Streamlit interface."""

import streamlit as st


def inject_theme_css(dark_mode: bool = False) -> None:
    """Inject the app theme CSS."""
    if dark_mode:
        palette = {
            "bg": "#101417",
            "surface": "#171d21",
            "surface_2": "#1f272c",
            "text": "#eef3f0",
            "muted": "#9aa8a1",
            "border": "rgba(238, 243, 240, 0.12)",
            "accent": "#4cc9a6",
            "accent_2": "#6ea8fe",
            "danger": "#ff6b6b",
            "warning": "#f2b84b",
            "success": "#57cc99",
            "user": "#214e48",
            "assistant": "#202a32",
            "shadow": "none",
        }
    else:
        palette = {
            "bg": "#f4f7f6",
            "surface": "#ffffff",
            "surface_2": "#eef3f1",
            "text": "#1d2726",
            "muted": "#62706b",
            "border": "rgba(29, 39, 38, 0.10)",
            "accent": "#0f8a73",
            "accent_2": "#2f6fed",
            "danger": "#d94f45",
            "warning": "#b7791f",
            "success": "#27845f",
            "user": "#d8f0e9",
            "assistant": "#ffffff",
            "shadow": "0 10px 26px rgba(24, 42, 38, 0.08)",
        }

    st.markdown(
        f"""
        <style>
        :root {{
            --bg: {palette["bg"]};
            --surface: {palette["surface"]};
            --surface-2: {palette["surface_2"]};
            --text: {palette["text"]};
            --muted: {palette["muted"]};
            --border: {palette["border"]};
            --accent: {palette["accent"]};
            --accent-2: {palette["accent_2"]};
            --danger: {palette["danger"]};
            --warning: {palette["warning"]};
            --success: {palette["success"]};
            --user: {palette["user"]};
            --assistant: {palette["assistant"]};
            --shadow: {palette["shadow"]};
        }}

        html, body, [class*="css"] {{
            font-family: Inter, "Noto Sans TC", "Microsoft JhengHei", Arial, sans-serif;
            letter-spacing: 0;
        }}

        .stApp {{
            background:
                linear-gradient(180deg, rgba(15, 138, 115, 0.06), transparent 240px),
                var(--bg);
            color: var(--text);
        }}

        footer, #MainMenu, header[data-testid="stHeader"] {{
            visibility: hidden;
        }}

        [data-testid="stAppViewContainer"] > .main {{
            padding-top: 0;
        }}

        [data-testid="stAppViewBlockContainer"] {{
            max-width: 1480px;
            padding: 22px 28px 28px;
        }}

        .app-shell {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 12px 0 18px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 16px;
        }}

        .brand-title {{
            margin: 0;
            font-size: 1.55rem;
            line-height: 1.2;
            font-weight: 750;
            color: var(--text);
        }}

        .brand-subtitle {{
            margin-top: 5px;
            color: var(--muted);
            font-size: 0.88rem;
        }}

        .top-status {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--muted);
            font-size: 0.82rem;
            white-space: nowrap;
        }}

        .status-dot {{
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: var(--success);
            box-shadow: 0 0 0 4px rgba(39, 132, 95, 0.16);
        }}

        .metric-row {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 16px;
        }}

        .metric-tile {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 13px;
            box-shadow: var(--shadow);
            min-height: 76px;
        }}

        .metric-label {{
            color: var(--muted);
            font-size: 0.78rem;
            line-height: 1.2;
            margin-bottom: 7px;
        }}

        .metric-value {{
            color: var(--text);
            font-size: 1.36rem;
            font-weight: 760;
            line-height: 1;
        }}

        .panel {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
            box-shadow: var(--shadow);
        }}

        .section-title {{
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 10px;
            margin: 0 0 12px;
            color: var(--text);
            font-size: 1rem;
            font-weight: 720;
        }}

        .section-note {{
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 500;
        }}

        .inventory-list {{
            display: grid;
            gap: 8px;
        }}

        .inventory-item {{
            border: 1px solid var(--border);
            border-left: 4px solid var(--success);
            border-radius: 8px;
            background: var(--surface);
            padding: 10px 11px;
        }}

        .inventory-item.warning {{ border-left-color: var(--warning); }}
        .inventory-item.danger {{ border-left-color: var(--danger); }}

        .inventory-main {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }}

        .inventory-name {{
            color: var(--text);
            font-weight: 700;
            font-size: 0.95rem;
            overflow-wrap: anywhere;
        }}

        .inventory-date {{
            color: var(--muted);
            font-size: 0.76rem;
            white-space: nowrap;
        }}

        .inventory-meta {{
            margin-top: 6px;
            color: var(--muted);
            font-size: 0.78rem;
            overflow-wrap: anywhere;
        }}

        .empty-state {{
            border: 1px dashed var(--border);
            border-radius: 8px;
            padding: 18px 14px;
            color: var(--muted);
            background: var(--surface-2);
            font-size: 0.9rem;
        }}

        .chat-frame {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            box-shadow: var(--shadow);
        }}

        .chat-bubble {{
            width: fit-content;
            max-width: min(76%, 680px);
            border-radius: 8px;
            border: 1px solid var(--border);
            padding: 11px 13px;
            margin: 9px 0;
            font-size: 0.94rem;
            line-height: 1.58;
            overflow-wrap: anywhere;
        }}

        .assistant-bubble {{
            background: var(--assistant);
            color: var(--text);
            margin-right: auto;
        }}

        .user-bubble {{
            background: var(--user);
            color: var(--text);
            margin-left: auto;
        }}

        .log-panel {{
            min-height: 420px;
            max-height: 620px;
            overflow: auto;
            background: #111820;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 12px;
            font-family: Consolas, "Courier New", monospace;
            font-size: 0.76rem;
            line-height: 1.55;
            color: #d7dee8;
        }}

        .log-step {{
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
            padding-bottom: 10px;
            margin-bottom: 10px;
        }}

        .log-thought {{ color: #f6d365; }}
        .log-tool {{ color: #79b8ff; }}
        .log-observation {{ color: #7ee787; padding-left: 10px; }}
        .log-indent {{ color: #8b949e; }}

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stSelectbox [data-baseweb="select"] {{
            border-radius: 8px;
        }}

        .stButton > button,
        button[data-testid="stPopoverButton"] {{
            border-radius: 8px;
            border: 1px solid var(--border);
            font-weight: 680;
            min-height: 40px;
        }}

        .stButton > button[kind="primary"] {{
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }}

        .stButton > button:hover,
        button[data-testid="stPopoverButton"]:hover {{
            border-color: var(--accent);
        }}

        div[data-testid="stExpander"] {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: none;
        }}

        hr {{
            border-color: var(--border);
        }}

        @media (max-width: 900px) {{
            [data-testid="stAppViewBlockContainer"] {{
                padding: 16px 14px 20px;
            }}

            .app-shell {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .metric-row {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .chat-bubble {{
                max-width: 92%;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
