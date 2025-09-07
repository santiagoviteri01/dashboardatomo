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
with tab3:
    st.header("📑 P&L desde Holded (API)")
    st.caption("Calculado desde documentos de Holded y libro diario contable para mayor precisión.")

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
    def list_purchases_any(start_dt: datetime, end_dt: datetime, page_size=500):
        """Descarga todas las compras (endpoint purchase) y filtra por fecha local."""
        headers = {"accept": "application/json", "key": get_holded_token()}
        url = "https://api.holded.com/api/invoicing/v1/documents/purchase"
        
        out = []
        page = 1
        while True:
            r = requests.get(url, headers=headers, params={"page": page, "limit": page_size}, timeout=30)
            if r.status_code != 200:
                break
            data = r.json()
            if not data:
                break
            out.extend(data)
            if len(data) < page_size:
                break
            page += 1
        
        if not out:
            return pd.DataFrame()
        
        df = pd.DataFrame(out)
        
        # Filtrar localmente por fecha
        if "date" in df.columns:
            df["_date"] = pd.to_datetime(df["date"], unit="s", errors="coerce")
            mask = (df["_date"] >= pd.to_datetime(start_dt)) & (df["_date"] <= pd.to_datetime(end_dt))
            df = df[mask].copy()
        
        return df
        @st.cache_data(ttl=60)
        def get_document_detail_corrected(doc_type: str, doc_id: str):
            """Obtiene detalle de documento específico"""
            if not doc_id:
                return {}
            url = f"https://api.holded.com/api/invoicing/v1/documents/{doc_type}/{doc_id}"
            headers = {"accept": "application/json", "key": get_holded_token()}
            try:
                r = requests.get(url, headers=headers, timeout=30)
                return r.json() if r.status_code == 200 else {}
            except Exception as e:
                st.warning(f"Error obteniendo detalle de {doc_id}: {e}")
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

    # ====== CLASIFICADOR PGC ======
    def _strip_accents(s: str) -> str:
        s = str(s or "")
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

    def _only_leading_digits(code: str) -> str:
        code = str(code or "").strip().replace("\xa0", " ")
        m = re.match(r"^([0-9]{2,})", code)
        return m.group(1) if m else ""

    def classify_account_corrected(code: str, name: str = "") -> str:
        """
        - Limpia el código (dígitos iniciales).
        - Prioriza 768/668 (Diferencias) antes que 76/66.
        - Añade 68/69 como gastos.
        """
        code = _only_leading_digits(code)
        name_clean = _strip_accents(str(name or "").lower())

        # Reglas por código
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

        # Fallback por nombre
        if any(w in name_clean for w in ["nomina", "sueldo", "salario", "personal", "seguridad social"]):
            return "Gastos de personal"
        if any(w in name_clean for w in ["interes", "financiero", "prestamo", "credito"]):
            return "Gastos financieros"
        if "cambio" in name_clean or "divisa" in name_clean:
            return "Diferencias de cambio"
        if any(w in name_clean for w in ["compra", "suministro", "materia prima"]):
            return "Aprovisionamientos"

        return "Otros gastos de explotación"

    # ====== PARSERS / NORMALIZADORES ======
    def _line_amount_fallback(ln: dict) -> float:
        for k in ("subTotal","subtotal","untaxedAmount","netAmount","base","amount","total"):
            v = ln.get(k)
            if v is not None:
                try: return float(v)
                except: pass
        qty = ln.get("quantity") or ln.get("qty") or 1
        price = (ln.get("unitPrice") or ln.get("price") or ln.get("unitprice") or
                 ln.get("unit_cost") or ln.get("unitCost") or 0)
        try: return float(qty) * float(price)
        except: return 0.0
    def parse_purchase_lines_corrected(doc_json: dict):
        """Extrae líneas de compra robustamente."""
        lines = []
        if not doc_json:
            return lines
        raw_date = doc_json.get("date")
        fecha = pd.to_datetime(raw_date, unit='s', errors='coerce') if isinstance(raw_date, (int, float)) \
                else pd.to_datetime(raw_date, errors='coerce')

        items = doc_json.get("items", []) or doc_json.get("lines", []) or doc_json.get("concepts", [])
        if items:
            for ln in items:
                amt = _line_amount_fallback(ln)
                account_code = (ln.get("expenseAccountCode") or ln.get("accountCode") or
                                ln.get("expenseAccountId") or ln.get("accountId") or "")
                account_name = (ln.get("accountName") or ln.get("name") or ln.get("description") or "")
                lines.append((fecha, str(account_code), account_name, float(amt)))
        else:
            total = 0.0
            for k in ("subTotal", "subtotal", "untaxedAmount", "total", "amount"):
                v = doc_json.get(k)
                if v is not None:
                    try:
                        total = float(v)
                        break
                    except Exception:
                        pass
            if total:
                lines.append((fecha, "62XXX", "Gasto sin desglosar", float(total)))
        return lines

    EXPENSE_CATS = {"Aprovisionamientos", "Gastos de personal", "Otros gastos de explotación", "Gastos financieros"}
    INCOME_CATS = {"Ingresos", "Ingresos financieros"}
    NEUTRAL_CATS = {"Diferencias de cambio", "Otros resultados"}  # mantener signo de origen

    def normalize_amount_by_category(cat: str, amount: float) -> float:
        amount = float(amount or 0)
        if cat in EXPENSE_CATS:
            return -abs(amount)
        if cat in INCOME_CATS:
            return abs(amount)
        return amount  # neutral

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
    df_purchases_for_clients = list_purchases_any(
        datetime.combine(fecha_inicio_pl, datetime.min.time()),
        datetime.combine(fecha_fin_pl, datetime.max.time())
    )
    clientes_invoices = df_invoices_for_clients["contactName"].dropna().unique().tolist() if not df_invoices_for_clients.empty else []
    clientes_purchases = df_purchases_for_clients["contactName"].dropna().unique().tolist() if not df_purchases_for_clients.empty else []

    ledger_entries_for_clients = list_daily_ledger_corrected(
        datetime.combine(fecha_inicio_pl, datetime.min.time()),
        datetime.combine(fecha_fin_pl, datetime.max.time())
    )
    clientes_ledger = []
    for entry in ledger_entries_for_clients:
        cliente = entry.get("contactName") or entry.get("thirdParty") or entry.get("customer")
        clientes_ledger.append(cliente if cliente else "Libro Diario (sin cliente)")

    clientes_unicos = sorted(set(clientes_invoices + clientes_purchases + clientes_ledger))
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
        list_purchases_any.clear()
        get_document_detail_corrected.clear()
        list_daily_ledger_corrected.clear()

    st.sidebar.info(f"**Filtros activos:**\n- Período: {fecha_inicio_pl} a {fecha_fin_pl}\n- Cliente: {cliente_pl}\n- Libro diario: {'Sí' if usar_libro_diario else 'No'}")

    # ====== PROCESAMIENTO ======
    inicio_dt = datetime.combine(fecha_inicio_pl, datetime.min.time())
    fin_dt = datetime.combine(fecha_fin_pl, datetime.max.time())

    if not st.session_state.get("pl_data_updated", False):
        try:
            with st.spinner("Cargando datos de Holded..."):
                # 1) INGRESOS
                st.info("📥 Cargando facturas de venta...")
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
                                    amount = float(inv[k]); break
                                except Exception:
                                    pass
                        cliente = inv.get("contactName", "Sin nombre")
                        if cliente_pl != "Todo" and cliente != cliente_pl:
                            continue
                        periodo = fecha.to_period("M").strftime("%Y-%m")
                        cat = "Ingresos"
                        amount_norm = normalize_amount_by_category(cat, amount)
                        ingresos_data.append({
                            "periodo": periodo, "fecha": fecha, "cliente": cliente,
                            "categoria": cat, "importe": amount_norm,
                            "cuenta": "70XXX", "descripcion": f"Factura {inv.get('docNumber', '')}"
                        })
                st.success(f"✅ Procesadas {len(ingresos_data)} facturas de venta")

                # 2) COMPRAS (purchase + bill + expense)
                # --- 🔎 SONDEO DE ENDPOINTS DE COMPRAS (pegar antes de usar df_purchases) ---

                @st.cache_data(ttl=60)
                def _try_get(url, headers, params):
                    try:
                        r = requests.get(url, headers=headers, params=params, timeout=30)
                        return r.status_code, (r.json() if r.headers.get("content-type","").startswith("application/json") else None), r.text[:200]
                    except Exception as e:
                        return -1, None, str(e)
                
                @st.cache_data(ttl=60)
                def probe_purchases_endpoints(start_dt: datetime, end_dt: datetime, page_size=200):
                    """
                    Prueba múltiples variantes de compras y distintos parámetros de fecha.
                    Devuelve: (best_kind, best_df, debug_rows)
                    """
                    headers = {"accept": "application/json", "key": get_holded_token()}
                    base = "https://api.holded.com/api/invoicing/v1"
                
                    # Candidatos de ruta (lista de (kind, path))
                    route_candidates = [
                        ("purchase", f"{base}/documents/purchase"),
                        ("bill",     f"{base}/documents/bill"),
                        ("expense",  f"{base}/documents/expense"),
                        # Por si la API usa plurales en algunos tenants:
                        ("bills",    f"{base}/documents/bills"),
                        ("expenses", f"{base}/documents/expenses"),
                        # Por si existiera un recurso directo (algunos tenants antiguos):
                        ("purchases", f"{base}/purchases"),
                    ]
                
                    # Candidatos de filtros de fecha
                    date_params_candidates = [
                        {"starttmp": int(start_dt.timestamp()), "endtmp": int(end_dt.timestamp())},
                        {"dateFrom": start_dt.strftime("%Y-%m-%d"), "dateTo": end_dt.strftime("%Y-%m-%d")},
                        {"from": start_dt.strftime("%Y-%m-%d"), "to": end_dt.strftime("%Y-%m-%d")},
                        # Último recurso: sin filtros (y filtramos local si toca)
                        {},
                    ]
                
                    debug_rows = []
                    best = ("", pd.DataFrame(), 0, {}, "")  # (kind, df, n_rows, params, url)
                    for kind, url in route_candidates:
                        for date_params in date_params_candidates:
                            params = {"sort": "created-asc", "limit": page_size} | date_params
                            code, js, preview = _try_get(url, headers, params)
                            n = len(js) if isinstance(js, list) else 0
                            debug_rows.append({
                                "kind": kind, "url": url, "status": code, "params": date_params, "n": n, "preview": preview
                            })
                            if n > best[2]:
                                df = pd.DataFrame(js) if isinstance(js, list) else pd.DataFrame()
                                best = (kind, df, n, date_params, url)
                
                    return best[0], best[1], pd.DataFrame(debug_rows).sort_values("n", ascending=False).head(20)
                
                # === úsalo antes de armar df_purchases ===
                best_kind, best_df, probe_table = probe_purchases_endpoints(inicio_dt, fin_dt)
                
                with st.expander("🔧 Debug de búsqueda de compras"):
                    st.write("Mejor endpoint encontrado:", best_kind)
                    st.dataframe(probe_table, use_container_width=True)
                    if not best_df.empty:
                        st.write("Muestra de 5 docs:")
                        st.dataframe(best_df.head(5))
                
                # Si no encontró nada, seguimos con DF vacío
                df_purchases = best_df.copy()
                # Guardamos el 'kind' ganador en sesión para usarlo al pedir el detalle:
                st.session_state.setdefault("best_purchase_kind", best_kind or "purchase")

                st.info("📤 Cargando compras (purchase/bill/expense)...")
                #df_purchases = list_purchases_any(inicio_dt, fin_dt)

                gastos_data = process_expenses_corrected(inicio_dt, fin_dt, cliente_pl)



                # 3) LIBRO DIARIO (opcional)
                diario_data = []
                if usar_libro_diario:
                    st.info("📚 Cargando libro diario...")
                    ledger_entries = list_daily_ledger_corrected(inicio_dt, fin_dt)
                    for entry in ledger_entries:
                        entry_date = entry.get("date")
                        fecha = pd.to_datetime(entry_date, unit="s", errors="coerce") if isinstance(entry_date, (int, float)) else pd.to_datetime(entry_date, errors="coerce")
                        if pd.isna(fecha):
                            continue
                        amount = entry.get("amount")
                        if amount is None:
                            debit = float(entry.get("debit", 0) or 0)
                            credit = float(entry.get("credit", 0) or 0)
                            amount = debit - credit
                        else:
                            amount = float(amount)
                        if amount == 0:
                            continue
                        account_code = str(entry.get("accountCode", "") or "")
                        account_name = str(entry.get("accountName", "") or "")
                        categoria = classify_account_corrected(account_code, account_name)
                        amount_norm = normalize_amount_by_category(categoria, amount)
                        periodo = fecha.to_period("M").strftime("%Y-%m")
                        cliente_entry = entry.get("contactName") or entry.get("thirdParty") or entry.get("customer") or "Libro Diario (sin cliente)"
                        if cliente_pl != "Todo" and cliente_entry != cliente_pl:
                            continue
                        diario_data.append({
                            "periodo": periodo, "fecha": fecha, "cliente": cliente_entry,
                            "categoria": categoria, "importe": amount_norm,
                            "cuenta": account_code, "descripcion": account_name
                        })
                    st.success(f"✅ Procesadas {len(diario_data)} entradas del diario")

                # 4) CONSOLIDAR
                all_data = ingresos_data + gastos_data + diario_data
                df_consolidated = pd.DataFrame(all_data)
                if df_consolidated.empty:
                    st.warning("⚠️ No se encontraron datos en el período seleccionado")
                    st.session_state.pl_data_updated = True
                    st.stop()

                st.session_state.df_pl_consolidated = df_consolidated
                st.session_state.pl_data_updated = True

                # Debug corto
                st.write("🔎 Debug P&L:",
                         {"ingresos_facturas": len(ingresos_data),
                          "lineas_compras": len(gastos_data),
                          "asientos_diario": len(diario_data),
                          "cats": pd.Series([r["categoria"] for r in all_data]).value_counts().to_dict()})

        except Exception as e:
            st.error(f"❌ Error procesando datos: {str(e)}")
            st.exception(e)
            st.stop()
    tab_pgc, tab_actual = st.tabs(["📋 Formato PGC", "📊 Dashboard Actual"])
    with tab_pgc:
        if st.session_state.get("pl_data_updated", False):
            df_data = st.session_state.get("df_pl_consolidated", pd.DataFrame())
            if not df_data.empty:
                generate_pgc_report(df_data, inicio_dt, fin_dt)
    with tab_actual:
        # ====== MOSTRAR RESULTADOS ======
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
                        df_detail_display = df_filtered[["periodo", "cliente", "categoria", "cuenta", "descripcion", "importe"]].copy()
                        df_detail_display = df_detail_display.sort_values(["periodo", "categoria", "importe"], ascending=[True, True, False])
                        df_detail_display["importe"] = df_detail_display["importe"].round(2)
                        st.dataframe(df_detail_display, use_container_width=True, height=400)
    
                        # Resumen por categoría (sin forzar colores)
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


# ====== FIN DEL CÓDIGO ======


