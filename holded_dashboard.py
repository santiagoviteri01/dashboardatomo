import streamlit as st
import pandas as pd
import re
import difflib
import mysql.connector
from datetime import datetime


st.set_page_config(page_title="Dashboard de Márgenes", layout="wide")
st.title("📊 Panel de Control")

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

        @st.cache_resource
        def conectar_db():
            return mysql.connector.connect(
                host=st.secrets["db"]["host"],
                user=st.secrets["db"]["user"],
                password=st.secrets["db"]["password"]
            )

        def consultar(sql):
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute(sql)
            datos = cursor.fetchall()
            columnas = [col[0] for col in cursor.description]
            cursor.close()
            conn.close()
            return pd.DataFrame(datos, columns=columnas)

        try:
            fecha = st.date_input("📅 Selecciona una fecha para consultar", key="fecha_tab2")

            # Nuevo filtro por cliente
            clientes_disponibles = consultar("SELECT DISTINCT firstname FROM plasma_core.users ORDER BY firstname ASC")
            cliente_seleccionado = st.selectbox("🧍‍♂️ Selecciona Cliente", clientes_disponibles["firstname"].tolist())

            if fecha and cliente_seleccionado:
                fecha_str = fecha.strftime("%Y-%m-%d")

                # Nuevas Altas
                df_altas = consultar(f"""
                    SELECT COUNT(*) as nuevas_altas
                    FROM plasma_core.users 
                    WHERE ts_creation BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59'
                    AND firstname = '{cliente_seleccionado}'
                """)
                st.metric("👥 Nuevas Altas en el Día", f"{df_altas.iloc[0, 0]:,}")

                # Depósitos
                df_depositos = consultar(f"""
                    SELECT COUNT(*) AS total_transacciones, 
                           AVG(amount) AS promedio_amount,
                           SUM(amount) AS total_amount
                    FROM (
                        SELECT amount FROM plasma_payments.nico_transactions
                        WHERE ts_commit BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59'
                        AND user_id IN (SELECT user_id FROM plasma_core.users WHERE firstname = '{cliente_seleccionado}')
                        UNION ALL
                        SELECT amount FROM plasma_payments.payphone_transactions
                        WHERE ts_commit BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59'
                        AND user_id IN (SELECT user_id FROM plasma_core.users WHERE firstname = '{cliente_seleccionado}')
                    ) AS transacciones
                """)
                st.metric("💰 Depósitos Día", f"{df_depositos.iloc[0]['total_transacciones']:,}")
                st.metric("💵 Importe Medio de Depósitos", f"${df_depositos.iloc[0]['promedio_amount']:,.2f}" if df_depositos.iloc[0]['promedio_amount'] else "-")
                st.metric("💳 Valor Total Depósitos", f"${df_depositos.iloc[0]['total_amount']:,.2f}" if df_depositos.iloc[0]['total_amount'] else "-")

                # Altas actuales
                df_total = consultar(f"""
                    SELECT COUNT(*) AS total_usuarios 
                    FROM plasma_core.users
                    WHERE firstname = '{cliente_seleccionado}'
                """)
                st.metric("🧍‍♂️ Altas Actuales", f"{df_total.iloc[0, 0]:,}")

                # Jugadores activos
                df_jugadores = consultar(f"""
                    SELECT COUNT(DISTINCT u.user_id) AS jugadores,
                           AVG(re.amount) AS importe_medio
                    FROM plasma_games.rounds_entries re
                    JOIN plasma_games.sessions s ON re.session_id = s.session_id
                    JOIN plasma_core.users u ON s.user_id = u.user_id
                    WHERE re.ts BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59'
                      AND re.`type` = 'BET'
                      AND u.firstname = '{cliente_seleccionado}'
                """)
                st.metric("🎮 Jugadores Día", f"{df_jugadores.iloc[0]['jugadores']:,}")
                st.metric("💸 Importe Medio Jugado", f"${df_jugadores.iloc[0]['importe_medio']:,.2f}" if df_jugadores.iloc[0]['importe_medio'] else "-")

                # GGR
                df_ggr = consultar(f"""
                    SELECT 
                        SUM(CASE WHEN `type` = 'BET' THEN amount ELSE 0 END) AS total_bet,
                        SUM(CASE WHEN `type` = 'WIN' THEN amount ELSE 0 END) AS total_win,
                        SUM(CASE WHEN `type` = 'BET' THEN amount ELSE 0 END) -
                        SUM(CASE WHEN `type` = 'WIN' THEN amount ELSE 0 END) AS ggr
                    FROM plasma_games.rounds_entries
                    WHERE ts BETWEEN '{fecha_str} 00:00:00' AND '{fecha_str} 23:59:59'
                    AND session_id IN (
                        SELECT session_id FROM plasma_games.sessions s
                        JOIN plasma_core.users u ON s.user_id = u.user_id
                        WHERE u.firstname = '{cliente_seleccionado}'
                    )
                """)
                st.metric("🎯 Total BET", f"${df_ggr.iloc[0]['total_bet']:,.2f}" if df_ggr.iloc[0]['total_bet'] else "-")
                st.metric("🎯 Total WIN", f"${df_ggr.iloc[0]['total_win']:,.2f}" if df_ggr.iloc[0]['total_win'] else "-")
                st.metric("📊 GGR Día", f"${df_ggr.iloc[0]['ggr']:,.2f}" if df_ggr.iloc[0]['ggr'] else "-")

        except IndexError:
            st.warning("⚠️ No se pudo procesar la fecha seleccionada. Intenta con otra fecha o revisa la conexión a la base de datos.")
        except mysql.connector.Error as e:
            st.error(f"❌ Error de conexión con la base de datos: {e}")







