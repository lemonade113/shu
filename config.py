# config.py - AI隐私合规检测配置文件
# -*- coding: utf-8 -*-

# ===================== GDPR隐私基线配置 =====================
PRIVACY_BASELINE = [
    {"id": 1, "name": "数据最小化（GDPR第5条）", "suggestion": "仅采集与业务核心功能直接相关的必要数据，采用最小粒度采集，禁止采集非必要/冗余数据，限制存储时长"},
    {"id": 2, "name": "知情同意与数据主体权利（GDPR第6/17条）", "suggestion": "补充分层同意机制，明确告知用户权利"},
    {"id": 3, "name": "敏感数据保护（GDPR第9条）", "suggestion": "对敏感数据进行不可逆的脱敏处理，禁止无时限存储并加密储存"},
    {"id": 4, "name": "存储加密与安全（AI Act第25条）", "suggestion": "采用AES-256加密算法对存储的个人数据进行加密"},
    {"id": 5, "name": "高风险AI隐私评估（AI Act第14条）", "suggestion": "完成DPIA数据保护影响评估，建立人工监督机制"}
]

# ===================== AI法案决策树配置 =====================
AI_ACT_DECISION_TREE = {
    "forbidden_behavior": ["社会信用评分", "实时远程生物识别", "操纵性设计", "大规模监控"],
    "high_risk_app": ["人脸识别", "医疗诊断", "教育评估", "就业筛选", "信贷评分"],
    "profiling_keywords": ["用户画像", "行为分析", "精准推送", "偏好预测"]
}

# ===================== 领域-业务场景配置 =====================
DOMAIN_BUSINESS_CONFIG = {
    "education": {
        "作业批改工具": {
            "core_function": "批改学生作业、反馈成绩",
            "necessary_data": [
                {"name": "学生姓名", "granularity": "完整姓名（必要识别）"},
                {"name": "学号", "granularity": "完整学号（唯一标识）"},
                {"name": "作业ID", "granularity": "唯一ID（关联作业）"}
            ],
            "forbidden_data": ["家庭住址", "父母职业", "社交账号", "具体生日", "学生照片"]
        },
        "在线辅导平台": {
            "core_function": "实时辅导、解答疑问",
            "necessary_data": [
                {"name": "学生姓名", "granularity": "完整姓名"},
                {"name": "年级", "granularity": "年级（如3年级，无需具体班级）"},
                {"name": "学科", "granularity": "具体学科（如数学）"}
            ],
            "forbidden_data": ["家庭电话", "父母收入", "家庭住址", "学生身份证号"]
        },
        "default": {
            "core_function": "教育相关服务",
            "necessary_data": [{"name": "学生姓名", "granularity": "完整姓名"}],
            "forbidden_data": ["家庭住址", "父母职业", "社交账号"]
        }
    },
    "medical": {
        "病历分析工具": {
            "core_function": "分析病历、辅助诊断",
            "necessary_data": [
                {"name": "病历号", "granularity": "完整病历号（唯一标识）"},
                {"name": "诊断结果", "granularity": "具体诊断（如肺炎）"},
                {"name": "症状描述", "granularity": "关键症状（无需详细病史）"},
                {"name": "用药史", "granularity": "相关药物（无需全部病史）"}
            ],
            "forbidden_data": ["患者家庭住址", "家属联系方式", "患者职业", "非相关病史", "患者照片"]
        },
        "远程问诊平台": {
            "core_function": "远程诊断、指导用药",
            "necessary_data": [
                {"name": "病历号", "granularity": "完整病历号"},
                {"name": "诊断结果", "granularity": "具体诊断"},
                {"name": "症状描述", "granularity": "详细症状"},
                {"name": "过敏史", "granularity": "具体过敏原"}
            ],
            "forbidden_data": ["患者身份证号", "家庭收入", "非相关健康数据"]
        },
        "default": {
            "core_function": "医疗相关服务",
            "necessary_data": [{"name": "病历号", "granularity": "完整病历号"}, {"name": "诊断结果", "granularity": "具体诊断"}],
            "forbidden_data": ["家庭住址", "家属联系方式", "非相关病史"]
        }
    },
    "finance": {
        "支付风控工具": {
            "core_function": "验证身份、防范交易风险",
            "necessary_data": [
                {"name": "银行卡后4位", "granularity": "后4位（无需完整卡号）"},
                {"name": "手机号脱敏", "granularity": "隐藏中间4位（如138****1234）"},
                {"name": "交易金额", "granularity": "具体金额"}
            ],
            "forbidden_data": ["完整卡号", "身份证完整号", "社交账号", "家庭住址", "职业信息"]
        },
        "征信查询平台": {
            "core_function": "查询征信、评估信用",
            "necessary_data": [
                {"name": "身份证后6位", "granularity": "后6位（无需完整号）"},
                {"name": "手机号脱敏", "granularity": "隐藏中间4位"},
                {"name": "征信评分", "granularity": "具体评分"}
            ],
            "forbidden_data": ["完整身份证号", "家庭收入", "社交关系", "非信用相关数据"]
        },
        "default": {
            "core_function": "金融相关服务",
            "necessary_data": [{"name": "银行卡后4位", "granularity": "后4位"}, {"name": "手机号脱敏", "granularity": "隐藏中间4位"}],
            "forbidden_data": ["完整卡号", "完整身份证号", "家庭住址"]
        }
    },
    "general": {
        "用户登录系统": {
            "core_function": "验证身份、登录账号",
            "necessary_data": [{"name": "手机号脱敏", "granularity": "隐藏中间4位"}],
            "forbidden_data": ["身份证号", "人脸数据", "住址", "职业"]
        },
        "信息采集工具": {
            "core_function": "收集必要用户信息",
            "necessary_data": [{"name": "姓名", "granularity": "完整姓名"}, {"name": "手机号脱敏", "granularity": "隐藏中间4位"}],
            "forbidden_data": ["身份证号", "家庭住址", "社交账号", "非必要个人信息"]
        },
        "default": {
            "core_function": "通用服务",
            "necessary_data": [{"name": "手机号脱敏", "granularity": "隐藏中间4位"}],
            "forbidden_data": ["身份证号", "人脸数据", "家庭住址"]
        }
    }
}

