import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { AuthLoginRequest } from "@job-tracker/shared/api";

export const authUserKey = ["auth", "current-user"] as const;

export function useCurrentUser() {
  return useQuery({
    queryKey: authUserKey,
    queryFn: api.getCurrentUser,
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (credentials: AuthLoginRequest) => api.login(credentials),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: authUserKey }),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSuccess: () => queryClient.removeQueries({ queryKey: authUserKey }),
  });
}
