import streamlit as st
import pandas as pd
import plotly.express as px
from github import Github
import io
from datetime import datetime
import pytz

# --- 1. Page Configuration ---
st.set_page_config(page_title="Sajid Medical Store", page_icon="💊", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #ccc; color: black; }
    .target-card { 
        background-color: #e8f5e9; 
        padding: 25px; 
        border-radius: 15px; 
        text-align: center; 
        border: 2px solid #2e7d32; 
        margin-bottom: 20px; 
        color: black;
    }
    .expense-card { 
        background-color: #ffebee; 
        padding: 25px; 
        border-radius: 15px; 
        text-align: center; 
        border: 2px solid #c62828; 
        margin-bottom: 20px; 
        color: black;
    }
    .stock-alert {
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #ffecb5;
        color: #856404;
        text-align: center;
        font-weight: bold;
    }
    h1, h2, h3 { color: #2e7d32 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GitHub Auth ---
try:
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["REPO_NAME"]
    g = Github(token)
    repo = g.get_repo(repo_name)
except Exception as e:
    st.error(f"Secrets Missing! Settings check karein. Error: {e}")
    st.stop()

# --- 3. Functions ---
CSV_FILE = "medical_data.csv"
STOCK_FILE = "stock_data.csv" # New file for stock

COLS = ['Date', 'Category', 'Item', 'Cost', 'Sale', 'Profit', 'Payment']
STOCK_COLS = ['Medicine Name', 'Type', 'Quantity', 'Status'] # Status = Available or Order Now

def load_data(file_name, columns):
    try:
        contents = repo.get_contents(file_name)
        raw_df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
        # Ensure columns match
        if set(columns).issubset(raw_df.columns):
            raw_df = raw_df[columns]
        else:
            raw_df = pd.DataFrame(columns=columns)
            
        if 'Date' in raw_df.columns:
            raw_df['Date'] = pd.to_datetime(raw_df['Date'], errors='coerce')
            raw_df = raw_df.dropna(subset=['Date'])
        return raw_df
    except Exception:
        return pd.DataFrame(columns=columns)

def save_data(df, file_name, message="Update"):
    csv_buffer = io.StringIO()
    save_df = df.copy()
    if 'Date' in save_df.columns:
        save_df['Date'] = pd.to_datetime(save_df['Date']).dt.strftime('%Y-%m-%d')
    
    save_df.to_csv(csv_buffer, index=False)
    try:
        contents = repo.get_contents(file_name)
        repo.update_file(file_name, message, csv_buffer.getvalue(), contents.sha)
        return True
    except Exception:
        try:
            repo.create_file(file_name, "Initial Create", csv_buffer.getvalue())
            return True
        except: return False

# --- 4. Logic ---
pk_tz = pytz.timezone('Asia/Karachi')
now = datetime.now(pk_tz)

df = load_data(CSV_FILE, COLS)
stock_df = load_data(STOCK_FILE, STOCK_COLS)

# Header
st.markdown("<h1 style='text-align: center;'>🏥 Sajid Medical Store</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center;'><b>Date:</b> {now.strftime('%d %B, %Y')}</p>", unsafe_allow_html=True)
st.markdown("---")

menu = st.sidebar.radio("Main Menu", ["📝 Daily Sale Entry", "💊 Stock / Order List", "📊 Dashboard", "📂 Archive", "⚙️ Manage Sales"])

# --- SECTION 1: ENTRY ---
if menu == "📝 Daily Sale Entry":
    st.header("📝 Nayi Sale/Kharcha Entry")
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date_input = st.date_input("Tareekh", now.date())
            cat = st.selectbox("Category", ["Medicine (Tabs/Syrup)", "Injections/Drips", "General Items (Pampers etc)", "Ghar ka Kharcha", "Shop Expense (Bil/Rent)"])
            item = st.text_input("Item Name / Detail")
        with c2:
            cost = st.number_input("Cost (Khareed)", 0.0)
            sale = st.number_input("Sale (Becha)", 0.0)
            pay = st.selectbox("Payment Type", ["Cash", "EasyPaisa", "Udhaar"])
        
        if st.form_submit_button("💾 Save Entry"):
            if item:
                # Ghar ke kharche ya Shop expense pe profit nahi hota
                if "Kharcha" in cat or "Expense" in cat:
                    profit = 0
                else:
                    profit = sale - cost
                
                new_row = pd.DataFrame([[pd.to_datetime(date_input), cat, item, cost, sale, profit, pay]], columns=COLS)
                df = pd.concat([df, new_row], ignore_index=True)
                if save_data(df, CSV_FILE, f"Added: {item}"):
                    st.success(f"✅ {item} Saved!")
                    st.rerun()

# --- SECTION 2: STOCK MANAGEMENT (NEW) ---
elif menu == "💊 Stock / Order List":
    st.header("💊 Medicine Stock & Order List")
    
    # Tabs layout
    tab1, tab2 = st.tabs(["➕ Add/Update Stock", "📋 View Lists"])
    
    with tab1:
        st.subheader("Update Medicine Stock")
        with st.form("stock_form", clear_on_submit=True):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                med_name = st.text_input("Medicine Name (e.g., Panadol)")
                med_type = st.selectbox("Type", ["Tablet", "Syrup", "Injection", "Cream/Ointment", "Other"])
            with col_s2:
                qty = st.text_input("Quantity Remaining (e.g. 5 boxes, 10 strips)")
                status = st.radio("Mangwani hai?", ["No (Stock OK)", "Yes (Order Now)"], horizontal=True)
            
            if st.form_submit_button("Update Stock"):
                if med_name:
                    clean_status = "Order Now" if "Yes" in status else "OK"
                    
                    # Check if medicine exists, update it, else add new
                    if not stock_df.empty and med_name in stock_df['Medicine Name'].values:
                        idx = stock_df[stock_df['Medicine Name'] == med_name].index[0]
                        stock_df.at[idx, 'Quantity'] = qty
                        stock_df.at[idx, 'Status'] = clean_status
                        stock_df.at[idx, 'Type'] = med_type
                        msg = "Updated"
                    else:
                        new_stock = pd.DataFrame([[med_name, med_type, qty, clean_status]], columns=STOCK_COLS)
                        stock_df = pd.concat([stock_df, new_stock], ignore_index=True)
                        msg = "Added"
                    
                    if save_data(stock_df, STOCK_FILE, f"Stock {msg}: {med_name}"):
                        st.success(f"{med_name} list mein update ho gayi!")
                        st.rerun()

    with tab2:
        # Filter for Order List
        order_list = stock_df[stock_df['Status'] == 'Order Now']
        
        st.markdown("### ⚠️ Order List (Jo Cheezein Mangwani Hain)")
        if not order_list.empty:
            st.markdown("""<div class="stock-alert">Niche di gayi medicines khatam hain, distributor se mangwa lein!</div>""", unsafe_allow_html=True)
            st.table(order_list[['Medicine Name', 'Type', 'Quantity']])
        else:
            st.info("Filhal koi cheez order nahi karni.")
            
        st.markdown("---")
        st.markdown("### ✅ Full Stock List")
        st.dataframe(stock_df, use_container_width=True)
        
        # Delete Button for Stock
        st.markdown("#### Delete Medicine")
        del_name = st.selectbox("Select to Delete", stock_df['Medicine Name'].unique())
        if st.button("❌ Remove from List"):
            stock_df = stock_df[stock_df['Medicine Name'] != del_name]
            save_data(stock_df, STOCK_FILE, f"Deleted Stock: {del_name}")
            st.rerun()

# --- SECTION 3: DASHBOARD ---
elif menu == "📊 Dashboard":
    st.header(f"📊 Report: {now.strftime('%B %Y')}")
    if not df.empty:
        df_month = df[(df['Date'].dt.month == now.month) & (df['Date'].dt.year == now.year)]
        df_today = df[df['Date'].dt.date == now.date()]

        # Filter Sales vs Expense
        sales_data = df_month[~df_month['Category'].str.contains("Kharcha|Expense")]
        expense_data = df_month[df_month['Category'].str.contains("Kharcha|Expense")]

        m_profit = sales_data['Profit'].sum()
        m_expense = expense_data['Cost'].sum()
        net_savings = m_profit - m_expense

        target = 100000 # Example Target for Medical Store
        
        row_cards = st.columns(2)
        with row_cards[0]:
            st.markdown(f"""
                <div class="target-card">
                    <h3>💰 Monthly Profit (Bachat)</h3>
                    <h1>Rs. {m_profit:,.0f}</h1>
                    <p>Target: Rs. {target:,.0f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with row_cards[1]:
            st.markdown(f"""
                <div class="expense-card">
                    <h3>🏠 Shop/Home Expense</h3>
                    <h1>Rs. {m_expense:,.0f}</h1>
                    <p style="font-weight:bold; color:black;">Net Savings: Rs. {net_savings:,.0f}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Month Sale", f"Rs. {sales_data['Sale'].sum():,.0f}")
        col2.metric("Aaj ki Sale", f"Rs. {df_today[~df_today['Category'].str.contains('Kharcha')]['Sale'].sum():,.0f}")
        col3.metric("Aaj ka Profit", f"Rs. {df_today[~df_today['Category'].str.contains('Kharcha')]['Profit'].sum():,.0f}")

        st.markdown("### 📋 Aaj Ki Tafseel")
        if not df_today.empty:
            st.dataframe(df_today[['Item', 'Category', 'Sale', 'Profit', 'Payment']], use_container_width=True)
        else:
            st.info("Aaj koi entry nahi hui.")

# --- SECTION 4: ARCHIVE ---
elif menu == "📂 Archive":
    st.header("📂 Purana Monthly Record")
    if not df.empty:
        df['Month_Year'] = df['Date'].dt.strftime('%B %Y')
        
        summary = df.groupby('Month_Year').apply(lambda x: pd.Series({
            'Total Sale': x[~x['Category'].str.contains("Kharcha")]['Sale'].sum(),
            'Total Profit': x[~x['Category'].str.contains("Kharcha")]['Profit'].sum(),
            'Total Expense': x[x['Category'].str.contains("Kharcha")]['Cost'].sum(),
        })).reset_index().sort_values(by='Month_Year', ascending=False)
        
        summary['Net Saving'] = summary['Total Profit'] - summary['Total Expense']
        
        st.dataframe(summary.style.format("Rs. {:,.0f}", subset=['Total Sale', 'Total Profit', 'Total Expense', 'Net Saving']), use_container_width=True)
        
        st.markdown("---")
        sel_m = st.selectbox("Mahina Select Karein:", summary['Month_Year'].unique())
        detail_df = df[df['Month_Year'] == sel_m].sort_values(by='Date', ascending=False)
        st.dataframe(detail_df[COLS], use_container_width=True)

# --- SECTION 5: MANAGE ---
elif menu == "⚙️ Manage Sales":
    st.header("⚙️ Edit or Delete Entries")
    if not df.empty:
        # Show recent entries
        st.write("Last 10 Entries:")
        st.dataframe(df.tail(10).iloc[::-1][COLS], use_container_width=True)
        
        st.markdown("---")
        action_idx = st.number_input("Enter Index Number to Delete/Edit (See row number on left):", 0, len(df)-1, value=len(df)-1)
        
        c1, c2 = st.columns(2)
        if c1.button("🗑️ Delete Permanently"):
            df = df.drop(df.index[action_idx])
            save_data(df, CSV_FILE, "Deleted Entry")
            st.warning("Deleted!")
            st.rerun()
            
        if c2.button("✏️ Edit This"):
            st.session_state.edit_idx = action_idx
            st.session_state.edit_mode = True

        if st.session_state.get("edit_mode", False):
            idx = st.session_state.edit_idx
            row = df.iloc[idx]
            with st.form("edit_form"):
                st.write(f"Editing: {row['Item']}")
                n_sale = st.number_input("New Sale", value=float(row['Sale']))
                n_cost = st.number_input("New Cost", value=float(row['Cost']))
                if st.form_submit_button("Update"):
                    df.at[idx, 'Sale'] = n_sale
                    df.at[idx, 'Cost'] = n_cost
                    if "Kharcha" not in row['Category']:
                        df.at[idx, 'Profit'] = n_sale - n_cost
                    save_data(df, CSV_FILE, "Edited Entry")
                    st.session_state.edit_mode = False
                    st.success("Updated!")
                    st.rerun()
