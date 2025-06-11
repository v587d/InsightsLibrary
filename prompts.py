from config import config

class Prompts:
    # 所有提示模板存储在这里
    _prompt_templates = {
        # Qwen VL 模型的提示模板
        config.vlm_model_name: {
            "v1": {
                "system": """作为文档解析专家，请完整描述此页面内容。**不能遗漏任何有效信息**。必须按以下步骤执行任务，并根据输出JSON格式：
## 步骤
1. 分析该页面属性：封面、目录、正文、作者介绍、免责申明（条款）、联系方式、封底、其他。
2. 分析该页面标题：优先完整摘抄文档中首要标题。若无则根据文档内容，你拟定一个 **不超过20个字** 的标题。
3. 完整摘抄文档正文中文字部分，务必分析文档正文中 **"不规则图形（含标题）"**、**"不规则表格（含标题"**，并根据你的理解总结"不规则图形"、"不规则表格"中核心要点和关键数据。
4. 校验步骤<3>的内容完整涵盖了步骤<2>的描述，若缺少，请补充完整。
5. 当页面属性是 **正文** 时，用不超过100个字总结该页面摘要。**其他页面属性不用总结**。
6. 总结 **不超过10个字** 关键词。

## 自动过滤页面中水印、页码、作者企业等和页面主题无关的内容

## 输出`JSON`格式
{
  property: str = 以下枚举值取其一 `["cover","index","main","author_introduction","disclaimer","contact","back_cover","others"]`,
  title: str,
  content: str,
  abstract: Optional[str] = "",
  keywords: list[str],
}""",
                "user": "完整描述这页文档的内容，**不能遗漏任何有效信息**，并按系统提示语规定的`JSON`格式返回。"
            },
            "v2":{
                "system": """作为文档解析专家，请使用文档中的语种完整描述此页面内容。**不能遗漏任何有效信息**。必须按以下步骤执行任务，并根据输出JSON格式返回：
## 步骤
1. 分析该页面属性：封面、目录、正文、参考文献、作者介绍、免责申明（条款）、联系方式、附录、封底、其他。
2. 分析该页面标题：优先完整摘抄文档中首要标题。若无则根据文档内容，你用文档中的语种拟定一个 **不超过20个tokens** 的标题。
3. 完整摘抄文档正文中文字部分，务必分析文档正文中 **"不规则图形（含标题）"**、**"不规则表格（含标题"**，并根据你的理解总结"不规则图形"、"不规则表格"中核心要点和关键数据。
4. 校验步骤<3>的内容完整涵盖了步骤<2>的描述，若缺少，请补充完整。
5. 当页面属性是 **正文** 时，用不超过100个tokens总结该页面摘要。**其他页面属性不用总结**。
6. 总结 **不超过15个tokens** 关键词。

## 自动过滤页面中水印、页码、作者企业等和页面主题无关的内容

## 输出`JSON`格式
{
  property: str = 以下枚举值取其一 `["cover","index","main","references","author_introduction","disclaimer","contact","appendix","back_cover","others"]`,
  title: str, 
  content: str, 
  abstract: Optional[str] = "", 
  keywords: list[str], 
}""",
                "user": "请使用文档中的语种完整描述这页文档的内容，**不能遗漏任何有效信息**，并按系统提示语规定的`JSON`格式返回。",
                "log": "优化v1，适配多语种"
            }
        },

        "keywords_extractor": {
            "v1": {
                "system": """请从用户问题中提取不超过20个关键词，并返回JSON格式。
## 关键词要求
  1. 每个关键词需同时有中文和英文两个版本
  2. 每个关键词不超过15个tokens
## 示例
用户输入: "2025年人工智能智能体在企业级应用场景的发展前景如何"
你的输出: {
  "keywords_zh":["2025", "人工智能", "智能体", "企业级", "应用场景", "发展场景"],
  "keywords_en":["2025", "AI", "Agent", "enterprise-level", "application scenarios", "future prospects"]
}"""
            },
        },
        "coarse_filter": {
            "v1": {
                "system": """请根据用户查询<user_query>和拆分后的查询<sub_query>，根据以下材料的标题和关键字，运用推理能力，判断该材料的全文是否与查询条件相关，并返回`JSON`格式。
## 输出`JSON`格式
{
  "file_id": str <照抄>
  "file_name": str <照抄>
  "relevant": bool <根据材料标题和关键词，预测该材料是否与用户查询和拆分后的查询相关，可能相关则为true>
  "reason": str <言简意赅阐述你为何判断相关的理由，和重点关注哪些关键词，不超过100个tokens>
  "confidence_level": int <取值范围为0到100，你需量化相关程度，越相关此值越高，不相关则为0>
}"""
            },
        }
        # 其他模型的提示模板可以在这里添加
    }

    @classmethod
    def get_prompt(cls, model_name: str, version: str = "latest") -> dict:
        """
        获取指定模型和版本的提示模板

        Args:
            model_name: 模型名称 (e.g., "qwen-vl-72b-instruct")
            version: 提示版本，默认为"latest"

        Returns:
            dict: 包含"system"和"user"键的提示字典

        Raises:
            ValueError: 如果找不到指定的模型或版本
        """
        # 检查模型是否存在
        if model_name not in cls._prompt_templates:
            raise ValueError(f"未找到模型 '{model_name}' 的提示模板")

        model_versions = cls._prompt_templates[model_name]

        # 处理最新版本请求
        if version == "latest":
            # 获取最新版本号（字典键排序后的最后一个）
            latest_version = sorted(model_versions.keys())[-1]
            return model_versions[latest_version]

        # 检查指定版本是否存在
        if version not in model_versions:
            raise ValueError(f"模型 '{model_name}' 未找到版本 '{version}' 的提示模板")

        return model_versions[version]

if __name__ == "__main__":
    prompt = Prompts.get_prompt(config.vlm_model_name)
    system_prompt = prompt["system"]
    user_message = prompt["user"]
    print(system_prompt)
    print("-----------------------------------------")
    print(user_message)