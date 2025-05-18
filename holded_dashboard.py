import streamlit as st
import pandas as pd
import re
import difflib
import mysql.connector
from datetime import datetime
from datetime import date

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
        st.header("📊 Métricas de la Plataforma de Juego (Fecha o Rango de Fechas)")

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

        # Fecha única o rango
        default_dates = (date.today(), date.today())
        fecha = st.date_input(
            "📅 Selecciona fecha o rango de fechas",
            value=default_dates,
            key="fecha_tab2"
        )
        if isinstance(fecha, (tuple, list)) and len(fecha) == 2:
            start_date, end_date = fecha
        else:
            start_date = end_date = fecha
        if end_date is None:
            end_date = start_date

        if end_date < start_date:
            st.warning("⚠️ La fecha final no puede ser anterior a la inicial.")
        else:
            # Selección de cliente y actualización
            clientes_df = consultar(
                "SELECT DISTINCT user_id, CONCAT(firstname,' ',lastname) AS nombre FROM plasma_core.users ORDER BY nombre ASC"
            )
            opciones_cliente = ["Todos"] + clientes_df["user_id"].astype(str).tolist()
            cliente_seleccionado = st.selectbox("🧍‍♂️ Cliente", opciones_cliente)
            if st.button("🔄 Actualizar"):
                filtro_cli = "" if cliente_seleccionado == "Todos" else f"AND re.user_id = '{cliente_seleccionado}'"
                start_str, end_str = start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

                # Consultas diarias
                df_altas = consultar(f"""
                    SELECT DATE(ts_creation) AS fecha, COUNT(*) AS nuevas_altas
                    FROM plasma_core.users
                    WHERE ts_creation BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_cli.replace('re.user_id','')}
                    GROUP BY fecha ORDER BY fecha
                """)
                df_depositos = consultar(f"""
                    SELECT DATE(ts_commit) AS fecha,
                           COUNT(*) AS total_transacciones,
                           AVG(amount) AS promedio_amount,
                           SUM(amount) AS total_amount
                    FROM (
                      SELECT ts_commit, amount, user_id FROM plasma_payments.nico_transactions
                      WHERE ts_commit BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_cli.replace('re.user_id','user_id')}
                      UNION ALL
                      SELECT ts_commit, amount, user_id FROM plasma_payments.payphone_transactions
                      WHERE ts_commit BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_cli.replace('re.user_id','user_id')}
                    ) t
                    GROUP BY fecha ORDER BY fecha
                """)
                df_jugadores = consultar(f"""
                    SELECT DATE(re.ts) AS fecha,
                           COUNT(DISTINCT re.session_id) AS jugadores,
                           AVG(re.amount) AS importe_medio
                    FROM plasma_games.rounds_entries re
                    JOIN plasma_games.sessions s ON re.session_id = s.session_id
                    WHERE re.ts BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_cli}
                    GROUP BY fecha ORDER BY fecha
                """)
                df_ggr = consultar(f"""
                    SELECT DATE(re.ts) AS fecha,
                           SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END) AS total_bet,
                           SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END) AS total_win,
                           SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END)
                           - SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END) AS ggr
                    FROM plasma_games.rounds_entries re
                    WHERE re.ts BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_cli}
                    GROUP BY fecha ORDER BY fecha
                """)

                # Consolidar rango
                df_range = pd.concat([
                    df_altas.set_index('fecha'),
                    df_depositos.set_index('fecha'),
                    df_jugadores.set_index('fecha'),
                    df_ggr.set_index('fecha')
                ], axis=1).fillna(0)
                st.session_state['df_range'] = df_range
                st.session_state['filtro_cli'] = filtro_cli
                import altair as alt

                # Mostrar gráficos con títulos
                for col in df_range.columns:
                    title = col.replace('_',' ').title()
                    st.markdown(f"**{title}**")
                    # Preparo el DataFrame para Altair
                    df_plot = (
                        df_range[[col]]
                        .reset_index()
                        .rename(columns={'fecha': 'Fecha', col: title})
                    )
                    chart = (
                        alt.Chart(df_plot)
                        .mark_line()
                        .encode(
                            x='Fecha:T',
                            y=alt.Y(f'{title}:Q', title=title)
                        )
                        .properties(width=600, height=300)
                    )
                    st.altair_chart(chart, use_container_width=True)

        # Top 20 Clientes por KPI
        if 'df_range' in st.session_state:
            df_range = st.session_state['df_range']
            filtro_cli = st.session_state['filtro_cli']
            st.markdown("---")
            st.header("🔎 Top 20 Clientes por KPI")
            fecha_detalle = st.selectbox("📅 Fecha detalle", df_range.index.astype(str).tolist(), key="k_fecha")
            kpi_map = {
                '👥 Nuevas Altas': ("COUNT(*)","plasma_core.users","ts_creation"),
                '💰 Depósitos Tot.': ("COUNT(*)","nico","ts_commit"),
                '💵 Importe Medio Depósito': ("AVG(amount)","nico","ts_commit"),
                '💳 Valor Total Depósito': ("SUM(amount)","nico","ts_commit"),
                '🎮 Jugadores': ("COUNT(DISTINCT re.session_id)","re","ts"),
                '💸 Importe Medio Jugado': ("AVG(re.amount)","re","ts"),
                '🎯 Total BET': ("SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END)","re","ts"),
                '🎯 Total WIN': ("SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END)","re","ts"),
                '📊 GGR': ("SUM(CASE WHEN re.`type`='BET' THEN re.amount ELSE 0 END) - SUM(CASE WHEN re.`type`='WIN' THEN re.amount ELSE 0 END)", "re", "ts")

            }
            kpi = st.selectbox("📊 KPI", list(kpi_map.keys()), key="k_kpi")
            if st.button("Mostrar Top 20", key="b_top"):
                agg, tbl, ts_col = kpi_map[kpi]
                if tbl == 'plasma_core.users':
                    sql = f"""
                        SELECT user_id, {agg} AS valor
                        FROM plasma_core.users
                        WHERE DATE({ts_col}) = '{fecha_detalle}' {filtro_cli.replace('re.user_id','')}
                        GROUP BY user_id ORDER BY valor DESC LIMIT 20
                    """
                elif tbl == 'nico':
                    sql = f"""
                        SELECT user_id, {agg} AS valor FROM (
                            SELECT user_id, amount, ts_commit FROM plasma_payments.nico_transactions
                            WHERE DATE(ts_commit) = '{fecha_detalle}' {filtro_cli.replace('re.user_id','user_id')}
                            UNION ALL
                            SELECT user_id, amount, ts_commit FROM plasma_payments.payphone_transactions
                            WHERE DATE(ts_commit) = '{fecha_detalle}' {filtro_cli.replace('re.user_id','user_id')}
                        ) t GROUP BY user_id ORDER BY valor DESC LIMIT 20
                    """
                else:
                    sql = f"""
                        SELECT s.user_id, {agg} AS valor
                        FROM plasma_games.rounds_entries re
                        JOIN plasma_games.sessions s ON re.session_id=s.session_id
                        WHERE DATE(re.{ts_col}) = '{fecha_detalle}' {filtro_cli}
                        GROUP BY s.user_id ORDER BY valor DESC LIMIT 20
                    """
                df_top = consultar(sql)
                df_names = consultar("SELECT user_id, CONCAT(firstname,' ',lastname) AS nombre FROM plasma_core.users")
                df_merge = df_top.merge(df_names, on="user_id", how="left").set_index('user_id')
                st.table(df_merge.rename(columns={'valor': kpi}).round(2))











