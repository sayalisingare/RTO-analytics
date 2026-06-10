import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page layout to wide
st.set_page_config(page_title="Advanced RTO Analytics", page_icon="🛒", layout="wide")

# Custom CSS for dark theme look and aesthetics
st.markdown("""
    <style>
        .reportview-container {
            background: #1e1e1e;
        }
        .metric-card {
            background-color: #2b2b2b;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
            text-align: center;
            color: white;
            margin-bottom: 20px;
        }
        .metric-title {
            font-size: 1.1rem;
            color: #b0b0b0;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #4CAF50;
            white-space: nowrap;
        }
        .metric-value.loss {
            color: #ff4b4b;
        }
        .metric-value.warn {
            color: #ffce56;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv("raw_ecommerce_data.csv")
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['month_year'] = df['order_date'].dt.to_period('M').astype(str)
    df['total_shipping_cost'] = df['forward_shipping_cost'] + df['return_shipping_cost']
    return df

st.title("🛒 Executive Dashboard: RTO & Financial Impact")
st.markdown("Deep dive into business losses, logistics failures, and high-risk customer behavior.")

# Load Data
try:
    with st.spinner("Loading Data..."):
        df = load_data()
except Exception as e:
    st.error("Failed to load raw_ecommerce_data.csv.")
    st.stop()

# ================= SIDEBAR FILTERS =================
st.sidebar.header("🔍 Filters")

min_date = df['order_date'].min().date()
max_date = df['order_date'].max().date()
date_range = st.sidebar.date_input("Select Order Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

tiers = df['city_tier'].unique().tolist()
selected_tiers = st.sidebar.multiselect("Select City Tier", tiers, default=tiers)

payment = df['payment_type'].unique().tolist()
selected_payment = st.sidebar.multiselect("Select Payment Type", payment, default=payment)

# Apply Filters
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = df[(df['order_date'].dt.date >= start_date) & (df['order_date'].dt.date <= end_date)]
else:
    filtered_df = df

if selected_tiers:
    filtered_df = filtered_df[filtered_df['city_tier'].isin(selected_tiers)]
if selected_payment:
    filtered_df = filtered_df[filtered_df['payment_type'].isin(selected_payment)]

# Helper to format large numbers
def format_currency(num):
    if num >= 10000000:
        return f"₹{num/10000000:.2f} Cr"
    elif num >= 100000:
        return f"₹{num/100000:.2f} L"
    elif num >= 1000:
        return f"₹{num/1000:.1f} K"
    else:
        return f"₹{num:,.0f}"

def format_number(num):
    if num >= 10000000:
        return f"{num/10000000:.2f} Cr"
    elif num >= 100000:
        return f"{num/100000:.2f} L"
    elif num >= 1000:
        return f"{num/1000:.1f} K"
    else:
        return f"{num:,}"

# ================= FINANCIAL KPIs =================
st.markdown("### 💰 Financial Impact Overview")
col1, col2, col3, col4, col5 = st.columns(5)

total_orders = len(filtered_df)
total_revenue = filtered_df['order_value'].sum()
rto_df = filtered_df[filtered_df['order_status'] == 'RTO']
total_rtos = len(rto_df)
rto_rate = (total_rtos / total_orders * 100) if total_orders > 0 else 0

# Financial Losses
revenue_at_risk = rto_df['order_value'].sum()
shipping_loss = rto_df['total_shipping_cost'].sum()

with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Total Orders</div><div class="metric-value">{format_number(total_orders)}</div></div>', unsafe_allow_html=True)

with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Gross Revenue</div><div class="metric-value">{format_currency(total_revenue)}</div></div>', unsafe_allow_html=True)

with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-title">RTO Rate</div><div class="metric-value warn">{rto_rate:.1f}%</div></div>', unsafe_allow_html=True)

with col4:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Shipping ₹ Lost</div><div class="metric-value loss">{format_currency(shipping_loss)}</div></div>', unsafe_allow_html=True)

with col5:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Revenue Cancelled</div><div class="metric-value loss">{format_currency(revenue_at_risk)}</div></div>', unsafe_allow_html=True)


st.markdown("---")
# ================= ROW 1: TRENDS =================
st.markdown("### 📈 Monthly Trend Analysis")

monthly_trend = filtered_df.groupby('month_year').agg(
    Total_Orders=('order_id', 'count'),
    RTO_Orders=('order_status', lambda x: (x == 'RTO').sum())
).reset_index()
monthly_trend['RTO Rate (%)'] = (monthly_trend['RTO_Orders'] / monthly_trend['Total_Orders']) * 100

fig_trend = go.Figure()
fig_trend.add_trace(go.Bar(x=monthly_trend['month_year'], y=monthly_trend['Total_Orders'], name='Total Orders', marker_color='#4CAF50'))
fig_trend.add_trace(go.Bar(x=monthly_trend['month_year'], y=monthly_trend['RTO_Orders'], name='RTO Orders', marker_color='#ff4b4b'))
fig_trend.add_trace(go.Scatter(x=monthly_trend['month_year'], y=monthly_trend['RTO Rate (%)'], name='RTO Rate (%)', yaxis='y2', line=dict(color='#ffce56', width=3)))

fig_trend.update_layout(
    template="plotly_dark",
    yaxis=dict(title='Order Volume'),
    yaxis2=dict(title='RTO Rate (%)', overlaying='y', side='right', range=[0, 100]),
    barmode='group',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("---")
# ================= ROW 2: PAYMENT & TIER =================
col_pay, col_tier = st.columns(2)

with col_pay:
    st.markdown("#### 💳 Payment Method Risk")
    pay_stats = filtered_df.groupby('payment_type').apply(
        lambda x: pd.Series({'RTO Rate (%)': (len(x[x['order_status'] == 'RTO']) / len(x)) * 100 if len(x) > 0 else 0})
    ).reset_index()
    fig_pay = px.bar(pay_stats, x='payment_type', y='RTO Rate (%)', color='payment_type', 
                     color_discrete_map={"COD": "#ff4b4b", "Prepaid": "#4CAF50"}, template="plotly_dark")
    st.plotly_chart(fig_pay, use_container_width=True)

with col_tier:
    st.markdown("#### 🏙️ City Tier RTO Breakdown")
    tier_stats = filtered_df.groupby('city_tier').apply(
        lambda x: pd.Series({'RTO Rate (%)': (len(x[x['order_status'] == 'RTO']) / len(x)) * 100 if len(x) > 0 else 0})
    ).reset_index().sort_values('RTO Rate (%)', ascending=True)
    fig_tier = px.bar(tier_stats, x='RTO Rate (%)', y='city_tier', orientation='h', color='RTO Rate (%)',
                      color_continuous_scale='Reds', template="plotly_dark")
    st.plotly_chart(fig_tier, use_container_width=True)

st.markdown("---")
# ================= ROW 3: COURIER & CUSTOMERS =================
col_courier, col_cust = st.columns(2)

with col_courier:
    st.markdown("#### 🚚 Courier Performance Scorecard")
    st.markdown("Highlighting SLA Breaches (>2 days delayed) and RTO performance.")
    courier_stats = filtered_df.groupby('courier_partner').agg(
        Total_Orders=('order_id', 'count'),
        SLA_Breaches=('delivery_delay_days', lambda x: (x > 2).sum()),
        Shipping_Loss=('total_shipping_cost', lambda x: x[filtered_df['order_status'] == 'RTO'].sum())
    ).reset_index()
    courier_stats['SLA Breach Rate (%)'] = (courier_stats['SLA_Breaches'] / courier_stats['Total_Orders']) * 100
    courier_stats = courier_stats.sort_values('SLA Breach Rate (%)', ascending=False)
    
    fig_courier = px.bar(courier_stats, x='courier_partner', y='SLA Breach Rate (%)', 
                         hover_data=['Shipping_Loss'],
                         color='SLA Breach Rate (%)', color_continuous_scale='Oranges', template="plotly_dark")
    st.plotly_chart(fig_courier, use_container_width=True)

with col_cust:
    st.markdown("#### 🚨 Top Abusive Customers (Financial Loss)")
    st.markdown("Customers costing the business the most money in wasted shipping.")
    
    cust_stats = rto_df.groupby(['customer_id', 'city']).agg(
        RTO_Count=('order_id', 'count'),
        Money_Lost_INR=('total_shipping_cost', 'sum')
    ).reset_index().sort_values(by='Money_Lost_INR', ascending=False)
    
    # Format currency for display
    display_df = cust_stats.head(10).copy()
    display_df['Money_Lost_INR'] = display_df['Money_Lost_INR'].apply(lambda x: f"₹{x:,.0f}")
    
    st.dataframe(display_df, use_container_width=True)
