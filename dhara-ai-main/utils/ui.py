import streamlit as st


def landing_fullscreen_header() -> None:
    st.markdown(
        """
        <div class="dhara-shell">
          <div class="dhara-topbar">
            <div class="dhara-brand">
              <span class="dhara-brand-badge">Dh</span>
              <span>Dhāra AI</span>
            </div>
            <div class="dhara-muted" style="font-weight:600;">Agricultural credit decisioning</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero_section() -> None:
    st.markdown(
        """
        <div class="dhara-hero">
          <div class="dhara-hero-content">
            <div class="dhara-kicker">Corporate-grade agricultural credit intelligence</div>
            <div class="dhara-title">Dhāra AI — Agricultural Credit Scoring</div>
            <div class="dhara-subtitle">
              Dhāra AI helps lenders underwrite agricultural loans by combining model-driven Trust Scores, verification confidence, and live climate context
              for every farmer application — so decisions are faster, more explainable, and grounded in agronomic reality.
            </div>
            <div class="dhara-badges">
              <span class="dhara-badge">ML Trust Score per farmer</span>
              <span class="dhara-badge">Rule-based verification confidence</span>
              <span class="dhara-badge">Live weather & rainfall signals</span>
              <span class="dhara-badge">Lender-ready PDF & portfolio reports</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_cards() -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
            <div class="dhara-card dhara-anim dhara-delay-1">
              <h4>End-to-end workflow</h4>
              <p>From onboarding to scoring and simulation, designed like a real underwriting tool — not a demo.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="dhara-card dhara-anim dhara-delay-2">
              <h4>Explainable outcomes</h4>
              <p>Confidence penalties and model-driven trust score combine into a clear, actionable risk status.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div class="dhara-card dhara-anim dhara-delay-3">
              <h4>Operational readiness</h4>
              <p>Role-based login, consistent UI system, and pragmatic defaults to keep decisioning fast.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def workflow_stepper() -> None:
    st.markdown(
        """
        <div class="dhara-workflow dhara-anim dhara-delay-2">
          <div class="dhara-workflow-inner">
            <div class="dhara-workflow-title">Workflow (how Dhāra AI works)</div>
            <div class="dhara-stepper">
              <div class="dhara-stepper-item">
                <div class="dhara-stepper-kicker">Step 01</div>
                <div class="dhara-stepper-head">Onboard farmer</div>
                <div class="dhara-stepper-desc">Capture identity, farm profile, crop season, and requested loan.</div>
              </div>
              <div class="dhara-stepper-item">
                <div class="dhara-stepper-kicker">Step 02</div>
                <div class="dhara-stepper-head">Enrich with climate</div>
                <div class="dhara-stepper-desc">Fetch live weather + rainfall outlook for the farmer’s location.</div>
              </div>
              <div class="dhara-stepper-item">
                <div class="dhara-stepper-kicker">Step 03</div>
                <div class="dhara-stepper-head">Score & verify</div>
                <div class="dhara-stepper-desc">Compute ML Trust Score + rule-based verification confidence with explainable signals.</div>
              </div>
              <div class="dhara-stepper-item">
                <div class="dhara-stepper-kicker">Step 04</div>
                <div class="dhara-stepper-head">Approve & report</div>
                <div class="dhara-stepper-desc">Admin reviews portfolio, approves amount, and downloads lender-ready PDFs.</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def process_steps() -> None:
    st.markdown("### Process flow")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            """
            <div class="dhara-step">
              <div class="dhara-step-num">1</div>
              <div>
                <b>Identify profile</b><br/>
                <span class="dhara-muted">New / Existing / Verified farmer verification intensity.</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            """
            <div class="dhara-step">
              <div class="dhara-step-num">2</div>
              <div>
                <b>Capture inputs</b><br/>
                <span class="dhara-muted">Agronomic, environment, and financial proxy indicators.</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            """
            <div class="dhara-step">
              <div class="dhara-step-num">3</div>
              <div>
                <b>Score & simulate</b><br/>
                <span class="dhara-muted">Dashboard, risk status, and what‑if stress testing.</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def section_divider() -> None:
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

