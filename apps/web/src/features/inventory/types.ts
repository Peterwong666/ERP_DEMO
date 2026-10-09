export type StockType = 'available' | 'pending' | 'defective'

export type TxnType =
  | 'recv_inbound'
  | 'qc_pass'
  | 'qc_fail'
  | 'manual_adjust'
  | 'adjust_outbound'

export interface InventoryBalance {
  product_id: number
  sku_code: string
  name: string
  qty_available: number
  qty_pending: number
  qty_defective: number
}

export interface InventoryTransaction {
  txn_id: number
  product_id: number
  change_qty: number
  stock_type: StockType
  txn_type: TxnType
  ref_doc_type: string
  ref_doc_no: string
  reason: string | null
  operator: string
  created_at: string
}

export interface ReconciliationRow {
  product_id: number
  stock_type: StockType
  book_qty: number
  ledger_qty: number
}

export interface LowStockRow {
  product_id: number
  sku_code: string
  name: string
  days_cover: number | null
  qty_available: number
  safety_stock: number
}

export interface AdjustForm {
  product_id: string
  change_qty: string
  reason: string
}
