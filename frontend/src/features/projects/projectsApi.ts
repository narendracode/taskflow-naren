import { baseApi } from "@/features/api/baseApi";
import type { PaginatedResponse, Project, ProjectStats } from "@/types";

export const projectsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getProjects: builder.query<
      PaginatedResponse<Project>,
      { page?: number; limit?: number } | void
    >({
      query: ({ page = 1, limit = 50 } = {}) =>
        `/projects?page=${page}&limit=${limit}`,
      providesTags: ["Project"],
    }),

    createProject: builder.mutation<
      Project,
      { name: string; description?: string }
    >({
      query: (body) => ({ url: "/projects", method: "POST", body }),
      invalidatesTags: ["Project"],
    }),

    getProject: builder.query<Project, string>({
      query: (id) => `/projects/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Project", id }],
    }),

    updateProject: builder.mutation<
      Project,
      { id: string; name?: string; description?: string }
    >({
      query: ({ id, ...body }) => ({
        url: `/projects/${id}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: (_r, _e, { id }) => ["Project", { type: "Project", id }],
    }),

    deleteProject: builder.mutation<void, string>({
      query: (id) => ({ url: `/projects/${id}`, method: "DELETE" }),
      invalidatesTags: ["Project"],
    }),

    getProjectStats: builder.query<ProjectStats, string>({
      query: (id) => `/projects/${id}/stats`,
      providesTags: (_r, _e, id) => [{ type: "ProjectStats", id }],
    }),
  }),
});

export const {
  useGetProjectsQuery,
  useCreateProjectMutation,
  useGetProjectQuery,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
  useGetProjectStatsQuery,
} = projectsApi;
