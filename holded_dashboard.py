import streamlit as st
import pandas as pd
import re
import difflib
import mysql.connector
from datetime import datetime
from datetime import date
import altair as alt
st.set_page_config(page_title="Dashboard de Márgenes", layout="wide")
st.title("📊 Dashboard Interactivo Holded-Financiero")

# ===================
# 📁 SUBIR ARCHIVO
# ===================
import requests
import pandas as pd
import streamlit as st

API_KEY = "fafbb8191b37e6b696f192e70b4a198c"
HEADERS = {
    "accept": "application/json",
    "key": API_KEY
}


# ===================
# 🧩 TABS PRINCIPALES
# ===================
tab1, tab2, tab3 = st.tabs(["📈 Márgenes Comerciales", "🧪 Datos Plataforma (DB)", "📑 P&L Holded (API)"])

with tab1:
    HEADERS = {"accept": "application/json", "key": API_KEY}
    # =============================
    # 📦 FUNCIONES DE CARGA
    # =============================

    @st.cache_data(ttl=3600)
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

    # -- Formulario de filtros --
    with st.form("filtros"):
        today = date.today()
        fechas = st.date_input(
            "📅 Selecciona fecha o rango de fechas",
            value=st.session_state.get("fechas", (today, today)),
            min_value=date(2000, 1, 1),
            max_value=today,
            key="fecha_tab2"
        )
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

# ====== Helpers Holded P&L (puedes subirlos a la sección superior del script) ======
import requests
import pandas as pd
from datetime import datetime
import streamlit as st

BASE_INV = "https://api.holded.com/api/invoicing/v1"
BASE_ACC = "https://api.holded.com/api/accounting/v1"
HEADERS = {"accept": "application/json", "key": API_KEY}

@st.cache_data(ttl=3600)
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

@st.cache_data(ttl=3600)
def get_document_detail(doc_type: str, doc_id: str):
    """Detalle de documento (para leer líneas y cuentas, si están disponibles)."""
    url = f"{BASE_INV}/documents/{doc_type}/{doc_id}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else None

