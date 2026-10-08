import { createFileRoute } from '@tanstack/react-router'
import { PagePlaceholder } from '@/components/layout/page-placeholder'

export const Route = createFileRoute('/_authenticated/purchase-orders/')({
  component: PurchaseOrdersPage,
})

function PurchaseOrdersPage() {
  return <PagePlaceholder title='采购管理' phase='阶段 5' />
}
