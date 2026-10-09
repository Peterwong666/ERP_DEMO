import {
  Boxes,
  ClipboardCheck,
  LayoutDashboard,
  Package,
  PackageCheck,
  ShoppingCart,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: '供应链运营',
    email: 'peterwong@example.com',
    avatar: '/avatars/peter.svg',
  },
  teams: [],
  navGroups: [
    {
      title: '供应链',
      items: [
        { title: '数据看板', url: '/', icon: LayoutDashboard },
        { title: '新品管理', url: '/products', icon: Package },
        { title: '采购管理', url: '/purchase-orders', icon: ShoppingCart },
        { title: '收货管理', url: '/receiving', icon: PackageCheck },
        { title: '质检管理', url: '/inspection', icon: ClipboardCheck },
        { title: '库存管理', url: '/inventory', icon: Boxes },
        { title: '补货管理', url: '/replenishment', icon: TrendingUp },
        { title: 'AI 供应链', url: '/ai-supply', icon: Sparkles },
      ],
    },
  ],
}