@st.cache_data(ttl=3600)
def list_chart_of_accounts():
    """Plan de cuentas de Holded (si tienes contabilidad activa)."""
    url = f"{BASE_ACC}/chartofaccounts"
    r = requests.get(url, headers=HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else []

@st.cache_data(ttl=3600)
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

# ====== UI del Tab 3: P&L desde Holded ======
with tab3:
    st.header("📑 P&L Holded (API)")
    st.caption("Calculado desde documentos de Holded y (opcional) libro diario contable para mayor precisión.")

    # Rango de fechas (reutilizamos el sidebar del Tab 1 si quieres; aquí lo hacemos local)
    colA, colB = st.columns(2)
    hoy = datetime.today()
    inicio_pl = colA.date_input("📅 Inicio", value=hoy.replace(day=1))
    fin_pl    = colB.date_input("📅 Fin", value=hoy)
    inicio_pl = datetime(inicio_pl.year, inicio_pl.month, inicio_pl.day)
    fin_pl    = datetime(fin_pl.year, fin_pl.month, fin_pl.day, 23, 59, 59)

    usar_libro = st.toggle("🔎 Usar contabilidad (Libro diario) si está disponible", value=True)

    # 1) Ventas (Ingresos) por mes
    df_inv = list_documents("invoice", inicio_pl, fin_pl)
    if df_inv.empty:
        st.warning("No se encontraron facturas de venta en el rango.")
    df_inv["_fecha"] = pd.to_datetime(df_inv.get("date"), unit="s", errors="coerce")
    df_inv["_ym"] = df_inv["_fecha"].dt.to_period("M").astype(str)
    df_inv["importe"] = pd.to_numeric(df_inv.get("subTotal"), errors="coerce").fillna(pd.to_numeric(df_inv.get("total"), errors="coerce")).fillna(0.0)
    ingresos_mes = df_inv.groupby("_ym")["importe"].sum().rename("Ingresos").reset_index()

    # 2) Compras: intentamos desglosar por cuenta leyendo líneas
    df_pur = list_documents("purchase", inicio_pl, fin_pl)
    compras_rows = []
    for _, row in df_pur.iterrows():
        det = get_document_detail("purchase", str(row.get("id") or row.get("_id") or row.get("docId") or ""))
        for (fecha, acct, acct_name, amt) in parse_purchase_lines(det):
            ym = pd.to_datetime(fecha).to_period("M").astype(str) if pd.notna(fecha) else pd.to_datetime(row.get("date"), unit="s", errors="coerce").to_period("M").astype(str)
            cat = classify_account(str(acct), acct_name)
            compras_rows.append({"🗓️ Año-Mes": ym, "cuenta": acct, "nombre_cuenta": acct_name, "categoria": cat, "importe": amt})

    df_comp = pd.DataFrame(compras_rows)
    if df_comp.empty:
        # fallback: si no hay líneas, tratamos todo como Otros gastos de explotación
        df_pur["_fecha"] = pd.to_datetime(df_pur.get("date"), unit="s", errors="coerce")
        df_pur["_ym"] = df_pur["_fecha"].dt.to_period("M").astype(str)
        df_comp = df_pur.groupby("_ym").apply(lambda g: pd.Series({"categoria": "Otros gastos de explotación", "importe": -abs(pd.to_numeric(g.get("total"), errors="coerce").fillna(0).sum())})).reset_index().rename(columns={"_ym":"🗓️ Año-Mes"})

    # 3) (Opcional) Libro diario para afinar categorías (personal, financieros, etc.)
    ledger_rows = []
    if usar_libro:
        asientos = list_daily_ledger(inicio_pl, fin_pl)
        for a in asientos:
            fecha = a.get("date") or a.get("ts")
            fecha = pd.to_datetime(fecha, errors="coerce")
            ym = fecha.to_period("M").astype(str) if pd.notna(fecha) else None
            # campos comunes: accountCode/account/name y amounts (debit/credit/amount)
            acct_code = str(a.get("accountCode") or a.get("account") or "")
            acct_name = str(a.get("accountName") or "")
            # importe: intentamos 'amount' y si no, debit - credit
            amt = a.get("amount", None)
            if amt is None:
                debit = a.get("debit", 0) or 0
                credit = a.get("credit", 0) or 0
                amt = float(debit) - float(credit)
            cat = classify_account(acct_code, acct_name)
            if ym:
                ledger_rows.append({"🗓️ Año-Mes": ym, "categoria": cat, "importe": float(amt)})
    df_ledger = pd.DataFrame(ledger_rows)

    # 4) Agregación por KPI P&L
    # Base: Ingresos desde facturas + gastos desde compras (si activamos libro, lo usamos para refinar y sumar también financieros y personal)
    # Empezamos con facturación:
    base = ingresos_mes.rename(columns={"_ym":"🗓️ Año-Mes"}).copy()
    # Gastos (compras por categoría)
    comp_piv = df_comp.groupby(["🗓️ Año-Mes","categoria"])["importe"].sum().unstack(fill_value=0).reset_index()
    for col in ["Aprovisionamientos","Gastos de personal","Otros gastos de explotación","Ingresos financieros","Gastos financieros","Diferencias de cambio","Otros resultados"]:
        if col not in comp_piv.columns:
            comp_piv[col] = 0.0
    df_pl = base.merge(comp_piv, on="🗓️ Año-Mes", how="outer").fillna(0)

    # Si hay libro diario, sumamos/sobrescribimos por categoría (prioridad contable)
    if not df_ledger.empty:
        add = df_ledger.groupby(["🗓️ Año-Mes","categoria"])["importe"].sum().unstack(fill_value=0).reset_index()
        for col in add.columns:
            if col != "🗓️ Año-Mes":
                # sumamos (libro puede incluir nóminas, financieros, dif. de cambio que no estarán en compras)
                df_pl[col] = df_pl.get(col, 0) + add[col]

    # KPIs derivados
    for c in ["Ingresos","Aprovisionamientos","Gastos de personal","Otros gastos de explotación","Ingresos financieros","Gastos financieros","Diferencias de cambio","Otros resultados"]:
        if c not in df_pl.columns:
            df_pl[c] = 0.0

    df_pl["Margen Bruto"] = df_pl["Ingresos"] + df_pl["Aprovisionamientos"]  # compras negativas
    df_pl["EBITDA aprox"] = df_pl["Margen Bruto"] + df_pl["Gastos de personal"] + df_pl["Otros gastos de explotación"]
    df_pl["Resultado antes de finanzas"] = df_pl["EBITDA aprox"] + df_pl["Otros resultados"]
    df_pl["Resultado neto aprox"] = (df_pl["Resultado antes de finanzas"]
                                     + df_pl["Ingresos financieros"]
                                     + df_pl["Gastos financieros"]
                                     + df_pl["Diferencias de cambio"])

    df_pl = df_pl.sort_values("🗓️ Año-Mes")
    st.subheader("KPIs P&L")
    tot = df_pl.select_dtypes(include=[float,int]).sum(numeric_only=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingresos", f"${tot['Ingresos']:,.2f}")
    col2.metric("Margen Bruto", f"${tot['Margen Bruto']:,.2f}")
    col3.metric("EBITDA aprox", f"${tot['EBITDA aprox']:,.2f}")
    col4.metric("Resultado neto aprox", f"${tot['Resultado neto aprox']:,.2f}")

    st.subheader("Detalle por mes")
    mostrar_cols = ["🗓️ Año-Mes","Ingresos","Aprovisionamientos","Gastos de personal","Otros gastos de explotación",
                    "Margen Bruto","EBITDA aprox","Otros resultados","Ingresos financieros","Gastos financieros",
                    "Diferencias de cambio","Resultado antes de finanzas","Resultado neto aprox"]
    st.dataframe(df_pl[mostrar_cols], use_container_width=True)

    st.subheader("Evolución")
    import altair as alt
    evo = df_pl.melt(id_vars=["🗓️ Año-Mes"], value_vars=["Ingresos","Margen Bruto","EBITDA aprox","Resultado neto aprox"],
                     var_name="KPI", value_name="Valor")
    chart = (alt.Chart(evo)
                .mark_line(point=True)
                .encode(x="🗓️ Año-Mes:O", y="Valor:Q", color="KPI:N", tooltip=["🗓️ Año-Mes","KPI","Valor:Q"])
                .properties(height=320))
    st.altair_chart(chart, use_container_width=True)

