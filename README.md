
# 卡牌数据爬虫

## 项目说明
本项目用于爬取卡牌数据并生成SQL文件，支持将数据导入到PostgreSQL数据库中。

## 功能特点
- 自动爬取卡牌链接和详细信息
- 下载卡牌图片
- 生成PostgreSQL SQL文件
- 支持数据更新和版本控制
- 支持技能效果的JSON格式存储

## 数据库结构

### Card表
存储卡牌的基本信息，包括：
- `id`: UUID主键
- `card_code`: 卡牌代码（非空）
- `card_link`: 卡牌链接（非空）
- `card_number`: 卡牌编号
- `card_rarity`: 卡牌罕贵度
- `name_cn`: 中文名称
- `name_jp`: 日文名称
- `nation`: 所属国家
- `clan`: 所属种族
- `grade`: 等级
- `skill`: 技能
- `card_power`: 力量值
- `shield`: 护盾值
- `critical`: 暴击值
- `special_mark`: 特殊标识
- `card_type`: 卡片类型
- `trigger_type`: 触发类型
- `ability`: 能力描述
- `card_alias`: 卡牌别称
- `card_group`: 所属集团
- `ability_json`: 技能效果JSON数据（JSONB类型，默认NULL）
- `create_user_id`: 创建用户
- `update_user_id`: 更新用户
- `create_time`: 创建时间
- `update_time`: 更新时间
- `is_deleted`: 是否删除
- `card_version`: 版本号
- `remark`: 备注信息

### CardRarity表
存储卡牌的稀有度相关信息，包括：
- `id`: UUID主键
- `card_id`: 关联的卡牌ID
- `pack_name`: 卡包名称
- `card_number`: 卡包内编号
- `release_info`: 收录信息
- `quote`: 卡牌台词
- `illustrator`: 绘师
- `image_url`: 卡牌图片URL
- `create_time`: 创建时间
- `update_time`: 更新时间

## 技能效果JSON格式
`ability_json`列使用JSONB类型存储技能效果数据，格式如下：
```json
{
  "skill_id": "BT07-001-ACT",
  "skill_type": "ACTIVE",
  "activation_phase": ["MAIN_PHASE"],
  "activation_cost": {"CB": 1},
  "limitation": {"per_turn": 1},
  "effects": [
    {
      "effect_id": "BT07-001-ACT-EFF1",
      "effect_category": "RULE_MODIFY",
      "sub_category": "IGNORE_GB_RULE",
      "parameters": {
        "rule_key": "GB_EFFECT_BY_G_UNITS",
        "override_type": "FULL_IGNORE"
      },
      "resolution_rule": "CHAIN_RESOLVE",
      "priority": 1024,
      "execution_order": 1
    }
  ]
}
```

## 使用方法

### 环境要求
- Python 3.8+
- 相关Python包（见requirements.txt）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行爬虫
```bash
python main.py
```

### 操作指南
按钮功能依次为
1.获取所有卡片的链接
2.根据链接依次爬取数据
3.根据爬好的数据依次下载图片
4.将数据处理后生成sql文件用于导入psql

## 注意事项
1. 确保数据库连接配置正确
2. 爬取过程中请遵守网站的robots.txt规则
3. 建议定期备份数据库
4. 技能效果JSON数据需要符合预定义的格式

## 更新日志
- 2024-03-xx: 添加ability_json列，支持技能效果的JSON格式存储
- 2024-03-xx: 初始版本发布
