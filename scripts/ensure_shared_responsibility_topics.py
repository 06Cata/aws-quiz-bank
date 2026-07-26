#!/usr/bin/env python3
"""Ensure every CLF/SAA chapter ends with a shared-responsibility topic."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SUBJECTS = {
    "What is Cloud Computing?": "AWS Cloud",
    "AWS Identity & Access Management": "IAM",
    "AWS Identity & Access Management (AWS IAM)": "IAM",
    "Amazon EC2": "Amazon EC2",
    "Amazon EC2 – Basics": "Amazon EC2",
    "Amazon EC2 – Associate": "Advanced Amazon EC2",
    "Amazon EC2 Instance Storage": "EC2 Storage",
    "Amazon EC2 – Instance Storage": "EC2 Storage",
    "Elastic Load Balancing & Auto Scaling Group": "ELB and Auto Scaling",
    "High Availability & Scalability": "High Availability and Scalability",
    "Databases & Analytics": "Databases and Analytics",
    "RDS, Aurora & ElastiCache": "RDS, Aurora, and ElastiCache",
    "Deploying & Managing Infrastructure at Scale": "Infrastructure Deployment and Management",
    "Account Management, Billing, & Support": "Accounts, Billing, and Support",
    "AWS Architecting & EcoSystem": "AWS Architecture and Ecosystem",
    "White Papers & Architectures": "AWS Architectures and Best Practices",
}


def chapter_label(chapter_key: str) -> str:
    return chapter_key.split(":", 1)[1].strip()


def subject_for(label: str) -> str:
    return SUBJECTS.get(label, label.replace(" – Advanced", "").strip())


def details_for(label: str) -> tuple[str, str, str]:
    """Return AWS duty, customer duty, and a common exam distinction."""
    low = label.casefold()
    if "identity" in low or "iam" in low:
        return (
            "IAM 服務的底層基礎設施、可用性與服務安全",
            "建立與管理 users、groups、roles、policies、MFA、federation 與憑證，並落實最小權限及定期撤銷不再需要的存取",
            "AWS 不會替客戶決定誰應取得權限；過度授權、未啟用 MFA 或外洩 access keys 都屬於客戶責任",
        )
    if "instance storage" in low or "ec2 storage" in low or "storage extras" in low:
        return (
            "儲存服務的實體設備、底層基礎設施、故障硬體更換，以及服務承諾範圍內的資料複寫機制",
            "資料內容、存取權限、KMS 加密設定、snapshot／backup 排程、保留政策、復原測試，以及理解 Instance Store 的暫時性風險",
            "底層磁碟故障由 AWS 處理；是否建立備份、能否還原，以及誤刪資料的風險由客戶管理",
        )
    if "ec2" in low:
        return (
            "資料中心、實體伺服器、網路、儲存硬體與 hypervisor 等雲端底層基礎設施",
            "Guest OS 修補、Security Groups、IAM roles、已安裝軟體、應用程式、資料加密與備份",
            "EC2 是 IaaS；AWS 更換故障主機，但客戶仍要修補 EC2 內的作業系統與軟體",
        )
    if "s3" in low:
        return (
            "S3 的實體基礎設施、服務可用性與耐久性機制，以及底層硬體維護",
            "objects 與資料分類、bucket／IAM policies、Block Public Access、加密選項、versioning、replication 與 lifecycle 設定",
            "AWS 保護 S3 服務本身；bucket 意外公開、未啟用所需版本控制或錯誤刪除 objects 通常是客戶責任",
        )
    if any(term in low for term in ("rds", "database", "data & analytics", "data and analytics")):
        return (
            "受管資料庫與分析服務的底層硬體、服務軟體、故障替換，以及各服務承諾範圍內的修補與可用性",
            "資料、schema、帳號權限、網路存取、加密、備份保留期、容量與高可用設定；若資料庫裝在 EC2，客戶還要管理資料庫引擎與 OS",
            "題目先判斷是受管資料庫還是 EC2 自管資料庫；受管程度越高，AWS 承擔的作業越多，但資料與存取永遠由客戶負責",
        )
    if any(term in low for term in ("load balancing", "scalability", "availability")):
        return (
            "ELB、Auto Scaling 控制平面及其底層基礎設施的可用性、修補與擴展",
            "listener、target group、health check、launch template、minimum／desired／maximum capacity、跨 AZ 設計與應用程式可擴展性",
            "AWS 維運 ELB／ASG 服務，但不會替客戶選擇正確的 health check、容量上下限或修復無法水平擴展的應用程式",
        )
    if "route 53" in low or "cloudfront" in low or "global accelerator" in low or "global infrastructure" in low:
        return (
            "全球網路、edge／DNS／加速服務的底層設施、服務可用性與硬體維護",
            "DNS records、routing policies、origins、cache／TLS／存取設定、health checks，以及資料與應用程式本身的安全",
            "AWS 維運全球基礎設施；錯誤 DNS、公開 origin、錯誤路由或未保護內容屬於客戶設定責任",
        )
    if "vpc" in low:
        return (
            "AWS 全球網路、實體路由與 VPC 服務底層的隔離、可用性及硬體維護",
            "CIDR、subnets、route tables、Security Groups、NACLs、endpoints、VPN／Direct Connect 邏輯設定與流量監控",
            "AWS 保護網路基礎設施；允許 0.0.0.0/0、錯誤路由或過寬 firewall rules 是客戶責任",
        )
    if any(term in low for term in ("integration", "messaging")):
        return (
            "SQS、SNS、EventBridge、Kinesis 等受管整合服務的基礎設施、服務修補與可用性",
            "queue／topic／event bus policies、加密、retention、DLQ、consumer 錯誤處理、資料內容及 least-privilege 存取",
            "AWS 確保受管服務運作；訊息是否被正確授權、處理、重試或送入 DLQ 由客戶設計",
        )
    if "container" in low:
        return (
            "ECS／EKS／ECR／Fargate 受管控制平面與底層服務基礎設施；Fargate 另負責執行工作節點的 OS",
            "container images、應用程式依賴、task／pod IAM、secrets、network policies、日誌，以及 EC2 launch type 的 worker nodes",
            "Fargate 不代表應用程式完全免管理；映像漏洞、容器權限與資料安全仍是客戶責任",
        )
    if "serverless" in low:
        return (
            "Lambda、API Gateway、Step Functions 等受管服務的伺服器、OS、runtime 基礎設施與自動擴展平台",
            "程式碼、dependencies、IAM execution roles、API authorization、資料、secrets、timeout／concurrency 與 workflow 錯誤處理",
            "Serverless 免除伺服器管理，不會免除程式碼、權限、資料及安全設定責任",
        )
    if "monitor" in low or "audit" in low:
        return (
            "CloudWatch、CloudTrail、Config 等監控與稽核服務的平台、底層儲存與服務可用性",
            "啟用所需 logs／trails／rules、設定保留與加密、建立 alarms、限制 log access，並實際回應告警與調查事件",
            "AWS 提供監控工具，但不會自動替客戶開啟所有紀錄、設定正確門檻或處理告警",
        )
    if "security" in low or "encryption" in low:
        return (
            "雲端底層安全，以及 KMS、Shield、WAF、GuardDuty 等安全服務本身的可用性與基礎設施",
            "資料分類、keys 與 policies 的使用方式、偵測服務啟用範圍、告警回應、修復弱點及合規決策",
            "AWS 提供安全能力與合規文件；客戶仍要正確設定、監看發現結果並保護自己的資料與身分",
        )
    if "machine learning" in low:
        return (
            "SageMaker 與各項 AI 服務的受管基礎設施、平台修補與服務可用性",
            "訓練／推論資料、模型、notebooks、IAM roles、network isolation、加密、輸出品質與負責任 AI 使用",
            "AWS 維運 ML 平台；資料合法性、模型結果、權限與商業決策仍由客戶負責",
        )
    if "migration" in low or "disaster recovery" in low:
        return (
            "遷移與復原服務的底層平台、硬體、服務可用性及受管元件",
            "選擇 RPO／RTO、資料一致性、複寫與 cutover 設定、備份保留、權限、網路及定期復原演練",
            "AWS 提供遷移與 DR 工具，但成功切換、資料驗證和是否達到企業 RPO／RTO 是客戶責任",
        )
    if any(term in low for term in ("billing", "account", "support")):
        return (
            "帳務、Organizations 與 Support 服務平台的可用性、計費資料處理及底層安全",
            "帳戶結構、SCP／IAM、付款資料、Budgets／alerts、成本標籤、資源使用與收到告警後的處置",
            "AWS 提供帳單與成本工具，但不會自動停止所有超支資源；客戶要設定門檻並採取行動",
        )
    if any(term in low for term in ("deploy", "infrastructure", "other services")):
        return (
            "CloudFormation、Beanstalk、Systems Manager 等受管部署與管理服務的底層平台和可用性",
            "templates、application code、service roles、parameters／secrets、變更審查、部署設定與服務建立之資源的安全",
            "受管部署工具會依客戶宣告執行；template 錯誤、過大的 role 或部署後資源設定仍是客戶責任",
        )
    return (
        "AWS Cloud 的資料中心、實體硬體、全球網路、虛擬化層與受管服務底層平台",
        "資料、身分與權限、服務組態、加密、備份、應用程式，以及依業務需求選擇並正確使用 AWS 服務",
        "考題先判斷 Security OF the Cloud 與 Security IN the Cloud；AWS 管底層，客戶管資料、存取與設定",
    )


def is_responsibility_card(title: str) -> bool:
    low = title.casefold()
    return "responsibility" in low or "security of" in low or "security in" in low


def is_roleplay_topic(topic: str) -> bool:
    low = topic.casefold()
    return topic.startswith("角色扮演") or "role-play" in low or "roleplay" in low


def normalize_existing_topics(chapter_key: str, topics: dict, new_topic: str) -> dict:
    moved: dict = {}
    for topic_name in list(topics):
        if topic_name == new_topic:
            moved.update(topics.pop(topic_name))
            continue
        if "responsib" not in topic_name.casefold():
            continue
        cards = topics[topic_name]
        for title in list(cards):
            if is_responsibility_card(title):
                moved[title] = cards.pop(title)
        if not cards:
            del topics[topic_name]
        elif topic_name == "Database Fundamentals and Responsibility":
            topics["Database Fundamentals"] = topics.pop(topic_name)
        elif topic_name == "Shared Responsibility and Compliance":
            topics["Compliance Resources"] = topics.pop(topic_name)
        elif topic_name == "IAM Security and Responsibility":
            topics["IAM Auditing Tools"] = topics.pop(topic_name)
    return moved


def ensure_exam(exam: str) -> tuple[int, int]:
    source = ROOT / "flashcards_sources" / f"{exam}_flashcards.json"
    data = json.loads(source.read_text())
    added_topics = 0
    added_cards = 0
    for chapter_key, topics in data.items():
        label = chapter_label(chapter_key)
        subject = subject_for(label)
        topic_name = f"Shared Responsibility for {subject}"
        roleplay_topics = [
            (name, topics.pop(name))
            for name in list(topics)
            if is_roleplay_topic(name)
        ]
        existing = normalize_existing_topics(chapter_key, topics, topic_name)
        domain = next(iter(next(iter(topics.values())).values()))["Domain"]
        aws_duty, customer_duty, exam_cue = details_for(label)
        has_aws = any("security of" in title.casefold() or title.casefold().startswith("aws responsibility") for title in existing)
        has_customer = any("security in" in title.casefold() or title.casefold().startswith("customer responsibility") for title in existing)
        if not has_aws:
            existing[f"AWS Responsibility – Security OF {subject}"] = {
                "Domain": domain,
                "Description": f"AWS 負責 {aws_duty}。這是 Security OF the Cloud。常見考法：{exam_cue}。",
            }
            added_cards += 1
        if not has_customer:
            existing[f"Customer Responsibility – Security IN {subject}"] = {
                "Domain": domain,
                "Description": f"客戶負責 {customer_duty}。這是 Security IN the Cloud。常見考法：{exam_cue}。",
            }
            added_cards += 1
        topics[topic_name] = existing
        for roleplay_name, roleplay_cards in roleplay_topics:
            topics[roleplay_name] = roleplay_cards
        added_topics += 1
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    for directory in ("flashcards_sources", "flashcards"):
        (ROOT / directory / f"{exam}_flashcards.json").write_text(rendered)
    return added_topics, added_cards


def main() -> None:
    for exam in ("clf", "saa"):
        topics, cards = ensure_exam(exam)
        print(f"{exam.upper()}: responsibility_topics={topics}, added_cards={cards}")


if __name__ == "__main__":
    main()
