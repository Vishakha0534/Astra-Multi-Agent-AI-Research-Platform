"use client"

import { cn } from "@/lib/utils"
import { ShieldCheck, Info } from "lucide-react"

interface ReliabilityVisualizationProps {
    trustScore: float
    confidenceScore: float
    className?: string
}

export function ReliabilityVisualization({
    trustScore,
    confidenceScore,
    className
}: ReliabilityVisualizationProps) {
    const getScoreColor = (score: number) => {
        if (score > 0.8) return "text-green-500"
        if (score > 0.5) return "text-yellow-500"
        return "text-red-500"
    }

    return (
        <div className={cn("glass p-4 rounded-xl space-y-4", className)}>
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-primary" />
                    Reliability Analysis
                </h3>
                <Info className="w-3 h-3 text-muted-foreground" />
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                    <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider">Trust Score</p>
                    <div className="flex items-end gap-1">
                        <span className={cn("text-2xl font-bold leading-none", getScoreColor(trustScore))}>
                            {Math.round(trustScore * 100)}%
                        </span>
                    </div>
                    <div className="w-full bg-muted h-1 rounded-full overflow-hidden">
                        <div
                            className="bg-primary h-full transition-all duration-1000"
                            style={{ width: `${trustScore * 100}%` }}
                        />
                    </div>
                </div>

                <div className="space-y-1">
                    <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider">Confidence</p>
                    <div className="flex items-end gap-1">
                        <span className={cn("text-2xl font-bold leading-none", getScoreColor(confidenceScore))}>
                            {Math.round(confidenceScore * 100)}%
                        </span>
                    </div>
                    <div className="w-full bg-muted h-1 rounded-full overflow-hidden">
                        <div
                            className="bg-primary/60 h-full transition-all duration-1000"
                            style={{ width: `${confidenceScore * 100}%` }}
                        />
                    </div>
                </div>
            </div>
        </div>
    )
}
