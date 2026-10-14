import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      return data;
    } catch {
      setUser(false);
      return false;
    }
  }, []);
  useEffect(() => {
    refresh();
    const onExp = () => setUser(false);
    window.addEventListener("auth:expired", onExp);
    return () => window.removeEventListener("auth:expired", onExp);
  }, [refresh]);
  const logout = async (all = false) => {
    try { await api.post(all ? "/auth/logout-all" : "/auth/logout"); } catch { /* session may already be gone */ }
    setUser(false);
  };
  return <AuthCtx.Provider value={{ user, setUser, refresh, logout }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
