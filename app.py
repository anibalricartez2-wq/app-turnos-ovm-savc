import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Turnos SAVC", layout="wide")

def login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.title("🔐 Acceso al Sistema de Turnos")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if "passwords" in st.secrets and u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("Credenciales incorrectas")
        return False
    return True

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_ABR = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TURNOS = ["Mañana (06-15)", "Tarde (15-24)"]

def crear_pdf(df_final, mes_nombre, anio):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    t_pdf = f"CRONOGRAMA DE TURNOS - {mes_nombre.upper()} {anio}"
    pdf.cell(190, 10, t_pdf.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
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
    f_p = False
    for _, r in df_final.iterrows():
        pdf.set_fill_color(240, 240, 240)
        f_val = str(r['Fecha']).encode('latin-1', 'replace').decode('latin-1')
        m_val = str(r['Mañana (06-15)']).replace("[VACANTE]", "VACANTE").encode('latin-1', 'replace').decode('latin-1')
        t_val = str(r['Tarde (15-24)']).replace("[VACANTE]", "VACANTE").encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(50, 8, f_val, border=1, align="C", fill=f_p)
        pdf.cell(70, 8, m_val, border=1, align="C", fill=f_p)
        pdf.cell(70, 8, t_val, border=1, align="C", fill=f_p)
        pdf.ln()
        f_p = not f_p
    return pdf.output(dest='S').encode('latin-1', 'ignore')

if login():
    st.sidebar.header("⚙️ Configuración")
    m_nom = st.sidebar.selectbox("Mes", MESES_ES, index=datetime.now().month - 1)
    m_nro = MESES_ES.index(m_nom) + 1
    a_nro = st.sidebar.number_input("Año", value=2026)
    
    empleados = ["Sánchez", "García", "Barros", "Ricartez"]
    L_MENSUAL, C_SEMANAL = 160, 45 
    
    cfg = {}
    for e in empleados:
        with st.sidebar.expander(f"👤 {e}"):
            r = st.date_input(f"Licencia", value=[], key=f"l_{e}")
            ff = st.multiselect(f"Francos fijos:", range(1, 32), key=f"f_{e}")
            
            # --- OPCIÓN DE PREFERENCIA DE TURNO ---
            t_pref = st.radio("Turno de trabajo:", ["Ambos", "Solo Mañana", "Solo Tarde"], key=f"pref_{e}", horizontal=True)
            
            st.write("**Bloqueos por día (No trabaja):**")
            bl = []
            c1, c2 = st.columns(2)
            for i, d_n in enumerate(DIAS_ES):
                col = c1 if i < 4 else c2
                if col.checkbox(f"{d_n} M", key=f"m_{e}_{d_n}"): bl.append((d_n, TURNOS[0]))
                if col.checkbox(f"{d_n} T", key=f"t_{e}_{d_n}"): bl.append((d_n, TURNOS[1]))
            fl = pd.date_range(start=r[0], end=r[1]).date if len(r) == 2 else []
            cfg[e] = {"lic": fl, "fra": ff, "blo": bl, "pref": t_pref}

    if st.button("🚀 GENERAR PLANILLA"):
        n_dias = calendar.monthrange(a_nro, m_nro)[1]
        cron, h_tot, h_sem = [], {e: 0 for e in empleados}, {e: 0 for e in empleados}
        t_ayer, s_act = None, None

        for d in range(1, n_dias + 1):
            f_dt = datetime(a_nro, m_nro, d)
            idx_s, n_dia = f_dt.weekday(), DIAS_ES[f_dt.weekday()]
            i_sem = f_dt.isocalendar()[1]
            if i_sem != s_act:
                h_sem = {e: 0 for e in empleados}
                s_act = i_sem
