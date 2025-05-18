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

        # Selección de fecha única o rango
        default_dates = (date.today(), date.today())
        fecha = st.date_input(
            "📅 Selecciona fecha o rango de fechas",
            value=default_dates,
            key="fecha_tab2"
        )
        # Desempaquetar fecha; soportar tuplas o listas de dos fechas
        if isinstance(fecha, (tuple, list)) and len(fecha) == 2:
            start_date, end_date = fecha
        else:
            start_date = end_date = fecha

        # Normalizar fecha final si está vacía
        if end_date is None:
            end_date = start_date

        # Validar rango
        if end_date < start_date:
            st.warning("⚠️ La fecha final no puede ser anterior a la inicial.")
        else:
            # Selector de cliente
            clientes_df = consultar(
                "SELECT DISTINCT user_id, CONCAT(firstname,' ',lastname) AS nombre FROM plasma_core.users ORDER BY nombre ASC"
            )
            opciones_cliente = ["Todos"] + clientes_df["user_id"].dropna().astype(str).tolist()
            cliente_seleccionado = st.selectbox("🧍‍♂️ Selecciona Cliente por ID", opciones_cliente)

            # Botón de actualización
            actualizar = st.button("🔄 Actualizar", disabled=(not start_date or not end_date))

            if actualizar:
                filtro_cli = "" if cliente_seleccionado == "Todos" else f"AND user_id = '{cliente_seleccionado}'"

                if start_date == end_date:
                    # Modo fecha única: métricas individuales
                    fecha_str = start_date.strftime("%Y-%m-%d")
                    # ... (métricas del día) ...
                else:
                    # Modo rango de fechas: series y promedios
                    start_str = start_date.strftime("%Y-%m-%d")
                    end_str = end_date.strftime("%Y-%m-%d")

                    # Consulta de datos por día
                    df_altas_range = consultar(f"""
                        SELECT DATE(ts_creation) AS fecha, COUNT(*) AS nuevas_altas
                        FROM plasma_core.users
                        WHERE ts_creation BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_cli}
                        GROUP BY DATE(ts_creation) ORDER BY fecha
                    """)
                    df_depositos_range = consultar(f"""
                        SELECT DATE(ts_commit) AS fecha, COUNT(*) AS total_transacciones, AVG(amount) AS promedio_amount, SUM(amount) AS total_amount
                        FROM (
                          SELECT ts_commit, amount FROM plasma_payments.nico_transactions WHERE ts_commit BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_cli}
                          UNION ALL
                          SELECT ts_commit, amount FROM plasma_payments.payphone_transactions WHERE ts_commit BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {filtro_cli}
                        ) t GROUP BY DATE(ts_commit) ORDER BY fecha
                    """)
                    df_jugadores_range = consultar(f"""
                        SELECT DATE(re.ts) AS fecha, COUNT(DISTINCT s.user_id) AS jugadores, AVG(re.amount) AS importe_medio
                        FROM plasma_games.rounds_entries re
                        JOIN plasma_games.sessions s ON re.session_id=s.session_id
                        WHERE re.ts BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' AND re.`type`='BET' {filtro_cli.replace('user_id','s.user_id')}
                        GROUP BY DATE(re.ts) ORDER BY fecha
                    """)
                    df_ggr_range = consultar(f"""
                        SELECT fecha, SUM(total_bet) AS total_bet, SUM(total_win) AS total_win, SUM(total_bet)-SUM(total_win) AS ggr FROM (
                          SELECT DATE(ts) AS fecha, CASE WHEN `type`='BET' THEN amount ELSE 0 END AS total_bet, CASE WHEN `type`='WIN' THEN amount ELSE 0 END AS total_win
                          FROM plasma_games.rounds_entries WHERE ts BETWEEN '{start_str} 00:00:00' AND '{end_str} 23:59:59' {'' if cliente_seleccionado=='Todos' else f"AND session_id IN (SELECT session_id FROM plasma_games.sessions WHERE user_id='{cliente_seleccionado}')"}
                        ) t GROUP BY fecha ORDER BY fecha
                    """)
                    # Unir datos
                    df_range = pd.concat([
                        df_altas_range.set_index('fecha'),
                        df_depositos_range.set_index('fecha'),
                        df_jugadores_range.set_index('fecha'),
                        df_ggr_range.set_index('fecha')
                    ], axis=1).fillna(0)

                    # Gráficos individuales de totales diarios redondeados a 2 decimales
                    for col in ['nuevas_altas','total_transacciones','total_amount','jugadores','total_bet','total_win','ggr']:
                        st.subheader(f"📈 {col.replace('_',' ').title()} Diario")
                        st.line_chart(df_range[[col]].round(2))

                    # Gráficos individuales de promedios diarios redondeados a 2 decimales
                    for col in ['promedio_amount','importe_medio']:
                        st.subheader(f"📊 {col.replace('_',' ').title()} Diario")
                        st.line_chart(df_range[[col]].round(2))

                    # Promedio diario de cada KPI
                    st.subheader("📋 Promedio diario de cada KPI (periodo completo)")
                    st.bar_chart(df_range.mean().round(2))

                    # Sección de detalle por cliente y KPI
                    st.subheader("🔎 Top 20 Clientes por KPI")
                    fecha_detalle = st.selectbox(
                        "📅 Selecciona fecha para detalle",
                        df_range.index.astype(str),
                        key="fecha_detalle"
                    )
                    kpi_sql = None
                    kpi = st.selectbox(
                        "📊 Selecciona KPI para Top 20",
                        ['👥 Nuevas Altas', '💰 Depósitos (Total Transacciones)', '💵 Importe Medio Depósitos', '💳 Valor Total Depósitos', '🎮 Jugadores', '💸 Importe Medio Jugado', '🎯 Total BET', '🎯 Total WIN', '📊 GGR'],
                        key="kpi_detalle"
                    )
                    if st.button("Mostrar Top 20", key="boton_top20"):
                        if kpi == '👥 Nuevas Altas':
                            kpi_sql = f"""
                                SELECT user_id, COUNT(*) AS valor
                                FROM plasma_core.users
                                WHERE ts_creation BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' {filtro_cli}
                                GROUP BY user_id
                                ORDER BY valor DESC LIMIT 20
                            """
                        elif kpi == '💰 Depósitos (Total Transacciones)':
                            kpi_sql = f"""
                                SELECT user_id, COUNT(*) AS valor FROM (
                                    SELECT user_id, ts_commit FROM plasma_payments.nico_transactions
                                    WHERE ts_commit BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' {filtro_cli}
                                    UNION ALL
                                    SELECT user_id, ts_commit FROM plasma_payments.payphone_transactions
                                    WHERE ts_commit BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' {filtro_cli}
                                ) t GROUP BY user_id ORDER BY valor DESC LIMIT 20
                            """
                        elif kpi == '💵 Importe Medio Depósitos':
                            kpi_sql = f"""
                                SELECT user_id, AVG(amount) AS valor FROM (
                                    SELECT user_id, amount FROM plasma_payments.nico_transactions
                                    WHERE ts_commit BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' {filtro_cli}
                                    UNION ALL
                                    SELECT user_id, amount FROM plasma_payments.payphone_transactions
                                    WHERE ts_commit BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' {filtro_cli}
                                ) t GROUP BY user_id ORDER BY valor DESC LIMIT 20
                            """
                        elif kpi == '💳 Valor Total Depósitos':
                            kpi_sql = f"""
                                SELECT user_id, SUM(amount) AS valor FROM (
                                    SELECT user_id, amount FROM plasma_payments.nico_transactions
                                    WHERE ts_commit BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' {filtro_cli}
                                    UNION ALL
                                    SELECT user_id, amount FROM plasma_payments.payphone_transactions
                                    WHERE ts_commit BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' {filtro_cli}
                                ) t GROUP BY user_id ORDER BY valor DESC LIMIT 20
                            """
                        elif kpi == '🎮 Jugadores':
                            kpi_sql = f"""
                                SELECT u.user_id, COUNT(DISTINCT re.session_id) AS valor
                                FROM plasma_games.rounds_entries re
                                JOIN plasma_games.sessions s ON re.session_id=s.session_id
                                JOIN plasma_core.users u ON s.user_id=u.user_id
                                WHERE re.ts BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' AND re.`type`='BET' {filtro_cli.replace('user_id','u.user_id')}
                                GROUP BY u.user_id ORDER BY valor DESC LIMIT 20
                            """
                        elif kpi == '💸 Importe Medio Jugado':
                            kpi_sql = f"""
                                SELECT s.user_id, AVG(re.amount) AS valor
                                FROM plasma_games.rounds_entries re
                                JOIN plasma_games.sessions s ON re.session_id=s.session_id
                                WHERE re.ts BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' AND re.`type`='BET' {filtro_cli.replace('user_id','s.user_id')}
                                GROUP BY s.user_id ORDER BY valor DESC LIMIT 20
                            """
                        elif kpi == '🎯 Total BET':
                            kpi_sql = f"""
                                SELECT s.user_id, SUM(amount) AS valor
                                FROM plasma_games.rounds_entries re
                                JOIN plasma_games.sessions s ON re.session_id=s.session_id
                                WHERE re.ts BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' AND re.`type`='BET' {filtro_cli.replace('user_id','s.user_id')}
                                GROUP BY s.user_id ORDER BY valor DESC LIMIT 20
                            """
                        elif kpi == '🎯 Total WIN':
                            kpi_sql = f"""
                                SELECT s.user_id, SUM(amount) AS valor
                                FROM plasma_games.rounds_entries re
                                JOIN plasma_games.sessions s ON re.session_id=s.session_id
                                WHERE re.ts BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' AND re.`type`='WIN' {filtro_cli.replace('user_id','s.user_id')}
                                GROUP BY s.user_id ORDER BY valor DESC LIMIT 20
                            """
                        elif kpi == '📊 GGR':
                            kpi_sql = f"""
                                SELECT user_id, SUM(CASE WHEN `type`='BET' THEN amount ELSE 0 END) - SUM(CASE WHEN `type`='WIN' THEN amount ELSE 0 END) AS valor
                                FROM plasma_games.rounds_entries re
                                JOIN plasma_games.sessions s ON re.session_id=s.session_id
                               	WHERE re.ts BETWEEN '{fecha_detalle} 00:00:00' AND '{fecha_detalle} 23:59:59' {filtro_cli.replace('user_id','s.user_id')}
                                GROUP BY s.user_id ORDER BY valor DESC LIMIT 20
                            """
                        # Ejecutar y mostrar
                        if kpi_sql:
                            df_top = consultar(kpi_sql)
                            df_nombres = consultar("SELECT user_id, CONCAT(firstname,' ',lastname) AS nombre FROM plasma_core.users")
                            df_result = df_top.merge(df_nombres, on="user_id", how="left")
                            df_result = df_result.rename(columns={"valor": kpi})
                            st.table(df_result.round({kpi: 2}))
            except IndexError:
                st.warning("⚠️ No se pudo procesar la fecha seleccionada. Intenta con otra fecha o revisa la conexión a la base de datos.")
            except mysql.connector.Error as e:
                st.error(f"❌ Error de conexión con la base de datos: {e}")







