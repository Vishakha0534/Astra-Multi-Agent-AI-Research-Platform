"use client"

import { cn } from "@/lib/utils"
import { Agent } from "@/store/useAgentStore"
import { Cpu, Terminal } from "lucide-react"

export function AgentCard({ agent }: { agent: Agent }) {
    return (
        <div className="glass p-4 rounded-xl space-y-3 transition-all hover:border-primary/30">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-secondary flex items-center justify-center">
                        <Cpu className="w-4 h-4 text-primary" />
                    </div>
                    <div>
                        <h4 className="text-sm font-semibold">{agent.name}</h4>
                        <div className="flex items-center gap-1.5">
                            <span className={cn(
                                "w-1.5 h-1.5 rounded-full",
                                agent.status === 'working' ? "bg-primary animate-pulse" :
                                    agent.status === 'idle' ? "bg-green-500" : "bg-red-500"
                            )} />
                            <span className="text-[10px] uppercase font-bold text-muted-foreground">
                                {agent.status}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="bg-background/40 rounded p-2 flex items-start gap-2">
                <Terminal className="w-3 h-3 text-muted-foreground mt-0.5" />
                <p className="text-[10px] font-mono text-muted-foreground line-clamp-2">
                    {agent.lastAction}
                </p>
            </div>
        </div>
    )
}
