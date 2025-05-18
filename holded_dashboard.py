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
archivo = st.file_uploader("Sube el archivo Excel generado por Holded", type=["xlsx"])

# ===================
# 🧩 TABS PRINCIPALES
# ===================
tab1, tab2 = st.tabs(["📈 Márgenes Comerciales", "🧪 Datos Plataforma (DB)"])

with tab1:

    if archivo:
        df_raw = pd.read_excel(archivo, sheet_name="Holded", header=None)
    
        df_filtered = df_raw[df_raw[0].astype(str).str.startswith(("7", "6"), na=False)].copy()
        df_filtered["codigo"] = df_filtered[0].str.extract(r"^(\d+)")
        df_filtered["descripcion"] = df_filtered[0].astype(str).str.upper()
        df_filtered["tipo"] = df_filtered["codigo"].str[:3].map(lambda x: "ingreso" if x.startswith("705") else "gasto")
    
        def normalizar_cliente(texto):
            texto = str(texto).upper()
            texto = re.sub(r"\d{6,} - ", "", texto)  # elimina el código contable
            texto = re.sub(r"(PRESTACI[ÓO]N SERVICIOS BET593 -|TRABAJOS REALIZADOS POR)", "", texto)
            texto = re.sub(r"[^A-Z ]", "", texto)
            texto = re.sub(r"\s+", " ", texto).strip()
            return texto
    
        df_filtered["cliente_final"] = df_filtered["descripcion"].apply(normalizar_cliente)
    
        # Extraer meses desde fila 4 (índice 4), columnas 1 a 13
        meses = df_raw.iloc[4, 1:14].tolist()
    
        df_melted = df_filtered.melt(
            id_vars=["codigo", "cliente_final", "tipo"],
            value_vars=df_filtered.columns[1:14],
            var_name="mes_col_index",
            value_name="valor"
        )
        df_melted["mes"] = df_melted["mes_col_index"].apply(lambda col: meses[col - 1] if 1 <= col <= len(meses) else None)
    
        df_melted = df_melted.dropna(subset=["valor"])
        df_melted["valor"] = pd.to_numeric(df_melted["valor"], errors="coerce").fillna(0)
    
        df_agg = df_melted.groupby(["cliente_final", "mes", "tipo"])["valor"].sum().reset_index()
    
        df_pivot = df_agg.pivot_table(index=["cliente_final", "mes"], columns="tipo", values="valor", fill_value=0).reset_index()
        # Lista oficial normalizada
        clientes_oficiales = [
            "METRONIA S.A", "LOTTERY (No proveedor)", "OCTAVIAN SRL", "VITAL GAMES PROJECT SLOT SRL",
            "PIN-PROJEKT D.O.O", "APOLLO SOFT,S.R.O.", "PSM TECH S.r.l.", "SEVEN A.B.C SOLUTION CH",
            "PROJEKT SERVICE SRL", "MYMOON LTD", "WORLDMATCH,SRL", "ARRISE SOLUTIONS LIMITED",
            "STREET WEB SRL", "TALENTA LABS SRL", "EVOPLAY ENTERTAIMENT LTD", "SAMINO GAMING NV",
            "ANAKATECH", "ALTENAR SOFTWARE LIMITED", "MIRAGE CORPORATION NV", "EDICT MALTA LIMITED",
            "MONGIBELLO TECH SRL", "AD CONSULTING S.P.A.", "GAMIFY TECH OOD"
        ]
        clientes_oficiales_upper = [c.upper() for c in clientes_oficiales]
        
        # Corrección manual explícita (cuando fuzzy no sirve)
        mapeo_manual = {
            "ALTENAR BET": "ALTENAR SOFTWARE LIMITED",
            "VITALGAMES": "VITAL GAMES PROJECT SLOT SRL",
            "SAMINO": "SAMINO GAMING NV",
            "SEVEN ABC": "SEVEN A.B.C SOLUTION CH",
            "AD CONSULTING BET": "AD CONSULTING S.P.A.",
            "MONGIBELLO": "MONGIBELLO TECH SRL",
        }
        
        def normalizar(texto):
            texto = str(texto).upper()
            texto = re.sub(r"\d{6,} - ", "", texto)
            texto = re.sub(r"(PRESTACI[ÓO]N SERVICIOS BET593 -|TRABAJOS REALIZADOS POR)", "", texto)
            texto = re.sub(r"[^A-Z ]", "", texto)
            texto = re.sub(r"\s+", " ", texto).strip()
            return texto
        
        def mapear_cliente_final(nombre):
            normal = normalizar(nombre)
            # Paso 1: corrección manual directa
            for key, value in mapeo_manual.items():
                if key in normal:
                    return value
            # Paso 2: fuzzy match
            match = difflib.get_close_matches(normal, clientes_oficiales_upper, n=1, cutoff=0.4)
            return match[0] if match else normal
        
        # Aplica al DataFrame
        df_pivot["cliente_final"] = df_pivot["cliente_final"].apply(mapear_cliente_final)
        if "ingreso" not in df_pivot.columns:
            df_pivot["ingreso"] = 0
        if "gasto" not in df_pivot.columns:
            df_pivot["gasto"] = 0
        df_pivot["margen"] = df_pivot["ingreso"] - abs(df_pivot["gasto"])
        mes_limpio = df_pivot["mes"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        df_pivot[["mes_nombre", "año"]] = mes_limpio.str.extract(r"([A-Za-záéíóúÁÉÍÓÚñÑ]+)\s+(\d+)", expand=True)
        
    
        meses_dict = {
            "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
            "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
            "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
        }
        df_pivot["año"] = pd.to_numeric(df_pivot["año"], errors="coerce").fillna(0).astype(int)
        df_pivot["año"] = df_pivot["año"].apply(lambda x: 2000 + x if x < 100 else x)
    
        df_pivot["mes_num"] = df_pivot["mes_nombre"].replace(meses_dict)
        df_pivot["año"] = pd.to_numeric(df_pivot["año"], errors="coerce").fillna(0).astype(int)
        df_pivot = df_pivot[df_pivot["año"] > 0]
    
    
        df_pivot = df_pivot[
            df_pivot["mes_num"].between(1, 12) &
            df_pivot["año"].between(2020, 2100)
        ]
        
        df_pivot["mes_num"] = df_pivot["mes_num"].astype(int)
        df_pivot["año"] = df_pivot["año"].astype(int)
        
        df_pivot["fecha_orden"] = pd.to_datetime({
            "year": df_pivot["año"],
            "month": df_pivot["mes_num"],
            "day": 1
        }, errors='coerce')
        
    
        if df_pivot["fecha_orden"].notna().any():
            fecha_min = df_pivot["fecha_orden"].min()
            fecha_max = df_pivot["fecha_orden"].max()
        
            st.sidebar.header("Filtros")
            fecha_rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])
            
            clientes_unicos = sorted(df_pivot["cliente_final"].unique())
            cliente_opcion = st.sidebar.selectbox("Selecciona un cliente", ["Todos"] + clientes_unicos)
            
            try:
                df_filtro = df_pivot[
                    (df_pivot["fecha_orden"] >= pd.to_datetime(fecha_rango[0])) &
                    (df_pivot["fecha_orden"] <= pd.to_datetime(fecha_rango[1]))
                ]
            
                if cliente_opcion != "Todos":
                    df_filtro = df_filtro[df_filtro["cliente_final"] == cliente_opcion]
            
                st.metric("💰 Margen Total", f"${df_filtro['margen'].sum():,.2f}")
                st.subheader("📊 Margen por Cliente")
                st.dataframe(df_filtro.groupby("cliente_final")[["ingreso", "gasto", "margen"]].sum().sort_values("margen", ascending=False))
            
                st.subheader("📈 Gráfico de Márgenes")
                st.bar_chart(df_filtro.groupby("cliente_final")["margen"].sum())
            
            except IndexError:
                st.warning("⚠️ Selecciona un rango de fechas válido para aplicar el filtro.")
    else:
        st.info("⬆️ Por favor, sube un archivo Excel para continuar.")


