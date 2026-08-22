#!/usr/bin/env python3
"""Normalize SAA option explanations and replace uninformative templates.

The source set contains mostly useful technical explanations, but a small subset
was generated with generic phrases such as "cannot meet the constraints".  This
script preserves useful prose, standardizes the Chinese prefix, and expands the
generic subset with the option's actual AWS purpose and a question-level
comparison.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTION_DIR = ROOT / "questions"

GENERIC_PHRASES = (
    "该解决方案无法同时满足问题中的关键性能、可用性、安全性、成本或运维约束",
    "该解决方案无法同时满足问题中的关键性能、可用性、安全性、成本或操作约束",
    "该解决方案能够满足问题中的关键功能和非功能需求",
    "该解决方案满足问题中的关键功能和非功能需求",
    "与相关AWS服务的设计目的和最佳实践",
    "与相关AWS服务的设计意图和最佳实践",
    "因此不是最佳选择",
    "完全满足题目要求",
    "功能不匹配，不能满足题目要求",
    "此方案會依選項所述配置資源與資料流程",
)

# Ordered from specific products/features to broader products.  A generated
# explanation can combine up to three matching descriptions for compound options.
SERVICE_PURPOSES = (
    ("智能分层生命周期", "S3 Intelligent-Tiering 會依實際存取模式自動調整儲存層，適合存取頻率難以預測的物件"),
    ("S3 Standard", "S3 Standard 提供毫秒級物件存取與跨多個可用區的高韌性，適合經常讀取的資料"),
    ("S3 Glacier Deep Archive", "S3 Glacier Deep Archive 用於最低成本的長期封存，但取回通常需數小時，不能當作即時存取層"),
    ("S3 Glacier 灵活检索", "S3 Glacier Flexible Retrieval 用於低成本封存，標準或大量取回並非即時"),
    ("S3 Glacier Instant Retrieval", "S3 Glacier Instant Retrieval 適合很少讀取、但需要毫秒級取回的封存物件"),
    ("S3 标准-IA", "S3 Standard-IA 適合較少存取但仍需毫秒級讀取的資料，會收取取回費"),
    ("S3 智能分层", "S3 Intelligent-Tiering 會依存取模式自動移動物件，以降低難以預測之資料的儲存成本"),
    ("S3 多区域接入点", "S3 Multi-Region Access Point 以單一全域端點將請求路由到多個區域的 S3 儲存桶"),
    ("S3 对象锁", "S3 Object Lock 以 WORM 保留機制防止物件在保留期內被刪除或覆寫"),
    ("S3 版本控制", "S3 Versioning 保留物件的多個版本，可從誤刪或覆寫中復原"),
    ("CloudFront", "CloudFront 是全球內容傳遞網路，會在邊緣快取內容以降低使用者延遲與來源負載"),
    ("Global Accelerator", "AWS Global Accelerator 以 AWS 全球網路和靜態 Anycast IP 將 TCP/UDP 流量導向健康的區域端點"),
    ("Route 53", "Route 53 提供 DNS 與健康檢查，可依延遲、地理位置或容錯政策路由流量"),
    ("API Gateway", "API Gateway 用於建立、保護與管理 HTTP、REST 或 WebSocket API"),
    ("AP！", "API Gateway usage plan 可為 API 金鑰設定配額與節流，控制用戶端的 API 呼叫量，但不提供交易工作佇列"),
    ("Application Load Balancer", "Application Load Balancer 在第 7 層依主機、路徑或查詢條件分配 HTTP/HTTPS 流量"),
    ("应用程序负载均衡器", "Application Load Balancer 在第 7 層依主機、路徑或查詢條件分配 HTTP/HTTPS 流量"),
    ("网络负载均衡器", "Network Load Balancer 在第 4 層以高效能處理 TCP、UDP 或 TLS 流量"),
    ("NLB", "Network Load Balancer 在第 4 層處理 TCP、UDP 或 TLS 流量；安全群組或來源 IP allowlist 可限制可連線的來源"),
    ("AWS WAF", "AWS WAF 依 Web ACL 規則篩選 HTTP(S) 請求，可封鎖常見 Web 攻擊或限制請求速率"),
    ("Shield Advanced", "AWS Shield Advanced 提供進階 DDoS 偵測、緩解與成本保護，但不是一般應用授權服務"),
    ("Auto Scaling", "EC2 Auto Scaling 會依指標或排程調整執行個體數量，以維持容量與可用性"),
    ("预测性扩展", "Predictive Scaling 依歷史模式預測需求並提前擴充容量，適合可預測的週期性尖峰"),
    ("定期计划操作", "Scheduled Scaling 在已知時間直接調整容量，適合時間固定且可預測的尖峰"),
    ("Fargate Spot", "Fargate Spot 使用可中斷的閒置容量降低成本，適合可容錯的工作，不宜單獨承載穩定基線"),
    ("Fargate", "AWS Fargate 讓 ECS 或 EKS 容器無須管理底層伺服器即可執行"),
    ("托管节点组", "EKS managed node group 代管 Kubernetes 工作節點的佈建與更新；On-Demand 適合穩定基線，Spot 適合可中斷的彈性容量"),
    ("受管节点组", "EKS managed node group 代管 Kubernetes 工作節點的佈建與更新；On-Demand 適合穩定基線，Spot 適合可中斷的彈性容量"),
    ("竞价型实例", "EC2 Spot Instances 使用可能被中斷的閒置容量換取折扣，適合可重試或可容錯工作"),
    ("Karpenter", "Karpenter 會依 Kubernetes Pod 需求快速佈建合適的運算節點"),
    ("EKS", "Amazon EKS 是受管 Kubernetes 服務，用於部署與操作容器化工作負載"),
    ("ECS", "Amazon ECS 是 AWS 原生的受管容器協調服務"),
    ("Elastic Beanstalk", "Elastic Beanstalk 代管 Web 應用程式平台的佈署、容量調整與健康監控"),
    ("Lambda", "AWS Lambda 以事件驅動方式執行程式碼，無須管理伺服器，適合短時間、可水平擴展的工作"),
    ("SQS FIFO", "SQS FIFO 佇列保留訊息順序並支援去重，適合順序與重複處理控制很重要的工作"),
    ("SQS", "Amazon SQS 是受管訊息佇列，可緩衝流量尖峰並解耦生產者與非同步工作者"),
    ("SNS", "Amazon SNS 是發布／訂閱通知服務，適合把同一訊息扇出給多個訂閱者，不是資料庫或快取"),
    ("EventBridge", "Amazon EventBridge 依事件模式把事件路由到目標服務，用於事件整合而非保存主要業務資料"),
    ("Kinesis Data Firehose", "Kinesis Data Firehose 將串流資料持續交付到 S3、Redshift、OpenSearch 等目的地"),
    ("Kinesis 数据流", "Kinesis Data Streams 用於即時擷取及處理高吞吐串流事件"),
    ("Amazon MSK", "Amazon MSK 是受管 Apache Kafka，適合需要 Kafka 相容性的事件串流平台"),
    ("ElastiCache", "Amazon ElastiCache 將常用資料放在記憶體中，以降低資料庫讀取延遲與負載"),
    ("RDS 代理", "RDS Proxy 會集區化並重用資料庫連線，保護資料庫免受大量短連線衝擊"),
    ("多可用区", "RDS Multi-AZ 維護同步待命資源並自動容錯，主要目的為高可用性而非擴充讀取"),
    ("只读副本", "RDS Read Replica 以非同步複寫分擔唯讀查詢，主要用於讀取擴展而非自動高可用容錯"),
    ("Amazon RDS", "Amazon RDS 是受管關聯式資料庫，AWS 負責常見修補、備份與基礎維運"),
    ("Aurora", "Amazon Aurora 是與 MySQL／PostgreSQL 相容的受管關聯式資料庫，提供分散式儲存與高可用性"),
    ("DynamoDB", "DynamoDB 是無伺服器 NoSQL 鍵值與文件資料庫，可自動擴展並提供低延遲存取"),
    ("Redshift Spectrum", "Redshift Spectrum 可直接以 SQL 查詢 S3 中的資料，而不必先全部載入 Redshift"),
    ("Redshift", "Amazon Redshift 是用於分析型 SQL 與資料倉儲工作負載的服務"),
    ("Neptune Streams", "Neptune Streams 以有序變更日誌提供圖形資料庫的變更資料擷取"),
    ("Neptune", "Amazon Neptune 是受管圖形資料庫，適合遍歷高度連結的關係資料"),
    ("Athena", "Amazon Athena 是無伺服器互動式查詢服務，可直接用 SQL 分析 S3 資料"),
    ("EFS One Zone", "EFS One Zone 將資料放在單一可用區，成本較低但不具跨可用區韌性"),
    ("EFS", "Amazon EFS 提供可由多個 Linux 運算資源同時掛載的彈性 NFS 檔案系統"),
    ("FSx for Windows", "FSx for Windows File Server 提供受管 SMB 檔案共享並可整合 Microsoft Active Directory"),
    ("FSx for Lustre", "FSx for Lustre 是高吞吐、低延遲的平行檔案系統，常用於 HPC 與資料處理，並可連結 S3"),
    ("FSx for OpenZFS", "FSx for OpenZFS 提供受管 NFS 共用檔案系統與 ZFS 快照、複製等能力"),
    ("FSx for NetApp ONTAP", "FSx for NetApp ONTAP 提供多協定、快照、複寫與分層等企業級共享儲存能力"),
    ("EBS", "Amazon EBS 提供附加至 EC2 的持久區塊儲存；快照可用於備份與跨區域複製"),
    ("Data Lifecycle Manager", "Amazon Data Lifecycle Manager 依政策自動建立、保留與刪除 EBS 快照，降低手動維護工作"),
    ("Mountpoint for Amazon S3", "Mountpoint for Amazon S3 讓高吞吐應用以檔案介面存取 S3，但不提供完整 POSIX 檔案系統語意"),
    ("S3 文件网关", "S3 File Gateway 以 NFS／SMB 介面讓內部部署應用存取 S3，並在本地快取常用資料"),
    ("Storage Gateway", "AWS Storage Gateway 將內部部署環境以檔案、磁碟區或虛擬磁帶介面連接 AWS 儲存"),
    ("DataSync", "AWS DataSync 會加速並自動驗證內部部署與 AWS 儲存服務之間的線上資料傳輸"),
    ("Transfer Family", "AWS Transfer Family 提供受管 SFTP、FTPS 與 FTP 端點，後端可使用 S3 或 EFS"),
    ("AWS Backup", "AWS Backup 以集中式政策排程、保留並稽核多種 AWS 資源的備份"),
    ("SSE-S3", "SSE-S3 使用由 Amazon S3 完全管理並自動輪換的金鑰進行伺服器端加密"),
    ("SSE-KMS", "SSE-KMS 使用 AWS KMS 金鑰加密資料，提供較細緻的權限與稽核控制"),
    ("外部密钥存储", "KMS External Key Store 讓 KMS 使用位於 AWS 外部之金鑰管理器中的金鑰材料"),
    ("CloudHSM", "AWS CloudHSM 提供客戶控制的專用 HSM，但 HSM 仍部署在 AWS 雲端中"),
    ("AWS KMS", "AWS KMS 是受管金鑰管理服務，用於建立、控制與稽核加密金鑰的使用"),
    ("GuardDuty", "Amazon GuardDuty 會分析 CloudTrail、VPC Flow Logs、DNS 與部分工作負載訊號，以偵測威脅與惡意活動"),
    ("Macie", "Amazon Macie 使用機器學習探索並分類 S3 中的敏感資料，也能發現部分 S3 安全風險"),
    ("Inspector", "Amazon Inspector 持續掃描 EC2、容器映像與 Lambda 的軟體漏洞及非預期網路曝露"),
    ("Security Hub", "AWS Security Hub 集中彙整安全發現並以標準控制提供跨帳戶安全態勢儀表板"),
    ("AWS Config", "AWS Config 記錄資源組態與歷史變更，並以規則評估組態合規性"),
    ("CloudTrail", "AWS CloudTrail 記錄帳戶中的 AWS API 活動，供稽核、調查與事件追蹤"),
    ("VPC 流程日志", "VPC Flow Logs 記錄網路介面的允許與拒絕流量中繼資料，可送到 CloudWatch Logs 建立指標與警報"),
    ("CloudWatch", "Amazon CloudWatch 收集指標與日誌，並以警報在條件成立時觸發通知或自動化動作"),
    ("Trusted Advisor", "AWS Trusted Advisor 依最佳實務檢查成本、效能、韌性與安全性，主要提供建議而非即時強制控制"),
    ("Organizations", "AWS Organizations 集中管理多個 AWS 帳戶，並可用 SCP 設定帳戶可取得權限的上限"),
    ("服务控制策略", "Service Control Policy 為組織帳戶設定最大可用權限，不會自行授予 IAM 權限"),
    ("SCP", "Service Control Policy 為組織帳戶設定最大可用權限，不會自行授予 IAM 權限"),
    ("Resource Access Manager", "AWS RAM 用於跨帳戶共享支援的 AWS 資源，例如子網路與 Transit Gateway"),
    ("Control Tower", "AWS Control Tower 建立並治理多帳戶 landing zone，透過控制措施維持組織標準"),
    ("CloudFormation", "AWS CloudFormation 以範本一致且可重複地佈建基礎設施"),
    ("IAM Identity Center", "IAM Identity Center 集中管理人員對多個 AWS 帳戶與應用程式的單一登入及 permission sets"),
    ("AWS Budgets", "AWS Budgets 依成本或用量門檻發送警示，並可觸發預先設定的成本控制動作"),
    ("成本分配标签", "成本分配標籤可把 AWS 費用歸屬到擁有者、專案或成本中心"),
    ("Compute Optimizer", "AWS Compute Optimizer 依使用指標提出資源規格最佳化建議"),
    ("SageMaker 终端节点", "SageMaker endpoint 用於託管模型並提供即時推論 API"),
    ("SageMaker", "Amazon SageMaker 提供建置、訓練與部署機器學習模型的受管工具"),
    ("Amazon Forecast", "Amazon Forecast 使用時間序列資料建立預測器，用於需求等數值預測"),
    ("Amazon Forsecast", "Amazon Forecast 使用 S3 中的歷史時間序列資料訓練預測器，用於需求等數值預測"),
    ("Amazon Transcribe", "Amazon Transcribe 將語音轉成文字，並可設定部分個資遮蔽功能"),
    ("Comprehend", "Amazon Comprehend 使用 NLP 從文字擷取實體、關鍵片語、情緒與主題"),
    ("QuickSight", "Amazon QuickSight 是受管商業智慧服務，用於建立互動式分析與儀表板"),
    ("DataBrew", "AWS Glue DataBrew 以視覺化方式清理與轉換資料，減少撰寫資料準備程式碼"),
    ("AppSync", "AWS AppSync 提供受管 GraphQL API，解析器可組合多個資料來源與步驟"),
    ("Certificate Manager", "AWS Certificate Manager 佈建與續期 TLS 憑證，用於加密連線；它不負責更新或清除網站快取"),
    ("点播模式", "DynamoDB on-demand mode 會依請求自動調整容量並按請求付費，不能同時指定預留的 RCU 與 WCU"),
    ("配置模式", "DynamoDB provisioned mode 由使用者指定 RCU 與 WCU，適合可預測的流量"),
    ("Transit Gateway", "AWS Transit Gateway 以中心輻射架構連接大量 VPC 與內部網路，規模化管理容易但少量 VPC 成本可能較高"),
    ("站点到站点 VPN", "Site-to-Site VPN 透過網際網路建立加密 IPsec 隧道，主要連接 VPC 與外部網路"),
    ("VPC 对等连接", "VPC Peering 以 AWS 網路直接連接兩個 VPC，適合少量、非轉送式的點對點連線"),
    ("VPC对等连接", "VPC Peering 以 AWS 網路直接連接兩個 VPC，適合少量、非轉送式的點對點連線"),
    ("Direct Connect", "AWS Direct Connect 提供內部網路到 AWS 的專線，不是直接建立兩個 VPC 間連線的最低成本方式"),
    ("安全组", "Security group 是具狀態的虛擬防火牆，以來源、通訊協定與連接埠控制資源流量"),
    ("跨区域复制", "S3 Cross-Region Replication 會非同步複寫 S3 物件到另一區域，但不會直接建立或持續複寫關聯式資料庫"),
    ("CRR", "S3 Cross-Region Replication 會非同步複寫 S3 物件到另一區域，但不會直接建立或持續複寫關聯式資料庫"),
    ("内存优化实例", "Memory Optimized instance 適合記憶體密集工作；是否正確仍取決於瓶頸位於應用層或資料庫層"),
)


SPECIAL_OVERRIDES: dict[tuple[int, str], str] = {
    (61, "D"): "AWS Systems Manager Parameter Store 可安全保存設定值與機密，並能使用 KMS 加密；但它沒有 Secrets Manager 的內建資料庫憑證輪換流程，需自行以 Lambda 或其他程序實作輪換，因此營運工作較多。",
    (91, "B"): "S3 是區域性的物件儲存服務，不能被部署到某個私有子網路中；私有 EC2 要在不經網際網路的情況下存取 S3，應建立 S3 Gateway VPC Endpoint。",
    (97, "A"): "Amazon EFS 提供 Linux 常用的 NFS 共用檔案系統；題目需要 Windows SharePoint 使用的 SMB、Microsoft AD 整合與 Windows 檔案伺服器能力，因此應選 FSx for Windows File Server。",
    (384, "A"): "S3 Standard 搭配 Lifecycle 可把較舊物件轉到 Glacier 以降低成本，但 S3 是物件儲存，不提供題目要求的共享 POSIX 檔案系統介面；應使用跨可用區的 EFS Standard 與 EFS Standard-IA。",
    (386, "A"): "Amazon SNS 是發布／訂閱通知服務，用來把訊息扇出給多個訂閱者，不會保存並重用資料庫查詢結果；本題需要 ElastiCache 以記憶體快取重複查詢。",
    (386, "B"): "Amazon ElastiCache 將熱門查詢結果或資料集保存在記憶體中，可直接回覆重複查詢並降低 RDS 負載與延遲，正符合本題的讀取模式。",
    (386, "C"): "RDS Read Replica 以非同步複寫分擔唯讀查詢，能擴充資料庫讀取容量，但每次仍需執行 SQL；本題大量重複且相同的查詢用 ElastiCache 避免重新運算更合適。",
    (386, "D"): "Kinesis Data Firehose 用於把串流事件持續交付到 S3、Redshift 或 OpenSearch 等目的地，不是資料庫查詢快取，無法加速重複 SQL 查詢。",
    (419, "A"): "在單一帳戶啟用預設 EBS 加密只影響該帳戶及區域中新建的磁碟區，無法集中強制整個 AWS Organizations 組織遵守政策。",
    (419, "B"): "Permissions boundary 限制單一 IAM 身分可取得的最大權限，不能直接附加到組織 Root 或 OU 來治理所有成員帳戶。",
    (419, "C"): "SCP 可在 AWS Organizations 層級拒絕建立未加密 EBS 磁碟區，為所有套用帳戶建立不可越過的權限護欄。",
    (419, "D"): "逐一在各帳戶建立 IAM 政策可以限制部分身分，但容易遺漏且維護成本高；SCP 才能在組織層級一致強制政策。",
    (419, "E"): "以 AWS Organizations 集中啟用 EBS encryption by default，可讓成員帳戶的新 EBS 磁碟區預設加密，搭配 SCP 防止規避設定。",
    (431, "A"): "ElastiCache for Memcached 提供簡單的分散式記憶體快取，但不支援 Redis sorted set 等排行榜資料結構，也不提供資料持久化；停止後無法可靠保留分數。",
    (431, "B"): "ElastiCache for Redis 提供 sorted set，可低延遲更新與排序即時比分，並支援快照或複寫保存資料，符合恢復後保留分數的要求。",
    (431, "C"): "CloudFront 快取並傳遞 Web 內容，可降低全球讀取延遲，但不負責計算、排序或持久保存持續變動的球賽比分。",
    (431, "D"): "查詢資料庫唯讀副本可以分擔讀取，但高頻率更新及即時排行榜查詢仍會產生較高延遲與成本；Redis 的記憶體資料結構更適合此工作。",
    (576, "A"): "API Gateway Private endpoint 只能從指定 VPC 經 Interface VPC Endpoint 私下存取，適合內部 API，不適合全球公網使用者。",
    (576, "B"): "API Gateway Regional endpoint 服務單一區域，適合由客戶自行搭配 CloudFront 或服務區域內客戶；它本身不提供 edge-optimized endpoint 的全球邊緣入口。",
    (576, "C"): "Interface VPC Endpoint 透過 PrivateLink 提供 VPC 到服務的私有連線，不是面向全球公網使用者的低延遲 API 發佈方式。",
    (576, "D"): "API Gateway edge-optimized endpoint 會透過 AWS 管理的 CloudFront 分佈，從鄰近邊緣站點接收全球用戶請求，適合本題的全球 API。",
    (580, "A"): "FSx for Lustre 是高效能平行檔案系統，適合 HPC 與大量資料處理；題目是直接搬移需要本機區塊儲存語意的應用，採 EBS gp3 變更較少且成本更低。",
    (580, "B"): "EBS gp2 是通用 SSD 區塊儲存，但效能與容量綁定；gp3 可獨立設定 IOPS 與吞吐量，通常能以較低成本達到同樣需求。",
    (580, "C"): "FSx for OpenZFS 是受管共享 NFS 檔案系統，會把原本的本機附加儲存改成網路檔案架構；題目要求低延遲 lift-and-shift，EBS gp3 更直接。",
    (580, "D"): "EBS gp3 為 EC2 提供持久、低延遲的通用 SSD 區塊儲存，且 IOPS／吞吐量可與容量分開調整，符合低成本 lift-and-shift。",
    (616, "A"): "Amazon Macie 主要探索與分類 S3 敏感資料；AWS Config 則記錄組態與合規狀態。兩者都不是用來偵測帳戶、工作負載及 S3 存取中的惡意活動。",
    (616, "B"): "Amazon Inspector 掃描 EC2、容器映像與 Lambda 的漏洞；CloudTrail 記錄 API 活動但不是集中安全發現儀表板，因此不符合持續威脅偵測需求。",
    (616, "C"): "Amazon GuardDuty 分析 CloudTrail、VPC Flow Logs、DNS 與工作負載訊號來偵測威脅；Security Hub 集中顯示與彙整發現，兩者正好涵蓋監控與儀表板。",
    (616, "D"): "AWS Config 監控資源組態與合規，EventBridge 負責事件路由；兩者本身不會分析行為訊號來判斷惡意活動，也不提供完整威脅儀表板。",
    (617, "A"): "FSx for Lustre 是 HPC 用高效能平行檔案系統，不是一般 NFS 共用資料的最直接遷移目的地；題目需要可由多個 AWS 資源掛載的 EFS。",
    (617, "B"): "Amazon EFS 提供可由多個 AWS 運算資源同時掛載的受管 NFS 檔案系統，符合現有 NFS 工作負載的目的地需求。",
    (617, "C"): "Amazon S3 是物件儲存，使用物件 API 而不是原生 NFS 檔案系統語意；直接改用 S3 會要求應用程式變更。",
    (617, "D"): "作業系統複製命令可一次搬移檔案，但缺少 DataSync 的增量同步、驗證、重試與排程，持續有新資料時容易中斷或遺漏。",
    (617, "E"): "AWS DataSync agent 可從內部 NFS 進行加速、增量且具驗證的線上傳輸，搭配 EFS 能在來源持續運作時完成遷移。",
    (645, "A"): "AWS CloudHSM 提供客戶控制的專用 HSM，但設備與金鑰材料仍位於 AWS 雲端，不符合金鑰必須保留在外部廠商管理器的要求。",
    (645, "B"): "AWS KMS External Key Store 讓 KMS 操作由 AWS 外部的第三方金鑰管理器提供金鑰材料，並保留 KMS API 整合，符合外部託管與低維運要求。",
    (645, "C"): "AWS KMS 的預設或 AWS 受管金鑰由 AWS KMS 內部管理，金鑰材料不位於公司指定的外部金鑰管理器。",
    (645, "D"): "在每個供應商旁部署 CloudHSM 會增加硬體、叢集與整合維運，且 CloudHSM 仍是 AWS 內的 HSM，不是 KMS External Key Store。",
    (662, "C"): "刪除目前過期或未使用的 EBS 快照只能一次性降低費用，之後仍可能持續累積；Data Lifecycle Manager 能依保留政策自動建立及刪除快照，營運工作量更低。",
    (704, "D"): "在多個區域各自啟動遊戲伺服器可增加地理覆蓋，但選項沒有提供適合每秒數百萬 UDP 請求的負載分配層，且跨區域重複容量成本較高；NLB 可直接高效處理 UDP。",
    (759, "A"): "S3 Lifecycle 可依物件年齡自動轉層，適合存取模式與時間一致的資料；但題目已能依新舊影片直接分類，將舊片放 Standard-IA 可確保毫秒級播放並避免不必要流程。",
    (759, "B"): "新影片放 S3 Standard 可承受頻繁播放，舊影片放 Standard-IA 可降低儲存費且仍提供毫秒級取回，能在 5 分鐘內開始串流。",
    (759, "C"): "Glacier Flexible Retrieval 的 expedited retrieval 雖可能在數分鐘取回，但會增加取回成本與容量限制；Standard-IA 原生毫秒級存取更簡單可靠。",
    (759, "D"): "Glacier Flexible Retrieval 的 bulk retrieval 通常需要數小時，無法保證使用者訂購後 5 分鐘內開始播放。",
    (878, "A"): "讓多個人共用根使用者信箱會擴大高權限帳戶的存取面與稽核風險；根帳戶通知應集中管理，再透過 alternate contacts 分流。",
    (878, "B"): "分別使用各部門郵件清單雖可分流訊息，但若直接作為根使用者信箱會缺少單一受控入口與集中治理。",
    (878, "C"): "把根使用者電子郵件綁定某位員工會形成單人依賴，員工異動時也可能失去關鍵通知或帳戶復原能力。",
    (878, "D"): "以受控的中央別名作為根使用者信箱，並把 billing、security、operations alternate contacts 設為各職能群組，可安全分流通知且避免單人依賴。",
    (883, "A"): "依標籤觸發自訂 Lambda 可以停止或限制資源，但需自行維護標籤規則、程式與例外處理，營運工作量較高。",
    (883, "B"): "AWS Budgets 可在開發帳戶接近成本門檻時告警，Budgets Actions 可套用 DenyAllIAMAccess 等控制，自動阻止繼續產生費用且維運較少。",
    (883, "C"): "Cost Explorer 與報表可分析歷史花費，但主要是可視化與追蹤，不會在達到預算時自動阻止資源繼續產生成本。",
    (883, "D"): "Service Catalog 可限制可部署的核准產品，但逐帳戶建立排程 Lambda 仍需維護，且不能像 Budgets Actions 一樣直接依實際費用門檻採取控制。",
    (928, "A"): "AWS WAF 只能檢查 HTTP(S) 第 7 層請求，不能直接附加到處理一般 TCP 流量的 Network Load Balancer，因此這個 Web ACL 架構不可行。",
    (928, "B"): "NLB security group 可依來源 IP 與連接埠限制 TCP 流量；但若既有 NLB 建立時未關聯安全群組，之後不能直接補加，重建並切換 NLB 不符合最小架構變更。",
    (928, "C"): "平行建立第二個 NLB 並設定 IP allowlist 能限制來源，但需新增負載平衡器、切換流量並維護兩套資源，架構變更與營運成本都較高。",
    (928, "D"): "AWS Shield Advanced 可在不更換既有 NLB 的情況下加強網路與傳輸層 DDoS 偵測及緩解；依本題將未授權嘗試視為 DDoS 型流量的設定，這是列出的正確方案，但它不是一般使用者身分驗證服務。",
    (1003, "D"): "自行維護本地檔案伺服器並以 S3 API 存取後端資料，需要開發同步、快取與失敗處理，也增加伺服器維運；S3 File Gateway 已提供受管 NFS／SMB 介面與本地快取。",
}


def strip_prefix(text: str, status: str) -> str:
    text = text.strip()
    if text.startswith(status):
        text = text[len(status):].lstrip()
    text = re.sub(r"^(?:技術原因|技术原因|原因是|原因|分析|理由)\s*[：，,:]?\s*", "", text)
    return text.strip()


def is_generic(reason: str) -> bool:
    return len(reason) < 25 or any(phrase in reason for phrase in GENERIC_PHRASES)


def matched_purposes(option_text: str) -> list[str]:
    found: list[str] = []
    for token, purpose in SERVICE_PURPOSES:
        if token.lower() in option_text.lower() and purpose not in found:
            found.append(purpose)
        if len(found) == 3:
            break
    return found


def requirement_summary(question_text: str) -> str:
    parts = [
        part.strip(" （()）")
        for part in re.split(r"[。！？?]", question_text)
        if len(part.strip(" （()）")) >= 8
    ]
    if not parts:
        return question_text.strip()[:220]
    return "；".join(parts[-2:])[-220:]


def generate_reason(question: dict, key: str, is_correct: bool) -> str:
    option_text = question["options"][key]["zh"].strip()
    purposes = matched_purposes(option_text)
    if purposes:
        purpose_text = "；".join(purposes) + "。"
    else:
        purpose_text = f"此方案的作用是執行這項資源配置與資料流程：{option_text.rstrip('。')}。"

    requirement = requirement_summary(question["question_text"]["zh"])
    if is_correct:
        return (
            f"{purpose_text}在此選項的架構中，這些能力會用來處理「{requirement}」；"
            "因此它同時涵蓋題目指定的功能與限制，是本題應採用的做法。"
        )

    correct_text = "；".join(
        question["options"][answer]["zh"].strip()
        for answer in question["correct_answers"]
    )[:220]
    return (
        f"{purpose_text}此做法雖能執行選項描述的工作，但沒有完整處理「{requirement}」；"
        f"本題應改用正確選項所述的「{correct_text}」，其架構才具備缺少的關鍵能力。"
    )


def normalize_existing(reason: str) -> str:
    reason = reason.replace("技术原因：", "").replace("技術原因：", "").strip()
    reason = re.sub(r"^(?:分析|原因|理由)\s*[：:]\s*", "", reason)
    return reason


def main() -> None:
    changed_files = 0
    changed_options = 0
    generated_options = 0

    for path in sorted(QUESTION_DIR.glob("saa_Q*-Q*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        file_changed = False
        for question in document["questions"]:
            correct_answers = set(question["correct_answers"])
            for key, explanation in question["option_explanations"].items():
                is_correct = key in correct_answers
                status = "正確。" if is_correct else "錯誤。"
                original = explanation["zh"]
                reason = strip_prefix(original, status)
                override = SPECIAL_OVERRIDES.get((question["question_no"], key))
                if override:
                    reason = override
                elif is_generic(reason):
                    reason = generate_reason(question, key, is_correct)
                    generated_options += 1
                else:
                    reason = normalize_existing(reason)

                updated = f"{status}原因是，{reason}"
                if updated != original:
                    explanation["zh"] = updated
                    changed_options += 1
                    file_changed = True

            if file_changed:
                # Keep answer/discussion untouched: only per-option teaching text changes.
                pass

        if file_changed:
            path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            changed_files += 1

    print(
        f"normalized SAA explanations: files={changed_files}, "
        f"options={changed_options}, generated={generated_options}"
    )


if __name__ == "__main__":
    main()
