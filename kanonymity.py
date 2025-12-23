import pandas as pd


def check_k_anonymity(df: pd.DataFrame, k_threshold=3):
    result = {"is_calculated": False, "k_value": -1, "risky_records": 0, "risk_msg": ""}
    try:
        # Quasi-identifiers (English keywords)
        qi_keywords = ['gender', 'sex', 'age', 'birth', 'year', 'zip', 'postal', 'city', 'region', 'job', 'occupation',
                       'class', 'role']
        qis = [c for c in df.columns if any(kw in c.lower() for kw in qi_keywords)]

        if len(qis) < 2:
            result["risk_msg"] = "Not enough quasi-identifiers found."
            return result

        result["is_calculated"] = True
        group_sizes = df.fillna('Unknown').groupby(qis).size().reset_index(name='count')

        if group_sizes.empty:
            min_k = 0
        else:
            min_k = int(group_sizes['count'].min())

        result["k_value"] = min_k
        risky_records = group_sizes[group_sizes['count'] < k_threshold]['count'].sum()
        result["risky_records"] = int(risky_records)
        result["total_records"] = len(df)

        if min_k < k_threshold:
            result["risk_msg"] = f"High Re-identification Risk (k={min_k}). {risky_records} records are unique."
        else:
            result["risk_msg"] = f"Low Risk (k={min_k}), complies with k-anonymity (threshold>={k_threshold})."

    except Exception as e:
        result["risk_msg"] = str(e)
    return result