import streamlit as st
import pandas as pd
import re
import difflib
import mysql.connector
from datetime import datetime
from datetime import date
import altair as alt
import requests
import re, unicodedata
# ====== P&L CON FORMATO PGC ESPAÑOL PARA HOLDED ======

import pandas as pd
import streamlit as st
from datetime import datetime
import requests
import unicodedata
import re

# ====== CLASIFICADOR PGC MEJORADO ======
def classify_pgc_account(account_code: str, account_name: str = "") -> dict:
    """
    Clasifica cuentas según PGC español y devuelve categoría, subcategoría y orden
    """
    code = str(account_code or "").strip()
    name = str(account_name or "").lower()
    
    # Extraer solo dígitos iniciales
    digits = re.match(r'^(\d{2,})', code.replace(" ", ""))
    code_num = digits.group(1) if digits else ""
    
    # Estructura del PGC
    pgc_structure = {
        # INGRESOS
        "70": {"main": "1. Importe neto de la cifra de negocios", "sub": "b) Prestaciones de servicios", "order": 100},
        "71": {"main": "1. Importe neto de la cifra de negocios", "sub": "a) Ventas", "order": 101},
        "72": {"main": "1. Importe neto de la cifra de negocios", "sub": "a) Ventas", "order": 102},
        "73": {"main": "1. Importe neto de la cifra de negocios", "sub": "a) Ventas", "order": 103},
        "74": {"main": "1. Importe neto de la cifra de negocios", "sub": "c) Otros ingresos", "order": 104},
        "75": {"main": "1. Importe neto de la cifra de negocios", "sub": "c) Otros ingresos", "order": 105},
        
        # APROVISIONAMIENTOS
        "60": {"main": "4. Aprovisionamientos", "sub": "a) Consumo de mercaderías", "order": 200},
        "61": {"main": "4. Aprovisionamientos", "sub": "b) Consumo de materias primas", "order": 201},
        "607": {"main": "4. Aprovisionamientos", "sub": "c) Trabajos realizados por otras empresas", "order": 202},
        
        # GASTOS DE PERSONAL  
        "640": {"main": "6. Gastos de personal", "sub": "a) Sueldos, salarios y asimilados", "order": 300},
        "641": {"main": "6. Gastos de personal", "sub": "a) Sueldos, salarios y asimilados", "order": 301},
        "642": {"main": "6. Gastos de personal", "sub": "b) Cargas sociales", "order": 302},
        "649": {"main": "6. Gastos de personal", "sub": "b) Cargas sociales", "order": 303},
        
        # OTROS GASTOS DE EXPLOTACIÓN
        "621": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 400},
        "622": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 401},
        "623": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 402},
        "624": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 403},
        "625": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 404},
        "626": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 405},
        "627": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 406},
        "628": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 407},
        "629": {"main": "7. Otros gastos de explotación", "sub": "a) Servicios exteriores", "order": 408},
        "631": {"main": "7. Otros gastos de explotación", "sub": "b) Tributos", "order": 409},
        
        # INGRESOS FINANCIEROS
        "76": {"main": "14. Ingresos financieros", "sub": "b) De valores negociables y de créditos", "order": 500},
        "769": {"main": "14. Ingresos financieros", "sub": "b) De valores negociables y de créditos", "order": 501},
        
        # GASTOS FINANCIEROS
        "662": {"main": "15. Gastos financieros", "sub": "b) Por deudas con terceros", "order": 600},
        "663": {"main": "15. Gastos financieros", "sub": "b) Por deudas con terceros", "order": 601},
        "664": {"main": "15. Gastos financieros", "sub": "b) Por deudas con terceros", "order": 602},
        "665": {"main": "15. Gastos financieros", "sub": "b) Por deudas con terceros", "order": 603},
        "669": {"main": "15. Gastos financieros", "sub": "b) Por deudas con terceros", "order": 604},
        
        # DIFERENCIAS DE CAMBIO
        "668": {"main": "17. Diferencias de cambio", "sub": "Diferencias de cambio", "order": 700},
        "768": {"main": "17. Diferencias de cambio", "sub": "Diferencias de cambio", "order": 701},
        
        # OTROS RESULTADOS
        "778": {"main": "13. Otros resultados", "sub": "a) Ingresos excepcionales", "order": 800},
        "678": {"main": "13. Otros resultados", "sub": "b) Gastos excepcionales", "order": 801},
    }
    
    # Buscar por código exacto primero
    for code_key, data in pgc_structure.items():
        if code_num.startswith(code_key):
            return {
                "main_category": data["main"],
                "sub_category": data["sub"],
                "order": data["order"],
                "account_code": code,
                "account_name": account_name
            }
    
    # Fallback por nombre o código general
    if "nomina" in name or "sueldo" in name or "salario" in name:
        return {"main_category": "6. Gastos de personal", "sub_category": "a) Sueldos, salarios y asimilados", "order": 300, "account_code": code, "account_name": account_name}
    elif "seguridad social" in name or "ss" in name:
        return {"main_category": "6. Gastos de personal", "sub_category": "b) Cargas sociales", "order": 302, "account_code": code, "account_name": account_name}
    elif "interes" in name or "prestamo" in name:
        return {"main_category": "15. Gastos financieros", "sub_category": "b) Por deudas con terceros", "order": 600, "account_code": code, "account_name": account_name}
    elif "cambio" in name or "divisa" in name:
        return {"main_category": "17. Diferencias de cambio", "sub_category": "Diferencias de cambio", "order": 700, "account_code": code, "account_name": account_name}
    elif code_num.startswith("7"):
        return {"main_category": "1. Importe neto de la cifra de negocios", "sub_category": "b) Prestaciones de servicios", "order": 100, "account_code": code, "account_name": account_name}
    elif code_num.startswith("6"):
        return {"main_category": "7. Otros gastos de explotación", "sub_category": "a) Servicios exteriores", "order": 400, "account_code": code, "account_name": account_name}
    
    # Default
    return {"main_category": "7. Otros gastos de explotación", "sub_category": "a) Servicios exteriores", "order": 400, "account_code": code, "account_name": account_name}

