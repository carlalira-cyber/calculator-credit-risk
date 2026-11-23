import streamlit as st
import numpy as np

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="CreditRisk - Análisis Crediticio MCO", page_icon="💳", layout="wide")

# --- MANEJO DE ESTADO PARA LA PANTALLA INICIAL ---
if 'show_calculator' not in st.session_state:
    st.session_state.show_calculator = False

def start_calculator():
    st.session_state.show_calculator = True

# --- PANTALLA INICIAL ---
if not st.session_state.show_calculator:
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center; color: #1B365D; font-size: 3em;'>💳 CreditRisk</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #4A777A;'>Calculadora de Análisis Crediticio</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #64748B;'>Por Tomás Málaga</h4>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            st.button("▶ INICIAR CALCULADORA", on_click=start_calculator, use_container_width=True, type="primary")
            
        st.markdown("<br><p style='text-align: center; color: #94A3B8; font-size: 0.9em;'>Motor Econométrico MCO (HC3) • Dataset UCI Taiwán (N = 30.000)</p>", unsafe_allow_html=True)

# --- PANTALLA DE LA CALCULADORA ---
else:
    st.title("💳 CreditRisk: Calculadora de Análisis Crediticio")
    st.markdown("**Simulador de Riesgo y Cupo de Préstamo basado en modelo MCO (HC3) sobre 30.000 clientes (UCI Taiwán).**")
    st.divider()

    # --- 1. PANEL DE CARGA EN VIVO ---
    col_in1, col_in2, col_in3 = st.columns(3)

    with col_in1:
        st.subheader("👤 Perfil Demográfico")
        edu_opciones = {
            1: "Con Educación Superior (Universidad / Posgrado)",
            0: "Sin Educación Superior (Secundaria / Otros)"
        }
        edu_cat = st.selectbox(
            "Nivel Educativo (Proxy de Alfabetización Financiera)",
            options=list(edu_opciones.keys()),
            format_func=lambda x: edu_opciones[x]
        )
        age = st.number_input(
            "Edad (entre 18 y 90 años)", 
            min_value=18, max_value=90, value=32, step=1
        )

    with col_in2:
        st.subheader("💰 Límite y Uso de Tarjeta")
        limit_bal = st.number_input(
            "Límite de Crédito Actual (ARS 100.000 a 4.000.000)", 
            min_value=100000, max_value=4000000, value=1000000, step=50000
        )
        bill_amt1 = st.number_input(
            "Saldo Facturado Último Mes (ARS 0 a 4.800.000)", 
            min_value=0, max_value=4800000, value=350000, step=25000
        )
        uso_limite_raw = bill_amt1 / limit_bal if limit_bal > 0 else 0
        uso_limite = min(uso_limite_raw, 1.2)
        st.info(f"📊 **Uso_Limite calculado:** {uso_limite_raw*100:.1f}% (acotado a 120% máx.)")

    with col_in3:
        st.subheader("⏱️ Comportamiento de Pago")
        pay_1 = st.number_input(
            "Meses de Atraso PAY_1 (entre -2 y 8)", 
            min_value=-2, max_value=8, value=0, step=1
        )
        st.caption("**Referencia PAY_1:** `-2` = Sin consumo | `-1` = Pago total | `0` = Pago mínimo al día | `1 a 8` = Meses de atraso")

    st.divider()

    # --- 2. MOTOR ECONOMÉTRICO (COEFICIENTES REALES HC3) ---
    def calcular_riesgo(uso, limite, edad, edu_sup, atraso):
        intercepto = 0.8001
        efecto_limite = -0.0538 * np.log(limite) if limite > 0 else 0
        efecto_edad = 0.0020 * edad
        efecto_atraso = 0.1204 * atraso
        efecto_uso_base = -0.0890 * uso
        
        efecto_edu = 0.0202 if edu_sup == 1 else 0.0
        efecto_interaccion = (-0.000066 * uso) if edu_sup == 1 else 0.0
            
        prob_cruda = (intercepto + efecto_limite + efecto_edad + 
                      efecto_atraso + efecto_uso_base + efecto_edu + efecto_interaccion)
        prob_final = np.clip(prob_cruda, 0.0, 1.0)
        return prob_final, prob_cruda

    prob_dec, prob_cruda_dec = calcular_riesgo(
        uso_limite, limit_bal, age, edu_cat, pay_1
    )
    prob_pct = prob_dec * 100
    prob_cruda_pct = prob_cruda_dec * 100
    MEDIA_DATASET = 22.1

    # --- 3. RESULTADO DE PROBABILIDAD DE DEFAULT ---
    st.subheader("🎯 Probabilidad de Default (PD)")
    diferencia_media = prob_pct - MEDIA_DATASET
    st.metric(
        label="Riesgo Estimado vs. Media Histórica (22.1%)",
        value=f"{prob_pct:.1f}%",
        delta=f"{diferencia_media:+.1f} p.p. vs promedio",
        delta_color="inverse"
    )
    st.progress(float(prob_dec))
    
    if prob_cruda_pct < 0 or prob_cruda_pct > 100:
        st.caption(f"⚠️ *Restricción MPL: Predicción lineal cruda = {prob_cruda_pct:.1f}%, acotada a [0%, 100%].*")

    st.divider()

    # --- 4. CÁLCULO FINANCIERO DE PRÉSTAMO AJUSTADO POR RIESGO ---
    st.subheader("📋 Dictamen de Análisis Crediticio y Política de Cupo")

    PD_MAX_TOLERADA = 0.40

    if prob_dec >= PD_MAX_TOLERADA:
        factor_otorgamiento = 0.0
        monto_prestable = 0
    else:
        factor_otorgamiento = ((1 - (prob_dec / PD_MAX_TOLERADA)) ** 1.2) * 1.50
        monto_prestable = int(round(limit_bal * factor_otorgamiento, -2))

    perdida_esperada = monto_prestable * prob_dec

    if prob_pct < 15:
        tier = "🟢 NIVEL A (Solvente / Prime)"
        politica = "APROBACIÓN PREFERENCIAL"
        color_box = "success"
        explicacion_riesgo = (
            f"Con una Probabilidad de Default de apenas **{prob_pct:.1f}%** (muy por debajo de la media), "
            f"el modelo habilita un multiplicador de **{factor_otorgamiento:.2f}x** sobre su capacidad (ARS {limit_bal:,.0f}), "
            f"autorizando un préstamo máximo de **ARS {monto_prestable:,.0f}** con una pérdida esperada acotada de **ARS {perdida_esperada:,.0f}**."
        )
    elif prob_pct < 28:
        tier = "🟡 NIVEL B (Riesgo Estándar)"
        politica = "APROBACIÓN REGULAR"
        color_box = "warning"
        explicacion_riesgo = (
            f"El solicitante registra un riesgo del **{prob_pct:.1f}%** (en línea con el promedio histórico de la muestra). "
            f"La fórmula ajusta su factor de exposición a **{factor_otorgamiento:.2f}x**, habilitando un desembolso máximo "
            f"de **ARS {monto_prestable:,.0f}** (pérdida esperada estimada: **ARS {perdida_esperada:,.0f}**)."
        )
    elif prob_pct < 40:
        tier = "🟠 NIVEL C (Riesgo Alto / Subprime)"
        politica = "APROBACIÓN RESTRINGIDA"
        color_box = "warning"
        explicacion_riesgo = (
            f"Debido a que la probabilidad de default escala al **{prob_pct:.1f}%**, el motor financiero penaliza el cupo "
            f"reduciendo el multiplicador a **{factor_otorgamiento:.2f}x**. Se autoriza un préstamo acotado de **ARS {monto_prestable:,.0f}** "
            f"para contener la pérdida esperada en **ARS {perdida_esperada:,.0f}**."
        )
    else:
        tier = "🔴 NIVEL D (Riesgo Crítico / Default)"
        politica = "RECHAZO AUTOMÁTICO"
        color_box = "error"
        explicacion_riesgo = (
            f"La probabilidad de incumplimiento (**{prob_pct:.1f}%**) supera el umbral máximo de tolerancia (40.0%). "
            f"{'El determinante principal es el atraso en pagos (`PAY_1 = ' + str(pay_1) + '`), que opaca cualquier efecto de la educación financiera.' if pay_1 > 0 else 'La combinación de baja capacidad crediticia y perfil demográfico eleva el riesgo.'} "
            f"El multiplicador cae a **0.00x** y el préstamo sugerido es **ARS 0**."
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clasificación de Riesgo", tier)
    c2.metric("Multiplicador de Riesgo", f"{factor_otorgamiento:.2f}x")
    c3.metric("Préstamo Máximo a Otorgar", f"ARS {monto_prestable:,.0f}")
    c4.metric("Pérdida Esperada (EL)", f"ARS {perdida_esperada:,.0f}")

    if color_box == "success":
        st.success(f"**Dictamen ({politica}):** {explicacion_riesgo}")
    elif color_box == "warning":
        st.warning(f"**Dictamen ({politica}):** {explicacion_riesgo}")
    else:
        st.error(f"**Dictamen ({politica}):** {explicacion_riesgo}")

    # --- 5. TRANSPARENCIA METODOLÓGICA ---
    with st.expander("ℹ️ Conclusión del Análisis Crediticio y Metodología"):
        st.markdown("""
        * **Hallazgo Principal (Muestra Taiwán):** Sobre los 30.000 clientes analizados, tener estudios superiores no actúa como escudo frente al sobreendeudamiento ($p = 0,997$) e incluso conlleva un leve mayor riesgo base (+2,02 p.p.). El **historial de atraso reciente (`PAY_1`)** posee un impacto predictivo exponencialmente mayor (+12,04 p.p. por mes) que cualquier credencial académica.
        * **Especificación Econométrica:** Modelo de Probabilidad Lineal (MCO) con dummy binaria de Educación Superior, término de interacción y errores robustos a heterocedasticidad (**HC3**) sobre N = 30.000 observaciones del repositorio UCI (Taiwán).
        * **Validez Externa y Restricciones:** Al tratarse de un MPL, las predicciones crudas pueden exceder teóricamente el intervalo [0, 1] y han sido acotadas. Los coeficientes provienen de cartera taiwanesa y se proyectan sobre límites en ARS de forma ilustrativa; para producción local requiere re-entrenamiento con datos argentinos.
        """)