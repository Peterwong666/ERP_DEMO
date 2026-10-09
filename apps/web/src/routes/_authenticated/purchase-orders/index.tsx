import { createFileRoute } from '@tanstack/react-router'
import { PurchaseOrdersPage } from '@/features/purchase-orders/purchase-orders-page'

export const Route = createFileRoute('/_authenticated/purchase-orders/')({
  component: PurchaseOrdersPage,
})
