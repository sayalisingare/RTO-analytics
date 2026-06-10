import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_v2_data(num_rows=100000):
    np.random.seed(42)
    random.seed(42)
    
    cities = [
        {"city": "Mumbai", "tier": "Tier 1", "state": "Maharashtra", "pincode_start": 400001},
        {"city": "Delhi", "tier": "Tier 1", "state": "Delhi", "pincode_start": 110001},
        {"city": "Bangalore", "tier": "Tier 1", "state": "Karnataka", "pincode_start": 560001},
        {"city": "Pune", "tier": "Tier 2", "state": "Maharashtra", "pincode_start": 411001},
        {"city": "Jaipur", "tier": "Tier 2", "state": "Rajasthan", "pincode_start": 302001},
        {"city": "Lucknow", "tier": "Tier 2", "state": "Uttar Pradesh", "pincode_start": 226001},
        {"city": "Patna", "tier": "Tier 2", "state": "Bihar", "pincode_start": 800001},
        {"city": "Meerut", "tier": "Tier 3", "state": "Uttar Pradesh", "pincode_start": 250001},
        {"city": "Hubli", "tier": "Tier 3", "state": "Karnataka", "pincode_start": 580001},
        {"city": "Rohtak", "tier": "Tier 3", "state": "Haryana", "pincode_start": 124001},
        {"city": "Kurnool", "tier": "Tier 3", "state": "Andhra Pradesh", "pincode_start": 518001},
        {"city": "Siliguri", "tier": "Tier 3", "state": "West Bengal", "pincode_start": 734001}
    ]
    
    # Pre-generate 20,000 unique customers to simulate repeat buyers
    customer_pool = [f"CUST-{str(i).zfill(5)}" for i in range(1, 20001)]
    # Assign an inherent "returner" risk to each customer (beta distribution biased towards low risk, but some high risk)
    customer_risk = {c: np.random.beta(a=1.5, b=8) for c in customer_pool} 
    customer_age = {c: random.randint(1, 1000) for c in customer_pool}
    
    order_ids = [f"ORD-{str(i).zfill(6)}" for i in range(1, num_rows + 1)]
    customers = random.choices(customer_pool, k=num_rows)
    
    city_choices = random.choices(cities, k=num_rows)
    
    categories = random.choices(["Electronics", "Clothing", "Beauty", "Home", "Fashion"], weights=[0.2, 0.3, 0.15, 0.15, 0.2], k=num_rows)
    payment_types = random.choices(["COD", "Prepaid"], weights=[0.6, 0.4], k=num_rows)
    couriers = random.choices(["Delhivery", "Ekart", "Shadowfax", "BlueDart"], k=num_rows)
    sellers = [f"Seller_{str(random.randint(1, 50)).zfill(2)}" for _ in range(num_rows)]
    
    # Dates and SLA
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 12, 31)
    days_diff = (end_date - start_date).days
    
    order_dates = [start_date + timedelta(days=random.randint(0, days_diff)) for _ in range(num_rows)]
    expected_sla_days = [random.randint(3, 7) for _ in range(num_rows)]
    # Actual delivery: sometimes early (-1), sometimes late (+ up to 5)
    actual_delivery_days = [s + random.randint(-1, 5) for s in expected_sla_days]
    
    expected_delivery_dates = [order_dates[i] + timedelta(days=expected_sla_days[i]) for i in range(num_rows)]
    actual_delivery_dates = [order_dates[i] + timedelta(days=actual_delivery_days[i]) for i in range(num_rows)]
    
    # New metrics
    ndr_counts = random.choices([0, 1, 2, 3], weights=[0.7, 0.15, 0.1, 0.05], k=num_rows)
    # Discount normal distribution centered around 15%, max 80%
    discount_pcts = np.clip(np.random.normal(loc=15, scale=20, size=num_rows), 0, 80).astype(int)
    order_values = [random.randint(500, 15000) for _ in range(num_rows)]
    
    # Weights for products
    weight_map = {"Electronics": (0.5, 5), "Clothing": (0.1, 1), "Beauty": (0.1, 0.5), "Home": (2, 20), "Fashion": (0.2, 1.5)}
    product_weights = [round(random.uniform(weight_map[c][0], weight_map[c][1]), 1) for c in categories]
    
    df = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": customers,
        "order_date": order_dates,
        "expected_delivery_date": expected_delivery_dates,
        "actual_delivery_date": actual_delivery_dates,
        "customer_pincode": [c["pincode_start"] + random.randint(0, 99) for c in city_choices],
        "city": [c["city"] for c in city_choices],
        "city_tier": [c["tier"] for c in city_choices],
        "state": [c["state"] for c in city_choices],
        "seller_id": sellers,
        "product_category": categories,
        "product_weight_kg": product_weights,
        "order_value": order_values,
        "discount_percentage": discount_pcts,
        "payment_type": payment_types,
        "courier_partner": couriers,
        "ndr_count": ndr_counts
    })
    
    df["delivery_delay_days"] = (df["actual_delivery_date"] - df["expected_delivery_date"]).dt.days
    df["customer_account_age_days"] = df["customer_id"].map(customer_age)
    df["customer_inherent_risk"] = df["customer_id"].map(customer_risk)
    
    # Calculate RTO Probabilities based on V2 Logic
    def calculate_v2_rto(row):
        prob = 0.20 if row["payment_type"] == "COD" else 0.05
        
        # 1. Logistics Penalty (Huge impact if late)
        if row["delivery_delay_days"] > 2:
            prob += 0.35  
            
        # 2. NDR Penalty
        if row["ndr_count"] > 1:
            prob += 0.25
            
        # 3. Impulse Buy (High Discount)
        if row["discount_percentage"] > 50:
            prob += 0.15
            
        # 4. Customer History
        prob += row["customer_inherent_risk"]
        
        if row["city_tier"] == "Tier 3":
            prob += 0.05
            
        return max(0.01, min(0.99, prob))
        
    rto_probs = df.apply(calculate_v2_rto, axis=1)
    df["order_status"] = np.where(np.random.rand(num_rows) < rto_probs, "RTO", "Delivered")
    
    # Dynamic Shipping Costs based on weight and tier
    base_cost = 40
    weight_cost = df["product_weight_kg"] * 12
    tier_penalty = np.where(df["city_tier"] == "Tier 3", 30, np.where(df["city_tier"] == "Tier 2", 15, 0))
    
    df["forward_shipping_cost"] = np.round(base_cost + weight_cost + tier_penalty)
    df["return_shipping_cost"] = np.where(df["order_status"] == "RTO", np.round(df["forward_shipping_cost"] * 0.8), 0)
    
    # Drop intermediate columns
    df.drop(columns=["customer_inherent_risk"], inplace=True)
    
    df.to_csv("raw_ecommerce_data.csv", index=False)
    
    print("V2 Data Generated successfully.")
    print(f"Overall RTO Rate: {df['order_status'].value_counts(normalize=True).get('RTO', 0):.2%}")
    print("\nRTO by Delivery Delay (>2 days):")
    print(df[df['delivery_delay_days'] > 2]['order_status'].value_counts(normalize=True))

if __name__ == "__main__":
    generate_v2_data(100000)
