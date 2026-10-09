"""Generate 35 Adjudicated Multi-Turn Test Cases for Semantic Compilation Experiment.

Covers:
  - 2-turn dialogues (12 cases)
  - 3-turn dialogues (10 cases)
  - 4-5 turn dialogues (8 cases)
  - 6-8 turn long dialogues (5 cases)

Explicitly attacks:
  - correction & partial correction
  - correction after unrelated turns
  - modality transition
  - plan -> execution -> completion
  - reference resolution ("后者")
  - ambiguous reference ("那个" -> DEFER)
  - nested negation
  - source-relative stance
  - durable instructions buried in long conversations
  - tail omission
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

CASES = [
    # =========================================================================
    # Group 1: 2-Turn Dialogues (12 cases)
    # =========================================================================
    {
        "case_id": "MT-2T-01",
        "category": "direct_correction",
        "description": "User sets meeting time then updates it in next turn",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我们定在周二上午十点开项目周会。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "好的，已为你记下周二上午十点的项目周会。"},
            {"evidence_id": "E03", "speaker": "user", "text": "等等，周二客户要来，改到周四上午十点。"}
        ],
        "must_preserve": [
            "用户原定周二上午十点开项目周会",
            "周二有客户要来",
            "项目周会改到周四上午十点"
        ],
        "must_not_infer": [
            "周二上午仍然要开项目周会",
            "客户周四来"
        ],
        "must_cohabit": [],
        "must_context": [("周四上午开会", "原定周二开会")],
        "must_separate": [("客户周二要来", "周四上午十点开会")],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-02",
        "category": "partial_correction",
        "description": "User updates budget while explicitly retaining venue",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "年会选在外滩华尔道夫酒店，预算暂定5万元。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "外滩华尔道夫酒店办年会，预算5万，记下了。"},
            {"evidence_id": "E03", "speaker": "user", "text": "预算跟财务争取到了，追加到8万元，地点不变。"}
        ],
        "must_preserve": [
            "年会地点选在外滩华尔道夫酒店",
            "年会预算由5万元追加调整为8万元",
            "地点保持不变"
        ],
        "must_not_infer": [
            "年会地点发生变更",
            "年会总预算变成了13万元"
        ],
        "must_cohabit": [],
        "must_context": [("预算追加到8万元", "预算暂定5万元")],
        "must_separate": [("年会选在外滩华尔道夫酒店", "预算追加到8万元")],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-03",
        "category": "reference_resolution_latter",
        "description": "User refers to '后者' which must resolve to Option B",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我们目前考虑两个方案：方案A开发周期短但维护成本极高，方案B重构需要一个月但扩展性极佳。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "方案A重在快但有技术债，方案B重构稳健但初期耗时。"},
            {"evidence_id": "E03", "speaker": "user", "text": "综合长远利益，我们决定采用后者。"}
        ],
        "must_preserve": [
            "方案A开发周期短但维护成本极高",
            "方案B重构需要一个月但扩展性极佳",
            "用户决定采用方案B（后者）"
        ],
        "must_not_infer": [
            "用户决定采用方案A",
            "用户同时采纳了两个方案"
        ],
        "must_cohabit": [],
        "must_context": [("决定采用方案B", "方案B重构需要一个月但扩展性极佳")],
        "must_separate": [("方案A开发周期短维护成本高", "决定采用方案B")],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-04",
        "category": "ambiguous_reference_defer",
        "description": "User refers to '那个方案' with no antecedent in context -> MUST DEFER",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "刚才跟老李在走廊聊了半天。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "聊得怎么样？有什么新进展吗？"},
            {"evidence_id": "E03", "speaker": "user", "text": "我们觉得还是执行那个方案最稳妥。"}
        ],
        "must_preserve": [
            "用户与老李交流",
            "用户决定执行'那个方案'（指代不明，需DEFER）"
        ],
        "must_not_infer": [
            "指代了某个具体的未提及方案"
        ],
        "must_cohabit": [],
        "must_context": [],
        "must_separate": [],
        "must_defer": ["那个方案"]
    },
    {
        "case_id": "MT-2T-05",
        "category": "modality_transition",
        "description": "Transition from uncertain consideration to committed plan",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "最近油价太贵了，我可能考虑换台纯电车。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "电车通勤确实能省不少油费，有心仪的车型吗？"},
            {"evidence_id": "E03", "speaker": "user", "text": "已经去店里交了定金，下周六直接去提Model Y。"}
        ],
        "must_preserve": [
            "用户曾考虑换纯电车",
            "用户已经交了定金",
            "用户确定下周六提Model Y"
        ],
        "must_not_infer": [
            "用户当前仍然处于犹豫不决的考虑阶段",
            "用户已经提到了车"
        ],
        "must_cohabit": [],
        "must_context": [("交定金下周提Model Y", "考虑换纯电车")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-06",
        "category": "plan_execution_completion",
        "description": "Plan in turn 1 transitions to completed state in turn 2",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我准备今天下午把用户认证模块的代码提交审核。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "好的，提交后记得提醒组内同学评审。"},
            {"evidence_id": "E03", "speaker": "user", "text": "PR已经合并进主干了，现在流水线正在跑回归测试。"}
        ],
        "must_preserve": [
            "用户原计划下午提交用户认证模块代码审核",
            "用户认证模块PR已经合并进主干",
            "当前流水线正在跑回归测试"
        ],
        "must_not_infer": [
            "用户还在准备提交审核",
            "回归测试已经通过"
        ],
        "must_cohabit": [],
        "must_context": [("PR已经合并进主干", "原计划提交审核")],
        "must_separate": [("PR已经合并", "正在跑回归测试")],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-07",
        "category": "retraction_and_flip",
        "description": "User cancels cancellation: decide not to cancel, but keep for canary",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "由于架构演进，我们决定下线旧版推荐接口。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "收到，旧版推荐接口下线会影响现有老客户端吗？"},
            {"evidence_id": "E03", "speaker": "user", "text": "等等，先别全下线，保留老接口给海外慢速节点做灰度。"}
        ],
        "must_preserve": [
            "用户曾决定下线旧版推荐接口",
            "用户停止完全下线",
            "保留老接口给海外慢速节点做灰度测试"
        ],
        "must_not_infer": [
            "旧版推荐接口已经被彻底下线",
            "国内节点继续使用老接口"
        ],
        "must_cohabit": [],
        "must_context": [("保留老接口做灰度", "决定下线旧版接口")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-08",
        "category": "source_relative_stance",
        "description": "Contrast third-party reported stance with user's own opinion",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "老张说系统重构后性能至少能提升十倍，建议下周全量上线。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "十倍提升很显著，压测报告出来了吗？"},
            {"evidence_id": "E03", "speaker": "user", "text": "我认为他的测试样本太理想化，真实网络环境下根本不可能达标，绝不能下周上。"}
        ],
        "must_preserve": [
            "老张声称重构后性能提升十倍并建议下周上线",
            "用户认为老张测试样本过于理想化",
            "用户断言真实环境下不可能达标并反对下周上线"
        ],
        "must_not_infer": [
            "用户认为性能提升了十倍",
            "系统已确定下周全量上线"
        ],
        "must_cohabit": [("认为老张测试样本理想化", "断言真实环境不可能达标且反对下周上线")],
        "must_context": [("用户反对上线", "老张建议下周上线")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-09",
        "category": "nested_negation",
        "description": "User explicitly denies that critic's denial was correct",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "审计组昨天指出我们的汇率折算公式存在逻辑错误。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "审计组具体指出了哪个环节的计算问题？"},
            {"evidence_id": "E03", "speaker": "user", "text": "我重新核对了国际会计准则，我不认为审计组说我们错了是对的，我们的折算完全合规。"}
        ],
        "must_preserve": [
            "审计组指出汇率折算公式存在逻辑错误",
            "用户核对准则后否认审计组的指责（不认为审计组说错是对的）",
            "用户坚持汇率折算完全合规"
        ],
        "must_not_infer": [
            "用户承认汇率折算公式有错误"
        ],
        "must_cohabit": [("否认审计组的指责", "坚持汇率折算完全合规")],
        "must_context": [("用户否认指责", "审计组指出公式错误")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-10",
        "category": "tail_omission_trap",
        "description": "User adds secondary trailing constraint at the end of turn 2",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我今天必须把季度总结写完发给王总。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "好的，抓紧时间写，有需要润色的段落随时发我。"},
            {"evidence_id": "E03", "speaker": "user", "text": "发给王总前抄送李经理，顺便把附件里所有财务数字都隐去。"}
        ],
        "must_preserve": [
            "总结发给王总前抄送李经理",
            "将附件中所有财务数字隐去"
        ],
        "must_not_infer": [
            "李经理可以查看财务数字",
            "总结不用发给王总了"
        ],
        "must_cohabit": [],
        "must_context": [("抄送李经理且隐去财务数字", "写完发给王总")],
        "must_separate": [("抄送李经理", "隐去财务数字")],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-11",
        "category": "durable_instruction_intro",
        "description": "User sets a permanent behavioral rule for future outputs",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "帮我看看这篇报告排版怎么样。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "整体排版层次分明，标题很突出。"},
            {"evidence_id": "E03", "speaker": "user", "text": "以后不管生成什么文档，正文一律用四级标题编号，严禁使用非标准罗马数字。"}
        ],
        "must_preserve": [
            "指令要求以后所有文档正文统一使用四级标题编号",
            "严禁使用非标准罗马数字"
        ],
        "must_not_infer": [
            "该约束仅适用于当前这一篇报告"
        ],
        "must_cohabit": [("统一使用四级标题编号", "严禁使用非标准罗马数字")],
        "must_context": [],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-2T-12",
        "category": "condition_resolution",
        "description": "Condition established in T1 evaluated and cleared in T2",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "明天如果下暴雨，户外团建就取消改在室内轰趴。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "好，明天早晨看下气象预警再最后决定。"},
            {"evidence_id": "E03", "speaker": "user", "text": "刚看了最新雷达图，明天晴空万里，户外团建照常举行。"}
        ],
        "must_preserve": [
            "原计划若下暴雨则团建改室内轰趴",
            "最新雷达图显示明天晴空万里",
            "户外团建照常举行"
        ],
        "must_not_infer": [
            "团建改到了室内轰趴",
            "明天有暴雨"
        ],
        "must_cohabit": [],
        "must_context": [("户外团建照常举行", "原计划暴雨改室内")],
        "must_separate": [("最新雷达图显示晴空万里", "户外团建照常举行")],
        "must_defer": []
    },

    # =========================================================================
    # Group 2: 3-Turn Dialogues (10 cases)
    # =========================================================================
    {
        "case_id": "MT-3T-01",
        "category": "correction_after_unrelated_turn",
        "description": "Correction occurs after an unrelated topic turn intervening",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我准备买索尼A7M4相机拍视频。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "A7M4是水桶机，色彩和对焦都很均衡。"},
            {"evidence_id": "E03", "speaker": "user", "text": "今天北京这大风吹得头疼，外面降温好厉害。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "秋冬季节注意保暖，出门多添衣物。"},
            {"evidence_id": "E05", "speaker": "user", "text": "对了，相机我不买索尼了，决定买佳能R6 Mark II。"}
        ],
        "must_preserve": [
            "用户原计划购买索尼A7M4相机",
            "北京降温且风大导致用户头疼",
            "用户取消购买索尼并决定购买佳能R6 Mark II"
        ],
        "must_not_infer": [
            "用户仍然打算买索尼A7M4",
            "用户在索尼和佳能两台都买"
        ],
        "must_cohabit": [],
        "must_context": [("决定买佳能R6 Mark II", "原计划买索尼A7M4")],
        "must_separate": [("北京降温大风头疼", "决定买佳能R6 Mark II")],
        "must_defer": []
    },
    {
        "case_id": "MT-3T-02",
        "category": "stepwise_plan_execution",
        "description": "Progressive execution across three stages",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "新房准备在这个月开始硬装施工。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "硬装开工前要做好设计图和物业报备。"},
            {"evidence_id": "E03", "speaker": "user", "text": "昨天已经跟装修施工队签好了闭口合同。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "签闭口合同能避免后期恶意增项，很明智。"},
            {"evidence_id": "E05", "speaker": "user", "text": "今天上午水电工已经进场开槽拆墙了。"}
        ],
        "must_preserve": [
            "新房准备本月硬装施工",
            "昨天与装修施工队签订了闭口合同",
            "今天上午水电工进场开槽拆墙（已开工）"
        ],
        "must_not_infer": [
            "新房还处于挑选装修队阶段",
            "硬装已经完工"
        ],
        "must_cohabit": [],
        "must_context": [("签订闭口合同", "硬装施工计划"), ("水电工进场开槽", "签订闭口合同")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-3T-03",
        "category": "modality_chain",
        "description": "Consideration -> Booking -> Passed verification",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我最近在考虑要不要去考个PMP证书。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "PMP对项目管理规范化很有帮助，很多大厂有要求。"},
            {"evidence_id": "E03", "speaker": "user", "text": "上周咬牙交了培训费，报了12月的考试。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "加油备考，做好章节模拟题。"},
            {"evidence_id": "E05", "speaker": "user", "text": "今天成绩出来了，5A高分通过！"}
        ],
        "must_preserve": [
            "用户曾考虑考PMP证书",
            "用户上周缴纳培训费报名12月考试",
            "用户今天获知以5A成绩通过PMP考试"
        ],
        "must_not_infer": [
            "用户当前还在考虑要不要考",
            "用户还在备考复习中"
        ],
        "must_cohabit": [],
        "must_context": [("报名考试", "考虑考证"), ("5A成绩通过", "报名考试")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-3T-04",
        "category": "multi_entity_anaphora_resolution",
        "description": "User assigns roles to Xiao Li and Xiao Wang, then resolves '后者'",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "登录界面重构交给小李，支付通道对接交给小王。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "小李负责登录重构，小王负责支付通道。"},
            {"evidence_id": "E03", "speaker": "user", "text": "小李今天突发感冒请假了。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "那登录界面的进度可能要顺延或者找人顶替。"},
            {"evidence_id": "E05", "speaker": "user", "text": "后者的工作最关键，先集中全力把他的联调环境搭好。"}
        ],
        "must_preserve": [
            "登录界面重构分配给小李",
            "支付通道对接分配给小王",
            "小李今天感冒请假",
            "用户要求集中全力搭建小王（后者）的联调环境"
        ],
        "must_not_infer": [
            "集中搭建小李的环境",
            "小王请假了"
        ],
        "must_cohabit": [],
        "must_context": [("小王工作最关键搭建联调环境", "支付通道对接交给小王")],
        "must_separate": [("小李感冒请假", "搭建小王联调环境")],
        "must_defer": []
    },
    {
        "case_id": "MT-3T-05",
        "category": "cross_turn_partial_override",
        "description": "Architecture choice: change DB from PG to MySQL, retain Redis cache",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "后端架构初定：主数据库用PostgreSQL，会话缓存用Redis。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "PostgreSQL支持复杂查询，配合Redis缓存很稳。"},
            {"evidence_id": "E03", "speaker": "user", "text": "运维刚把Redis集群的高可用搭建完毕了。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "集群可用性有保障了，接下来配置数据库连接池吗？"},
            {"evidence_id": "E05", "speaker": "user", "text": "主数据库改用MySQL 8.0，业务方更熟悉；缓存依然用已经建好的Redis。"}
        ],
        "must_preserve": [
            "初始方案主库PostgreSQL且会话缓存Redis",
            "运维已完成Redis集群高可用搭建",
            "主数据库由PostgreSQL变更为MySQL 8.0",
            "会话缓存继续保持使用已建好的Redis"
        ],
        "must_not_infer": [
            "Redis缓存被弃用",
            "主数据库仍然使用PostgreSQL"
        ],
        "must_cohabit": [],
        "must_context": [("主数据库改用MySQL", "主数据库用PostgreSQL")],
        "must_separate": [("运维完成Redis高可用", "主数据库改用MySQL")],
        "must_defer": []
    },
    {
        "case_id": "MT-3T-06",
        "category": "buried_durable_instruction",
        "description": "User inserts permanent coding constraint in turn 2 surrounded by chatter",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "今天周五了，工位旁边都在聊周末去哪玩。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "忙碌了一周，周末确实该好好放松。"},
            {"evidence_id": "E03", "speaker": "user", "text": "交代个规矩：以后写的所有Python代码，类型注解一律用typing的新标准（如使用int | None，严禁使用Optional）。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "明白，以后生成的Python代码全部采用PEP 604联合类型语法。"},
            {"evidence_id": "E05", "speaker": "user", "text": "下周一上午十点记得提醒我向架构组汇报。"}
        ],
        "must_preserve": [
            "指令要求以后生成的Python代码一律使用新联合类型注解（int | None）",
            "严禁使用Optional",
            "要求下周一上午十点提醒向架构组汇报"
        ],
        "must_not_infer": [
            "类型注解要求只在当前会话生效一次",
            "周五就要向架构组汇报"
        ],
        "must_cohabit": [("一律使用新联合类型注解", "严禁使用Optional")],
        "must_context": [],
        "must_separate": [("Python类型注解规矩", "下周一汇报提醒")],
        "must_defer": []
    },
    {
        "case_id": "MT-3T-07",
        "category": "ambiguous_cross_turn_defer",
        "description": "User mentions two candidate companies, then says '买那个好的' -> MUST DEFER",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我今天调研了宁德时代和比亚迪两家公司。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "动力电池和整车制造各有千秋，财务指标如何？"},
            {"evidence_id": "E03", "speaker": "user", "text": "两家Q3利润都超预期了，毛利率也咬得很紧。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "行业龙头竞争激烈，技术路线也各有侧重。"},
            {"evidence_id": "E05", "speaker": "user", "text": "下周一开盘直接全仓买入那个更好的。"}
        ],
        "must_preserve": [
            "用户调研了宁德时代和比亚迪两家公司",
            "两家公司Q3利润均超预期且毛利相近",
            "用户计划全仓买入'那个更好的'（未指明是哪家，必须DEFER）"
        ],
        "must_not_infer": [
            "断言买入宁德时代",
            "断言买入比亚迪"
        ],
        "must_cohabit": [],
        "must_context": [],
        "must_separate": [],
        "must_defer": ["那个更好的"]
    },
    {
        "case_id": "MT-3T-08",
        "category": "stance_attribution_multi_turn",
        "description": "Management target vs sales team fear vs user personal commitment",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "集团领导宣布Q4各业务线营收目标整体上调30%。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "年底冲刺上调30%指标，各条线压力都会很大。"},
            {"evidence_id": "E03", "speaker": "user", "text": "销售二组组长私下跟我抱怨，说这个目标绝对不可能完成。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "一线销售往往对市场行情敏感，担忧很正常。"},
            {"evidence_id": "E05", "speaker": "user", "text": "但我认为只要把海外电商渠道跑通，我们组不仅能完成，还能超额达标。"}
        ],
        "must_preserve": [
            "集团领导宣布Q4营收目标上调30%",
            "销售二组组长认为目标绝对不可能完成（转述他国立场）",
            "用户本人认为跑通海外电商渠道不仅能完成且能超额达标"
        ],
        "must_not_infer": [
            "用户认为目标不可能完成",
            "销售二组组长对目标持乐观态度"
        ],
        "must_cohabit": [],
        "must_context": [("用户认为能超额达标", "营收目标上调30%")],
        "must_separate": [("销售二组组长抱怨不可能完成", "用户认为能超额达标")],
        "must_defer": []
    },
    {
        "case_id": "MT-3T-09",
        "category": "condition_branch_accumulation",
        "description": "Nested contingency conditions across three turns",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "如果明天下午不下雨，我们就去江滩踢足球。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "户外踢球很畅快，注意带好护膝。"},
            {"evidence_id": "E03", "speaker": "user", "text": "如果下雨但风不大，就改去室内羽毛球馆。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "室内羽毛球也是很好的备选。"},
            {"evidence_id": "E05", "speaker": "user", "text": "要是既下暴雨又刮大风，大家就都在家线上打游戏。"}
        ],
        "must_preserve": [
            "若不下雨则去江滩踢足球",
            "若下雨但风不大则改室内羽毛球",
            "若既下暴雨又刮大风则在家线上打游戏"
        ],
        "must_not_infer": [
            "已经确定去踢足球",
            "明天一定会下暴雨"
        ],
        "must_cohabit": [
            ("不下雨", "江滩踢足球"),
            ("下雨但风不大", "室内羽毛球"),
            ("既下暴雨又刮大风", "在家线上打游戏")
        ],
        "must_context": [],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-3T-10",
        "category": "plan_scope_tightening",
        "description": "Plan gets progressively tightened with strict boundary conditions",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我想在国庆假期自驾去川西环线旅游。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "川西风景绝美，折多山和新都桥值得去。"},
            {"evidence_id": "E03", "speaker": "user", "text": "同行的小张高反严重，所以海拔超过4000米的点全部剔除。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "避开高海拔垭口，行程会更舒适安全。"},
            {"evidence_id": "E05", "speaker": "user", "text": "还有，全程只能开燃油车，严禁开纯电车，充电排队耗不起。"}
        ],
        "must_preserve": [
            "用户计划国庆假期自驾川西环线",
            "因小张高反剔除所有海拔超过4000米的地点",
            "全程只开燃油车且严禁开纯电车"
        ],
        "must_not_infer": [
            "用户打算开纯电车去川西",
            "小张没有高反"
        ],
        "must_cohabit": [("小张高反严重", "剔除海拔超过4000米的点"), ("全程只开燃油车", "严禁开纯电车")],
        "must_context": [("剔除高海拔点", "川西自驾计划"), ("限制只开燃油车", "川西自驾计划")],
        "must_separate": [],
        "must_defer": []
    },

    # =========================================================================
    # Group 3: 4-5 Turn Dialogues (8 cases)
    # =========================================================================
    {
        "case_id": "MT-4T-01",
        "category": "deep_correction_intervening_shifts",
        "description": "Deadline established in T1, discussed infrastructure in T2-T3, updated in T4",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "项目一期交付截止日期定在10月15日。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "收到，10月15日交付一期。"},
            {"evidence_id": "E03", "speaker": "user", "text": "服务器配置选4核16G应该够支撑初期流量吧？"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "初期流量单机4C16G完全没问题，配合Nginx缓存更稳。"},
            {"evidence_id": "E05", "speaker": "user", "text": "云厂商我们打算在阿里云和腾讯云之间挑一家便宜的。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "两家都有新客优惠券，可以对比一下折扣。"},
            {"evidence_id": "E07", "speaker": "user", "text": "对了，客户通知上线时间提前了，一期交付改到10月10日，云厂商定选AWS。"}
        ],
        "must_preserve": [
            "原定项目一期交付截止日为10月15日",
            "服务器规格考虑4核16G",
            "一期交付日期提前变更为10月10日",
            "云厂商最终确定选用AWS"
        ],
        "must_not_infer": [
            "交付时间仍然是10月15日",
            "云厂商选用阿里云或腾讯云"
        ],
        "must_cohabit": [],
        "must_context": [("交付改到10月10日", "原定交付10月15日"), ("云厂商定选AWS", "挑选阿里云或腾讯云")],
        "must_separate": [("交付改到10月10日", "云厂商定选AWS")],
        "must_defer": []
    },
    {
        "case_id": "MT-4T-02",
        "category": "progressive_constraint_accumulation",
        "description": "5 turns of accumulating rental search constraints",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我想在浦东租一套两居室。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "浦东两居室房源不少，预算大概多少？"},
            {"evidence_id": "E03", "speaker": "user", "text": "月租预算控制在6000元以内，最多不能超过6500元。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "6000-6500元在张江或三林附近挺合适。"},
            {"evidence_id": "E05", "speaker": "user", "text": "必须步行10分钟内到2号线地铁站。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "靠近2号线通勤很方便。楼层和朝向有要求吗？"},
            {"evidence_id": "E07", "speaker": "user", "text": "一楼潮湿顶楼漏水，绝对不要一楼和顶楼。"},
            {"evidence_id": "E08", "speaker": "assistant", "text": "中间楼层更干燥安静。入住时间定了吗？"},
            {"evidence_id": "E09", "speaker": "user", "text": "本月25号前必须搬进去，最晚不能拖过月底。"}
        ],
        "must_preserve": [
            "用户想在浦东租两居室",
            "月租预算控制在6000以内最多不超6500",
            "必须步行10分钟内到2号线地铁站",
            "坚决不要一楼和顶楼",
            "本月25号前必须入住最迟不过月底"
        ],
        "must_not_infer": [
            "用户可以接受一楼或顶楼",
            "预算可以超过7000元"
        ],
        "must_cohabit": [],
        "must_context": [
            ("预算6000-6500", "浦东租两居室"),
            ("步行10分钟到2号线", "浦东租两居室"),
            ("拒绝一楼顶楼", "浦东租两居室"),
            ("25号前入住", "浦东租两居室")
        ],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-4T-03",
        "category": "state_evolution_patient",
        "description": "Tracking patient temperature and symptoms across 5 turns",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "孩子下午发烧到38.8度，精神有点蔫。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "超过38.5度可以考虑吃退烧药，多补充温水。"},
            {"evidence_id": "E03", "speaker": "user", "text": "刚才吃了对乙酰氨基酚，额头贴了退热贴。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "服药后观察半小时到一小时，注意散热。"},
            {"evidence_id": "E05", "speaker": "user", "text": "现在体温降到37.4度了，但是开始有点咳嗽。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "体温降下来是好事，咳嗽有痰还是干咳？"},
            {"evidence_id": "E07", "speaker": "user", "text": "是干咳，晚上睡觉鼻子也塞住了。"},
            {"evidence_id": "E08", "speaker": "assistant", "text": "可以垫高枕头或者用生理盐水喷鼻。"},
            {"evidence_id": "E09", "speaker": "user", "text": "目前完全退烧了（36.7度），精神恢复了，就剩轻微鼻塞。"}
        ],
        "must_preserve": [
            "孩子曾发烧38.8度且精神萎靡",
            "服用了对乙酰氨基酚并贴退热贴",
            "体温先降至37.4度并伴有干咳鼻塞",
            "当前体温完全恢复正常（36.7度）且精神良好，仅余轻微鼻塞"
        ],
        "must_not_infer": [
            "孩子当前仍然处于38.8度高烧状态",
            "孩子咳嗽有浓痰"
        ],
        "must_cohabit": [],
        "must_context": [("退烧至36.7度", "发烧38.8度")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-4T-04",
        "category": "buried_durable_persona_instruction",
        "description": "User sets a system format requirement in turn 2, followed by multiple tasks",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我们开始进行技术选型讨论。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "好的，请随时提出具体方向。"},
            {"evidence_id": "E03", "speaker": "user", "text": "立个规矩：后续所有技术方案对比，必须用三栏Markdown表格呈现（维度、方案A、方案B），严禁纯文本罗列。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "明白，后续所有技术方案对比均严格输出三栏对比表格。"},
            {"evidence_id": "E05", "speaker": "user", "text": "先帮我对比一下FastAPI与Go Gin在高并发场景下的性能表现。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "| 维度 | FastAPI | Go Gin |\n| --- | --- | --- |\n| 吞吐量 | 中高 | 极高 |"},
            {"evidence_id": "E07", "speaker": "user", "text": "再对比一下PostgreSQL和MongoDB在JSON文档检索上的差异。"}
        ],
        "must_preserve": [
            "持久指令：后续所有技术对比必须使用三栏Markdown表格输出",
            "严禁使用纯文本罗列技术对比",
            "用户要求对比FastAPI与Go Gin",
            "用户要求对比PostgreSQL与MongoDB的JSON检索差异"
        ],
        "must_not_infer": [
            "该表格输出规则仅对FastAPI和Gin有效"
        ],
        "must_cohabit": [("必须用三栏Markdown表格呈现", "严禁纯文本罗列")],
        "must_context": [],
        "must_separate": [("Markdown三栏表格规矩", "FastAPI与Gin对比")],
        "must_defer": []
    },
    {
        "case_id": "MT-4T-05",
        "category": "anaphora_chain_candidates",
        "description": "User interviews Zhang and Li, evaluates pros/cons, then hires '后者'",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "今天面试了两位高级前端候选人：张三和李四。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "两位候选人的面试表现如何？"},
            {"evidence_id": "E03", "speaker": "user", "text": "张三算法很强，但沟通比较生硬，要价25k。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "那李四的技术栈和团队协同怎么样？"},
            {"evidence_id": "E05", "speaker": "user", "text": "李四工程经验扎实，沟通顺畅，期望薪资20k。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "综合性价比和团队匹配度，各有所长。"},
            {"evidence_id": "E07", "speaker": "user", "text": "团队目前更需要接地气的协作，我们决定发offer给后者，定薪21k。"}
        ],
        "must_preserve": [
            "面试了张三和李四两位候选人",
            "张三算法强但沟通生硬且要价25k",
            "李四工程扎实沟通顺畅且期望20k",
            "决定向李四（后者）发放offer并定薪21k"
        ],
        "must_not_infer": [
            "决定录用张三",
            "李四定薪25k"
        ],
        "must_cohabit": [],
        "must_context": [("录用李四定薪21k", "李四工程扎实期望20k")],
        "must_separate": [("张三面试评价", "录用李四")],
        "must_defer": []
    },
    {
        "case_id": "MT-4T-06",
        "category": "multiple_cancellations_flip_flop",
        "description": "Group dinner proposals: Hotpot -> Cantonese -> Sichuan -> Japanese",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "周五团建聚餐，我提议去吃海底捞火锅。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "火锅气氛热闹，适合团队聚餐。"},
            {"evidence_id": "E03", "speaker": "user", "text": "老陈痛风发作不能吃高嘌呤，火锅取消，换成顺德粤菜。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "顺德菜清淡健康，照顾到了老陈。"},
            {"evidence_id": "E05", "speaker": "user", "text": "几个湖南同事嫌粤菜太淡没味道，强烈要求改吃川菜。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "川菜和痛风忌口又冲突了，众口难调。"},
            {"evidence_id": "E07", "speaker": "user", "text": "谁也别吵了，最终定下去吃日料放题，既有刺身又有熟食，定案不再改了。"}
        ],
        "must_preserve": [
            "曾提议吃海底捞火锅（因老陈痛风取消）",
            "曾提议顺德粤菜（因湖南同事嫌淡取消）",
            "最终拍板确定去吃日料放题且不再更改"
        ],
        "must_not_infer": [
            "最终聚餐去吃火锅或川菜",
            "老陈同意吃火锅"
        ],
        "must_cohabit": [],
        "must_context": [("最终定日料放题", "提议火锅粤菜")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-4T-07",
        "category": "ambiguous_anaphora_trap",
        "description": "User discusses multiple designs, then asks '那个好吗' -> MUST DEFER",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "UI设计师给APP首页提供了极简黑白和活力彩色两版方案。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "黑白高级感强，彩色对年轻用户吸引力大。"},
            {"evidence_id": "E03", "speaker": "user", "text": "后来产品经理又加了一版沉浸式暗黑主题。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "现在共有三版候选方案了。"},
            {"evidence_id": "E05", "speaker": "user", "text": "运营总监也拿出了海外竞品的拟物化排版方案。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "方案非常多元化，用户群体偏好调研过吗？"},
            {"evidence_id": "E07", "speaker": "user", "text": "你觉得我们采用那个怎么样？"}
        ],
        "must_preserve": [
            "候选UI方案包括极简黑白、活力彩色、沉浸暗黑、拟物化排版",
            "用户询问采用'那个'（指代完全模糊，必须DEFER）"
        ],
        "must_not_infer": [
            "用户指定采用拟物化方案",
            "用户指定采用极简黑白方案"
        ],
        "must_cohabit": [],
        "must_context": [],
        "must_separate": [],
        "must_defer": ["那个"]
    },
    {
        "case_id": "MT-4T-08",
        "category": "complex_negation_limitation_scope",
        "description": "User limits third party claim: 99% accuracy on small test set != production ready",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "算法团队的小赵宣称新模型在测试集上达到了99.2%的准确率。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "99.2%是个非常漂亮的数据，他们准备申请上线了吗？"},
            {"evidence_id": "E03", "speaker": "user", "text": "我今天仔细查验了他们的测试集，发现总共只有80个样本，且全是简单样本。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "样本量太小且缺乏长尾样本，容易过拟合。"},
            {"evidence_id": "E05", "speaker": "user", "text": "所以我明确告知团队：这只能说明模型在极小玩具集上跑通了，绝不代表真实能力达到99%，坚决不能批准上线。"}
        ],
        "must_preserve": [
            "小赵宣称新模型测试集准确率达到99.2%",
            "测试集仅有80个简单样本",
            "用户定性：仅证明在极小玩具集跑通",
            "用户坚决否认模型真实能力达到99%并拒绝批准上线"
        ],
        "must_not_infer": [
            "用户认可模型达到99%准确率",
            "新模型已获准上线"
        ],
        "must_cohabit": [("仅证明在极小玩具集跑通", "绝不代表真实能力达到99%且拒绝上线")],
        "must_context": [("用户否定小赵结论", "小赵宣称准确率99.2%")],
        "must_separate": [],
        "must_defer": []
    },

    # =========================================================================
    # Group 4: 6-8 Turn Long Dialogues (5 cases)
    # =========================================================================
    {
        "case_id": "MT-LT-01",
        "category": "full_lifecycle_project_turns",
        "description": "6 turns project from concept to tech choice, budget shift, timeline change, commit",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我们计划立项自研一个企业内部的实时知识库问答系统。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "立项内部知识库很有价值，初期的核心架构怎么考虑？"},
            {"evidence_id": "E03", "speaker": "user", "text": "底层模型使用Qwen-2.5-72B私有化部署，向量库选Milvus。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "Qwen私有化加上Milvus是成熟可靠的企业级方案。"},
            {"evidence_id": "E05", "speaker": "user", "text": "硬件预算最初批了20万，刚收到通知被财务砍到了12万。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "预算被砍了40%，可能需要考虑量化模型或者减少GPU卡数。"},
            {"evidence_id": "E07", "speaker": "user", "text": "交付时间由原定年底缩短到11月15日必须内部公测。"},
            {"evidence_id": "E08", "speaker": "assistant", "text": "时间紧任务重，需要砍掉一些边缘功能保核心问答链路。"},
            {"evidence_id": "E09", "speaker": "user", "text": "决定了：模型改用Qwen-2.5-32B INT4量化版以适应12万预算，11月15日前只交付文档解析和向量检索两项核心能力。"},
            {"evidence_id": "E10", "speaker": "assistant", "text": "务实的裁剪方案，集中攻坚核心链路。"},
            {"evidence_id": "E11", "speaker": "user", "text": "另外补充一条：所有上传的内部敏感文档严禁调用外部API，必须完全在本地局域网闭环。"}
        ],
        "must_preserve": [
            "立项自研企业内部实时知识库问答系统",
            "预算由原定20万缩减为12万",
            "公测交付时间提前到11月15日",
            "模型最终改为Qwen-2.5-32B INT4量化版",
            "11月15日前只交付文档解析和向量检索",
            "硬性安全约束：敏感文档严禁调用外部API且必须完全在本地局域网闭环"
        ],
        "must_not_infer": [
            "私有化模型依然采用72B非量化版",
            "预算仍然保持20万",
            "可以调用外部商业API处理内部敏感文档"
        ],
        "must_cohabit": [("严禁调用外部API", "必须在本地局域网闭环")],
        "must_context": [("模型改用32B量化版", "预算缩减为12万"), ("公测提前至11月15日", "原定年底公测")],
        "must_separate": [("公测提前至11月15日", "敏感文档局域网闭环约束")],
        "must_defer": []
    },
    {
        "case_id": "MT-LT-02",
        "category": "long_distractor_buried_directive",
        "description": "7 turns: Durable directive set in T2, turns 3-6 discuss news/weather/sports, T7 applies directive",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "今天我们要开启一个长期协作项目。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "随时待命，请明确协作规范。"},
            {"evidence_id": "E03", "speaker": "user", "text": "设定永久规则：以后任何时候只要生成SQL查询，关键字必须大写，字段名必须全部用反引号包裹，且禁止使用SELECT *。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "明白，SQL关键字大写、字段用反引号、严禁SELECT *，已存为永久规则。"},
            {"evidence_id": "E05", "speaker": "user", "text": "今天看欧冠比赛了吗？皇马那场逆转太不可思议了。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "补时绝杀确实跌宕起伏，很有韧性。"},
            {"evidence_id": "E07", "speaker": "user", "text": "明天上海好像要降温到十度左右，秋天一下子就来了。"},
            {"evidence_id": "E08", "speaker": "assistant", "text": "换季温差大，早晚出门记得多穿一件外套。"},
            {"evidence_id": "E09", "speaker": "user", "text": "中午在公司食堂吃的红烧牛肉面，牛肉给得还挺多。"},
            {"evidence_id": "E10", "speaker": "assistant", "text": "食堂厚道能提升一整天的工作幸福感。"},
            {"evidence_id": "E11", "speaker": "user", "text": "回到正题，写个查询用户表订单总额大于1000的SQL。"}
        ],
        "must_preserve": [
            "永久SQL规则：关键字必须大写",
            "永久SQL规则：字段名必须用反引号包裹",
            "永久SQL规则：严禁使用SELECT *",
            "用户要求编写查询订单总额大于1000的SQL"
        ],
        "must_not_infer": [
            "SQL编写规则已被闲聊冲淡失效",
            "可以使用SELECT *"
        ],
        "must_cohabit": [
            ("关键字必须大写", "字段名必须用反引号包裹"),
            ("字段名用反引号包裹", "严禁使用SELECT *")
        ],
        "must_context": [],
        "must_separate": [("永久SQL规则", "用户查询订单SQL任务")],
        "must_defer": []
    },
    {
        "case_id": "MT-LT-03",
        "category": "multi_party_debate_attribution",
        "description": "User reports Alice's opinion, Bob's rebuttal, Charlie's proposal, then makes synthesis decision",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "下午开会就微服务拆分进行了激烈讨论。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "大家主要的分歧点在什么地方？"},
            {"evidence_id": "E03", "speaker": "user", "text": "爱丽丝主张立刻把订单和库存从单体拆分成独立服务。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "拆分后可以独立扩容，但分布式事务复杂度会上升。"},
            {"evidence_id": "E05", "speaker": "user", "text": "鲍勃强烈反对，认为当前日活只有两万，过早拆分就是灾难。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "鲍勃的顾虑很实际，团队人力维护微服务开销很大。"},
            {"evidence_id": "E07", "speaker": "user", "text": "查理提出了折中方案：先保持单体架构，但在代码库内部进行严格的模块化解耦。"},
            {"evidence_id": "E08", "speaker": "assistant", "text": "模块化单体是极佳的过渡方案，进可攻退可守。"},
            {"evidence_id": "E09", "speaker": "user", "text": "我作为技术负责人最终拍板：采纳查理的模块化单体方案，半年内严禁拆分独立微服务。"}
        ],
        "must_preserve": [
            "爱丽丝主张立即拆分订单与库存为独立微服务（第三方立场）",
            "鲍勃强烈反对拆分微服务（第三方立场）",
            "查理提议先采用模块化单体方案（第三方立场）",
            "用户作为负责人最终拍板采纳查理的模块化单体方案",
            "硬性规定半年内严禁拆分独立微服务"
        ],
        "must_not_infer": [
            "用户赞成立刻拆分为微服务",
            "鲍勃赞成微服务拆分"
        ],
        "must_cohabit": [("采纳查理的模块化单体方案", "半年内严禁拆分独立微服务")],
        "must_context": [("用户采纳查理方案", "查理提议模块化单体")],
        "must_separate": [("爱丽丝主张", "鲍勃反对"), ("鲍勃反对", "用户拍板方案")],
        "must_defer": []
    },
    {
        "case_id": "MT-LT-04",
        "category": "multi_step_car_purchase_updates",
        "description": "6 turns car purchase: budget changed in T2, model changed in T4, payment changed in T5, delivery T6",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "我准备年底买辆新车，预算定在25万左右。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "25万预算选择很多，看重轿车还是SUV？"},
            {"evidence_id": "E03", "speaker": "user", "text": "老婆把年终奖拿出来了，预算提高到35万。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "预算提升到35万，豪华品牌或高端新能源都可以看了。"},
            {"evidence_id": "E05", "speaker": "user", "text": "本来想买宝马3系，试驾后觉得后排太硬，决定买理想L7。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "理想L7空间大且适合家用，舒适度确实比3系强。"},
            {"evidence_id": "E07", "speaker": "user", "text": "付款方式原想全款，销售说有两年免息贷款，决定办分期贷款。"},
            {"evidence_id": "E08", "speaker": "assistant", "text": "免息分期资金利用率更高，很划算。"},
            {"evidence_id": "E09", "speaker": "user", "text": "合同已签，交了1万定金，销售保证下个月20号前提车。"}
        ],
        "must_preserve": [
            "买车预算由25万提升到35万",
            "放弃宝马3系并最终决定购买理想L7",
            "付款方式由全款改为两年免息分期贷款",
            "合同已签且已交1万定金",
            "销售承诺下个月20号前提车"
        ],
        "must_not_infer": [
            "最终决定购买宝马3系",
            "采用全款支付",
            "预算仍然是25万"
        ],
        "must_cohabit": [("已签合同", "已交1万定金"), ("已交定金", "承诺下月20号前提车")],
        "must_context": [("预算提高到35万", "预算定在25万"), ("决定买理想L7", "想买宝马3系"), ("决定分期贷款", "原想全款")],
        "must_separate": [],
        "must_defer": []
    },
    {
        "case_id": "MT-LT-05",
        "category": "mixed_anaphora_resolve_and_defer",
        "description": "8 turns: Multiple items introduced, several resolved, one remains ambiguous -> MUST resolve resolved and DEFER ambiguous",
        "dialogue": [
            {"evidence_id": "E01", "speaker": "user", "text": "公司准备采购三批设备：第一批是开发用MacBook Pro，第二批是设计用Dell显示器，第三批是会议室投影仪。"},
            {"evidence_id": "E02", "speaker": "assistant", "text": "三批设备分工明确，供应商都联系了吗？"},
            {"evidence_id": "E03", "speaker": "user", "text": "苹果直营店已经给了企业折扣，第一批设备今天下午直接下单。"},
            {"evidence_id": "E04", "speaker": "assistant", "text": "第一批MacBook落实得很快。显示器和投影仪呢？"},
            {"evidence_id": "E05", "speaker": "user", "text": "Dell代理商那边缺货，第二批设备延期到下个月中旬采购。"},
            {"evidence_id": "E06", "speaker": "assistant", "text": "那第三批会议室投影仪的选型定了吗？"},
            {"evidence_id": "E07", "speaker": "user", "text": "投影仪我们看了爱普生和明基两个品牌。"},
            {"evidence_id": "E08", "speaker": "assistant", "text": "两家都是老牌投影大厂，流明和色彩表现如何？"},
            {"evidence_id": "E09", "speaker": "user", "text": "爱普生流明高但体积大，明基色彩好但价格贵。"},
            {"evidence_id": "E10", "speaker": "assistant", "text": "会议室遮光好的话色彩更重要，遮光一般就需要高流明。"},
            {"evidence_id": "E11", "speaker": "user", "text": "会议室采光太强，第三批投影仪我们决定采购前者。"},
            {"evidence_id": "E12", "speaker": "assistant", "text": "选爱普生高流明保证强光下看得清。"},
            {"evidence_id": "E13", "speaker": "user", "text": "还有，行政刚才又提了一个神秘的补充采购需求，我们觉得还是买那个算了。"}
        ],
        "must_preserve": [
            "第一批MacBook Pro今天下午下单采购",
            "第二批Dell显示器因缺货延期至下月中旬采购",
            "第三批投影仪在爱普生与明基中决定选购前者（爱普生）",
            "行政提出的补充采购需求中'买那个算了'（指代不明，必须DEFER）"
        ],
        "must_not_infer": [
            "第三批投影仪决定采购明基",
            "第一批设备延期采购"
        ],
        "must_cohabit": [],
        "must_context": [("投影仪决定采购爱普生", "爱普生流明高明基色彩好")],
        "must_separate": [("第一批MacBook下单", "第二批Dell延期"), ("第三批选爱普生", "行政补充采购买那个")],
        "must_defer": ["那个（行政神秘补充采购需求）"]
    }
]


def main():
    cases_file = HERE / "cases_multiturn_v1.json"
    gt_file = HERE / "ground_truth_multiturn_v1.json"

    # Separate public cases and ground truth
    clean_cases = []
    ground_truth = {}

    for c in CASES:
        clean_cases.append({
            "case_id": c["case_id"],
            "category": c["category"],
            "description": c["description"],
            "dialogue": c["dialogue"],
        })
        ground_truth[c["case_id"]] = {
            "must_preserve": c["must_preserve"],
            "must_not_infer": c["must_not_infer"],
            "must_cohabit": c["must_cohabit"],
            "must_context": c["must_context"],
            "must_separate": c["must_separate"],
            "must_defer": c["must_defer"],
        }

    cases_file.write_text(json.dumps(clean_cases, ensure_ascii=False, indent=2), encoding="utf-8")
    gt_file.write_text(json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(clean_cases)} multi-turn test cases in {cases_file}")
    print(f"Generated ground truth in {gt_file}")


if __name__ == "__main__":
    main()
