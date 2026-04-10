import { useEffect, useRef } from "react";
import type { Task } from "@/types";
import { useAppSelector, useAppDispatch } from "@/app/store";
import { store } from "@/app/store";
import { baseApi } from "@/features/api/baseApi";
import { tasksApi, type GetTasksParams } from "@/features/tasks/tasksApi";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * Opens an SSE connection to `/projects/{projectId}/events` and patches the
 * RTK Query cache for `getProjectTasks` whenever a task event arrives.
 *
 * This keeps every open browser tab / device in sync without polling.
 */
export function useProjectSSE(projectId: string | undefined) {
  const token = useAppSelector((s) => s.auth.token);
  const dispatch = useAppDispatch();
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!projectId || !token) return;

    // EventSource doesn't support custom headers, so pass the token as a
    // query parameter.  The backend also accepts `?token=` for SSE auth.
    const url = `${API_URL}/projects/${encodeURIComponent(projectId)}/events?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    /**
     * Helper: update every cached `getProjectTasks` query whose
     * `projectId` matches.  We don't know which filter combos are cached,
     * so we use `updateQueryData` across all matching entries.
     */
    function patchAllCaches(
      updater: (draft: { data: Task[] }) => void,
    ) {
      const state = store.getState();
      const apiState = state.api?.queries as
        | Record<string, { endpointName?: string; originalArgs?: GetTasksParams }>
        | undefined;
      if (!apiState) return;

      for (const entry of Object.values(apiState)) {
        if (
          entry?.endpointName === "getProjectTasks" &&
          entry?.originalArgs?.projectId === projectId
        ) {
          dispatch(
            tasksApi.util.updateQueryData(
              "getProjectTasks",
              entry.originalArgs as GetTasksParams,
              updater,
            ),
          );
        }
      }
    }

    es.addEventListener("task_created", (e: MessageEvent) => {
      const task: Task = JSON.parse(e.data);
      patchAllCaches((draft) => {
        // Avoid duplicates (the originating tab already has this via optimistic update / invalidation)
        if (!draft.data.some((t) => t.id === task.id)) {
          draft.data.unshift(task);
        }
      });
      dispatch(baseApi.util.invalidateTags([{ type: "ProjectStats", id: projectId }]));
    });

    es.addEventListener("task_updated", (e: MessageEvent) => {
      const task: Task = JSON.parse(e.data);
      patchAllCaches((draft) => {
        const idx = draft.data.findIndex((t) => t.id === task.id);
        if (idx !== -1) {
          draft.data[idx] = task;
        } else {
          // Task might have been filtered out — add it
          draft.data.unshift(task);
        }
      });
      dispatch(baseApi.util.invalidateTags([{ type: "ProjectStats", id: projectId }]));
    });

    es.addEventListener("task_deleted", (e: MessageEvent) => {
      const { id } = JSON.parse(e.data);
      patchAllCaches((draft) => {
        draft.data = draft.data.filter((t) => t.id !== id);
      });
      dispatch(baseApi.util.invalidateTags([{ type: "ProjectStats", id: projectId }]));
    });

    es.onerror = () => {
      // EventSource reconnects automatically; nothing special needed.
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [projectId, token, dispatch]);
}
