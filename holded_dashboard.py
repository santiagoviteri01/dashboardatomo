import streamlit as st
import pandas as pd
import re
import difflib
import mysql.connector
from datetime import datetime
from datetime import date
import altair as alt
import requests
st.set_page_config(page_title="Dashboard de Márgenes", layout="wide")
st.title("📊 Dashboard Interactivo Holded-Financiero")
API_KEY = "fafbb8191b37e6b696f192e70b4a198c"
HEADERS = {
    "accept": "application/json",
    "key": API_KEY
}
from datetime import datetime

BASE_INV = "https://api.holded.com/api/invoicing/v1"
BASE_ACC = "https://api.holded.com/api/accounting/v1"
HEADERS = {"accept": "application/json", "key": API_KEY}

@st.cache_data(ttl=60)
def list_documents(doc_type: str, start_dt: datetime, end_dt: datetime, page_size=200):
    """Lista documentos de ventas/compras (usa starttmp/endtmp)."""
    url = f"{BASE_INV}/documents/{doc_type}"
    params = {
        "starttmp": int(start_dt.timestamp()),
        "endtmp": int(end_dt.timestamp()),
        "sort": "created-asc",
        "limit": page_size
    }
    # Paginación best-effort: algunos tenants exponen 'page'/'offset'
    out = []
    page = 1
    while True:
        params_try = params.copy()
        params_try["page"] = page
        r = requests.get(url, headers=HEADERS, params=params_try, timeout=30)
        if r.status_code != 200:
            # sin paginación explícita: devolvemos lo que haya en la primera llamada
            if page == 1:
                try:
                    data = r.json()
                    return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame()
                except Exception:
                    return pd.DataFrame()
            break
        data = r.json()
        if not data:
            break
        out.extend(data)
        if len(data) < page_size:
            break
        page += 1
    return pd.DataFrame(out)

@st.cache_data(ttl=60)
def get_document_detail(doc_type: str, doc_id: str):
    """Detalle de documento (para leer líneas y cuentas, si están disponibles)."""
    url = f"{BASE_INV}/documents/{doc_type}/{doc_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else None

