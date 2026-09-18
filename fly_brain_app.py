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
        token = st.secrets.get("NEUPRINT_TOKEN", "cb5ffc15e9e26d2f021c51ed4ae0a37c734e3aad08164411e0f2f9e97eccb5b5")
        return Client('neuprint.janelia.org', dataset='male-cns:v1.0', token=token)
    except Exception as e:
        st.error(f"Failed to connect to neuPrint. Verify your API token configuration. Error: {e}")
        return None

c = get_neuprint_client()

# 3. User Interface Components
if c:
    st.sidebar.header("Search Filters")
    
    # Pre-configured dropdown list of famous fruit fly brain structures
    preset_options = {
        "Custom Type (Use Text Box Below)": "",
        "Memory Center (MBON - Mushroom Body Output)": "MBON",
        "Learning Layer (KC - Kenyon Cells)": "KC",
        "Motor Pathways (DNge - Descending Neurons)": "DNge",
        "Visual Reflex Center (LC - Lobula Columnar)": "LC",
        "Clock/Sleep Neurons (ER - Ellipsoid Ring)": "ER"
    }
    
    selected_preset = st.sidebar.selectbox("Choose a Brain Structure Preset:", list(preset_options.keys()))
    preset_value = preset_options[selected_preset]
    
    # Text input box for custom queries
    custom_query = st.sidebar.text_input(
        "Or type custom Neuron Type/Instance manually:", 
        value=preset_value if preset_value else "DNge104"
    )
    
    limit = st.sidebar.slider("Max rows to fetch", 10, 500, 100)

    if st.sidebar.button("Fetch Brain Data"):
        with st.spinner("Querying the fly brain connectome..."):
            try:
                # Use the manual text box input for the actual database query
                type_regex = f".*{custom_query}.*" if custom_query else ".*"
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
                    st.warning(f"No neurons matched '{custom_query}'.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
