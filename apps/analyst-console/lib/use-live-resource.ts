"use client";

import { useEffect, useRef, useState } from "react";

import { fetchBrowserJson } from "@/lib/browser-api";

export function useLiveResource<T>({
  path,
  initialData,
  storageKey,
  intervalMs = 3000,
  liveByDefault = true,
  onData,
}: {
  path: string;
  initialData: T;
  storageKey: string;
  intervalMs?: number;
  liveByDefault?: boolean;
  onData?: (previous: T, current: T) => void;
}) {
  const [data, setData] = useState(initialData);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [liveMode, setLiveMode] = useState(liveByDefault);
  const [lastSuccessfulFetchAt, setLastSuccessfulFetchAt] = useState(() =>
    new Date().toISOString(),
  );
  const latestData = useRef(initialData);
  const latestOnData = useRef(onData);
  const inFlight = useRef(false);
  const refreshRef = useRef<() => Promise<void>>(async () => {});

  useEffect(() => {
    latestOnData.current = onData;
  }, [onData]);

  refreshRef.current = async () => {
    if (inFlight.current) {
      return;
    }
    inFlight.current = true;
    setIsRefreshing(true);
    try {
      const result = await fetchBrowserJson<T>(path);
      if (result.data) {
        const previous = latestData.current;
        latestData.current = result.data;
        setData(result.data);
        setError(null);
        setLastSuccessfulFetchAt(new Date().toISOString());
        latestOnData.current?.(previous, result.data);
        return;
      }
      setError(result.error ?? "Unable to refresh live data.");
    } finally {
      inFlight.current = false;
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    latestData.current = initialData;
    setData(initialData);
    setError(null);
    setLastSuccessfulFetchAt(new Date().toISOString());
  }, [initialData, path]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const saved = window.localStorage.getItem(storageKey);
    if (saved !== null) {
      setLiveMode(saved === "true");
    }
  }, [storageKey]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(storageKey, String(liveMode));
  }, [liveMode, storageKey]);

  useEffect(() => {
    if (!liveMode) {
      return;
    }
    const interval = window.setInterval(() => {
      void refreshRef.current();
    }, intervalMs);
    return () => window.clearInterval(interval);
  }, [intervalMs, liveMode, path]);

  return {
    data,
    error,
    isRefreshing,
    lastSuccessfulFetchAt,
    liveMode,
    refresh: () => refreshRef.current(),
    setLiveMode,
  };
}