@st.cache_data(ttl=60)
def list_chart_of_accounts():
    """Plan de cuentas de Holded (si tienes contabilidad activa)."""
    url = f"{BASE_ACC}/chartofaccounts"
    r = requests.get(url, headers=HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else []

@st.cache_data(ttl=60)
def list_daily_ledger(start_dt: datetime, end_dt: datetime, page_size=500):
    """Libro diario (más fiel). Intentamos filtrar por fecha si el endpoint lo soporta."""
    url = f"{BASE_ACC}/dailyledger"
    out = []
    page = 1
    # Intentos de query params comunes; si no funcionan, traemos páginas y filtramos localmente
    base_params = {"limit": page_size}
    date_params_candidates = [
        {"start": start_dt.strftime("%Y-%m-%d"), "end": end_dt.strftime("%Y-%m-%d")},
        {"dateFrom": start_dt.strftime("%Y-%m-%d"), "dateTo": end_dt.strftime("%Y-%m-%d")},
        {"from": start_dt.strftime("%Y-%m-%d"), "to": end_dt.strftime("%Y-%m-%d")},
    ]
    for candidate in date_params_candidates:
        params = base_params | candidate | {"page": page}
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if r.status_code == 200:
            # asumimos que el servidor aceptó el filtro de fechas
            while True:
                data = r.json()
                if not data:
                    break
                out.extend(data)
                if len(data) < page_size:
                    break
                page += 1
                params["page"] = page
                r = requests.get(url, headers=HEADERS, params=params, timeout=30)
                if r.status_code != 200:
                    break
            if out:
                break

    if not out:
        # fallback sin filtros: paginamos y luego filtramos por fecha localmente
        page = 1
        while True:
            r = requests.get(url, headers=HEADERS, params={"page": page, "limit": page_size}, timeout=30)
            if r.status_code != 200:
                break
            data = r.json()
            if not data:
                break
            out.extend(data)
            if len(data) < page_size:
                break
            page += 1
        # filtro local
        def to_dt(x):
            try:
                return pd.to_datetime(x)
            except Exception:
                return pd.NaT
        for d in out:
            if "date" in d:
                d["_date"] = to_dt(d["date"])
        out = [d for d in out if d.get("_date") is not pd.NaT and start_dt <= d["_date"] <= end_dt]

    return out  # lista de asientos

# ---- Clasificador P&L por código de cuenta (PGC ESP aproximado) -----------------
def classify_account(code: str, name: str = "") -> str:
    code = (code or "").strip()
    if code.startswith("60"):  # Compras
        return "Aprovisionamientos"
    if code.startswith("64"):
        return "Gastos de personal"
    if code.startswith(("62", "63", "65")):
        return "Otros gastos de explotación"
    if code.startswith("66"):
        return "Gastos financieros"
    if code.startswith(("76",)):
        return "Ingresos financieros"
    if code.startswith("768"):
        return "Diferencias de cambio"  # ingreso
    if code.startswith("668"):
        return "Diferencias de cambio"  # gasto
    if code.startswith(("70", "73", "75", "77")):
        return "Ingresos"
    return "Otros resultados"

# ---- Extractores de valores desde documentos/líneas -----------------------------
def safe_amount(d: dict):
    """Prefiere neto/importe sin impuestos si existe."""
    for k in ("subTotal", "subtotal", "untaxedAmount", "base", "amount", "total"):
        if k in d and isinstance(d[k], (int, float)):
            return float(d[k])
    # a veces 'total' llega en centavos o string
    if "total" in d:
        try:
            return float(d["total"])
        except Exception:
            pass
    return 0.0

def parse_purchase_lines(doc_json: dict):
    """Devuelve lista de (fecha, cuenta, importe) por línea; si no hay líneas, usa total del documento."""
    out = []
    if not doc_json:
        return out
    fecha = pd.to_datetime(doc_json.get("date"), unit="s", errors="coerce") if isinstance(doc_json.get("date"), (int, float)) else pd.to_datetime(doc_json.get("date"), errors="coerce")
    # posibles ubicaciones de líneas
    candidates = []
    for key in ("lines", "items", "concepts"):
        if isinstance(doc_json.get(key), list):
            candidates = doc_json[key]; break
    if candidates:
        for ln in candidates:
            amt = safe_amount(ln)
            # posibles campos de cuenta
            acct = ln.get("expenseAccountId") or ln.get("accountId") or ln.get("accountCode") or ln.get("expenseAccountCode") or ""
            acct_name = ln.get("accountName") or ""
            out.append((fecha, acct, acct_name, -abs(amt)))  # gasto negativo
    else:
        # sin líneas: llevamos todo a 'Otros gastos de explotación'
        amt = safe_amount(doc_json)
        out.append((fecha, "62XXX", "Gasto sin desglosar", -abs(amt)))
    return out

# ===================
# 🧩 TABS PRINCIPALES
# ===================
tab1, tab2, tab3 = st.tabs(["📈 Márgenes Comerciales", "🧪 Datos Plataforma (DB)", "📑 P&L Holded (API)"])

with tab1:
    HEADERS = {"accept": "application/json", "key": API_KEY}
    # =============================
    # 📦 FUNCIONES DE CARGA
    # =============================

    @st.cache_data(ttl=60)
    def cargar_documentos_holded(tipo, inicio, fin):
        url = f"https://api.holded.com/api/invoicing/v1/documents/{tipo}"
        params = {
            "starttmp": int(inicio.timestamp()),
            "endtmp": int(fin.timestamp()),
            "sort": "created-asc"
        }
        r = requests.get(url, headers=HEADERS, params=params)
        if r.status_code == 200:
            return pd.DataFrame(r.json())
        else:
            st.error(f"❌ Error {r.status_code}: {r.text[:300]}")
            return pd.DataFrame()
    
    # =============================
    # 📅 FILTROS DE FECHA (de mes-año a mes-año)
    # =============================
    st.sidebar.header("📅 Filtros de Fecha para Márgenes Comerciales")
    hoy = datetime.today()
    hace_1_ano = hoy.replace(year=hoy.year - 1)
    
    mes_inicio = st.sidebar.selectbox("Mes inicio", list(range(1, 13)), index=hoy.month - 2)
    año_inicio = st.sidebar.selectbox("Año inicio", list(range(hace_1_ano.year, hoy.year + 1)), index=1)
    
    mes_fin = st.sidebar.selectbox("Mes fin", list(range(1, 13)), index=hoy.month - 1)
    año_fin = st.sidebar.selectbox("Año fin", list(range(hace_1_ano.year, hoy.year + 1)), index=1)
    
    fecha_inicio = datetime(año_inicio, mes_inicio, 1)
    fecha_fin = pd.to_datetime(datetime(año_fin, mes_fin, 1) + pd.offsets.MonthEnd(1))
    
    if fecha_inicio > fecha_fin:
        st.sidebar.error("⚠️ La fecha de inicio no puede ser posterior a la fecha de fin.")
        st.stop()
    
    # =============================
    # 📥 CARGA DE DATOS
    # =============================
    st.sidebar.markdown("---")
    st.sidebar.info("Cargando ingresos y gastos desde Holded...")
    df_ingresos = cargar_documentos_holded("invoice", fecha_inicio, fecha_fin)
    df_gastos = cargar_documentos_holded("purchase", fecha_inicio, fecha_fin)
    
    if df_ingresos.empty and df_gastos.empty:
        st.warning("No se encontraron documentos en el rango seleccionado.")
        st.stop()
    
    # =============================
    # 🧮 PROCESAMIENTO DE MÁRGENES
    # =============================
    columnas_necesarias = ["cliente_final", "fecha", "tipo", "valor"]
    
    # Ingresos
    df_ingresos = df_ingresos.copy()
    df_ingresos["tipo"] = "ingreso"
    df_ingresos["valor"] = pd.to_numeric(df_ingresos.get("total"), errors="coerce")
    df_ingresos["cliente_final"] = df_ingresos.get("contactName", "Sin nombre")
    df_ingresos["fecha"] = pd.to_datetime(df_ingresos.get("date"), unit="s", errors="coerce")
    df_ingresos = df_ingresos[columnas_necesarias] if not df_ingresos.empty else pd.DataFrame(columns=columnas_necesarias)
    
    # Gastos
    df_gastos = df_gastos.copy()
    df_gastos["tipo"] = "gasto"
    df_gastos["valor"] = -pd.to_numeric(df_gastos.get("total"), errors="coerce")
    df_gastos["cliente_final"] = df_gastos.get("contactName", "Sin nombre")
    df_gastos["fecha"] = pd.to_datetime(df_gastos.get("date"), unit="s", errors="coerce")
    df_gastos = df_gastos[columnas_necesarias] if not df_gastos.empty else pd.DataFrame(columns=columnas_necesarias)
    
    # Unimos y normalizamos
    df_completo = pd.concat([df_ingresos, df_gastos], ignore_index=True)
    df_completo["mes"] = df_completo["fecha"].dt.to_period("M")
    df_completo["año_mes"] = df_completo["mes"].astype(str)
    
    # 🎯 Filtro por cliente
    clientes_disponibles = sorted(df_completo["cliente_final"].dropna().unique())
    filtro_cliente = st.sidebar.selectbox("🧑 Cliente específico", ["Todos"] + clientes_disponibles,key="tab1_cliente_pl")
    if filtro_cliente != "Todos":
        df_completo = df_completo[df_completo["cliente_final"] == filtro_cliente]
    
    # Agregación
    df_agg = df_completo.groupby(["cliente_final", "año_mes", "tipo"])["valor"].sum().reset_index()
    df_agg.rename(columns={"año_mes": "🗓️ Año-Mes"}, inplace=True)
    df_pivot = df_agg.pivot_table(index=["cliente_final", "🗓️ Año-Mes"], columns="tipo", values="valor", fill_value=0).reset_index()
    df_pivot["margen"] = df_pivot.get("ingreso", 0) - abs(df_pivot.get("gasto", 0))
    
    for col in ["ingreso", "gasto", "margen"]:
        if col not in df_pivot.columns:
            df_pivot[col] = 0
    
    # =============================
    # 📊 DASHBOARD
    # =============================
    st.metric("💰 Margen Total", f"${df_pivot['margen'].sum():,.2f}")
    
    st.subheader("📋 Márgenes por Cliente y Mes")
    st.dataframe(df_pivot.sort_values(["🗓️ Año-Mes", "margen"], ascending=[False, False]))
    
    st.subheader("📉 Evolución de Márgenes")
    df_total_mes = df_pivot.groupby("🗓️ Año-Mes")[["ingreso", "gasto", "margen"]].sum().reset_index()
    
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 5))
    df_total_mes.set_index("🗓️ Año-Mes")[["ingreso", "gasto", "margen"]].plot(kind='line', marker='o', ax=ax)
    ax.set_title("Evolución de Márgenes por Mes")
    ax.set_ylabel("USD")
    ax.set_xlabel("🗓️ Año-Mes")
    ax.grid(True)
    st.pyplot(fig)

