export type POStatus =
  | 'draft'
  | 'ordered'
  | 'partial_received'
  | 'received'
  | 'closed'
  | 'cancelled'

export interface POLine {
  item_id: number
  product_id: number
  qty_ordered: number
  qty_received: number
  unit_price: string
}

export interface PurchaseOrder {
  po_id: number
  po_no: string
  supplier_id: number
  status: POStatus
  total_amount: string
  order_date: string | null
  expected_date: string | null
  notes: string | null
  created_by: string
  items: POLine[]
}

export interface SupplierOption {
  supplier_id: number
  code: string
  name: string
  lead_time_days: number
  status: string
}

export type POFormLine = {
  product_id: string
  qty_ordered: string
  unit_price: string
}

export type POFormValues = {
  supplier_id: string
  notes: string
  lines: POFormLine[]
}

export const PO_STATUS_LABELS: Record<POStatus, string> = {
  draft: '草稿',
  ordered: '已下单',
  partial_received: '部分收货',
  received: '已收货',
  closed: '已关闭',
  cancelled: '已取消',
}

export const EMPTY_PO_FORM: POFormValues = {
  supplier_id: '',
  notes: '',
  lines: [{ product_id: '', qty_ordered: '', unit_price: '' }],
}
