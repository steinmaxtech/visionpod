import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Car, 
  Activity, 
  Building2, 
  Cpu, 
  Settings,
  Shield,
  ChevronDown
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: React.ReactNode;
  propertyName?: string;
  onPropertyChange?: () => void;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Plates', href: '/plates', icon: Car },
  { name: 'Events', href: '/events', icon: Activity },
  { name: 'Devices', href: '/devices', icon: Cpu },
  { name: 'Properties', href: '/properties', icon: Building2 },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Layout({ children, propertyName = 'All Properties' }: LayoutProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-void flex">
      {/* Sidebar */}
      <aside className="w-64 bg-surface border-r border-border flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-border">
          <Shield className="w-8 h-8 text-accent mr-3" />
          <div>
            <span className="font-semibold text-text-primary">SteinMax</span>
            <span className="text-text-muted ml-1">Vision</span>
          </div>
        </div>

        {/* Property Selector */}
        <div className="p-4 border-b border-border">
          <button className="w-full flex items-center justify-between px-3 py-2 bg-surface-raised border border-border rounded-md hover:border-border-strong transition-colors">
            <span className="text-sm text-text-primary truncate">{propertyName}</span>
            <ChevronDown className="w-4 h-4 text-text-muted flex-shrink-0" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                  isActive
                    ? 'bg-accent/10 text-accent'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-raised'
                )}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
              <span className="text-accent text-sm font-medium">SC</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-primary truncate">SteinMax Corp</p>
              <p className="text-xs text-text-muted">Admin</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