with tab2:
    st.header("📊 Métricas de la Plataforma de Juego")

    # -- Función de consulta --
    def consultar(sql):
        try:
            conn = mysql.connector.connect(
                host=st.secrets["db"]["host"],
                user=st.secrets["db"]["user"],
                password=st.secrets["db"]["password"]
            )
            cursor = conn.cursor()
            cursor.execute(sql)
            datos = cursor.fetchall()
            columnas = [col[0] for col in cursor.description]
            cursor.close()
            conn.close()
            return pd.DataFrame(datos, columns=columnas)
        except mysql.connector.Error as e:
            st.error(f"❌ Error de conexión: {e}")
            return pd.DataFrame()

    # -- Inicializar estado --
    if "filtros_ok" not in st.session_state:
        st.session_state["filtros_ok"] = False
    if "top20_ok" not in st.session_state:
        st.session_state["top20_ok"] = False
        

    def ensure_date_tuple(val):
        if isinstance(val, tuple) or isinstance(val, list):
            return tuple(
                v if isinstance(v, date) else date.fromisoformat(str(v))
                for v in val
            )
        if isinstance(val, (date, datetime)):
            return (val, val)
        return (today, today)
    
    with st.form("filtros"):
        today = date.today()
        raw_fechas = st.session_state.get("fechas", (today, today))
    
        # 🔑 Normalizar lo que venga del session_state
        if isinstance(raw_fechas, (tuple, list)):
            fechas_value = tuple(
                v if isinstance(v, date) else getattr(v, "date", lambda: today)()
                for v in raw_fechas
            )
        elif isinstance(raw_fechas, date):
            fechas_value = (raw_fechas, raw_fechas)
        else:
            fechas_value = (today, today)
    
        fechas = st.date_input(
            "📅 Selecciona fecha o rango de fechas",
            value=fechas_value,
            min_value=date(2000, 1, 1),
        )
        st.session_state["fechas"] = fechas
        # Desempaquetar
        if isinstance(fechas, (tuple, list)) and len(fechas) == 2:
            sd, ed = fechas
        else:
            sd = ed = fechas
        if ed < sd:
            st.error("⚠️ La fecha final debe ser igual o posterior a la inicial.")

        clientes_df = consultar("SELECT DISTINCT user_id FROM plasma_core.users ORDER BY user_id")
        opciones_cliente = ["Todos"] + clientes_df["user_id"].astype(str).tolist()
        cliente_sel = st.selectbox(
            "🧍‍♂️ Selecciona Cliente",
            opciones_cliente,
            index=opciones_cliente.index(st.session_state.get("cliente", "Todos"))
        )

        filtros_btn = st.form_submit_button("🔄 Actualizar")
        if filtros_btn:
            st.session_state["fechas"] = (sd, ed)
            st.session_state["cliente"] = cliente_sel
            st.session_state["filtros_ok"] = True
            # reset Top20 cuando cambian filtros
            st.session_state["top20_ok"] = False

    # -- Si no enviaron filtros aún, no hacemos nada más --
    if not st.session_state["filtros_ok"]:
        st.stop()

    # -- Calcular df_range y mostrar métricas y gráficos --
    start_date, end_date = st.session_state["fechas"]
    cliente = st.session_state["cliente"]

    filtro_altas = "" if cliente == "Todos" else f"AND user_id = '{cliente}'"
    filtro_dep   = filtro_altas
    filtro_jug   = "" if cliente == "Todos" else f"AND s.user_id = '{cliente}'"
    filtro_ggr   = "" if cliente == "Todos" else f"AND session_id IN (SELECT session_id FROM plasma_games.sessions WHERE user_id = '{cliente}')"

    # Construcción de df_range
    if start_date == end_date:
        fecha_str = start_date.strftime("%Y-%m-%d")
        df_altas = consultar(f"""
            SELECT COUNT(*) AS nuevas_altas
            FROM plasma_core.users
            WHERE ts_creation BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' {filtro_altas}
        """)
        df_depos = consultar(f"""
            SELECT COUNT(*) AS total_transacciones,
                   AVG(amount) AS promedio_amount,
                   SUM(amount) AS total_amount
            FROM (
              SELECT amount, user_id
                FROM plasma_payments.nico_transactions
               WHERE ts_commit BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' {filtro_dep}
              UNION ALL
              SELECT amount, user_id
                FROM plasma_payments.payphone_transactions
               WHERE ts_commit BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' {filtro_dep}
            ) t
        """)
        df_jug = consultar(f"""
            SELECT COUNT(DISTINCT re.session_id) AS jugadores,
                   AVG(re.amount)               AS importe_medio
            FROM plasma_games.rounds_entries re
            JOIN plasma_games.sessions s ON re.session_id = s.session_id
            WHERE re.ts BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59'
              AND re.`type`='BET' {filtro_jug}
        """)
        df_ggr = consultar(f"""
            SELECT SUM(CASE WHEN `type`='BET' THEN amount ELSE 0 END) AS total_bet,
                   SUM(CASE WHEN `type`='WIN' THEN amount ELSE 0 END) AS total_win,
                   SUM(CASE WHEN `type`='BET' THEN amount ELSE 0 END)
                   - SUM(CASE WHEN `type`='WIN' THEN amount ELSE 0 END) AS ggr
            FROM plasma_games.rounds_entries
            WHERE ts BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' {filtro_ggr}
        """)
        df_range = pd.DataFrame({
            "nuevas_altas":        [df_altas.iloc[0, 0]],
            "total_transacciones": [df_depos.iloc[0]["total_transacciones"]],
            "promedio_amount":     [df_depos.iloc[0]["promedio_amount"] or 0],
            "total_amount":        [df_depos.iloc[0]["total_amount"] or 0],
            "jugadores":           [df_jug.iloc[0]["jugadores"]],
            "importe_medio":       [df_jug.iloc[0]["importe_medio"] or 0],
            "total_bet":           [df_ggr.iloc[0]["total_bet"]],
            "total_win":           [df_ggr.iloc[0]["total_win"]],
            "ggr":                 [df_ggr.iloc[0]["ggr"]],
        }, index=[fecha_str])
    else:
        start_str = start_date.strftime("%Y-%m-%d")
        end_str   = end_date.strftime("%Y-%m-%d")
        df_altas = consultar(f"""
            SELECT DATE(ts_creation) AS fecha, COUNT(*) AS nuevas_altas
            FROM plasma_core.users
            WHERE ts_creation BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_altas}
            GROUP BY fecha ORDER BY fecha
        """)
        df_depos = consultar(f"""
            SELECT DATE(ts_commit) AS fecha,
                   COUNT(*)            AS total_transacciones,
                   AVG(amount)         AS promedio_amount,
                   SUM(amount)         AS total_amount
            FROM (
              SELECT ts_commit, amount
                FROM plasma_payments.nico_transactions
               WHERE ts_commit BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_dep}
              UNION ALL
              SELECT ts_commit, amount
                FROM plasma_payments.payphone_transactions
               WHERE ts_commit BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_dep}
            ) t
            GROUP BY fecha ORDER BY fecha
        """)
        df_jug = consultar(f"""
            SELECT DATE(re.ts)            AS fecha,
                   COUNT(DISTINCT re.session_id) AS jugadores,
                   AVG(re.amount)               AS importe_medio
            FROM plasma_games.rounds_entries re
            JOIN plasma_games.sessions s ON re.session_id = s.session_id
            WHERE re.ts BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59'
              AND re.`type`='BET' {filtro_jug}
            GROUP BY fecha ORDER BY fecha
        """)
        df_ggr = consultar(f"""
            SELECT DATE(re.ts) AS fecha,
                   SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END) AS total_bet,
                   SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END) AS total_win,
                   SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END)
                   - SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END) AS ggr
            FROM plasma_games.rounds_entries re
            WHERE re.ts BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_ggr}
            GROUP BY fecha ORDER BY fecha
        """)
        date_index = pd.date_range(start_str, end_str, freq="D")
        for df_tmp in (df_altas, df_depos, df_jug, df_ggr):
            df_tmp["fecha"] = pd.to_datetime(df_tmp["fecha"])
        df_range = pd.DataFrame(index=date_index)
        df_range = df_range.join(df_altas.set_index("fecha"))
        df_range = df_range.join(df_depos.set_index("fecha"))
        df_range = df_range.join(df_jug.set_index("fecha"))
        df_range = df_range.join(df_ggr.set_index("fecha")).fillna(0)

    # Guardar en sesión
    st.session_state["df_range"] = df_range

    # Mostrar métricas / gráficos
    for col in df_range.columns:
        title = col.replace("_", " ").title()
        st.subheader(title)
        df_plot = df_range[[col]].reset_index().rename(columns={"index": "Fecha", col: title})
        chart = (
            alt.Chart(df_plot)
               .mark_line(point=True)
               .encode(x="Fecha:T", y=alt.Y(f"{title}:Q", title=title))
               .properties(width=600, height=300)
        )
        st.altair_chart(chart, use_container_width=True)

    # 1) Mapa de KPIs (defínelo antes del form)
    kpi_map = {
        '👥 Nuevas Altas': (
            "COUNT(*)",
            "plasma_core.users u",
            "ts_creation",
            None  # se rellenará dinámicamente con el WHERE
        ),
        '💰 Depósitos (Transacciones)': (
            "COUNT(*)",
            "(SELECT user_id, ts_commit FROM plasma_payments.nico_transactions WHERE 1=1 "
            "UNION ALL "
            "SELECT user_id, ts_commit FROM plasma_payments.payphone_transactions WHERE 1=1) t",
            "ts_commit",
            None
        ),
        '💵 Importe Medio Depósitos': (
            "AVG(amount)",
            "(SELECT user_id, amount, ts_commit FROM plasma_payments.nico_transactions WHERE 1=1 "
            "UNION ALL "
            "SELECT user_id, amount, ts_commit FROM plasma_payments.payphone_transactions WHERE 1=1) t",
            "ts_commit",
            None
        ),
        '💳 Valor Total Depósitos': (
            "SUM(amount)",
            "(SELECT user_id, amount, ts_commit FROM plasma_payments.nico_transactions WHERE 1=1 "
            "UNION ALL "
            "SELECT user_id, amount, ts_commit FROM plasma_payments.payphone_transactions WHERE 1=1) t",
            "ts_commit",
            None
        ),
        '🎮 Jugadores': (
            "COUNT(DISTINCT re.session_id)",
            "plasma_games.rounds_entries re "
            "JOIN plasma_games.sessions s ON re.session_id = s.session_id",
            "ts",
            None
        ),
        '💸 Importe Medio Jugado': (
            "AVG(re.amount)",
            "plasma_games.rounds_entries re "
            "JOIN plasma_games.sessions s ON re.session_id = s.session_id",
            "ts",
            None
        ),
        '🎯 Total BET': (
            "SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END)",
            "plasma_games.rounds_entries re "
            "JOIN plasma_games.sessions s ON re.session_id = s.session_id",
            "ts",
            None
        ),
        '🎯 Total WIN': (
            "SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END)",
            "plasma_games.rounds_entries re "
            "JOIN plasma_games.sessions s ON re.session_id = s.session_id",
            "ts",
            None
        ),
        '📊 GGR': (
            "SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END) - "
            "SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END)",
            "plasma_games.rounds_entries re "
            "JOIN plasma_games.sessions s ON re.session_id = s.session_id",
            "ts",
            None
        ),
    }

    # 3) Formulario Top 20
    #
    st.markdown("---")
    st.header("🔎 Top 20 Clientes por KPI")
    
    with st.form("top20"):
        # 1) Calendario acotado al rango original
        fechas_detalle = st.date_input(
            "🗓 Selecciona fecha o rango para detalle",
            value=st.session_state["fechas"],
            min_value=st.session_state["fechas"][0],
            max_value=st.session_state["fechas"][1],
            key="fechas_detalle"
        )
        if isinstance(fechas_detalle, (tuple, list)) and len(fechas_detalle) == 2:
            sub_start, sub_end = fechas_detalle
        else:
            sub_start = sub_end = fechas_detalle
    
        # 2) Selector de KPI
        kpi_sel = st.selectbox(
            "📊 Selecciona KPI",
            list(kpi_map.keys()),
            key="det_kpi"
        )
    
        # 3) **ESTE** debe ir **dentro** del with y al final
        top20_btn = st.form_submit_button("Mostrar Top 20")
    
    # — Fuera del form, reaccionamos al submit —
    if top20_btn:
        sub_start_str = sub_start.strftime("%Y-%m-%d")
        sub_end_str   = sub_end.strftime("%Y-%m-%d")
    
        # Desempaquetar definición de KPI
        agg, from_clause, ts_col, _ = kpi_map[kpi_sel]
        if "plasma_core.users" in from_clause:
            alias = "u"
        elif "nico_transactions" in from_clause or "payphone_transactions" in from_clause:
            alias = "t"
        else:
            # Para todas las métricas de rounds_entries
            alias = "re"
    
        # Construir cláusula WHERE con alias correcto
        where_clause = (
            f"{alias}.{ts_col} BETWEEN "
            f"'{sub_start_str} 00:00:00' AND '{sub_end_str} 23:59:59'"
        )
    
        # Generar SQL según origen
        if "plasma_core.users" in from_clause:
            sql = f"""
                SELECT {alias}.user_id AS user_id,
                       {agg}           AS valor
                  FROM {from_clause}
                 WHERE {where_clause}
                 GROUP BY {alias}.user_id
                 ORDER BY valor DESC
                 LIMIT 20
            """
        elif "nico_transactions" in from_clause or "payphone_transactions" in from_clause:
            sql = f"""
                SELECT t.user_id, {agg} AS valor
                  FROM (
                        SELECT user_id, amount, ts_commit
                          FROM plasma_payments.nico_transactions
                         WHERE {where_clause}
                        UNION ALL
                        SELECT user_id, amount, ts_commit
                          FROM plasma_payments.payphone_transactions
                         WHERE {where_clause}
                       ) AS t
                 GROUP BY t.user_id
                 ORDER BY valor DESC
                 LIMIT 20
            """
        else:
            # rounds_entries
            sql = f"""
                SELECT s.user_id, {agg} AS valor
                  FROM {from_clause}
                 WHERE {where_clause}
                 GROUP BY s.user_id
                 ORDER BY valor DESC
                 LIMIT 20
            """
    
        # Ejecutar y mostrar
        df_top20 = consultar(sql)
        if not df_top20.empty:
            st.table(df_top20.set_index("user_id").round(2))
        else:
            st.info("⚠️ No hay datos para ese KPI en el periodo seleccionado.")


