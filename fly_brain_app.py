import streamlit as st
import pandas as pd
import random
import time
from neuprint import Client, fetch_neurons, NeuronCriteria as NC

# 1. Configure the app layout and title
st.set_page_config(page_title="Fruit Fly Brain Explorer & Emulator", layout="wide")
st.title("🧠 Fruit Fly Brain Connectome Explorer & Emulator")
st.write("Search data from Janelia's male-cns:v1.0 dataset and test neural impulse emulations.")

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

# Create tabs to split the database view and the emulator engine
tab1, tab2 = st.tabs(["📊 Connectome Explorer", "⚡ Neural Network Emulator"])

# 3. TAB 1: Connectome Explorer
with tab1:
    if c:
        st.header("Database Search & Extraction")
        
        # UI Selection inputs
        preset_options = {
            "Custom Type (Use Text Box Below)": "",
            "Memory Center (MBON - Mushroom Body Output)": "MBON",
            "Learning Layer (KC - Kenyon Cells)": "KC",
            "Motor Pathways (DNge - Descending Neurons)": "DNge",
            "Visual Reflex Center (LC - Lobula Columnar)": "LC",
            "Clock/Sleep Neurons (ER - Ellipsoid Ring)": "ER"
        }
        
        selected_preset = st.selectbox("Choose a Brain Structure Preset:", list(preset_options.keys()))
        preset_value = preset_options[selected_preset]
        
        custom_query = st.text_input(
            "Or type custom Neuron Type/Instance manually:", 
            value=preset_value if preset_value else "DNge104"
        )
        
        limit = st.slider("Max rows to fetch", 10, 500, 100)

        if st.button("Fetch Brain Data"):
            with st.spinner("Querying the fly brain connectome..."):
                try:
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

# 4. TAB 2: Neural Network Emulator Widget
with tab2:
    st.header("⚡ Live Synaptic Pulse Emulator")
    st.write("Simulate how signals propagate across a circuit of fruit fly neurons.")

    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Simulation Parameters")
        stimulus_type = st.selectbox("Select Incoming Sensory Stimulus:", [
            "Visual Threat (Approaching Swatter)",
            "Odour Detection (Fermenting Fruit)",
            "Wind Blast (Antenna Mechanical Shift)"
        ])
        
        network_size = st.slider("Circuit Depth (Layers)", 3, 7, 4)
        noise_level = st.slider("Synaptic Backnoise / Failure Rate (%)", 0, 50, 10)
        
        run_sim = st.button("🚀 Fire Neural Impulse", type="primary")

    with col2:
        st.subheader("Circuit Execution Log")
        
        if run_sim:
            # Map paths dynamically for user flavor context
            pathways = {
                "Visual Threat (Approaching Swatter)": ["Visual-LC Cells", "Optic-Glomerulus", "Giant Fiber Interneuron", "Motor-DNge Path"],
                "Odour Detection (Fermenting Fruit)": ["Olfactory Receptor", "Antennal Lobe", "Kenyon Cells (KC)", "Mushroom Body Output (MBON)"],
                "Wind Blast (Antenna Mechanical Shift)": ["Johnston Organ", "AMMC Region", "Descending Reflex Pathways", "Flight Motor Output"]
            }
            
            nodes = pathways[stimulus_type]
            
            # Progress bar simulation setup
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Build and display interactive firing sequence
            for idx in range(network_size):
                # Calculate current layer context
                node_name = nodes[idx % len(nodes)]
                weight = random.randint(75, 120) - noise_level
                
                # Update text logs dynamically
                status_text.markdown(f"**Layer {idx+1}: Firing {node_name}...**")
                
                if weight > 50:
                    st.info(f"✨ Layer {idx+1} ({node_name}): Synaptic threshold cleared! Spike generated with weight {weight} pA.")
                else:
                    st.warning(f"❌ Layer {idx+1} ({node_name}): Signal lost! Synaptic noise blocked propagation.")
                    st.error("Simulation Halted: Signal failed to cross the cleft.")
                    break
                    
                progress_bar.progress(int(((idx + 1) / network_size) * 100))
                time.sleep(0.6) # Simulates delay time
                
            else:
                status_text.markdown("**✅ Simulation Finished! Signal reached downstream motor output.**")
                st.success("Target Action Executed: Fly behavioral motor response triggered successfully.")

