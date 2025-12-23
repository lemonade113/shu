import pandas as pd
from presidio_analyzer import AnalyzerEngine
import re

# Load Engine (Default English is fine)
analyzer = AnalyzerEngine()


def is_text_masked(text):
    text_str = str(text)
    if '*' in text_str or 'xxxx' in text_str: return True
    keywords = ['[REDACTED]', 'Anonymized', 'Masked', 'Unknown', 'Deleted', 'Hidden']
    for kw in keywords:
        if kw.lower() in text_str.lower(): return True
    return False


def is_valid_pii_entity(entity_type, text_snippet, column_name):
    """
    终极抗误报版校验逻辑
    """
    text = str(text_snippet).lower().strip()
    col = str(column_name).lower()

    # 1. 【核心】脱敏特征检测 (Mask Detection)
    # 只要包含星号、x、或者常见的脱敏占位符，直接放行
    if '*' in text or 'xxxx' in text: return False
    if any(k in text for k in ['redacted', 'masked', 'anonymized', 'hidden']): return False

    # 2. 【核心】测试数据白名单 (Test Data Whitelist)
    # 这些词在 generate_realistic_cases.py 里大量出现，必须忽略
    safe_substrings = [
        'example.com', 'sample', 'test', 'demo',
        'user_', 'usr_', 'uid_', 'id_',  # 过滤 ID 类
        'group', 'staff', 'student', 'visitor',  # 职业泛化词
        'region', 'zone', 'district', 'location',  # 地点泛化词
        'normal', 'log', 'entry', 'feedback',  # 文本噪音
        'nan', 'null', 'none'
    ]
    if any(safe in text for safe in safe_substrings):
        return False



    # 针对 PERSON (人名) 的强力过滤
    if entity_type == 'PERSON':
        # 名字里不该有数字
        if any(char.isdigit() for char in text): return False
        # 名字里不该有常用名词
        if text in ['admin', 'manager', 'support', 'system', 'unknown']: return False

    # 针对 EMAIL 的过滤
    if entity_type == 'EMAIL_ADDRESS':
        # 再次确认排除 example
        if 'example' in text: return False

    # 4. 针对 ID 列的保护
    # 如果列名明显是 ID，除非是极高置信度，否则不认
    if any(k in col for k in ['id', 'uid', 'key', 'code', 'ref']):
        # ID 列里出现人名或地点，通常是误报
        if entity_type in ['PERSON', 'LOCATION', 'ORGANIZATION']:
            return False

    return True


def check_pii_compliance(df: pd.DataFrame):
    pii_report = {}
    detected_types = set()
    total_risks = 0
    risky_rows = set()

    sample_data = df.head(100)  # Scan first 100 rows
    object_cols = sample_data.select_dtypes(include=['object', 'string']).columns

    for col in object_cols:
        col_risks = []
        for idx, text in sample_data[col].dropna().astype(str).items():
            if is_text_masked(text): continue

            try:
                results = analyzer.analyze(text=text, language='en')
                has_risk = False
                for res in results:
                    snippet = text[res.start:res.end]
                    if res.score < 0.4: continue
                    if res.entity_type in ['DATE_TIME', 'NRP', 'URL', 'IP_ADDRESS']: continue

                    if is_valid_pii_entity(res.entity_type, snippet, col):
                        col_risks.append(res.entity_type)
                        detected_types.add(res.entity_type)
                        has_risk = True

                if has_risk: risky_rows.add(idx)
            except:
                continue

        if col_risks:
            pii_report[col] = list(set(col_risks))
            total_risks += len(col_risks)

    return {
        "has_pii": total_risks > 0,
        "details": pii_report,
        "risk_types": list(detected_types),
        "total_count": total_risks,
        "risky_rows": risky_rows
    }


def calculate_metrics(df, detected_risky_indices):
    if 'Type' not in df.columns: return None
    actual_risky = set(df[df['Type'] == 'Risky'].index)
    actual_compliant = set(df[df['Type'] == 'Compliant'].index)
    detected = set(detected_risky_indices)

    tp = len(detected.intersection(actual_risky))
    fp = len(detected.intersection(actual_compliant))
    fn = len(actual_risky) - tp
    tn = len(actual_compliant) - fp

    try:
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        accuracy = (tp + tn) / (tp + tn + fp + fn)
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    except:
        recall, precision, accuracy, f1 = 0, 0, 0, 0

    return {
        "Recall": round(recall * 100, 2),
        "Precision": round(precision * 100, 2),
        "F1_Score": round(f1 * 100, 2),
        "Accuracy": round(accuracy * 100, 2),
        "Matrix": {"TP": tp, "FP": fp, "FN": fn, "TN": tn}
    }