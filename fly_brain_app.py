import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from neuprint import (
    Client,
    fetch_neurons,
    fetch_adjacencies,
    NeuronCriteria as NC,
)

from datetime import datetime


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Fruit Fly Brain Explorer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at top right,
                rgba(80, 90, 180, 0.15),
                transparent 35%
            ),
            linear-gradient(
                135deg,
                #080b14 0%,
                #0d1220 45%,
                #090c15 100%
            );
        color: #eeeeee;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            #090c15,
            #111827
        );
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    .main-title {
        font-size: 3.2rem;
        font-weight: 800;
        letter-spacing: -2px;
        margin-bottom: 0;
        background: linear-gradient(
            90deg,
            #ffffff,
            #8fa8ff,
            #bca7ff
        );
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .subtitle {
        color: #9ca3af;
        font-size: 1.05rem;
        margin-top: -5px;
        margin-bottom: 25px;
    }

    .glass-card {
        background: rgba(18, 24, 38, 0.78);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 10px 35px rgba(0,0,0,0.22);
        margin-bottom: 18px;
    }

    .metric-card {
        background: linear-gradient(
            135deg,
            rgba(35,42,65,0.9),
            rgba(18,24,38,0.9)
        );
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 18px;
        min-height: 120px;
    }

    .metric-title {
        color: #9ca3af;
        font-size: 0.85rem;
        margin-bottom: 7px;
    }

    .metric-value {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 800;
    }

    .metric-icon {
        font-size: 1.5rem;
        float: right;
    }

    .status-online {
        display: inline-block;
        padding: 5px 11px;
        border-radius: 999px;
        background: rgba(34,197,94,0.15);
        color: #86efac;
        border: 1px solid rgba(34,197,94,0.3);
        font-size: 0.8rem;
    }

    .status-offline {
        display: inline-block;
        padding: 5px 11px;
        border-radius: 999px;
        background: rgba(239,68,68,0.15);
        color: #fca5a5;
        border: 1px solid rgba(239,68,68,0.3);
        font-size: 0.8rem;
    }

    .target-box {
        background: linear-gradient(
            135deg,
            rgba(69,87,180,0.20),
            rgba(120,82,180,0.10)
        );
        border: 1px solid rgba(130,145,255,0.25);
        border-radius: 16px;
        padding: 16px;
        margin: 10px 0 20px 0;
    }

    .target-label {
        color: #9ca3af;
        font-size: 0.8rem;
    }

    .target-value {
        font-size: 1.35rem;
        font-weight: 700;
        color: #ffffff;
    }

    div[data-testid="stMetric"] {
        background: rgba(20,25,40,0.75);
        border: 1px solid rgba(255,255,255,0.07);
        padding: 15px;
        border-radius: 14px;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 750;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    .footer {
        text-align: center;
        color: #6b7280;
        padding: 30px 0 10px 0;
        font-size: 0.8rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "search_history" not in st.session_state:
    st.session_state.search_history = []

if "favorites" not in st.session_state:
    st.session_state.favorites = []

if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

if "selected_neuron" not in st.session_state:
    st.session_state.selected_neuron = None


# ============================================================
# CONNECT TO NEUPRINT
# ============================================================

@st.cache_resource
def get_neuprint_client():

    try:

        token = st.secrets["NEUPRINT_TOKEN"]

        client = Client(
            "neuprint.janelia.org",
            dataset="male-cns:v1.0",
            token=token
        )

        return client

    except Exception as e:

        return None


client = get_neuprint_client()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🧠 Fruit Fly Brain Explorer</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Explore neurons, cell types, brain regions and connectome relationships '
    'from the Janelia male-cns:v1.0 dataset.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# CONNECTION STATUS
# ============================================================

if client:

    st.markdown(
        '<span class="status-online">● neuPrint CONNECTED</span>',
        unsafe_allow_html=True
    )

else:

    st.markdown(
        '<span class="status-offline">● neuPrint NOT CONNECTED</span>',
        unsafe_allow_html=True
    )

    st.error(
        "neuPrint could not be connected. "
        "Add your API token to Streamlit Secrets as "
        "`NEUPRINT_TOKEN`."
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## 🧠 Brain Explorer")

st.sidebar.caption(
    "Janelia • male-cns:v1.0"
)

st.sidebar.divider()


# ============================================================
# SEARCH MODE
# ============================================================

st.sidebar.markdown("### 🔎 Search Mode")

search_mode = st.sidebar.radio(
    "Search by",
    [
        "Neuron Type",
        "Neuron Instance",
        "Body ID"
    ],
    index=0
)


# ============================================================
# PRESETS
# ============================================================

preset_options = {
    "Custom Search": "",
    "🍄 MBON — Mushroom Body Output": "MBON",
    "🧠 KC — Kenyon Cells": "KC",
    "🚀 DNge — Descending Neurons": "DNge",
    "👁️ LC — Lobula Columnar": "LC",
    "⏰ ER — Ellipsoid Ring": "ER",
    "🦋 AL — Antennal Lobe": "AL",
    "🌈 FB — Fan-shaped Body": "FB",
    "🔵 EB — Ellipsoid Body": "EB",
    "🟣 LH — Lateral Horn": "LH"
}

selected_preset = st.sidebar.selectbox(
    "Brain Structure Preset",
    list(preset_options.keys())
)

preset_value = preset_options[selected_preset]


# ============================================================
# SEARCH BOX
# ============================================================

if search_mode == "Body ID":

    search_value = st.sidebar.text_input(
        "Body ID",
        value=""
    )

else:

    search_value = st.sidebar.text_input(
        "Search term",
        value=preset_value
    )


# ============================================================
# SEARCH OPTIONS
# ============================================================

st.sidebar.markdown("### ⚙️ Search Options")

limit = st.sidebar.slider(
    "Maximum neurons",
    min_value=10,
    max_value=500,
    value=100,
    step=10
)

exact_match = st.sidebar.checkbox(
    "Exact match",
    value=False
)

include_unclassified = st.sidebar.checkbox(
    "Include unclassified neurons",
    value=True
)


# ============================================================
# SEARCH BUTTON
# ============================================================

search_clicked = st.sidebar.button(
    "🔍 SEARCH BRAIN",
    type="primary",
    use_container_width=True
)

clear_clicked = st.sidebar.button(
    "🗑️ Clear Results",
    use_container_width=True
)

if clear_clicked:

    st.session_state.results = pd.DataFrame()
    st.session_state.selected_neuron = None
    st.rerun()


# ============================================================
# SEARCH FUNCTION
# ============================================================

@st.cache_data(ttl=600)
def search_neurons(
    mode,
    query,
    max_rows,
    exact,
    include_unclassified
):

    if not query:
        return pd.DataFrame()

    query = str(query).strip()

    if mode == "Body ID":

        try:

            body_id = int(query)

            neurons, _ = fetch_neurons(
                NC(bodyId=body_id),
                client=client
            )

            return neurons.head(max_rows)

        except Exception:

            return pd.DataFrame()

    if exact:

        regex = f"^{query}$"

    else:

        regex = f".*{query}.*"

    if mode == "Neuron Type":

        criteria = NC(
            type=regex
        )

    else:

        criteria = NC(
            instance=regex
        )

    neurons, _ = fetch_neurons(
        criteria,
        client=client
    )

    if neurons.empty and mode == "Neuron Type":

        neurons, _ = fetch_neurons(
            NC(instance=regex),
            client=client
        )

    if not include_unclassified and not neurons.empty:

        if "type" in neurons.columns:

            neurons = neurons[
                neurons["type"].notna()
            ]

    return neurons.head(max_rows)


# ============================================================
# PERFORM SEARCH
# ============================================================

if search_clicked:

    if not search_value.strip():

        st.warning(
            "Enter a neuron type, instance or body ID first."
        )

    else:

        with st.spinner(
            "🧬 Querying the fruit fly connectome..."
        ):

            try:

                results = search_neurons(
                    search_mode,
                    search_value,
                    limit,
                    exact_match,
                    include_unclassified
                )

                st.session_state.results = results

                if search_value not in st.session_state.search_history:

                    st.session_state.search_history.insert(
                        0,
                        search_value
                    )

                    st.session_state.search_history = (
                        st.session_state.search_history[:10]
                    )

            except Exception as e:

                st.error(
                    f"Search failed: {e}"
                )


# ============================================================
# CURRENT TARGET
# ============================================================

active_target = search_value.strip()

if not active_target:

    active_target = "No target selected"

st.markdown(
    f"""
    <div class="target-box">

    <div class="target-label">
    CURRENT TARGET
    </div>

    <div class="target-value">
    🎯 {active_target}
    </div>

    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# TOP METRICS
# ============================================================

results = st.session_state.results

if not results.empty:

    total_neurons = len(results)

    unique_types = (
        results["type"].nunique()
        if "type" in results.columns
        else 0
    )

    unique_instances = (
        results["instance"].nunique()
        if "instance" in results.columns
        else 0
    )

    body_ids = (
        results["bodyId"].nunique()
        if "bodyId" in results.columns
        else 0
    )

else:

    total_neurons = 0
    unique_types = 0
    unique_instances = 0
    body_ids = 0


m1, m2, m3, m4 = st.columns(4)

with m1:

    st.metric(
        "🧠 Neurons",
        f"{total_neurons:,}"
    )

with m2:

    st.metric(
        "🧬 Cell Types",
        f"{unique_types:,}"
    )

with m3:

    st.metric(
        "🔬 Instances",
        f"{unique_instances:,}"
    )

with m4:

    st.metric(
        "🆔 Body IDs",
        f"{body_ids:,}"
    )


st.write("")


# ============================================================
# TABS
# ============================================================

tab_data, tab_stats, tab_neuron, tab_connections, tab_tools = st.tabs(
    [
        "📊 Data Explorer",
        "📈 Analytics",
        "🧬 Neuron Inspector",
        "🕸️ Connections",
        "🛠️ Tools"
    ]
)


# ============================================================
# DATA EXPLORER
# ============================================================

with tab_data:

    st.markdown(
        '<div class="section-title">'
        '📊 Connectome Inventory'
        '</div>',
        unsafe_allow_html=True
    )

    if results.empty:

        st.info(
            "Search for a neuron type, instance or body ID "
            "using the sidebar."
        )

    else:

        st.success(
            f"Found {len(results):,} neurons."
        )

        display_df = results.copy()

        st.dataframe(
            display_df,
            use_container_width=True,
            height=520,
            hide_index=True
        )

        st.write("")

        download_col1, download_col2 = st.columns(2)

        with download_col1:

            csv_data = display_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "📥 Download CSV",
                csv_data,
                "fly_brain_neurons.csv",
                "text/csv",
                use_container_width=True
            )

        with download_col2:

            json_data = display_df.to_json(
                orient="records",
                indent=2
            )

            st.download_button(
                "📥 Download JSON",
                json_data,
                "fly_brain_neurons.json",
                "application/json",
                use_container_width=True
            )


# ============================================================
# ANALYTICS
# ============================================================

with tab_stats:

    st.markdown(
        '<div class="section-title">'
        '📈 Brain Analytics'
        '</div>',
        unsafe_allow_html=True
    )

    if results.empty:

        st.info(
            "Search for neurons to generate analytics."
        )

    else:

        if "type" in results.columns:

            type_counts = (
                results["type"]
                .fillna("Unclassified")
                .value_counts()
                .head(20)
                .reset_index()
            )

            type_counts.columns = [
                "Neuron Type",
                "Count"
            ]

            fig = px.bar(
                type_counts,
                x="Count",
                y="Neuron Type",
                orientation="h",
                title="Top Neuron Types"
            )

            fig.update_layout(
                template="plotly_dark",
                height=600,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        if "instance" in results.columns:

            instance_counts = (
                results["instance"]
                .fillna("Unknown")
                .value_counts()
                .head(20)
                .reset_index()
            )

            instance_counts.columns = [
                "Instance",
                "Count"
            ]

            fig2 = px.bar(
                instance_counts,
                x="Instance",
                y="Count",
                title="Neuron Instance Distribution"
            )

            fig2.update_layout(
                template="plotly_dark",
                height=450,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(
                fig2,
                use_container_width=True
            )


        # DATA COMPLETENESS

        st.markdown(
            '<div class="section-title">'
            '🔍 Data Completeness'
            '</div>',
            unsafe_allow_html=True
        )

        completeness = (
            results.notna()
            .mean()
            .sort_values(ascending=False)
            * 100
        )

        completeness_df = pd.DataFrame({
            "Field": completeness.index,
            "Available": completeness.values
        })

        fig3 = px.bar(
            completeness_df,
            x="Available",
            y="Field",
            orientation="h",
            range_x=[0, 100],
            title="Percentage of Non-Empty Values"
        )

        fig3.update_layout(
            template="plotly_dark",
            height=500,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig3,
            use_container_width=True
        )


# ============================================================
# NEURON INSPECTOR
# ============================================================

with tab_neuron:

    st.markdown(
        '<div class="section-title">'
        '🧬 Neuron Inspector'
        '</div>',
        unsafe_allow_html=True
    )

    if results.empty:

        st.info(
            "Search for neurons first."
        )

    else:

        if "bodyId" in results.columns:

            body_options = results["bodyId"].dropna().tolist()

            if body_options:

                selected_body = st.selectbox(
                    "Select a neuron Body ID",
                    body_options
                )

                selected_row = results[
                    results["bodyId"] == selected_body
                ]

                if not selected_row.empty:

                    neuron = selected_row.iloc[0]

                    st.session_state.selected_neuron = selected_body

                    a, b, c_col = st.columns(3)

                    with a:

                        st.metric(
                            "Body ID",
                            str(selected_body)
                        )

                    with b:

                        neuron_type = neuron.get(
                            "type",
                            "Unknown"
                        )

                        st.metric(
                            "Type",
                            str(neuron_type)
                        )

                    with c_col:

                        instance = neuron.get(
                            "instance",
                            "Unknown"
                        )

                        st.metric(
                            "Instance",
                            str(instance)
                        )

                    st.write("")

                    st.markdown(
                        "### 🔬 Neuron Metadata"
                    )

                    neuron_df = pd.DataFrame(
                        {
                            "Property": neuron.index,
                            "Value": [
                                str(x)
                                for x in neuron.values
                            ]
                        }
                    )

                    st.dataframe(
                        neuron_df,
                        use_container_width=True,
                        hide_index=True
                    )

                    # FAVORITE

                    is_favorite = (
                        selected_body
                        in st.session_state.favorites
                    )

                    if is_favorite:

                        if st.button(
                            "⭐ Remove from Favorites"
                        ):

                            st.session_state.favorites.remove(
                                selected_body
                            )

                            st.rerun()

                    else:

                        if st.button(
                            "☆ Add to Favorites"
                        ):

                            st.session_state.favorites.append(
                                selected_body
                            )

                            st.rerun()

                    # NEUPRINT LINK

                    neuprint_url = (
                        "https://neuprint.janelia.org/"
                        "?dataset=male-cns%3Av1.0"
                        f"&qt=findneurons&bodyId={selected_body}"
                    )

                    st.link_button(
                        "🌐 Open Neuron in neuPrint",
                        neuprint_url,
                        use_container_width=True
                    )


# ============================================================
# CONNECTIONS
# ============================================================

with tab_connections:

    st.markdown(
        '<div class="section-title">'
        '🕸️ Neuron Connectivity'
        '</div>',
        unsafe_allow_html=True
    )

    if results.empty:

        st.info(
            "Search for neurons and select a Body ID "
            "to investigate connectivity."
        )

    else:

        if "bodyId" not in results.columns:

            st.warning(
                "The search results do not contain Body IDs."
            )

        else:

            available_ids = (
                results["bodyId"]
                .dropna()
                .astype(int)
                .tolist()
            )

            if available_ids:

                connection_body = st.selectbox(
                    "Neuron to investigate",
                    available_ids,
                    key="connection_body"
                )

                connection_limit = st.slider(
                    "Maximum connections",
                    10,
                    500,
                    100,
                    key="connection_limit"
                )

                load_connections = st.button(
                    "🕸️ Load Connections",
                    type="primary"
                )

                if load_connections:

                    with st.spinner(
                        "Tracing synaptic connections..."
                    ):

                        try:

                            neuron_criteria = NC(
                                bodyId=connection_body
                            )

                            upstream, downstream = fetch_adjacencies(
                                neuron_criteria,
                                None,
                                client=client
                            )

                            st.session_state["upstream"] = upstream
                            st.session_state["downstream"] = downstream

                        except Exception as e:

                            st.error(
                                f"Could not load connections: {e}"
                            )

                upstream = st.session_state.get(
                    "upstream",
                    pd.DataFrame()
                )

                downstream = st.session_state.get(
                    "downstream",
                    pd.DataFrame()
                )

                c1, c2 = st.columns(2)

                with c1:

                    st.metric(
                        "⬅️ Upstream Records",
                        len(upstream)
                    )

                with c2:

                    st.metric(
                        "➡️ Downstream Records",
                        len(downstream)
                    )

                if not upstream.empty:

                    st.markdown(
                        "### ⬅️ Upstream Connections"
                    )

                    st.dataframe(
                        upstream.head(connection_limit),
                        use_container_width=True,
                        hide_index=True
                    )

                    upstream_csv = upstream.to_csv(
                        index=False
                    ).encode("utf-8")

                    st.download_button(
                        "📥 Download Upstream CSV",
                        upstream_csv,
                        "upstream_connections.csv",
                        "text/csv"
                    )

                if not downstream.empty:

                    st.markdown(
                        "### ➡️ Downstream Connections"
                    )

                    st.dataframe(
                        downstream.head(connection_limit),
                        use_container_width=True,
                        hide_index=True
                    )

                    downstream_csv = downstream.to_csv(
                        index=False
                    ).encode("utf-8")

                    st.download_button(
                        "📥 Download Downstream CSV",
                        downstream_csv,
                        "downstream_connections.csv",
                        "text/csv"
                    )


# ============================================================
# TOOLS
# ============================================================

with tab_tools:

    st.markdown(
        '<div class="section-title">'
        '🛠️ Explorer Tools'
        '</div>',
        unsafe_allow_html=True
    )

    tool1, tool2 = st.columns(2)

    # --------------------------------------------------------
    # 3D VIEWER
    # --------------------------------------------------------

    with tool1:

        st.markdown("### 🌐 3D Brain Viewer")

        st.write(
            "Open the official neuPrint interface for interactive "
            "connectome exploration."
        )

        neuprint_home = (
            "https://neuprint.janelia.org/"
            "?dataset=male-cns%3Av1.0"
        )

        st.link_button(
            "🚀 Launch neuPrint",
            neuprint_home,
            use_container_width=True,
            type="primary"
        )

        st.caption(
            "The official neuPrint interface provides the "
            "interactive connectome visualisation tools."
        )


    # --------------------------------------------------------
    # BODY ID TOOL
    # --------------------------------------------------------

    with tool2:

        st.markdown("### 🆔 Body ID Lookup")

        body_lookup = st.text_input(
            "Enter a Body ID",
            key="body_lookup"
        )

        if st.button(
            "🔎 Inspect Body ID",
            use_container_width=True
        ):

            try:

                body_number = int(
                    body_lookup.strip()
                )

                neurons, _ = fetch_neurons(
                    NC(bodyId=body_number),
                    client=client
                )

                if neurons.empty:

                    st.warning(
                        "No neuron was found with that Body ID."
                    )

                else:

                    st.session_state.results = neurons
                    st.session_state.selected_neuron = body_number

                    st.success(
                        f"Found Body ID {body_number}"
                    )

                    st.rerun()

            except ValueError:

                st.error(
                    "Body ID must be a number."
                )

            except Exception as e:

                st.error(
                    f"Lookup failed: {e}"
                )


    st.divider()


    # ========================================================
    # SEARCH HISTORY
    # ========================================================

    st.markdown(
        "### 🕘 Search History"
    )

    if st.session_state.search_history:

        for item in st.session_state.search_history:

            if st.button(
                f"🔎 {item}",
                key=f"history_{item}"
            ):

                st.session_state.results = search_neurons(
                    "Neuron Type",
                    item,
                    limit,
                    False,
                    True
                )

                st.rerun()

    else:

        st.caption(
            "Your searches will appear here."
        )


    # ========================================================
    # FAVORITES
    # ========================================================

    st.markdown(
        "### ⭐ Favorite Neurons"
    )

    if st.session_state.favorites:

        favorite_df = pd.DataFrame(
            {
                "Body ID":
                    st.session_state.favorites
            }
        )

        st.dataframe(
            favorite_df,
            use_container_width=True,
            hide_index=True
        )

        if st.button(
            "🗑️ Clear Favorites"
        ):

            st.session_state.favorites = []
            st.rerun()

    else:

        st.caption(
            "No favorite neurons yet."
        )


    st.divider()


    # ========================================================
    # DATASET INFO
    # ========================================================

    st.markdown(
        "### 🧪 Dataset Information"
    )

    info_col1, info_col2 = st.columns(2)

    with info_col1:

        st.write(
            "**Dataset:** `male-cns:v1.0`"
        )

        st.write(
            "**Source:** Janelia Research Campus"
        )

    with info_col2:

        st.write(
            "**Database:** neuPrint"
        )

        st.write(
            "**Explorer:** Fruit Fly Brain Explorer"
        )


# ============================================================
# EXPORT SUMMARY
# ============================================================

if not results.empty:

    st.divider()

    st.markdown(
        "### 📋 Export Summary"
    )

    summary = {
        "Search": active_target,
        "Search Mode": search_mode,
        "Rows": len(results),
        "Unique Types": unique_types,
        "Unique Instances": unique_instances,
        "Body IDs": body_ids,
        "Generated": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    summary_df = pd.DataFrame(
        [summary]
    )

    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">

    🧠 Fruit Fly Brain Connectome Explorer<br>

    Built with Streamlit + neuPrint + Plotly<br>

    Dataset: Janelia male-cns:v1.0

    </div>
    """,
    unsafe_allow_html=True
)
