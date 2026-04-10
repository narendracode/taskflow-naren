import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

function loadFromStorage(): AuthState {
  try {
    const token = localStorage.getItem("taskflow_token");
    const raw = localStorage.getItem("taskflow_user");
    if (token && raw) {
      return { token, user: JSON.parse(raw) as User, isAuthenticated: true };
    }
  } catch {
    // corrupted storage — start fresh
  }
  return { token: null, user: null, isAuthenticated: false };
}

const authSlice = createSlice({
  name: "auth",
  initialState: loadFromStorage(),
  reducers: {
    setCredentials(
      state,
      { payload }: PayloadAction<{ user: User; token: string }>
    ) {
      state.user = payload.user;
      state.token = payload.token;
      state.isAuthenticated = true;
      localStorage.setItem("taskflow_token", payload.token);
      localStorage.setItem("taskflow_user", JSON.stringify(payload.user));
    },
    logout(state) {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      localStorage.removeItem("taskflow_token");
      localStorage.removeItem("taskflow_user");
    },
  },
});

export const { setCredentials, logout } = authSlice.actions;
export default authSlice.reducer;
