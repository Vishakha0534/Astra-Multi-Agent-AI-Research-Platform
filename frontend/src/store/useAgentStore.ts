import { create } from 'zustand'

export interface Agent {
    id: string
    name: string
    status: 'idle' | 'working' | 'error'
    lastAction: string
}

interface AgentState {
    agents: Agent[]
    updateAgent: (id: string, updates: Partial<Agent>) => void
}

export const useAgentStore = create<AgentState>((set) => ({
    agents: [
        { id: '1', name: 'Researcher Alpha', status: 'idle', lastAction: 'Initialized' },
        { id: '2', name: 'Analyst Beta', status: 'idle', lastAction: 'Waiting' },
        { id: '3', name: 'Validator Gamma', status: 'idle', lastAction: 'Offline' },
    ],
    updateAgent: (id, updates) => set((state) => ({
        agents: state.agents.map(a => a.id === id ? { ...a, ...updates } : a)
    })),
}))
