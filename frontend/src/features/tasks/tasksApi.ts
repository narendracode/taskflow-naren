import { baseApi } from "@/features/api/baseApi";
import type { PaginatedResponse, Task, TaskPriority, TaskStatus } from "@/types";

export interface GetTasksParams {
  projectId: string;
  status?: TaskStatus;
  assignee?: string;
  page?: number;
  limit?: number;
}

interface CreateTaskParams {
  projectId: string;
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: string | null;
  due_date?: string | null;
}

interface UpdateTaskParams {
  taskId: string;
  projectId: string; // needed for cache invalidation + optimistic update targeting
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: string | null;
  due_date?: string | null;
}

export const tasksApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getProjectTasks: builder.query<PaginatedResponse<Task>, GetTasksParams>({
      query: ({ projectId, status, assignee, page = 1, limit = 100 }) => {
        const p = new URLSearchParams({
          page: String(page),
          limit: String(limit),
        });
        if (status) p.set("status", status);
        if (assignee) p.set("assignee", assignee);
        return `/projects/${projectId}/tasks?${p.toString()}`;
      },
      providesTags: (result, _e, { projectId }) =>
        result
          ? [
              ...result.data.map((t) => ({
                type: "Task" as const,
                id: t.id,
              })),
              { type: "Task" as const, id: `LIST-${projectId}` },
            ]
          : [{ type: "Task" as const, id: `LIST-${projectId}` }],
    }),

    createTask: builder.mutation<Task, CreateTaskParams>({
      query: ({ projectId, ...body }) => ({
        url: `/projects/${projectId}/tasks`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_r, _e, { projectId }) => [
        { type: "Task", id: `LIST-${projectId}` },
        { type: "ProjectStats", id: projectId },
      ],
    }),

    updateTask: builder.mutation<Task, UpdateTaskParams>({
      query: ({ taskId, projectId: _pid, ...body }) => ({
        url: `/tasks/${taskId}`,
        method: "PATCH",
        body,
      }),

      // ── Optimistic update ────────────────────────────────────────────────
      async onQueryStarted(
        { taskId, projectId, ...update },
        { dispatch, queryFulfilled, getState }
      ) {
        // Find every cached getProjectTasks entry that belongs to this project
        // and update the task in all of them — handles any active filter combo.
        type ApiState = { queries: Record<string, { endpointName?: string; originalArgs?: GetTasksParams }> };
        const apiState = (getState() as { api: ApiState }).api;

        const patches = Object.values(apiState.queries)
          .filter(
            (q) =>
              q?.endpointName === "getProjectTasks" &&
              q?.originalArgs?.projectId === projectId
          )
          .map((q) =>
            dispatch(
              tasksApi.util.updateQueryData(
                "getProjectTasks",
                q.originalArgs as GetTasksParams,
                (draft) => {
                  const task = draft.data.find((t) => t.id === taskId);
                  if (task) Object.assign(task, update);
                }
              )
            )
          );

        try {
          await queryFulfilled;
        } catch {
          patches.forEach((p) => p.undo());
        }
      },

      invalidatesTags: (_r, _e, { taskId, projectId }) => [
        { type: "Task", id: taskId },
        { type: "ProjectStats", id: projectId },
      ],
    }),

    deleteTask: builder.mutation<void, { taskId: string; projectId: string }>({
      query: ({ taskId }) => ({ url: `/tasks/${taskId}`, method: "DELETE" }),
      invalidatesTags: (_r, _e, { projectId, taskId }) => [
        { type: "Task", id: taskId },
        { type: "Task", id: `LIST-${projectId}` },
        { type: "ProjectStats", id: projectId },
      ],
    }),
  }),
});

export const {
  useGetProjectTasksQuery,
  useCreateTaskMutation,
  useUpdateTaskMutation,
  useDeleteTaskMutation,
} = tasksApi;
