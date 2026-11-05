import { QueryProvider } from "@/app/providers/query-provider";
import { ThemeProvider } from "@/app/providers/theme-provider";
import { AppRouter } from "@/app/router/app-router";

export function App() {
  return (
    <QueryProvider>
      <ThemeProvider>
        <AppRouter />
      </ThemeProvider>
    </QueryProvider>
  );
}
