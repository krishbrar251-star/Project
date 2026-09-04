"""
Cp vs T Materials Explorer
---------------------------
Streamlit app that reads a CSV of materials with Kelley-type
heat-capacity coefficients:

        Cp(T) = a + b*T + c/T^2        (Cp in J/mol*K, T in K)

CSV must have (at least) these columns:
    Name, Formula, Category, T_min_K, T_max_K, Unit, a, b, c, Source

Run with:
    streamlit run cp_explorer_app.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(page_title="Cp vs T Materials Explorer", layout="wide")

CSV_PATH = "data.csv"   # keep the CSV in the same folder as this script


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------




  

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
   
    return df


def cp_curve(a: float, b: float, c: float, t_arr: np.ndarray) -> np.ndarray:
    """Kelley equation: Cp = a + b*T + c/T^2"""
    return a + b * t_arr + c / (t_arr ** 2)




# --------------------------------------------------------------------------
# Load data
# --------------------------------------------------------------------------
df = load_data(CSV_PATH)

# Make sure numeric columns are actually numeric (a bad cell, stray text,
# or thousands-separator in the CSV would otherwise cause silent errors
# later when plotting).
for numeric_col in ["T_min_K", "T_max_K", "a", "b", "c"]:
    df[numeric_col] = pd.to_numeric(df[numeric_col], errors="coerce")

bad_rows = df[df[["T_min_K", "T_max_K", "a", "b", "c"]].isna().any(axis=1)]
if len(bad_rows) > 0:
    st.warning(
        f"{len(bad_rows)} row(s) had non-numeric values in T_min_K/T_max_K/a/b/c "
        "and were dropped: " + ", ".join(bad_rows["Name"].astype(str).tolist())
    )
    df = df.dropna(subset=["T_min_K", "T_max_K", "a", "b", "c"])

st.title("🔬 Cp vs T Materials Explorer")
st.caption("Heat capacity curves from the Kelley equation:  Cp = a + b·T + c/T²  (J/mol·K)")

tab_single, tab_compare = st.tabs(["📈 Single Material", "⚖️ Compare Materials"])


# ==========================================================================
# TAB 1 — SINGLE MATERIAL
# ==========================================================================
with tab_single:
    st.subheader("Explore a single material")

    col1, col2 = st.columns(2)

    with col1:
        category = st.selectbox(
            "1. Select category",
            sorted(df["Category"].unique()),
            key="single_category",
        )

    filtered_df = df[df["Category"] == category]

    with col2:
        material_name = st.selectbox(
            "2. Select material",
            sorted(filtered_df["Material_Name"].unique()),
            key="single_material",
        )

    row = filtered_df[filtered_df["Material_Name"] == material_name].iloc[0]

    t_min, t_max = float(row["T_min_K"]), float(row["T_max_K"])

    st.markdown(
        f"**Formula:** {row['Chemical_Formula']}  |  **Valid range:** {t_min:.0f} K – {t_max:.0f} K  "
        f"|  **Source:** {row['Source_Database']}"
    )

    # Temperature range slider restricted to [T_min_K, T_max_K] of the material
    t_range = st.slider(
        "3. Select temperature range (K) — restricted to this material's valid range",
        min_value=t_min,
        max_value=t_max,
        value=(t_min, t_max),
        step=max((t_max - t_min) / 200, 1.0),
        key="single_t_range",
    )

    t_start, t_end = t_range
    T = np.linspace(t_start, t_end, 300)
    Cp = cp_curve(row["a"], row["b"], row["c"], T)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(T, Cp, color="#d62728", linewidth=2.2, label=material_name)
    ax.set_xlabel("Temperature, T (K)")
    ax.set_ylabel(f"Specific heat, Cp ({row['Cp_Unit']})")
    ax.set_title(f"Cp vs T — {material_name} ({row['Chemical_Formula']})")
    ax.grid(True, alpha=0.3)
    ax.legend()
    st.pyplot(fig)

    with st.expander("Show raw Cp–T data table"):
        table = pd.DataFrame({"T (K)": T, "Cp (J/mol*K)": Cp})
        st.dataframe(table, use_container_width=True)
        st.download_button(
            "Download this curve as CSV",
            table.to_csv(index=False).encode("utf-8"),
            file_name=f"{material_name}_Cp_vs_T.csv",
            mime="text/csv",
        )

    with st.expander("Show equation & coefficients"):
        st.latex(r"C_p(T) = a + bT + \dfrac{c}{T^2}")
        st.write(
            f"a = {row['a']:.5g}, "
            f"b = {row['b']:.5g}, "
            f"c = {row['c']:.5g}"
        )


# ==========================================================================
# TAB 2 — COMPARE MATERIALS
# ==========================================================================
with tab_compare:
    st.subheader("Compare Cp–T curves of multiple materials (same conditions)")

    col1, col2 = st.columns(2)

    with col1:
        compare_categories = st.multiselect(
            "1. Filter by category (optional — leave empty to show all)",
            sorted(df["Category"].unique()),
            key="compare_categories",
        )

    compare_pool = df if not compare_categories else df[df["Category"].isin(compare_categories)]

    with col2:
        compare_materials = st.multiselect(
            "2. Select materials to compare",
            sorted(compare_pool["Material_Name"].unique()),
            default=list(sorted(compare_pool["Material_Name"].unique()))[:2],
            key="compare_materials",
        )

    if len(compare_materials) == 0:
        st.info("Select at least one material to compare.")
    else:
        selected_rows = df[df["Material_Name"].isin(compare_materials)]

        # The comparison must use the SAME temperature window for every
        # material, so restrict the slider to the overlap of all selected
        # materials' valid ranges.
        common_t_min = float(selected_rows["T_min_K"].max())
        common_t_max = float(selected_rows["T_max_K"].min())

        if common_t_min >= common_t_max:
            st.error(
                "The selected materials have no overlapping valid temperature "
                "range in common, so they cannot be compared under identical "
                "conditions. Choose a different set of materials."
            )
        else:
            st.markdown(
                f"**Common valid range for the selected materials:** "
                f"{common_t_min:.0f} K – {common_t_max:.0f} K"
            )

            t_range_cmp = st.slider(
                "3. Select temperature range (K) — restricted to the common valid range",
                min_value=common_t_min,
                max_value=common_t_max,
                value=(common_t_min, common_t_max),
                step=max((common_t_max - common_t_min) / 200, 1.0),
                key="compare_t_range",
            )

            t_start, t_end = t_range_cmp
            T = np.linspace(t_start, t_end, 300)

            fig, ax = plt.subplots(figsize=(9, 5.5))
            cmap = plt.get_cmap("tab10")

            comparison_table = {"T (K)": T}
            for i, (_, r) in enumerate(selected_rows.iterrows()):
                Cp = cp_curve(r["a"], r["b"], r["c"], T)
                ax.plot(T, Cp, linewidth=2.2, color=cmap(i % 10),
                         label=f"{r['Material_Name']} ({r['Chemical_Formula']})")
                comparison_table[f"{r['Material_Name']} Cp (J/mol*K)"] = Cp

            ax.set_xlabel("Temperature, T (K)")
            ax.set_ylabel("Specific heat, Cp (J/mol*K)")
            ax.set_title("Cp vs T — Material Comparison (identical T range)")
            ax.grid(True, alpha=0.3)
            ax.legend()
            st.pyplot(fig)

            with st.expander("Show comparison table & summary"):
                comp_df = pd.DataFrame(comparison_table)
                st.dataframe(comp_df, use_container_width=True)
                st.download_button(
                    "Download comparison data as CSV",
                    comp_df.to_csv(index=False).encode("utf-8"),
                    file_name="Cp_comparison.csv",
                    mime="text/csv",
                )

                summary_rows = []
                for _, r in selected_rows.iterrows():
                    Cp = cp_curve(r["a"], r["b"], r["c"], T)
                    summary_rows.append({
                        "Material": r["Material_Name"],
                        "Formula": r["Chemical_Formula"],
                        "Category": r["Category"],
                        f"Cp at {t_start:.0f} K": round(float(Cp[0]), 2),
                        f"Cp at {t_end:.0f} K": round(float(Cp[-1]), 2),
                        "Source": r["Source_Database"],
                    })
                st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)


# --------------------------------------------------------------------------
# Sidebar: full database view
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Database")
    st.write(f"{len(df)} materials loaded, {df['Category'].nunique()} categories.")
    if st.checkbox("Show full materials table"):
        st.dataframe(df, use_container_width=True)
