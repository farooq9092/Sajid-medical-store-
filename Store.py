import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="Synergy MSMS", page_icon="🏥", layout="wide")

# --- Custom Styling ---
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
    }
    .expired { color: #dc3545; font-weight: bold; }
    .warning { color: #ffc107; font-weight: bold; }
    .good { color: #28a745; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- Data Initialization (Simulating a Database) ---
if 'inventory' not in st.session_state:
    # seeding with some mock data based on the article's context
    data = {
        'ID': [101, 102, 103, 104, 105],
        'Medicine Name': ['Amoxicillin 500mg', 'Paracetamol', 'Insulin Glargine', 'Vitamin C', 'Ibuprofen'],
        'Category': ['Antibiotic', 'Pain Relief', 'Diabetes', 'Supplement', 'Pain Relief'],
        'Stock': [50, 120, 4, 200, 15],
        'Min_Stock_Level': [20, 50, 10, 30, 20],  # Threshold for auto-reorder
        'Price': [15.00, 5.00, 1200.00, 10.00, 8.00],
        'Expiry_Date': [
            (datetime.now() + timedelta(days=365)).date(), # Good
            (datetime.now() + timedelta(days=600)).date(), # Good
            (datetime.now() + timedelta(days=10)).date(),  # Expiring Soon
            (datetime.now() + timedelta(days=400)).date(), # Good
            (datetime.now() - timedelta(days=5)).date()    # Expired
        ]
    }
    st.session_state.inventory = pd.DataFrame(data)

# Helper function to get dataframe
def get_data():
    return st.session_state.inventory

# --- Sidebar Navigation ---
st.sidebar.title("🏥 Synergy MSMS")
st.sidebar.info("Medical Store Management System")
menu = st.sidebar.radio("Navigation", ["📊 Dashboard", "💊 Inventory & Stock", "⚡ Alerts & Reordering", "🛒 Point of Sale"])

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("🏥 Administrator Dashboard")
    st.markdown("Overview of operational efficiency and inventory health.")
    
    df = get_data()
    
    # Logic for Metrics
    total_products = len(df)
    total_stock_value = (df['Stock'] * df['Price']).sum()
    
    # Low Stock Logic
    low_stock_count = df[df['Stock'] <= df['Min_Stock_Level']].shape[0]
    
    # Expiry Logic
    today = datetime.now().date()
    df['Expiry_Date'] = pd.to_datetime(df['Expiry_Date']).dt.date
    expired_count = df[df['Expiry_Date'] < today].shape[0]
    expiring_soon_count = df[(df['Expiry_Date'] >= today) & (df['Expiry_Date'] <= today + timedelta(days=30))].shape[0]

    # 
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Medicines", total_products)
    col2.metric("Inventory Value", f"${total_stock_value:,.2f}")
    col3.metric("⚠️ Low Stock Alerts", low_stock_count, delta_color="inverse")
    col4.metric("📅 Expiring Soon/Expired", expired_count + expiring_soon_count, delta_color="inverse")

    st.divider()
    
    # Visual Charts
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Stock Levels by Medicine")
        st.bar_chart(df.set_index("Medicine Name")['Stock'])
    
    with c2:
        st.subheader("Category Distribution")
        cat_counts = df['Category'].value_counts()
        st.bar_chart(cat_counts)

# --- 2. INVENTORY & STOCK ---
elif menu == "💊 Inventory & Stock":
    st.title("📦 Inventory Management")
    st.markdown("Centralized data storage for medication details.")

    df = get_data()
    
    # Tab layout
    tab1, tab2 = st.tabs(["View Inventory", "Add New Medicine"])
    
    with tab1:
        st.dataframe(df.style.format({"Price": "${:.2f}"}), use_container_width=True)
    
    with tab2:
        with st.form("add_med_form"):
            c1, c2 = st.columns(2)
            new_name = c1.text_input("Medicine Name")
            new_cat = c2.selectbox("Category", ["Antibiotic", "Pain Relief", "Diabetes", "Supplement", "Cardio", "Other"])
            
            c3, c4 = st.columns(2)
            new_stock = c3.number_input("Initial Stock", min_value=1)
            new_min = c4.number_input("Min Stock Level (Reorder Point)", min_value=1)
            
            c5, c6 = st.columns(2)
            new_price = c5.number_input("Price per Unit", min_value=0.1)
            new_expiry = c6.date_input("Expiry Date")
            
            submitted = st.form_submit_button("Add to Inventory")
            
            if submitted:
                new_id = df['ID'].max() + 1
                new_row = {
                    'ID': new_id, 'Medicine Name': new_name, 'Category': new_cat,
                    'Stock': new_stock, 'Min_Stock_Level': new_min,
                    'Price': new_price, 'Expiry_Date': new_expiry
                }
                st.session_state.inventory = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"{new_name} added successfully!")
                st.rerun()

# --- 3. ALERTS & REORDERING (The "Automation" Part) ---
elif menu == "⚡ Alerts & Reordering":
    st.title("⚡ Automation Center")
    st.markdown("Automated alerts for low stock and expiration to reduce wastage.")

    # 

    df = get_data()
    today = datetime.now().date()
    df['Expiry_Date'] = pd.to_datetime(df['Expiry_Date']).dt.date

    # --- Section A: Low Stock (Automated Reordering) ---
    st.subheader("🔴 Low Stock Alerts (Reordering Needed)")
    low_stock_df = df[df['Stock'] <= df['Min_Stock_Level']]
    
    if not low_stock_df.empty:
        st.error(f"{len(low_stock_df)} items are below safety levels.")
        st.dataframe(low_stock_df[['Medicine Name', 'Stock', 'Min_Stock_Level', 'Category']])
        
        if st.button("Generate Reorder Request for Suppliers"):
            # Simulation of the "Automated stock reordering" mentioned in article
            st.toast("✅ Purchase Orders sent to suppliers via Email/EDI!")
    else:
        st.success("All stock levels are healthy.")

    st.divider()

    # --- Section B: Expiry Monitoring ---
    st.subheader("📅 Expiry Monitor")
    
    # Filter 1: Already Expired
    expired_df = df[df['Expiry_Date'] < today]
    if not expired_df.empty:
        st.error("🚨 The following items have EXPIRED. Please remove from shelf.")
        st.table(expired_df[['Medicine Name', 'Expiry_Date', 'Stock']])
    
    # Filter 2: Expiring Soon (30 Days)
    soon_df = df[(df['Expiry_Date'] >= today) & (df['Expiry_Date'] <= today + timedelta(days=30))]
    if not soon_df.empty:
        st.warning("⚠️ The following items expire within 30 days. Consider discounting.")
        st.table(soon_df[['Medicine Name', 'Expiry_Date', 'Stock']])

# --- 4. POINT OF SALE ---
elif menu == "🛒 Point of Sale":
    st.title("🛒 Dispensing & Billing")
    st.markdown("Process prescriptions and update inventory automatically.")
    
    df = get_data()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Select Medicine
        med_list = df['Medicine Name'].tolist()
        selected_med_name = st.selectbox("Select Medicine", med_list)
        
        # Get details of selected med
        med_row = df[df['Medicine Name'] == selected_med_name].iloc[0]
        current_stock = med_row['Stock']
        price = med_row['Price']
        
        st.info(f"Available Stock: {current_stock} units | Price: ${price}")
        
        qty = st.number_input("Quantity", min_value=1, max_value=int(current_stock))
        
        total_bill = qty * price
        st.metric("Total Bill", f"${total_bill:,.2f}")
        
        if st.button("Confirm Sale"):
            # Update Stock Logic
            idx = df[df['Medicine Name'] == selected_med_name].index[0]
            st.session_state.inventory.at[idx, 'Stock'] = current_stock - qty
            st.success("Sale Recorded! Inventory Updated.")
            st.rerun()

