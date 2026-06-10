import duckdb
import pandas as pd

def run_v2_sql_analysis():
    print("Running Advanced SQL Analysis on V2 Dataset...\n")
    con = duckdb.connect(database=':memory:')
    con.execute("CREATE VIEW orders AS SELECT * FROM read_csv_auto('raw_ecommerce_data.csv')")
    
    # 1. Impact of Delivery Delays on RTO
    query_sla = """
    SELECT 
        CASE 
            WHEN delivery_delay_days <= 0 THEN 'Early/On Time'
            WHEN delivery_delay_days BETWEEN 1 AND 2 THEN '1-2 Days Late'
            WHEN delivery_delay_days BETWEEN 3 AND 4 THEN '3-4 Days Late'
            ELSE '5+ Days Late'
        END as delivery_performance,
        COUNT(*) as total_orders,
        ROUND(AVG(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100, 2) as rto_rate_pct
    FROM orders
    GROUP BY delivery_performance
    ORDER BY rto_rate_pct DESC;
    """
    print("--- 1. Logistics: Impact of Delivery Delays on RTO ---")
    print(con.execute(query_sla).fetchdf())
    print("\n")
    
    # 2. Impact of Impulse Buying (Discounts)
    query_discount = """
    SELECT 
        CASE 
            WHEN discount_percentage < 10 THEN '0-10% (Low)'
            WHEN discount_percentage BETWEEN 10 AND 30 THEN '10-30% (Medium)'
            WHEN discount_percentage BETWEEN 31 AND 50 THEN '31-50% (High)'
            ELSE '50%+ (Clearance)'
        END as discount_tier,
        COUNT(*) as total_orders,
        ROUND(AVG(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100, 2) as rto_rate_pct
    FROM orders
    GROUP BY discount_tier
    ORDER BY rto_rate_pct DESC;
    """
    print("--- 2. Customer Behavior: Discount Depth vs RTO Rate ---")
    print(con.execute(query_discount).fetchdf())
    print("\n")
    
    # 3. NDR Problem by Courier
    query_ndr = """
    SELECT courier_partner,
           ROUND(AVG(ndr_count), 2) as avg_ndr_attempts,
           COUNT(*) as total_orders,
           ROUND(AVG(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100, 2) as rto_rate_pct
    FROM orders
    GROUP BY courier_partner
    ORDER BY avg_ndr_attempts DESC;
    """
    print("--- 3. Logistics: Which Courier is struggling with Delivery Attempts? ---")
    print(con.execute(query_ndr).fetchdf())
    print("\n")
    
    # 4. Serial Returners (Fraud / System Abuse)
    query_fraud = """
    SELECT customer_id,
           COUNT(*) as total_lifetime_orders,
           SUM(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) as lifetime_rtos,
           ROUND(AVG(CASE WHEN order_status = 'RTO' THEN 1 ELSE 0 END) * 100, 2) as rto_rate_pct,
           SUM(forward_shipping_cost + return_shipping_cost) as total_loss_caused
    FROM orders
    GROUP BY customer_id
    HAVING COUNT(*) >= 10 AND rto_rate_pct >= 50
    ORDER BY total_loss_caused DESC
    LIMIT 10;
    """
    print("--- 4. Customer Abuse: Top 10 Serial Returners (>= 10 orders) ---")
    print(con.execute(query_fraud).fetchdf())
    print("\n")
    
    # 5. Financial loss by Product Weight (The heavy items hurt the most)
    query_weight = """
    SELECT 
        CASE 
            WHEN product_weight_kg < 1 THEN 'Light (<1kg)'
            WHEN product_weight_kg BETWEEN 1 AND 5 THEN 'Medium (1-5kg)'
            WHEN product_weight_kg BETWEEN 5 AND 15 THEN 'Heavy (5-15kg)'
            ELSE 'Oversized (15kg+)'
        END as weight_class,
        COUNT(*) as total_rto_orders,
        SUM(forward_shipping_cost + return_shipping_cost) as total_loss
    FROM orders
    WHERE order_status = 'RTO'
    GROUP BY weight_class
    ORDER BY total_loss DESC;
    """
    print("--- 5. Financials: Which products are burning shipping budgets? ---")
    print(con.execute(query_weight).fetchdf())
    print("\n")
    
if __name__ == "__main__":
    run_v2_sql_analysis()
