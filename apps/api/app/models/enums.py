from enum import StrEnum


class SupplierStatus(StrEnum):
    active = "合作中"
    inactive = "已停用"


class ProductCategory(StrEnum):
    electronics = "电子"
    bags = "包袋"
    home = "家居"
    apparel = "服饰"
    beauty = "美妆"
    toys = "玩具"


class ProductStatus(StrEnum):
    developing = "开发中"
    on_sale = "在售"
    discontinued = "停售"


class POStatus(StrEnum):
    draft = "草稿"
    ordered = "已下单"
    partial_received = "部分收货"
    received = "已收货"
    closed = "已关闭"
    cancelled = "已取消"


class ReceivingStatus(StrEnum):
    pending_inspection = "待质检"
    inspecting = "质检中"
    completed = "已完成"


class InspectionStatus(StrEnum):
    pending_inspection = "待质检"
    inspecting = "质检中"
    completed = "已完成"


class DefectReason(StrEnum):
    scratch = "外观划伤"
    functional = "功能异常"
    packaging = "包装破损"
    dimension = "尺寸偏差"
    label = "标签错误"
    other = "其他"


class StockType(StrEnum):
    available = "available"
    pending = "pending"
    defective = "defective"


class TxnType(StrEnum):
    recv_inbound = "收货入库"
    qc_pass = "质检合格"
    qc_fail = "质检不良"
    manual_adjust = "手工调整"
    adjust_outbound = "调整出库"


class SettingValueType(StrEnum):
    int = "int"
    float = "float"
    enum = "enum"


class SettingCategory(StrEnum):
    stock_alert = "库存预警"
    replenishment = "AI 补货"
    qc = "质检"
    caliber = "业务口径"


class Urgency(StrEnum):
    normal = "正常"
    suggest = "建议"
    emergency = "紧急"
