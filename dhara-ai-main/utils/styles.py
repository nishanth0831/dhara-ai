import streamlit as st

# Theme constants for consistency across Python and CSS
THEME = {
    "bg": "#0b1220",
    "surface": "#0f172a",
    "surface2": "#111c33",
    "text": "#e5e7eb",
    "muted": "#94a3b8",
    "border": "rgba(148, 163, 184, 0.18)",
    "brand": "#60a5fa",
    "brand_dark": "#3b82f6",
    "good": "#22c55e",
    "warn": "#fbbf24",
    "bad": "#f87171",
    "brand_bg_alpha": "rgba(96, 165, 250, 0.16)",
}

def apply_custom_css():
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        :root {{
            /* Corporate dark theme tokens */
            --bg: {THEME['bg']};
            --surface: {THEME['surface']};
            --surface2: {THEME['surface2']};
            --text: {THEME['text']};
            --muted: {THEME['muted']};
            --border: {THEME['border']};
            --brand: {THEME['brand']};
            --brandDark: {THEME['brand_dark']};
            --good: {THEME['good']};
            --warn: {THEME['warn']};
            --bad: {THEME['bad']};
        }}
        
        html, body, [class*="st-"] {{
            font-family: 'Inter', sans-serif;
        }}
        
        .stApp {{ background-color: var(--bg); }}

        /* Ensure default text colors on dark background */
        body, .stMarkdown, .stText, p, span, li, code, small {{ color: var(--text); }}
        a {{ color: var(--brand); text-decoration: none; transition: color 0.2s; }}
        a:hover {{ color: #93c5fd; }}

        /* Streamlit containers background */
        section.main {{ background: transparent; }}
        
        /* Layout width - wider for better data visualization */
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }}

        /* Fullscreen landing shell */
        .dhara-shell {{
            /* min-height removed */
            display: flex;
            flex-direction: column;
            gap: 18px;
        }}

        .dhara-topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 16px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(15,23,42,0.65);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }}

        .dhara-brand {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 800;
            letter-spacing: 0.01em;
            color: var(--text);
            font-size: 1.1rem;
        }}

        .dhara-brand-badge {{
            width: 34px;
            height: 34px;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: {THEME['brand_bg_alpha']};
            border: 1px solid var(--border);
            color: #93c5fd;
            font-weight: 900;
        }}

        /* Top nav container */
        .dhara-nav {{
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 8px 10px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            position: sticky;
            top: 0.75rem;
            z-index: 50;
            margin-bottom: 1.5rem;
        }}

        /* Hero */
        .dhara-hero {{
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 32px;
            background:
              radial-gradient(1200px 380px at 20% -10%, rgba(96, 165, 250, 0.15), rgba(11, 18, 32, 0) 55%),
              radial-gradient(900px 320px at 90% 10%, rgba(34, 197, 94, 0.10), rgba(11, 18, 32, 0) 55%),
              linear-gradient(180deg, rgba(15,23,42,0.95), rgba(15,23,42,0.98));
            box-shadow: 0 14px 40px rgba(0, 0, 0, 0.35);
            overflow: hidden;
            position: relative;
        }}

        .dhara-hero::after {{
            content: "";
            position: absolute;
            inset: -2px;
            background: linear-gradient(120deg, rgba(96,165,250,0.15), rgba(34,197,94,0.1), rgba(11,18,32,0));
            filter: blur(30px);
            opacity: 0.55;
            animation: dharaGlow 10s ease-in-out infinite;
            pointer-events: none;
        }}

        @keyframes dharaGlow {{
            0% {{ transform: translate3d(-10px, -6px, 0) scale(1.02); opacity: 0.45; }}
            50% {{ transform: translate3d(10px, 6px, 0) scale(1.04); opacity: 0.65; }}
            100% {{ transform: translate3d(-10px, -6px, 0) scale(1.02); opacity: 0.45; }}
        }}

        /* Animations */
        @keyframes dharaFadeUp {{
            from {{ opacity: 0; transform: translate3d(0, 10px, 0); }}
            to   {{ opacity: 1; transform: translate3d(0, 0, 0); }}
        }}

        .dhara-anim {{
            animation: dharaFadeUp 520ms ease-out both;
            will-change: transform, opacity;
        }}
        .dhara-delay-1 {{ animation-delay: 60ms; }}
        .dhara-delay-2 {{ animation-delay: 120ms; }}
        .dhara-delay-3 {{ animation-delay: 180ms; }}
        .dhara-delay-4 {{ animation-delay: 240ms; }}

        /* Workflow stepper */
        .dhara-workflow {{
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            background: rgba(15,23,42,0.62);
            position: relative;
            overflow: hidden;
        }}

        .dhara-workflow::before {{
            content: "";
            position: absolute;
            inset: -2px;
            background: radial-gradient(800px 120px at 10% 0%, rgba(96,165,250,0.12), rgba(15,23,42,0) 60%),
                        radial-gradient(700px 120px at 90% 0%, rgba(34,197,94,0.08), rgba(15,23,42,0) 60%);
            opacity: 0.9;
            pointer-events: none;
        }}

        .dhara-workflow-inner {{
            position: relative;
            z-index: 2;
        }}

        .dhara-workflow-title {{
            font-weight: 800;
            color: var(--text);
            margin: 0 0 16px 0;
            font-size: 1.1rem;
        }}

        .dhara-stepper {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }}

        .dhara-stepper-item {{
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(15,23,42,0.72);
            padding: 16px;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s;
        }}
        
        .dhara-stepper-item:hover {{
            transform: translateY(-2px);
            border-color: rgba(148, 163, 184, 0.4);
        }}

        .dhara-stepper-item::after {{
            content: "";
            position: absolute;
            left: -40%;
            top: 0;
            height: 100%;
            width: 40%;
            background: linear-gradient(90deg, rgba(255,255,255,0), rgba(96,165,250,0.10), rgba(255,255,255,0));
            transform: skewX(-18deg);
            animation: dharaShine 5.5s ease-in-out infinite;
            opacity: 0.65;
            pointer-events: none;
        }}

        @keyframes dharaShine {{
            0% {{ transform: translateX(-120%) skewX(-18deg); opacity: 0.0; }}
            15% {{ opacity: 0.5; }}
            35% {{ opacity: 0.0; }}
            100% {{ transform: translateX(520%) skewX(-18deg); opacity: 0.0; }}
        }}

        .dhara-stepper-kicker {{
            font-size: 0.75rem;
            font-weight: 700;
            color: #93c5fd;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}

        .dhara-stepper-head {{
            font-size: 1rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 8px;
        }}

        .dhara-stepper-desc {{
            color: var(--muted);
            font-size: 0.875rem;
            line-height: 1.4;
        }}

        @media (max-width: 980px) {{
            .dhara-stepper {{ grid-template-columns: 1fr; }}
        }}

        .dhara-hero-content {{
            position: relative;
            z-index: 2;
        }}

        .dhara-kicker {{
            color: var(--brand);
            font-weight: 600;
            letter-spacing: 0.05em;
            font-size: 0.875rem;
            margin-bottom: 12px;
            text-transform: uppercase;
        }}

        .dhara-title {{
            color: var(--text);
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0 0 16px 0;
            line-height: 1.1;
        }}

        .dhara-subtitle {{
            color: var(--muted);
            font-size: 1.125rem;
            line-height: 1.6;
            margin: 0 0 24px 0;
            max-width: 800px;
        }}

        .dhara-badges {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 16px;
        }}

        .dhara-badge {{
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: rgba(15,23,42,0.6);
            color: var(--text);
            font-weight: 500;
            font-size: 0.85rem;
        }}

        /* Cards */
        .dhara-card {{
            border: 1px solid var(--border);
            border-radius: 14px;
            background: linear-gradient(180deg, rgba(17,28,51,0.85), rgba(15,23,42,0.92));
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            height: 100%;
        }}

        .dhara-card h4 {{
            margin: 0 0 8px 0;
            color: var(--text);
            font-size: 1.1rem;
            font-weight: 600;
        }}

        .dhara-card p {{
            margin: 0;
            color: var(--muted);
            line-height: 1.5;
            font-size: 0.95rem;
        }}

        .dhara-step {{
            display: flex;
            gap: 16px;
            align-items: flex-start;
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: rgba(15,23,42,0.75);
            height: 100%;
        }}

        .dhara-step-num {{
            min-width: 32px;
            height: 32px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: {THEME['brand_bg_alpha']};
            color: var(--brand);
            font-weight: 700;
            font-size: 1rem;
        }}

        .dhara-muted {{
            color: var(--muted);
        }}

        /* Streamlit Buttons */
        .stButton>button {{
            border-radius: 8px;
            font-weight: 600;
            background-color: var(--brandDark);
            color: #ffffff;
            border: none;
            padding: 0.6rem 1.2rem;
            transition: all 0.2s ease-in-out;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }}
        .stButton>button:hover {{
            background-color: var(--brand);
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
        }}
        
        .stButton>button:active {{
            transform: translateY(0);
        }}

        /* Secondary Buttons */
        .stButton>button[kind="secondary"] {{
            background-color: rgba(30, 41, 59, 0.5);
            color: var(--text);
            border: 1px solid var(--border);
            box-shadow: none;
        }}

        .stButton>button[kind="secondary"]:hover {{
            background-color: rgba(30, 41, 59, 0.8);
            border-color: var(--brand);
            color: var(--brand);
        }}
        
        /* Metric Styling - clearer hierarchy */
        div[data-testid="stMetric"] {{
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem 1.25rem;
        }}
        div[data-testid="stMetricValue"] {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text);
        }}
        div[data-testid="stMetricLabel"] {{
            font-size: 0.85rem;
            color: var(--muted);
            font-weight: 500;
        }}

        div[data-testid="stMetricDelta"] svg {{
            fill: currentColor;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: #080d16;
            border-right: 1px solid var(--border);
        }}

        section[data-testid="stSidebar"] .css-1d391kg, 
        section[data-testid="stSidebar"] .css-1v3fvcr {{
            font-weight: 500;
            color: var(--text);
        }}
        
        /* Sidebar Toggle */
        button[kind="header"] {{
            color: var(--muted) !important;
        }}
        button[kind="header"]:hover {{
            color: var(--brand) !important;
        }}

        /* Headers */
        h1, h2, h3 {{
            color: var(--text);
            font-weight: 700;
            letter-spacing: -0.02em;
        }}

        /* Messages / Alerts - clearer visual distinction */
        div[data-baseweb="notification"]:has([fill="#22c55e"]) {{
            background: rgba(34, 197, 94, 0.12) !important;
            border: 1px solid rgba(34, 197, 94, 0.35) !important;
        }}
        div[data-baseweb="notification"]:has([fill="#f87171"]) {{
            background: rgba(248, 113, 113, 0.12) !important;
            border: 1px solid rgba(248, 113, 113, 0.35) !important;
        }}
        div[data-baseweb="notification"][kind="positive"], div[data-baseweb="notification"][data-kind="positive"] {{
            background: rgba(34, 197, 94, 0.15) !important;
            border: 1px solid rgba(34, 197, 94, 0.4) !important;
            border-radius: 10px !important;
            color: #86efac !important;
        }}
        div[data-baseweb="notification"][kind="negative"] {{
            background: rgba(248, 113, 113, 0.15) !important;
            border: 1px solid rgba(248, 113, 113, 0.4) !important;
            border-radius: 10px !important;
            color: #fca5a5 !important;
        }}
        div[data-baseweb="notification"][kind="warning"] {{
            background: rgba(251, 191, 36, 0.15) !important;
            border: 1px solid rgba(251, 191, 36, 0.4) !important;
            border-radius: 10px !important;
            color: #fde047 !important;
        }}
        div[data-baseweb="notification"][kind="info"] {{
            background: rgba(96, 165, 250, 0.12) !important;
            border: 1px solid rgba(96, 165, 250, 0.35) !important;
            border-radius: 10px !important;
            color: #93c5fd !important;
        }}
        .stAlert > div {{
            border-radius: 10px;
            border: 1px solid var(--border);
            background: rgba(15,23,42,0.9);
            color: var(--text);
        }}
        
        div[data-testid="stToast"] {{
            background-color: rgba(15,23,42,0.95) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            color: var(--text) !important;
        }}

        /* Tables */
        .stTable thead tr th {{
            background-color: rgba(30, 41, 59, 0.8) !important;
            color: var(--text) !important;
            font-weight: 600;
            border-bottom: 1px solid var(--border) !important;
        }}

        .stTable tbody tr:nth-child(even) {{
            background-color: rgba(30, 41, 59, 0.3);
        }}
        
        .stTable tbody tr:hover {{
            background-color: rgba(30, 41, 59, 0.6);
        }}

        /* Inputs */
        input, textarea, select {{
            border-radius: 8px !important;
            background: rgba(15,23,42,0.6) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            transition: border-color 0.2s !important;
        }}
        
        input:focus, textarea:focus, select:focus {{
            border-color: var(--brand) !important;
            box-shadow: 0 0 0 1px var(--brand) !important;
        }}

        /* Input placeholders */
        input::placeholder, textarea::placeholder {{
            color: rgba(148,163,184,0.5) !important;
        }}

        /* Select / dropdown menu panels */
        div[role="listbox"] {{
            background: rgba(15,23,42,0.98) !important;
            border: 1px solid var(--border) !important;
        }}
        
        /* StNumberInput buttons */
        div[data-testid="stNumberInput"] button {{
            background: transparent;
            color: var(--muted);
            border-color: var(--border);
        }}
        div[data-testid="stNumberInput"] button:hover {{
            color: var(--brand);
            border-color: var(--brand);
        }}

        /* Radio / Checkbox labels */
        label {{
            font-weight: 500;
            color: var(--text) !important;
        }}
        
        /* Checkbox checkmark */
        .stCheckbox input:checked + div {{
            background-color: var(--brand) !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 20px;
            border-bottom: 1px solid var(--border);
        }}
        
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            color: var(--muted);
            font-weight: 500;
        }}
        
        .stTabs [data-baseweb="tab"]:hover {{
            color: var(--text);
            background: transparent;
        }}
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            color: var(--brand);
            border-bottom: 2px solid var(--brand);
        }}

        /* Expanders */
        .streamlit-expanderHeader {{
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            background: rgba(15,23,42,0.5) !important;
            color: var(--text) !important;
        }}
        
        .streamlit-expanderContent {{
            border: 1px solid var(--border);
            border-top: none;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            background: rgba(15,23,42,0.3);
            padding: 16px !important;
        }}
        
        details {{
            border: none !important;
            background: transparent !important;
        }}

        /* Dataframes */
        div[data-testid="stDataFrame"] {{
            background: rgba(15,23,42,0.4) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            overflow: hidden;
        }}
        div[data-testid="stDataFrame"] * {{
            color: var(--text) !important;
        }}
        
        /* Progress bars */
        .stProgress > div > div > div > div {{
            background-color: var(--brand) !important;
        }}

        /* Plotly charts background */
        .js-plotly-plot .plotly .main-svg {{
            background: transparent !important;
        }}

        /* Make plot area blend in dark */
        .js-plotly-plot .plotly .bg {{
            fill: rgba(15,23,42,0.0) !important;
        }}

        /* Option menu adjustments */
        div[data-testid="stHorizontalBlock"] [data-testid="stMarkdownContainer"] > div.dhara-nav + div {{
            margin-top: 0.75rem;
        }}
        
        /* Sliders */
        div[data-testid="stSlider"] > div {{
            /* Slider track */
        }}
        </style>
    """, unsafe_allow_html=True)
