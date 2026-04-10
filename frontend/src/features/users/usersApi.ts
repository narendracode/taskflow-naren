import { baseApi } from "@/features/api/baseApi";
import type { Theme, User } from "@/types";

export const usersApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getMe: builder.query<User, void>({
      query: () => "/users/me",
    }),

    searchUsers: builder.query<User[], string>({
      query: (q) => `/users/search?q=${encodeURIComponent(q)}&limit=10`,
    }),

    updatePreferences: builder.mutation<User, { theme: Theme }>({
      query: (body) => ({
        url: "/users/me/preferences",
        method: "PATCH",
        body,
      }),
    }),
  }),
});

export const {
  useGetMeQuery,
  useSearchUsersQuery,
  useUpdatePreferencesMutation,
} = usersApi;
