import os
import json
# 确保 app.py 在同一目录下
from app import collect_multi_files_info, check_privacy_compliance, ai_act_risk_prejudge

# ================= 1. 定义标准答案 (Ground Truth) =================
# 这里的 ID 必须与 generate_realistic_cases.py 生成的一模一样
# ID对应关系: 1:数据最小化, 2:知情同意, 3:敏感数据, 4:存储加密, 5:DPIA
GROUND_TRUTH = {
    # --- General ---
    "01_Gen_Perfect": [],  # 完美合规
    "02_Gen_Vague_Doc": [],  # 模糊文档 -> 可能会误报缺失加密(4)
    "03_Gen_Mixed_Leak": [1, 3],  # 混合泄露 -> 最小化(1), 敏感(3)
    "04_Gen_Custom_Crypto": [4],  # 自定义库 -> AST识别不出 -> 判为不安全(4)
    "05_Gen_Fail_Sec": [4],  # 隐藏漏洞 -> 安全(4)
    "06_Gen_Border_K": [],  # 边界K值 -> 应该通过，除非随机到极低值

    # --- Education ---
    "11_Edu_Pass": [],
    "12_Edu_Vague_Risk": [5],  # 模糊描述导致判为低风险? 或者文档缺DPIA关键词 -> DPIA(5)
    "13_Edu_Fail_Consent": [2],  # 缺同意 -> 同意(2)
    "14_Edu_Hidden_PII": [1, 3],  # 隐性泄露
    "15_Edu_Fail_K": [1],  # K值低

    # --- Medical ---
    "21_Med_Pass": [],
    "22_Med_Vague_Crypto": [4],  # 模糊加密描述 -> 加密(4)
    "23_Med_Fail_Data": [1, 3],  # 明文PII
    "24_Med_Fail_Code": [4],  # Pickle漏洞
    "25_Med_Border_K": [1],  # 医疗领域对K值敏感，边界值可能被判违规

    # --- Finance ---
    "31_Fin_Pass": [],
    "32_Fin_False_Alarm": [],  # 这是一个陷阱题，其实是合规的，看工具会不会误报
    "33_Fin_Fail_XAI": [5],  # 缺解释性 -> 透明度/DPIA(5)
    "34_Fin_Fail_Bias": [1],  # 偏见数据(Race) -> 最小化(1)
}


# ================= 2. 评估引擎 =================

class PrincipleEvaluator:
    def __init__(self):
        self.stats = {pid: {"TP": 0, "FP": 0, "FN": 0, "TN": 0} for pid in range(1, 6)}
        # === 关键修改：指向正确的文件夹 ===
        self.test_dir = "Test_Cases"

    class MockFile:
        def __init__(self, path):
            self.filename = os.path.basename(path)
            self.path = path

        def save(self, dst):
            import shutil
            shutil.copy(self.path, dst)

    def run(self):
        print(f"🚀 开始评估 5 大核心原则 (基于 {self.test_dir})...")

        if not os.path.exists(self.test_dir):
            print(f"❌ 错误：找不到文件夹 '{self.test_dir}'。请先运行 generate_realistic_cases.py")
            return

        for case_id, actual_violations in GROUND_TRUTH.items():
            case_path = os.path.join(self.test_dir, case_id)
            if not os.path.exists(case_path):
                continue

            # 1. 模拟文件
            files = []
            for f in os.listdir(case_path):
                files.append(self.MockFile(os.path.join(case_path, f)))

            # 2. 确定领域
            domain = "general"
            if "_Edu_" in case_id:
                domain = "education"
            elif "_Med_" in case_id:
                domain = "medical"
            elif "_Fin_" in case_id:
                domain = "finance"

            try:
                # 3. 核心检测
                ai_info = collect_multi_files_info(files, domain)

                # 必须调用新的 ai_act_risk_prejudge (它现在是独立的函数)
                risk_result = ai_act_risk_prejudge(ai_info)

                detection_result = check_privacy_compliance(ai_info, risk_result['risk_level'])

                # 4. 获取预测结果
                predicted_violations = []
                if detection_result and detection_result['details']:
                    for item in detection_result['details']:
                        if not item['compliant']:
                            predicted_violations.append(item['id'])

                self._update_matrix(case_id, actual_violations, predicted_violations)

            except Exception as e:
                print(f"❌ 用例 {case_id} 出错: {e}")

        self._print_report()

    def _update_matrix(self, case_id, actual_list, predicted_list):
        for pid in range(1, 6):
            is_actual = pid in actual_list
            is_pred = pid in predicted_list

            if is_actual and is_pred:
                self.stats[pid]["TP"] += 1
            elif not is_actual and not is_pred:
                self.stats[pid]["TN"] += 1
            elif not is_actual and is_pred:
                self.stats[pid]["FP"] += 1
                # print(f"   [FP 误报] {case_id} 原则{pid}") # 调试用
            elif is_actual and not is_pred:
                self.stats[pid]["FN"] += 1
                # print(f"   [FN 漏报] {case_id} 原则{pid}") # 调试用

    def _print_report(self):
        print("\n" + "=" * 65)
        print(f"{'Principle':<25} | {'Recall':<8} | {'Precision':<10} | {'F1-Score':<8}")
        print("-" * 65)

        p_names = {1: "Data Minimization", 2: "Consent", 3: "Sensitive Data", 4: "Security", 5: "DPIA/Accountability"}
        avg_rec, avg_prec = 0, 0

        for pid in range(1, 6):
            s = self.stats[pid]
            tp, fp, fn = s["TP"], s["FP"], s["FN"]

            rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
            prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
            f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

            print(f"{p_names[pid]:<25} | {rec:.1%}    | {prec:.1%}     | {f1:.1%}")
            avg_rec += rec
            avg_prec += prec

        print("-" * 65)
        print(f"Average: Recall={avg_rec / 5:.1%} , Precision={avg_prec / 5:.1%}")
        print("=" * 65)


if __name__ == "__main__":
    evaluator = PrincipleEvaluator()
    evaluator.run()