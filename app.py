# -*- coding: utf-8 -*-
import os
import json
import re
import jieba
from flask import Flask, request, render_template, send_file, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
# ===================== 导入配置文件 =====================
from config import (
    PRIVACY_BASELINE,
    AI_ACT_DECISION_TREE,
    DOMAIN_BUSINESS_CONFIG,
    DOMAIN_CONFIG,
    SYNONYM_DICT,
    NEGATIVE_WORDS
)
# ===================== 基础配置 & 初始化 =====================
app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

# 路径配置（兼容所有系统，自动创建文件夹）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['REPORT_FOLDER'] = os.path.join(BASE_DIR, 'reports')
app.config['TEMPLATE_FOLDER'] = os.path.join(BASE_DIR, 'templates')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB限制

# 自动创建所有必要文件夹
for folder in [app.config['UPLOAD_FOLDER'], app.config['REPORT_FOLDER'], app.config['TEMPLATE_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder, mode=0o777, exist_ok=True)


# ===================== NLP预处理工具 =====================

def nlp_preprocess(content):
    """文本预处理：分词 + 同义词替换"""
    if not content:
        return []
    words = jieba.lcut(content.lower())
    processed_words = []
    for word in words:
        replaced = False
        for core_word, synonyms in SYNONYM_DICT.items():
            if word in synonyms:
                processed_words.append(core_word)
                replaced = True
                break
        if not replaced:
            processed_words.append(word)
    return processed_words


def has_semantic_match(processed_words, target_core_word, content):
    """
    语义匹配（排除否定词）：遍历所有匹配位置，而非仅第一个
    """
    if target_core_word not in processed_words:
        return False

    content_lower = content.lower()
    # 遍历所有目标词出现的位置
    target_len = len(target_core_word)
    start_idx = 0
    while True:
        target_index = content_lower.find(target_core_word, start_idx)
        if target_index == -1:
            break

        # 上下文窗口：目标词前后15个字符
        window_start = max(0, target_index - 15)
        window_end = min(len(content_lower), target_index + target_len + 15)
        window = content_lower[window_start:window_end]

        # 检查否定词：无否定词则匹配成功
        has_neg = any(neg_word in window for neg_word in NEGATIVE_WORDS)
        if not has_neg:
            return True

        start_idx = target_index + target_len  # 继续查找下一个位置

    # 所有位置都有否定词 → 匹配失败
    return False


# ===================== 业务场景识别 =====================
def identify_business_scenario(content, domain):
    domain = domain.lower()
    if domain not in DOMAIN_BUSINESS_CONFIG:
        domain = "general"
    domain_scenarios = DOMAIN_BUSINESS_CONFIG[domain]

    for scenario in domain_scenarios.keys():
        if scenario in content:
            return scenario, domain_scenarios[scenario]
    return "default", domain_scenarios["default"]


# ===================== 数据最小化判定 =====================
def check_data_minimization(content, collected_data, domain, scenario_config):
    violation_reasons = []
    if not collected_data:
        return violation_reasons

    necessary_data_names = [item["name"] for item in scenario_config["necessary_data"]]
    forbidden_data_names = scenario_config["forbidden_data"]
    core_function = scenario_config["core_function"]

    # 维度1：采集禁止项
    forbidden_collected = [item for item in collected_data if item in forbidden_data_names]
    if forbidden_collected:
        violation_reasons.append(f"采集与业务功能（{core_function}）无关的禁止项：{','.join(forbidden_collected)}")

    # 维度2：必要项过度粒度
    for item in scenario_config["necessary_data"]:
        data_name = item["name"]
        required_granularity = item["granularity"]
        if data_name in collected_data:
            if "脱敏" in required_granularity and re.search(r'完整|未脱敏', content, re.IGNORECASE):
                violation_reasons.append(
                    f"必要项「{data_name}」采集过度粒度（要求：{required_granularity}，实际：完整/未脱敏）")
            if "无需" in required_granularity and re.search(f'{data_name}.*具体|{data_name}.*完整', content,
                                                            re.IGNORECASE):
                violation_reasons.append(
                    f"必要项「{data_name}」采集过度粒度（要求：{required_granularity}，实际：具体/完整信息）")

    # 维度3：冗余必要项
    redundant_necessary = []
    same_purpose = [item["name"] for item in scenario_config["necessary_data"] if "标识" in item["granularity"]]
    if len(same_purpose) > 1:
        collected_same_purpose = [d for d in collected_data if d in same_purpose]
        if len(collected_same_purpose) > 1:
            redundant_necessary = collected_same_purpose
    if redundant_necessary:
        violation_reasons.append(
            f"采集冗余必要项（同一目的无需多项）：{','.join(redundant_necessary)}（可选：{same_purpose[0]}）")

    # 维度4：永久存储
    if re.search(r'永久存储|无时限', content, re.IGNORECASE):
        violation_reasons.append(f"{DOMAIN_CONFIG[domain]['name']}禁止永久存储个人数据，需按业务周期限制存储时长")

    return violation_reasons


# ===================== 领域规则适配 =====================
def apply_domain_rules(info, content, processed_words, domain):
    domain = domain.lower() if domain else "general"
    if domain not in DOMAIN_CONFIG:
        domain = "general"
    config = DOMAIN_CONFIG[domain]

    info['domain'] = domain
    info['domain_name'] = config['name']
    info['domain_violation'] = []
    info['has_domain_violation'] = False

    # 识别业务场景
    scenario, scenario_config = identify_business_scenario(content, domain)
    info['business_scenario'] = scenario
    info['scenario_core_function'] = scenario_config['core_function']
    info['scenario_necessary_data'] = scenario_config['necessary_data']

    # 数据最小化违规
    data_min_violations = check_data_minimization(content, info['collected_data'], domain, scenario_config)
    info['domain_violation'].extend(data_min_violations)

    # 领域专属违规
    if domain == "education":
        if re.search(r'儿童|学生|未成年人', content, re.IGNORECASE) and not has_semantic_match(processed_words,
                                                                                               "知情同意", content):
            info['domain_violation'].append("教育领域儿童数据需获取监护人同意（仅学生同意无效）")
        if not any(word in content for word in config['encryption']):
            info['domain_violation'].append("教育领域学生数据需采用AES-256/双重加密存储")

    elif domain == "medical":
        if re.search(r'病历|患者数据', content, re.IGNORECASE) and not re.search(r'AES-256', content, re.IGNORECASE):
            info['domain_violation'].append("医疗领域病历数据必须采用AES-256加密")
        if re.search(r'口头授权', content, re.IGNORECASE) and not re.search(r'书面授权', content, re.IGNORECASE):
            info['domain_violation'].append("医疗领域需获取患者书面授权（仅口头授权无效）")
        if re.search(r'病历|患者数据', content, re.IGNORECASE) and not re.search(r'脱敏', content, re.IGNORECASE):
            info['domain_violation'].append("医疗领域病历数据需做脱敏处理")

    elif domain == "finance":
        if re.search(r'征信数据', content, re.IGNORECASE) and re.search(r'单重加密', content, re.IGNORECASE):
            info['domain_violation'].append("金融领域征信数据需采用双重加密存储")
        if not has_semantic_match(processed_words, "知情同意", content) and re.search(r'授权|同意', content,
                                                                                      re.IGNORECASE):
            info['domain_violation'].append("金融领域需获取用户双重确认授权（短信+弹窗）")

    info['has_domain_violation'] = len(info['domain_violation']) > 0
    return info


# ===================== 单文件信息采集（核心修复） =====================
def collect_single_file_info(file_path, file_type, domain="general"):
    info = {
        "collected_data": [], "sensitive_data": False, "encryption": False,
        "consent": False, "consent_revocable": False, "dpiia_completed": False,
        "has_forbidden_behavior": False, "is_high_risk_app": False, "has_profiling": False,
        "has_human_interaction": False, "has_unlimited_storage": False,
        "has_data_desensitization": False, "has_manual_supervision": False,
        "business_scenario": "default", "scenario_core_function": "", "scenario_necessary_data": [],
        "domain_violation": [], "has_domain_violation": False
    }

    # 修复点2：优化文件读取异常处理，保留已解析内容
    content = ""
    try:
        if file_type in ['py', 'json', 'md', 'txt']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        elif file_type == 'pdf':
            reader = PdfReader(file_path)
            content = '\n'.join([page.extract_text() or '' for page in reader.pages])
    except Exception as e:
        print(f"解析文件 {file_path} 出错：{str(e)}")
        # 不直接返回空info，保留基础结构
        return info

    # 预处理
    processed_words = nlp_preprocess(content)

    # 提取采集的数据项
    collect_patterns = r'身份证|手机号|人脸|儿童数据|学生数据|学号|年级|班级|学科|作业ID|病历号|诊断结果|症状描述|用药史|过敏史|银行卡|征信|交易数据|家庭住址|父母职业|姓名|社交账号|具体生日|学生照片|家属联系方式|患者职业|完整卡号|手机号脱敏'
    info['collected_data'] = list(set(re.findall(collect_patterns, content, re.IGNORECASE)))

    # 基础隐私字段检测
    info['sensitive_data'] = has_semantic_match(processed_words, "敏感数据", content)
    info['encryption'] = has_semantic_match(processed_words, "加密", content)
    info['consent'] = has_semantic_match(processed_words, "知情同意", content)

    # 修复点3：同意可撤回检测复用has_semantic_match，避免否定场景误判
    info['consent_revocable'] = has_semantic_match(processed_words, "撤回", content) or has_semantic_match(
        processed_words, "取消", content)

    info['dpiia_completed'] = has_semantic_match(processed_words, "DPIA", content)
    info['has_unlimited_storage'] = bool(re.search(r'永久存储|无时限', content, re.IGNORECASE))
    info['has_data_desensitization'] = bool(re.search(r'脱敏|数据掩码', content, re.IGNORECASE))
    info['has_manual_supervision'] = bool(re.search(r'人工监督|人工审核', content, re.IGNORECASE))

    # AI法案检测
    for forbidden in AI_ACT_DECISION_TREE['forbidden_behavior']:
        if forbidden in content:
            info['has_forbidden_behavior'] = True
            break
    for high_risk in AI_ACT_DECISION_TREE['high_risk_app']:
        if high_risk in content:
            info['is_high_risk_app'] = True
            break
    info['has_profiling'] = any(word in content for word in AI_ACT_DECISION_TREE['profiling_keywords'])
    info['has_human_interaction'] = bool(re.search(r'用户交互|人机交互', content, re.IGNORECASE))

    # 应用领域规则
    info = apply_domain_rules(info, content, processed_words, domain)

    return info


# ===================== 多文件信息合并（核心修复） =====================
def collect_multi_files_info(files, domain="general"):
    merged_info = {
        "collected_data": [], "sensitive_data": False, "encryption": False,
        "consent": False, "consent_revocable": False, "dpiia_completed": False,
        "has_forbidden_behavior": False, "is_high_risk_app": False, "has_profiling": False,
        "has_human_interaction": False, "has_unlimited_storage": False,
        "has_data_desensitization": False, "has_manual_supervision": False,
        "domain": domain, "domain_name": DOMAIN_CONFIG[domain]['name'],
        "domain_violation": [], "has_domain_violation": False,
        "business_scenario": "default", "scenario_core_function": "", "scenario_necessary_data": [],
        "scenario_count": {}  # 新增：统计各场景出现次数
    }

    for file in files:
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            file_type = file.filename.split('.')[-1].lower()
            single_info = collect_single_file_info(file_path, file_type, domain)

            # 合并基础字段（逻辑不变）
            merged_info['collected_data'] = list(set(merged_info['collected_data'] + single_info['collected_data']))
            merged_info['sensitive_data'] |= single_info['sensitive_data']
            merged_info['encryption'] |= single_info['encryption']
            merged_info['consent'] |= single_info['consent']
            merged_info['consent_revocable'] |= single_info['consent_revocable']
            merged_info['dpiia_completed'] |= single_info['dpiia_completed']
            merged_info['has_forbidden_behavior'] |= single_info['has_forbidden_behavior']
            merged_info['is_high_risk_app'] |= single_info['is_high_risk_app']
            merged_info['has_profiling'] |= single_info['has_profiling']
            merged_info['has_human_interaction'] |= single_info['has_human_interaction']
            merged_info['has_unlimited_storage'] |= single_info['has_unlimited_storage']
            merged_info['has_data_desensitization'] |= single_info['has_data_desensitization']
            merged_info['has_manual_supervision'] |= single_info['has_manual_supervision']

            # 合并领域字段（逻辑不变）
            merged_info['domain_violation'].extend(single_info.get('domain_violation', []))
            merged_info['has_domain_violation'] |= single_info.get('has_domain_violation', False)

            # 修复点4：统计各业务场景出现次数，避免覆盖
            scenario = single_info.get('business_scenario', "default")
            merged_info['scenario_count'][scenario] = merged_info['scenario_count'].get(scenario, 0) + 1

            # 暂存场景信息（后续取最高频）
            if scenario != "default":
                merged_info['scenario_core_function'] = single_info.get('scenario_core_function', "")
                merged_info['scenario_necessary_data'] = single_info.get('scenario_necessary_data', [])

        except Exception as e:
            print(f"处理文件 {file.filename} 出错：{str(e)}")
            continue

    # 修复点4续：取出现次数最多的场景（非默认优先）
    if merged_info['scenario_count']:
        # 过滤掉default，优先选非默认场景
        non_default = {k: v for k, v in merged_info['scenario_count'].items() if k != "default"}
        if non_default:
            merged_info['business_scenario'] = max(non_default, key=non_default.get)
        else:
            merged_info['business_scenario'] = max(merged_info['scenario_count'], key=merged_info['scenario_count'].get)

    # 去重违规原因
    merged_info['domain_violation'] = list(set(merged_info['domain_violation']))
    return merged_info


# ===================== AI法案风险分级 =====================
def ai_act_risk_prejudge(merged_info):
    if merged_info['has_forbidden_behavior']:
        return {
            "risk_level": "forbidden",
            "risk_desc": "不可接受风险（AI法案第5条禁止行为）",
            "action": "禁止部署，无需后续检测"
        }
    if merged_info['is_high_risk_app'] or merged_info['has_profiling']:
        return {
            "risk_level": "high",
            "risk_desc": f"{merged_info['domain_name']}高风险（AI法案附件III高风险应用）",
            "action": "需执行全面隐私检测"
        }
    if merged_info['has_human_interaction']:
        return {
            "risk_level": "limited",
            "risk_desc": f"{merged_info['domain_name']}有限风险（与人类交互/生成内容）",
            "action": "需执行核心隐私检测"
        }
    return {
        "risk_level": "low",
        "risk_desc": f"{merged_info['domain_name']}最小风险（本地处理/无人类交互）",
        "action": "仅需执行基础隐私检测"
    }


# ===================== 隐私合规检测 =====================
def check_privacy_compliance(ai_info, ai_risk_level):
    risk_level_map = {"high": "高风险", "limited": "有限风险", "low": "最小风险"}
    domain = ai_info['domain']
    domain_name = ai_info['domain_name']
    domain_violation = ai_info['domain_violation']
    business_scenario = ai_info['business_scenario']
    core_function = ai_info['scenario_core_function']

    # 分级检测策略
    if ai_risk_level == "high":
        target_items = PRIVACY_BASELINE
    elif ai_risk_level == "limited":
        target_items = [item for item in PRIVACY_BASELINE if item["id"] in [1, 2, 3, 4]]
    elif ai_risk_level == "low":
        target_items = [item for item in PRIVACY_BASELINE if item["id"] in [1, 3, 4]]
    else:
        target_items = []

    detection_results = []
    compliant_count = 0
    total_target_items = len(target_items)

    for item in target_items:
        item_result = {
            "id": item["id"],
            "name": f"{domain_name}-{business_scenario}-{item['name']}",
            "compliant": False,
            "suggestion": item["suggestion"],
            "reason": ""
        }
        reason_list = []

        # 1. 数据最小化检测
        if item["id"] == 1:
            data_min_reasons = [v for v in domain_violation if
                                "采集禁止项" in v or "采集过度粒度" in v or "冗余必要项" in v or "永久存储" in v]
            reason_list.extend(data_min_reasons)
            item_result["compliant"] = len(data_min_reasons) == 0

        # 2. 知情同意检测
        elif item["id"] == 2:
            if not ai_info["consent"]:
                reason_list.append(f"{domain_name}未获取用户知情同意")
            if ai_info["consent"] and not ai_info["consent_revocable"]:
                reason_list.append(f"{domain_name}同意不可撤回（需支持撤回）")
            consent_violations = [v for v in domain_violation if "同意" in v or "授权" in v]
            reason_list.extend(consent_violations)
            item_result["compliant"] = ai_info["consent"] and ai_info["consent_revocable"] and len(
                consent_violations) == 0

        # 3. 敏感数据保护检测
        elif item["id"] == 3:
            if ai_info["sensitive_data"] and not ai_info["has_data_desensitization"]:
                reason_list.append(f"{domain_name}敏感数据未做脱敏处理")
            if ai_info["sensitive_data"] and ai_info["has_unlimited_storage"]:
                reason_list.append(f"{domain_name}敏感数据无时限存储（违规）")
            sensitive_violations = [v for v in domain_violation if "敏感数据" in v or "脱敏" in v]
            reason_list.extend(sensitive_violations)
            item_result["compliant"] = (not ai_info["sensitive_data"]) or (
                        ai_info["sensitive_data"] and ai_info["has_data_desensitization"] and not ai_info[
                    "has_unlimited_storage"])

        # 4. 存储加密检测
        elif item["id"] == 4:
            if ai_info["sensitive_data"] and not ai_info["encryption"]:
                reason_list.append(f"{domain_name}敏感数据未加密存储")
            encryption_violations = [v for v in domain_violation if "加密" in v]
            reason_list.extend(encryption_violations)
            item_result["compliant"] = not ai_info["sensitive_data"] or (
                        ai_info["sensitive_data"] and ai_info["encryption"] and len(encryption_violations) == 0)

        # 5. 高风险AI评估检测
        elif item["id"] == 5:
            if not ai_info["dpiia_completed"]:
                reason_list.append(f"{domain_name}未完成DPIA隐私影响评估")
            if ai_info["dpiia_completed"] and not ai_info["has_manual_supervision"]:
                reason_list.append(f"{domain_name}DPIA评估无人工监督机制")
            item_result["compliant"] = ai_info["dpiia_completed"] and ai_info["has_manual_supervision"]

        # 整理结果
        item_result["reason"] = "；".join(reason_list) if reason_list else "无"
        if item_result["compliant"]:
            compliant_count += 1
        detection_results.append(item_result)

    # 计算合规率 & 结论
    if total_target_items == 0:
        compliance_rate = 100.0
        conclusion = f"{domain_name}该AI系统为禁止类应用（AI法案第5条），禁止部署"
        non_compliant_num = 0
    else:
        compliance_rate = round((compliant_count / total_target_items) * 100, 2)
        non_compliant_num = total_target_items - compliant_count
        if compliance_rate == 100:
            conclusion = f"{domain_name}-{business_scenario}（核心功能：{core_function}）该{risk_level_map[ai_risk_level]}AI系统符合GDPR/AI Act隐私合规要求"
        else:
            domain_note = f"【专属违规】：{';'.join(domain_violation)}" if domain_violation else ""
            conclusion = f"{domain_name}-{business_scenario}（核心功能：{core_function}）该{risk_level_map[ai_risk_level]}AI系统存在{non_compliant_num}项隐私不合规问题；{domain_note}"

    return {
        "ai_risk_level": f"{domain_name}-{risk_level_map.get(ai_risk_level, '未知风险')}",
        "compliance_rate": compliance_rate,
        "conclusion": conclusion,
        "details": detection_results,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_num,
        "detected_items_num": total_target_items,
        "domain_violation": domain_violation,
        "business_scenario": business_scenario,
        "core_function": core_function
    }


# ===================== PDF报告生成 =====================
def generate_pdf_report(detection_result, risk_result):
    # 报告路径
    report_path = os.path.join(app.config['REPORT_FOLDER'], 'ai_privacy_report.pdf')
    # 创建PDF文档
    doc = SimpleDocTemplate(report_path, pagesize=A4,
                            leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)

    # 样式配置
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontSize = 12
    normal_style.leading = 20
    normal_style.wordWrap = 'CJK'

    heading1_style = styles['Heading1']
    heading1_style.fontSize = 20
    heading1_style.alignment = 1

    heading2_style = styles['Heading2']
    heading2_style.fontSize = 16
    heading2_style.textColor = '#2c3e50'

    # 构建PDF内容
    story = []
    story.append(Paragraph("AI系统隐私合规检测报告", heading1_style))
    story.append(Spacer(1, 30))

    # 1. 风险预判断
    story.append(Paragraph("一、AI法案风险预判断", heading2_style))
    story.append(Spacer(1, 15))
    risk_data = [
        ["风险等级判定", risk_result['risk_desc']],
        ["处理建议", risk_result['action']]
    ]
    risk_table = Table(risk_data, colWidths=[200, 400])
    risk_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, '#dddddd')
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 25))

    # 2. 合规检测结果
    story.append(Paragraph("二、隐私合规检测结果", heading2_style))
    story.append(Spacer(1, 15))
    basic_data = [
        ["检测领域", detection_result['ai_risk_level'].split('-')[0]],
        ["业务场景", detection_result['business_scenario']],
        ["核心功能", detection_result['core_function']],
        ["风险等级", detection_result['ai_risk_level'].split('-')[1]],
        ["检测项总数", str(detection_result['detected_items_num'])],
        ["合规项数", str(detection_result['compliant_count'])],
        ["不合规项数", str(detection_result['non_compliant_count'])],
        ["合规率", f"{detection_result['compliance_rate']}%"],
        ["核心结论", detection_result['conclusion']]
    ]
    basic_table = Table(basic_data, colWidths=[200, 400])
    basic_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, '#dddddd')
    ]))
    story.append(basic_table)
    story.append(Spacer(1, 25))

    # 3. 详细检测项
    if detection_result['details']:
        story.append(Paragraph("三、详细检测项结果", heading2_style))
        story.append(Spacer(1, 15))
        detail_data = [
            ["检测项名称", "合规状态", "不合规原因", "整改建议"]
        ]
        for item in detection_result['details']:
            status = "符合" if item['compliant'] else "不符合"
            reason = item['reason'] if item['reason'] else "无"
            detail_data.append([
                item['name'],
                status,
                reason,
                item['suggestion']
            ])
        detail_table = Table(detail_data, colWidths=[220, 70, 120, 180])
        detail_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
            ('BACKGROUND', (0, 0), (-1, 0), '#f5f7fa'),
            ('GRID', (0, 0), (-1, -1), 1, '#dddddd'),
            ('PADDING', (0, 0), (-1, -1), 8, 8)
        ]))
        story.append(detail_table)

    # 生成PDF
    doc.build(story)
    return report_path


