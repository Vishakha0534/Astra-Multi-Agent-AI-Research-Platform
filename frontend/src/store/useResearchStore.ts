import { create } from 'zustand'

interface ResearchMessage {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    timestamp: string
}

interface ResearchState {
    isResearching: boolean
    messages: ResearchMessage[]
    currentTrace: string[]
    setResearching: (val: boolean) => void
    addMessage: (msg: ResearchMessage) => void
    addTrace: (msg: string) => void
    clearTrace: () => void
}

export const useResearchStore = create<ResearchState>((set) => ({
    isResearching: false,
    messages: [],
    currentTrace: [],
    setResearching: (val) => set({ isResearching: val }),
    addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
    addTrace: (msg) => set((state) => ({ currentTrace: [...state.currentTrace, msg] })),
    clearTrace: () => set({ currentTrace: [] }),
}))
