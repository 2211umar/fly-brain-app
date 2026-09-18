import streamlit as st
import pandas as pd
from neuprint import Client, fetch_neurons, NeuronCriteria as NC

# 1. Configure the app layout and title
st.set_page_config(page_title="Fruit Fly Brain Connectome Explorer", layout="wide")
st.title("🧠 Fruit Fly Brain Connectome Explorer")
st.write("Search, view clean 3D models, and download data from the Janelia male-cns:v1.0 dataset.")

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

# 3. Sidebar Control Layout
if c:
    st.sidebar.header("Search Filters")
    
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
    
    custom_query = st.sidebar.text_input(
        "Or type custom Neuron Type/Instance manually:", 
        value=preset_value if preset_value else "DNge104"
    )
    
    limit = st.sidebar.slider("Max rows to fetch", 10, 500, 100)
    fetch_triggered = st.sidebar.button("Fetch Brain Data", type="primary")

    # 4. Main Panel Split Layout (Data Table left, 3D Quick-Launch Hub right)
    col_table, col_3d = st.columns([1.1, 0.9])

    with col_table:
        st.subheader("📊 Connectome Inventory Data")
        
        if fetch_triggered or custom_query:
            with st.spinner("Querying the fly brain connectome..."):
                try:
                    type_regex = f".*{custom_query}.*" if custom_query else ".*"
                    neurons, _ = fetch_neurons(NC(type=type_regex), client=c)
                    
                    if neurons.empty:
                        neurons, _ = fetch_neurons(NC(instance=type_regex), client=c)
                    
                    if not neurons.empty:
                        df_display = neurons.head(limit)
                        st.success(f"Fetched {len(df_display)} matching neurons!")
                        st.dataframe(df_display, use_container_width=True, height=500)
                        
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

    with col_3d:
        st.subheader("🌐 3D Interactive Model Quick-Launch")
        st.write("Janelia protects its 3D environment from being embedded. Click below to launch the clean, full-screen 3D interactive viewer directly:")
        
        # Format the active search term to pass to the portal
        active_search = custom_query.strip() if custom_query else "DNge104"
        
        # Build direct-launch link matrices
        neuprint_portal = "https://janelia.org"
        clio_portal = f"https://janelia.org{active_search}"
        
        # Visual Launch Buttons
        st.info(f"💡 Current Active Target: **{active_search}**")
        
        st.link_button(
            "🚀 Open Upgraded 3D Mesh Viewer (NeuPrint v2)", 
            url=neuprint_portal, 
            use_container_width=True,
            type="primary"
        )
        
        st.link_button(
            "🧬 Open Direct Clio Connectome Workbench", 
            url=clio_portal, 
            use_container_width=True
        )
        
        st.markdown("""
        ---
        ### How to view the 3D cells instantly:
        1. Click the **Upgraded 3D Mesh Viewer** button above.
        2. In the new window, simply type your target (like **`""" + active_search + """`**) straight into their visual search bar.
        3. The system will cleanly generate the true, colorful anatomical wireframes without loading those clunky black-and-white tissue slices!
        """)
