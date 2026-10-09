export type DefectReason =
  | 'scratch'
  | 'functional'
  | 'packaging'
  | 'dimension'
  | 'label'
  | 'other'

export type InspectionStatus = 'pending_inspection' | 'inspecting' | 'completed'

export interface InspectionItem {
  insp_item_id: number
  product_id: number
  qty_inspected: number
  qty_passed: number
  qty_failed: number
}

export interface InspectionOrder {
  insp_id: number
  insp_no: string
  recv_id: number
  status: InspectionStatus
  inspected_at: string | null
  inspector: string
  items: InspectionItem[]
}

export interface DefectFormLine {
  reason_code: DefectReason | ''
  qty: string
}

export interface ItemResultForm {
  insp_item_id: number
  qty_passed: string
  defects: DefectFormLine[]
}

export const DEFECT_REASON_OPTIONS: {
  value: DefectReason
  label: string
}[] = [
  { value: 'scratch', label: '外观划伤' },
  { value: 'functional', label: '功能异常' },
  { value: 'packaging', label: '包装破损' },
  { value: 'dimension', label: '尺寸偏差' },
  { value: 'label', label: '标签错误' },
  { value: 'other', label: '其他' },
]

export const INSP_STATUS_LABELS: Record<InspectionStatus, string> = {
  pending_inspection: '待质检',
  inspecting: '质检中',
  completed: '已完成',
}