# ====== TAB 3: P&L desde Holded - VERSION CORREGIDA ======
with tab3:
    st.header("📑 P&L desde Holded (API)")
    st.caption("Calculado desde documentos de Holded y libro diario contable para mayor precisión.")

    # ====== FUNCIONES AUXILIARES PARA HOLDED API ======
    
    @st.cache_data(ttl=300)
    def get_holded_token():
        """Obtener token de autenticación de Holded"""
        try:
            token = "fafbb8191b37e6b696f192e70b4a198c"
            return token
        except Exception as e:
            st.warning(f"Error obteniendo token de Holded: {e}. Usando datos de ejemplo.")
            return None

    @st.cache_data(ttl=60)
    def list_documents_corrected(doc_type: str, start_dt: datetime, end_dt: datetime, page_size=200):
        """Lista documentos con filtros de fecha corregidos"""
        url = f"https://api.holded.com/api/invoicing/v1/documents/{doc_type}"
        headers = {"accept": "application/json", "key": get_holded_token()}
        
        # Usar timestamps correctamente
        params = {
            "starttmp": int(start_dt.timestamp()),
            "endtmp": int(end_dt.timestamp()),
            "sort": "created-asc",
            "limit": page_size
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame()
            else:
                st.error(f"Error {response.status_code} en {doc_type}: {response.text}")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error conectando con Holded: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=60)
    def get_document_detail_corrected(doc_type: str, doc_id: str):
        """Obtiene detalle de documento específico"""
        if not doc_id:
            return {}
            
        url = f"https://api.holded.com/api/invoicing/v1/documents/{doc_type}/{doc_id}"
        headers = {"accept": "application/json", "key": get_holded_token()}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            return response.json() if response.status_code == 200 else {}
        except Exception as e:
            st.warning(f"Error obteniendo detalle de {doc_id}: {e}")
            return {}

    @st.cache_data(ttl=60)
    def list_daily_ledger_corrected(start_dt: datetime, end_dt: datetime):
        """Obtiene libro diario con filtros de fecha mejorados"""
        url = "https://api.holded.com/api/accounting/v1/dailyledger"
        headers = {"accept": "application/json", "key": get_holded_token()}
        
        # Diferentes formatos de fecha que puede aceptar la API
        date_formats = [
            {"from": start_dt.strftime("%Y-%m-%d"), "to": end_dt.strftime("%Y-%m-%d")},
            {"dateFrom": start_dt.strftime("%Y-%m-%d"), "dateTo": end_dt.strftime("%Y-%m-%d")},
            {"starttmp": int(start_dt.timestamp()), "endtmp": int(end_dt.timestamp())},
        ]
        
        for params in date_formats:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if data:  # Si hay datos, usar este formato
                        return data
            except Exception:
                continue
        
        # Si no funcionó ningún filtro, traer todos y filtrar localmente
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # Filtrar localmente por fecha
                filtered_data = []
                for entry in data:
                    entry_date = entry.get('date')
                    if entry_date:
                        try:
                            # Intentar diferentes formatos de fecha
                            if isinstance(entry_date, (int, float)):
                                entry_dt = pd.to_datetime(entry_date, unit='s')
                            else:
                                entry_dt = pd.to_datetime(entry_date)
                            
                            if start_dt <= entry_dt <= end_dt:
                                filtered_data.append(entry)
                        except:
                            continue
                return filtered_data
        except Exception as e:
            st.warning(f"Error obteniendo libro diario: {e}")
            return []
        
        return []

    def classify_account_corrected(code: str, name: str = "") -> str:
        """Clasificador de cuentas PGC mejorado"""
        code = str(code).strip()
        name = str(name).lower()
        
        # Clasificación por código
        if code.startswith("7"):
            return "Ingresos"
        elif code.startswith("60"):
            return "Aprovisionamientos"
        elif code.startswith("64"):
            return "Gastos de personal"
        elif code.startswith(("62", "63", "65")):
            return "Otros gastos de explotación"
        elif code.startswith("66"):
            return "Gastos financieros"
        elif code.startswith("76"):
            return "Ingresos financieros"
        elif code.startswith("768"):
            return "Diferencias de cambio"
        elif code.startswith("668"):
            return "Diferencias de cambio"
        elif code.startswith(("77")):
            return "Otros resultados"
        elif code.startswith("6"):
            return "Otros gastos de explotación"
        
        # Clasificación por nombre
        if any(word in name for word in ["nomina", "sueldo", "salario", "personal", "seguridad social"]):
            return "Gastos de personal"
        elif any(word in name for word in ["interes", "financiero", "prestamo", "credito"]):
            return "Gastos financieros"
        elif "cambio" in name or "divisa" in name:
            return "Diferencias de cambio"
        elif any(word in name for word in ["compra", "suministro", "materia prima"]):
            return "Aprovisionamientos"
        
        return "Otros gastos de explotación"

    def parse_purchase_lines_corrected(doc_json: dict):
        """Extrae líneas de compra con mejor manejo de datos"""
        lines = []
        if not doc_json:
            return lines
            
        # Obtener fecha del documento
        doc_date = doc_json.get("date")
        if isinstance(doc_date, (int, float)):
            fecha = pd.to_datetime(doc_date, unit='s', errors='coerce')
        else:
            fecha = pd.to_datetime(doc_date, errors='coerce')
        
        # Buscar líneas en diferentes campos posibles
        items = doc_json.get("items", []) or doc_json.get("lines", []) or doc_json.get("concepts", [])
        
        if items:
            for item in items:
                # Obtener importe
                amount = 0
                for field in ["subTotal", "subtotal", "untaxedAmount", "base", "amount", "total"]:
                    if field in item and item[field] is not None:
                        try:
                            amount = float(item[field])
                            break
                        except (ValueError, TypeError):
                            continue
                
                # Obtener cuenta contable
                account_code = (item.get("expenseAccountCode") or 
                               item.get("accountCode") or 
                               item.get("expenseAccountId") or 
                               item.get("accountId") or "")
                
                account_name = (item.get("accountName") or 
                               item.get("name") or 
                               item.get("description") or "")
                
                # Los gastos van negativos
                lines.append((fecha, str(account_code), account_name, -abs(amount)))
        else:
            # Si no hay líneas, usar el total del documento
            total_amount = 0
            for field in ["subTotal", "total", "amount"]:
                if field in doc_json and doc_json[field] is not None:
                    try:
                        total_amount = float(doc_json[field])
                        break
                    except (ValueError, TypeError):
                        continue
            
            if total_amount > 0:
                lines.append((fecha, "6XXX", "Gasto sin desglosar", -abs(total_amount)))
        
        return lines

    # ====== INTERFAZ MEJORADA ======
    
    # Sección de filtros en sidebar para Tab 3
    st.sidebar.markdown("---")
    st.sidebar.header("📑 Filtros P&L Holded")
    
    # Filtros de fecha
    hoy = datetime.today()
    primer_dia_mes = hoy.replace(day=1)
    
    # Usar session_state para mantener los valores
    if "pl_fecha_inicio" not in st.session_state:
        st.session_state.pl_fecha_inicio = primer_dia_mes.date()
    if "pl_fecha_fin" not in st.session_state:
        st.session_state.pl_fecha_fin = hoy.date()
    
    fecha_inicio_pl = st.sidebar.date_input(
        "Fecha Inicio P&L",
        value=st.session_state.pl_fecha_inicio,
        key="pl_inicio_input"
    )
    
    fecha_fin_pl = st.sidebar.date_input(
        "Fecha Fin P&L",
        value=st.session_state.pl_fecha_fin,
        key="pl_fin_input"
    )
    
    # Actualizar session state
    if fecha_inicio_pl != st.session_state.pl_fecha_inicio:
        st.session_state.pl_fecha_inicio = fecha_inicio_pl
        st.session_state.pl_data_updated = False
        
    if fecha_fin_pl != st.session_state.pl_fecha_fin:
        st.session_state.pl_fecha_fin = fecha_fin_pl
        st.session_state.pl_data_updated = False
    
    # Validar fechas
    if fecha_inicio_pl > fecha_fin_pl:
        st.sidebar.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
        st.stop()
    
