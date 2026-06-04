"use client"

import { Settings, Shield, Cpu, Database, Save, User, Globe, Lock } from "lucide-react"

export default function SettingsPage() {
    const sections = [
        { title: "Research Preferences", icon: Shield, desc: "Configure default reliability thresholds and citation standards." },
        { title: "Agent Configuration", icon: Cpu, desc: "Manage agent personas, model selection, and resource scaling." },
        { title: "Storage & Knowledge", icon: Database, desc: "Connect external knowledge bases and manage stored reports." },
        { title: "Security & API", icon: Lock, desc: "Manage API keys, webhooks, and multi-factor authentication." },
    ]

    return (
        <div className="p-6 max-w-4xl mx-auto w-full space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">System Settings</h1>
                <p className="text-muted-foreground text-sm">Customize platform behavior, agent protocols, and security.</p>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {sections.map((sec) => (
                    <div key={sec.title} className="glass p-6 rounded-2xl flex items-start gap-4 hover:border-primary/30 transition-all cursor-pointer group">
                        <div className="w-12 h-12 rounded-xl bg-secondary border border-border flex items-center justify-center shrink-0 group-hover:bg-primary/10 transition-colors">
                            <sec.icon className="w-6 h-6 text-muted-foreground group-hover:text-primary" />
                        </div>
                        <div className="flex-1 space-y-1">
                            <h3 className="font-semibold">{sec.title}</h3>
                            <p className="text-sm text-muted-foreground leading-relaxed">{sec.desc}</p>
                        </div>
                        <button className="text-muted-foreground hover:text-foreground transition-all mt-1">
                            <Settings className="w-5 h-5" />
                        </button>
                    </div>
                ))}
            </div>

            <div className="glass p-8 rounded-2xl space-y-6">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                    <User className="w-5 h-5 text-primary" />
                    Primary Profile
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-widest pl-1">Organization Name</label>
                        <input
                            type="text"
                            defaultValue="ASTRA Research Lab"
                            className="w-full bg-secondary/50 border border-border rounded-xl p-3 outline-none focus:ring-2 focus:ring-primary/50"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-xs font-bold uppercase text-muted-foreground tracking-widest pl-1">Default Locale</label>
                        <div className="relative">
                            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <select className="w-full bg-secondary/50 border border-border rounded-xl p-3 pl-10 outline-none appearance-none focus:ring-2 focus:ring-primary/50">
                                <option>Global (English)</option>
                                <option>EU (Multi-lingual)</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div className="pt-4 flex justify-end">
                    <button className="flex items-center gap-2 px-6 py-2.5 rounded-xl active-gradient text-white font-semibold transition-transform hover:scale-105 active:scale-95 shadow-lg shadow-primary/20">
                        <Save className="w-4 h-4" /> Save Changes
                    </button>
                </div>
            </div>
        </div>
    )
}
