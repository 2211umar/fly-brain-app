import streamlit as st
import pandas as pd
from neuprint import Client, fetch_neurons, NeuronCriteria as NC

# 1. Configure the app layout and title
st.set_page_config(page_title="Fruit Fly Brain Explorer", layout="wide")
st.title("🧠 Fruit Fly Brain Connectome Explorer")
st.write("Search and download data from the Janelia male-cns:v1.0 dataset.")

# 2. Securely connect to the database using Cloud Secrets
@st.cache_resource
def get_neuprint_client():
    try:
        # If running locally, fall back to your hardcoded token; if on the cloud, use hidden secrets
        token = st.secrets.get("NEUPRINT_TOKEN", "cb5ffc15e9e26d2f021c51ed4ae0a37c734e3aad08164411e0f2f9e97eccb5b5")
        return Client('neuprint.janelia.org', dataset='male-cns:v1.0', token=token)
    except Exception as e:
        st.error(f"Failed to connect to neuPrint. Verify your API token configuration. Error: {e}")
        return None

c = get_neuprint_client()

# 3. User Interface Components
if c:
    st.sidebar.header("Search Filters")
    neuron_type_query = st.sidebar.text_input("Filter by Type or Instance (e.g., DNge104, MBON)", "DNge104")
    limit = st.sidebar.slider("Max rows to fetch", 10, 500, 100)

    if st.sidebar.button("Fetch Brain Data"):
        with st.spinner("Querying the fly brain connectome..."):
            try:
                type_regex = f".*{neuron_type_query}.*" if neuron_type_query else ".*"
                neurons, _ = fetch_neurons(NC(type=type_regex), client=c)
                
                if neurons.empty:
                    neurons, _ = fetch_neurons(NC(instance=type_regex), client=c)
                
                if not neurons.empty:
                    df_display = neurons.head(limit)
                    st.success(f"Successfully fetched {len(df_display)} matching neurons!")
                    st.dataframe(df_display, use_container_width=True)
                    
                    csv = df_display.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download current view as CSV",
                        data=csv,
                        file_name="fly_brain_data.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning(f"No neurons matched '{neuron_type_query}'.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
