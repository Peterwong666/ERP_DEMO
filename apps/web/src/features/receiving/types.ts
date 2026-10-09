export type RecvStatus = 'pending_inspection' | 'inspecting' | 'completed'

export interface ReceivingItem {
  recv_item_id: number
  po_item_id: number
  product_id: number
  qty_received: number
}

export interface ReceivingOrder {
  recv_id: number
  recv_no: string
  po_id: number
  status: RecvStatus
  received_at: string
  operator: string
  notes: string | null
  items: ReceivingItem[]
}

export interface RecvFormLine {
  po_item_id: number
  product_id: number
  qty_received: string
}

export const RECV_STATUS_LABELS: Record<RecvStatus, string> = {
  pending_inspection: '待质检',
  inspecting: '质检中',
  completed: '已完成',
}
