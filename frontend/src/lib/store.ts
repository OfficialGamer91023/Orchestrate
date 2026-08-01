import { create } from "zustand";
import type { BatchEvalResponse } from "./api";

interface EvalState {
  isRunning: boolean;
  setIsRunning: (running: boolean) => void;
  result: BatchEvalResponse | null;
  setResult: (result: BatchEvalResponse | null) => void;
}

export const useEvalStore = create<EvalState>((set) => ({
  isRunning: false,
  setIsRunning: (running) => set({ isRunning: running }),
  result: null,
  setResult: (result) => set({ result }),
}));
