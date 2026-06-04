"use client"

import { FileText, Download, Calendar, Search, Filter, Shield } from "lucide-react"

export default function ReportsPage() {
    const reports = [
        { id: 1, title: "Q3 Market Impact Analysis", date: "2024-03-15", trust: 0.94, size: "12.4 MB", type: "Financial" },
        { id: 2, title: "Neuro-plasticity Synthesis", date: "2024-03-12", trust: 0.88, size: "8.2 MB", type: "Medical" },
        { id: 3, title: "Smart Grid Security Audit", date: "2024-03-10", trust: 0.91, size: "15.1 MB", type: "Technology" },
        { id: 4, title: "Global Supply Chain Risks", date: "2024-03-08", trust: 0.76, size: "22.3 MB", type: "Logistics" },
        { id: 5, title: "Renewable Energy Adoption", date: "2024-03-05", trust: 0.95, size: "10.1 MB", type: "Environmental" },
    ]

    return (
        <div className="p-6 max-w-7xl mx-auto w-full space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Research Reports</h1>
                <p className="text-muted-foreground text-sm">Access and export deep-dive research with verified reliability scores.</p>
            </div>

            <div className="flex flex-col md:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search reports..."
                        className="w-full bg-secondary/50 border border-border rounded-xl py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-primary/50 outline-none"
                    />
                </div>
                <button className="flex items-center gap-2 px-4 py-2 bg-secondary border border-border rounded-xl text-xs font-semibold hover:bg-muted transition-all">
                    <Filter className="w-3.5 h-3.5" /> Filter
                </button>
            </div>

            <div className="glass rounded-2xl overflow-hidden">
                <table className="w-full text-left text-sm">
                    <thead className="bg-muted/50 border-b border-border">
                        <tr>
                            <th className="px-6 py-4 font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">Report Title</th>
                            <th className="px-6 py-4 font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">Type</th>
                            <th className="px-6 py-4 font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">Date</th>
                            <th className="px-6 py-4 font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">Trust Score</th>
                            <th className="px-6 py-4 font-semibold text-muted-foreground uppercase text-[10px] tracking-wider text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {reports.map((report) => (
                            <tr key={report.id} className="hover:bg-muted/30 transition-colors group cursor-pointer">
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all">
                                            <FileText className="w-4 h-4" />
                                        </div>
                                        <span className="font-medium">{report.title}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="px-2 py-0.5 rounded-full bg-secondary border border-border text-[10px] font-bold uppercase">{report.type}</span>
                                </td>
                                <td className="px-6 py-4 text-muted-foreground text-xs">
                                    <div className="flex items-center gap-1.5">
                                        <Calendar className="w-3 h-3 text-muted-foreground" />
                                        {report.date}
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-2">
                                        <Shield className={`w-3.5 h-3.5 ${report.trust > 0.8 ? 'text-green-500' : 'text-yellow-500'}`} />
                                        <span className="font-mono text-xs">{Math.round(report.trust * 100)}%</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <button className="p-2 rounded-lg bg-secondary border border-border hover:border-primary/50 text-muted-foreground hover:text-primary transition-all">
                                        <Download className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
