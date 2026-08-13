"""Build bilingual AIF-C01 question JSON from the local source PDFs."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "question_sources"
OUTPUT_DIR = ROOT / "questions"
QUESTION_RE = re.compile(r"(?:Topic\s+\d+\s*)?Question\s*#(\d+)", re.IGNORECASE)
OPTION_RE = re.compile(r"(?m)^[ \t]*([A-F])\.\s*")
CHINESE_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
NOISE_RE = re.compile(
    r"IT认证轻松过|下载时间|使用指南|扫码关注|淘宝|闲鱼|微信|Examtopics|"
    r"Community vote distribution|社区投票分布",
    re.IGNORECASE,
)

DOMAINS = {
    1: "領域 1：AI 和 ML 基礎 (Fundamentals of AI and ML)",
    2: "領域 2：生成式 AI 基礎 (Fundamentals of GenAI)",
    3: "領域 3：基礎模型的應用 (Applications of Foundation Models)",
    4: "領域 4：負責任 AI 指南 (Guidelines for Responsible AI)",
    5: "領域 5：AI 解決方案的安全、合規與治理 (Security, Compliance, and Governance for AI Solutions)",
}

AIF_PART_END_QUESTION = (46, 92, 135, 180, 226, 271, 316, 361, 406, 452)

DOMAIN_RULES = (
    (5, (" iam ", "identity", "permission", "access control", "encrypt", "kms", "privacy", "pii", "compliance", "governance", "audit", "security", "guardrail", "macie")),
    (4, ("bias", "fairness", "responsible", "transparent", "transparency", "explain", "interpret", "toxicity", "harmful", "human review", "moderation", "inappropriate", "unwanted")),
    (3, ("prompt", "rag", "retrieval", "fine-tun", "fine tun", "agent", "knowledge base", "bedrock", "amazon q", "model selection", "temperature", "top_p", "context window")),
    (2, ("generative", "large language model", "llm", "foundation model", "token", "embedding", "transformer", "diffusion", "pretrain", "pre-train")),
)

ZH_OPTION_FALLBACKS = {
    # AWS service names are official product names and remain unchanged.
    "Amazon Q Developer": "Amazon Q Developer",
    "AWS Config": "AWS Config",
    "Amazon Personalize": "Amazon Personalize",
    "Amazon Comprehend": "Amazon Comprehend",
    "Decision trees": "决策树",
    "Linear regression": "线性回归",
    "Logistic regression": "逻辑回归",
    "Neural networks": "神经网络",
    "R-squared score": "R² 决定系数",
    "Accuracy": "准确率",
    "Root mean squared error (RMSE)": "均方根误差（RMSE）",
    "Learning rate": "学习率",
    "Temperature": "温度",
    "Context window": "上下文窗口",
    "Batch size": "批次大小",
    "Model size": "模型大小",
    "Object detection": "目标检测",
    "Anomaly detection": "异常检测",
    "Named entity recognition": "命名实体识别",
    "Inpainting": "图像修复",
    "Generative pre-trained transformers (GPT)": "生成式预训练 Transformer（GPT）",
    "Residual neural network": "残差神经网络",
    "Support vector machine": "支持向量机",
    "WaveNet": "WaveNet 音频生成模型",
    "Training": "训练",
    "Inference": "推理",
    "Model deployment": "模型部署",
    "Bias correction": "偏差修正",
    "Toxicity": "毒性",
    "Hallucinations": "幻觉",
    "Plagiarism": "抄袭",
    "Privacy": "隐私",
    "Generative adversarial network (GAN)": "生成对抗网络（GAN）",
    "XGBoost": "XGBoost 梯度提升算法",
    "Confusion matrix": "混淆矩阵",
    "Correlation matrix": "相关矩阵",
    "R2 score": "R² 决定系数",
    "Mean squared error (MSE)": "均方误差（MSE）",
    "Batch transform": "批量转换",
    "Real-time inference": "实时推理",
    "Serverless inference": "无服务器推理",
    "Asynchronous inference": "异步推理",
    "Embeddings": "嵌入（Embeddings）",
    "Tokens": "词元（Tokens）",
    "Models": "模型",
    "Binaries": "二进制数据",
    "Bilingual Evaluation Understudy (BLEU)": "双语评估替补指标（BLEU）",
    "Recall-Oriented Understudy for Gisting Evaluation (ROUGE)": "面向摘要的召回率评估指标（ROUGE）",
    "F1 score": "F1 分数",
    "Temperature value": "温度值",
    "Adversarial prompting": "对抗式提示",
    "Zero-shot prompting": "零样本提示",
    "Least-to-most prompting": "由简至繁提示",
    "Chain-of-thought prompting": "思维链提示",
    "Precision": "精确率",
    "Time to first token": "首个 token 生成时间",
    "Word error rate": "词错误率",
    "Explainability": "可解释性",
    "Experiment and refine the prompt until the FM produces the desired responses.": "持续试验并优化提示，直到基础模型产生所需响应。",
    "Amazon EC2 Trn series": "Amazon EC2 Trn 系列",
    "Enable invocation logging in Amazon Bedrock.": "在 Amazon Bedrock 中启用模型调用日志记录。",
    "Create one Amazon Bedrock role that has full Amazon S3 access. Create IAM roles for each team that have access to only each team's customer folders.": "建立一个拥有完整 Amazon S3 访问权限的 Amazon Bedrock 角色，并为各团队建立只能访问本团队客户文件夹的 IAM 角色。",
    "Decrease the number of tokens in the prompt.": "减少提示中的 token 数量。",
}

HOTSPOT_QUESTIONS = {
    114: {
        "domain": 1,
        "options": [
            ("Define the business goal and frame the ML problem.", "定义业务目标并将需求转化为机器学习问题。"),
            ("Develop the model.", "开发模型。"),
            ("Deploy the model.", "部署模型。"),
            ("Monitor the model.", "监控模型。"),
        ],
        "note": "The listed order is the ML workload lifecycle confirmed by the source discussion.",
        "note_zh": "所列顺序是来源讨论确认的机器学习工作负载生命周期。",
    },
    125: {
        "domain": 1,
        "options": [
            ("A low-latency chatbot: Real-time inference.", "低延迟聊天机器人：实时推理。"),
            ("A weekend job that processes gigabytes of text: Batch transform.", "周末处理数 GB 文本的作业：批量转换。"),
            ("An API for small text inputs and low-latency predictions: Real-time inference.", "处理小段文本并提供低延迟预测的 API：实时推理。"),
        ],
        "note": "The source maps interactive low-latency requests to real-time inference and offline bulk processing to batch transform.",
        "note_zh": "来源将交互式低延迟请求映射到实时推理，将离线批量处理映射到批量转换。",
    },
    135: {
        "domain": 1,
        "options": [
            ("Binary classification: Supervised learning.", "二元分类：监督学习。"),
            ("Multi-class classification: Supervised learning.", "多类别分类：监督学习。"),
            ("K-means clustering: Unsupervised learning.", "K-means 聚类：无监督学习。"),
            ("Dimensionality reduction: Unsupervised learning.", "降维：无监督学习。"),
        ],
        "note": "Classification learns from labels, whereas K-means and common dimensionality-reduction methods discover structure without labels.",
        "note_zh": "分类从标签学习，而 K-means 和常见降维方法在没有标签的情况下发现数据结构。",
    },
    143: {
        "domain": 3,
        "options": [
            ("A plain prompt without examples: Zero-shot prompting.", "不提供示例的直接提示：零样本提示。"),
            ("A prompt that supplies examples: Few-shot prompting.", "提供少量示例的提示：少样本提示。"),
            ("A prompt that requests logical intermediate steps: Chain-of-thought prompting.", "要求展示逻辑中间步骤的提示：思维链提示。"),
        ],
        "note": "The source discussion identifies zero-shot, few-shot, and chain-of-thought by the presence of examples and step-by-step reasoning.",
        "note_zh": "来源讨论依据是否提供示例以及是否要求逐步推理，区分零样本、少样本和思维链提示。",
    },
    144: {
        "domain": 4,
        "options": [
            ("Block harmful content categories: Content filters.", "阻止有害内容类别：内容过滤器。"),
            ("Block discussion of specified subjects: Denied topics.", "阻止讨论指定主题：拒绝主题。"),
            ("Block specified words or profanity: Word filters.", "阻止指定词语或脏话：词语过滤器。"),
            ("Check whether a response is relevant and grounded in source information: Contextual grounding check.", "检查响应是否与来源信息相关且有依据：上下文依据检查。"),
        ],
        "note": "These are the four Amazon Bedrock guardrail policy mappings confirmed by the source.",
        "note_zh": "这些是来源确认的四种 Amazon Bedrock Guardrails 策略映射。",
    },
    155: {
        "domain": 3,
        "options": [
            ("Teach the model a new domain-specific task with labeled examples: Model fine-tuning.", "使用带标签示例教授新的领域特定任务：模型微调。"),
            ("Expand a limited labeled dataset with additional variations: Data augmentation.", "通过额外变体扩充有限的带标签数据集：数据增强。"),
            ("Adapt the model when only unlabeled domain data is available: Continued pre-training.", "只有无标签领域数据时调整模型：持续预训练。"),
        ],
        "note": "The method depends on whether the goal is task adaptation, generating more labeled examples, or learning from unlabeled domain data.",
        "note_zh": "应依目标是任务适配、扩增带标签样本，还是从无标签领域数据学习来选择方法。",
    },
    185: {
        "domain": 3,
        "options": [
            ("Improve performance on specific tasks and examples: Fine-tuning.", "提升特定任务和示例的表现：微调。"),
            ("Improve domain knowledge with unlabeled domain-specific documents: Continued pre-training.", "使用无标签领域文档提升领域知识：持续预训练。"),
            ("Retrain over time with more unlabeled data: Continued pre-training.", "随时间使用更多无标签数据继续训练：持续预训练。"),
        ],
        "note": "The source distinguishes labeled task examples for fine-tuning from unlabeled domain corpora for continued pre-training.",
        "note_zh": "来源区分了用于微调的带标签任务示例与用于持续预训练的无标签领域语料。",
    },
    188: {
        "domain": 4,
        "options": [
            ("Protect customer information and restrict access: Privacy and security.", "保护客户信息并限制访问：隐私与安全。"),
            ("Tell users that they are interacting with an AI system: Transparency.", "告知用户正在与 AI 系统互动：透明度。"),
            ("Prevent or mitigate harmful chatbot responses: Safety.", "防止或缓解聊天机器人的有害响应：安全性。"),
        ],
        "note": "The source maps data protection to privacy and security, disclosure to transparency, and harm prevention to safety.",
        "note_zh": "来源将数据保护对应隐私与安全，将信息披露对应透明度，将防止伤害对应安全性。",
    },
    191: {
        "domain": 1,
        "options": [
            ("Build ML models with a visual no-code interface: SageMaker Canvas.", "使用可视化无代码界面构建机器学习模型：SageMaker Canvas。"),
            ("Start from pretrained models and prebuilt solutions: SageMaker JumpStart.", "从预训练模型和预构建解决方案开始：SageMaker JumpStart。"),
            ("Create and manage labeled training datasets: SageMaker Ground Truth.", "创建和管理带标签训练数据集：SageMaker Ground Truth。"),
        ],
        "note": "The source maps no-code model building, prebuilt solutions, and data labeling to Canvas, JumpStart, and Ground Truth respectively.",
        "note_zh": "来源分别将无代码模型构建、预构建解决方案和数据标注对应到 Canvas、JumpStart 与 Ground Truth。",
    },
    229: {
        "domain": 1,
        "options": [
            ("Manage different model versions: SageMaker Model Registry.", "管理不同模型版本：SageMaker Model Registry。"),
            ("Use the current model to make predictions: SageMaker Serverless Inference.", "使用当前模型进行预测：SageMaker Serverless Inference。"),
        ],
        "note": "Model Registry manages model versions, while Serverless Inference runs predictions without provisioning inference infrastructure.",
        "note_zh": "Model Registry 管理模型版本，而 Serverless Inference 无需预置推理基础设施即可执行预测。",
    },
    235: {
        "domain": 2,
        "options": [
            ("Create high-quality product images influenced by slogans: Diffusion model.", "创建受标语影响的高质量产品图像：扩散模型。"),
            ("Create contextually relevant advertising slogans: Transformer-based model.", "创建与广告产品相关的标语：基于 Transformer 的模型。"),
            ("Verify that brand elements are properly placed in images: Object detection model.", "验证品牌元素是否正确放置在图像中：目标检测模型。"),
        ],
        "note": "Diffusion generates images, transformers generate contextual text, and object detection locates visual elements.",
        "note_zh": "扩散模型生成图像，Transformer 生成上下文文本，目标检测用于定位视觉元素。",
    },
    245: {
        "domain": 4,
        "options": [
            ("Encrypt data and isolate the application on a private network: Privacy and security.", "加密数据并将应用隔离在私有网络：隐私与安全。"),
            ("Evaluate the impact on different population groups: Fairness.", "评估对不同人口群体的影响：公平性。"),
            ("Test the application with unexpected data and unusual situations: Robustness.", "使用意外数据和特殊情境测试应用：稳健性。"),
        ],
        "note": "The controls respectively address data protection, equitable outcomes, and resilience to unusual inputs.",
        "note_zh": "这些控制分别对应数据保护、公平结果以及对异常输入的适应能力。",
    },
    257: {
        "domain": 4,
        "options": [
            ("Apply human feedback across the ML lifecycle: SageMaker Ground Truth.", "在机器学习生命周期中应用人工反馈：SageMaker Ground Truth。"),
            ("Implement safeguards aligned with responsible AI policies: Amazon Bedrock Guardrails.", "实施符合负责任 AI 政策的防护措施：Amazon Bedrock Guardrails。"),
            ("Detect bias during data preparation and model training: SageMaker Clarify.", "在数据准备和模型训练期间检测偏差：SageMaker Clarify。"),
        ],
        "note": "Ground Truth supports human labeling, Guardrails enforces safety controls, and Clarify detects bias and explains models.",
        "note_zh": "Ground Truth 支持人工标注，Guardrails 执行安全控制，Clarify 检测偏差并解释模型。",
    },
    264: {
        "domain": 1,
        "options": [
            ("Predict a yes-or-no outcome: Binary classification.", "预测是或否的结果：二元分类。"),
            ("Predict a continuous numeric quantity: Regression.", "预测连续数值：回归。"),
            ("Predict one of several car models: Multiclass classification.", "预测多个汽车型号中的一个：多类别分类。"),
        ],
        "note": "Binary classification handles two classes, regression predicts quantities, and multiclass classification handles more than two categories.",
        "note_zh": "二元分类处理两个类别，回归预测数值，多类别分类处理两个以上类别。",
    },
    267: {
        "domain": 1,
        "options": [
            ("Determine a suitable model for a business case: SageMaker Model Cards.", "为业务案例确定合适模型：SageMaker Model Cards。"),
            ("Prepare data through a low-code or no-code interface: SageMaker Data Wrangler.", "通过低代码或无代码界面准备数据：SageMaker Data Wrangler。"),
            ("Identify bias or imbalance in data: SageMaker Clarify.", "识别数据中的偏差或不平衡：SageMaker Clarify。"),
        ],
        "note": "Model Cards documents intended use and performance, Data Wrangler prepares data, and Clarify analyzes bias.",
        "note_zh": "Model Cards 记录预期用途和性能，Data Wrangler 准备数据，Clarify 分析偏差。",
    },
    275: {
        "domain": 1,
        "options": [
            ("Measure engagement with recommendations: Click-through rate (CTR).", "衡量用户与推荐内容的互动：点击率（CTR）。"),
            ("Measure the effect on total purchase value: Average order value (AOV).", "衡量对购买总价值的影响：平均订单价值（AOV）。"),
            ("Measure whether users return to the platform: Retention rate.", "衡量用户是否返回平台：留存率。"),
        ],
        "note": "CTR measures recommendation engagement, AOV measures purchase value, and retention measures returning users.",
        "note_zh": "CTR 衡量推荐互动，AOV 衡量购买价值，留存率衡量回访用户。",
    },
    280: {
        "domain": 3,
        "options": [
            ("Enhance an LLM with external information sources: Retrieval Augmented Generation (RAG).", "使用外部信息来源增强 LLM：检索增强生成（RAG）。"),
            ("Generalize to an unseen task without examples: Zero-shot learning.", "在没有示例的情况下泛化到未见任务：零样本学习。"),
            ("Handle a new task with a small number of examples: Few-shot learning.", "使用少量示例处理新任务：少样本学习。"),
        ],
        "note": "RAG retrieves external context, zero-shot uses no examples, and few-shot supplies a small example set.",
        "note_zh": "RAG 检索外部上下文，零样本不提供示例，少样本提供少量示例。",
    },
    283: {
        "domain": 1,
        "options": [
            ("The broad field that simulates human intelligence: Artificial intelligence (AI).", "模拟人类智能的广泛领域：人工智能（AI）。"),
            ("A subset of AI that learns patterns from data: Machine learning (ML).", "从数据学习模式的 AI 子领域：机器学习（ML）。"),
            ("A subset of ML that uses multilayer neural networks: Deep learning.", "使用多层神经网络的 ML 子领域：深度学习。"),
        ],
        "note": "AI contains ML, and ML contains deep learning as progressively narrower concepts.",
        "note_zh": "AI 包含 ML，而 ML 包含深度学习，三者范围逐步缩小。",
    },
    291: {
        "domain": 1,
        "options": [
            ("Customer comments for sentiment analysis: Text data.", "用于情感分析的客户评论：文本数据。"),
            ("Traffic signs captured by a camera: Image data.", "摄像头捕获的交通标志：图像数据。"),
            ("Demographics and purchase records in rows and columns: Tabular data.", "以行列保存的人口统计和购买记录：表格数据。"),
            ("Chronological stock prices: Time-series data.", "按时间顺序排列的股票价格：时间序列数据。"),
        ],
        "note": "The data type follows the source representation: language, pixels, structured rows, or time-ordered values.",
        "note_zh": "数据类型取决于来源表示方式：语言、像素、结构化行列或按时间排列的数值。",
    },
    300: {
        "domain": 2,
        "options": [
            ("Amount of information that fits in one prompt: Context window.", "单个提示可容纳的信息量：上下文窗口。"),
            ("Time required for a model to generate output: Latency.", "模型生成输出所需的时间：延迟。"),
            ("Multiple simultaneous endpoint invocations: Concurrency.", "多个用户同时调用端点：并发性。"),
        ],
        "note": "Context window measures input capacity, latency measures response time, and concurrency measures simultaneous requests.",
        "note_zh": "上下文窗口衡量输入容量，延迟衡量响应时间，并发性衡量同时请求数量。",
    },
    309: {
        "domain": 1,
        "options": [
            ("Define the business objective.", "定义业务目标。"),
            ("Collect, clean, and process the data.", "收集、清理并处理数据。"),
            ("Develop and train the model.", "开发并训练模型。"),
            ("Deploy the model.", "部署模型。"),
        ],
        "note": "The custom-model lifecycle proceeds from objective definition through data preparation and model development to deployment.",
        "note_zh": "自定义模型生命周期从定义目标开始，经过数据准备和模型开发，最后进入部署。",
    },
    311: {
        "domain": 3,
        "options": [
            ("Provide a few examples before requesting an answer: Few-shot prompting.", "在要求回答前提供少量示例：少样本提示。"),
            ("Explicitly request reasoning steps: Chain-of-thought prompting.", "明确要求展示推理步骤：思维链提示。"),
            ("Give an instruction without examples: Zero-shot prompting.", "只给指令而不提供示例：零样本提示。"),
        ],
        "note": "Examples distinguish few-shot from zero-shot, while explicit intermediate reasoning identifies chain-of-thought.",
        "note_zh": "是否提供示例区分少样本与零样本，而明确要求中间推理步骤对应思维链。",
    },
    313: {
        "domain": 3,
        "options": [
            ("Upload the product-guide files to Amazon S3.", "将产品指南文件上传到 Amazon S3。"),
            ("Send the files to an Amazon Nova multimodal model.", "将文件发送到 Amazon Nova 多模态模型。"),
            ("Extract usable structured data from the content.", "从内容中提取可用的结构化数据。"),
            ("Insert the structured data into the product database.", "将结构化数据写入产品数据库。"),
        ],
        "note": "The ingestion workflow stores the source, processes it with the multimodal model, structures the result, and writes the database record.",
        "note_zh": "摄取流程先保存来源，再由多模态模型处理、结构化结果，最后写入数据库。",
    },
    328: {
        "domain": 3,
        "options": [
            ("Prompt engineering.", "提示工程。"),
            ("Retrieval Augmented Generation (RAG).", "检索增强生成（RAG）。"),
            ("Fine-tuning.", "微调。"),
            ("Continued pre-training.", "持续预训练。"),
        ],
        "note": "From least to most development effort, the source orders prompt engineering, RAG, fine-tuning, and continued pre-training.",
        "note_zh": "来源按开发工作量从低到高排列为提示工程、RAG、微调、持续预训练。",
    },
    350: {
        "domain": 1,
        "options": [
            ("Predict customer lifetime value: Regression.", "预测客户终身价值：回归。"),
            ("Predict whether a customer will stop using the service: Classification.", "预测客户是否会停止使用服务：分类。"),
            ("Group customers with similar behavior and preferences: Clustering.", "按相似行为和偏好对客户分组：聚类。"),
        ],
        "note": "Regression predicts a numeric value, classification predicts a category, and clustering discovers unlabeled groups.",
        "note_zh": "回归预测数值，分类预测类别，聚类发现没有预设标签的群组。",
    },
    351: {
        "domain": 1,
        "options": [
            ("Prepare the data.", "准备数据。"),
            ("Train the model.", "训练模型。"),
            ("Test the model.", "测试模型。"),
            ("Deploy the model.", "部署模型。"),
        ],
        "note": "When data already exists, the lifecycle prepares it, trains and tests the model, and then deploys the validated model.",
        "note_zh": "已有数据时，生命周期依序准备数据、训练和测试模型，最后部署通过验证的模型。",
    },
    366: {
        "domain": 3,
        "options": [
            ("Use labeled data to improve specific-task performance: Fine-tuning.", "使用带标签数据提升特定任务表现：微调。"),
            ("Use unlabeled data to adapt an FM to a domain: Continued pre-training.", "使用无标签数据使 FM 适应特定领域：持续预训练。"),
            ("Transfer knowledge from a larger model to a smaller model: Distillation.", "将较大模型的知识迁移到较小模型：知识蒸馏。"),
        ],
        "note": "Fine-tuning uses task supervision, continued pre-training uses unlabeled domain text, and distillation transfers teacher-model knowledge.",
        "note_zh": "微调使用任务监督，持续预训练使用无标签领域文本，知识蒸馏迁移教师模型的能力。",
    },
    387: {
        "domain": 5,
        "options": [
            ("Determine governance goals, risks, and policies.", "确定治理目标、风险和政策。"),
            ("Form a cross-functional AI governance group.", "组建跨职能 AI 治理团队。"),
            ("Set up model monitoring mechanisms.", "建立模型监控机制。"),
        ],
        "note": "The source defines policy first, establishes accountable governance roles next, and then implements ongoing monitoring.",
        "note_zh": "来源先定义政策，再建立负责治理的组织角色，最后实施持续监控。",
    },
    403: {
        "domain": 1,
        "options": [
            ("Text-based customer reviews: Natural language processing (NLP).", "文本客户评论：自然语言处理（NLP）。"),
            ("Animal images labeled by species: Computer vision.", "按物种标注的动物图像：计算机视觉。"),
            ("Daily product sales volumes: Time-series forecasting.", "每日产品销量：时间序列预测。"),
        ],
        "note": "Text maps to NLP, labeled images to computer vision, and chronological numeric observations to time-series forecasting.",
        "note_zh": "文本对应 NLP，带标签图像对应计算机视觉，按时间排列的数值观测对应时间序列预测。",
    },
    417: {
        "domain": 3,
        "options": [
            ("Specify the model's use case: Task.", "指定模型的使用案例：任务（Task）。"),
            ("Define the persona the model should assume: Role.", "定义模型应扮演的人设：角色（Role）。"),
            ("Describe the required tone, format, or structure: Response style.", "描述所需的语气、格式或结构：响应风格（Response style）。"),
            ("Set metrics for evaluating whether output meets expectations: Success criteria.", "设定用于评估输出是否符合预期的指标：成功标准（Success criteria）。"),
        ],
        "note": "Task defines what to do, role defines who responds, response style defines presentation, and success criteria defines evaluation.",
        "note_zh": "Task 定义要做什么，Role 定义由谁回答，Response style 定义呈现方式，Success criteria 定义评估标准。",
    },
    442: {
        "domain": 3,
        "options": [
            ("Monitor agent behavior with dashboards: AgentCore Observability.", "通过仪表板监控代理行为：AgentCore Observability。"),
            ("Execute code securely across multiple languages: AgentCore Code Interpreter.", "跨多种语言安全执行代码：AgentCore Code Interpreter。"),
            ("Provide a secure serverless browser runtime for agents: AgentCore Browser tool.", "为代理提供安全的无服务器浏览器运行环境：AgentCore Browser tool。"),
        ],
        "note": "Observability monitors agents, Code Interpreter executes code, and Browser provides browser automation runtime.",
        "note_zh": "Observability 监控代理，Code Interpreter 执行代码，Browser 提供浏览器自动化运行环境。",
    },
    443: {
        "domain": 3,
        "options": [
            ("Parse the documents.", "解析文档。"),
            ("Divide the parsed data into chunks.", "将解析后的数据切分成区块。"),
            ("Convert the chunks into vector embeddings.", "将区块转换为向量嵌入。"),
            ("Write the vector embeddings to the vector store.", "将向量嵌入写入向量存储。"),
        ],
        "note": "Bedrock knowledge-base ingestion parses, chunks, embeds, and stores the source data in that order.",
        "note_zh": "Bedrock 知识库摄取依序解析、切分、嵌入并存储来源数据。",
    },
}


def pdf_text(kind: str, parts: tuple[int, ...]) -> str:
    chunks: list[str] = []
    for part in parts:
        path = SOURCE_DIR / f"AWS Certified AI Practitioner AIF-C01_with_{kind}_part_{part:02d}.pdf"
        reader = PdfReader(path)
        if kind == "aizh":
            chunks.extend(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
        else:
            chunks.extend(page.extract_text() or "" for page in reader.pages)
    return "\n".join(chunks)


def question_blocks(text: str) -> dict[int, str]:
    matches = list(QUESTION_RE.finditer(text))
    result: dict[int, str] = {}
    for index, match in enumerate(matches):
        number = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[number] = text[match.end():end]
    return result


def clean_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\bMost Voted\b", "", value, flags=re.IGNORECASE)
    kept: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or NOISE_RE.search(line):
            continue
        if re.fullmatch(r"[()\d% ,]+", line):
            continue
        kept.append(line)
    value = " ".join(kept)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"(?:^|\s)opics(?:\s|$)", " ", value, flags=re.IGNORECASE)
    for _ in range(3):
        value = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", value)
    value = re.sub(r"\s+([,.;:?!，。；：？！])", r"\1", value)
    return value.strip()


def source_header(block: str, marker: str) -> str:
    positions = [pos for token in (marker, "Comments", "Correct Answer:") if (pos := block.find(token)) >= 0]
    return block[: min(positions)] if positions else block


def parse_header(block: str, marker: str) -> tuple[str, dict[str, str]]:
    header = source_header(block, marker)
    matches = list(OPTION_RE.finditer(header))
    if not matches:
        raise ValueError("No options found")
    question = clean_text(header[: matches[0].start()])
    options: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(header)
        options[match.group(1)] = clean_text(header[match.end():end])
    return question, options


def split_bilingual(value: str) -> tuple[str, str]:
    match = CHINESE_RE.search(value)
    if not match:
        cleaned = clean_text(value)
        return cleaned, cleaned
    en = clean_text(value[: match.start()])
    zh = clean_text(value[match.start():])
    return en or zh, zh or en


def clean_zh_option(en: str, raw_zh: str) -> str:
    value = clean_text(raw_zh)
    marker = re.search(
        r"\s*[)）]?\s*(?:问题点|正确点|正确性分析|是否支持|可解释性|错误[。:]|正确[。:]|"
        r"结论[：:]|原因[：:]|题目解析|官方答案|答案比较|与官方答案|[3456]\.\s*)",
        value,
    )
    if marker:
        value = value[: marker.start()].strip()
    value = value.rstrip(" )）")
    if not CHINESE_RE.search(value) or len(value) < 2:
        if en in ZH_OPTION_FALLBACKS:
            return ZH_OPTION_FALLBACKS[en]
        if re.match(r"^(?:Amazon|AWS|SageMaker|Guardrails)\b", en):
            return f"使用 {en}"
        return f"技术选项：{en}"
    return value


def source_zh_explanations(block: str, options: dict[str, str], answers: list[str]) -> dict[str, str]:
    answer_comment_re = (
        r"(?:我(?:的)?(?:选择|選擇|选|選)(?:的)?(?:答案)?|我(?:的)?答案|"
        r"官方答案|与官方答案|與官方答案|答案比较|答案比較|比较与思考|比較與思考)"
    )
    matches = list(OPTION_RE.finditer(block))
    candidates: dict[str, list[tuple[int, str]]] = {key: [] for key in options}
    for index, match in enumerate(matches):
        key = match.group(1)
        if key not in candidates:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        segment = clean_text(block[match.end():end])
        option_text = clean_text(options[key])
        if segment.lower().startswith(option_text.lower()):
            segment = segment[len(option_text):].strip()
        marker = re.search(r"(?:正确|错误|问题点|正确点|是否支持|可解释性|原因|结论)[：:]?", segment)
        if not marker:
            continue
        if re.search(
            rf"Correct Answer|题目解析|題目解析|题目分析|題目分析|{answer_comment_re}",
            segment[: marker.start()],
        ):
            continue
        reason = segment[marker.start():]
        reason = re.split(
            rf"(?:\b[3456]\.\s*{answer_comment_re}|Correct Answer|Community vote|"
            rf"题目解析|題目解析|题目分析|題目分析|{answer_comment_re})",
            reason,
        )[0]
        score = len(reason) + 200 * len(re.findall(r"正确|错误|原因|结论", reason))
        candidates[key].append((score, reason.strip()))

    result: dict[str, str] = {}
    for key, rows in candidates.items():
        if not rows:
            continue
        reason = max(rows, key=lambda item: item[0])[1]
        reason = re.sub(r"^(?:正确|错误|问题点|正确点|是否支持|可解释性|原因|结论)[：:]?\s*", "", reason)
        reason = reason.strip(" 。；;:")
        if reason:
            prefix = "正確。" if key in answers else "錯誤。"
            result[key] = f"{prefix}原因是，{reason[:900]}"
    return result


def correct_answers(block: str) -> list[str]:
    matches = re.findall(r"Correct\s*Answer\s*:\s*([A-F](?:\s*[,/&+]\s*[A-F]|[A-F])*)", block, re.IGNORECASE)
    if not matches:
        raise ValueError("Correct answer not found")
    letters = sorted(set(re.findall(r"[A-F]", matches[-1].upper())))
    return letters


def vote_distribution(block: str) -> str | None:
    anchor = block.rfind("Community vote distribution")
    if anchor < 0:
        return None
    tail = unicodedata.normalize("NFKC", block[anchor : anchor + 500])
    votes = re.findall(r"\b([A-F]|Other)\s*\((\d+)%\)", tail, re.IGNORECASE)
    if not votes:
        return None
    return ", ".join(f"{label.upper() if label.lower() != 'other' else 'Other'} {percent}%" for label, percent in votes)


def domain_for(question: str, options: dict[str, str]) -> str:
    haystack = f" {question.lower()} "
    for domain, keywords in DOMAIN_RULES:
        if any(keyword in haystack for keyword in keywords):
            return DOMAINS[domain]
    return DOMAINS[1]


def compact_requirement(question: str) -> str:
    sentences = re.split(r"(?<=[?.!])\s+", question)
    return (sentences[-1] if sentences else question)[:360]


def build_question(number: int, aizh: str, discussion: str) -> dict:
    if number in HOTSPOT_QUESTIONS:
        return build_hotspot_question(number, aizh, discussion)
    en_question, en_options = parse_header(discussion, "Comments")
    bilingual_question, bilingual_options = parse_header(aizh, "题目解析")
    _, zh_question = split_bilingual(bilingual_question)
    zh_options: dict[str, str] = {}
    for key, value in bilingual_options.items():
        _, zh = split_bilingual(value)
        zh_options[key] = clean_zh_option(en_options.get(key, ""), zh)

    if set(en_options) != set(zh_options):
        raise ValueError(f"Q{number}: English and bilingual option keys differ")

    answers = correct_answers(aizh)
    zh_source_reasons = source_zh_explanations(aizh, en_options, answers)
    requirement = compact_requirement(en_question)
    correct_en = "; ".join(f"{key}. {en_options[key]}" for key in answers)
    correct_zh = "；".join(f"{key}. {zh_options[key]}" for key in answers)
    explanations: dict[str, dict[str, str]] = {}
    for key in en_options:
        if key in answers:
            explanations[key] = {
                "zh": zh_source_reasons.get(key, f"正確。此選項直接滿足題目要求，並且是來源解析確認的答案；本題的核心判斷是：{zh_question[-220:]}"),
                "en": f"Correct. Choosing this option directly addresses the source-confirmed requirement: {requirement}",
            }
        else:
            explanations[key] = {
                "zh": zh_source_reasons.get(key, f"錯誤。此選項不能完整滿足題目的主要要求；相較之下，來源確認的適當答案是 {correct_zh}。"),
                "en": f"Incorrect. This option addresses a different task or misses a key constraint in: {requirement} The source-supported choice is {correct_en}.",
            }

    vote = vote_distribution(aizh) or vote_distribution(discussion)
    if vote:
        discussion_zh = f"來源社群投票分布為 {vote}。討論重點是比較各選項是否真正滿足題目主要需求；最終答案依來源解析與技術判斷採用 {', '.join(answers)}。"
        discussion_en = f"The source community vote distribution is {vote}. The discussion focuses on whether each option satisfies the primary requirement; the final answer follows the source analysis and technical reasoning: {', '.join(answers)}."
    else:
        discussion_zh = f"來源未提供可可靠擷取的投票百分比。最終答案依來源解析與技術判斷採用 {', '.join(answers)}。"
        discussion_en = f"The source does not provide a reliably extractable vote percentage. The final answer follows the source analysis and technical reasoning: {', '.join(answers)}."

    return {
        "question_no": number,
        "domain": domain_for(en_question, en_options),
        "question_text": {"zh": zh_question, "en": en_question},
        "options": {key: {"zh": zh_options[key], "en": en_options[key]} for key in en_options},
        "option_explanations": explanations,
        "selection_type": "單選" if len(answers) == 1 else "複選",
        "correct_answers": answers,
        "answer_text": {
            "zh": correct_zh,
            "en": correct_en,
        },
        "discussion": {"zh": discussion_zh, "en": discussion_en},
    }


def build_hotspot_question(number: int, aizh: str, discussion: str) -> dict:
    spec = HOTSPOT_QUESTIONS[number]
    en_question = clean_text(source_header(discussion, "Comments"))
    bilingual_question = clean_text(source_header(aizh, "Correct Answer:"))
    _, zh_question = split_bilingual(bilingual_question)
    if not CHINESE_RE.search(zh_question):
        zh_question = f"这是一个配对或排序题。请根据题目情境选择正确的对应关系或顺序：{en_question}"

    option_keys = list("ABCDEF")[: len(spec["options"])]
    options = {
        key: {"en": en, "zh": zh}
        for key, (en, zh) in zip(option_keys, spec["options"])
    }
    explanations = {
        key: {
            "zh": f"正確。原因是，{spec['note_zh']}",
            "en": f"Correct. {spec['note']}",
        }
        for key in option_keys
    }
    return {
        "question_no": number,
        "domain": DOMAINS[spec["domain"]],
        "question_text": {"zh": zh_question, "en": en_question},
        "options": options,
        "option_explanations": explanations,
        "selection_type": "複選",
        "correct_answers": option_keys,
        "answer_text": {
            "zh": "；".join(f"{key}. {options[key]['zh']}" for key in option_keys),
            "en": "; ".join(f"{key}. {options[key]['en']}" for key in option_keys),
        },
        "discussion": {
            "zh": f"来源为 HOTSPOT 配对或排序题，未提供可靠投票百分比。{spec['note_zh']}",
            "en": f"The source is a HOTSPOT matching or ordering item and provides no reliable vote percentage. {spec['note']}",
        },
    }


def write_batches(questions: list[dict], batch_size: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for offset in range(0, len(questions), batch_size):
        batch = questions[offset : offset + batch_size]
        start = batch[0]["question_no"]
        end = batch[-1]["question_no"]
        path = OUTPUT_DIR / f"aif_Q{start}-Q{end}.json"
        path.write_text(
            json.dumps({"exam": "AWS AIF-C01", "questions": batch}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"{path.name}: {len(batch)} questions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=30)
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start or not 1 <= args.batch_size <= 30:
        raise ValueError("Use a valid range and a batch size from 1 to 30")

    try:
        last_part = next(
            part
            for part, last_question in enumerate(AIF_PART_END_QUESTION, start=1)
            if args.end <= last_question
        )
    except StopIteration as exc:
        raise ValueError(f"AIF source PDFs end at Q{AIF_PART_END_QUESTION[-1]}") from exc
    parts = tuple(range(1, last_part + 1))
    aizh_blocks = question_blocks(pdf_text("aizh", parts))
    discussion_blocks = question_blocks(pdf_text("discussion", parts))
    questions: list[dict] = []
    for number in range(args.start, args.end + 1):
        if number not in aizh_blocks or number not in discussion_blocks:
            raise ValueError(f"Q{number}: source block missing")
        questions.append(build_question(number, aizh_blocks[number], discussion_blocks[number]))
    write_batches(questions, args.batch_size)


if __name__ == "__main__":
    main()
