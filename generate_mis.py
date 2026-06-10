import pandas as pd
import duckdb
from datetime import datetime

def generate_v2_mis(file_path="raw_ecommerce_data.csv", rto_threshold_pct=40.0):
    print(f"Generating Advanced MIS Report from {file_path}...")
    
    df = pd.read_csv(file_path)
    con = duckdb.connect(database=':memory:')
    con.register('orders', df)
    
    # 1. Executive Summary
    summary_query = """
    SELECT 
        COUNT(*) as Total_Orders,
        SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) as Total_RTO_Orders,
        ROUND(AVG(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100, 2) as Overall_RTO_Pct,
        SUM(CASE WHEN order_status = 'RTO' THEN forward_shipping_cost + return_shipping_cost ELSE 0 END) as Total_RTO_Loss_INR,
        ROUND(AVG(CASE WHEN delivery_delay_days > 2 THEN 1 ELSE 0 END) * 100, 2) as Pct_Orders_Delayed_Late
    FROM orders
    """
    exec_summary_t = con.execute(summary_query).fetchdf().T.reset_index()
    exec_summary_t.columns = ['Metric', 'Value']
    
    # 2. Flagged Pincodes
    pincodes_query = f"""
    SELECT customer_pincode, city, state,
           COUNT(*) as Total_Orders,
           ROUND(AVG(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100, 2) as RTO_Rate_Pct,
           SUM(forward_shipping_cost + return_shipping_cost) as Estimated_Loss_INR
    FROM orders
    GROUP BY customer_pincode, city, state
    HAVING COUNT(*) >= 50 AND RTO_Rate_Pct > {rto_threshold_pct}
    ORDER BY Estimated_Loss_INR DESC
    """
    flagged_pincodes = con.execute(pincodes_query).fetchdf()
    
    # 3. Courier SLA Breaches
    courier_sla = """
    SELECT courier_partner,
           COUNT(*) as Total_Orders,
           ROUND(AVG(CASE WHEN delivery_delay_days > 2 THEN 1 ELSE 0 END) * 100, 2) as SLA_Breach_Pct,
           ROUND(AVG(ndr_count), 2) as Avg_NDR_Attempts,
           ROUND(AVG(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100, 2) as RTO_Rate_Pct
    FROM orders
    GROUP BY courier_partner
    ORDER BY SLA_Breach_Pct DESC
    """
    courier_metrics = con.execute(courier_sla).fetchdf()
    
    # 4. High-Risk Customers (Abusive Returners)
    high_risk_customers = """
    SELECT customer_id,
           COUNT(*) as Lifetime_Orders,
           SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) as Lifetime_RTOs,
           ROUND(AVG(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100, 2) as RTO_Rate_Pct,
           SUM(forward_shipping_cost + return_shipping_cost) as Loss_Caused_INR
    FROM orders
    GROUP BY customer_id
    HAVING COUNT(*) >= 5 AND RTO_Rate_Pct >= 50
    ORDER BY Loss_Caused_INR DESC
    LIMIT 1000
    """
    abusive_customers = con.execute(high_risk_customers).fetchdf()

    # Write to Excel
    report_name = f"V2_Weekly_RTO_MIS_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(report_name, engine='openpyxl') as writer:
        exec_summary_t.to_excel(writer, sheet_name='Executive Summary', index=False)
        courier_metrics.to_excel(writer, sheet_name='Courier SLA Tracking', index=False)
        flagged_pincodes.to_excel(writer, sheet_name='Flagged Pincodes', index=False)
        abusive_customers.to_excel(writer, sheet_name='High Risk Customers', index=False)
        
    print(f"Advanced MIS Report successfully generated: {report_name}")

if __name__ == "__main__":
    generate_v2_mis(rto_threshold_pct=50.0)
