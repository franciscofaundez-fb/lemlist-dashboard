"""
Dashboard Lemlist — Clusters SO
"""
import streamlit as st
import plotly.graph_objects as go
import urllib.request, json, base64, re, time, csv, io
from datetime import datetime
from collections import defaultdict

# ── Config ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clusters SO — Lemlist",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    LEMLIST_KEY = st.secrets["LEMLIST_KEY"]
except Exception:
    LEMLIST_KEY = "de60d9240b77ed27390a25893a847145"

TAGS = ["SO005", "SO007", "SO009"]

STATE_LABELS = {
    "emailsOpened":  "Abrió",
    "emailsReplied": "Respondió",
    "emailsSent":    "Enviado",
    "emailsBounced": "Bounce",
    "emailsClicked": "Clickeó",
}
SCORE_MAP = {
    "emailsReplied": (100, "Alto",  "#22C55E"),
    "emailsClicked": (70,  "Medio", "#F59E0B"),
    "emailsOpened":  (40,  "Medio", "#F59E0B"),
    "emailsSent":    (10,  "Bajo",  "#6B7280"),
    "emailsBounced": (0,   "—",     "#EF4444"),
}

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, body { font-family: 'Inter', sans-serif !important; }

[data-testid="stAppViewContainer"] { background: #0D1117; }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { display: none !important; }

/* ── Sidebar toggle button ── */
[data-testid="collapsedControl"] {
  background: #21262D !important;
  border: 1px solid #30363D !important;
  border-radius: 6px !important;
  width: 28px !important; height: 28px !important;
  overflow: hidden !important;
  position: relative !important;
}
[data-testid="collapsedControl"]:hover {
  background: #30363D !important; border-color: #58A6FF !important;
}
[data-testid="collapsedControl"] * {
  opacity: 0 !important;
  font-size: 0 !important;
}
[data-testid="collapsedControl"]::after {
  content: "›";
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  font-size: 18px !important; font-weight: 700 !important;
  color: #8B949E !important; font-family: Inter, sans-serif !important;
  line-height: 1; opacity: 1 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: #161B22;
  border-right: 1px solid #21262D;
}
[data-testid="stSidebar"] * { color: #E6EDF3 !important; }
[data-testid="stSidebar"] label {
  color: #8B949E !important; font-size: 0.7rem !important;
  text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600;
}

/* Multiselect pills más pequeñas y softs */
[data-testid="stSidebar"] [data-baseweb="tag"] {
  background: #21262D !important;
  border: 1px solid #30363D !important;
  border-radius: 4px !important;
  padding: 1px 8px !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] span { color: #58A6FF !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] [role="presentation"] { color: #8B949E !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: #21262D !important; border: 1px solid #30363D !important;
  border-radius: 6px !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
  background: #21262D !important; border: 1px solid #30363D !important;
}

/* Botón actualizar */
[data-testid="stSidebar"] .stButton > button {
  background: #21262D !important; color: #E6EDF3 !important;
  border: 1px solid #30363D !important; border-radius: 6px !important;
  font-weight: 500 !important; font-size: 0.8rem !important;
  padding: 6px 14px !important; width: 100% !important;
  transition: all 0.15s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: #30363D !important; border-color: #58A6FF !important;
  color: #58A6FF !important;
}

/* ── KPI cards ── */
.kpi-card {
  background: #161B22; border: 1px solid #21262D; border-radius: 10px;
  padding: 18px 20px; position: relative; overflow: hidden;
}
.kpi-card::after {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, #1F6FEB 0%, #238636 100%);
}
.kpi-num   { font-size: 2.2rem; font-weight: 800; color: #E6EDF3; line-height: 1; letter-spacing: -0.04em; }
.kpi-label { font-size: 0.68rem; color: #8B949E; margin-top: 7px; text-transform: uppercase; letter-spacing: 0.1em; }
.kpi-sub   { font-size: 0.78rem; color: #58A6FF; font-weight: 500; margin-top: 6px; }

/* ── Cluster cards ── */
.cluster-card {
  background: #161B22; border: 1px solid #21262D; border-radius: 10px; padding: 20px;
}
.cluster-tag  { font-size: 1.35rem; font-weight: 800; color: #E6EDF3; letter-spacing: -0.03em; }
.cluster-name { font-size: 0.73rem; color: #8B949E; margin: 5px 0 14px; line-height: 1.4; }
.stat-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 0; border-bottom: 1px solid #21262D;
}
.stat-row:last-of-type { border-bottom: none; }
.stat-key { font-size: 0.78rem; color: #8B949E; }
.stat-val { font-size: 0.88rem; font-weight: 700; color: #E6EDF3; }
.bar-wrap  { background: #21262D; border-radius: 4px; height: 4px; width: 100%; margin-top: 10px; }
.bar-fill  { height: 4px; border-radius: 4px; }

/* ── Badges ── */
.badge { display: inline-block; padding: 1px 7px; border-radius: 4px; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.06em; }
.badge-active  { background: rgba(34,197,94,0.12);  color: #22C55E; border: 1px solid rgba(34,197,94,0.2); }
.badge-paused  { background: rgba(245,158,11,0.12); color: #F59E0B; border: 1px solid rgba(245,158,11,0.2); }
.badge-draft   { background: rgba(107,114,128,0.12);color: #6B7280; border: 1px solid rgba(107,114,128,0.2); }

/* ── Sección títulos ── */
.sec-title {
  font-size: 0.68rem; color: #8B949E; text-transform: uppercase;
  letter-spacing: 0.12em; font-weight: 600; margin-bottom: 10px;
}

/* ── Search card ── */
.lead-card {
  background: #161B22; border: 1px solid #21262D; border-radius: 10px;
  padding: 16px 20px; margin-bottom: 10px;
}
.lead-card:hover { border-color: #30363D; }
.lead-name   { font-size: 0.95rem; font-weight: 700; color: #E6EDF3; }
.lead-email  { font-size: 0.78rem; color: #8B949E; margin-top: 2px; }
.score-pill  { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; }

/* ── Reply cards ── */
.reply-card {
  background: #0D1117; border: 1px solid #21262D; border-radius: 8px;
  padding: 14px 16px; margin-bottom: 8px; position: relative;
}
.reply-card.your-turn { border-left: 3px solid #238636; }
.reply-name    { font-size: 0.88rem; font-weight: 700; color: #E6EDF3; }
.reply-company { font-size: 0.73rem; color: #8B949E; margin-top: 1px; }
.reply-preview {
  font-size: 0.8rem; color: #C9D1D9; margin-top: 10px; line-height: 1.5;
  background: #161B22; border-radius: 6px; padding: 8px 12px;
  border-left: 2px solid #30363D;
}
.ai-score-bar { background: #21262D; border-radius: 4px; height: 4px; margin-top: 8px; }
.your-turn-badge {
  display: inline-block; padding: 1px 8px; border-radius: 4px;
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.05em;
  background: rgba(34,197,94,0.12); color: #22C55E;
  border: 1px solid rgba(34,197,94,0.25);
}

/* ── Expander styling ── */
[data-testid="stExpander"] {
  background: #161B22 !important; border: 1px solid #21262D !important;
  border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
  color: #E6EDF3 !important; font-weight: 600 !important;
}

/* ── Tabla ── */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
  background: #21262D !important; color: #E6EDF3 !important;
  border: 1px solid #30363D !important; border-radius: 6px !important;
  font-size: 0.78rem !important; font-weight: 500 !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: #8B949E !important;
}
</style>
""", unsafe_allow_html=True)

# ── Lemlist API ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_replies():
    auth = base64.b64encode(f":{LEMLIST_KEY}".encode()).decode()
    hdr  = {"Authorization": f"Basic {auth}", "User-Agent": "Mozilla/5.0"}
    req  = urllib.request.Request(
        "https://api.lemlist.com/api/activities?type=emailsReplied&limit=100", headers=hdr)
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        return data if isinstance(data, list) else data.get("data", [])
    except:
        return []

@st.cache_data(ttl=300, show_spinner=False)
def fetch_lemlist_data():
    auth = base64.b64encode(f":{LEMLIST_KEY}".encode()).decode()
    hdr  = {"Authorization": f"Basic {auth}", "User-Agent": "Mozilla/5.0"}

    def lm(path):
        req = urllib.request.Request(f"https://api.lemlist.com/api{path}", headers=hdr)
        try:
            return json.loads(urllib.request.urlopen(req, timeout=20).read())
        except:
            return None

    all_camps = lm("/campaigns") or []
    clusters = {}
    for c in all_camps:
        m = re.search(r"(SO\d{3,})", c.get("name", ""))
        if m and m.group(1) in TAGS:
            clusters[m.group(1)] = {"id": c["_id"], "name": c["name"], "status": c.get("status", "")}

    result = {}
    for tag in TAGS:
        if tag not in clusters:
            continue
        camp = clusters[tag]
        time.sleep(0.3)
        raw = lm(f"/campaigns/{camp['id']}/leads?limit=500&offset=0") or []
        seen = set(); leads = []
        for l in raw:
            if l["_id"] not in seen:
                seen.add(l["_id"]); leads.append(l)

        states = defaultdict(int)
        for l in leads:
            states[l.get("state", "unknown")] += 1

        total = len(leads)
        bounced = states.get("emailsBounced", 0)
        opened  = states.get("emailsOpened", 0)
        replied = states.get("emailsReplied", 0)
        sent    = states.get("emailsSent", 0)
        clicked = states.get("emailsClicked", 0)
        deliverable = total - bounced
        def pct(n, d): return round(n / d * 100, 1) if d else 0

        result[tag] = {
            "name": camp["name"], "status": camp["status"],
            "total": total, "bounced": bounced, "deliverable": deliverable,
            "opened": opened, "replied": replied, "sent": sent, "clicked": clicked,
            "or_deliverable": pct(opened, deliverable),
            "rr":             pct(replied, deliverable),
            "leads": leads,
        }
    return result, datetime.now().strftime("%d/%m/%Y %H:%M")


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo MP
    st.markdown("""
    <div style="padding: 4px 0 20px">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="background:#009EE3;border-radius:8px;width:36px;height:36px;
                    display:flex;align-items:center;justify-content:center;flex-shrink:0">
          <span style="color:white;font-weight:900;font-size:0.85rem;letter-spacing:-0.03em">MP</span>
        </div>
        <div>
          <div style="font-size:0.88rem;font-weight:700;color:#E6EDF3;">Lemlist</div>
          <div style="font-size:0.68rem;color:#8B949E;">Clusters SO · Outbound</div>
        </div>
      </div>
    </div>
    <hr style="border-color:#21262D;margin:0 0 16px">
    """, unsafe_allow_html=True)

    if st.button("↻  Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    tags_sel   = st.multiselect("Clusters", options=TAGS, default=TAGS, label_visibility="visible")
    estado_sel = st.selectbox("Estado", ["Todos"] + list(STATE_LABELS.keys()),
                              format_func=lambda x: "Todos" if x == "Todos" else STATE_LABELS[x])

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    buscar = st.text_input("Buscar lead", placeholder="Nombre, email, empresa...")

    st.markdown("""
    <hr style="border-color:#21262D;margin:16px 0 12px">
    <div style="font-size:0.67rem;color:#484F58;line-height:1.7">
      Cache: 5 min · Lemlist API
    </div>
    """, unsafe_allow_html=True)


# ── Cargar datos ─────────────────────────────────────────────────────────────
with st.spinner(""):
    data, ultima_act = fetch_lemlist_data()

if not data:
    st.error("No se pudo conectar a Lemlist.")
    st.stop()

data_fil = {k: v for k, v in data.items() if k in tags_sel}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:22px">
  <div>
    <div style="font-size:1.5rem;font-weight:800;color:#E6EDF3;letter-spacing:-0.04em">Clusters SO</div>
    <div style="font-size:0.78rem;color:#8B949E;margin-top:3px">
      Seguimiento de campañas outbound · {len(tags_sel)} clusters
    </div>
  </div>
  <div style="font-size:0.72rem;color:#484F58">Actualizado {ultima_act}</div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_leads       = sum(v["total"] for v in data_fil.values())
total_deliverable = sum(v["deliverable"] for v in data_fil.values())
total_opened      = sum(v["opened"] for v in data_fil.values())
total_replied     = sum(v["replied"] for v in data_fil.values())
or_g = round(total_opened / total_deliverable * 100, 1) if total_deliverable else 0
rr_g = round(total_replied / total_deliverable * 100, 1) if total_deliverable else 0

for col, (val, label, sub) in zip(st.columns(5), [
    (f"{total_leads:,}",       "Total leads",   f"{total_leads - total_deliverable} bounces"),
    (f"{total_deliverable:,}", "Entregables",   f"{round(total_deliverable/total_leads*100,1) if total_leads else 0}% del total"),
    (f"{total_opened:,}",      "Abrieron",      f"OR {or_g}% sobre entregables"),
    (f"{total_replied:,}",     "Respondieron",  f"RR {rr_g}% sobre entregables"),
    (f"{len(data_fil)}",       "Clusters",      " · ".join(data_fil.keys())),
]):
    with col:
        st.markdown(f"""<div class="kpi-card">
          <div class="kpi-num">{val}</div>
          <div class="kpi-label">{label}</div>
          <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# ── Gráficos ──────────────────────────────────────────────────────────────────
g1, g2 = st.columns(2)
tags_list = list(data_fil.keys())

FONT = "Inter, sans-serif"
BG   = "#161B22"
HOVER = dict(bgcolor="#1C2128", bordercolor="#30363D", font=dict(color="#E6EDF3", size=12, family=FONT))

with g1:
    st.markdown('<div class="sec-title">Leads por cluster</div>', unsafe_allow_html=True)
    fig = go.Figure()
    layers = [
        ("sent",    "Enviados",    "#1F6FEB", 0.9),
        ("opened",  "Abrieron",   "#238636", 1.0),
        ("replied", "Respondió",  "#B45309", 1.0),
        ("bounced", "Bounce",     "#4A1010", 1.0),
    ]
    for key, name, color, opacity in layers:
        vals = [data_fil[t][key] for t in tags_list]
        fig.add_trace(go.Bar(
            name=name, x=tags_list, y=vals,
            marker=dict(color=color, opacity=opacity, line=dict(width=0)),
            hovertemplate=f"<b>%{{x}}</b><br>{name}: <b>%{{y}}</b><extra></extra>",
        ))
    # Anotación con total encima de cada barra
    for t in tags_list:
        total = data_fil[t]["total"]
        fig.add_annotation(
            x=t, y=total, text=f"<b>{total}</b>",
            showarrow=False, yanchor="bottom", yshift=6,
            font=dict(size=12, color="#C9D1D9", family=FONT),
        )
    fig.update_layout(
        plot_bgcolor=BG, paper_bgcolor=BG,
        font=dict(family=FONT, size=11),
        margin=dict(l=40, r=16, t=32, b=64), height=290,
        barmode="stack", bargap=0.45,
        showlegend=True,
        legend=dict(
            orientation="h", y=-0.28, x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=10, color="#8B949E"),
            itemsizing="constant", traceorder="normal",
        ),
        hoverlabel=HOVER,
        xaxis=dict(
            showgrid=False, zeroline=False, showline=False,
            tickfont=dict(color="#C9D1D9", size=13, family=FONT),
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#1E252E", zeroline=False, showline=False,
            tickfont=dict(color="#8B949E", size=10),
            tickformat=",d",
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with g2:
    st.markdown('<div class="sec-title">Open Rate & Reply Rate</div>', unsafe_allow_html=True)
    fig2 = go.Figure()

    # Fondo de referencia (100%)
    for t in tags_list:
        fig2.add_shape(type="rect",
            x0=0, x1=100, y0=tags_list.index(t)-0.4, y1=tags_list.index(t)+0.4,
            fillcolor="#1E252E", line=dict(width=0), layer="below",
        )

    for vals, name, color, offset in [
        ([data_fil[t]["or_deliverable"] for t in tags_list], "Open Rate",  "#1F6FEB", -0.22),
        ([data_fil[t]["rr"]             for t in tags_list], "Reply Rate", "#238636",  0.22),
    ]:
        fig2.add_trace(go.Bar(
            name=name, x=vals, y=tags_list, orientation="h",
            marker=dict(color=color, line=dict(width=0), cornerradius=3),
            hovertemplate=f"<b>%{{y}}</b><br>{name}: <b>%{{x}}%</b><extra></extra>",
            width=0.38,
            offset=offset - 0.19,
        ))
        # Anotación con % al final de cada barra
        for i, (t, v) in enumerate(zip(tags_list, vals)):
            fig2.add_annotation(
                x=v, y=i + (offset * 2),
                text=f"<b>{v}%</b>",
                showarrow=False, xanchor="left", xshift=6,
                font=dict(size=11, color=color, family=FONT),
            )

    fig2.update_layout(
        plot_bgcolor=BG, paper_bgcolor=BG,
        font=dict(family=FONT, size=11),
        margin=dict(l=16, r=64, t=32, b=64), height=290,
        barmode="overlay",
        showlegend=True,
        legend=dict(
            orientation="h", y=-0.28, x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=10, color="#8B949E"),
            itemsizing="constant",
        ),
        hoverlabel=HOVER,
        xaxis=dict(
            showgrid=False, zeroline=False, showline=False,
            range=[0, 108], showticklabels=False,
        ),
        yaxis=dict(
            showgrid=False, showline=False,
            tickfont=dict(color="#C9D1D9", size=13, family=FONT),
            categoryorder="array", categoryarray=list(reversed(tags_list)),
        ),
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# ── Cluster cards ─────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">Detalle por cluster</div>', unsafe_allow_html=True)
BADGE = {"active": "badge-active", "paused": "badge-paused", "draft": "badge-draft"}

for col, (tag, d) in zip(st.columns(len(data_fil)), data_fil.items()):
    bc = BADGE.get(d["status"], "badge-draft")
    with col:
        st.markdown(f"""<div class="cluster-card">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span class="cluster-tag">{tag}</span>
            <span class="badge {bc}">{d['status'].upper()}</span>
          </div>
          <div class="cluster-name">{d['name'][:55]}</div>
          <div class="stat-row"><span class="stat-key">Total leads</span><span class="stat-val">{d['total']}</span></div>
          <div class="stat-row"><span class="stat-key">Entregables</span><span class="stat-val">{d['deliverable']}</span></div>
          <div class="stat-row"><span class="stat-key">Abrieron</span><span class="stat-val">{d['opened']}</span></div>
          <div class="stat-row"><span class="stat-key">Respondieron</span><span class="stat-val">{d['replied']}</span></div>
          <div class="stat-row"><span class="stat-key">Bounces</span><span class="stat-val">{d['bounced']}</span></div>
          <div style="margin-top:14px">
            <div style="display:flex;justify-content:space-between;margin-bottom:5px">
              <span style="font-size:0.68rem;color:#8B949E">Open Rate</span>
              <span style="font-size:0.75rem;font-weight:700;color:#1F6FEB">{d['or_deliverable']}%</span>
            </div>
            <div class="bar-wrap"><div class="bar-fill" style="width:{min(d['or_deliverable'],100)}%;background:#1F6FEB"></div></div>
          </div>
          <div style="margin-top:8px">
            <div style="display:flex;justify-content:space-between;margin-bottom:5px">
              <span style="font-size:0.68rem;color:#8B949E">Reply Rate</span>
              <span style="font-size:0.75rem;font-weight:700;color:#238636">{d['rr']}%</span>
            </div>
            <div class="bar-wrap"><div class="bar-fill" style="width:{min(d['rr'],100)}%;background:#238636"></div></div>
          </div>
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# ── Inbox: leads que respondieron ────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.markdown('<div class="sec-title">Inbox — Respuestas recibidas</div>', unsafe_allow_html=True)

replies_raw = fetch_replies()

# Agrupar por campaña (solo clusters SO)
replies_by_tag = defaultdict(list)
for r in replies_raw:
    camp = r.get("campaignName", "")
    m = re.search(r"(SO\d{3,})", camp)
    if m and m.group(1) in tags_sel:
        replies_by_tag[m.group(1)].append(r)

if not replies_by_tag:
    st.markdown('<div style="color:#8B949E;font-size:0.85rem;padding:12px 0">No hay respuestas registradas aún.</div>',
                unsafe_allow_html=True)
else:
    for tag in tags_sel:
        replies = replies_by_tag.get(tag, [])
        if not replies:
            continue
        your_turn = sum(1 for r in replies if not r.get("bot", False))
        label = f"{tag} · {len(replies)} respuesta{'s' if len(replies)>1 else ''}"
        if your_turn:
            label += f"  ·  {your_turn} esperando respuesta"

        with st.expander(label, expanded=False):
            for r in sorted(replies, key=lambda x: x.get("createdAt",""), reverse=True):
                nombre  = f"{r.get('leadFirstName','')} {r.get('leadLastName','')}".strip() or r.get("leadEmail","")
                empresa = r.get("leadCompanyName", "")
                email   = r.get("leadEmail", "")
                preview = r.get("messagePreview", "").strip()
                subject = r.get("subject", "")
                fecha   = r.get("createdAt", "")[:10] if r.get("createdAt") else ""
                ai_raw  = r.get("aiLeadInterestScore", 0) or 0
                ai_pct  = round(ai_raw * 100)
                is_turn = not r.get("bot", False)

                if ai_raw >= 0.7:
                    ai_color, ai_label = "#22C55E", "Muy interesado"
                elif ai_raw >= 0.4:
                    ai_color, ai_label = "#F59E0B", "Interesado"
                else:
                    ai_color, ai_label = "#6B7280", "Poco interesado"

                turn_badge = '<span class="your-turn-badge">Tu turno</span>' if is_turn else ""
                card_class = "reply-card your-turn" if is_turn else "reply-card"

                st.markdown(f"""
                <div class="{card_class}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div class="reply-name">{nombre}</div>
                      <div class="reply-company">{empresa}{' · ' + email if empresa else email}</div>
                    </div>
                    <div style="text-align:right;display:flex;flex-direction:column;align-items:flex-end;gap:4px">
                      {turn_badge}
                      <span style="font-size:0.68rem;color:#484F58">{fecha}</span>
                    </div>
                  </div>
                  {f'<div style="font-size:0.7rem;color:#8B949E;margin-top:8px">Asunto: <span style="color:#C9D1D9">{subject}</span></div>' if subject else ''}
                  {f'<div class="reply-preview">{preview}...</div>' if preview else ''}
                  <div style="margin-top:10px;display:flex;align-items:center;gap:10px">
                    <div style="flex:1">
                      <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                        <span style="font-size:0.67rem;color:#8B949E">Interés IA</span>
                        <span style="font-size:0.67rem;font-weight:700;color:{ai_color}">{ai_label} · {ai_pct}%</span>
                      </div>
                      <div class="ai-score-bar">
                        <div style="height:4px;border-radius:4px;width:{ai_pct}%;background:{ai_color}"></div>
                      </div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# ── Buscador de leads ─────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">Buscar lead</div>', unsafe_allow_html=True)

# Armar lista completa
rows = []
for tag, d in data_fil.items():
    for l in d["leads"]:
        state = l.get("state", "")
        score_val, score_label, score_color = SCORE_MAP.get(state, (0, "—", "#6B7280"))
        rows.append({
            "Cluster":    tag,
            "Secuencia":  d["name"],
            "Nombre":     f"{l.get('firstName', '')} {l.get('lastName', '')}".strip(),
            "Email":      l.get("email", ""),
            "Empresa":    l.get("companyName", ""),
            "Estado":     state,
            "estado_label": STATE_LABELS.get(state, state),
            "score":      score_val,
            "score_label": score_label,
            "score_color": score_color,
            "LinkedIn":   l.get("linkedinUrl", ""),
        })

# Aplicar filtros
filtered = rows[:]
if estado_sel != "Todos":
    filtered = [r for r in filtered if r["Estado"] == estado_sel]
if buscar and len(buscar) >= 2:
    q = buscar.lower()
    filtered = [r for r in filtered if
                q in r["Nombre"].lower() or q in r["Email"].lower() or q in r["Empresa"].lower()]

# Si hay búsqueda activa, mostrar cards detalladas
if buscar and len(buscar) >= 2:
    if not filtered:
        st.markdown('<div style="color:#8B949E;font-size:0.85rem;padding:20px 0">No se encontraron leads.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='font-size:0.75rem;color:#8B949E;margin-bottom:12px'>{len(filtered)} resultado{'s' if len(filtered)>1 else ''}</div>",
                    unsafe_allow_html=True)
        for r in filtered[:10]:
            li_btn = f'<a href="{r["LinkedIn"]}" target="_blank" style="font-size:0.72rem;color:#58A6FF;text-decoration:none">Ver LinkedIn →</a>' if r["LinkedIn"] else ""
            st.markdown(f"""
            <div class="lead-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>
                  <div class="lead-name">{r['Nombre'] or '(sin nombre)'}</div>
                  <div class="lead-email">{r['Email']}</div>
                </div>
                <div style="text-align:right">
                  <span class="score-pill" style="background:{r['score_color']}22;color:{r['score_color']};border:1px solid {r['score_color']}44">
                    Score {r['score']}</span>
                  <div style="font-size:0.68rem;color:#8B949E;margin-top:4px">{r['score_label']} engagement</div>
                </div>
              </div>
              <div style="display:flex;gap:20px;margin-top:12px;flex-wrap:wrap">
                <div style="font-size:0.75rem"><span style="color:#8B949E">Empresa </span><span style="color:#E6EDF3;font-weight:500">{r['Empresa'] or '—'}</span></div>
                <div style="font-size:0.75rem"><span style="color:#8B949E">Cluster </span><span style="color:#58A6FF;font-weight:600">{r['Cluster']}</span></div>
                <div style="font-size:0.75rem"><span style="color:#8B949E">Estado </span><span style="color:#E6EDF3;font-weight:500">{r['estado_label']}</span></div>
                <div style="font-size:0.75rem"><span style="color:#8B949E">Secuencia </span><span style="color:#8B949E">{r['Secuencia'][:40]}</span></div>
              </div>
              {f'<div style="margin-top:8px">{li_btn}</div>' if li_btn else ''}
            </div>""", unsafe_allow_html=True)
else:
    # Vista tabla completa
    table_rows = [
        {"Cluster": r["Cluster"], "Nombre": r["Nombre"], "Email": r["Email"],
         "Empresa": r["Empresa"], "Estado": r["estado_label"], "Score": r["score_label"],
         "LinkedIn": r["LinkedIn"]}
        for r in filtered
    ]
    st.markdown(f"<div style='font-size:0.75rem;color:#8B949E;margin-bottom:8px'>{len(table_rows)} leads</div>",
                unsafe_allow_html=True)
    st.dataframe(
        table_rows, use_container_width=True, hide_index=True, height=360,
        column_config={
            "Cluster":  st.column_config.TextColumn("Cluster", width=80),
            "LinkedIn": st.column_config.LinkColumn("LinkedIn", display_text="Ver"),
            "Score":    st.column_config.TextColumn("Score", width=80),
        },
    )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["Cluster","Nombre","Email","Empresa","Estado","Score","LinkedIn"])
    writer.writeheader(); writer.writerows(table_rows)
    st.download_button("Descargar CSV", buf.getvalue().encode("utf-8"),
                       f"leads_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
