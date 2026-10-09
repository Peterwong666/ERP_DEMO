export interface DefectShare {
  reason_code: string
  reason_label: string
  qty: number
}

export interface DashboardData {
  open_po_count: number
  pending_qc_count: number
  inbound_today_qty: number
  available_sku_count: number
  qc_pass_rate: number
  qc_inspected_today: number
  qc_passed_today: number
  low_stock_count: number
  suggestion_count: number
  defect_total_today: number
  defect_shares: DefectShare[]
  inbound_last_7d: number[]
  anchor_date: string
}