# ===================== 领域专属配置 =====================
DOMAIN_CONFIG = {
    "general": {
        "name": "通用领域",
        "encryption": ["加密", "AES", "encrypt"],
        "consent": ["授权", "同意"],
        "sensitive_data": ["身份证", "手机号", "人脸"]
    },
    "education": {
        "name": "教育领域",
        "encryption": ["AES-256", "双重加密"],
        "consent": ["监护人同意", "双重授权"],
        "sensitive_data": ["儿童数据", "学生数据", "未成年人"]
    },
    "medical": {
        "name": "医疗领域",
        "encryption": ["AES-256"],
        "consent": ["书面授权", "患者授权"],
        "sensitive_data": ["病历", "患者数据", "诊断结果", "医疗记录"]
    },
    "finance": {
        "name": "金融领域",
        "encryption": ["双重加密", "AES-256"],
        "consent": ["双重确认", "双重授权"],
        "sensitive_data": ["银行卡", "征信", "交易数据"]
    }
}

# ===================== NLP相关配置 =====================
# 同义词映射字典
SYNONYM_DICT = {
    "数据最小化": ["必要数据", "最少采集", "限制存储", "存储时长", "仅采集"],
    "知情同意": ["授权", "同意", "consent", "知情", "分层同意", "监护人同意", "书面授权", "双重确认"],
    "敏感数据": ["身份证", "手机号", "人脸", "儿童数据", "学生数据", "病历", "患者数据", "银行卡", "征信"],
    "加密": ["加密存储", "AES", "AES-256", "encrypt", "双重加密", "单重加密"],
    "DPIA": ["DPIA", "隐私评估", "数据保护影响评估", "人工监督"],
    "业务场景": ["作业批改", "在线辅导", "学生管理", "病历分析", "远程问诊", "支付风控", "征信查询", "用户登录"],
    "撤回": ["撤回", "取消"],
    "取消": ["撤回", "取消"]
}

# 否定词列表
NEGATIVE_WORDS = ["不", "未", "无", "没有", "无需", "不支持", "未获取", "未加密"]