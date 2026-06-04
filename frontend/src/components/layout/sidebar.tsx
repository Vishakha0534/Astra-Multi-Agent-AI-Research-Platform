"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
    LayoutDashboard,
    FlaskConical,
    Activity,
    FileText,
    Settings,
    ShieldCheck
} from "lucide-react"

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Research", href: "/research", icon: FlaskConical },
    { name: "Agent Monitor", href: "/monitor", icon: Activity },
    { name: "Reports", href: "/reports", icon: FileText },
    { name: "Settings", href: "/settings", icon: Settings },
]

export function Sidebar() {
    const pathname = usePathname()

    return (
        <div className="flex flex-col w-64 border-r border-border bg-card/30 backdrop-blur-xl h-screen sticky top-0">
            <div className="p-6 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg active-gradient flex items-center justify-center">
                    <ShieldCheck className="text-white w-5 h-5" />
                </div>
                <span className="text-xl font-bold tracking-tight">ASTRA AI</span>
            </div>

            <nav className="flex-1 px-4 space-y-1">
                {navigation.map((item) => {
                    const isActive = pathname === item.href
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-all duration-200",
                                isActive
                                    ? "bg-primary/10 text-primary"
                                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                            )}
                        >
                            <item.icon className={cn("w-4 h-4", isActive ? "text-primary" : "text-muted-foreground")} />
                            {item.name}
                        </Link>
                    )
                })}
            </nav>

            <div className="p-4 border-t border-border">
                <div className="bg-muted/50 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">System Status</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground leading-tight">
                        All systems nominal. AI Reliability Engines active.
                    </p>
                </div>
            </div>
        </div>
    )
}
