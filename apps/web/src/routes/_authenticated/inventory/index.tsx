import { createFileRoute } from '@tanstack/react-router'
import { InventoryPage } from '@/features/inventory/inventory-page'

export const Route = createFileRoute('/_authenticated/inventory/')({
  component: InventoryPage,
})
