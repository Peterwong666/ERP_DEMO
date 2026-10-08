import { createFileRoute } from '@tanstack/react-router'
import { PagePlaceholder } from '@/components/layout/page-placeholder'

export const Route = createFileRoute('/_authenticated/inventory/')({
  component: InventoryPage,
})

function InventoryPage() {
  return <PagePlaceholder title='库存管理' phase='阶段 8' />
}