def create_pgc_report(df_data: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Crear reporte P&L en formato PGC español
    """
    if df_data.empty:
        return pd.DataFrame()
    
    # Clasificar cada línea según PGC
    classified_data = []
    
    for _, row in df_data.iterrows():
        classification = classify_pgc_account(row.get('cuenta', ''), row.get('descripcion', ''))
        
        classified_data.append({
            'fecha': row['fecha'],
            'periodo': row['periodo'],
            'main_category': classification['main_category'],
            'sub_category': classification['sub_category'],
            'order': classification['order'],
            'account_code': classification['account_code'],
            'account_name': classification['account_name'],
            'description': f"{classification['account_code']} - {classification['account_name']}",
            'amount': row['importe']
        })
    
    df_classified = pd.DataFrame(classified_data)
    
    # Crear estructura de periodos
    date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
    periods = [d.strftime('%B %y') for d in date_range]
    
    # Inicializar estructura del reporte
    report_structure = []
    
    # Agrupar por categorías y subcategorías
    grouped = df_classified.groupby(['order', 'main_category', 'sub_category', 'description'])['amount'].sum().reset_index()
    
    current_main = None
    current_sub = None
    
    for _, group in grouped.sort_values('order').iterrows():
        main_cat = group['main_category']
        sub_cat = group['sub_category']
        description = group['description']
        
        # Agregar encabezado principal si es nuevo
        if main_cat != current_main:
            report_structure.append({
                'category': main_cat,
                'type': 'main_header',
                'description': main_cat,
                'level': 0,
                'amount': 0,
                'order': group['order']
            })
            current_main = main_cat
            current_sub = None
        
        # Agregar subencabezado si es nuevo
        if sub_cat != current_sub and sub_cat != main_cat:
            report_structure.append({
                'category': main_cat,
                'type': 'sub_header',
                'description': sub_cat,
                'level': 1,
                'amount': 0,
                'order': group['order']
            })
            current_sub = sub_cat
        
        # Agregar línea de detalle
        report_structure.append({
            'category': main_cat,
            'type': 'detail',
            'description': description,
            'level': 2,
            'amount': group['amount'],
            'order': group['order']
        })
    
    # Calcular totales y agregar líneas de resultado
    df_report = pd.DataFrame(report_structure)
    
    # Calcular totales por categoría principal
    category_totals = df_classified.groupby('main_category')['amount'].sum().to_dict()
    
    # Agregar líneas de resultado importantes
    ingresos = category_totals.get("1. Importe neto de la cifra de negocios", 0)
    aprovisionamientos = category_totals.get("4. Aprovisionamientos", 0)
    gastos_personal = category_totals.get("6. Gastos de personal", 0)
    otros_gastos = category_totals.get("7. Otros gastos de explotación", 0)
    otros_resultados = category_totals.get("13. Otros resultados", 0)
    ingresos_financieros = category_totals.get("14. Ingresos financieros", 0)
    gastos_financieros = category_totals.get("15. Gastos financieros", 0)
    diferencias_cambio = category_totals.get("17. Diferencias de cambio", 0)
    
    # Calcular métricas clave
    resultado_explotacion = ingresos + aprovisionamientos + gastos_personal + otros_gastos + otros_resultados
    resultado_financiero = ingresos_financieros + gastos_financieros + diferencias_cambio
    resultado_antes_impuestos = resultado_explotacion + resultado_financiero
    
    # Agregar líneas de resultado al final
    result_lines = [
        {'category': 'RESULTADO', 'type': 'result', 'description': 'Resultado de explotación', 'level': 0, 'amount': resultado_explotacion, 'order': 900},
        {'category': 'RESULTADO', 'type': 'result', 'description': 'Resultado financiero', 'level': 0, 'amount': resultado_financiero, 'order': 901},
        {'category': 'RESULTADO', 'type': 'result', 'description': 'Resultado antes de impuestos', 'level': 0, 'amount': resultado_antes_impuestos, 'order': 902},
        {'category': 'RESULTADO', 'type': 'result', 'description': 'Resultado del ejercicio', 'level': 0, 'amount': resultado_antes_impuestos, 'order': 903}
    ]
    
    df_results = pd.DataFrame(result_lines)
    df_final_report = pd.concat([df_report, df_results], ignore_index=True)
    
    return df_final_report.sort_values('order')

def format_pgc_display(df_report: pd.DataFrame) -> pd.DataFrame:
    """
    Formatear el reporte para visualización tipo PGC español
    """
    if df_report.empty:
        return pd.DataFrame()
    
    display_data = []
    
    for _, row in df_report.iterrows():
        # Formatear descripción con indentación
        indent = "    " * row['level']
        description = f"{indent}{row['description']}"
        
        # Formatear importe
        amount = row['amount']
        if amount == 0 and row['type'] in ['main_header', 'sub_header']:
            amount_str = ""
        else:
            amount_str = f"{amount:,.2f} €" if amount != 0 else "0.00 €"
        
        display_data.append({
            'Concepto': description,
            'Importe': amount_str,
            'Tipo': row['type'],
            'Nivel': row['level']
        })
    
    return pd.DataFrame(display_data)

# ====== FUNCIÓN PRINCIPAL PARA USAR EN TU CÓDIGO ======
def generate_pgc_report(df_consolidated: pd.DataFrame, fecha_inicio: datetime, fecha_fin: datetime):
    """
    Generar reporte P&L en formato PGC español
    """
    st.subheader("📋 P&L - Formato Plan General Contable")
    
    if df_consolidated.empty:
        st.warning("No hay datos para generar el reporte")
        return
    
    # Generar reporte PGC
    df_pgc_report = create_pgc_report(df_consolidated, fecha_inicio, fecha_fin)
    
    if df_pgc_report.empty:
        st.warning("No se pudo generar el reporte PGC")
        return
    
    # Formatear para visualización
    df_display = format_pgc_display(df_pgc_report)
    
    # Mostrar reporte con formato personalizado
    st.markdown("### SOLUCIONES PARA GAMING ONLINE ATOMO GAMES SL")
    st.markdown("---")
    
    # Crear tabla HTML personalizada para mejor formato
    html_table = "<table style='width:100%; border-collapse: collapse;'>"
    
    for _, row in df_display.iterrows():
        # Aplicar estilos según el tipo
        if row['Tipo'] == 'main_header':
            style = "font-weight: bold; background-color: #f0f0f0; border-top: 2px solid #333;"
        elif row['Tipo'] == 'sub_header':
            style = "font-weight: bold; font-style: italic; background-color: #f8f8f8;"
        elif row['Tipo'] == 'result':
            style = "font-weight: bold; border-top: 1px solid #666; background-color: #e8e8e8;"
        else:
            style = "padding-left: 20px;"
        
        html_table += f"""
        <tr style='{style}'>
            <td style='padding: 4px; border-bottom: 1px solid #ddd;'>{row['Concepto']}</td>
            <td style='padding: 4px; text-align: right; border-bottom: 1px solid #ddd;'>{row['Importe']}</td>
        </tr>
        """
    
    html_table += "</table>"
    
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Mostrar también como DataFrame para exportación
    with st.expander("📊 Datos en formato tabla"):
        st.dataframe(df_display[['Concepto', 'Importe']], use_container_width=True, height=600)
    
    # Resumen ejecutivo
    ingresos_total = df_consolidated[df_consolidated['categoria'] == 'Ingresos']['importe'].sum()
    gastos_total = df_consolidated[df_consolidated['categoria'].str.contains('gasto|Aprovisionamiento', case=False, na=False)]['importe'].sum()
    resultado_neto = ingresos_total + gastos_total  # gastos ya son negativos
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Ingresos Totales", f"{ingresos_total:,.2f} €")
    col2.metric("💸 Gastos Totales", f"{abs(gastos_total):,.2f} €")  
    col3.metric("💎 Resultado Neto", f"{resultado_neto:,.2f} €", delta=f"{(resultado_neto/ingresos_total*100):.1f}%" if ingresos_total > 0 else "0%")


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
def get_document_detail_corrected(doc_type: str, doc_id: str):
    """
    Trae el detalle de un documento de Holded.
    Fallback: si el doc_type falla, intenta con 'purchase'.
    """
    if not doc_id:
        return {}
    headers = {"accept": "application/json", "key": get_holded_token()}

    # 1) Intento con el tipo indicado
    url = f"https://api.holded.com/api/invoicing/v1/documents/{doc_type}/{doc_id}"
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # 2) Fallback con 'purchase' (tu tenant confirmó gastos en purchase)
    if doc_type != "purchase":
        try:
            url2 = f"https://api.holded.com/api/invoicing/v1/documents/purchase/{doc_id}"
            r2 = requests.get(url2, headers=headers, timeout=30)
            if r2.status_code == 200:
                return r2.json()
        except Exception:
            pass

    return {}
    
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
    clientes_unicos_1=["Todos"] + clientes_disponibles
    filtro_cliente = st.sidebar.selectbox(
        "Cliente (Tab 1)",
        clientes_unicos_1,
        key="tab1_cliente_select"
    )
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
            index=opciones_cliente.index(st.session_state.get("cliente", "Todos")),
            key="tab2_cliente_select"
            
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


@st.cache_data(ttl=60)
def diagnose_purchases_comprehensive(start_dt: datetime, end_dt: datetime):
    """
    Diagnóstico exhaustivo de todos los endpoints de compras/gastos
    """
    headers = {"accept": "application/json", "key": get_holded_token()}
    base = "https://api.holded.com/api/invoicing/v1"
    
    # Endpoints principales a probar
    endpoints_to_test = [
        ("purchase", f"{base}/documents/purchase"),
        ("bill", f"{base}/documents/bill"),
        ("expense", f"{base}/documents/expense"),
        ("purchaseorder", f"{base}/documents/purchaseorder"),
        ("receipt", f"{base}/documents/receipt"),
        # Endpoints alternativos
        ("purchases", f"{base}/purchases"),
        ("expenses", f"{base}/expenses"),
        ("bills", f"{base}/bills"),
    ]
    
    # Parámetros de fecha a probar
    date_params_variants = [
        # Timestamp Unix
        {"starttmp": int(start_dt.timestamp()), "endtmp": int(end_dt.timestamp())},
        # Formato ISO
        {"dateFrom": start_dt.strftime("%Y-%m-%d"), "dateTo": end_dt.strftime("%Y-%m-%d")},
        {"from": start_dt.strftime("%Y-%m-%d"), "to": end_dt.strftime("%Y-%m-%d")},
        # Formato alternativo
        {"start": start_dt.strftime("%Y-%m-%d"), "end": end_dt.strftime("%Y-%m-%d")},
        {"created_from": start_dt.strftime("%Y-%m-%d"), "created_to": end_dt.strftime("%Y-%m-%d")},
        # Sin filtros (traer todo)
        {},
    ]
    
    results = []
    
    for endpoint_name, url in endpoints_to_test:
        for i, date_params in enumerate(date_params_variants):
            try:
                params = {"limit": 100, "sort": "created-asc", **date_params}
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        count = len(data) if isinstance(data, list) else 1 if data else 0
                        
                        # Información adicional sobre la estructura
                        sample_doc = data[0] if isinstance(data, list) and data else data if data else {}
                        doc_fields = list(sample_doc.keys()) if sample_doc else []
                        
                        results.append({
                            "endpoint": endpoint_name,
                            "url": url,
                            "date_params": f"Variant_{i+1}",
                            "status": response.status_code,
                            "count": count,
                            "success": True,
                            "fields": ", ".join(doc_fields[:10]),  # Primeros 10 campos
                            "error": None
                        })
                        
                        # Si encontramos datos, guardamos una muestra
                        if count > 0:
                            results[-1]["sample_data"] = sample_doc
                            
                    except json.JSONDecodeError:
                        results.append({
                            "endpoint": endpoint_name,
                            "url": url,
                            "date_params": f"Variant_{i+1}",
                            "status": response.status_code,
                            "count": 0,
                            "success": False,
                            "fields": "",
                            "error": "Invalid JSON response"
                        })
                else:
                    results.append({
                        "endpoint": endpoint_name,
                        "url": url,
                        "date_params": f"Variant_{i+1}",
                        "status": response.status_code,
                        "count": 0,
                        "success": False,
                        "fields": "",
                        "error": response.text[:200] if response.text else "No response text"
                    })
                    
            except Exception as e:
                results.append({
                    "endpoint": endpoint_name,
                    "url": url,
                    "date_params": f"Variant_{i+1}",
                    "status": -1,
                    "count": 0,
                    "success": False,
                    "fields": "",
                    "error": str(e)
                })
    
    return pd.DataFrame(results)
@st.cache_data(ttl=60)
def get_all_expenses_improved(start_dt: datetime, end_dt: datetime):
    """
    Función mejorada para obtener todos los gastos desde múltiples endpoints
    """
    headers = {"accept": "application/json", "key": get_holded_token()}
    all_expenses = []
    
    # Lista de endpoints que podrían contener gastos
    expense_endpoints = [
        "purchase",
        "bill", 
        "expense",
        "receipt"
    ]
    
    for endpoint in expense_endpoints:
        try:
            st.info(f"🔍 Buscando en endpoint: {endpoint}")
            
            # Método 1: Con filtros de fecha
            url = f"https://api.holded.com/api/invoicing/v1/documents/{endpoint}"
            
            # Probar diferentes formatos de fecha
            date_params_list = [
                {"starttmp": int(start_dt.timestamp()), "endtmp": int(end_dt.timestamp())},
                {"dateFrom": start_dt.strftime("%Y-%m-%d"), "dateTo": end_dt.strftime("%Y-%m-%d")},
                {"from": start_dt.strftime("%Y-%m-%d"), "to": end_dt.strftime("%Y-%m-%d")}
            ]
            
            found_data = False
            
            for date_params in date_params_list:
                params = {"limit": 500, "sort": "created-asc", **date_params}
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and data:
                        st.success(f"✅ Encontrados {len(data)} documentos en {endpoint}")
                        all_expenses.extend([(endpoint, doc) for doc in data])
                        found_data = True
                        break
                        
            # Método 2: Si no encontró con filtros, traer todo y filtrar localmente
            if not found_data:
                st.warning(f"⚠️ No se encontraron datos con filtros en {endpoint}, probando sin filtros...")
                
                # Paginación para traer todos los documentos
                page = 1
                while True:
                    params = {"page": page, "limit": 500}
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    
                    if response.status_code != 200:
                        break
                        
                    data = response.json()
                    if not isinstance(data, list) or not data:
                        break
                    
                    # Filtrar por fecha localmente
                    filtered_docs = []
                    for doc in data:
                        doc_date = doc.get("date")
                        if doc_date:
                            try:
                                if isinstance(doc_date, (int, float)):
                                    parsed_date = pd.to_datetime(doc_date, unit='s')
                                else:
                                    parsed_date = pd.to_datetime(doc_date)
                                
                                if start_dt <= parsed_date <= end_dt:
                                    filtered_docs.append(doc)
                            except:
                                continue
                    
                    all_expenses.extend([(endpoint, doc) for doc in filtered_docs])
                    
                    if len(data) < 500:  # Última página
                        break
                    
                    page += 1
                
                if filtered_docs:
                    st.success(f"✅ Encontrados {len(filtered_docs)} documentos filtrados localmente en {endpoint}")
                    
        except Exception as e:
            st.error(f"❌ Error en endpoint {endpoint}: {str(e)}")
            continue
    
    return all_expenses
def parse_expense_lines_improved(endpoint_type: str, doc_json: dict):
    """
    Parser mejorado que maneja diferentes estructuras de documentos
    """
    lines = []
    if not doc_json:
        return lines
        
    # Obtener fecha del documento
    raw_date = doc_json.get("date")
    if isinstance(raw_date, (int, float)):
        fecha = pd.to_datetime(raw_date, unit='s', errors='coerce')
    else:
        fecha = pd.to_datetime(raw_date, errors='coerce')
    
    if pd.isna(fecha):
        return lines
    
    # Diferentes estructuras según el tipo de documento
    items_keys = ["items", "lines", "concepts", "expenses", "details"]
    items = []
    
    for key in items_keys:
        if key in doc_json and doc_json[key]:
            items = doc_json[key]
            break
    
    if items and isinstance(items, list):
        # Procesar líneas detalladas
        for item in items:
            if not isinstance(item, dict):
                continue
                
            # Obtener importe de la línea
            amount = 0.0
            amount_keys = ["subTotal", "subtotal", "untaxedAmount", "netAmount", "base", "amount", "total", "value"]
            
            for key in amount_keys:
                if key in item and item[key] is not None:
                    try:
                        amount = float(item[key])
                        break
                    except:
                        continue
            
            # Si no hay importe directo, calcular qty * price
            if amount == 0:
                try:
                    qty = float(item.get("quantity", item.get("qty", 1)))
                    price_keys = ["unitPrice", "price", "unitprice", "unit_cost", "unitCost"]
                    price = 0
                    for key in price_keys:
                        if key in item and item[key] is not None:
                            price = float(item[key])
                            break
                    amount = qty * price
                except:
                    continue
            
            if amount == 0:
                continue
                
            # Obtener código y nombre de cuenta
            account_code = ""
            account_name = ""
            
            code_keys = ["expenseAccountCode", "accountCode", "expenseAccountId", "accountId", "account"]
            for key in code_keys:
                if key in item and item[key]:
                    account_code = str(item[key])
                    break
            
            name_keys = ["accountName", "name", "description", "concept", "title"]
            for key in name_keys:
                if key in item and item[key]:
                    account_name = str(item[key])
                    break
            
            lines.append((fecha, account_code, account_name, float(amount)))
    
    else:
        # Si no hay líneas detalladas, usar el total del documento
        total = 0.0
        total_keys = ["subTotal", "subtotal", "untaxedAmount", "total", "amount", "netAmount"]
        
        for key in total_keys:
            if key in doc_json and doc_json[key] is not None:
                try:
                    total = float(doc_json[key])
                    break
                except:
                    continue
        
        if total > 0:
            # Usar cuenta genérica según el tipo de documento
            default_accounts = {
                "purchase": ("60XXX", "Compras"),
                "bill": ("62XXX", "Servicios externos"),
                "expense": ("62XXX", "Gastos generales"),
                "receipt": ("62XXX", "Gastos diversos")
            }
            
            account_code, account_name = default_accounts.get(endpoint_type, ("62XXX", "Gasto sin desglosar"))
            lines.append((fecha, account_code, account_name, float(total)))
    
    return lines
def classify_account_enhanced(code: str, name: str = "", endpoint_type: str = "") -> str:
    """
    Clasificador mejorado que considera el tipo de endpoint
    """
    code = _only_leading_digits(code)
    name_clean = _strip_accents(str(name or "").lower())
    
    # Clasificación por código (prioritaria)
    if code.startswith("768") or code.startswith("668"):
        return "Diferencias de cambio"
    elif code.startswith("76"):
        return "Ingresos financieros"
    elif code.startswith("66"):
        return "Gastos financieros"
    elif code.startswith("64"):
        return "Gastos de personal"
    elif code.startswith(("60", "61")):
        return "Aprovisionamientos"
    elif code.startswith(("62", "63", "65", "68", "69")):
        return "Otros gastos de explotación"
    elif code.startswith("77"):
        return "Otros resultados"
    elif code.startswith(("70", "71", "72", "73", "74", "75")):
        return "Ingresos"
    elif code.startswith("7"):
        return "Ingresos"
    elif code.startswith("6"):
        return "Otros gastos de explotación"
    
    # Clasificación por nombre
    if any(w in name_clean for w in ["nomina", "sueldo", "salario", "personal", "seguridad social", "ss"]):
        return "Gastos de personal"
    elif any(w in name_clean for w in ["interes", "financiero", "prestamo", "credito", "banco"]):
        return "Gastos financieros"
    elif "cambio" in name_clean or "divisa" in name_clean:
        return "Diferencias de cambio"
    elif any(w in name_clean for w in ["compra", "suministro", "materia prima", "mercancia"]):
        return "Aprovisionamientos"
    
    # Clasificación por tipo de endpoint
    if endpoint_type == "purchase":
        return "Aprovisionamientos"
    elif endpoint_type in ["bill", "expense", "receipt"]:
        return "Otros gastos de explotación"
    
    return "Otros gastos de explotación"

# 5. FUNCIÓN PRINCIPAL CORREGIDA
def process_expenses_corrected(start_dt: datetime, end_dt: datetime, cliente_filter: str = "Todo"):
    """
    Función principal corregida para procesar gastos
    """
    st.info("🔍 Iniciando diagnóstico de gastos...")
    
    # Paso 1: Diagnóstico
    with st.expander("🔧 Diagnóstico de Endpoints", expanded=True):
        diagnosis_df = diagnose_purchases_comprehensive(start_dt, end_dt)
        
        # Mostrar solo los exitosos
        successful = diagnosis_df[diagnosis_df["success"] == True].sort_values("count", ascending=False)
        if not successful.empty:
            st.success(f"✅ Encontrados {len(successful)} endpoints exitosos")
            st.dataframe(successful[["endpoint", "count", "fields"]], use_container_width=True)
        else:
            st.error("❌ No se encontraron endpoints exitosos")
            st.dataframe(diagnosis_df[["endpoint", "status", "error"]], use_container_width=True)
            return []
    
    # Paso 2: Obtener datos
    st.info("📥 Obteniendo datos de gastos...")
    all_expense_data = get_all_expenses_improved(start_dt, end_dt)
    
    if not all_expense_data:
        st.warning("⚠️ No se encontraron gastos en el período seleccionado")
        return []
    
    st.success(f"✅ Encontrados {len(all_expense_data)} documentos de gastos")
    
    # Paso 3: Procesar líneas
    st.info("⚙️ Procesando líneas de gastos...")
    processed_lines = []
    
    progress_bar = st.progress(0)
    
    for i, (endpoint_type, doc) in enumerate(all_expense_data):
        progress_bar.progress((i + 1) / len(all_expense_data))
        
        # Filtrar por cliente si es necesario
        if cliente_filter != "Todo":
            doc_cliente = doc.get("contactName", "")
            if doc_cliente != cliente_filter:
                continue
        
        # Obtener detalle si es necesario
        doc_id = str(doc.get("id", ""))
        if doc_id:
            detail = get_document_detail_corrected(endpoint_type, doc_id)
            if detail:
                doc = detail
        
        # Parsear líneas
        lines = parse_expense_lines_improved(endpoint_type, doc)
        
        for fecha, account_code, account_name, amount in lines:
            if pd.isna(fecha) or amount == 0:
                continue
                
            proveedor = doc.get("contactName", "Sin nombre")
            periodo = fecha.to_period("M").strftime("%Y-%m")
            categoria = classify_account_enhanced(account_code, account_name, endpoint_type)
            amount_norm = normalize_amount_by_category(categoria, amount)
            
            processed_lines.append({
                "periodo": periodo,
                "fecha": fecha,
                "cliente": proveedor,
                "categoria": categoria,
                "importe": amount_norm,
                "cuenta": account_code or f"{endpoint_type.upper()}XXX",
                "descripcion": account_name or f"Gasto desde {endpoint_type}",
                "endpoint": endpoint_type
            })
    
    progress_bar.empty()
    
    st.success(f"✅ Procesadas {len(processed_lines)} líneas de gastos")
    
    # Mostrar resumen por endpoint
    if processed_lines:
        endpoint_summary = pd.DataFrame(processed_lines).groupby(["endpoint", "categoria"])["importe"].sum().unstack(fill_value=0)
        st.subheader("📊 Resumen por Endpoint")
        st.dataframe(endpoint_summary, use_container_width=True)
    
    return processed_lines

# ====== TAB 3: P&L desde Holded - VERSION PARCHEADA ======
# ====== TAB 3: P&L desde Holded - VERSION CORREGIDA COMPLETA ======
with tab3:
    st.header("📑 P&L desde Holded (API)")
    st.caption("Calculado desde documentos de Holded y libro diario contable para mayor precisión.")

    # ====== MAPEO ESPECÍFICO DE CUENTAS BASADO EN EL EXCEL ======
    ACCOUNT_MAPPING = {
        # APROVISIONAMIENTOS
        "60700017": ("Aprovisionamientos", "Trabajos realizados por AD CONSULTING Bet593"),
        
        # GASTOS DE PERSONAL
        "64000000": ("Gastos de personal", "Sueldos y salarios"),
        "64100000": ("Gastos de personal", "Indemnizaciones"),
        "64200000": ("Gastos de personal", "Seguridad Social a cargo de la empresa"),
        "64900000": ("Gastos de personal", "Otros gastos sociales"),
        
        # OTROS GASTOS DE EXPLOTACIÓN - Servicios exteriores
        "62100000": ("Otros gastos de explotación", "Alquiler vehículos"),
        "62100001": ("Otros gastos de explotación", "Alquiler apartamentos turísticos"),
        "62100002": ("Otros gastos de explotación", "Renting Lexus kinto ONe"),
        "62200001": ("Otros gastos de explotación", "Mantenimiento Holded"),
        "62200002": ("Otros gastos de explotación", "Hostings"),
        "62300001": ("Otros gastos de explotación", "Servicios de profesionales - Sensus Consultoria"),
        "62300002": ("Otros gastos de explotación", "Servicios de profesionales - Notarios Registros y FNMT"),
        "62300004": ("Otros gastos de explotación", "Servicios de profesionales Abogados"),
        "62300005": ("Otros gastos de explotación", "Servicios de profesionales Recruting"),
        "62300008": ("Otros gastos de explotación", "Servicios profesionales JUNIOR CALZADILLA"),
        "62300020": ("Otros gastos de explotación", "Servicios de profesionales TECHNOURCE"),
        "62300021": ("Otros gastos de explotación", "Servicios de profesionales ITMA"),
        "62300024": ("Otros gastos de explotación", "Servicios de profesionales Informaticos"),
        "62400000": ("Otros gastos de explotación", "Transportes"),
        "62500000": ("Otros gastos de explotación", "Primas de seguros"),
        "62600001": ("Otros gastos de explotación", "Servicios bancarios CAIXABANK"),
        "62600002": ("Otros gastos de explotación", "Servicios bancarios BBVA"),
        "62600003": ("Otros gastos de explotación", "Servicios bancarios BINANCE"),
        "62700000": ("Otros gastos de explotación", "Publicidad propaganda y relaciones públicas"),
        "62900001": ("Otros gastos de explotación", "Software y Licencias"),
        "62900002": ("Otros gastos de explotación", "Material oficina y consumibles"),
        "62900003": ("Otros gastos de explotación", "GTOS VIAJES hotelesvuelosetc"),
        "62900004": ("Otros gastos de explotación", "DIETAS"),
        "62900005": ("Otros gastos de explotación", "DESPLAZAMIENTO Taxi peajes etc"),
        "62900006": ("Otros gastos de explotación", "Gasoil"),
        
        # TRIBUTOS
        "63100000": ("Otros gastos de explotación", "Otros tributos"),
        
        # OTROS RESULTADOS
        "77800000": ("Otros resultados", "Ingresos excepcionales"),
        "67800000": ("Otros resultados", "Gastos excepcionales"),
        
        # INGRESOS FINANCIEROS
        "76900000": ("Ingresos financieros", "Otros ingresos financieros"),
        
        # GASTOS FINANCIEROS
        "66230000": ("Gastos financieros", "Intereses de deudas con entidades de crédito"),
        "66240000": ("Gastos financieros", "Intereses de deudas otras empresas"),
        
        # DIFERENCIAS DE CAMBIO
        "66800000": ("Diferencias de cambio", "Diferencias negativas de cambio"),
        "76800000": ("Diferencias de cambio", "Diferencias positivas de cambio"),
        
        # INGRESOS (principales cuentas del Excel)
        "70500000": ("Ingresos", "Prestaciones de servicios (Licencia Internacional)"),
        "70500002": ("Ingresos", "Prestación de servicios Descuento torneos BET593"),
        "70500005": ("Ingresos", "Prestación de servicios Descuento torneos BET502"),
        "70500006": ("Ingresos", "Prestación servicios BET502 - METRONIA"),
        "70500008": ("Ingresos", "Prestación servicios BET593 - METRONIA"),
        "70500009": ("Ingresos", "Prestación servicios BET593 - LOTTERY"),
        "70500010": ("Ingresos", "Prestación servicios BET593 - OCTAVIAN SRL"),
        "70500011": ("Ingresos", "Prestación servicios BET593 - VITAL GAMES PROJECT SLOT SRL"),
        "70500013": ("Ingresos", "Prestación servicios BET593 - APOLLO SOFTSRO"),
        "70500014": ("Ingresos", "Prestación servicios BET593 - PSM TECH Srl"),
        "70500015": ("Ingresos", "Prestación servicios BET593 - SEVEN ABC SOLUTION CH"),
        "70500016": ("Ingresos", "Prestación servicios BET593 - PROJEKT SERVICE SRL"),
        "70500017": ("Ingresos", "Prestación servicios BET593 - MYMOON LTD"),
        "70500018": ("Ingresos", "Prestación servicios BET593 - WORLDMATCHSRL"),
        "70500019": ("Ingresos", "Prestación servicios BET593 - ARRISE SOLUTIONS LIMITED"),
    }

    # ====== FUNCIONES AUXILIARES PARA HOLDED API ======
    import unicodedata, re

    @st.cache_data(ttl=300)
    def get_holded_token():
        """Obtener token de autenticación de Holded"""
        try:
            token = "fafbb8191b37e6b696f192e70b4a198c"
            return token
        except Exception as e:
            st.warning(f"Error obteniendo token de Holded: {e}.")
            return None

    @st.cache_data(ttl=60)
    def list_documents_corrected(doc_type: str, start_dt: datetime, end_dt: datetime, page_size=200):
        """Lista documentos con filtros de fecha corregidos"""
        url = f"https://api.holded.com/api/invoicing/v1/documents/{doc_type}"
        headers = {"accept": "application/json", "key": get_holded_token()}
        params = {
            "starttmp": int(start_dt.timestamp()),
            "endtmp": int(end_dt.timestamp()),
            "sort": "created-asc",
            "limit": page_size
        }
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame()
            else:
                st.error(f"Error {r.status_code} en {doc_type}: {r.text[:300]}")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error conectando con Holded ({doc_type}): {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=60)
    def get_document_detail_corrected(doc_type: str, doc_id: str):
        """
        Trae el detalle de un documento de Holded.
        Fallback: si el doc_type falla, intenta con 'purchase'.
        """
        if not doc_id:
            return {}
        headers = {"accept": "application/json", "key": get_holded_token()}

        # 1) Intento con el tipo indicado
        url = f"https://api.holded.com/api/invoicing/v1/documents/{doc_type}/{doc_id}"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

        # 2) Fallback con 'purchase'
        if doc_type != "purchase":
            try:
                url2 = f"https://api.holded.com/api/invoicing/v1/documents/purchase/{doc_id}"
                r2 = requests.get(url2, headers=headers, timeout=30)
                if r2.status_code == 200:
                    return r2.json()
            except Exception:
                pass

        return {}

    @st.cache_data(ttl=60)
    def list_daily_ledger_corrected(start_dt: datetime, end_dt: datetime):
        """Obtiene libro diario con filtros de fecha mejorados"""
        url = "https://api.holded.com/api/accounting/v1/dailyledger"
        headers = {"accept": "application/json", "key": get_holded_token()}
        date_formats = [
            {"from": start_dt.strftime("%Y-%m-%d"), "to": end_dt.strftime("%Y-%m-%d")},
            {"dateFrom": start_dt.strftime("%Y-%m-%d"), "dateTo": end_dt.strftime("%Y-%m-%d")},
            {"starttmp": int(start_dt.timestamp()), "endtmp": int(end_dt.timestamp())},
        ]
        for params in date_formats:
            try:
                r = requests.get(url, headers=headers, params=params, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    if data:
                        return data
            except Exception:
                continue
        # Fallback: traer todo y filtrar local
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                out = []
                for d in data:
                    dt = d.get("date")
                    try:
                        dtp = pd.to_datetime(dt, unit="s") if isinstance(dt, (int, float)) else pd.to_datetime(dt)
                    except Exception:
                        continue
                    if start_dt <= dtp <= end_dt:
                        out.append(d)
                return out
        except Exception as e:
            st.warning(f"Error obteniendo libro diario: {e}")
        return []

    # ====== CLASIFICADOR MEJORADO CON MAPEO ESPECÍFICO ======
    def classify_account_with_mapping(code: str, name: str = "") -> tuple:
        """
        Clasifica cuenta usando primero el mapeo específico, luego reglas generales.
        Retorna: (categoria, descripcion_completa)
        """
        # Limpiar código
        code_clean = str(code or "").strip().replace(" ", "")
        
        # 1. Buscar en mapeo específico primero
        if code_clean in ACCOUNT_MAPPING:
            categoria, descripcion = ACCOUNT_MAPPING[code_clean]
            return categoria, f"{code_clean} - {descripcion}"
        
        # 2. Reglas generales por prefijo
        name_clean = str(name or "").lower()
        
        # Extraer solo dígitos iniciales
        digits = re.match(r'^(\d{2,})', code_clean)
        code_num = digits.group(1) if digits else ""
        
        if code_num.startswith("768") or code_num.startswith("668"):
            return "Diferencias de cambio", f"{code_clean} - {name}"
        elif code_num.startswith("76"):
            return "Ingresos financieros", f"{code_clean} - {name}"
        elif code_num.startswith("66"):
            return "Gastos financieros", f"{code_clean} - {name}"
        elif code_num.startswith("64"):
            return "Gastos de personal", f"{code_clean} - {name}"
        elif code_num.startswith(("60", "61")):
            return "Aprovisionamientos", f"{code_clean} - {name}"
        elif code_num.startswith(("62", "63", "65", "68", "69")):
            return "Otros gastos de explotación", f"{code_clean} - {name}"
        elif code_num.startswith("77"):
            return "Otros resultados", f"{code_clean} - {name}"
        elif code_num.startswith(("70", "71", "72", "73", "74", "75")):
            return "Ingresos", f"{code_clean} - {name}"
        elif code_num.startswith("7"):
            return "Ingresos", f"{code_clean} - {name}"
        elif code_num.startswith("6"):
            return "Otros gastos de explotación", f"{code_clean} - {name}"
        
        # 3. Fallback por nombre
        if any(w in name_clean for w in ["nomina", "sueldo", "salario", "personal", "seguridad social"]):
            return "Gastos de personal", f"{code_clean} - {name}"
        elif any(w in name_clean for w in ["interes", "financiero", "prestamo", "credito"]):
            return "Gastos financieros", f"{code_clean} - {name}"
        elif "cambio" in name_clean or "divisa" in name_clean:
            return "Diferencias de cambio", f"{code_clean} - {name}"
        elif any(w in name_clean for w in ["compra", "suministro", "materia prima"]):
            return "Aprovisionamientos", f"{code_clean} - {name}"
        
        return "Otros gastos de explotación", f"{code_clean} - {name or 'Sin descripción'}"

    # ====== BUSCADOR COMPLETO DE GASTOS ======
    @st.cache_data(ttl=60)
    def get_comprehensive_expenses(start_dt: datetime, end_dt: datetime):
        """
        Búsqueda exhaustiva de gastos en todos los endpoints posibles
        """
        headers = {"accept": "application/json", "key": get_holded_token()}
        all_expenses = []
        
        # Endpoints a probar para gastos
        expense_endpoints = [
            "purchase", "bill", "expense", "receipt", 
            "purchaseorder", "creditnote"
        ]
        
        for endpoint in expense_endpoints:
            try:
                st.info(f"🔍 Buscando gastos en: {endpoint}")
                url = f"https://api.holded.com/api/invoicing/v1/documents/{endpoint}"
                
                # Diferentes formatos de filtros de fecha
                date_filters = [
                    {"starttmp": int(start_dt.timestamp()), "endtmp": int(end_dt.timestamp())},
                    {"dateFrom": start_dt.strftime("%Y-%m-%d"), "dateTo": end_dt.strftime("%Y-%m-%d")},
                    {"from": start_dt.strftime("%Y-%m-%d"), "to": end_dt.strftime("%Y-%m-%d")},
                    {}  # Sin filtros
                ]
                
                found_data = False
                for date_filter in date_filters:
                    params = {"limit": 500, "sort": "created-asc", **date_filter}
                    
                    try:
                        response = requests.get(url, headers=headers, params=params, timeout=30)
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, list) and data:
                                # Filtrar por fecha si no se usaron filtros
                                if not date_filter:
                                    filtered_data = []
                                    for doc in data:
                                        doc_date = doc.get("date")
                                        if doc_date:
                                            try:
                                                if isinstance(doc_date, (int, float)):
                                                    parsed_date = pd.to_datetime(doc_date, unit='s')
                                                else:
                                                    parsed_date = pd.to_datetime(doc_date)
                                                
                                                if start_dt <= parsed_date <= end_dt:
                                                    filtered_data.append(doc)
                                            except:
                                                continue
                                    data = filtered_data
                                
                                if data:
                                    st.success(f"✅ {endpoint}: {len(data)} documentos")
                                    all_expenses.extend([(endpoint, doc) for doc in data])
                                    found_data = True
                                    break
                    except Exception as e:
                        continue
                        
                if not found_data:
                    st.warning(f"⚠️ No se encontraron datos en {endpoint}")
                    
            except Exception as e:
                st.error(f"❌ Error en {endpoint}: {str(e)}")
        
        return all_expenses

    # ====== PARSER MEJORADO DE LÍNEAS DE DOCUMENTOS ======
    def parse_document_lines_enhanced(endpoint_type: str, doc_json: dict):
        """
        Parser mejorado que maneja diferentes estructuras de documentos
        """
        lines = []
        if not doc_json:
            return lines
            
        # Obtener fecha del documento
        raw_date = doc_json.get("date")
        if isinstance(raw_date, (int, float)):
            fecha = pd.to_datetime(raw_date, unit='s', errors='coerce')
        else:
            fecha = pd.to_datetime(raw_date, errors='coerce')
        
        if pd.isna(fecha):
            return lines
        
        # Buscar líneas en múltiples campos
        items_keys = ["items", "lines", "concepts", "expenses", "details", "entries"]
        items = []
        
        for key in items_keys:
            if key in doc_json and doc_json[key]:
                items = doc_json[key]
                break
        
        if items and isinstance(items, list):
            # Procesar líneas detalladas
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                # Obtener importe de la línea
                amount = 0.0
                amount_keys = ["subTotal", "subtotal", "untaxedAmount", "netAmount", 
                              "base", "amount", "total", "value", "import"]
                
                for key in amount_keys:
                    if key in item and item[key] is not None:
                        try:
                            amount = float(item[key])
                            break
                        except:
                            continue
                
                # Si no hay importe directo, calcular qty * price
                if amount == 0:
                    try:
                        qty = float(item.get("quantity", item.get("qty", 1)))
                        price_keys = ["unitPrice", "price", "unitprice", "unit_cost", "unitCost"]
                        price = 0
                        for key in price_keys:
                            if key in item and item[key] is not None:
                                price = float(item[key])
                                break
                        amount = qty * price
                    except:
                        continue
                
                if amount == 0:
                    continue
                    
                # Obtener código y nombre de cuenta
                account_code = ""
                account_name = ""
                
                code_keys = ["expenseAccountCode", "accountCode", "expenseAccountId", 
                            "accountId", "account", "expenseAccount"]
                for key in code_keys:
                    if key in item and item[key]:
                        account_code = str(item[key])
                        break
                
                name_keys = ["accountName", "name", "description", "concept", "title"]
                for key in name_keys:
                    if key in item and item[key]:
                        account_name = str(item[key])
                        break
                
                lines.append((fecha, account_code, account_name, float(amount)))
        
        else:
            # Si no hay líneas detalladas, usar el total del documento
            total = 0.0
            total_keys = ["subTotal", "subtotal", "untaxedAmount", "total", 
                         "amount", "netAmount", "baseAmount"]
            
            for key in total_keys:
                if key in doc_json and doc_json[key] is not None:
                    try:
                        total = float(doc_json[key])
                        break
                    except:
                        continue
            
            if total > 0:
                # Inferir cuenta por proveedor o tipo de documento
                account_code = infer_account_from_context(doc_json, endpoint_type)
                account_name = f"Gasto {doc_json.get('contactName', 'sin proveedor')} - {endpoint_type}"
                lines.append((fecha, account_code, account_name, float(total)))
        
        return lines

    # ====== INFERENCIA DE CUENTA POR CONTEXTO ======
    def infer_account_from_context(doc_json: dict, endpoint_type: str) -> str:
        """
        Infiere el código de cuenta basado en el proveedor y tipo de documento
        """
        supplier = str(doc_json.get("contactName", "")).lower()
        description = str(doc_json.get("description", "")).lower()
        
        # Mapeo por proveedor conocido
        supplier_mapping = {
            "ad consulting": "60700017",
            "holded": "62200001",
            "caixabank": "62600001",
            "bbva": "62600002",
            "binance": "62600003",
            "lexus": "62100002",
            "technource": "62300020",
            "itma": "62300021",
            "sensus": "62300001",
        }
        
        for key, account in supplier_mapping.items():
            if key in supplier:
                return account
        
        # Mapeo por palabras clave en descripción
        keyword_mapping = {
            "nomina": "64000000",
            "sueldo": "64000000",
            "salario": "64000000",
            "seguridad social": "64200000",
            "indemnizacion": "64100000",
            "alquiler": "62100001",
            "renting": "62100002",
            "hosting": "62200002",
            "mantenimiento": "62200001",
            "abogado": "62300004",
            "consultor": "62300001",
            "transporte": "62400000",
            "seguro": "62500000",
            "banco": "62600001",
            "publicidad": "62700000",
            "software": "62900001",
            "licencia": "62900001",
            "viaje": "62900003",
            "dieta": "62900004",
            "combustible": "62900006",
            "gasoil": "62900006",
        }
        
        for keyword, account in keyword_mapping.items():
            if keyword in description or keyword in supplier:
                return account
        
        # Fallback por tipo de endpoint
        endpoint_defaults = {
            "purchase": "60000000",  # Compras
            "bill": "62300000",      # Servicios profesionales
            "expense": "62900000",   # Otros gastos
            "receipt": "62900000",   # Otros gastos
        }
        
        return endpoint_defaults.get(endpoint_type, "62900000")

    # ====== VALIDACIÓN Y COMPARACIÓN ======
    def validate_totals_against_expected(df_consolidated: pd.DataFrame):
        """
        Valida los totales obtenidos contra los esperados del Excel
        """
        st.subheader("🔍 Validación de Totales")
        
        # Totales esperados (del Excel)
        expected_totals = {
            "Aprovisionamientos": -9012.02,
            "Gastos de personal": -52201.39,
            "Otros gastos de explotación": -275769.55,
            "Gastos financieros": -890.53,
            "Diferencias de cambio": 10628.19,  # Neto positivo
            "Otros resultados": 259.36,  # Neto (ingresos - gastos excepcionales)
            "Ingresos financieros": 0.18,
        }
        
        # Totales obtenidos
        obtained_totals = df_consolidated.groupby("categoria")["importe"].sum().to_dict()
        
        # Crear tabla de comparación
        comparison_data = []
        total_diff = 0
        
        for categoria, expected in expected_totals.items():
            obtained = obtained_totals.get(categoria, 0)
            difference = obtained - expected
            percentage_diff = (difference / expected * 100) if expected != 0 else 0
            total_diff += abs(difference)
            
            status = "✅" if abs(difference) < 100 else "⚠️" if abs(difference) < 1000 else "❌"
            
            comparison_data.append({
                "Categoría": categoria,
                "Esperado": f"{expected:,.2f} €",
                "Obtenido": f"{obtained:,.2f} €",
                "Diferencia": f"{difference:,.2f} €",
                "% Diff": f"{percentage_diff:.1f}%",
                "Status": status
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True)
        
        # Resumen de validación
        if total_diff < 1000:
            st.success(f"✅ Validación exitosa: Diferencia total < 1.000 € ({total_diff:,.2f} €)")
        elif total_diff < 10000:
            st.warning(f"⚠️ Validación parcial: Diferencia total = {total_diff:,.2f} €")
        else:
            st.error(f"❌ Validación fallida: Diferencia total = {total_diff:,.2f} €")
        
        return df_comparison

    # ====== PROCESADOR PRINCIPAL CORREGIDO ======
    def process_expenses_comprehensive(start_dt: datetime, end_dt: datetime, cliente_filter: str = "Todo"):
        """
        Procesador principal que combina libro diario + documentos
        """
        all_expense_lines = []
        
        st.subheader("📊 Procesamiento Comprehensivo de Gastos")
        
        # PASO 1: LIBRO DIARIO (FUENTE PRINCIPAL)
        with st.expander("📚 Procesando Libro Diario", expanded=True):
            st.info("🔍 Obteniendo entradas del libro diario...")
            
            ledger_entries = list_daily_ledger_corrected(start_dt, end_dt)
            ledger_count = 0
            
            for entry in ledger_entries:
                try:
                    # Fecha
                    entry_date = entry.get("date")
                    if isinstance(entry_date, (int, float)):
                        fecha = pd.to_datetime(entry_date, unit="s", errors="coerce")
                    else:
                        fecha = pd.to_datetime(entry_date, errors="coerce")
                    
                    if pd.isna(fecha):
                        continue
                    
                    # Importe
                    amount = entry.get("amount")
                    if amount is None:
                        debit = float(entry.get("debit", 0) or 0)
                        credit = float(entry.get("credit", 0) or 0)
                        amount = debit - credit
                    else:
                        amount = float(amount)
                    
                    if amount == 0:
                        continue
                    
                    # Cuenta y clasificación
                    account_code = str(entry.get("accountCode", "") or "")
                    account_name = str(entry.get("accountName", "") or "")
                    
                    if not account_code:
                        continue
                    
                    categoria, descripcion_completa = classify_account_with_mapping(account_code, account_name)
                    
                    # Cliente
                    cliente_entry = (entry.get("contactName") or 
                                   entry.get("thirdParty") or 
                                   entry.get("customer") or 
                                   "Libro Diario (sin cliente)")
                    
                    if cliente_filter != "Todo" and cliente_entry != cliente_filter:
                        continue
                    
                    # Normalizar importe según categoría
                    amount_norm = normalize_amount_by_category(categoria, amount)
                    periodo = fecha.to_period("M").strftime("%Y-%m")
                    
                    all_expense_lines.append({
                        "periodo": periodo,
                        "fecha": fecha,
                        "cliente": cliente_entry,
                        "categoria": categoria,
                        "importe": amount_norm,
                        "cuenta": account_code,
                        "descripcion": descripcion_completa,
                        "fuente": "Libro Diario"
                    })
                    ledger_count += 1
                    
                except Exception as e:
                    continue
            
            st.success(f"✅ Procesadas {ledger_count} entradas del libro diario")
        
        # PASO 2: DOCUMENTOS DE GASTOS (FUENTE COMPLEMENTARIA)
        with st.expander("📄 Procesando Documentos de Gastos", expanded=True):
            st.info("🔍 Obteniendo documentos de gastos...")
            
            expense_docs = get_comprehensive_expenses(start_dt, end_dt)
            docs_count = 0
            
            # Obtener cuentas ya procesadas del libro diario para evitar duplicados
            existing_accounts = set()
            for line in all_expense_lines:
                if line["cuenta"]:
                    existing_accounts.add((line["fecha"].date(), line["cuenta"], abs(line["importe"])))
            
            for endpoint_type, doc in expense_docs:
                try:
                    # Filtrar por cliente
                    if cliente_filter != "Todo":
                        doc_cliente = doc.get("contactName", "")
                        if doc_cliente != cliente_filter:
                            continue
                    
                    # Obtener detalle del documento
                    doc_id = str(doc.get("id", ""))
                    if doc_id:
                        detail = get_document_detail_corrected(endpoint_type, doc_id)
                        if detail:
                            doc = detail
                    
                    # Procesar líneas del documento
                    doc_lines = parse_document_lines_enhanced(endpoint_type, doc)
                    
                    for fecha, account_code, account_name, amount in doc_lines:
                        if pd.isna(fecha) or amount == 0:
                            continue
                        
                        # Evitar duplicados con libro diario
                        line_key = (fecha.date(), account_code, abs(amount))
                        if line_key in existing_accounts:
                            continue
                        
                        categoria, descripcion_completa = classify_account_with_mapping(account_code, account_name)
                        
                        proveedor = doc.get("contactName", "Sin nombre")
                        periodo = fecha.to_period("M").strftime("%Y-%m")
                        amount_norm = normalize_amount_by_category(categoria, amount)
                        
                        all_expense_lines.append({
                            "periodo": periodo,
                            "fecha": fecha,
                            "cliente": proveedor,
                            "categoria": categoria,
                            "importe": amount_norm,
                            "cuenta": account_code or f"{endpoint_type.upper()}XXX",
                            "descripcion": descripcion_completa,
                            "fuente": f"Documento {endpoint_type}"
                        })
                        docs_count += 1
                        
                except Exception as e:
                    continue
            
            st.success(f"✅ Procesadas {docs_count} líneas de documentos")
        
        return all_expense_lines

    # ====== FUNCIÓN PRINCIPAL MEJORADA ======
    def process_pl_holded_comprehensive(inicio_dt: datetime, fin_dt: datetime, cliente_pl: str, usar_libro_diario: bool = True):
        """
        Función principal que procesa P&L de forma comprehensiva
        """
        all_data = []
        
        try:
            # 1) INGRESOS (facturas de venta)
            st.info("📥 Procesando ingresos...")
            df_invoices = list_documents_corrected("invoice", inicio_dt, fin_dt)
            
            ingresos_data = []
            if not df_invoices.empty:
                for _, inv in df_invoices.iterrows():
                    inv_date = inv.get("date")
                    fecha = pd.to_datetime(inv_date, unit="s", errors="coerce") if isinstance(inv_date, (int, float)) else pd.to_datetime(inv_date, errors="coerce")
                    if pd.isna(fecha):
                        continue
                        
                    amount = 0.0
                    for k in ("subTotal", "subtotal", "untaxedAmount", "total"):
                        if k in inv and inv[k] is not None:
                            try:
                                amount = float(inv[k])
                                break
                            except:
                                pass
                    
                    cliente = inv.get("contactName", "Sin nombre")
                    if cliente_pl != "Todo" and cliente != cliente_pl:
                        continue
                    
                    periodo = fecha.to_period("M").strftime("%Y-%m")
                    amount_norm = normalize_amount_by_category("Ingresos", amount)
                    
                    ingresos_data.append({
                        "periodo": periodo,
                        "fecha": fecha,
                        "cliente": cliente,
                        "categoria": "Ingresos",
                        "importe": amount_norm,
                        "cuenta": "70XXX",
                        "descripcion": f"Factura {inv.get('docNumber', '')}",
                        "fuente": "Factura Venta"
                    })
            
            st.success(f"✅ Procesados {len(ingresos_data)} ingresos")
            all_data.extend(ingresos_data)
            
            # 2) GASTOS (usando función comprehensiva)
            st.info("📤 Procesando gastos...")
            gastos_data = process_expenses_comprehensive(inicio_dt, fin_dt, cliente_pl)
            st.success(f"✅ Procesados {len(gastos_data)} gastos")
            all_data.extend(gastos_data)
            
            # 3) CONSOLIDAR DATOS
            df_consolidated = pd.DataFrame(all_data)
            
            if df_consolidated.empty:
                st.warning("⚠️ No se encontraron datos en el período seleccionado")
                return pd.DataFrame()
            
            # 4) VALIDAR CONTRA TOTALES ESPERADOS
            validate_totals_against_expected(df_consolidated)
            
            # 5) MOSTRAR RESUMEN POR FUENTE
            st.subheader("📊 Resumen por Fuente de Datos")
            source_summary = df_consolidated.groupby(["fuente", "categoria"])["importe"].sum().unstack(fill_value=0)
            st.dataframe(source_summary, use_container_width=True)
            
            return df_consolidated
            
        except Exception as e:
            st.error(f"❌ Error en procesamiento comprehensivo: {str(e)}")
            st.exception(e)
            return pd.DataFrame()

    # ====== UTILIDADES ADICIONALES ======
    def normalize_amount_by_category(cat: str, amount: float) -> float:
        """Normaliza importes según categoría"""
        amount = float(amount or 0)
        expense_cats = {"Aprovisionamientos", "Gastos de personal", "Otros gastos de explotación", "Gastos financieros"}
        income_cats = {"Ingresos", "Ingresos financieros"}
        
        if cat in expense_cats:
            return -abs(amount)
        elif cat in income_cats:
            return abs(amount)
        else:
            return amount  # Mantener signo original para diferencias de cambio y otros resultados

    def _strip_accents(s: str) -> str:
        s = str(s or "")
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

    def _only_leading_digits(code: str) -> str:
        code = str(code or "").strip().replace("\xa0", " ")
        m = re.match(r"^([0-9]{2,})", code)
        return m.group(1) if m else ""

    # ====== FUNCIONES PARA P&L MENSUAL CON EVOLUCIÓN ======
    def create_monthly_pl_analysis(df_consolidated: pd.DataFrame, inicio_dt: datetime, fin_dt: datetime):
        """
        Crea análisis P&L mensual con evolución temporal y gráficos
        """
        if df_consolidated.empty:
            st.warning("No hay datos para el análisis mensual")
            return None, None, None
        
        # Crear rango de meses para el período seleccionado
        date_range = pd.date_range(start=inicio_dt, end=fin_dt, freq='MS')
        month_labels = [d.strftime('%Y-%m') for d in date_range]
        month_names = [d.strftime('%B %Y') for d in date_range]
        
        # Preparar datos por mes
        df_monthly = df_consolidated.copy()
        df_monthly['mes_num'] = df_monthly['fecha'].dt.to_period('M').astype(str)
        
        # Agrupar por mes y categoría
        monthly_summary = df_monthly.groupby(['mes_num', 'categoria'])['importe'].sum().unstack(fill_value=0)
        
        # Asegurar que todos los meses están presentes
        monthly_summary = monthly_summary.reindex(month_labels, fill_value=0)
        
        # Categorías principales
        main_categories = [
            "Ingresos", "Aprovisionamientos", "Gastos de personal",
            "Otros gastos de explotación", "Ingresos financieros",
            "Gastos financieros", "Diferencias de cambio", "Otros resultados"
        ]
        
        # Añadir categorías faltantes con valor 0
        for cat in main_categories:
            if cat not in monthly_summary.columns:
                monthly_summary[cat] = 0.0
        
        # Calcular métricas derivadas
        monthly_summary["Margen Bruto"] = monthly_summary["Ingresos"] + monthly_summary["Aprovisionamientos"]
        monthly_summary["Total Gastos Operativos"] = (monthly_summary["Gastos de personal"] + 
                                                      monthly_summary["Otros gastos de explotación"])
        monthly_summary["EBITDA"] = monthly_summary["Margen Bruto"] + monthly_summary["Total Gastos Operativos"]
        monthly_summary["Resultado Operativo"] = monthly_summary["EBITDA"] + monthly_summary["Otros resultados"]
        monthly_summary["Resultado Financiero"] = (monthly_summary["Ingresos financieros"] + 
                                                  monthly_summary["Gastos financieros"] + 
                                                  monthly_summary["Diferencias de cambio"])
        monthly_summary["Resultado Neto"] = monthly_summary["Resultado Operativo"] + monthly_summary["Resultado Financiero"]
        
        # Calcular acumulado
        cumulative_summary = monthly_summary.cumsum()
        
        # Reset index para trabajar mejor con los datos
        monthly_summary.reset_index(inplace=True)
        cumulative_summary.reset_index(inplace=True)
        
        # Añadir nombres de meses para mejor visualización
        month_mapping = dict(zip(month_labels, month_names))
        monthly_summary['Mes'] = monthly_summary['mes_num'].map(month_mapping)
        cumulative_summary['Mes'] = cumulative_summary['mes_num'].map(month_mapping)
        
        return monthly_summary, cumulative_summary, month_names

    def display_monthly_kpis(monthly_summary: pd.DataFrame, cumulative_summary: pd.DataFrame):
        """
        Muestra KPIs mensuales y acumulados
        """
        st.subheader("📊 KPIs - Último Mes vs Acumulado")
        
        # Último mes con datos
        last_month_data = monthly_summary.iloc[-1]
        cumulative_data = cumulative_summary.iloc[-1]
        
        # Crear métricas en columnas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💰 Ingresos (Último Mes)", 
                f"${last_month_data['Ingresos']:,.0f}",
                help=f"Acumulado: ${cumulative_data['Ingresos']:,.0f}"
            )
            
        with col2:
            st.metric(
                "📈 Margen Bruto (Último Mes)", 
                f"${last_month_data['Margen Bruto']:,.0f}",
                help=f"Acumulado: ${cumulative_data['Margen Bruto']:,.0f}"
            )
            
        with col3:
            st.metric(
                "🎯 EBITDA (Último Mes)", 
                f"${last_month_data['EBITDA']:,.0f}",
                help=f"Acumulado: ${cumulative_data['EBITDA']:,.0f}"
            )
            
        with col4:
            st.metric(
                "💎 Resultado Neto (Último Mes)", 
                f"${last_month_data['Resultado Neto']:,.0f}",
                help=f"Acumulado: ${cumulative_data['Resultado Neto']:,.0f}"
            )

    def create_evolution_charts(monthly_summary: pd.DataFrame):
        """
        Crea gráficos de evolución temporal
        """
        st.subheader("📈 Evolución Temporal - Gráficos Interactivos")
        
        # Preparar datos para gráficos
        chart_data_monthly = monthly_summary[['Mes', 'Ingresos', 'Margen Bruto', 'EBITDA', 'Resultado Neto']].copy()
        
        # Convertir a formato largo para Altair
        chart_data_long = chart_data_monthly.melt(
            id_vars=['Mes'], 
            value_vars=['Ingresos', 'Margen Bruto', 'EBITDA', 'Resultado Neto'],
            var_name='Métrica', 
            value_name='Valor'
        )
        
        # Gráfico de líneas principal
        line_chart = alt.Chart(chart_data_long).mark_line(point=True, strokeWidth=3).encode(
            x=alt.X('Mes:O', title='Período', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Valor:Q', title='Importe ($)', axis=alt.Axis(format='$,.0f')),
            color=alt.Color('Métrica:N', 
                           scale=alt.Scale(range=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']),
                           legend=alt.Legend(title="Métricas")),
            tooltip=['Mes:O', 'Métrica:N', alt.Tooltip('Valor:Q', format='$,.0f')]
        ).properties(
            width=700,
            height=400,
            title="Evolución Mensual de Métricas Clave"
        )
        
        st.altair_chart(line_chart, use_container_width=True)

    def generate_monthly_pl_analysis(df_consolidated: pd.DataFrame, inicio_dt: datetime, fin_dt: datetime):
        """
        Función principal que genera todo el análisis mensual
        """
        if df_consolidated.empty:
            st.warning("No hay datos para el análisis mensual")
            return
        
        # Crear análisis mensual
        monthly_summary, cumulative_summary, month_names = create_monthly_pl_analysis(df_consolidated, inicio_dt, fin_dt)
        
        if monthly_summary is None:
            return
        
        # Mostrar KPIs
        display_monthly_kpis(monthly_summary, cumulative_summary)
        
        # Mostrar gráficos
        create_evolution_charts(monthly_summary)
        
        # Mostrar tabla mensual
        st.subheader("📋 Tabla P&L Mensual")
        
        # Seleccionar columnas principales para mostrar
        display_columns = ['Mes', 'Ingresos', 'Margen Bruto', 'EBITDA', 'Resultado Neto']
        df_display = monthly_summary[display_columns].copy()
        
        # Formatear números
        for col in ['Ingresos', 'Margen Bruto', 'EBITDA', 'Resultado Neto']:
            df_display[col] = df_display[col].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(df_display, use_container_width=True, height=400)

    # ====== FUNCIÓN PARA GENERAR REPORTE PGC ======
    def generate_pgc_report(df_data: pd.DataFrame, inicio_dt: datetime, fin_dt: datetime):
        """Genera un reporte en formato PGC español"""
        
        st.subheader("📋 Estado de Pérdidas y Ganancias (Formato PGC)")
        st.caption(f"Período: {inicio_dt.strftime('%d/%m/%Y')} - {fin_dt.strftime('%d/%m/%Y')}")
        
        # Agrupar por cuenta y categoría
        df_cuentas = df_data.groupby(["categoria", "cuenta", "descripcion"])["importe"].sum().reset_index()
        df_cuentas = df_cuentas[df_cuentas["importe"] != 0].sort_values(["categoria", "cuenta"])
        
        # Totales por categoría
        totales = df_data.groupby("categoria")["importe"].sum()
        
        # === ESTRUCTURA PGC ===
        pgc_structure = [
            ("1. IMPORTE NETO DE LA CIFRA DE NEGOCIOS", "Ingresos"),
            ("4. APROVISIONAMIENTOS", "Aprovisionamientos"),
            ("A) RESULTADO BRUTO", None),  # Calculado
            ("6. GASTOS DE PERSONAL", "Gastos de personal"),
            ("7. OTROS GASTOS DE EXPLOTACIÓN", "Otros gastos de explotación"),
            ("B) RESULTADO DE EXPLOTACIÓN", None),  # Calculado
            ("13. OTROS RESULTADOS", "Otros resultados"),
            ("C) RESULTADO OPERATIVO", None),  # Calculado
            ("14. INGRESOS FINANCIEROS", "Ingresos financieros"),
            ("15. GASTOS FINANCIEROS", "Gastos financieros"),
            ("17. DIFERENCIAS DE CAMBIO", "Diferencias de cambio"),
            ("D) RESULTADO FINANCIERO", None),  # Calculado
            ("E) RESULTADO ANTES DE IMPUESTOS", None),  # Calculado
        ]
        
        # Crear el reporte
        reporte_data = []
        
        for titulo, categoria in pgc_structure:
            if categoria:  # Es una categoría real
                valor = totales.get(categoria, 0)
                reporte_data.append({
                    "Concepto": titulo,
                    "Importe": valor,
                    "Tipo": "categoria"
                })
                
                # Mostrar detalle de cuentas
                cuentas_cat = df_cuentas[df_cuentas["categoria"] == categoria]
                for _, row in cuentas_cat.iterrows():
                    if abs(row["importe"]) > 0.01:  # Solo mostrar importes significativos
                        reporte_data.append({
                            "Concepto": f"  {row['cuenta']} - {row['descripcion'][:50]}",
                            "Importe": row["importe"],
                            "Tipo": "cuenta"
                        })
            
            else:  # Es un subtotal calculado
                if "RESULTADO BRUTO" in titulo:
                    valor = totales.get("Ingresos", 0) + totales.get("Aprovisionamientos", 0)
                elif "RESULTADO DE EXPLOTACIÓN" in titulo:
                    valor = (totales.get("Ingresos", 0) + 
                            totales.get("Aprovisionamientos", 0) +
                            totales.get("Gastos de personal", 0) +
                            totales.get("Otros gastos de explotación", 0))
                elif "RESULTADO OPERATIVO" in titulo:
                    valor = (totales.get("Ingresos", 0) + 
                            totales.get("Aprovisionamientos", 0) +
                            totales.get("Gastos de personal", 0) +
                            totales.get("Otros gastos de explotación", 0) +
                            totales.get("Otros resultados", 0))
                elif "RESULTADO FINANCIERO" in titulo:
                    valor = (totales.get("Ingresos financieros", 0) +
                            totales.get("Gastos financieros", 0) +
                            totales.get("Diferencias de cambio", 0))
                elif "RESULTADO ANTES DE IMPUESTOS" in titulo:
                    valor = (totales.get("Ingresos", 0) + 
                            totales.get("Aprovisionamientos", 0) +
                            totales.get("Gastos de personal", 0) +
                            totales.get("Otros gastos de explotación", 0) +
                            totales.get("Otros resultados", 0) +
                            totales.get("Ingresos financieros", 0) +
                            totales.get("Gastos financieros", 0) +
                            totales.get("Diferencias de cambio", 0))
                
                reporte_data.append({
                    "Concepto": titulo,
                    "Importe": valor,
                    "Tipo": "subtotal"
                })
        
        # Mostrar el reporte
        df_reporte = pd.DataFrame(reporte_data)
        
        def format_row(row):
            if row["Tipo"] == "subtotal":
                return f"**{row['Concepto']}** | **{row['Importe']:,.2f} €**"
            elif row["Tipo"] == "categoria":
                return f"**{row['Concepto']}** | {row['Importe']:,.2f} €"
            else:
                return f"{row['Concepto']} | {row['Importe']:,.2f} €"
        
        for _, row in df_reporte.iterrows():
            st.write(format_row(row))
        
        # Métricas clave
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ingresos = totales.get("Ingresos", 0)
            st.metric("💰 Ingresos Netos", f"{ingresos:,.2f} €")
            
        with col2:
            resultado_bruto = ingresos + totales.get("Aprovisionamientos", 0)
            margen_bruto = (resultado_bruto / ingresos * 100) if ingresos > 0 else 0
            st.metric("📈 Resultado Bruto", f"{resultado_bruto:,.2f} €", f"{margen_bruto:.1f}%")
            
        with col3:
            resultado_final = sum(totales.get(cat, 0) for cat in totales.index)
            margen_final = (resultado_final / ingresos * 100) if ingresos > 0 else 0
            st.metric("🎯 Resultado Final", f"{resultado_final:,.2f} €", f"{margen_final:.1f}%")
        
        # Exportar datos
        if st.button("📥 Descargar Reporte PGC"):
            csv_data = df_reporte.to_csv(index=False, sep=';', decimal=',')
            st.download_button(
                label="💾 Descargar CSV",
                data=csv_data,
                file_name=f"PyG_PGC_{inicio_dt.strftime('%Y%m%d')}_{fin_dt.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    # ====== INTERFAZ (FILTROS) ======
    st.sidebar.markdown("---")
    st.sidebar.header("📑 Filtros P&L Holded")

    hoy = datetime.today()
    primer_dia_mes = hoy.replace(day=1)

    if "pl_fecha_inicio" not in st.session_state:
        st.session_state.pl_fecha_inicio = primer_dia_mes.date()
    if "pl_fecha_fin" not in st.session_state:
        st.session_state.pl_fecha_fin = hoy.date()

    fecha_inicio_pl = st.sidebar.date_input("Fecha Inicio P&L", value=st.session_state.pl_fecha_inicio, key="pl_inicio_input")
    fecha_fin_pl = st.sidebar.date_input("Fecha Fin P&L", value=st.session_state.pl_fecha_fin, key="pl_fin_input")

    if fecha_inicio_pl != st.session_state.pl_fecha_inicio:
        st.session_state.pl_fecha_inicio = fecha_inicio_pl
        st.session_state.pl_data_updated = False
    if fecha_fin_pl != st.session_state.pl_fecha_fin:
        st.session_state.pl_fecha_fin = fecha_fin_pl
        st.session_state.pl_data_updated = False

    if fecha_inicio_pl > fecha_fin_pl:
        st.sidebar.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
        st.stop()

    # Cargar clientes dinámicamente para filtro
    df_invoices_for_clients = list_documents_corrected(
        "invoice",
        datetime.combine(fecha_inicio_pl, datetime.min.time()),
        datetime.combine(fecha_fin_pl, datetime.max.time())
    )

    clientes_invoices = df_invoices_for_clients["contactName"].dropna().unique().tolist() if not df_invoices_for_clients.empty else []

    clientes_unicos = sorted(set(clientes_invoices))
    clientes_pl_3 = ["Todo"] + clientes_unicos

    if "pl_cliente_sel" not in st.session_state:
        st.session_state.pl_cliente_sel = "Todo"

    col1, = st.columns([1])
    cliente_pl = col1.selectbox("Cliente (Tab 3)", clientes_pl_3, index=0, key="tab3_cliente_select")

    if cliente_pl != st.session_state.pl_cliente_sel:
        st.session_state.pl_cliente_sel = cliente_pl
        st.session_state.pl_data_updated = False

    usar_libro_diario = st.sidebar.checkbox("Usar Libro Diario", value=True, key="usar_libro")
    mostrar_detalle_cuentas = st.sidebar.checkbox("Mostrar Detalle por Cuenta", value=False, key="mostrar_detalle")

    if st.sidebar.button("🔄 Actualizar P&L", type="primary"):
        st.session_state.pl_data_updated = False
        list_documents_corrected.clear()
        get_document_detail_corrected.clear()
        list_daily_ledger_corrected.clear()
        get_comprehensive_expenses.clear()

    st.sidebar.info(f"**Filtros activos:**\n- Período: {fecha_inicio_pl} a {fecha_fin_pl}\n- Cliente: {cliente_pl}\n- Libro diario: {'Sí' if usar_libro_diario else 'No'}")

    # ====== PROCESAMIENTO PRINCIPAL ======
    inicio_dt = datetime.combine(fecha_inicio_pl, datetime.min.time())
    fin_dt = datetime.combine(fecha_fin_pl, datetime.max.time())

    if not st.session_state.get("pl_data_updated", False):
        try:
            with st.spinner("Procesando P&L comprehensivo..."):
                # PROCESAMIENTO COMPREHENSIVO (reemplaza todo el procesamiento anterior)
                df_consolidated = process_pl_holded_comprehensive(inicio_dt, fin_dt, cliente_pl, usar_libro_diario)
                
                if df_consolidated.empty:
                    st.warning("⚠️ No se encontraron datos en el período seleccionado")
                    st.session_state.pl_data_updated = True
                    st.stop()

                st.session_state.df_pl_consolidated = df_consolidated
                st.session_state.pl_data_updated = True

                # Debug resumen
                categories_summary = df_consolidated.groupby("categoria")["importe"].sum()
                st.write("🔎 Resumen por Categoría:", categories_summary.to_dict())

        except Exception as e:
            st.error(f"❌ Error procesando datos: {str(e)}")
            st.exception(e)
            st.stop()

    # ====== MOSTRAR RESULTADOS ======
    tab_pgc, tab_actual, tab_mensual = st.tabs(["📋 Formato PGC", "📊 Dashboard Actual", "📅 Análisis Mensual"])
    
    with tab_pgc:
        if st.session_state.get("pl_data_updated", False):
            df_data = st.session_state.get("df_pl_consolidated", pd.DataFrame())
            if not df_data.empty:
                generate_pgc_report(df_data, inicio_dt, fin_dt)
    
    with tab_actual:
        if st.session_state.get("pl_data_updated", False):
            df_data = st.session_state.get("df_pl_consolidated", pd.DataFrame())
            if not df_data.empty:
                df_pl_summary = df_data.groupby(["periodo", "categoria"])["importe"].sum().unstack(fill_value=0).reset_index()

                required_columns = [
                    "Ingresos", "Aprovisionamientos", "Gastos de personal",
                    "Otros gastos de explotación", "Ingresos financieros",
                    "Gastos financieros", "Diferencias de cambio", "Otros resultados"
                ]
                for col in required_columns:
                    if col not in df_pl_summary.columns:
                        df_pl_summary[col] = 0.0

                # KPIs (gastos ya son negativos por normalización)
                df_pl_summary["Margen Bruto"] = df_pl_summary["Ingresos"] + df_pl_summary["Aprovisionamientos"]
                df_pl_summary["EBITDA"] = (df_pl_summary["Margen Bruto"] +
                                           df_pl_summary["Gastos de personal"] +
                                           df_pl_summary["Otros gastos de explotación"])
                df_pl_summary["Resultado Operativo"] = df_pl_summary["EBITDA"] + df_pl_summary["Otros resultados"]
                df_pl_summary["Resultado Financiero"] = (df_pl_summary["Ingresos financieros"] +
                                                         df_pl_summary["Gastos financieros"] +
                                                         df_pl_summary["Diferencias de cambio"])
                df_pl_summary["Resultado Neto"] = df_pl_summary["Resultado Operativo"] + df_pl_summary["Resultado Financiero"]

                st.subheader("📊 Resumen P&L")
                totales = df_pl_summary.select_dtypes(include=[float, int]).sum()
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("💰 Ingresos", f"${totales['Ingresos']:,.2f}")
                col2.metric("📈 Margen Bruto", f"${totales['Margen Bruto']:,.2f}")
                col3.metric("🎯 EBITDA", f"${totales['EBITDA']:,.2f}")
                col4.metric("💎 Resultado Neto", f"${totales['Resultado Neto']:,.2f}")

                if totales['Ingresos'] > 0:
                    col5, col6, col7, col8 = st.columns(4)
                    col5.metric("Margen %", f"{(totales['Margen Bruto']/totales['Ingresos']*100):.1f}%")
                    col6.metric("EBITDA %", f"{(totales['EBITDA']/totales['Ingresos']*100):.1f}%")
                    col7.metric("Resultado %", f"{(totales['Resultado Neto']/totales['Ingresos']*100):.1f}%")
                    gp = abs(totales['Gastos de personal'])
                    if gp > 0:
                        col8.metric("Personal %", f"{(gp/totales['Ingresos']*100):.1f}%")

                st.subheader("📋 P&L Detallado")
                display_columns = [
                    "periodo", "Ingresos", "Aprovisionamientos", "Margen Bruto",
                    "Gastos de personal", "Otros gastos de explotación", "EBITDA",
                    "Ingresos financieros", "Gastos financieros", "Diferencias de cambio",
                    "Resultado Financiero", "Otros resultados", "Resultado Operativo", "Resultado Neto"
                ]
                df_display = df_pl_summary[display_columns].copy().round(2)
                df_display.columns = [col.replace('periodo', '🗓️ Período') for col in df_display.columns]
                st.dataframe(df_display, use_container_width=True, height=400)

                if len(df_pl_summary) > 1:
                    st.subheader("📈 Evolución Temporal")
                    chart_metrics = ["Ingresos", "Margen Bruto", "EBITDA", "Resultado Neto"]
                    chart_data = df_pl_summary[["periodo"] + chart_metrics].melt(
                        id_vars=["periodo"], var_name="Métrica", value_name="Valor"
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

                if mostrar_detalle_cuentas:
                    st.subheader("🔍 Detalle por Cuenta Contable")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    categorias_disponibles = ["Todas"] + sorted(df_data["categoria"].unique().tolist())
                    cat_filter = col_f1.selectbox("Categoría", categorias_disponibles, key="cat_detail")
                    periodos_disponibles = ["Todos"] + sorted(df_data["periodo"].unique().tolist())
                    periodo_filter = col_f2.selectbox("Período", periodos_disponibles, key="periodo_detail")
                    clientes_disponibles = ["Todos"] + sorted(df_data["cliente"].unique().tolist())
                    cliente_detail_filter = col_f3.selectbox("Cliente", clientes_disponibles, key="cliente_detail")

                    df_filtered = df_data.copy()
                    if cat_filter != "Todas":
                        df_filtered = df_filtered[df_filtered["categoria"] == cat_filter]
                    if periodo_filter != "Todos":
                        df_filtered = df_filtered[df_filtered["periodo"] == periodo_filter]
                    if cliente_detail_filter != "Todos":
                        df_filtered = df_filtered[df_filtered["cliente"] == cliente_detail_filter]

                    if not df_filtered.empty:
                        df_detail_display = df_filtered[["periodo", "cliente", "categoria", "cuenta", "descripcion", "importe", "fuente"]].copy()
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
                                    y=alt.Y("categoria:N", sort="-x", title="Categoría")
                                )
                                .properties(height=300)
                            )
                            st.altair_chart(chart_cat, use_container_width=True)
                    else:
                        st.info("No hay datos que coincidan con los filtros seleccionados.")
            else:
                st.warning("⚠️ No hay datos consolidados disponibles.")
        else:
            st.info("👆 Usa los filtros del sidebar y presiona 'Actualizar P&L' para cargar los datos.")
    
    with tab_mensual:
        if st.session_state.get("pl_data_updated", False):
            df_data = st.session_state.get("df_pl_consolidated", pd.DataFrame())
            if not df_data.empty:
                # Verificar que hay más de un mes de datos
                meses_unicos = df_data['fecha'].dt.to_period('M').nunique()
                
                if meses_unicos > 1:
                    generate_monthly_pl_analysis(df_data, inicio_dt, fin_dt)
                else:
                    st.info("📅 El análisis mensual requiere datos de al menos 2 meses. Selecciona un período más amplio.")
            else:
                st.warning("⚠️ No hay datos consolidados disponibles.")
        else:
            st.info("👆 Usa los filtros del sidebar y presiona 'Actualizar P&L' para cargar los datos.")

    # ====== DIAGNÓSTICOS AVANZADOS ======
    st.markdown("---")
    st.header("🔧 Diagnósticos Avanzados")
    
    # Función para diagnosticar aprovisionamientos
    def diagnose_aprovisionamientos_issues(df_consolidated: pd.DataFrame):
        """
        Diagnóstico detallado de aprovisionamientos para detectar duplicados y errores
        """
        st.subheader("🔍 Diagnóstico de Aprovisionamientos")
        
        if df_consolidated.empty:
            st.warning("No hay datos para diagnosticar")
            return
        
        # Filtrar solo aprovisionamientos
        df_aprov = df_consolidated[df_consolidated["categoria"] == "Aprovisionamientos"].copy()
        
        if df_aprov.empty:
            st.info("No se encontraron aprovisionamientos en los datos")
            return
        
        # === ANÁLISIS GENERAL ===
        total_aprov = df_aprov["importe"].sum()
        expected_aprov = -9012.02  # Del Excel
        difference = total_aprov - expected_aprov
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Obtenido", f"{total_aprov:,.2f} €")
        col2.metric("🎯 Total Esperado", f"{expected_aprov:,.2f} €")
        col3.metric("⚠️ Diferencia", f"{difference:,.2f} €", 
                    delta=f"{(difference/expected_aprov*100):.1f}%" if expected_aprov != 0 else "N/A")
        
        # === VERIFICACIÓN CUENTA ESPECÍFICA ===
        st.subheader("🎯 Verificación Cuenta AD CONSULTING (60700017)")
        
        ad_consulting = df_aprov[df_aprov['cuenta'] == '60700017'].copy()
        
        if ad_consulting.empty:
            st.error("❌ No se encontró la cuenta 60700017 - Trabajos realizados por AD CONSULTING")
            
            # Buscar variaciones posibles
            possible_variants = df_consolidated[df_consolidated['descripcion'].str.contains('AD CONSULTING', case=False, na=False)]
            if not possible_variants.empty:
                st.warning("⚠️ Se encontraron estas variaciones:")
                st.dataframe(possible_variants[['cuenta', 'descripcion', 'importe', 'fuente']])
        else:
            st.success("✅ Cuenta 60700017 encontrada")
            
            total_ad = ad_consulting['importe'].sum()
            expected_ad = -9012.02
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total AD Consulting", f"{total_ad:,.2f} €")
            col2.metric("Esperado AD Consulting", f"{expected_ad:,.2f} €") 
            col3.metric("Diferencia AD", f"{total_ad - expected_ad:,.2f} €")
            
            # Mostrar detalle
            st.dataframe(ad_consulting[['fecha', 'periodo', 'importe', 'fuente', 'cliente']])
        
        # === DETALLE POR CUENTA ===
        st.subheader("📋 Detalle por Cuenta")
        
        cuenta_summary = df_aprov.groupby(["cuenta", "descripcion"]).agg({
            "importe": ["sum", "count"],
            "fuente": lambda x: ", ".join(x.unique()),
            "fecha": ["min", "max"]
        }).round(2)
        
        # Aplanar columnas
        cuenta_summary.columns = ["Total", "Cantidad_Registros", "Fuentes", "Fecha_Min", "Fecha_Max"]
        cuenta_summary = cuenta_summary.reset_index()
        
        st.dataframe(cuenta_summary, use_container_width=True)
        
        # === DETECCIÓN DE DUPLICADOS ===
        st.subheader("🚨 Detección de Posibles Duplicados")
        
        # Buscar registros con mismo importe, fecha y cuenta
        df_aprov['fecha_str'] = df_aprov['fecha'].dt.strftime('%Y-%m-%d')
        df_aprov['importe_abs'] = df_aprov['importe'].abs()
        
        # Agrupar por fecha, cuenta e importe para detectar duplicados
        duplicados = df_aprov.groupby(['fecha_str', 'cuenta', 'importe_abs']).agg({
            'importe': 'sum',
            'fuente': lambda x: list(x),
            'descripcion': 'first',
            'cliente': 'first'
        }).reset_index()
        
        # Filtrar solo los que aparecen en múltiples fuentes
        duplicados['num_fuentes'] = duplicados['fuente'].apply(len)
        posibles_duplicados = duplicados[duplicados['num_fuentes'] > 1]
        
        if not posibles_duplicados.empty:
            st.error(f"⚠️ Encontrados {len(posibles_duplicados)} posibles duplicados:")
            
            # Mostrar duplicados
            duplicados_display = posibles_duplicados[['fecha_str', 'cuenta', 'descripcion', 'importe_abs', 'fuente', 'importe']].copy()
            duplicados_display.columns = ['Fecha', 'Cuenta', 'Descripción', 'Importe_Original', 'Fuentes', 'Total_Duplicado']
            st.dataframe(duplicados_display, use_container_width=True)
            
            # Calcular impacto de duplicados
            impacto_duplicados = posibles_duplicados['importe'].sum() / 2  # Dividir por 2 porque está duplicado
            st.error(f"💸 Impacto estimado de duplicados: {impacto_duplicados:,.2f} €")
            
            # Nuevo total sin duplicados
            total_corregido = total_aprov - impacto_duplicados
            st.success(f"✅ Total corregido (sin duplicados): {total_corregido:,.2f} €")
            st.success(f"📊 Diferencia con Excel después de corrección: {total_corregido - expected_aprov:,.2f} €")
            
            return posibles_duplicados
            
        else:
            st.success("✅ No se detectaron duplicados obvios en aprovisionamientos")
        
        # === ANÁLISIS POR FUENTE ===
        st.subheader("📊 Análisis por Fuente de Datos")
        
        fuente_summary = df_aprov.groupby("fuente")["importe"].agg(["sum", "count"]).round(2)
        fuente_summary.columns = ["Total", "Cantidad"]
        fuente_summary = fuente_summary.reset_index()
        
        st.dataframe(fuente_summary, use_container_width=True)
        
        return None

    def fix_aprovisionamientos_duplicates(df_consolidated: pd.DataFrame):
        """
        Función para corregir duplicados en aprovisionamientos
        """
        if df_consolidated.empty:
            return df_consolidated
        
        # Crear copia para no modificar el original
        df_fixed = df_consolidated.copy()
        
        # Filtrar aprovisionamientos
        df_aprov = df_fixed[df_fixed["categoria"] == "Aprovisionamientos"].copy()
        df_otros = df_fixed[df_fixed["categoria"] != "Aprovisionamientos"].copy()
        
        if df_aprov.empty:
            return df_consolidated
        
        # Detectar duplicados
        df_aprov['fecha_str'] = df_aprov['fecha'].dt.strftime('%Y-%m-%d')
        df_aprov['importe_abs'] = df_aprov['importe'].abs()
        df_aprov['duplicate_key'] = df_aprov['fecha_str'] + '_' + df_aprov['cuenta'] + '_' + df_aprov['importe_abs'].astype(str)
        
        # Remover duplicados manteniendo solo el del libro diario (más confiable)
        df_aprov['fuente_priority'] = df_aprov['fuente'].map({
            'Libro Diario': 1,
            'Documento purchase': 2,
            'Documento bill': 3,
            'Documento expense': 4,
            'Factura Venta': 5
        })
        
        # Ordenar por prioridad y mantener solo el primero de cada grupo
        df_aprov_sorted = df_aprov.sort_values(['duplicate_key', 'fuente_priority'])
        df_aprov_fixed = df_aprov_sorted.groupby('duplicate_key').first().reset_index()
        
        # Eliminar columnas auxiliares
        df_aprov_fixed = df_aprov_fixed.drop(['fecha_str', 'importe_abs', 'duplicate_key', 'fuente_priority'], axis=1)
        
        # Recombinar datos
        df_result = pd.concat([df_otros, df_aprov_fixed], ignore_index=True)
        
        return df_result

    # Botón para diagnosticar aprovisionamientos
    col_diag1, col_diag2, col_diag3 = st.columns(3)
    
    with col_diag1:
        if st.button("🔍 Diagnosticar Aprovisionamientos", type="secondary"):
            if st.session_state.get("pl_data_updated", False):
                df_data = st.session_state.get("df_pl_consolidated", pd.DataFrame())
                if not df_data.empty:
                    with st.expander("📋 Diagnóstico de Aprovisionamientos", expanded=True):
                        duplicados_encontrados = diagnose_aprovisionamientos_issues(df_data)
                        
                        if duplicados_encontrados is not None and not duplicados_encontrados.empty:
                            st.markdown("---")
                            if st.button("🔧 Corregir Duplicados Automáticamente", key="fix_aprov"):
                                df_fixed = fix_aprovisionamientos_duplicates(df_data)
                                st.session_state.df_pl_consolidated = df_fixed
                                st.success("✅ Duplicados corregidos. Presiona 'Actualizar P&L' para ver los cambios.")
                else:
                    st.warning("No hay datos cargados para diagnosticar")
            else:
                st.warning("Primero carga los datos usando 'Actualizar P&L'")

    with col_diag2:
        if st.button("🔍 Diagnosticar Otros Gastos", type="secondary"):
            if st.session_state.get("pl_data_updated", False):
                df_data = st.session_state.get("df_pl_consolidated", pd.DataFrame())
                if not df_data.empty:
                    with st.expander("📋 Diagnóstico de Otros Gastos de Explotación", expanded=True):
                        # Función específica para otros gastos
                        def diagnose_otros_gastos_explotacion(df_consolidated: pd.DataFrame):
                            """
                            Diagnóstico detallado de otros gastos de explotación
                            """
                            st.subheader("🔍 Diagnóstico de Otros Gastos de Explotación")
                            
                            if df_consolidated.empty:
                                st.warning("No hay datos para diagnosticar")
                                return
                            
                            # Filtrar solo otros gastos de explotación
                            df_otros = df_consolidated[df_consolidated["categoria"] == "Otros gastos de explotación"].copy()
                            
                            if df_otros.empty:
                                st.info("No se encontraron otros gastos de explotación en los datos")
                                return
                            
                            # === ANÁLISIS GENERAL ===
                            total_otros = df_otros["importe"].sum()
                            expected_otros = -275769.55  # Del Excel
                            difference = total_otros - expected_otros
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("💰 Total Obtenido", f"{total_otros:,.2f} €")
                            col2.metric("🎯 Total Esperado", f"{expected_otros:,.2f} €")
                            col3.metric("⚠️ Diferencia", f"{difference:,.2f} €", 
                                        delta=f"{(difference/expected_otros*100):.1f}%" if expected_otros != 0 else "N/A")
                            
                            # === VERIFICACIÓN DE CUENTAS ESPECÍFICAS IMPORTANTES ===
                            st.subheader("🎯 Verificación de Cuentas Clave del Excel")
                            
                            # Cuentas específicas con sus importes esperados del Excel
                            cuentas_clave = {
                                "62100001": {"esperado": -18180.00, "descripcion": "Alquiler apartamentos turísticos"},
                                "62100002": {"esperado": -4168.60, "descripcion": "Renting Lexus kinto ONe"},
                                "62200002": {"esperado": -23486.29, "descripcion": "Hostings"},
                                "62300004": {"esperado": -72264.93, "descripcion": "Servicios profesionales Abogados"},
                                "62300020": {"esperado": -17276.52, "descripcion": "Servicios TECHNOURCE"},
                                "62300021": {"esperado": -19421.85, "descripcion": "Servicios ITMA"},
                                "62700000": {"esperado": -46943.81, "descripcion": "Publicidad propaganda"},
                                "62900001": {"esperado": -13292.64, "descripcion": "Software y Licencias"},
                                "62900003": {"esperado": -36143.84, "descripcion": "Viajes hoteles vuelos"},
                                "62600001": {"esperado": -161.22, "descripcion": "Servicios bancarios CAIXABANK"},
                                "62600002": {"esperado": -1271.35, "descripcion": "Servicios bancarios BBVA"},
                            }
                            
                            verificacion_data = []
                            total_cuentas_clave = 0
                            
                            for cuenta, info in cuentas_clave.items():
                                cuenta_data = df_otros[df_otros['cuenta'] == cuenta]
                                
                                if cuenta_data.empty:
                                    obtenido = 0.0
                                    status = "❌ NO ENCONTRADA"
                                else:
                                    obtenido = cuenta_data['importe'].sum()
                                    total_cuentas_clave += obtenido
                                    diferencia = abs(obtenido - info["esperado"])
                                    
                                    if diferencia < 10:
                                        status = "✅ CORRECTO"
                                    elif diferencia < 100:
                                        status = "⚠️ MENOR DIF"
                                    else:
                                        status = "❌ DIFERENCIA"
                                
                                verificacion_data.append({
                                    "Cuenta": cuenta,
                                    "Descripción": info["descripcion"],
                                    "Esperado": f"{info['esperado']:,.2f} €",
                                    "Obtenido": f"{obtenido:,.2f} €",
                                    "Diferencia": f"{obtenido - info['esperado']:,.2f} €",
                                    "Status": status
                                })
                            
                            df_verificacion = pd.DataFrame(verificacion_data)
                            st.dataframe(df_verificacion, use_container_width=True)
                            
                            # === ANÁLISIS POR SUBCATEGORÍAS (62X) ===
                            st.subheader("📊 Análisis por Subcategorías")
                            
                            # Agrupar por prefijo de cuenta
                            df_otros['prefijo'] = df_otros['cuenta'].str[:3]
                            subcategoria_summary = df_otros.groupby('prefijo').agg({
                                'importe': ['sum', 'count'],
                                'cuenta': lambda x: ', '.join(sorted(x.unique())[:3])
                            }).round(2)
                            
                            subcategoria_summary.columns = ['Total', 'Cantidad', 'Cuentas_Ejemplo']
                            subcategoria_summary = subcategoria_summary.reset_index()
                            
                            # Mapeo de subcategorías
                            subcategoria_mapping = {
                                '621': 'Alquileres y renting',
                                '622': 'Mantenimiento y reparaciones',
                                '623': 'Servicios profesionales',
                                '624': 'Transportes',
                                '625': 'Primas de seguros',
                                '626': 'Servicios bancarios',
                                '627': 'Publicidad y propaganda',
                                '628': 'Suministros',
                                '629': 'Otros servicios',
                                '631': 'Tributos'
                            }
                            
                            subcategoria_summary['Descripción'] = subcategoria_summary['prefijo'].map(subcategoria_mapping)
                            subcategoria_summary = subcategoria_summary[['prefijo', 'Descripción', 'Total', 'Cantidad', 'Cuentas_Ejemplo']]
                            
                            st.dataframe(subcategoria_summary, use_container_width=True)
                            
                            # === DETECCIÓN DE DUPLICADOS ===
                            st.subheader("🚨 Detección de Posibles Duplicados")
                            
                            df_otros['fecha_str'] = df_otros['fecha'].dt.strftime('%Y-%m-%d')
                            df_otros['importe_abs'] = df_otros['importe'].abs()
                            
                            duplicados = df_otros.groupby(['fecha_str', 'cuenta', 'importe_abs']).agg({
                                'importe': 'sum',
                                'fuente': lambda x: list(x),
                                'descripcion': 'first'
                            }).reset_index()
                            
                            duplicados['num_fuentes'] = duplicados['fuente'].apply(len)
                            posibles_duplicados = duplicados[duplicados['num_fuentes'] > 1]
                            
                            if not posibles_duplicados.empty:
                                st.error(f"⚠️ Encontrados {len(posibles_duplicados)} posibles duplicados:")
                                st.dataframe(posibles_duplicados[['fecha_str', 'cuenta', 'descripcion', 'importe_abs', 'fuente']], 
                                           use_container_width=True)
                                return posibles_duplicados
                            else:
                                st.success("✅ No se detectaron duplicados obvios")
                            
                            # === TOP 10 GASTOS ===
                            st.subheader("💸 Top 10 Gastos Más Grandes")
                            
                            top_gastos = df_otros.groupby(['cuenta', 'descripcion'])['importe'].sum().reset_index()
                            top_gastos['importe_abs'] = top_gastos['importe'].abs()
                            top_gastos = top_gastos.nlargest(10, 'importe_abs')[['cuenta', 'descripcion', 'importe']]
                            
                            st.dataframe(top_gastos, use_container_width=True)
                            
                            return None
                        
                        duplicados_encontrados = diagnose_otros_gastos_explotacion(df_data)
                        
                        if duplicados_encontrados is not None and not duplicados_encontrados.empty:
                            st.markdown("---")
                            if st.button("🔧 Corregir Duplicados Otros Gastos", key="fix_otros"):
                                df_fixed = fix_otros_gastos_duplicates(df_data)
                                st.session_state.df_pl_consolidated = df_fixed
                                st.success("✅ Duplicados corregidos. Presiona 'Actualizar P&L' para ver los cambios.")
                else:
                    st.warning("No hay datos cargados para diagnosticar")
            else:
                st.warning("Primero carga los datos usando 'Actualizar P&L'")

    with col_diag3:
        if st.button("📊 Diagnóstico Completo", type="secondary"):
            if st.session_state.get("pl_data_updated", False):
                df_data = st.session_state.get("df_pl_consolidated", pd.DataFrame())
                if not df_data.empty:
                    with st.expander("📋 Diagnóstico Completo de Todas las Categorías", expanded=True):
                        # Función de diagnóstico completo
                        def diagnose_all_main_categories(df_consolidated: pd.DataFrame):
                            """
                            Diagnóstico comparativo de todas las categorías principales
                            """
                            st.subheader("📊 Diagnóstico Comparativo - Todas las Categorías")
                            
                            if df_consolidated.empty:
                                st.warning("No hay datos para diagnosticar")
                                return
                            
                            # Totales esperados del Excel
                            expected_totals = {
                                "Aprovisionamientos": -9012.02,
                                "Gastos de personal": -52201.39,
                                "Otros gastos de explotación": -275769.55,
                                "Gastos financieros": -890.53,
                                "Diferencias de cambio": 10628.19,
                                "Otros resultados": 259.36,
                                "Ingresos financieros": 0.18,
                                "Ingresos": 2318450.97
                            }
                            
                            # Totales obtenidos
                            obtained_totals = df_consolidated.groupby("categoria")["importe"].sum().to_dict()
                            
                            # Crear análisis detallado
                            analysis_data = []
                            total_difference = 0
                            
                            for categoria, expected in expected_totals.items():
                                obtained = obtained_totals.get(categoria, 0)
                                difference = obtained - expected
                                total_difference += abs(difference)
                                percentage_diff = (difference / expected * 100) if expected != 0 else 0
                                
                                # Determinar nivel de problema
                                if abs(difference) < 100:
                                    level = "✅ CORRECTO"
                                    priority = 1
                                elif abs(difference) < 1000:
                                    level = "⚠️ MENOR"
                                    priority = 2
                                elif abs(difference) < 10000:
                                    level = "🔶 MEDIO"
                                    priority = 3
                                else:
                                    level = "🚨 CRÍTICO"
                                    priority = 4
                                
                                analysis_data.append({
                                    "Categoría": categoria,
                                    "Esperado": f"{expected:,.2f} €",
                                    "Obtenido": f"{obtained:,.2f} €",
                                    "Diferencia": f"{difference:,.2f} €",
                                    "% Diferencia": f"{percentage_diff:.1f}%",
                                    "Nivel": level,
                                    "Prioridad": priority
                                })
                            
                            # Ordenar por prioridad
                            analysis_df = pd.DataFrame(analysis_data).sort_values(['Prioridad'], ascending=[False])
                            
                            st.dataframe(analysis_df[['Categoría', 'Esperado', 'Obtenido', 'Diferencia', '% Diferencia', 'Nivel']], 
                                        use_container_width=True)
                            
                            # Resumen general
                            st.subheader("📈 Resumen del Diagnóstico")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                criticos = len(analysis_df[analysis_df['Prioridad'] == 4])
                                st.metric("🚨 Problemas Críticos", criticos)
                                
                            with col2:
                                medios = len(analysis_df[analysis_df['Prioridad'] == 3])
                                st.metric("🔶 Problemas Medios", medios)
                                
                            with col3:
                                menores = len(analysis_df[analysis_df['Prioridad'] == 2])
                                st.metric("⚠️ Problemas Menores", menores)
                            
                            # Plan de acción
                            st.subheader("🎯 Plan de Acción Recomendado")
                            
                            for _, row in analysis_df.iterrows():
                                if row['Prioridad'] >= 3:  # Solo problemas medios y críticos
                                    categoria = row['Categoría']
                                    
                                    if categoria == "Aprovisionamientos":
                                        st.warning(f"🎯 **{categoria}**: Usar botón 'Diagnosticar Aprovisionamientos'")
                                    elif categoria == "Otros gastos de explotación":
                                        st.warning(f"🎯 **{categoria}**: Usar botón 'Diagnosticar Otros Gastos'")
                                    elif categoria == "Gastos de personal":
                                        st.warning(f"🎯 **{categoria}**: Verificar nóminas y cargas sociales")
                                    elif categoria == "Ingresos":
                                        st.warning(f"🎯 **{categoria}**: Verificar facturas de venta")
                                    else:
                                        st.info(f"🎯 **{categoria}**: Revisar clasificación")
                            
                            if total_difference < 1000:
                                st.success("🎉 ¡Excelente! Todas las categorías están muy cerca de los valores esperados.")
                            elif total_difference < 10000:
                                st.warning("⚠️ Hay algunas diferencias que requieren atención.")
                            else:
                                st.error("🚨 Hay diferencias significativas que requieren investigación urgente.")
                        
                        diagnose_all_main_categories(df_data)
                else:
                    st.warning("No hay datos cargados para diagnosticar")
            else:
                st.warning("Primero carga los datos usando 'Actualizar P&L'")

    # Función auxiliar para corregir duplicados en otros gastos
    def fix_otros_gastos_duplicates(df_consolidated: pd.DataFrame):
        """
        Función para corregir duplicados en otros gastos de explotación
        """
        if df_consolidated.empty:
            return df_consolidated
        
        # Crear copia para no modificar el original
        df_fixed = df_consolidated.copy()
        
        # Filtrar otros gastos de explotación
        df_otros = df_fixed[df_fixed["categoria"] == "Otros gastos de explotación"].copy()
        df_rest = df_fixed[df_fixed["categoria"] != "Otros gastos de explotación"].copy()
        
        if df_otros.empty:
            return df_consolidated
        
        # Detectar duplicados
        df_otros['fecha_str'] = df_otros['fecha'].dt.strftime('%Y-%m-%d')
        df_otros['importe_abs'] = df_otros['importe'].abs()
        df_otros['duplicate_key'] = df_otros['fecha_str'] + '_' + df_otros['cuenta'] + '_' + df_otros['importe_abs'].astype(str)
        
        # Remover duplicados manteniendo solo el del libro diario (más confiable)
        df_otros['fuente_priority'] = df_otros['fuente'].map({
            'Libro Diario': 1,
            'Documento purchase': 2,
            'Documento bill': 3,
            'Documento expense': 4,
            'Factura Venta': 5
        })
        
        # Ordenar por prioridad y mantener solo el primero de cada grupo
        df_otros_sorted = df_otros.sort_values(['duplicate_key', 'fuente_priority'])
        df_otros_fixed = df_otros_sorted.groupby('duplicate_key').first().reset_index()
        
        # Eliminar columnas auxiliares
        df_otros_fixed = df_otros_fixed.drop(['fecha_str', 'importe_abs', 'duplicate_key', 'fuente_priority'], axis=1)
        
        # Recombinar datos
        df_result = pd.concat([df_rest, df_otros_fixed], ignore_index=True)
        
        return df_result
