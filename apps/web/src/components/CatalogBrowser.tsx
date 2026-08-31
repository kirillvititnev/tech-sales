"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  useTransition,
  type KeyboardEvent,
} from "react";

import { ProductGrid, formatDeviceCategory } from "@/components/ProductGrid";
import {
  api,
  formatPrice,
  type CatalogFacets,
  type CatalogSort,
  type Product,
  type SuggestItem,
} from "@/lib/api";

const SORT_OPTIONS: { value: CatalogSort; label: string }[] = [
  { value: "relevance", label: "По умолчанию" },
  { value: "name_asc", label: "Название А–Я" },
  { value: "name_desc", label: "Название Я–А" },
  { value: "price_asc", label: "Цена ↑" },
  { value: "price_desc", label: "Цена ↓" },
  { value: "brand_asc", label: "Бренд" },
  { value: "newest", label: "Сначала новые" },
  { value: "hot", label: "Сначала HOT" },
];

const PAGE_SIZE = 120;

type Props = {
  initialProducts?: Product[];
  initialFacets?: CatalogFacets | null;
  productBasePath?: string;
};

export function CatalogBrowser({
  initialProducts = [],
  initialFacets = null,
  productBasePath = "/product",
}: Props) {
  const listboxId = useId();
  const searchWrapRef = useRef<HTMLDivElement>(null);

  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [brand, setBrand] = useState("");
  const [deviceCategory, setDeviceCategory] = useState("");
  const [hotOnly, setHotOnly] = useState(false);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [sort, setSort] = useState<CatalogSort>("relevance");

  const [products, setProducts] = useState<Product[]>(initialProducts);
  const [facets, setFacets] = useState<CatalogFacets | null>(initialFacets);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(initialProducts.length >= PAGE_SIZE);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const [suggestions, setSuggestions] = useState<SuggestItem[]>([]);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [activeSuggest, setActiveSuggest] = useState(-1);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQ(q.trim()), 280);
    return () => window.clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (q.trim().length < 2) {
      setSuggestions([]);
      setSuggestOpen(false);
      return;
    }
    let cancelled = false;
    const t = window.setTimeout(() => {
      void api
        .suggestLive(q.trim())
        .then((items) => {
          if (cancelled) return;
          setSuggestions(items);
          setSuggestOpen(items.length > 0);
          setActiveSuggest(-1);
        })
        .catch(() => {
          if (!cancelled) setSuggestions([]);
        });
    }, 200);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!searchWrapRef.current?.contains(e.target as Node)) {
        setSuggestOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    startTransition(() => {
      void (async () => {
        try {
          const params = {
            q: debouncedQ || undefined,
            brand: brand || undefined,
            device_category: deviceCategory || undefined,
            hot: hotOnly || undefined,
            min_price: minPrice ? Number(minPrice) : undefined,
            max_price: maxPrice ? Number(maxPrice) : undefined,
            sort,
            limit: PAGE_SIZE,
            offset: 0,
          };
          const [nextProducts, nextFacets] = await Promise.all([
            api.productsLive(params),
            api.facetsLive(params),
          ]);
          if (controller.signal.aborted) return;
          setProducts(nextProducts);
          setFacets(nextFacets);
          setOffset(0);
          setHasMore(nextProducts.length >= PAGE_SIZE);
          setError(null);
        } catch {
          if (!controller.signal.aborted) {
            setError("Не удалось загрузить каталог. Проверьте, что API запущен.");
          }
        }
      })();
    });
    return () => controller.abort();
  }, [debouncedQ, brand, deviceCategory, hotOnly, minPrice, maxPrice, sort]);

  async function loadMore() {
    const nextOffset = offset + PAGE_SIZE;
    try {
      const more = await api.productsLive({
        q: debouncedQ || undefined,
        brand: brand || undefined,
        device_category: deviceCategory || undefined,
        hot: hotOnly || undefined,
        min_price: minPrice ? Number(minPrice) : undefined,
        max_price: maxPrice ? Number(maxPrice) : undefined,
        sort,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });
      setProducts((prev) => [...prev, ...more]);
      setOffset(nextOffset);
      setHasMore(more.length >= PAGE_SIZE);
    } catch {
      setError("Не удалось подгрузить ещё товары.");
    }
  }

  function clearFilters() {
    setQ("");
    setDebouncedQ("");
    setBrand("");
    setDeviceCategory("");
    setHotOnly(false);
    setMinPrice("");
    setMaxPrice("");
    setSort("relevance");
    setSuggestOpen(false);
  }

  function pickSuggest(item: SuggestItem) {
    setSuggestOpen(false);
    setQ(item.title);
    setDebouncedQ(item.title);
  }

  function onSearchKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!suggestOpen || !suggestions.length) {
      if (e.key === "Enter") setDebouncedQ(q.trim());
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveSuggest((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveSuggest((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = suggestions[activeSuggest] ?? suggestions[0];
      if (item) pickSuggest(item);
    } else if (e.key === "Escape") {
      setSuggestOpen(false);
    }
  }

  const total = facets?.total ?? products.length;
  const allCategoryCount = (facets?.device_categories ?? []).reduce((sum, c) => sum + c.count, 0);
  const hasActiveFilters =
    Boolean(debouncedQ || brand || deviceCategory || hotOnly || minPrice || maxPrice) ||
    sort !== "relevance";

  return (
    <div className="catalog-browser">
      <div className="catalog-toolbar">
        <div className="catalog-search" ref={searchWrapRef}>
          <label className="sr-only" htmlFor="catalog-q">
            Поиск
          </label>
          <input
            id="catalog-q"
            type="search"
            placeholder="Поиск: iPhone 16, Galaxy, AirPods…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onFocus={() => suggestions.length && setSuggestOpen(true)}
            onKeyDown={onSearchKeyDown}
            autoComplete="off"
            role="combobox"
            aria-expanded={suggestOpen}
            aria-controls={listboxId}
            aria-autocomplete="list"
            aria-activedescendant={
              suggestOpen && suggestions[activeSuggest]
                ? `${listboxId}-${suggestions[activeSuggest].slug}`
                : undefined
            }
          />
          {suggestOpen && suggestions.length > 0 ? (
            <ul id={listboxId} className="catalog-suggest" role="listbox">
              {suggestions.map((item, idx) => (
                <li
                  key={item.slug}
                  id={`${listboxId}-${item.slug}`}
                  role="option"
                  aria-selected={idx === activeSuggest}
                >
                  <button
                    type="button"
                    className={idx === activeSuggest ? "is-active" : undefined}
                    onMouseEnter={() => setActiveSuggest(idx)}
                    onClick={() => pickSuggest(item)}
                  >
                    <span className="catalog-suggest-main">
                      <span className="catalog-suggest-title">
                        {item.title}
                      </span>
                      <span className="catalog-suggest-meta">
                        {[item.brand, item.device_category].filter(Boolean).join(" · ")}
                      </span>
                    </span>
                    <strong>{formatPrice(item.price)}</strong>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className="catalog-sort">
          <label htmlFor="catalog-sort">Сортировка</label>
          <select
            id="catalog-sort"
            value={sort}
            onChange={(e) => setSort(e.target.value as CatalogSort)}
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="catalog-categories" aria-label="Категории">
        <button
          type="button"
          aria-pressed={!deviceCategory}
          className={!deviceCategory ? "is-active" : undefined}
          onClick={() => setDeviceCategory("")}
        >
          Все
          {allCategoryCount > 0 ? (
            <span className="catalog-chip-count">{allCategoryCount}</span>
          ) : null}
        </button>
        {(facets?.device_categories ?? []).map((cat) => (
          <button
            key={cat.value}
            type="button"
            aria-pressed={deviceCategory === cat.value}
            className={deviceCategory === cat.value ? "is-active" : undefined}
            onClick={() => setDeviceCategory(cat.value === deviceCategory ? "" : cat.value)}
          >
            {formatDeviceCategory(cat.value)}
            <span className="catalog-chip-count">{cat.count}</span>
          </button>
        ))}
      </div>

      <div className="catalog-filters">
        <div className="catalog-filter-group">
          <span className="catalog-filter-label">Бренд</span>
          <div className="catalog-chips">
            <button
              type="button"
              aria-pressed={!brand}
              className={!brand ? "is-active" : undefined}
              onClick={() => setBrand("")}
            >
              Все
            </button>
            {(facets?.brands ?? []).map((b) => (
              <button
                key={b.value}
                type="button"
                aria-pressed={brand === b.value}
                className={brand === b.value ? "is-active" : undefined}
                onClick={() => setBrand(b.value === brand ? "" : b.value)}
              >
                {b.value}
                <span className="catalog-chip-count">{b.count}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="catalog-filter-row">
          <label className="catalog-check">
            <input
              type="checkbox"
              checked={hotOnly}
              onChange={(e) => setHotOnly(e.target.checked)}
            />
            Только HOT
          </label>

          <div className="catalog-price-range">
            <span className="catalog-filter-label">Цена, ₽</span>
            <input
              type="number"
              inputMode="numeric"
              placeholder={facets?.price_min ? String(Math.floor(Number(facets.price_min))) : "от"}
              value={minPrice}
              min={0}
              onChange={(e) => setMinPrice(e.target.value)}
              aria-label="Цена от"
            />
            <span aria-hidden>—</span>
            <input
              type="number"
              inputMode="numeric"
              placeholder={facets?.price_max ? String(Math.ceil(Number(facets.price_max))) : "до"}
              value={maxPrice}
              min={0}
              onChange={(e) => setMaxPrice(e.target.value)}
              aria-label="Цена до"
            />
          </div>

          {hasActiveFilters ? (
            <button type="button" className="catalog-clear" onClick={clearFilters}>
              Сбросить
            </button>
          ) : null}
        </div>
      </div>

      <div className="catalog-status" aria-live="polite">
        <p>
          {pending ? "Обновляем…" : `Найдено: ${total}`}
          {deviceCategory ? ` · ${deviceCategory}` : ""}
          {brand ? ` · ${brand}` : ""}
        </p>
      </div>

      {error ? <p className="empty">{error}</p> : null}

      {!error && !products.length && !pending ? (
        <p className="empty">
          Ничего не нашлось.{" "}
          <button type="button" className="linkish" onClick={clearFilters}>
            Сбросить фильтры
          </button>
        </p>
      ) : (
        <ProductGrid products={products} productBasePath={productBasePath} />
      )}

      {hasMore && products.length > 0 ? (
        <div className="catalog-more">
          <button type="button" className="btn btn-ghost" onClick={() => void loadMore()}>
            Показать ещё
          </button>
        </div>
      ) : null}
    </div>
  );
}
