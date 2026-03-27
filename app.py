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
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if "passwords" in st.secrets:
                if u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else: st.error("Usuario o contraseña incorrectos")
            else: st.error("Configurá 'Secrets' en Streamlit")
        return False
    return True

# --- CONSTANTES ---
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_ABR = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TURNOS = ["Mañana (06-15)", "Tarde (15-24)"]

# --- FUNCIÓN PDF ---
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

# --- CUERPO PRINCIPAL ---
if login():
    st.sidebar.header("⚙️ Configuración")
    m_nom = st.sidebar.selectbox("Mes", MESES_ES, index=datetime.now().month - 1)
    m_nro = MESES_ES.index(m_nom) + 1
    a_nro = st.sidebar.number_input("Año", value=2026)
    
    empleados = ["Sánchez", "García", "Barros", "Ricartez"]
    L_MENSUAL, C_SEMANAL = 160, 45 
    
    cfg = {}
    for e in empleados:
        with st.sidebar.expander(f"Restricciones {e}"):
            r = st.date_input(f"Licencia {e}", value=[], key=f"l_{e}")
            ff = st.multiselect(f"Francos fijos:", range(1, 32), key=f"f_{e}")
            st.write("**Bloqueos:**")
            bl = []
            c1, c2 = st.columns(2)
            for i, d_n in enumerate(DIAS_ES):
                col = c1 if i < 4 else c2
                if col.checkbox(f"{d_n} M", key=f"m_{e}_{d_n}"): bl.append((d_n, TURNOS[0]))
                if col.checkbox(f"{d_n} T", key=f"t_{e}_{d_n}"): bl.append((d_n, TURNOS[1]))
            fl = pd.date_range(start=r[0], end=r[1]).date if len(r) == 2 else []
            cfg[e] = {"lic": fl, "fra": ff, "blo": bl}

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
            h_v = 18 if idx_s >= 5 else 9
            f_s = f"{DIAS_ABR[idx_s]} {f_dt.strftime('%d/%m/%Y')}"
            h_asig = []
            for t in TURNOS:
                cand = []
                for e in empleados:
                    l_ok = f_dt.date() in cfg[e]["lic"]
                    f_ok = d in cfg[e]["fra"]
                    b_ok = (n_dia, t) in cfg[e]["blo"]
                    d_ok = not (t == TURNOS[0] and e == t_ayer)
                    l_m = h_tot[e] + h_v <= L_MENSUAL
                    l_s = h_sem[e] + h_v <= C_SEMANAL
                    if not any([l_ok, f_ok, b_ok]) and d_ok and l_m and l_s and e not in h_asig:
                        cand.append(e)
                cand.sort(key=lambda x: h_tot[x])
                el = cand[0] if cand else "[VACANTE]"
                cron.append({"n": d, "Fecha": f_s, "Turno": t, "Empleado": el})
                if el != "[VACANTE]":
                    h_tot[el] += h_v
                    h_sem[el] += h_v
                    h_asig.append(el)
                    if t == TURNOS[1]: t_ayer = el
                elif t == TURNOS[1]: t_ayer = None

        if cron:
            df = pd.DataFrame(cron)
            # Línea de pivot corregida y cerrada
            df_c = df.pivot_table(index=['n', 'Fecha'], columns='Turno', values='Empleado', aggfunc='first').reset_index()
            df_c = df_c.sort_values('n').drop(columns='n')
            st.dataframe(df_c, use_container_width=True)
            try:
                p_b = crear_pdf(df_c, m_nom, a_nro)
                st.download_button("📥 Descargar PDF", p_b, f"Turnos_{m_nom}.pdf", "application/pdf")
            except: st.error("Error al crear PDF")
            st.divider()
            cols = st.columns(len(empleados))
            for i, e in enumerate(empleados):
                cols[i].metric(e, f"{h_tot[e]} hs")
                cols[i].progress(min(h_tot[e]/160, 1.0))
