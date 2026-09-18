import streamlit as st
import pandas as pd
from neuprint import Client, fetch_neurons, fetch_adjacencies, NeuronCriteria as NC


st.set_page_config(
    page_title="Fruit Fly Brain Connectome Explorer",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>

.stApp {
    background: #0b1020;
    color: #e8ecf5;
}

[data-testid="stSidebar"] {
    background: #11182b;
    border-right: 1px solid #26314d;
}

[data-testid="stSidebar"] * {
    color: #e8ecf5;
}

.main-title {
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 5px;
}

.subtitle {
    color: #8e9bb5;
    font-size: 16px;
    margin-bottom: 25px;
}

.section-title {
    font-size: 23px;
    font-weight: 700;
    margin-top: 10px;
    margin-bottom: 12px;
}

.info-box {
    background: #131c31;
    border: 1px solid #344362;
    border-radius: 12px;
    padding: 15px;
    margin-top: 8px;
    margin-bottom: 12px;
}

.info-title {
    font-size: 17px;
    font-weight: 700;
    margin-bottom: 6px;
}

.info-text {
    color: #aab5ca;
    font-size: 14px;
    line-height: 1.5;
}

.stButton > button {
    border-radius: 10px;
    border: 1px solid #344362;
    background: #18233b;
    color: #e8ecf5;
    font-weight: 600;
}

.stButton > button:hover {
    border-color: #6078bd;
    background: #202e4c;
}

[data-testid="stMetric"] {
    background: #131c31;
    border: 1px solid #263451;
    border-radius: 14px;
    padding: 15px;
}

div[data-baseweb="tab-list"] {
    gap: 8px;
}

button[data-baseweb="tab"] {
    border-radius: 9px;
}

hr {
    border-color: #263451;
}

.brain-part {
    font-size: 15px;
    font-weight: 600;
    padding-top: 5px;
}

</style>
""", unsafe_allow_html=True)


st.markdown(
    '<div class="main-title">Fruit Fly Brain Connectome Explorer</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Explore neurons, brain regions, connectivity and metadata '
    'from the Janelia neuPrint male-cns:v1.0 dataset.'
    '</div>',
    unsafe_allow_html=True
)


if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

if "selected_neuron" not in st.session_state:
    st.session_state.selected_neuron = None

if "favorites" not in st.session_state:
    st.session_state.favorites = []

if "history" not in st.session_state:
    st.session_state.history = []

if "upstream" not in st.session_state:
    st.session_state.upstream = pd.DataFrame()

if "downstream" not in st.session_state:
    st.session_state.downstream = pd.DataFrame()

if "brain_info" not in st.session_state:
    st.session_state.brain_info = None


@st.cache_resource
def get_neuprint_client():

    try:

        token = st.secrets["NEUPRINT_TOKEN"]

        return Client(
            "neuprint.janelia.org",
            dataset="male-cns:v1.0",
            token=token
        )

    except Exception as e:

        st.error(
            "Could not connect to neuPrint."
        )

        st.caption(
            "Check that NEUPRINT_TOKEN is configured correctly."
        )

        st.caption(str(e))

        return None


client = get_neuprint_client()


if client is None:
    st.stop()


BRAIN_PARTS = {

    "Mushroom Body": {
        "search": "MBON",
        "description":
            "A brain region strongly associated with learning and memory. "
            "Mushroom body output neurons help send processed information "
            "to other parts of the brain."
    },

    "Kenyon Cells": {
        "search": "KC",
        "description":
            "Kenyon cells are major neurons of the mushroom body. "
            "They receive information from sensory systems and are "
            "important for learning and memory."
    },

    "Descending Neurons": {
        "search": "DNge",
        "description":
            "Descending neurons carry information from the brain toward "
            "motor systems in the ventral nerve cord."
    },

    "Visual Neurons": {
        "search": "LC",
        "description":
            "Lobula columnar neurons are involved in processing visual "
            "information and responding to visual features."
    },

    "Ellipsoid Ring": {
        "search": "ER",
        "description":
            "Ellipsoid ring neurons are associated with the central complex, "
            "a region involved in navigation and behavioural control."
    },

    "Antennal Lobe": {
        "search": "AL",
        "description":
            "The antennal lobe is an important olfactory processing region. "
            "It receives information related to smells detected by the fly."
    },

    "Fan-Shaped Body": {
        "search": "FB",
        "description":
            "The fan-shaped body is part of the central complex and is "
            "involved in processing information used for behaviour and navigation."
    },

    "Ellipsoid Body": {
        "search": "EB",
        "description":
            "The ellipsoid body is part of the central complex and has "
            "important roles in navigation and spatial orientation."
    },

    "Lateral Horn": {
        "search": "LH",
        "description":
            "The lateral horn is involved in processing olfactory information "
            "and connecting sensory information with behavioural responses."
    },

    "Central Complex": {
        "search": "CX",
        "description":
            "The central complex is a group of brain structures involved in "
            "navigation, movement, orientation and behavioural control."
    }
}


@st.dialog("Brain Part Information")
def show_brain_info(name, description):

    st.subheader(name)

    st.write(description)

    st.divider()

    st.caption(
        "This description is a simplified overview intended to help "
        "with exploring the connectome."
    )


@st.cache_data(show_spinner=False)
def search_neurons(
    search_mode,
    search_value,
    exact_match,
    max_results,
    include_unclassified
):

    if not search_value:
        return pd.DataFrame()

    value = str(search_value).strip()

    if search_mode == "Body ID":

        try:

            body_id = int(value)

        except ValueError:

            return pd.DataFrame()

        criteria = NC(
            bodyId=body_id
        )

    else:

        if exact_match:

            regex = f"^{value}$"

        else:

            regex = f".*{value}.*"

        if search_mode == "Neuron Type":

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

    if neurons is None or neurons.empty:

        return pd.DataFrame()


    if not include_unclassified and "type" in neurons.columns:

        neurons = neurons[
            neurons["type"]
            .fillna("")
            .astype(str)
            .str.strip()
            != ""
        ]


    return neurons.head(max_results)


with st.sidebar:

    st.header("Brain Structures")

    st.caption(
        "Select a structure or search manually."
    )


    selected_structure = st.selectbox(
        "Structure",
        [
            "Custom Search"
        ] + list(BRAIN_PARTS.keys())
    )


    if selected_structure != "Custom Search":

        structure_data = BRAIN_PARTS[
            selected_structure
        ]

        st.markdown(
            f'<div class="brain-part">{selected_structure}</div>',
            unsafe_allow_html=True
        )

        if st.button(
            "i",
            key="info_" + selected_structure,
            help=f"Information about {selected_structure}"
        ):

            show_brain_info(
                selected_structure,
                structure_data["description"]
            )

        selected_preset = structure_data["search"]

    else:

        selected_preset = ""


    st.divider()

    st.header("Search")

    search_mode = st.selectbox(
        "Search by",
        [
            "Neuron Type",
            "Neuron Instance",
            "Body ID"
        ]
    )


    if search_mode == "Body ID":

        search_value = st.text_input(
            "Body ID",
            value=""
        )

    else:

        search_value = st.text_input(
            "Search value",
            value=selected_preset
        )


    exact_match = st.checkbox(
        "Exact match",
        value=False
    )


    max_results = st.slider(
        "Maximum results",
        min_value=10,
        max_value=500,
        value=100,
        step=10
    )


    include_unclassified = st.checkbox(
        "Include unclassified neurons",
        value=False
    )


    search_button = st.button(
        "Search Connectome",
        use_container_width=True,
        type="primary"
    )


    st.divider()

    st.header("Quick Searches")


    quick_searches = [
        "Mushroom Body",
        "Kenyon Cells",
        "Descending Neurons",
        "Visual Neurons",
        "Ellipsoid Ring"
    ]


    for quick_name in quick_searches:

        if st.button(
            quick_name,
            use_container_width=True,
            key="quick_" + quick_name
        ):

            st.session_state.quick_search = (
                BRAIN_PARTS[quick_name]["search"]
            )


    if "quick_search" in st.session_state:

        search_value = st.session_state.quick_search

        search_mode = "Neuron Type"

        search_button = True

        del st.session_state.quick_search


if search_button:

    if not search_value:

        st.warning(
            "Enter a search value first."
        )

    else:

        with st.spinner(
            "Searching the connectome..."
        ):

            try:

                results = search_neurons(
                    search_mode,
                    search_value,
                    exact_match,
                    max_results,
                    include_unclassified
                )

                st.session_state.results = results


                search_record = (
                    f"{search_mode}: {search_value}"
                )


                if search_record not in st.session_state.history:

                    st.session_state.history.insert(
                        0,
                        search_record
                    )


                st.session_state.history = (
                    st.session_state.history[:10]
                )


            except Exception as e:

                st.error(
                    "The neuPrint query failed."
                )

                st.exception(e)


results = st.session_state.results


if not results.empty:

    st.markdown(
        '<div class="section-title">Connectome Overview</div>',
        unsafe_allow_html=True
    )


    neuron_count = len(results)


    if "type" in results.columns:

        type_count = (
            results["type"]
            .dropna()
            .astype(str)
            .nunique()
        )

    else:

        type_count = 0


    if "instance" in results.columns:

        instance_count = (
            results["instance"]
            .dropna()
            .astype(str)
            .nunique()
        )

    else:

        instance_count = 0


    if "bodyId" in results.columns:

        body_count = results["bodyId"].nunique()

    else:

        body_count = 0


    col1, col2, col3, col4 = st.columns(4)


    with col1:

        st.metric(
            "Neurons",
            f"{neuron_count:,}"
        )


    with col2:

        st.metric(
            "Neuron Types",
            f"{type_count:,}"
        )


    with col3:

        st.metric(
            "Instances",
            f"{instance_count:,}"
        )


    with col4:

        st.metric(
            "Body IDs",
            f"{body_count:,}"
        )


st.divider()


tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Data Explorer",
        "Analytics",
        "Neuron Inspector",
        "Connections",
        "Tools"
    ]
)


with tab1:

    st.markdown(
        '<div class="section-title">Neuron Data Explorer</div>',
        unsafe_allow_html=True
    )


    if results.empty:

        st.info(
            "Search for a neuron type, instance or Body ID to begin."
        )

    else:

        st.dataframe(
            results,
            use_container_width=True,
            height=520
        )


        csv_data = results.to_csv(
            index=False
        ).encode("utf-8")


        json_data = results.to_json(
            orient="records",
            indent=2
        ).encode("utf-8")


        col1, col2 = st.columns(2)


        with col1:

            st.download_button(
                "Download CSV",
                csv_data,
                "fly_brain_neurons.csv",
                "text/csv",
                use_container_width=True
            )


        with col2:

            st.download_button(
                "Download JSON",
                json_data,
                "fly_brain_neurons.json",
                "application/json",
                use_container_width=True
            )


with tab2:

    st.markdown(
        '<div class="section-title">Connectome Analytics</div>',
        unsafe_allow_html=True
    )


    if results.empty:

        st.info(
            "Run a search to generate analytics."
        )

    else:

        if "type" in results.columns:

            type_counts = (
                results["type"]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .head(20)
            )


            st.subheader(
                "Most Common Neuron Types"
            )


            st.bar_chart(
                type_counts
            )


        if "instance" in results.columns:

            instance_counts = (
                results["instance"]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .head(20)
            )


            st.subheader(
                "Most Common Instances"
            )


            st.bar_chart(
                instance_counts
            )


        st.subheader(
            "Data Completeness"
        )


        completeness = (
            results.notna()
            .mean()
            .sort_values(
                ascending=False
            )
            .head(20)
        )


        completeness_df = pd.DataFrame(
            {
                "Column": completeness.index,
                "Completeness": completeness.values
            }
        )


        st.dataframe(
            completeness_df,
            use_container_width=True,
            hide_index=True
        )


        numeric_columns = (
            results
            .select_dtypes(
                include="number"
            )
            .columns
            .tolist()
        )


        if numeric_columns:

            st.subheader(
                "Numeric Statistics"
            )


            st.dataframe(
                results[numeric_columns].describe(),
                use_container_width=True
            )


with tab3:

    st.markdown(
        '<div class="section-title">Neuron Inspector</div>',
        unsafe_allow_html=True
    )


    if results.empty:

        st.info(
            "Search for neurons first."
        )

    elif "bodyId" not in results.columns:

        st.warning(
            "The current results do not contain Body IDs."
        )

    else:

        body_ids = (
            results["bodyId"]
            .dropna()
            .astype(int)
            .tolist()
        )


        selected_body_id = st.selectbox(
            "Select a neuron Body ID",
            body_ids
        )


        selected_rows = results[
            results["bodyId"] == selected_body_id
        ]


        if not selected_rows.empty:

            neuron = selected_rows.iloc[0]


            st.session_state.selected_neuron = (
                selected_body_id
            )


            col1, col2, col3 = st.columns(3)


            with col1:

                st.metric(
                    "Body ID",
                    str(selected_body_id)
                )


            with col2:

                neuron_type = neuron.get(
                    "type",
                    "Unknown"
                )

                st.metric(
                    "Type",
                    str(neuron_type)
                )


            with col3:

                instance = neuron.get(
                    "instance",
                    "Unknown"
                )

                st.metric(
                    "Instance",
                    str(instance)
                )


            st.subheader(
                "Neuron Metadata"
            )


            metadata = pd.DataFrame(
                {
                    "Property": neuron.index,
                    "Value": neuron.values
                }
            )


            st.dataframe(
                metadata,
                use_container_width=True,
                hide_index=True
            )


            favorite_key = int(
                selected_body_id
            )


            if favorite_key in st.session_state.favorites:

                if st.button(
                    "Remove from Favorites",
                    use_container_width=True
                ):

                    st.session_state.favorites.remove(
                        favorite_key
                    )

                    st.rerun()


            else:

                if st.button(
                    "Add to Favorites",
                    use_container_width=True
                ):

                    st.session_state.favorites.append(
                        favorite_key
                    )

                    st.rerun()


            st.link_button(
                "Open neuPrint",
                "https://neuprint.janelia.org/",
                use_container_width=True
            )


with tab4:

    st.markdown(
        '<div class="section-title">Connection Explorer</div>',
        unsafe_allow_html=True
    )


    if results.empty:

        st.info(
            "Search for neurons first."
        )

    elif "bodyId" not in results.columns:

        st.warning(
            "No Body IDs are available."
        )

    else:

        body_ids = (
            results["bodyId"]
            .dropna()
            .astype(int)
            .tolist()
        )


        connection_body_id = st.selectbox(
            "Neuron Body ID",
            body_ids,
            key="connection_body_id"
        )


        load_connections = st.button(
            "Load Connections",
            type="primary"
        )


        if load_connections:

            with st.spinner(
                "Loading neuron connections..."
            ):

                try:

                    criteria = NC(
                        bodyId=int(
                            connection_body_id
                        )
                    )


                    upstream, downstream = (
                        fetch_adjacencies(
                            criteria,
                            None,
                            client=client
                        )
                    )


                    st.session_state.upstream = (
                        upstream
                    )

                    st.session_state.downstream = (
                        downstream
                    )


                except Exception as e:

                    st.error(
                        "Could not load connections."
                    )

                    st.exception(e)


        upstream = st.session_state.upstream

        downstream = st.session_state.downstream


        col1, col2 = st.columns(2)


        with col1:

            st.subheader(
                "Upstream Neurons"
            )


            if (
                upstream is not None
                and not upstream.empty
            ):

                st.dataframe(
                    upstream,
                    use_container_width=True,
                    height=400
                )


                upstream_csv = (
                    upstream
                    .to_csv(index=False)
                    .encode("utf-8")
                )


                st.download_button(
                    "Download Upstream CSV",
                    upstream_csv,
                    "upstream_connections.csv",
                    "text/csv",
                    use_container_width=True,
                    key="download_upstream"
                )


            else:

                st.info(
                    "No upstream connection data loaded."
                )


        with col2:

            st.subheader(
                "Downstream Neurons"
            )


            if (
                downstream is not None
                and not downstream.empty
            ):

                st.dataframe(
                    downstream,
                    use_container_width=True,
                    height=400
                )


                downstream_csv = (
                    downstream
                    .to_csv(index=False)
                    .encode("utf-8")
                )


                st.download_button(
                    "Download Downstream CSV",
                    downstream_csv,
                    "downstream_connections.csv",
                    "text/csv",
                    use_container_width=True,
                    key="download_downstream"
                )


            else:

                st.info(
                    "No downstream connection data loaded."
                )


with tab5:

    st.markdown(
        '<div class="section-title">Tools and Utilities</div>',
        unsafe_allow_html=True
    )


    st.subheader(
        "neuPrint"
    )


    st.write(
        "Open the official neuPrint environment to explore "
        "the connectome using the browser interface."
    )


    st.link_button(
        "Open neuPrint",
        "https://neuprint.janelia.org/",
        use_container_width=True
    )


    st.divider()


    st.subheader(
        "Direct Body ID Lookup"
    )


    body_lookup = st.text_input(
        "Enter a Body ID",
        key="body_lookup"
    )


    if st.button(
        "Find Body ID",
        use_container_width=True
    ):

        try:

            body_id = int(
                body_lookup
            )


            lookup_criteria = NC(
                bodyId=body_id
            )


            lookup_results, _ = (
                fetch_neurons(
                    lookup_criteria,
                    client=client
                )
            )


            if lookup_results.empty:

                st.warning(
                    "No neuron was found with that Body ID."
                )

            else:

                st.success(
                    "Neuron found."
                )


                st.dataframe(
                    lookup_results,
                    use_container_width=True
                )


        except ValueError:

            st.warning(
                "Body ID must be a number."
            )


        except Exception as e:

            st.error(
                "The Body ID lookup failed."
            )

            st.exception(e)


    st.divider()


    st.subheader(
        "Search History"
    )


    if st.session_state.history:

        for item in st.session_state.history:

            st.write(
                item
            )

    else:

        st.caption(
            "No searches have been performed yet."
        )


    st.divider()


    st.subheader(
        "Favorites"
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

    else:

        st.caption(
            "No favorite neurons yet."
        )


    st.divider()


    st.subheader(
        "Dataset Information"
    )


    st.write(
        "Dataset: male-cns:v1.0"
    )

    st.write(
        "Service: Janelia neuPrint"
    )

    st.write(
        "Application: Fruit Fly Brain Connectome Explorer"
    )


st.divider()


st.caption(
    "Fruit Fly Brain Connectome Explorer | "
    "Powered by Janelia neuPrint"
)
