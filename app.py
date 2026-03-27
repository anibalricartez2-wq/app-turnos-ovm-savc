import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Turnos SAVC", layout="wide")

# --- FUNCIÓN DE LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.title("🔐 Acceso al Sistema de Turnos")
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if "passwords" in st.secrets:
                if user in st.secrets["passwords"] and password == st.secrets["passwords"][user]:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
            else:
                st.error("Error: Configurá 'Secrets' en Streamlit Cloud")
        return False
    return True

# --- TRADUCCIONES ---
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_ABR = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TURNOS = ["Mañana (06-15)", "Tarde (15-24)"]

# --- FUNCIÓN PDF ---
def crear_pdf(df_final, mes_nombre, anio):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    titulo = f"CRONOGRAMA DE TURNOS - {mes_nombre.upper()} {anio}"
    pdf.cell(190, 10, titulo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(50, 10, "FECHA", border=1, align="C", fill=True)
    pdf.cell(70, 10, "MANANA (06-15)", border=1, align="C", fill=True)
    pdf.cell(70, 10, "TARDE (15-24)", border=1, align="C", fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(0, 0, 0)
    fill = False
    for _, row in df_final.iterrows():
        pdf.set_fill_color(240, 240, 240)
        f_t = str(row['Fecha']).encode('latin-1', 'replace').decode('latin-1')
        m_t = str(row['Mañana (06-15)']).replace("[VACANTE]", "VACANTE").encode('latin-1', 'replace').decode('latin-1')
        t_t = str(row['Tarde (15-24)']).replace("[VACANTE]", "VACANTE").encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(50, 8, f_t, border=1, align="C", fill=fill)
        pdf.cell(70, 8, m_t, border=1, align="C", fill=fill)
        pdf.cell(70, 8, t_t, border=1, align="C", fill=fill)
        pdf.ln()
        fill = not fill
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- CUERPO PRINCIPAL ---
if login():
    st.sidebar.header("⚙️ Configuración")
    mes_nombre = st.sidebar.selectbox("Seleccionar Mes", MESES_ES, index=datetime.now().month - 1)
    mes_nro = MESES_ES.index(mes_nombre) + 1
    anio = st.sidebar.number_input("Año", value=2026)
    
    empleados = ["Sánchez", "García", "Barros", "Ricartez"]
    
    LIMITE_MENSUAL = 160
    CUOTA_SEMANAL = 45 
    
    config_per = {}
    for e in empleados:
        with st.sidebar.expander(f"Restricciones {e}"):
            rango = st.date_input(f"Licencia Médica {e}", value=[], key=f"l_{e}")
            f_fijos = st.multiselect(f"Francos fijos (Días):", range(1, 32), key=f"f_{e}")
            
            st.write("**Restricciones por Día y Turno:**")
            restricciones_esp = []
            for d_nom in DIAS_ES:
                cols_r = st.columns(2)
                if cols_r[0].checkbox(f"{d_nom} Mañana", key=f"rm_{e}_{d_nom}"):
                    restricciones_esp.append((d_nom, TURNOS[0]))
                if cols_r[1].checkbox(f"{d_nom} Tarde", key=f"rt_{e}_{d_nom}"):
                    restricciones_esp.append((d_nom, TURNOS[1]))

            fechas_l = []
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                fechas_l = pd.date_range(start=rango[0], end=rango[1]).date
            
            config_per[e] = {
                "lic": fechas_l, 
                "f_fijos": f_fijos,
                "bloqueos_especificos": restricciones_esp
            }

    if st.button("🚀 GENERAR PLANILLA PROPORCIONAL"):
        num_dias = calendar.monthrange(anio, mes_nro)[1]
        cronograma = []
        hs_totales = {e: 0 for e in empleados}
        hs_semanales = {e: 0 for e in empleados}
        tarde_ayer = None
        semana_actual = None

        for d in range(1, num_dias + 1):
            f_dt = datetime(anio, mes_nro, d)
            idx_s = f_dt.weekday() # 0=Lunes
            nom_dia_hoy = DIAS_ES[idx_s]
            
            iso_semana = f_dt.isocalendar()[1]
            if iso_semana != semana_actual:
                hs_semanales = {e: 0 for e in empleados}
                semana_actual = iso_semana

            hs_v = 18 if idx_s >= 5 else 9
            f_str = f"{DIAS_ABR[idx_s]} {f_dt.strftime('%d/%m/%Y')}"
            
            hoy_asignados = []
            for t in TURNOS:
                cand = []
                for e in empleados:
                    # 1. Licencias y Francos fijos
                    en_lic = f_dt.date() in config_per[e]["lic"]
                    es_franco = d in config_per[e]["f_fijos"]
                    
                    # 2. Restricción específica (Ej: Jueves Tarde)
                    esta_bloqueado = (nom_dia_hoy, t) in config_per[e]["bloqueos_especificos"]
                    
                    # 3. Descanso mínimo (no mañana si hizo tarde ayer)
                    descanso_ok = not (t == TURNOS[0] and e == tarde_ayer)
                    
                    # 4. Límites de horas
                    tope_m = hs_totales[e] + hs_v <= LIMITE_MENSUAL
                    tope_s = hs_semanales[e] + hs_v <= CUOTA_SEMANAL
                    
                    if not any([en_lic, es_franco, esta_bloqueado]) and descanso_ok and tope_m and tope_s and e not in hoy_asignados:
                        cand.append(e)
                
                cand.sort(key=lambda x: hs_totales[x])
                
                if cand:
                    elegido = cand[0]
                    cronograma.append({"nro_dia": d, "Fecha": f_str, "Turno": t, "Empleado": elegido})
                    hs_totales[elegido] += hs_v
                    hs_semanales[elegido] += hs_v
                    hoy_asignados.append(elegido)
                    if t == TURNOS[1]: tarde_ayer = elegido
                else:
                    cronograma.append({"nro_dia": d, "Fecha": f_str, "Turno": t, "Empleado": "[VACANTE]"})
                    if t == TURNOS[1]: tarde_ayer =
