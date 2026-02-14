"use client";

import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";

export default function Home() {
  const tasks = useQuery(api.tasks.get);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8 font-sans">
      <main className="w-full max-w-2xl space-y-6">
        <h1 className="text-2xl font-semibold">Tasks</h1>
        {tasks === undefined ? (
          <p className="text-zinc-500">Loading tasks...</p>
        ) : tasks.length === 0 ? (
          <p className="text-zinc-500">
            No tasks yet. Run{" "}
            <code className="rounded bg-zinc-100 px-1 py-0.5 dark:bg-zinc-800">
              npx convex import --table tasks sampleData.jsonl
            </code>{" "}
            to add sample data.
          </p>
        ) : (
          <ul className="space-y-2">
            {tasks.map((task) => (
              <li
                key={task._id}
                className={`flex items-center gap-2 ${
                  task.isCompleted ? "text-zinc-500 line-through" : ""
                }`}
              >
                <span>{task.text}</span>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