# ===================== Flask路由 =====================
@app.route('/')
def index():
    """首页"""
    return render_template('index.html', result=None, risk_result=None, error=None)


@app.route('/detect', methods=['POST'])
def detect():
    """检测接口"""
    try:
        files = request.files.getlist('files')
        domain = request.form.get('domain', "general")

        # 校验文件
        if not files:
            return jsonify({
                "error": "请至少上传一个文件！",
                "risk_result": None,
                "result": None
            }), 400

        # 采集多文件信息
        ai_info = collect_multi_files_info(files, domain)
        # 风险预判断
        risk_result = ai_act_risk_prejudge(ai_info)

        # 禁止类应用直接返回
        if risk_result['risk_level'] == 'forbidden':
            return jsonify({
                "error": None,
                "risk_result": risk_result,
                "result": None
            }), 200

        # 合规检测
        detection_result = check_privacy_compliance(ai_info, risk_result['risk_level'])
        # 生成PDF报告
        generate_pdf_report(detection_result, risk_result)

        # 返回结果
        return jsonify({
            "error": None,
            "risk_result": risk_result,
            "result": detection_result
        }), 200

    except Exception as e:
        # 捕获所有异常，返回具体错误信息
        error_msg = f"检测失败：{str(e)}"
        print(error_msg)
        return jsonify({
            "error": error_msg,
            "risk_result": None,
            "result": None
        }), 500


@app.route('/download_report')
def download_report():
    """下载报告"""
    report_path = os.path.join(app.config['REPORT_FOLDER'], 'ai_privacy_report.pdf')
    if not os.path.exists(report_path):
        return render_template('index.html', result=None, risk_result=None, error="检测报告尚未生成！")
    return send_file(report_path, as_attachment=True)


# ===================== 启动服务 =====================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)