# 🔑 Cargar clientes dinámicamente desde invoices + purchases + libro diario
df_invoices_for_clients = list_documents_corrected(
    "invoice",
    datetime.combine(fecha_inicio_pl, datetime.min.time()),
    datetime.combine(fecha_fin_pl, datetime.max.time())
)
df_purchases_for_clients = list_documents_corrected(
    "purchase",
    datetime.combine(fecha_inicio_pl, datetime.min.time()),
    datetime.combine(fecha_fin_pl, datetime.max.time())
)

clientes_invoices = df_invoices_for_clients["contactName"].dropna().unique().tolist() if not df_invoices_for_clients.empty else []
clientes_purchases = df_purchases_for_clients["contactName"].dropna().unique().tolist() if not df_purchases_for_clients.empty else []

# 🆕 Añadir clientes detectados en el libro diario
ledger_entries_for_clients = list_daily_ledger_corrected(
    datetime.combine(fecha_inicio_pl, datetime.min.time()),
    datetime.combine(fecha_fin_pl, datetime.max.time())
)

clientes_ledger = []
for entry in ledger_entries_for_clients:
    cliente = entry.get("contactName") or entry.get("thirdParty") or entry.get("customer")
    if cliente:
        clientes_ledger.append(cliente)
    else:
        clientes_ledger.append("Libro Diario (sin cliente)")

    clientes_unicos = sorted(set(clientes_invoices + clientes_purchases + clientes_ledger))
    clientes_pl_3 = ["Todos"] + clientes_unicos
    
    if "pl_cliente_sel" not in st.session_state:
        st.session_state.pl_cliente_sel = "Todos"
    col1, =st.columns([1])
    cliente_pl = col1.selectbox(
        "Cliente P&L",
        clientes_pl_3,   # tu lista dinámica
        index=0,         # "Todos" por defecto
        key="tab3_cliente_pl"
    )

    
    if cliente_pl != st.session_state.pl_cliente_sel:
        st.session_state.pl_cliente_sel = cliente_pl
        st.session_state.pl_data_updated = False
    
    # Opciones adicionales
    usar_libro_diario = st.sidebar.checkbox("Usar Libro Diario", value=True, key="usar_libro")
    mostrar_detalle_cuentas = st.sidebar.checkbox("Mostrar Detalle por Cuenta", value=False, key="mostrar_detalle")
    
    # Botón para forzar actualización
    if st.sidebar.button("🔄 Actualizar P&L", type="primary"):
        st.session_state.pl_data_updated = False
        # Limpiar cache
        list_documents_corrected.clear()
        get_document_detail_corrected.clear()
        list_daily_ledger_corrected.clear()
    
    # Mostrar filtros activos
    st.sidebar.info(f"""
    **Filtros activos:**
    - Período: {fecha_inicio_pl} a {fecha_fin_pl}
    - Cliente: {cliente_pl}
    - Libro diario: {'Sí' if usar_libro_diario else 'No'}
    """)
    
    # ====== PROCESAMIENTO DE DATOS ======
    
    # Convertir fechas a datetime
    inicio_dt = datetime.combine(fecha_inicio_pl, datetime.min.time())
    fin_dt = datetime.combine(fecha_fin_pl, datetime.max.time())
    
    # Verificar si necesitamos actualizar datos
    if not st.session_state.get("pl_data_updated", False):
        
        try:
            with st.spinner("Cargando datos de Holded..."):
                
                # 1. CARGAR FACTURAS DE VENTA (INGRESOS)
                st.info("📥 Cargando facturas de venta...")
                df_invoices = list_documents_corrected("invoice", inicio_dt, fin_dt)
                
                # Procesar ingresos
                ingresos_data = []
                if not df_invoices.empty:
                    for _, invoice in df_invoices.iterrows():
                        # Convertir fecha
                        invoice_date = invoice.get("date")
                        if isinstance(invoice_date, (int, float)):
                            fecha = pd.to_datetime(invoice_date, unit='s', errors='coerce')
                        else:
                            fecha = pd.to_datetime(invoice_date, errors='coerce')
                        
                        if pd.isna(fecha):
                            continue
                            
                        # Obtener importe
                        amount = 0
                        for field in ["subTotal", "subtotal", "untaxedAmount", "total"]:
                            if field in invoice and invoice[field] is not None:
                                try:
                                    amount = float(invoice[field])
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        # Obtener cliente
                        cliente = invoice.get("contactName", "Sin nombre")
                        
                        # Filtrar por cliente si no es "Todos"
                        if cliente_pl != "Todos" and cliente != cliente_pl:
                            continue
                        
                        periodo = fecha.to_period("M").strftime("%Y-%m")
                        ingresos_data.append({
                            "periodo": periodo,
                            "fecha": fecha,
                            "cliente": cliente,
                            "categoria": "Ingresos",
                            "importe": amount,
                            "cuenta": "70XXX",
                            "descripcion": f"Factura {invoice.get('docNumber', '')}"
                        })
                
                st.success(f"✅ Procesadas {len(ingresos_data)} facturas de venta")
                
                # 2. CARGAR FACTURAS DE COMPRA (GASTOS)
                st.info("📤 Cargando facturas de compra...")
                df_purchases = list_documents_corrected("purchase", inicio_dt, fin_dt)
                
                gastos_data = []
                if not df_purchases.empty:
                    progress_bar = st.progress(0)
                    for idx, (_, purchase) in enumerate(df_purchases.iterrows()):
                        progress_bar.progress((idx + 1) / len(df_purchases))
                        
                        purchase_id = str(purchase.get("id", ""))
                        if purchase_id:
                            # Obtener detalle
                            detail = get_document_detail_corrected("purchase", purchase_id)
                            lines = parse_purchase_lines_corrected(detail)
                            
                            for fecha, account_code, account_name, amount in lines:
                                if pd.isna(fecha) or amount == 0:
                                    continue
                                
                                # Filtrar por cliente si aplica (usar proveedor)
                                proveedor = purchase.get("contactName", "Sin nombre")
                                if cliente_pl != "Todos" and proveedor != cliente_pl:
                                    continue
                                
                                periodo = fecha.to_period("M").strftime("%Y-%m")
                                categoria = classify_account_corrected(account_code, account_name)
                                
                                gastos_data.append({
                                    "periodo": periodo,
                                    "fecha": fecha,
                                    "cliente": proveedor,
                                    "categoria": categoria,
                                    "importe": amount,
                                    "cuenta": account_code,
                                    "descripcion": account_name
                                })
                    
                    progress_bar.empty()
                
                st.success(f"✅ Procesadas {len(gastos_data)} líneas de compra")
                
                # 3. CARGAR LIBRO DIARIO (SI ESTÁ HABILITADO)
                diario_data = []
                if usar_libro_diario:
                    st.info("📚 Cargando libro diario...")
                    ledger_entries = list_daily_ledger_corrected(inicio_dt, fin_dt)
                    
                    for entry in ledger_entries:
                        # Procesar fecha
                        entry_date = entry.get("date")
                        if isinstance(entry_date, (int, float)):
                            fecha = pd.to_datetime(entry_date, unit='s', errors='coerce')
                        else:
                            fecha = pd.to_datetime(entry_date, errors='coerce')
                        
                        if pd.isna(fecha):
                            continue
                        
                        # Calcular importe
                        amount = entry.get("amount")
                        if amount is None:
                            debit = float(entry.get("debit", 0) or 0)
                            credit = float(entry.get("credit", 0) or 0)
                            amount = debit - credit
                        else:
                            amount = float(amount)
                        
                        if amount == 0:
                            continue
                        
                        account_code = str(entry.get("accountCode", ""))
                        account_name = str(entry.get("accountName", ""))
                        categoria = classify_account_corrected(account_code, account_name)
                        periodo = fecha.to_period("M").strftime("%Y-%m")
                        
                        cliente_entry = entry.get("contactName") or entry.get("thirdParty") or entry.get("customer") or "Libro Diario (sin cliente)"
                        
                        # Aplicar filtro de cliente si no es "Todos"
                        if cliente_pl != "Todos" and cliente_entry != cliente_pl:
                            continue
                        
                        diario_data.append({
                            "periodo": periodo,
                            "fecha": fecha,
                            "cliente": cliente_entry,
                            "categoria": categoria,
                            "importe": amount,
                            "cuenta": account_code,
                            "descripcion": account_name
                        })
                    
                    st.success(f"✅ Procesadas {len(diario_data)} entradas del libro diario")
                
                # 4. CONSOLIDAR DATOS
                all_data = ingresos_data + gastos_data + diario_data
                df_consolidated = pd.DataFrame(all_data)
                
                if df_consolidated.empty:
                    st.warning("⚠️ No se encontraron datos en el período seleccionado")
                    st.session_state.pl_data_updated = True
                    st.stop()
                
                # Guardar en session state
                st.session_state.df_pl_consolidated = df_consolidated
                st.session_state.pl_data_updated = True
                
        except Exception as e:
            st.error(f"❌ Error procesando datos: {str(e)}")
            st.exception(e)
            st.stop()
    
    # ====== MOSTRAR RESULTADOS ======
    
    if st.session_state.get("pl_data_updated", False):
        df_data = st.session_state.get("df_pl_consolidated", pd.DataFrame())
        
        if not df_data.empty:
            
            # Crear P&L agregado
            df_pl_summary = df_data.groupby(["periodo", "categoria"])["importe"].sum().unstack(fill_value=0).reset_index()
            
            # Asegurar todas las columnas necesarias
            required_columns = [
                "Ingresos", "Aprovisionamientos", "Gastos de personal",
                "Otros gastos de explotación", "Ingresos financieros",
                "Gastos financieros", "Diferencias de cambio", "Otros resultados"
            ]
            
            for col in required_columns:
                if col not in df_pl_summary.columns:
                    df_pl_summary[col] = 0.0
            
            # Calcular métricas
            df_pl_summary["Margen Bruto"] = df_pl_summary["Ingresos"] + df_pl_summary["Aprovisionamientos"]
            df_pl_summary["EBITDA"] = (df_pl_summary["Margen Bruto"] + 
                                     df_pl_summary["Gastos de personal"] + 
                                     df_pl_summary["Otros gastos de explotación"])
            df_pl_summary["Resultado Operativo"] = df_pl_summary["EBITDA"] + df_pl_summary["Otros resultados"]
            df_pl_summary["Resultado Financiero"] = (df_pl_summary["Ingresos financieros"] + 
                                                   df_pl_summary["Gastos financieros"] + 
                                                   df_pl_summary["Diferencias de cambio"])
            df_pl_summary["Resultado Neto"] = df_pl_summary["Resultado Operativo"] + df_pl_summary["Resultado Financiero"]
            
            # Mostrar métricas principales
            st.subheader("📊 Resumen P&L")
            
            totales = df_pl_summary.select_dtypes(include=[float, int]).sum()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Ingresos", f"${totales['Ingresos']:,.2f}")
            col2.metric("📈 Margen Bruto", f"${totales['Margen Bruto']:,.2f}")
            col3.metric("🎯 EBITDA", f"${totales['EBITDA']:,.2f}")
            col4.metric("💎 Resultado Neto", f"${totales['Resultado Neto']:,.2f}")
            
            # Ratios
            if totales['Ingresos'] > 0:
                col5, col6, col7, col8 = st.columns(4)
                col5.metric("Margen %", f"{(totales['Margen Bruto']/totales['Ingresos']*100):.1f}%")
                col6.metric("EBITDA %", f"{(totales['EBITDA']/totales['Ingresos']*100):.1f}%")
                col7.metric("Resultado %", f"{(totales['Resultado Neto']/totales['Ingresos']*100):.1f}%")
                
                gastos_personal = abs(totales['Gastos de personal'])
                if gastos_personal > 0:
                    col8.metric("Personal %", f"{(gastos_personal/totales['Ingresos']*100):.1f}%")
            
            # Tabla detallada
            st.subheader("📋 P&L Detallado")
            
            display_columns = [
                "periodo", "Ingresos", "Aprovisionamientos", "Margen Bruto",
                "Gastos de personal", "Otros gastos de explotación", "EBITDA",
                "Ingresos financieros", "Gastos financieros", "Diferencias de cambio",
                "Resultado Financiero", "Otros resultados", "Resultado Operativo", "Resultado Neto"
            ]
            
            df_display = df_pl_summary[display_columns].copy()
            df_display = df_display.round(2)
            df_display.columns = [col.replace('periodo', '🗓️ Período') for col in df_display.columns]
            
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # Gráfico de evolución
            if len(df_pl_summary) > 1:
                st.subheader("📈 Evolución Temporal")
                
                # Preparar datos para gráfico
                chart_metrics = ["Ingresos", "Margen Bruto", "EBITDA", "Resultado Neto"]
                chart_data = df_pl_summary[["periodo"] + chart_metrics].melt(
                    id_vars=["periodo"],
                    var_name="Métrica",
                    value_name="Valor"
                )
                
                chart = (
                    alt.Chart(chart_data)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("periodo:O", title="Período"),
                        y=alt.Y("Valor:Q", title="Importe ($)"),
                        color=alt.Color("Métrica:N"),
                        tooltip=["periodo:O", "Métrica:N", "Valor:Q"]
                    )
                    .properties(height=400)
                )
                st.altair_chart(chart, use_container_width=True)
            
            # Detalle por cuenta si está habilitado
            if mostrar_detalle_cuentas:
                st.subheader("🔍 Detalle por Cuenta Contable")
                
                # Filtros para detalle
                col_f1, col_f2, col_f3 = st.columns(3)
                
                categorias_disponibles = ["Todas"] + sorted(df_data["categoria"].unique().tolist())
                cat_filter = col_f1.selectbox("Categoría", categorias_disponibles, key="cat_detail")
                
                periodos_disponibles = ["Todos"] + sorted(df_data["periodo"].unique().tolist())
                periodo_filter = col_f2.selectbox("Período", periodos_disponibles, key="periodo_detail")
                
                clientes_disponibles = ["Todos"] + sorted(df_data["cliente"].unique().tolist())
                cliente_detail_filter = col_f3.selectbox("Cliente", clientes_disponibles, key="cliente_detail")
                
                # Aplicar filtros
                df_filtered = df_data.copy()
                if cat_filter != "Todas":
                    df_filtered = df_filtered[df_filtered["categoria"] == cat_filter]
                if periodo_filter != "Todos":
                    df_filtered = df_filtered[df_filtered["periodo"] == periodo_filter]
                if cliente_detail_filter != "Todos":
                    df_filtered = df_filtered[df_filtered["cliente"] == cliente_detail_filter]
                
                # Mostrar detalle
                if not df_filtered.empty:
                    df_detail_display = df_filtered[["periodo", "cliente", "categoria", "cuenta", "descripcion", "importe"]].copy()
                    df_detail_display = df_detail_display.sort_values(["periodo", "categoria", "importe"], ascending=[True, True, False])
                    df_detail_display["importe"] = df_detail_display["importe"].round(2)
                    
                    st.dataframe(df_detail_display, use_container_width=True, height=400)
                    
                    # Resumen por categoría
                    resumen_cat = df_filtered.groupby("categoria")["importe"].sum().reset_index().sort_values("importe")
                    
                    if len(resumen_cat) > 0:
                        chart_cat = (
                            alt.Chart(resumen_cat)
                            .mark_bar()
                            .encode(
                                x=alt.X("importe:Q", title="Importe ($)"),
                                y=alt.Y("categoria:N", sort="-x", title="Categoría"),
                                color=alt.condition(
                                    alt.datum.importe > 0,
                                    alt.value("steelblue"),
                                    alt.value("orange")
                                )
                            )
                            .properties(height=300)
                        )
                        st.altair_chart(chart_cat, use_container_width=True)
                else:
                    st.info("No hay datos que coincidan con los filtros seleccionados.")
            
            # Información de debug
            with st.expander("🔧 Información de Debug"):
                st.write("**Parámetros de consulta:**")
                st.write(f"- Período: {fecha_inicio_pl} a {fecha_fin_pl}")
                st.write(f"- Cliente seleccionado: {cliente_pl}")
                st.write(f"- Usar libro diario: {usar_libro_diario}")
                
                st.write("**Datos procesados:**")
                st.write(f"- Total registros: {len(df_data)}")
                st.write(f"- Períodos únicos: {sorted(df_data['periodo'].unique())}")
                st.write(f"- Categorías únicas: {sorted(df_data['categoria'].unique())}")
                st.write(f"- Clientes únicos: {sorted(df_data['cliente'].unique())}")
                
                if st.checkbox("Mostrar datos raw"):
                    st.dataframe(df_data.head(50))
        else:
            st.warning("⚠️ No hay datos consolidados disponibles.")
    else:
        st.info("👆 Usa los filtros del sidebar y presiona 'Actualizar P&L' para cargar los datos.")

# ====== FIN DEL CÓDIGO ======


