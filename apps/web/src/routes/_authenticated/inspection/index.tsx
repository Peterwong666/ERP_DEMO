import { createFileRoute } from '@tanstack/react-router'
import { InspectionPage } from '@/features/inspection/inspection-page'

export const Route = createFileRoute('/_authenticated/inspection/')({
  component: InspectionPage,
})
