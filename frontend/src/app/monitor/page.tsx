"use client"

import { useAgentStore } from "@/store/useAgentStore"
import { AgentCard } from "@/components/agents/agent-card"
import { Monitor, Server, Cpu, HardDrive, RefreshCcw } from "lucide-react"

export default function MonitorPage() {
    const { agents } = useAgentStore()

    return (
        <div className="p-6 max-w-7xl mx-auto w-full space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Agent Monitor</h1>
                    <p className="text-muted-foreground text-sm">Observe agent behaviors, resource allocation, and task traces.</p>
                </div>
                <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-secondary border border-border hover:bg-muted transition-all text-sm font-medium shadow-sm">
                    <RefreshCcw className="w-4 h-4" />
                    Refresh Agents
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Resource Sidebar */}
                <div className="lg:col-span-1 space-y-4">
                    <div className="glass p-5 rounded-2xl space-y-6">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Resource Usage</h3>

                        <div className="space-y-4">
                            <div className="space-y-2">
                                <div className="flex justify-between text-xs font-semibold">
                                    <div className="flex items-center gap-2">
                                        <Cpu className="w-3.5 h-3.5 text-primary" /> CPU
                                    </div>
                                    <span>42%</span>
                                </div>
                                <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                                    <div className="bg-primary h-full w-[42%]" />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="flex justify-between text-xs font-semibold">
                                    <div className="flex items-center gap-2">
                                        <Server className="w-3.5 h-3.5 text-blue-400" /> RAM
                                    </div>
                                    <span>8.4GB / 16GB</span>
                                </div>
                                <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                                    <div className="bg-blue-400 h-full w-[52.5%]" />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="flex justify-between text-xs font-semibold">
                                    <div className="flex items-center gap-2">
                                        <HardDrive className="w-3.5 h-3.5 text-purple-400" /> Storage
                                    </div>
                                    <span>244GB Free</span>
                                </div>
                                <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                                    <div className="bg-purple-400 h-full w-[75%]" />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="glass p-5 rounded-2xl space-y-4">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Network Throughput</h3>
                        <div className="h-24 flex items-end gap-1">
                            {[20, 40, 35, 50, 45, 60, 55, 75, 70, 85, 80, 95, 90, 100, 85, 70].map((h, i) => (
                                <div key={i} className="flex-1 bg-primary/40 rounded-t-sm" style={{ height: `${h}%` }} />
                            ))}
                        </div>
                        <div className="flex justify-between text-[10px] text-muted-foreground font-bold tracking-tighter">
                            <span>RX: 12.4 MB/s</span>
                            <span>TX: 2.1 MB/s</span>
                        </div>
                    </div>
                </div>

                {/* Agent Grid */}
                <div className="lg:col-span-3 space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {agents.map(agent => (
                            <AgentCard key={agent.id} agent={agent} />
                        ))}
                    </div>

                    <div className="glass rounded-2xl overflow-hidden">
                        <div className="border-b border-border p-4 flex items-center justify-between bg-card/50">
                            <h3 className="text-sm font-semibold flex items-center gap-2">
                                <Monitor className="w-4 h-4 text-primary" />
                                Live Execution Stream
                            </h3>
                            <div className="flex gap-2">
                                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                                <span className="text-[10px] font-mono text-muted-foreground uppercase">Recording Trace</span>
                            </div>
                        </div>
                        <div className="p-4 bg-black/60 font-mono text-[11px] h-[300px] overflow-y-auto space-y-1">
                            <p className="text-green-500">[02:34:11] INFO: Agent Alpha entering 'deep_search' mode...</p>
                            <p className="text-blue-400">[02:34:12] DEBUG: Querying Google Scholarly API for 'asymmetric cryptography'</p>
                            <p className="text-muted-foreground">[02:34:15] WARN: Rate limit hit on EndPoint-B. Rotating proxies...</p>
                            <p className="text-green-500">[02:34:16] SUCCESS: Retrieved 12 high-confidence documents from EDU sources.</p>
                            <p className="text-purple-400">[02:34:18] INFO: Passing results to Analyst Beta for claim extraction.</p>
                            <p className="text-muted-foreground">[02:34:20] LOG: Extraction process 12.5% complete.</p>
                            <p className="text-muted-foreground">[02:34:21] LOG: Extraction process 28.0% complete.</p>
                            <p className="text-muted-foreground">[02:34:24] LOG: Extraction process 45.2% complete.</p>
                            <p className="text-muted-foreground">[02:34:27] LOG: Extraction process 72.1% complete.</p>
                            <p className="text-green-500">[02:34:30] SUCCESS: Analyst Beta generated 8 verifiable claims.</p>
                            <p className="text-blue-400">[02:34:31] DEBUG: Validator Gamma initiating cross-source verification...</p>
                            <p className="text-yellow-400">[02:34:33] WARN: Semantic contradiction detected in Claim #3. Rerunning analysis.</p>
                            <p className="text-muted-foreground">[02:34:35] LOG: Applying Bayesian filters to contradiction resolution.</p>
                            <div className="flex items-center gap-1 mt-2">
                                <span className="animate-pulse w-1 h-3 bg-primary" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
