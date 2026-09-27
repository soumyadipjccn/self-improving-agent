"use client";

import { useState } from "react";
import { 
  Upload, 
  Sliders, 
  PlayCircle, 
  BarChart3, 
  Cpu, 
  Sparkles, 
  RotateCcw, 
  Layers, 
  CheckCircle2, 
  Key, 
  ChevronRight,
  Bot
} from "lucide-react";
import UploadStep from "@/components/UploadStep";
import ConfigStep from "@/components/ConfigStep";
import RunningStep from "@/components/RunningStep";
import ResultsStep from "@/components/ResultsStep";

export default function Home() {
  const [currentStep, setCurrentStep] = useState(1);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(""); // Gemini model id; "" means backend default
  const [metadata, setMetadata] = useState<any>(null);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [evals, setEvals] = useState<any[]>([]);
  const [finalResult, setFinalResult] = useState<any>(null);

  const handleUploadComplete = (
    sid: string,
    key: string,
    chosenModel: string,
    meta: any,
    initialScenarios: any[],
    initialEvals: any[]
  ) => {
    setSessionId(sid);
    setApiKey(key);
    setModel(chosenModel);
    setMetadata(meta);
    setScenarios(initialScenarios);
    setEvals(initialEvals);
    setCurrentStep(2);
  };

  const handleConfigComplete = () => {
    setCurrentStep(3);
  };

  const handleOptimizationComplete = (result: any) => {
    setFinalResult(result);
    setCurrentStep(4);
  };

  const handleStartOver = () => {
    setCurrentStep(1);
    setSessionId(null);
    setApiKey("");
    setModel("");
    setMetadata(null);
    setScenarios([]);
    setEvals([]);
    setFinalResult(null);
  };

  const navItems = [
    { id: 1, name: "Skill Upload", icon: Upload, desc: "Import skill & credentials" },
    { id: 2, name: "Configure Evals", icon: Sliders, desc: "Scenarios & criteria", disabled: !sessionId },
    { id: 3, name: "Optimization", icon: PlayCircle, desc: "Run multi-agent loop", disabled: !sessionId || scenarios.length === 0 },
    { id: 4, name: "Results & Diff", icon: BarChart3, desc: "Analytics & export", disabled: !finalResult },
  ];

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-72 bg-zinc-900/90 border-r border-zinc-800/80 flex flex-col justify-between shrink-0 z-20 backdrop-blur-xl">
        <div>
          {/* Brand Header */}
          <div className="p-6 border-b border-zinc-800/60 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center shadow-lg shadow-violet-500/20">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-base tracking-tight leading-tight">Antigravity AI</h1>
                <p className="text-xs text-zinc-400 font-medium">Self-Improving Agent</p>
              </div>
            </div>
          </div>

          {/* Workflow Navigation */}
          <div className="p-4 space-y-1">
            <p className="px-3 text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Workflow</p>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentStep === item.id;
              const isCompleted = currentStep > item.id;
              return (
                <button
                  key={item.id}
                  disabled={item.disabled}
                  onClick={() => !item.disabled && setCurrentStep(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 text-left ${
                    isActive
                      ? "bg-violet-600/15 border border-violet-500/30 text-white shadow-sm"
                      : isCompleted
                      ? "text-zinc-300 hover:bg-zinc-800/50"
                      : item.disabled
                      ? "opacity-40 cursor-not-allowed text-zinc-500"
                      : "text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200"
                  }`}
                >
                  <div className={`p-2 rounded-lg ${
                    isActive 
                      ? "bg-violet-500 text-white" 
                      : isCompleted 
                      ? "bg-emerald-500/20 text-emerald-400" 
                      : "bg-zinc-800 text-zinc-400"
                  }`}>
                    {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium truncate">{item.name}</span>
                      {isActive && <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />}
                    </div>
                    <p className="text-xs text-zinc-500 truncate">{item.desc}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Sidebar Footer / Session Status */}
        <div className="p-4 border-t border-zinc-800/60 space-y-3">
          {sessionId && (
            <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400 font-medium">
                <span className="flex items-center gap-1.5"><Layers className="w-3.5 h-3.5 text-violet-400" /> Active Session</span>
                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 text-[10px]">Live</span>
              </div>
              <p className="text-xs font-mono text-zinc-300 truncate">{metadata?.name || sessionId.slice(0, 12)}</p>
              {model && (
                <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 font-mono">
                  <Cpu className="w-3 h-3 text-zinc-400" /> {model}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-zinc-500 px-1 pt-1">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Engine Ready
            </span>
            <span className="text-[11px] bg-zinc-800 px-2 py-0.5 rounded text-zinc-400">ADK 2.0</span>
          </div>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top Header */}
        <header className="h-16 border-b border-zinc-800/80 px-8 flex items-center justify-between bg-zinc-900/40 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <span>Dashboard</span>
              <ChevronRight className="w-4 h-4 text-zinc-600" />
              <span className="text-white font-semibold">
                {navItems.find((n) => n.id === currentStep)?.name}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-zinc-900 px-3 py-1.5 rounded-full border border-zinc-800 text-xs text-zinc-400">
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
              <span>Google ADK Multi-Agent System</span>
            </div>

            {sessionId && (
              <button
                onClick={handleStartOver}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-zinc-400 hover:text-white bg-zinc-800/60 hover:bg-zinc-800 rounded-lg transition-colors border border-zinc-700/50"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset Session
              </button>
            )}
          </div>
        </header>

        {/* Dashboard Main Workspace View */}
        <main className="flex-1 overflow-y-auto p-8 bg-zinc-950/40">
          <div className="max-w-7xl mx-auto space-y-6">
            {/* Step 1: Skill Upload & Configuration */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div className="p-6 rounded-2xl bg-gradient-to-r from-violet-900/20 via-purple-900/10 to-zinc-900 border border-violet-500/20">
                  <h2 className="text-2xl font-bold mb-1 text-white">Import Agent Skill & Model Settings</h2>
                  <p className="text-zinc-400 text-sm">
                    Upload your SKILL.md workspace archive, select your target Gemini model, and set your API credentials.
                  </p>
                </div>
                <UploadStep onComplete={handleUploadComplete} />
              </div>
            )}

            {/* Step 2: Configure Scenarios & Evals */}
            {currentStep === 2 && sessionId && (
              <div className="space-y-6">
                <div className="p-6 rounded-2xl bg-gradient-to-r from-violet-900/20 via-purple-900/10 to-zinc-900 border border-violet-500/20 flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold mb-1 text-white">Test Scenarios & Evaluation Criteria</h2>
                    <p className="text-zinc-400 text-sm">
                      Refine test inputs and define automated pass/fail verification prompts for skill evaluation.
                    </p>
                  </div>
                  {metadata && (
                    <span className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-300">
                      {metadata.name || "Skill Workspace"}
                    </span>
                  )}
                </div>
                <ConfigStep
                  sessionId={sessionId}
                  apiKey={apiKey}
                  model={model}
                  scenarios={scenarios}
                  evals={evals}
                  onScenariosChange={setScenarios}
                  onEvalsChange={setEvals}
                  onComplete={handleConfigComplete}
                />
              </div>
            )}

            {/* Step 3: Run Optimization */}
            {currentStep === 3 && sessionId && (
              <div className="space-y-6">
                <div className="p-6 rounded-2xl bg-gradient-to-r from-violet-900/20 via-purple-900/10 to-zinc-900 border border-violet-500/20">
                  <h2 className="text-2xl font-bold mb-1 text-white">Multi-Agent Self-Improvement Loop</h2>
                  <p className="text-zinc-400 text-sm">
                    Autonomous iteration running experiments, evaluating pass rates, and mutating skill logic.
                  </p>
                </div>
                <RunningStep
                  sessionId={sessionId}
                  apiKey={apiKey}
                  model={model}
                  scenarios={scenarios}
                  evals={evals}
                  onComplete={handleOptimizationComplete}
                />
              </div>
            )}

            {/* Step 4: Results & Skill Diff */}
            {currentStep === 4 && finalResult && (
              <div className="space-y-6">
                <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-900/20 via-violet-900/10 to-zinc-900 border border-emerald-500/20">
                  <h2 className="text-2xl font-bold mb-1 text-white">Optimization Report & Skill Export</h2>
                  <p className="text-zinc-400 text-sm">
                    Review improvement metrics, top changelog items, inspect side-by-side diffs, and download the refined skill.
                  </p>
                </div>
                <ResultsStep
                  result={finalResult}
                  sessionId={sessionId!}
                  onStartOver={handleStartOver}
                />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}