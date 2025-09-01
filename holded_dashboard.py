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
    filtro_cliente = st.sidebar.selectbox("🧑 Cliente específico", ["Todos"] + clientes_disponibles)
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


# ====== TAB 3: P&L desde Holded ======
with tab3:
    st.header("📑 P&L desde Holded (API)")
    st.caption("Calculado desde documentos de Holded y libro diario contable para mayor precisión.")

    # ====== FUNCIONES AUXILIARES PARA HOLDED API ======
    
    @st.cache_data(ttl=300)  # Cache por 5 minutos
    def get_holded_token():
        """Obtener token de autenticación de Holded"""
        try:
            # Intentar diferentes estructuras de secrets
            token = "fafbb8191b37e6b696f192e70b4a198c"
            #if "holded" in st.secrets:
            #    token = st.secrets["holded"].get("api_key") or st.secrets["holded"].get("token")
            #elif "HOLDED_API_KEY" in st.secrets:
            #    token = st.secrets["HOLDED_API_KEY"]
            #elif hasattr(st.secrets, "holded_api_key"):
            #    token = st.secrets.holded_api_key
                
            if not token:
                st.warning("⚠️ No se encontró la API key de Holded en secrets. Usando datos de ejemplo.")
                return None
            return token
        except Exception as e:
            st.warning(f"⚠️ Error obteniendo token de Holded: {e}. Usando datos de ejemplo.")
            return None
    def make_holded_request(endpoint, params=None):
        """Hacer petición a la API de Holded"""
        token = get_holded_token()
        if not token:
            return None
        
        import requests
        
        base_url = "https://api.holded.com/api"
        headers = {
            "accept": "application/json",
            "key": token
        }
        
        try:
            url = f"{base_url}/{endpoint}"
            response = requests.get(url, headers=headers, params=params or {}, timeout=30)
            
            if response.status_code == 401:
                st.error("❌ Token de Holded inválido o expirado. Verifica la configuración.")
                return None
            elif response.status_code == 403:
                st.error("❌ Sin permisos para acceder a este endpoint de Holded.")
                return None
            elif response.status_code == 404:
                st.warning("⚠️ Endpoint no encontrado en Holded API.")
                return None
                
            response.raise_for_status()
            
            if not response.text.strip():
                return []
            
            return response.json()
            
        except requests.exceptions.Timeout:
            st.error("❌ Timeout en la conexión con Holded API")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error en petición a Holded: {e}")
            return None
        except ValueError as e:
            st.error(f"❌ Error procesando respuesta JSON de Holded: {e}")
            return None

            

    def list_documents(doc_type, start_date, end_date):
        """Listar documentos de Holded en un rango de fechas"""
        try:
            # Convertir fechas a timestamp
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())
            
            params = {
                "dateFrom": start_ts,
                "dateTo": end_ts,
                "limit": 100
            }
            
            # Mapeo de tipos de documento
            endpoint_map = {
                "invoice": "invoicing/v1/documents/invoice",
                "purchase": "invoicing/v1/documents/purchase"
            }
            
            endpoint = endpoint_map.get(doc_type)
            if not endpoint:
                return pd.DataFrame()
            
            data = make_holded_request(endpoint, params)
            if not data:
                return pd.DataFrame()
            
            # Convertir a DataFrame
            documents = data.get("data", []) if isinstance(data, dict) else data
            return pd.DataFrame(documents)
            
        except Exception as e:
            st.error(f"❌ Error listando documentos {doc_type}: {e}")
            return pd.DataFrame()

    def get_document_detail(doc_type, doc_id):
        """Obtener detalle de un documento específico"""
        if not doc_id:
            return {}
        
        try:
            endpoint_map = {
                "invoice": f"invoicing/v1/documents/invoice/{doc_id}",
                "purchase": f"invoicing/v1/documents/purchase/{doc_id}"
            }
            
            endpoint = endpoint_map.get(doc_type)
            if not endpoint:
                return {}
            
            return make_holded_request(endpoint) or {}
            
        except Exception as e:
            st.error(f"❌ Error obteniendo detalle de documento: {e}")
            return {}

    def parse_purchase_lines(purchase_detail):
        """Extraer líneas de compra con cuentas contables"""
        lines = []
        try:
            items = purchase_detail.get("items", [])
            doc_date = purchase_detail.get("date")
            
            for item in items:
                account_code = item.get("accountCode", "")
                account_name = item.get("accountName", item.get("name", ""))
                amount = float(item.get("total", 0) or item.get("subtotal", 0) or 0)
                
                # Los gastos van en negativo
                amount = -abs(amount)
                
                lines.append((doc_date, account_code, account_name, amount))
                
        except Exception as e:
            st.warning(f"⚠️ Error procesando líneas de compra: {e}")
            
        return lines

    def list_daily_ledger(start_date, end_date):
        """Obtener asientos del libro diario"""
        try:
            params = {
                "dateFrom": start_date.strftime("%Y-%m-%d"),
                "dateTo": end_date.strftime("%Y-%m-%d"),
                "limit": 500
            }
            
            data = make_holded_request("accounting/v1/dailyledger", params)
            if not data:
                return []
            
            entries = data.get("data", []) if isinstance(data, dict) else data
            return entries
                
        except Exception as e:
            st.error(f"❌ Error obteniendo libro diario: {e}")
            return []

    def classify_account(account_code, account_name):
        """Clasificar cuenta contable en categorías P&L"""
        account_code = str(account_code).strip()
        account_name = str(account_name).lower()
        
        # Mapeo por código de cuenta (Plan General Contable)
        if account_code.startswith('7'):
            return "Ingresos"
        elif account_code.startswith('60'):
            return "Aprovisionamientos"
        elif account_code.startswith('64'):
            return "Gastos de personal"
        elif account_code.startswith('76'):
            return "Ingresos financieros"
        elif account_code.startswith('66') or account_code.startswith('67'):
            return "Gastos financieros"
        elif account_code.startswith('768') or account_code.startswith('668'):
            return "Diferencias de cambio"
        elif account_code.startswith('77') or account_code.startswith('67'):
            return "Otros resultados"
        elif account_code.startswith('6'):
            return "Otros gastos de explotación"
        
        # Clasificación por nombre si no hay código
        if any(word in account_name for word in ['nómina', 'sueldo', 'salario', 'personal', 'seguridad social']):
            return "Gastos de personal"
        elif any(word in account_name for word in ['interés', 'financiero', 'préstamo', 'crédito']):
            return "Gastos financieros"
        elif 'cambio' in account_name or 'divisa' in account_name:
            return "Diferencias de cambio"
        elif any(word in account_name for word in ['compra', 'suministro', 'materia prima']):
            return "Aprovisionamientos"
        
        return "Otros gastos de explotación"

    # ====== INTERFAZ DEL TAB 3 ======
    
    # Controles de fecha
    col1, col2 = st.columns(2)
    hoy = datetime.today()
    inicio_pl = col1.date_input(
        "📅 Fecha Inicio P&L", 
        value=hoy.replace(day=1),
        max_value=hoy
    )
    fin_pl = col2.date_input(
        "📅 Fecha Fin P&L", 
        value=hoy,
        max_value=hoy
    )
    
    # Validar fechas
    if inicio_pl > fin_pl:
        st.error("⚠️ La fecha de inicio no puede ser posterior a la fecha de fin.")
        st.stop()
    
    # Convertir a datetime
    inicio_pl = datetime(inicio_pl.year, inicio_pl.month, inicio_pl.day)
    fin_pl = datetime(fin_pl.year, fin_pl.month, fin_pl.day, 23, 59, 59)

    # Opciones adicionales
    col3, col4 = st.columns(2)
    usar_libro = col3.toggle("🔎 Usar Libro Diario Contable", value=True, help="Incluir datos del libro diario para mayor precisión")
    mostrar_detalle = col4.toggle("📋 Mostrar Detalle por Cuenta", value=False, help="Mostrar desglose detallado por cuenta contable")

    # Botón para actualizar datos
    if st.button("🔄 Actualizar P&L", type="primary"):
        st.session_state["pl_updated"] = True
    
    # Verificar conexión con Holded
    if get_holded_token() is None:
        st.error("❌ No se puede conectar con Holded. Verifica la configuración de la API.")
        st.info("💡 Configura la API key de Holded en los secrets de Streamlit.")
        st.stop()

    try:
        with st.spinner("📊 Procesando datos de Holded..."):
            
            # ====== 1. INGRESOS (FACTURAS DE VENTA) ======
            st.subheader("💰 Procesando Ingresos...")
            df_inv = list_documents("invoice", inicio_pl, fin_pl)
            
            ingresos_rows = []
            if not df_inv.empty:
                df_inv["_fecha"] = pd.to_datetime(df_inv.get("date", 0), unit="s", errors="coerce")
                df_inv["_ym"] = df_inv["_fecha"].dt.to_period("M").astype(str)
                
                # Intentar múltiples campos para el importe
                df_inv["importe"] = pd.to_numeric(
                    df_inv.get("subTotal", df_inv.get("total", 0)), 
                    errors="coerce"
                ).fillna(0.0)
                
                ingresos_mes = df_inv.groupby("_ym")["importe"].sum().reset_index()
                ingresos_mes.columns = ["🗓️ Año-Mes", "Ingresos"]
                
                st.success(f"✅ Procesadas {len(df_inv)} facturas de venta")
            else:
                st.warning("⚠️ No se encontraron facturas de venta en el período")
                ingresos_mes = pd.DataFrame(columns=["🗓️ Año-Mes", "Ingresos"])

            # ====== 2. GASTOS (FACTURAS DE COMPRA) ======
            st.subheader("💸 Procesando Gastos...")
            df_pur = list_documents("purchase", inicio_pl, fin_pl)
            
            compras_rows = []
            if not df_pur.empty:
                progress_bar = st.progress(0)
                total_purchases = len(df_pur)
                
                for idx, (_, row) in enumerate(df_pur.iterrows()):
                    # Actualizar barra de progreso
                    progress_bar.progress((idx + 1) / total_purchases)
                    
                    doc_id = str(row.get("id") or row.get("_id") or row.get("docId") or "")
                    if doc_id:
                        det = get_document_detail("purchase", doc_id)
                        lines = parse_purchase_lines(det)
                        
                        for (fecha, acct, acct_name, amt) in lines:
                            if pd.notna(fecha):
                                ym = pd.to_datetime(fecha, unit="s", errors="coerce").to_period("M").astype(str)
                            else:
                                ym = pd.to_datetime(row.get("date"), unit="s", errors="coerce").to_period("M").astype(str)
                            
                            cat = classify_account(str(acct), acct_name)
                            compras_rows.append({
                                "🗓️ Año-Mes": ym,
                                "cuenta": acct,
                                "nombre_cuenta": acct_name,
                                "categoria": cat,
                                "importe": amt
                            })
                
                progress_bar.empty()
                st.success(f"✅ Procesadas {len(df_pur)} facturas de compra")
            else:
                st.warning("⚠️ No se encontraron facturas de compra en el período")

            df_comp = pd.DataFrame(compras_rows)
            
            # Si no hay líneas detalladas, usar totales de compras
            if df_comp.empty and not df_pur.empty:
                st.info("📋 Usando totales de compras sin detalle por cuenta")
                df_pur["_fecha"] = pd.to_datetime(df_pur.get("date"), unit="s", errors="coerce")
                df_pur["_ym"] = df_pur["_fecha"].dt.to_period("M").astype(str)
                df_pur["importe"] = -abs(pd.to_numeric(df_pur.get("total", 0), errors="coerce").fillna(0))
                
                df_comp = df_pur.groupby("_ym").agg({
                    "importe": "sum"
                }).reset_index()
                df_comp["categoria"] = "Otros gastos de explotación"
                df_comp.columns = ["🗓️ Año-Mes", "importe", "categoria"]

            # ====== 3. LIBRO DIARIO (OPCIONAL) ======
            ledger_rows = []
            if usar_libro:
                st.subheader("📚 Procesando Libro Diario...")
                with st.spinner("Obteniendo asientos contables..."):
                    asientos = list_daily_ledger(inicio_pl, fin_pl)
                    
                    for asiento in asientos:
                        fecha = asiento.get("date") or asiento.get("ts")
                        fecha_dt = pd.to_datetime(fecha, errors="coerce")
                        
                        if pd.notna(fecha_dt):
                            ym = fecha_dt.to_period("M").astype(str)
                            
                            # Obtener información de la cuenta
                            acct_code = str(asiento.get("accountCode") or asiento.get("account") or "")
                            acct_name = str(asiento.get("accountName") or asiento.get("description") or "")
                            
                            # Calcular importe (debit - credit o amount)
                            amt = asiento.get("amount")
                            if amt is None:
                                debit = float(asiento.get("debit", 0) or 0)
                                credit = float(asiento.get("credit", 0) or 0)
                                amt = debit - credit
                            else:
                                amt = float(amt)
                            
                            cat = classify_account(acct_code, acct_name)
                            ledger_rows.append({
                                "🗓️ Año-Mes": ym,
                                "categoria": cat,
                                "importe": amt,
                                "cuenta": acct_code,
                                "descripcion": acct_name
                            })
                
                if ledger_rows:
                    st.success(f"✅ Procesados {len(ledger_rows)} asientos del libro diario")
                else:
                    st.warning("⚠️ No se encontraron asientos en el libro diario")

            df_ledger = pd.DataFrame(ledger_rows)

            # ====== 4. CONSOLIDACIÓN P&L ======
            st.subheader("📊 Consolidando P&L...")
            
            # Empezar con ingresos
            df_pl = ingresos_mes.copy()
            
            # Agregar gastos por categoría
            if not df_comp.empty:
                comp_pivot = df_comp.groupby(["🗓️ Año-Mes", "categoria"])["importe"].sum().unstack(fill_value=0).reset_index()
                df_pl = df_pl.merge(comp_pivot, on="🗓️ Año-Mes", how="outer").fillna(0)
            
            # Agregar datos del libro diario si están disponibles
            if not df_ledger.empty:
                ledger_pivot = df_ledger.groupby(["🗓️ Año-Mes", "categoria"])["importe"].sum().unstack(fill_value=0).reset_index()
                
                # Merge con df_pl, sumando valores existentes
                for col in ledger_pivot.columns:
                    if col != "🗓️ Año-Mes":
                        if col in df_pl.columns:
                            # Si la columna ya existe, sumar valores
                            df_pl = df_pl.merge(
                                ledger_pivot[["🗓️ Año-Mes", col]].rename(columns={col: f"{col}_ledger"}),
                                on="🗓️ Año-Mes", how="outer"
                            ).fillna(0)
                            df_pl[col] = df_pl[col] + df_pl[f"{col}_ledger"]
                            df_pl.drop(columns=[f"{col}_ledger"], inplace=True)
                        else:
                            # Si la columna no existe, hacer merge directo
                            df_pl = df_pl.merge(
                                ledger_pivot[["🗓️ Año-Mes", col]], 
                                on="🗓️ Año-Mes", how="outer"
                            ).fillna(0)

            # Asegurar que todas las columnas P&L existan
            required_cols = [
                "Ingresos", "Aprovisionamientos", "Gastos de personal", 
                "Otros gastos de explotación", "Ingresos financieros", 
                "Gastos financieros", "Diferencias de cambio", "Otros resultados"
            ]
            
            for col in required_cols:
                if col not in df_pl.columns:
                    df_pl[col] = 0.0

            # ====== 5. CÁLCULO DE KPIS P&L ======
            df_pl["Margen Bruto"] = df_pl["Ingresos"] + df_pl["Aprovisionamientos"]  # Compras son negativas
            df_pl["EBITDA"] = (df_pl["Margen Bruto"] + 
                             df_pl["Gastos de personal"] + 
                             df_pl["Otros gastos de explotación"])
            df_pl["Resultado Operativo"] = df_pl["EBITDA"] + df_pl["Otros resultados"]
            df_pl["Resultado Financiero"] = (df_pl["Ingresos financieros"] + 
                                           df_pl["Gastos financieros"] + 
                                           df_pl["Diferencias de cambio"])
            df_pl["Resultado Neto"] = df_pl["Resultado Operativo"] + df_pl["Resultado Financiero"]

            # Ordenar por fecha
            df_pl = df_pl.sort_values("🗓️ Año-Mes").fillna(0)

            # ====== 6. VISUALIZACIÓN ======
            st.success("✅ P&L procesado correctamente")
            
            # KPIs principales
            st.subheader("📈 KPIs Principales")
            totales = df_pl.select_dtypes(include=[float, int]).sum(numeric_only=True)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Ingresos Totales", f"${totales['Ingresos']:,.2f}")
            col2.metric("📊 Margen Bruto", f"${totales['Margen Bruto']:,.2f}")
            col3.metric("🎯 EBITDA", f"${totales['EBITDA']:,.2f}")
            col4.metric("💎 Resultado Neto", f"${totales['Resultado Neto']:,.2f}")

            # Ratios adicionales
            if totales['Ingresos'] > 0:
                col5, col6, col7, col8 = st.columns(4)
                col5.metric("Margen Bruto %", f"{(totales['Margen Bruto']/totales['Ingresos']*100):.1f}%")
                col6.metric("EBITDA %", f"{(totales['EBITDA']/totales['Ingresos']*100):.1f}%")
                col7.metric("Resultado Neto %", f"{(totales['Resultado Neto']/totales['Ingresos']*100):.1f}%")
                if totales['Gastos de personal'] < 0:
                    col8.metric("Gastos Personal %", f"{(abs(totales['Gastos de personal'])/totales['Ingresos']*100):.1f}%")

            # Tabla detallada
            st.subheader("📋 P&L Detallado por Mes")
            
            # Columnas a mostrar en el orden correcto
            display_cols = [
                "🗓️ Año-Mes", "Ingresos", "Aprovisionamientos", "Margen Bruto",
                "Gastos de personal", "Otros gastos de explotación", "EBITDA",
                "Otros resultados", "Resultado Operativo", "Ingresos financieros",
                "Gastos financieros", "Diferencias de cambio", "Resultado Financiero",
                "Resultado Neto"
            ]
            
            df_display = df_pl[display_cols].copy()
            
            # Formatear números
            numeric_cols = df_display.select_dtypes(include=[float, int]).columns
            for col in numeric_cols:
                df_display[col] = df_display[col].round(2)
            
            st.dataframe(df_display, use_container_width=True, height=400)

            # Gráfico de evolución
            st.subheader("📈 Evolución P&L")
            
            # Preparar datos para el gráfico
            chart_cols = [
                "🗓️ Año-Mes",
                "Ingresos",
                "Aprovisionamientos",
                "Margen Bruto",
                "Gastos de personal",
                "Otros gastos de explotación",
                "EBITDA",
                "Resultado Neto"
            ]
            
            chart_data = df_pl[chart_cols].melt(
                id_vars=["🗓️ Año-Mes"],
                var_name="Métrica",
                value_name="Valor"
            )
            
            if not chart_data.empty:
                chart = (
                    alt.Chart(chart_data)
                    .mark_line(point=True, strokeWidth=3)
                    .encode(
                        x=alt.X("🗓️ Año-Mes:O", title="Período"),
                        y=alt.Y("Valor:Q", title="Importe ($)"),
                        color=alt.Color("Métrica:N", scale=alt.Scale(scheme='category10')),
                        tooltip=["🗓️ Año-Mes:O", "Métrica:N", "Valor:Q"]
                    )
                    .properties(height=400, title="Evolución de Métricas P&L")
                )
                st.altair_chart(chart, use_container_width=True)

            # Gráfico de composición de gastos
            st.subheader("🥧 Composición de Gastos")
            
            gastos_cols = ["Aprovisionamientos", "Gastos de personal", "Otros gastos de explotación", "Gastos financieros"]
            gastos_totales = {}
            
            for col in gastos_cols:
                if col in df_pl.columns:
                    total = abs(df_pl[col].sum())
                    if total > 0:
                        gastos_totales[col] = total
            
            if gastos_totales:
                gastos_df = pd.DataFrame(list(gastos_totales.items()), columns=["Categoría", "Importe"])
                
                pie_chart = (
                    alt.Chart(gastos_df)
                    .mark_arc()
                    .encode(
                        theta=alt.Theta("Importe:Q"),
                        color=alt.Color("Categoría:N"),
                        tooltip=["Categoría:N", "Importe:Q"]
                    )
                    .properties(width=400, height=400, title="Distribución de Gastos")
                )
                st.altair_chart(pie_chart, use_container_width=True)

            # Detalle por cuenta si se solicita
            if mostrar_detalle and not usar_demo:
                st.subheader("🔍 Detalle por Cuenta Contable")
                
                # Combinar datos de compras y libro diario
                detalle_rows = []
                
                # Desde compras
                if 'df_comp' in locals() and not df_comp.empty:
                    for _, row in df_comp.iterrows():
                        detalle_rows.append({
                            "Período": row.get("🗓️ Año-Mes", ""),
                            "Cuenta": row.get("cuenta", "N/A"),
                            "Descripción": row.get("nombre_cuenta", ""),
                            "Categoría": row.get("categoria", ""),
                            "Importe": row.get("importe", 0),
                            "Origen": "Compras"
                        })
                
                # Desde libro diario
                if 'df_ledger' in locals() and not df_ledger.empty:
                    for _, row in df_ledger.iterrows():
                        detalle_rows.append({
                            "Período": row.get("🗓️ Año-Mes", ""),
                            "Cuenta": row.get("cuenta", "N/A"),
                            "Descripción": row.get("descripcion", ""),
                            "Categoría": row.get("categoria", ""),
                            "Importe": row.get("importe", 0),
                            "Origen": "Libro Diario"
                        })
                
                if detalle_rows:
                    df_detalle = pd.DataFrame(detalle_rows)
                    df_detalle["Importe"] = df_detalle["Importe"].round(2)
                    
                    # Filtros para el detalle
                    col_filter1, col_filter2 = st.columns(2)
                    
                    categorias_disponibles = ["Todas"] + sorted(df_detalle["Categoría"].unique().tolist())
                    cat_filter = col_filter1.selectbox("Filtrar por Categoría", categorias_disponibles)
                    
                    periodos_disponibles = ["Todos"] + sorted(df_detalle["Período"].unique().tolist())
                    periodo_filter = col_filter2.selectbox("Filtrar por Período", periodos_disponibles)
                    
                    # Aplicar filtros
                    df_filtered = df_detalle.copy()
                    if cat_filter != "Todas":
                        df_filtered = df_filtered[df_filtered["Categoría"] == cat_filter]
                    if periodo_filter != "Todos":
                        df_filtered = df_filtered[df_filtered["Período"] == periodo_filter]
                    
                    st.dataframe(df_filtered, use_container_width=True, height=400)
                    
                    # Resumen por categoría
                    if not df_filtered.empty:
                        resumen_cat = df_filtered.groupby("Categoría")["Importe"].sum().reset_index()
                        resumen_cat = resumen_cat.sort_values("Importe")
                        
                        st.subheader("📊 Resumen por Categoría")
                        
                        bar_chart = (
                            alt.Chart(resumen_cat)
                            .mark_bar()
                            .encode(
                                x=alt.X("Importe:Q", title="Importe ($)"),
                                y=alt.Y("Categoría:N", sort='-x', title="Categoría"),
                                color=alt.condition(
                                    alt.datum.Importe > 0,
                                    alt.value("steelblue"),
                                    alt.value("orange")
                                ),
                                tooltip=["Categoría:N", "Importe:Q"]
                            )
                            .properties(height=300)
                        )
                        st.altair_chart(bar_chart, use_container_width=True)
                else:
                    st.info("📋 No hay detalles por cuenta disponibles para mostrar.")

            # Exportar datos
            st.subheader("📥 Exportar Datos")
            
            col_exp1, col_exp2 = st.columns(2)
            
            # Exportar P&L resumido
            if not df_display.empty:
                csv_pl = df_display.to_csv(index=False)
                col_exp1.download_button(
                    label="💾 Descargar P&L (CSV)",
                    data=csv_pl,
                    file_name=f"pl_holded_{inicio_pl.strftime('%Y%m%d')}_{fin_pl.strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            # Exportar detalle si existe
            if mostrar_detalle and 'df_detalle' in locals() and not df_detalle.empty:
                csv_detalle = df_detalle.to_csv(index=False)
                col_exp2.download_button(
                    label="📋 Descargar Detalle (CSV)",
                    data=csv_detalle,
                    file_name=f"detalle_cuentas_{inicio_pl.strftime('%Y%m%d')}_{fin_pl.strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"❌ Error procesando P&L: {str(e)}")
        
        # Información adicional para debugging
        with st.expander("🔧 Información de Debug"):
            st.write("**Error completo:**")
            st.exception(e)
            
            st.write("**Variables disponibles:**")
            local_vars = locals()
            debug_vars = ['df_inv', 'df_pur', 'df_comp', 'df_ledger', 'df_pl']
            for var_name in debug_vars:
                if var_name in local_vars:
                    var_value = local_vars[var_name]
                    if hasattr(var_value, 'shape'):
                        st.write(f"- {var_name}: {type(var_value)}, Shape: {var_value.shape}")
                        if hasattr(var_value, 'columns'):
                            st.write(f"  Columnas: {list(var_value.columns)}")
                    else:
                        st.write(f"- {var_name}: {type(var_value)}")
            
            st.write("**Configuración:**")
            st.write(f"- Período: {inicio_pl} - {fin_pl}")
            st.write(f"- Usar libro diario: {usar_libro}")
            st.write(f"- Usar datos demo: {st.session_state.get('force_demo', False)}")
            st.write(f"- Token Holded disponible: {get_holded_token() is not None}")
            
        # Ofrecer datos de ejemplo como fallback
        if st.button("🧪 Cargar datos de ejemplo", key="fallback_demo"):
            st.session_state["force_demo"] = True
            st.rerun()

    # Información adicional
    with st.expander("ℹ️ Información sobre P&L"):
        st.markdown("""
        **📊 Métricas calculadas:**
        - **Ingresos**: Facturación de ventas del período
        - **Margen Bruto**: Ingresos - Aprovisionamientos (compras)
        - **EBITDA**: Margen Bruto - Gastos de personal - Otros gastos de explotación
        - **Resultado Operativo**: EBITDA + Otros resultados extraordinarios
        - **Resultado Neto**: Resultado Operativo + Resultado Financiero
        
        **🔄 Fuentes de datos:**
        - **Facturas de venta**: Para calcular ingresos por período
        - **Facturas de compra**: Para gastos categorizados por cuenta contable
        - **Libro diario contable**: Para refinamiento y gastos adicionales (nóminas, financieros, etc.)
        
        **📋 Clasificación automática de cuentas contables:**
        - **7xx**: Ingresos de explotación
        - **60x**: Aprovisionamientos (compras y consumos)
        - **64x**: Gastos de personal (sueldos, SS, etc.)
        - **66x/67x**: Gastos e ingresos financieros
        - **76x**: Ingresos financieros y diferencias de cambio
        - **Otros 6xx**: Otros gastos de explotación
        
        **🔧 Configuración necesaria:**
        
        Para conectar con Holded, configura en `st.secrets`:
        ```toml
        [holded]
        api_key = "tu-api-key-de-holded"
        ```
        
        **🧪 Modo Demo:**
        - Activa "Usar datos de ejemplo" para probar sin conexión a Holded
        - Los datos demo incluyen patrones realistas de ingresos y gastos
        - Útil para testing y presentaciones
        """)
        
        if usar_demo:
            st.success("🧪 **Modo Demo Activo** - Los datos mostrados son ejemplos para demostración")
        elif get_holded_token():
            st.success("✅ **Conectado a Holded** - Usando datos reales de tu cuenta")
        else:
            st.warning("⚠️ **Sin conexión a Holded** - Configura tu API key para usar datos reales")

# ====== FIN DEL CÓDIGO ======

# ====== FIN DEL CÓDIGO ======


