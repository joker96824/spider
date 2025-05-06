# 卡牌技能系统规则文档

## 1. 技能系统概述

### 1.1 技能类型
- ACTIVE（主动技能）：需要玩家主动发动的技能
- AUTO（自动技能）：满足条件自动触发的技能
- CONTINUOUS（持续技能）：持续生效的技能

### 1.2 技能结构
```json
{
  "skill_id": "BT07-001-ACT",
  "skill_type": "ACTIVE",
  "activation_phase": ["MAIN_PHASE"],
  "activation_cost": {"CB": 1},
  "limitation": {"per_turn": 1},
  "skill_script": "optional_lua_script",
  "effects": [
    {
      "effect_id": "BT07-001-ACT-EFF1",
      "effect_category": "RULE_MODIFY",
      "sub_category": "IGNORE_GB_RULE",
      "parameters": {...},
      "resolution_rule": "CHAIN_RESOLVE",
      "priority": 1024,
      "execution_order": 1
    }
  ]
}
```

## 2. 技能属性说明

### 2.1 技能ID（skill_id）
- 格式：`{卡牌ID}-{技能类型}`
- 示例：`BT07-001-ACT`
- 规则：必须唯一，用于标识具体技能

### 2.2 技能类型（skill_type）
- ACTIVE：主动技能
  - 需要玩家主动发动
  - 可以设置激活阶段和费用
  - 可以设置使用限制
- AUTO：自动技能
  - 满足条件自动触发
  - 可以设置触发条件
  - 可以设置触发时机
- CONTINUOUS：持续技能
  - 持续生效
  - 可以设置生效条件
  - 可以设置持续时间

### 2.3 激活阶段（activation_phase）
- 数组格式，可包含多个阶段
- 可选值：
  - MAIN_PHASE（主要阶段）
  - BATTLE_PHASE（战斗阶段）
  - END_PHASE（结束阶段）
  - RIDE_PHASE（超越阶段）
  - STRIDE_PHASE（超越阶段）

### 2.4 激活成本（activation_cost）
- JSON格式，可包含多种费用
- 费用类型：
  - CB：计数爆发
  - SB：灵魂爆发
  - EB：能量爆发
  - HAND：手牌
  - SOUL：灵魂
  - DROP：弃牌区
  - DECK：牌堆
  - G_ZONE：时空区

### 2.5 使用限制（limitation）
- JSON格式，可设置多种限制
- 限制类型：
  - per_turn：每回合次数
  - per_game：每局游戏次数
  - per_phase：每阶段次数
  - condition：条件限制

## 3. 效果系统

### 3.1 效果类别（effect_category）
- RULE_MODIFY：规则修改
- DECK_OPERATION：牌堆操作
- COST_MODIFY：费用修改
- STAT_MODIFY：数值修改
- UNIT_OPERATION：单位操作
- ZONE_OPERATION：区域操作
- STATE_MODIFY：状态修改
- NAME_MODIFY：名称修改
- ABILITY_GRANT：能力赋予
- TRIGGER_ADD：触发添加
- DAMAGE_OPERATION：伤害操作
- SOUL_OPERATION：灵魂操作
- HAND_OPERATION：手牌操作
- DROP_OPERATION：弃牌区操作

### 3.2 解析规则（resolution_rule）
- CHAIN_RESOLVE：链式解析
  - 效果按顺序依次解析
  - 每个效果解析完成后才能解析下一个
- SIMULTANEOUS：同时解析
  - 所有效果同时解析
  - 适用于需要同时处理的效果
- OPTIONAL_CHAIN：可选链式
  - 可以选择是否继续解析链
  - 适用于可选效果
- SELECT_ONE：选择其一
  - 从多个效果中选择一个执行
- SELECT_ALL：全选
  - 执行所有效果

### 3.3 优先级（priority）
- 数值范围：0-65535
- 默认值：1024
- 规则：
  - 数值越大优先级越高
  - 相同优先级按执行顺序处理
  - 0表示最低优先级

### 3.4 执行顺序（execution_order）
- 范围：1-255
- 规则：
  - 同一技能内的效果按顺序执行
  - 1表示最先执行
  - 255表示最后执行

## 4. 示例

### 4.1 主动技能示例
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

### 4.2 自动技能示例
```json
{
  "skill_id": "BT07-001-AUTO",
  "skill_type": "AUTO",
  "trigger_condition": "DISCARD_FOR_STRIDE",
  "effects": [
    {
      "effect_id": "BT07-001-AUTO-EFF1",
      "effect_category": "COST_MODIFY",
      "sub_category": "REDUCE_COUNTER_BLAST",
      "parameters": {
        "reduction_value": 1,
        "application_scope": "NEXT_PAYMENT",
        "target_card": "VANGUARD_OR_CORE"
      },
      "resolution_rule": "CHAIN_RESOLVE",
      "priority": 1024,
      "execution_order": 1
    }
  ]
}
```

### 4.3 持续技能示例
```json
{
  "skill_id": "BT05-EX01-PERM",
  "skill_type": "CONTINUOUS",
  "condition": {
    "type": "FASHION_MAGIC_COUNT",
    "value": 1,
    "comparison": ">="
  },
  "effects": [
    {
      "effect_id": "BT05-EX01-PERM-EFF1",
      "effect_category": "STAT_MODIFY",
      "sub_category": "POWER_INCREASE",
      "parameters": {
        "value": 5000
      },
      "resolution_rule": "SIMULTANEOUS",
      "priority": 1024,
      "execution_order": 1
    }
  ]
}
```

## 5. 注意事项

1. 技能ID必须唯一
2. 效果ID必须唯一
3. 优先级数值越大越优先
4. 执行顺序数值越小越先执行
5. 参数必须符合效果类型的要求
6. 解析规则必须符合效果类型的要求
7. 技能脚本必须符合Lua/Python语法
8. 所有JSON字段必须符合规范

## 6. 扩展建议

1. 可以添加新的技能类型
2. 可以添加新的效果类别
3. 可以添加新的解析规则
4. 可以扩展参数结构
5. 可以添加新的限制类型
6. 可以添加新的费用类型
7. 可以添加新的触发条件
8. 可以添加新的执行规则 