with tab2:
    with st.container():
        st.header("📊 Métricas de la Plataforma de Juego")

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
                st.error(f"❌ Error de conexión con la base de datos: {e}")
                return pd.DataFrame()

        # Selección de fecha única o rango
        today = date.today()
        fecha = st.date_input(
            "📅 Selecciona fecha o rango de fechas",
            value=(today, today),
            min_value=date(2000, 1, 1),
            max_value=today,
            key="fecha_tab2"
        )
        if isinstance(fecha, (tuple, list)) and len(fecha) == 2:
            start_date, end_date = fecha
        else:
            start_date = end_date = fecha
        if end_date < start_date:
            st.error("⚠️ La fecha final debe ser igual o posterior a la inicial.")

        # Selector de cliente
        clientes_df = consultar(
            "SELECT DISTINCT user_id FROM plasma_core.users ORDER BY user_id"
        )
        opciones_cliente = ["Todos"] + clientes_df["user_id"].astype(str).tolist()
        cliente = st.selectbox("🧍‍♂️ Selecciona Cliente", opciones_cliente)

        # Botón de actualización
        actualizar = st.button("🔄 Actualizar", disabled=(end_date < start_date))

        if actualizar:
            # Filtros según cliente
            filtro_altas = "" if cliente == 'Todos' else f"AND user_id = '{cliente}'"
            filtro_dep = filtro_altas
            filtro_jug = "" if cliente == 'Todos' else f"AND s.user_id = '{cliente}'"
            filtro_ggr = "" if cliente == 'Todos' else f"AND session_id IN (SELECT session_id FROM plasma_games.sessions WHERE user_id = '{cliente}')"

            # Cálculo de df_range
            if start_date == end_date:
                # Datos de un día
                fecha_str = start_date.strftime("%Y-%m-%d")
                df_altas = consultar(f"""
                    SELECT COUNT(*) AS nuevas_altas
                    FROM plasma_core.users
                    WHERE ts_creation BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' {filtro_altas}
                """)
                df_depos = consultar(f"""
                    SELECT COUNT(*) AS total_transacciones, AVG(amount) AS promedio_amount, SUM(amount) AS total_amount
                    FROM (
                      SELECT amount, user_id FROM plasma_payments.nico_transactions WHERE ts_commit BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' {filtro_dep}
                      UNION ALL
                      SELECT amount, user_id FROM plasma_payments.payphone_transactions WHERE ts_commit BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' {filtro_dep}
                    ) t
                """)
                df_jug = consultar(f"""
                    SELECT COUNT(DISTINCT re.session_id) AS jugadores, AVG(re.amount) AS importe_medio
                    FROM plasma_games.rounds_entries re
                    JOIN plasma_games.sessions s ON re.session_id=s.session_id
                    WHERE re.ts BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' AND re.`type`='BET' {filtro_jug}
                """)
                df_ggr = consultar(f"""
                    SELECT SUM(CASE WHEN `type`='BET' THEN amount ELSE 0 END) AS total_bet,
                           SUM(CASE WHEN `type`='WIN' THEN amount ELSE 0 END) AS total_win,
                           SUM(CASE WHEN `type`='BET' THEN amount ELSE 0 END) - SUM(CASE WHEN `type`='WIN' THEN amount ELSE 0 END) AS ggr
                    FROM plasma_games.rounds_entries
                    WHERE ts BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59' {filtro_ggr}
                """)
                # Un solo punto
                df_range = pd.DataFrame({
                    'nuevas_altas': [df_altas.iloc[0,0]],
                    'total_transacciones': [df_depos.iloc[0]['total_transacciones']],
                    'promedio_amount': [df_depos.iloc[0]['promedio_amount'] or 0],
                    'total_amount': [df_depos.iloc[0]['total_amount'] or 0],
                    'jugadores': [df_jug.iloc[0]['jugadores']],
                    'importe_medio': [df_jug.iloc[0]['importe_medio'] or 0],
                    'total_bet': [df_ggr.iloc[0]['total_bet']],
                    'total_win': [df_ggr.iloc[0]['total_win']],
                    'ggr': [df_ggr.iloc[0]['ggr']],
                }, index=[fecha_str])
            else:
                # Serie en rango
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                # Query por día
                df_altas = consultar(f"""
                    SELECT DATE(ts_creation) AS fecha, COUNT(*) AS nuevas_altas
                    FROM plasma_core.users
                    WHERE ts_creation BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_altas}
                    GROUP BY fecha ORDER BY fecha
                """)
                df_depos = consultar(f"""
                    SELECT DATE(ts_commit) AS fecha, COUNT(*) AS total_transacciones, AVG(amount) AS promedio_amount, SUM(amount) AS total_amount
                    FROM (
                      SELECT ts_commit, amount FROM plasma_payments.nico_transactions WHERE ts_commit BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_dep}
                      UNION ALL
                      SELECT ts_commit, amount FROM plasma_payments.payphone_transactions WHERE ts_commit BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_dep}
                    ) t
                    GROUP BY fecha ORDER BY fecha
                """)
                df_jug = consultar(f"""
                    SELECT DATE(re.ts) AS fecha, COUNT(DISTINCT re.session_id) AS jugadores, AVG(re.amount) AS importe_medio
                    FROM plasma_games.rounds_entries re
                    JOIN plasma_games.sessions s ON re.session_id=s.session_id
                    WHERE re.ts BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' AND re.`type`='BET' {filtro_jug}
                    GROUP BY fecha ORDER BY fecha
                """)
                df_ggr = consultar(f"""
                    SELECT DATE(re.ts) AS fecha, SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END) AS total_bet,
                           SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END) AS total_win,
                           SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END)-SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END) AS ggr
                    FROM plasma_games.rounds_entries re
                    WHERE re.ts BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_ggr}
                    GROUP BY fecha ORDER BY fecha
                """)
                # Índice completo y merge
                date_index = pd.date_range(start_str, end_str, freq='D')
                for df_tmp in (df_altas, df_depos, df_jug, df_ggr):
                    df_tmp['fecha'] = pd.to_datetime(df_tmp['fecha'])
                df_range = pd.DataFrame(index=date_index)
                df_range = df_range.join(df_altas.set_index('fecha')).join(df_depos.set_index('fecha'))
                df_range = df_range.join(df_jug.set_index('fecha')).join(df_ggr.set_index('fecha')).fillna(0)
            # Guardar
            st.session_state['df_range'] = df_range

            # Mostrar gráficos sin zoom
            for col in df_range.columns:
                title = col.replace('_', ' ').title()
                st.subheader(title)
                df_plot = df_range[[col]].reset_index().rename(columns={'index': 'Fecha', col: title})
                chart = alt.Chart(df_plot).mark_line().encode(
                    x='Fecha:T',
                    y=alt.Y(f'{title}:Q', title=title)
                ).properties(width=600, height=300)
                st.altair_chart(chart, use_container_width=True)


        # Sección Top 20 Clientes por KPI (siempre todos)
        if 'df_range' in st.session_state:
            df_range = st.session_state['df_range']
            st.markdown("---")
            st.header("🔎 Top 20 Clientes por KPI")
            fecha_detalle = st.selectbox(
                "📅 Fecha detalle",
                df_range.index.astype(str).tolist(),
                key="det_fecha"
            )
            kpi_map = {
                '👥 Nuevas Altas':    ("COUNT(*)",                     "plasma_core.users",             "ts_creation"),
                '💰 Depósitos Tot.':   ("COUNT(*)",                     "nico_transactions/payphone_transactions", "ts_commit"),
                '💵 Importe Medio Depósito': ("AVG(amount)",             "nico_transactions/payphone_transactions", "ts_commit"),
                '💳 Valor Total Depósito':   ("SUM(amount)",            "nico_transactions/payphone_transactions", "ts_commit"),
                '🎮 Jugadores':        ("COUNT(DISTINCT re.session_id)", "rounds_entries",               "ts"),
                '💸 Importe Medio Jugado':    ("AVG(re.amount)",           "rounds_entries",               "ts"),
                '🎯 Total BET':        ("SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END)", "rounds_entries", "ts"),
                '🎯 Total WIN':        ("SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END)", "rounds_entries", "ts"),
                '📊 GGR':              ("SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END)-SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END)", "rounds_entries", "ts")
            }
            kpi = st.selectbox("📊 KPI", list(kpi_map.keys()), key="det_kpi")
            if st.button("Mostrar Top 20", key="det_boton"):
                agg, tbl, ts_col = kpi_map[kpi]
                if tbl == "plasma_core.users":
                    sql = f"""
                        SELECT user_id, {agg} AS valor
                        FROM plasma_core.users
                        WHERE DATE({ts_col}) = '{fecha_detalle}'
                        GROUP BY user_id ORDER BY valor DESC LIMIT 20
                    """
                elif "nico_transactions" in tbl:
                    sql = f"""
                        SELECT user_id, {agg} AS valor FROM (
                            SELECT user_id, amount, ts_commit FROM plasma_payments.nico_transactions WHERE DATE(ts_commit) = '{fecha_detalle}'
                            UNION ALL
                            SELECT user_id, amount, ts_commit FROM plasma_payments.payphone_transactions WHERE DATE(ts_commit) = '{fecha_detalle}'
                        ) t GROUP BY user_id ORDER BY valor DESC LIMIT 20
                    """
                else:
                    tipo = 'BET' if 'BET' in kpi else 'WIN' if 'WIN' in kpi else ''
                    sql = f"""
                        SELECT s.user_id, {agg} AS valor
                        FROM plasma_games.rounds_entries re
                        JOIN plasma_games.sessions s ON re.session_id=s.session_id
                        WHERE DATE(re.{ts_col}) = '{fecha_detalle}' AND re.`type`='{tipo}'
                        GROUP BY s.user_id ORDER BY valor DESC LIMIT 20
                    """
                df_top = consultar(sql)
                df_top = df_top.set_index('user_id')
                st.table(df_top.round(2))






