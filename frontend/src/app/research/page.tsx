"use client"

import { useState } from "react"
import { useResearchStore } from "@/store/useResearchStore"
import { useAgentStore } from "@/store/useAgentStore"
import { ReliabilityVisualization } from "@/components/reliability/reliability-viz"
import { AgentCard } from "@/components/agents/agent-card"
import { Send, Zap, Search, Layers, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export default function ResearchPage() {
    const [input, setInput] = useState("")
    const { isResearching, messages, currentTrace, setResearching, addMessage, addTrace } = useResearchStore()
    const { agents } = useAgentStore()

    const handleStartResearch = async () => {
        if (!input.trim()) return

        setResearching(true)
        addMessage({
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date().toLocaleTimeString()
        })

        // Simulate real-time trace
        addTrace("Initializing multi-agent planning...")
        await new Promise(r => setTimeout(r, 1000))
        addTrace("Agent Alpha: Searching high-credibility domains...")
        await new Promise(r => setTimeout(r, 1500))
        addTrace("Agent Beta: Extracting claims from .gov sources...")

        setTimeout(() => {
            addMessage({
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "Based on current research, the data indicates a 15% increase in cross-sectional efficiency when utilizing distributed agents.",
                timestamp: new Date().toLocaleTimeString()
            })
            setResearching(false)
        }, 3000)

        setInput("")
    }

    return (
        <div className="h-full flex flex-col p-6 gap-6 max-w-7xl mx-auto w-full">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Research Workspace</h1>
                    <p className="text-muted-foreground text-sm">Orchestrate agents and verify reliability in real-time.</p>
                </div>
                <div className="flex gap-2">
                    <div className="px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 flex items-center gap-2">
                        <Layers className="w-4 h-4 text-primary" />
                        <span className="text-xs font-semibold text-primary">Active Session</span>
                    </div>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">
                {/* Left Column: Chat & Input */}
                <div className="col-span-8 flex flex-col gap-4 overflow-hidden">
                    <div className="flex-1 glass rounded-2xl p-4 overflow-y-auto space-y-4">
                        {messages.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-center opacity-50 grayscale">
                                <Search className="w-12 h-12 mb-4" />
                                <p>Start a new research project to see results</p>
                            </div>
                        ) : (
                            messages.map((msg) => (
                                <div key={msg.id} className={cn(
                                    "flex flex-col gap-1 max-w-[80%]",
                                    msg.role === 'user' ? "ml-auto items-end" : "items-start"
                                )}>
                                    <div className={cn(
                                        "px-4 py-2 rounded-2xl text-sm",
                                        msg.role === 'user' ? "bg-primary text-white" : "bg-secondary"
                                    )}>
                                        {msg.content}
                                    </div>
                                    <span className="text-[10px] text-muted-foreground px-1">{msg.timestamp}</span>
                                </div>
                            ))
                        )}
                        {isResearching && (
                            <div className="flex items-center gap-2 text-primary animate-pulse">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span className="text-xs font-medium">Researching...</span>
                            </div>
                        )}
                    </div>

                    <div className="relative">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Enter your research query here..."
                            className="w-full bg-secondary/50 border border-border rounded-2xl p-4 pr-16 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm h-24 transition-all"
                        />
                        <button
                            onClick={handleStartResearch}
                            disabled={isResearching}
                            className="absolute right-4 bottom-4 w-10 h-10 rounded-xl active-gradient flex items-center justify-center text-white transition-transform hover:scale-105 active:scale-95 disabled:opacity-50"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Right Column: Insights & Agents */}
                <div className="col-span-4 flex flex-col gap-4 overflow-y-auto pr-2">
                    <ReliabilityVisualization
                        trustScore={0.15}
                        confidenceScore={0.15}
                    />

                    <div className="glass p-4 rounded-xl">
                        <h3 className="text-sm font-semibold flex items-center gap-2 mb-4">
                            <Zap className="w-4 h-4 text-primary" />
                            Live Process Trace
                        </h3>
                        <div className="space-y-2">
                            {currentTrace.map((t, i) => (
                                <div key={i} className="flex gap-2 items-start animate-in fade-in slide-in-from-left-2 duration-500">
                                    <div className="w-1 h-1 rounded-full bg-primary mt-1.5 shrink-0" />
                                    <p className="text-[10px] font-mono text-muted-foreground leading-relaxed">{t}</p>
                                </div>
                            ))}
                            {isResearching && (
                                <div className="flex items-center gap-1.5 ml-0.5">
                                    <div className="w-1 h-1 rounded-full bg-primary animate-bounce" />
                                    <div className="w-1 h-1 rounded-full bg-primary animate-bounce delay-75" />
                                    <div className="w-1 h-1 rounded-full bg-primary animate-bounce delay-150" />
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold px-1">Active Agents</h3>
                        {agents.map(agent => (
                            <AgentCard key={agent.id} agent={agent} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
