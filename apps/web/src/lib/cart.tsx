"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { api, type Product } from "@/lib/api";
import { CartPriceSheet } from "@/components/CartPriceSheet";
import {
  acceptCartPending,
  livePriceNote,
  mergeLiveCart,
  type CartLine,
  type CartPendingChange,
} from "@/lib/cartPrices";

export type { CartLine };

type CartContextValue = {
  lines: CartLine[];
  count: number;
  total: number;
  ready: boolean;
  pricesSyncing: boolean;
  priceNote: string | null;
  pricePending: CartPendingChange[];
  add: (line: Omit<CartLine, "quantity">, qty?: number) => void;
  setQty: (productId: string, quantity: number) => void;
  remove: (productId: string) => void;
  clear: () => void;
  acceptPriceChanges: () => void;
  removePending: (productId: string) => void;
};

const STORAGE_KEY = "whiteshop.cart.v1";
const LIVE_CHUNK = 50;
const CartContext = createContext<CartContextValue | null>(null);

function loadCart(): CartLine[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as CartLine[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((l) => l.productId && l.slug && l.quantity > 0);
  } catch {
    return [];
  }
}

function saveCart(lines: CartLine[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
}

async function fetchLiveProducts(ids: string[]): Promise<Product[]> {
  const out: Product[] = [];
  for (let i = 0; i < ids.length; i += LIVE_CHUNK) {
    const chunk = ids.slice(i, i + LIVE_CHUNK);
    const live = await api.productsLive({ ids: chunk });
    out.push(...live);
  }
  return out;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>([]);
  const [ready, setReady] = useState(false);
  const [pricesSyncing, setPricesSyncing] = useState(false);
  const [priceNote, setPriceNote] = useState<string | null>(null);
  const [pricePending, setPricePending] = useState<CartPendingChange[]>([]);
  const linesRef = useRef<CartLine[]>([]);
  linesRef.current = lines;

  useEffect(() => {
    setLines(loadCart());
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    saveCart(lines);
  }, [lines, ready]);

  const idsKey = useMemo(
    () =>
      [...lines.map((line) => line.productId)]
        .sort()
        .join(","),
    [lines],
  );

  useEffect(() => {
    if (!ready) return;
    if (!idsKey) {
      setPriceNote(null);
      setPricePending([]);
      setPricesSyncing(false);
      return;
    }
    const ids = idsKey.split(",");
    let cancelled = false;
    setPricesSyncing(true);
    void (async () => {
      try {
        const live = await fetchLiveProducts(ids);
        if (cancelled) return;
        const result = mergeLiveCart(linesRef.current, live, ids);
        linesRef.current = result.next;
        setLines(result.next);
        setPricePending(result.pending);
        setPriceNote(livePriceNote(result.droppedPrices));
      } catch {
        if (!cancelled) {
          setPriceNote("Не удалось сверить цены с витриной. Проверьте сеть перед заказом.");
        }
      } finally {
        if (!cancelled) setPricesSyncing(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, idsKey]);

  const add = useCallback((line: Omit<CartLine, "quantity">, qty = 1) => {
    setLines((prev) => {
      const existing = prev.find((l) => l.productId === line.productId);
      if (existing) {
        return prev.map((l) =>
          l.productId === line.productId
            ? { ...l, quantity: Math.min(100, l.quantity + qty), price: line.price, title: line.title }
            : l,
        );
      }
      return [...prev, { ...line, quantity: qty }];
    });
  }, []);

  const setQty = useCallback((productId: string, quantity: number) => {
    if (quantity <= 0) {
      setLines((prev) => prev.filter((l) => l.productId !== productId));
      setPricePending((prev) => prev.filter((item) => item.productId !== productId));
      return;
    }
    setLines((prev) =>
      prev.map((l) => (l.productId === productId ? { ...l, quantity: Math.min(100, quantity) } : l)),
    );
  }, []);

  const remove = useCallback((productId: string) => {
    setLines((prev) => prev.filter((l) => l.productId !== productId));
    setPricePending((prev) => prev.filter((item) => item.productId !== productId));
  }, []);

  const clear = useCallback(() => {
    setLines([]);
    setPricePending([]);
    setPriceNote(null);
  }, []);

  const acceptPriceChanges = useCallback(() => {
    setLines((prev) => {
      const next = acceptCartPending(prev, pricePending);
      linesRef.current = next;
      return next;
    });
    setPricePending([]);
  }, [pricePending]);

  const removePending = useCallback((productId: string) => {
    setLines((prev) => {
      const next = prev.filter((line) => line.productId !== productId);
      linesRef.current = next;
      return next;
    });
    setPricePending((prev) => prev.filter((item) => item.productId !== productId));
  }, []);

  const count = useMemo(() => lines.reduce((s, l) => s + l.quantity, 0), [lines]);
  const total = useMemo(
    () => lines.reduce((s, l) => s + Number(l.price) * l.quantity, 0),
    [lines],
  );

  const value = useMemo(
    () => ({
      lines,
      count,
      total,
      ready,
      pricesSyncing,
      priceNote,
      pricePending,
      add,
      setQty,
      remove,
      clear,
      acceptPriceChanges,
      removePending,
    }),
    [
      lines,
      count,
      total,
      ready,
      pricesSyncing,
      priceNote,
      pricePending,
      add,
      setQty,
      remove,
      clear,
      acceptPriceChanges,
      removePending,
    ],
  );

  return (
    <CartContext.Provider value={value}>
      {children}
      <CartPriceSheet
        pending={pricePending}
        onAccept={acceptPriceChanges}
        onRemove={removePending}
      />
    </CartContext.Provider>
  );
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
