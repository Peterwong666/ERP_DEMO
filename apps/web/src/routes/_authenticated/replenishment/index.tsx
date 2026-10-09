import { createFileRoute } from '@tanstack/react-router'
import { ReplenishmentPage } from '@/features/replenishment/replenishment-page'

export const Route = createFileRoute('/_authenticated/replenishment/')({
  component: ReplenishmentPage,
})
