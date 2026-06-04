"use client"

import { ReliabilityVisualization } from "@/components/reliability/reliability-viz"
import { useAgentStore } from "@/store/useAgentStore"
import { Shield, Users, FileBarChart, Activity, ExternalLink, ArrowUpRight } from "lucide-react"

export default function DashboardPage() {
    const { agents } = useAgentStore()

    const stats = [
        { name: "Total Research Runs", value: "1,284", icon: FileBarChart, trend: "+12.5%" },
        { name: "Active Agents", value: agents.length.toString(), icon: Users, trend: "Stable" },
        { name: "Avg. Trust Score", value: "88.2%", icon: Shield, trend: "+2.1%" },
        { name: "System Uptime", value: "99.98%", icon: Activity, trend: "Nominal" },
    ]

    return (
        <div className="p-6 max-w-7xl mx-auto w-full space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">System Dashboard</h1>
                <p className="text-muted-foreground text-sm">Real-time overview of ASTRA AI performance and reliability.</p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat) => (
                    <div key={stat.name} className="glass p-5 rounded-2xl space-y-3">
                        <div className="flex items-center justify-between">
                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                <stat.icon className="w-5 h-5 text-primary" />
                            </div>
                            <span className="text-xs font-bold text-green-500 flex items-center gap-0.5">
                                {stat.trend} <ArrowUpRight className="w-3 h-3" />
                            </span>
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground font-medium">{stat.name}</p>
                            <h2 className="text-2xl font-bold">{stat.value}</h2>
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Analytics */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="glass rounded-2xl p-6 min-h-[300px] flex flex-col justify-between">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-semibold">Research Volume (24h)</h3>
                            <select className="bg-secondary text-xs rounded-md px-2 py-1 outline-none border border-border">
                                <option>Last 24 Hours</option>
                                <option>Last 7 Days</option>
                            </select>
                        </div>
                        <div className="flex-1 flex items-end gap-2 px-2">
                            {[40, 25, 45, 30, 55, 70, 45, 60, 35, 50, 65, 80].map((h, i) => (
                                <div
                                    key={i}
                                    className="flex-1 bg-primary/20 hover:bg-primary/40 transition-all rounded-t-sm"
                                    style={{ height: `${h}%` }}
                                />
                            ))}
                        </div>
                        <div className="flex justify-between mt-2 text-[10px] text-muted-foreground font-mono">
                            <span>00:00</span>
                            <span>06:00</span>
                            <span>12:00</span>
                            <span>18:00</span>
                            <span>23:59</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="glass p-5 rounded-2xl">
                            <h3 className="font-semibold mb-4 text-sm">Source Distribution</h3>
                            <div className="space-y-3">
                                {[
                                    { name: "Government (.gov)", val: 45 },
                                    { name: "Educational (.edu)", val: 30 },
                                    { name: "Peer Reviewed", val: 20 },
                                    { name: "News/Media", val: 5 },
                                ].map(s => (
                                    <div key={s.name} className="space-y-1">
                                        <div className="flex justify-between text-[11px]">
                                            <span>{s.name}</span>
                                            <span className="font-bold">{s.val}%</span>
                                        </div>
                                        <div className="w-full bg-muted h-1 rounded-full overflow-hidden">
                                            <div className="bg-primary h-full" style={{ width: `${s.val}%` }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="glass p-5 rounded-2xl">
                            <h3 className="font-semibold mb-4 text-sm">Reliability Health</h3>
                            <ReliabilityVisualization trustScore={0.88} confidenceScore={0.92} className="border-none p-0 bg-transparent backdrop-blur-none" />
                        </div>
                    </div>
                </div>

                {/* Recent Activity */}
                <div className="glass rounded-2xl p-6 space-y-6 flex flex-col">
                    <div className="flex items-center justify-between">
                        <h3 className="font-semibold">Recent Reports</h3>
                        <button className="text-primary text-xs font-semibold hover:underline flex items-center gap-1">
                            View All <ExternalLink className="w-3 h-3" />
                        </button>
                    </div>
                    <div className="space-y-4 flex-1">
                        {[
                            { title: "Q3 Market Impact Analysis", time: "2 min ago", type: "Financial" },
                            { title: "Neuro-plasticity Synthesis", time: "15 min ago", type: "Medical" },
                            { title: "Smart Grid Security Audit", time: "1h ago", type: "Tech" },
                            { title: "Global Supply Chain Risks", time: "3h ago", type: "Logistics" },
                        ].map((report, i) => (
                            <div key={i} className="flex items-center gap-3 p-3 rounded-xl hover:bg-muted/50 transition-colors cursor-pointer group">
                                <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center shrink-0 border border-border group-hover:border-primary/30">
                                    <FileBarChart className="w-5 h-5 text-muted-foreground" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium truncate">{report.title}</p>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] text-muted-foreground">{report.time}</span>
                                        <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-bold uppercase tracking-widest">{report.type}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="pt-4 border-t border-border">
                        <div className="p-4 rounded-xl active-gradient text-white">
                            <p className="text-xs font-bold mb-1">PRO TIP</p>
                            <p className="text-[11px] leading-relaxed opacity-90">
                                You can now export reports directly to PDF or JSON for external auditing.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
