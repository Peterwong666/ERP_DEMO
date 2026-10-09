export type Urgency = 'emergency' | 'suggest' | 'normal'

export interface ReplenishmentSuggestion {
  suggestion_id: number
  product_id: number
  sku_code: string
  name: string
  current_stock: number
  qty_in_transit: number
  forecast_7d: number
  suggested_qty: number
  days_cover: number | null
  urgency: Urgency
  generated_at: string
}

export const URGENCY_LABELS: Record<Urgency, string> = {
  emergency: '紧急',
  suggest: '建议',
  normal: '正常',
}
